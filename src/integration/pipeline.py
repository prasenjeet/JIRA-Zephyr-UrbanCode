"""Integration pipeline that orchestrates Plane, Wiki.js, Kiwi TCMS, and Harness CD."""

from __future__ import annotations

from typing import Optional

from src.wikijs.client import WikiJsClient
from src.plane.client import PlaneClient
from src.plane.models import Issue
from src.kiwi.client import KiwiTCMSClient
from src.kiwi.models import TestRun, TestStatus
from src.harness.client import HarnessClient
from src.harness.models import PipelineExecution, ExecutionStatus


_DEFAULT_TEST_CASES = [
    "TC-001", "TC-002", "TC-003", "TC-004", "TC-005",
]


def _divider(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


class IntegrationPipeline:
    """Orchestrates the end-to-end QA and deployment workflow.

    Connects Plane → Kiwi TCMS → Wiki.js → Harness CD in a single pipeline:

    1. Fetch Plane issue and transition it to "In QA".
    2. Create a Kiwi TCMS test run linked to the issue.
    3. Execute the test suite (via the Kiwi decoy runner).
    4. Publish a Wiki.js test report page.
    5a. If all tests pass  → trigger Harness pipeline execution → mark Plane "Deployed".
    5b. If any tests fail  → comment on Plane issue → revert state to "In Dev".

    Args:
        plane: :class:`PlaneClient` instance.
        wikijs: :class:`WikiJsClient` instance.
        kiwi: :class:`KiwiTCMSClient` instance.
        harness: :class:`HarnessClient` instance.
        version: Software version under test (used in run summaries / page paths).
    """

    def __init__(
        self,
        plane: PlaneClient,
        wikijs: WikiJsClient,
        kiwi: KiwiTCMSClient,
        harness: HarnessClient,
        version: str = "1.0.0",
    ) -> None:
        self.plane = plane
        self.wikijs = wikijs
        self.kiwi = kiwi
        self.harness = harness
        self.version = version

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run_qa_pipeline(
        self,
        issue_key: str,
        test_case_keys: Optional[list[str]] = None,
        pass_rate: float = 1.0,
        target_environment: str = "Production",
    ) -> dict:
        """Run the full QA → deploy pipeline for a Plane issue.

        Args:
            issue_key: The Plane issue that triggered this pipeline run.
            test_case_keys: Test cases to include in the run.
                Defaults to a standard 5-case suite.
            pass_rate: Fraction of tests that pass (decoy parameter, 0.0–1.0).
            target_environment: Harness CD target environment.

        Returns:
            Summary dict with keys:
            ``issue``, ``test_run``, ``report_page``, ``deployment``,
            ``all_tests_passed``, ``final_status``.
        """
        tc_keys = test_case_keys or _DEFAULT_TEST_CASES

        _divider(f"QA Pipeline — {issue_key} — v{self.version}")

        # ------------------------------------------------------------------ #
        # Step 1: Fetch Plane issue and move to In QA                         #
        # ------------------------------------------------------------------ #
        _divider("Step 1 — Fetching Plane issue")
        issue: Issue = self.plane.get_issue(issue_key)
        print(f"[PIPELINE] Issue: {issue!r}")

        if issue.state != "In QA":
            self.plane.transition_issue(issue_key, "In QA")
            print(f"[PIPELINE] Transitioned {issue_key} to 'In QA'")

        # ------------------------------------------------------------------ #
        # Step 2: Create Kiwi TCMS test run                                   #
        # ------------------------------------------------------------------ #
        _divider("Step 2 — Creating Kiwi TCMS test run")
        run_summary = f"{issue_key} — v{self.version} QA Run"
        test_run: TestRun = self.kiwi.create_test_run(
            summary=run_summary,
            plane_issue_keys=[issue_key],
            version=self.version,
        )
        self.kiwi.add_test_cases(test_run.id, tc_keys)
        self.plane.link_test_run(issue_key, test_run.id)
        print(f"[PIPELINE] Created run {test_run.id!r} with {len(tc_keys)} test cases")

        # ------------------------------------------------------------------ #
        # Step 3: Execute test suite                                           #
        # ------------------------------------------------------------------ #
        _divider("Step 3 — Executing test suite")
        executions = self.kiwi.run_all_tests_decoy(
            run_id=test_run.id,
            pass_rate=pass_rate,
        )
        summary = self.kiwi.get_run_summary(test_run.id)
        print(
            f"[PIPELINE] Results: {summary['passed']}/{summary['total']} passed "
            f"({summary['pass_rate']:.1f}%)"
        )

        # ------------------------------------------------------------------ #
        # Step 4: Publish Wiki.js test report page                            #
        # ------------------------------------------------------------------ #
        _divider("Step 4 — Publishing Wiki.js test report")
        report_title = f"Test Report — {issue_key} — v{self.version}"
        result_dicts = [e.to_dict() for e in executions]
        report_page = self.wikijs.create_test_report_page(
            title=report_title,
            test_results=result_dicts,
        )
        print(f"[PIPELINE] Report published: {report_page.url}")

        self.plane.add_comment(
            issue_key,
            f"Test report published to Wiki.js: {report_page.url}\n"
            f"Results: {summary['passed']}/{summary['total']} passed "
            f"({summary['pass_rate']:.1f}%)",
        )

        # ------------------------------------------------------------------ #
        # Step 5a: All tests passed — deploy                                  #
        # ------------------------------------------------------------------ #
        deployment: Optional[PipelineExecution] = None
        all_passed = summary["all_passed"]

        if all_passed:
            _divider("Step 5a — All tests PASSED — Triggering Harness deployment")
            proj = self.harness.project
            bundle = self.harness.create_artifact_bundle(
                project=proj,
                environment=target_environment,
                name=f"{proj}-v{self.version}",
            )
            deployment = self.harness.execute_pipeline(
                project=proj,
                artifact_bundle=bundle,
                environment=target_environment,
            )
            final_exec_status = self.harness.wait_for_execution(
                execution_id=deployment.id,
            )

            if final_exec_status == ExecutionStatus.SUCCESS:
                self.plane.transition_issue(issue_key, "Deployed")
                self.plane.add_comment(
                    issue_key,
                    f"Harness pipeline execution to {target_environment} SUCCEEDED.\n"
                    f"Execution ID: {deployment.id}\n"
                    f"Artifact Bundle: {bundle.name}\n"
                    f"Log: {deployment.log_url}",
                )
                final_status = "Deployed"
                print(f"[PIPELINE] Execution SUCCEEDED. Issue transitioned to 'Deployed'.")
            else:
                self.plane.add_comment(
                    issue_key,
                    f"Harness pipeline execution to {target_environment} FAILED "
                    f"(ID: {deployment.id}). Rollback initiated.",
                )
                self.harness.rollback_execution(deployment.id)
                final_status = "In QA"
                print(f"[PIPELINE] Execution FAILED. Rollback triggered.")
            deployment.status = final_exec_status

        # ------------------------------------------------------------------ #
        # Step 5b: Tests failed — notify team                                 #
        # ------------------------------------------------------------------ #
        else:
            _divider("Step 5b — Tests FAILED — Returning to In Dev")
            failed_keys = [
                e.test_case_key
                for e in executions
                if e.status == TestStatus.FAILED
            ]
            failure_msg = (
                f"Kiwi TCMS run {test_run.id} FAILED.\n"
                f"Failed test cases: {', '.join(failed_keys)}\n"
                f"Full report: {report_page.url}\n"
                "Returning issue to 'In Dev' for remediation."
            )
            self.plane.add_comment(issue_key, failure_msg)
            self.plane.transition_issue(issue_key, "In Dev")
            final_status = "In Dev"
            print(
                f"[PIPELINE] {len(failed_keys)} test(s) failed. "
                "Issue returned to 'In Dev'."
            )

        _divider("Pipeline Complete")
        result = {
            "issue": issue,
            "test_run": test_run,
            "report_page": report_page,
            "deployment": deployment,
            "all_tests_passed": all_passed,
            "final_status": final_status,
            "summary": summary,
        }
        print(f"[PIPELINE] Final issue state: {final_status!r}")
        return result

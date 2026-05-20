"""Integration pipeline that orchestrates JIRA, Confluence, Zephyr, and UrbanCode."""

from __future__ import annotations

from typing import Optional

from src.confluence.client import ConfluenceClient
from src.jira.client import JiraClient
from src.jira.models import Issue
from src.urbancode.client import UrbanCodeClient
from src.urbancode.models import DeploymentRequest, DeploymentStatus
from src.zephyr.client import ZephyrClient
from src.zephyr.models import TestCycle, TestStatus


_DEFAULT_TEST_CASES = [
    "TC-001", "TC-002", "TC-003", "TC-004", "TC-005",
]


def _divider(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


class IntegrationPipeline:
    """Orchestrates the end-to-end QA and deployment workflow.

    Connects JIRA → Zephyr → Confluence → UrbanCode in a single pipeline:

    1. Fetch JIRA issue and transition it to "In QA".
    2. Create a Zephyr test cycle linked to the issue.
    3. Execute the test suite (via the Zephyr decoy runner).
    4. Publish a Confluence test report page.
    5a. If all tests pass  → trigger UrbanCode deployment → mark JIRA "Deployed".
    5b. If any tests fail  → comment on JIRA issue → revert status to "In Dev".

    Args:
        jira: :class:`JiraClient` instance.
        confluence: :class:`ConfluenceClient` instance.
        zephyr: :class:`ZephyrClient` instance.
        urbancode: :class:`UrbanCodeClient` instance.
        version: Software version under test (used in cycle names / snapshots).
    """

    def __init__(
        self,
        jira: JiraClient,
        confluence: ConfluenceClient,
        zephyr: ZephyrClient,
        urbancode: UrbanCodeClient,
        version: str = "1.0.0",
    ) -> None:
        self.jira = jira
        self.confluence = confluence
        self.zephyr = zephyr
        self.urbancode = urbancode
        self.version = version

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run_qa_pipeline(
        self,
        jira_issue_key: str,
        test_case_keys: Optional[list[str]] = None,
        pass_rate: float = 1.0,
        target_environment: str = "Production",
    ) -> dict:
        """Run the full QA → deploy pipeline for a JIRA issue.

        Args:
            jira_issue_key: The JIRA issue that triggered this pipeline run.
            test_case_keys: Test cases to include in the cycle.
                Defaults to a standard 5-case suite.
            pass_rate: Fraction of tests that pass (decoy parameter, 0.0–1.0).
            target_environment: UrbanCode Deploy target environment.

        Returns:
            Summary dict with keys:
            ``issue``, ``cycle``, ``report_page``, ``deployment``,
            ``all_tests_passed``, ``final_status``.
        """
        tc_keys = test_case_keys or _DEFAULT_TEST_CASES

        _divider(f"QA Pipeline — {jira_issue_key} — v{self.version}")

        # ------------------------------------------------------------------ #
        # Step 1: Fetch JIRA issue and move to In QA                          #
        # ------------------------------------------------------------------ #
        _divider("Step 1 — Fetching JIRA issue")
        issue: Issue = self.jira.get_issue(jira_issue_key)
        print(f"[PIPELINE] Issue: {issue!r}")

        if issue.status != "In QA":
            self.jira.transition_issue(jira_issue_key, "In QA")
            print(f"[PIPELINE] Transitioned {jira_issue_key} to 'In QA'")

        # ------------------------------------------------------------------ #
        # Step 2: Create Zephyr test cycle                                     #
        # ------------------------------------------------------------------ #
        _divider("Step 2 — Creating Zephyr test cycle")
        cycle_name = f"{jira_issue_key} — v{self.version} QA Cycle"
        cycle: TestCycle = self.zephyr.create_test_cycle(
            name=cycle_name,
            jira_issue_keys=[jira_issue_key],
            version=self.version,
        )
        self.zephyr.add_test_cases(cycle.id, tc_keys)
        self.jira.link_test_cycle(jira_issue_key, cycle.id)
        print(f"[PIPELINE] Created cycle {cycle.id!r} with {len(tc_keys)} test cases")

        # ------------------------------------------------------------------ #
        # Step 3: Execute test suite                                           #
        # ------------------------------------------------------------------ #
        _divider("Step 3 — Executing test suite")
        results = self.zephyr.run_all_tests_decoy(
            cycle_id=cycle.id,
            pass_rate=pass_rate,
        )
        summary = self.zephyr.get_cycle_summary(cycle.id)
        print(
            f"[PIPELINE] Results: {summary['passed']}/{summary['total']} passed "
            f"({summary['pass_rate']:.1f}%)"
        )

        # ------------------------------------------------------------------ #
        # Step 4: Publish Confluence test report                               #
        # ------------------------------------------------------------------ #
        _divider("Step 4 — Publishing Confluence test report")
        report_title = f"Test Report — {jira_issue_key} — v{self.version}"
        result_dicts = [r.to_dict() for r in results]
        report_page = self.confluence.create_test_report_page(
            title=report_title,
            test_results=result_dicts,
        )
        print(f"[PIPELINE] Report published: {report_page.url}")

        # Add Confluence link as JIRA comment
        self.jira.add_comment(
            jira_issue_key,
            f"Test report published to Confluence: {report_page.url}\n"
            f"Results: {summary['passed']}/{summary['total']} passed "
            f"({summary['pass_rate']:.1f}%)",
        )

        # ------------------------------------------------------------------ #
        # Step 5a: All tests passed — deploy                                  #
        # ------------------------------------------------------------------ #
        deployment: Optional[DeploymentRequest] = None
        all_passed = summary["all_passed"]

        if all_passed:
            _divider("Step 5a — All tests PASSED — Triggering deployment")
            app_name = self.urbancode.application
            snapshot = self.urbancode.create_snapshot(
                application=app_name,
                environment=target_environment,
                name=f"{app_name}-v{self.version}",
            )
            deployment = self.urbancode.request_deployment(
                application=app_name,
                snapshot=snapshot,
                process="Deploy",
                environment=target_environment,
            )
            final_deploy_status = self.urbancode.wait_for_deployment(
                request_id=deployment.id,
            )

            if final_deploy_status == DeploymentStatus.SUCCEEDED:
                self.jira.transition_issue(jira_issue_key, "Deployed")
                self.jira.add_comment(
                    jira_issue_key,
                    f"Deployment to {target_environment} SUCCEEDED.\n"
                    f"Deployment ID: {deployment.id}\n"
                    f"Snapshot: {snapshot.name}\n"
                    f"Log: {deployment.log_url}",
                )
                final_status = "Deployed"
                print(f"[PIPELINE] Deployment SUCCEEDED. Issue transitioned to 'Deployed'.")
            else:
                self.jira.add_comment(
                    jira_issue_key,
                    f"Deployment to {target_environment} FAILED (ID: {deployment.id}). "
                    "Rollback initiated.",
                )
                self.urbancode.rollback_deployment(deployment.id)
                final_status = "In QA"
                print(f"[PIPELINE] Deployment FAILED. Rollback triggered.")
            deployment.status = final_deploy_status  # keep the object consistent

        # ------------------------------------------------------------------ #
        # Step 5b: Tests failed — notify team                                 #
        # ------------------------------------------------------------------ #
        else:
            _divider("Step 5b — Tests FAILED — Returning to In Dev")
            failed_keys = [
                r.test_case_key
                for r in results
                if r.status == TestStatus.FAIL
            ]
            failure_msg = (
                f"QA cycle {cycle.id} FAILED.\n"
                f"Failed test cases: {', '.join(failed_keys)}\n"
                f"Full report: {report_page.url}\n"
                "Returning issue to 'In Dev' for remediation."
            )
            self.jira.add_comment(jira_issue_key, failure_msg)
            self.jira.transition_issue(jira_issue_key, "In Dev")
            final_status = "In Dev"
            print(
                f"[PIPELINE] {len(failed_keys)} test(s) failed. "
                "Issue returned to 'In Dev'."
            )

        _divider("Pipeline Complete")
        result = {
            "issue": issue,
            "cycle": cycle,
            "report_page": report_page,
            "deployment": deployment,
            "all_tests_passed": all_passed,
            "final_status": final_status,
            "summary": summary,
        }
        print(f"[PIPELINE] Final issue status: {final_status!r}")
        return result

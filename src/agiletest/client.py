"""AgileTest Decoy Client - simulates the AgileTest for JIRA REST API.

AgileTest is a JIRA-native test management app (Atlassian Marketplace).
Test cases are JIRA issues of type "Test"; test plans and executions are
managed through the AgileTest REST API at /rest/agiletest/1.0/.

All methods print "[AGILETEST DECOY]" prefixed messages and return
realistic mock data. Simulated network latency of ~100ms is included
via time.sleep(0.1).
"""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from .models import TestCase, TestExecution, TestPlan, TestStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PLAN_COUNTER: int = 0
_TC_COUNTER: int = 0

_SAMPLE_TEST_NAMES = [
    "Verify user login with valid credentials",
    "Verify user login with invalid credentials",
    "Verify dashboard loads within 3 seconds",
    "Verify API returns 200 on health check",
    "Verify data export produces correct CSV",
    "Verify search returns relevant results",
    "Verify session timeout after inactivity",
    "Verify password reset email is sent",
    "Verify file upload handles large files",
    "Verify form validation on required fields",
]

_SAMPLE_STEPS = [
    "Navigate to the application URL",
    "Enter test credentials",
    "Perform the action under test",
    "Assert the expected response",
    "Verify the UI reflects the updated state",
]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _short_id() -> str:
    return uuid.uuid4().hex[:8].upper()


def _next_plan_id() -> str:
    global _PLAN_COUNTER
    _PLAN_COUNTER += 1
    return f"PLAN-{_PLAN_COUNTER:04d}"


def _next_tc_key(project_key: str) -> str:
    global _TC_COUNTER
    _TC_COUNTER += 1
    return f"{project_key}-T{_TC_COUNTER}"


# ---------------------------------------------------------------------------
# AgiletestClient
# ---------------------------------------------------------------------------


class AgiletestClient:
    """Decoy AgileTest client that simulates the AgileTest for JIRA REST API.

    All operations are performed in-memory.  Test cases are JIRA issues of
    type "Test"; test plans collect them for a coordinated execution run.

    Args:
        base_url: JIRA/AgileTest instance base URL (e.g. ``https://org.atlassian.net``).
        api_key: AgileTest API key (generated in JIRA → Apps → AgileTest → Settings).
        project_key: Default JIRA project key.
        use_decoy: When ``True`` all methods use in-memory mock data.
    """

    def __init__(
        self,
        base_url: str = "https://your-org.atlassian.net",
        api_key: str = "decoy-agiletest-key",
        project_key: str = "DEMO",
        use_decoy: bool = True,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.project_key = project_key
        self.use_decoy = use_decoy

        self._plans: dict[str, TestPlan] = {}
        self._test_cases: dict[str, TestCase] = {}

        self._seed_test_cases()
        self._log("AgiletestClient initialised (decoy mode).")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        print(f"[AGILETEST DECOY] {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

    def _api(self, path: str) -> str:
        return f"{self.base_url}/rest/agiletest/1.0/{path}"

    def _seed_test_cases(self) -> None:
        """Pre-populate a set of realistic test cases."""
        for i, name in enumerate(_SAMPLE_TEST_NAMES[:5]):
            key = _next_tc_key(self.project_key)
            tc = TestCase(
                key=key,
                name=name,
                description=f"Automated test: {name}",
                steps=_SAMPLE_STEPS[:3],
                labels=["automated", "regression"],
                priority="High" if i < 2 else "Normal",
                created=_now(),
                updated=_now(),
            )
            self._test_cases[key] = tc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_test_plan(
        self,
        name: str,
        jira_issue_keys: list[str] | None = None,
        version: str = "Unversioned",
        project_key: str | None = None,
    ) -> TestPlan:
        """Create a new AgileTest test plan.

        Args:
            name: Human-readable plan name.
            jira_issue_keys: JIRA issue keys this plan is linked to.
            version: Target version / fix version.
            project_key: Project key (defaults to ``self.project_key``).

        Returns:
            Newly created :class:`TestPlan`.
        """
        self._simulate_latency()
        pk = project_key or self.project_key
        plan_id = _next_plan_id()
        _jira_keys = list(jira_issue_keys) if jira_issue_keys else []
        self._log(f"POST {self._api('testplan')}  (project={pk!r})")
        self._log(f"  name        : {name!r}")
        self._log(f"  jira_issues : {_jira_keys}")
        self._log(f"  version     : {version!r}")

        plan = TestPlan(
            id=plan_id,
            name=name,
            project_key=pk,
            version=version,
            jira_issue_keys=_jira_keys,
            created=_now(),
            updated=_now(),
        )
        self._plans[plan_id] = plan
        self._log(f"  -> Created {plan!r}")
        return plan

    def get_test_plan(self, plan_id: str) -> TestPlan:
        """Fetch an existing test plan by ID.

        Args:
            plan_id: Plan identifier (e.g. ``"PLAN-0001"``).

        Returns:
            :class:`TestPlan` from the decoy store.

        Raises:
            KeyError: If the plan is not found.
        """
        self._simulate_latency()
        self._log(f"GET {self._api(f'testplan/{plan_id}')}")

        if plan_id not in self._plans:
            raise KeyError(f"Test plan {plan_id!r} not found in decoy store.")

        plan = self._plans[plan_id]
        self._log(f"  -> Returning {plan!r}")
        return plan

    def add_test_cases(self, plan_id: str, test_case_keys: list[str]) -> TestPlan:
        """Add test cases to an existing test plan.

        Args:
            plan_id: Target plan ID.
            test_case_keys: List of JIRA test issue keys to add.

        Returns:
            Updated :class:`TestPlan`.

        Raises:
            KeyError: If the plan is not found.
        """
        self._simulate_latency()
        self._log(f"POST {self._api(f'testplan/{plan_id}/testcases')}")
        self._log(f"  adding {len(test_case_keys)} test case(s): {test_case_keys}")

        plan = self.get_test_plan(plan_id)
        for key in test_case_keys:
            if key not in plan.test_case_keys:
                plan.test_case_keys.append(key)
                if key not in self._test_cases:
                    idx = len(self._test_cases)
                    self._test_cases[key] = TestCase(
                        key=key,
                        name=_SAMPLE_TEST_NAMES[idx % len(_SAMPLE_TEST_NAMES)],
                        description=f"Auto-created test case {key}",
                        steps=_SAMPLE_STEPS,
                        labels=["automated"],
                        created=_now(),
                        updated=_now(),
                    )

        plan.updated = _now()
        self._log(f"  -> Plan {plan_id} now has {len(plan.test_case_keys)} test case(s)")
        return plan

    def execute_test(
        self,
        plan_id: str,
        test_case_key: str,
        status: TestStatus | str,
        comment: str = "",
        executed_by: str = "automation",
        duration_ms: int | None = None,
    ) -> TestExecution:
        """Record the execution result of a test case within a test plan.

        Args:
            plan_id: The plan the test belongs to.
            test_case_key: The test case being executed.
            status: Execution status (PASS/FAIL/BLOCKED/…).
            comment: Optional comment about the execution.
            executed_by: Who executed the test.
            duration_ms: Optional execution duration in milliseconds.

        Returns:
            Newly created :class:`TestExecution`.

        Raises:
            KeyError: If the plan is not found.
        """
        self._simulate_latency()
        if isinstance(status, str):
            status = TestStatus(status.upper())

        self._log(
            f"POST {self._api('testexecution')}  "
            f"(plan={plan_id}, tc={test_case_key}, status={status})"
        )

        plan = self.get_test_plan(plan_id)
        tc = self._test_cases.get(test_case_key)
        test_name = tc.name if tc else f"Test {test_case_key}"

        execution = TestExecution(
            id=_short_id(),
            test_case_key=test_case_key,
            test_name=test_name,
            status=status,
            plan_id=plan_id,
            comment=comment,
            executed_by=executed_by,
            executed_at=_now(),
            duration_ms=duration_ms if duration_ms is not None else random.randint(200, 5000),
        )
        plan.executions.append(execution)
        plan.updated = _now()
        self._log(f"  -> Recorded {execution!r}  (comment: {comment[:50]!r})")
        return execution

    def get_test_executions(self, plan_id: str) -> list[TestExecution]:
        """Return all test executions for a given test plan.

        Args:
            plan_id: Plan identifier.

        Returns:
            List of :class:`TestExecution` objects.

        Raises:
            KeyError: If the plan is not found.
        """
        self._simulate_latency()
        self._log(f"GET {self._api('testexecution')}?planId={plan_id}")

        plan = self.get_test_plan(plan_id)
        self._log(f"  -> {len(plan.executions)} execution(s) found")
        return list(plan.executions)

    def get_plan_summary(self, plan_id: str) -> dict[str, Any]:
        """Return a summary dict with pass/fail/total counts and pass rate.

        Args:
            plan_id: Plan identifier.

        Returns:
            Dict with keys: ``plan_id``, ``name``, ``total``, ``passed``,
            ``failed``, ``blocked``, ``unexecuted``, ``pass_rate``,
            ``all_passed``.

        Raises:
            KeyError: If the plan is not found.
        """
        self._simulate_latency()
        self._log(f"GET {self._api(f'testplan/{plan_id}/summary')}")

        plan = self.get_test_plan(plan_id)
        blocked = sum(1 for e in plan.executions if e.status == TestStatus.BLOCKED)
        unexecuted = sum(1 for e in plan.executions if e.status == TestStatus.UNEXECUTED)

        summary: dict[str, Any] = {
            "plan_id": plan_id,
            "name": plan.name,
            "total": plan.total_count,
            "passed": plan.pass_count,
            "failed": plan.fail_count,
            "blocked": blocked,
            "unexecuted": unexecuted,
            "pass_rate": round(plan.pass_rate * 100, 1),
            "jira_issue_keys": plan.jira_issue_keys,
            "version": plan.version,
        }
        summary["all_passed"] = summary["failed"] == 0 and summary["total"] > 0
        self._log(
            f"  -> Summary: {summary['passed']}/{summary['total']} passed "
            f"({summary['pass_rate']}%)"
        )
        return summary

    def run_all_tests_decoy(
        self,
        plan_id: str,
        pass_rate: float = 1.0,
    ) -> list[TestExecution]:
        """Execute all test cases in a plan using a configurable pass rate.

        Convenience method for decoy/demo use that automatically executes
        every test case in the plan, determining pass/fail based on
        *pass_rate*.

        Args:
            plan_id: The plan whose test cases should be executed.
            pass_rate: Fraction of tests that should PASS (0.0–1.0). The
                first ``int(n * pass_rate)`` tests will PASS; the remainder
                will FAIL.

        Returns:
            List of :class:`TestExecution` objects, one per test case.

        Raises:
            KeyError: If the plan is not found.
        """
        self._simulate_latency()
        self._log(f"run_all_tests_decoy: plan={plan_id!r}, pass_rate={pass_rate:.0%}")
        plan = self.get_test_plan(plan_id)

        if not plan.test_case_keys:
            self._log("  No test cases in plan — nothing to execute.")
            return []

        n = len(plan.test_case_keys)
        pass_count = round(n * pass_rate)
        executions: list[TestExecution] = []

        for i, tc_key in enumerate(plan.test_case_keys):
            status = TestStatus.PASS if i < pass_count else TestStatus.FAIL
            comment = (
                "Automated execution: PASSED."
                if status == TestStatus.PASS
                else "Automated execution: FAILED — assertion error."
            )
            execution = self.execute_test(
                plan_id=plan_id,
                test_case_key=tc_key,
                status=status,
                comment=comment,
                executed_by="decoy-runner",
            )
            executions.append(execution)

        self._log(
            f"  -> Executed {n} test(s): "
            f"{pass_count} PASS, {n - pass_count} FAIL"
        )
        return executions

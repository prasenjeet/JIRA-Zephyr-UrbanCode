"""Zephyr Scale Decoy Client - simulates the Zephyr Scale REST API.

All methods print "[ZEPHYR DECOY]" prefixed messages and return realistic mock data.
Simulated network latency of ~100ms is included via time.sleep(0.1).
"""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from .base import BaseZephyrClient
from .models import TestCase, TestCycle, TestResult, TestStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CYCLE_COUNTER: int = 0
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
    "Navigate to the login page",
    "Enter valid test credentials",
    "Click the Submit button",
    "Assert the expected response is returned",
    "Verify the UI reflects the updated state",
]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _short_id() -> str:
    return uuid.uuid4().hex[:8].upper()


def _next_cycle_id() -> str:
    global _CYCLE_COUNTER
    _CYCLE_COUNTER += 1
    return f"CYC-{_CYCLE_COUNTER:04d}"


def _next_tc_key(project_key: str) -> str:
    global _TC_COUNTER
    _TC_COUNTER += 1
    return f"{project_key}-T{_TC_COUNTER}"


# ---------------------------------------------------------------------------
# DecoyZephyrClient
# ---------------------------------------------------------------------------


class DecoyZephyrClient(BaseZephyrClient):
    """Decoy Zephyr Scale client that simulates the Zephyr Scale REST API.

    All operations are performed in-memory.

    Args:
        base_url: Zephyr/JIRA instance base URL.
        api_token: Zephyr Scale API token.
        project_key: Default JIRA/Zephyr project key.
    """

    def __init__(
        self,
        base_url: str = "https://your-org.atlassian.net",
        api_token: str = "decoy-zephyr-token",
        project_key: str = "DEMO",
        **kwargs,
    ) -> None:
        self.base_url = base_url
        self.api_token = api_token
        self.project_key = project_key
        self.use_decoy = True

        self._cycles: dict[str, TestCycle] = {}
        self._test_cases: dict[str, TestCase] = {}

        # Seed a handful of reusable test cases
        self._seed_test_cases()

        self._log("DecoyZephyrClient initialised.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        print(f"[ZEPHYR DECOY] {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

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

    def create_test_cycle(
        self,
        name: str,
        jira_issue_keys: list[str] | None = None,
        version: str = "Unversioned",
        project_key: str | None = None,
    ) -> TestCycle:
        """Create a new Zephyr test cycle.

        Args:
            name: Human-readable cycle name.
            jira_issue_keys: JIRA issue keys this cycle is linked to.
            version: Target version / fix version.
            project_key: Project key (defaults to ``self.project_key``).

        Returns:
            Newly created :class:`TestCycle`.
        """
        self._simulate_latency()
        pk = project_key or self.project_key
        cycle_id = _next_cycle_id()
        _jira_keys = list(jira_issue_keys) if jira_issue_keys else []
        self._log(f"POST /api/v2/testcycles  (project={pk!r})")
        self._log(f"  name        : {name!r}")
        self._log(f"  jira_issues : {_jira_keys}")
        self._log(f"  version     : {version!r}")

        cycle = TestCycle(
            id=cycle_id,
            name=name,
            project_key=pk,
            version=version,
            jira_issue_keys=_jira_keys,
            created=_now(),
            updated=_now(),
        )
        self._cycles[cycle_id] = cycle
        self._log(f"  -> Created {cycle!r}")
        return cycle

    def get_test_cycle(self, cycle_id: str) -> TestCycle:
        """Fetch an existing test cycle by ID.

        Args:
            cycle_id: Cycle identifier (e.g. ``"CYC-0001"``).

        Returns:
            :class:`TestCycle` from the decoy store.

        Raises:
            KeyError: If the cycle is not found.
        """
        self._simulate_latency()
        self._log(f"GET /api/v2/testcycles/{cycle_id}")

        if cycle_id not in self._cycles:
            raise KeyError(f"Test cycle {cycle_id!r} not found in decoy store.")

        cycle = self._cycles[cycle_id]
        self._log(f"  -> Returning {cycle!r}")
        return cycle

    def add_test_cases(self, cycle_id: str, test_case_keys: list[str]) -> TestCycle:
        """Add test cases to an existing test cycle.

        Args:
            cycle_id: Target cycle ID.
            test_case_keys: List of test case keys to add.

        Returns:
            Updated :class:`TestCycle`.

        Raises:
            KeyError: If the cycle is not found.
        """
        self._simulate_latency()
        self._log(f"POST /api/v2/testcycles/{cycle_id}/testcases")
        self._log(f"  adding {len(test_case_keys)} test case(s): {test_case_keys}")

        cycle = self.get_test_cycle(cycle_id)
        for key in test_case_keys:
            if key not in cycle.test_case_keys:
                cycle.test_case_keys.append(key)
                # Auto-create the test case if not already known
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

        cycle.updated = _now()
        self._log(f"  -> Cycle {cycle_id} now has {len(cycle.test_case_keys)} test case(s)")
        return cycle

    def execute_test(
        self,
        cycle_id: str,
        test_case_key: str,
        status: TestStatus | str,
        comment: str = "",
        executed_by: str = "automation",
        duration_ms: int | None = None,
    ) -> TestResult:
        """Record the execution of a test case within a cycle.

        Args:
            cycle_id: The cycle the test belongs to.
            test_case_key: The test case being executed.
            status: Execution status (PASS/FAIL/BLOCKED/…).
            comment: Optional comment about the execution.
            executed_by: Who executed the test.
            duration_ms: Optional execution duration in milliseconds.

        Returns:
            Newly created :class:`TestResult`.

        Raises:
            KeyError: If the cycle is not found.
        """
        self._simulate_latency()
        if isinstance(status, str):
            status = TestStatus(status.upper())

        self._log(
            f"POST /api/v2/testexecutions  "
            f"(cycle={cycle_id}, tc={test_case_key}, status={status})"
        )

        cycle = self.get_test_cycle(cycle_id)
        tc = self._test_cases.get(test_case_key)
        test_name = tc.name if tc else f"Test {test_case_key}"

        result = TestResult(
            id=_short_id(),
            test_case_key=test_case_key,
            test_name=test_name,
            status=status,
            cycle_id=cycle_id,
            comment=comment,
            executed_by=executed_by,
            executed_at=_now(),
            duration_ms=duration_ms if duration_ms is not None else random.randint(200, 5000),
        )
        cycle.results.append(result)
        cycle.updated = _now()
        self._log(
            f"  -> Recorded {result!r}  (comment: {comment[:50]!r})"
        )
        return result

    def get_test_results(self, cycle_id: str) -> list[TestResult]:
        """Return all test results for a given cycle.

        Args:
            cycle_id: Cycle identifier.

        Returns:
            List of :class:`TestResult` objects.

        Raises:
            KeyError: If the cycle is not found.
        """
        self._simulate_latency()
        self._log(f"GET /api/v2/testexecutions?cycleId={cycle_id}")

        cycle = self.get_test_cycle(cycle_id)
        self._log(f"  -> {len(cycle.results)} result(s) found")
        return list(cycle.results)

    def get_cycle_summary(self, cycle_id: str) -> dict[str, Any]:
        """Return a summary dict with pass/fail/total counts and pass rate.

        Args:
            cycle_id: Cycle identifier.

        Returns:
            Dict with keys: ``cycle_id``, ``name``, ``total``, ``passed``,
            ``failed``, ``blocked``, ``not_executed``, ``pass_rate``.

        Raises:
            KeyError: If the cycle is not found.
        """
        self._simulate_latency()
        self._log(f"GET /api/v2/testcycles/{cycle_id}/summary")

        cycle = self.get_test_cycle(cycle_id)
        blocked = sum(1 for r in cycle.results if r.status == TestStatus.BLOCKED)
        not_exec = sum(1 for r in cycle.results if r.status == TestStatus.NOT_EXECUTED)

        summary: dict[str, Any] = {
            "cycle_id": cycle_id,
            "name": cycle.name,
            "total": cycle.total_count,
            "passed": cycle.pass_count,
            "failed": cycle.fail_count,
            "blocked": blocked,
            "not_executed": not_exec,
            "pass_rate": round(cycle.pass_rate * 100, 1),
            "jira_issue_keys": cycle.jira_issue_keys,
            "version": cycle.version,
        }
        summary["all_passed"] = summary["failed"] == 0 and summary["total"] > 0
        self._log(
            f"  -> Summary: {summary['passed']}/{summary['total']} passed "
            f"({summary['pass_rate']}%)"
        )
        return summary

    def run_test_suite(
        self,
        cycle_id: str,
        pass_rate: float = 1.0,
    ) -> list[TestResult]:
        """Execute all test cases in a cycle using a configurable pass rate.

        This is a convenience method for decoy/demo use that automatically
        executes every test case added to the cycle, determining pass/fail
        based on *pass_rate*.

        Args:
            cycle_id: The cycle whose test cases should be executed.
            pass_rate: Fraction of tests that should PASS (0.0–1.0). The
                first ``int(n * pass_rate)`` tests will PASS; the remainder
                will FAIL.

        Returns:
            List of :class:`TestResult` objects, one per test case.

        Raises:
            KeyError: If the cycle is not found.
        """
        self._simulate_latency()
        self._log(
            f"run_test_suite: cycle={cycle_id!r}, pass_rate={pass_rate:.0%}"
        )
        cycle = self.get_test_cycle(cycle_id)

        if not cycle.test_case_keys:
            self._log("  No test cases in cycle — nothing to execute.")
            return []

        n = len(cycle.test_case_keys)
        pass_count = round(n * pass_rate)
        results: list[TestResult] = []

        for i, tc_key in enumerate(cycle.test_case_keys):
            status = TestStatus.PASS if i < pass_count else TestStatus.FAIL
            comment = (
                "Automated execution: PASSED."
                if status == TestStatus.PASS
                else "Automated execution: FAILED — assertion error."
            )
            result = self.execute_test(
                cycle_id=cycle_id,
                test_case_key=tc_key,
                status=status,
                comment=comment,
                executed_by="decoy-runner",
            )
            results.append(result)

        self._log(
            f"  -> Executed {n} test(s): "
            f"{pass_count} PASS, {n - pass_count} FAIL"
        )
        return results

    # Backward-compatibility alias
    def run_all_tests_decoy(
        self,
        cycle_id: str,
        pass_rate: float = 1.0,
    ) -> list[TestResult]:
        """Alias for :meth:`run_test_suite` kept for backward compatibility."""
        return self.run_test_suite(cycle_id=cycle_id, pass_rate=pass_rate)

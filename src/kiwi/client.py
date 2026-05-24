"""Kiwi TCMS Decoy Client - simulates the Kiwi TCMS XML-RPC / REST API.

All methods print "[KIWI DECOY]" prefixed messages and return realistic mock data.
Kiwi TCMS exposes an XML-RPC API; method names here mirror the real RPC surface.
"""

from __future__ import annotations

import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .models import TestCase, TestExecution, TestRun, TestStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RUN_COUNTER: int = 0
_TC_COUNTER: int = 0
_EXEC_COUNTER: int = 0

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
    "Navigate to the target page",
    "Enter test data as specified",
    "Trigger the action under test",
    "Assert the expected response is returned",
    "Verify the UI reflects the updated state",
]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _short_id() -> str:
    return uuid.uuid4().hex[:8].upper()


def _next_run_id() -> str:
    global _RUN_COUNTER
    _RUN_COUNTER += 1
    return f"RUN-{_RUN_COUNTER:04d}"


def _next_tc_id() -> int:
    global _TC_COUNTER
    _TC_COUNTER += 1
    return _TC_COUNTER


def _next_exec_id() -> int:
    global _EXEC_COUNTER
    _EXEC_COUNTER += 1
    return _EXEC_COUNTER


# ---------------------------------------------------------------------------
# KiwiTCMSClient
# ---------------------------------------------------------------------------


class KiwiTCMSClient:
    """Decoy Kiwi TCMS client that simulates the Kiwi TCMS API.

    All operations are performed in-memory.

    Args:
        base_url: Kiwi TCMS instance URL (e.g. ``https://tcms.example.com``).
        username: Kiwi TCMS username.
        api_key: Kiwi TCMS API key.
        product: Default product name.
        use_decoy: When ``True`` all methods use in-memory mock data.
    """

    def __init__(
        self,
        base_url: str = "https://tcms.example.com",
        username: str = "decoy@example.com",
        api_key: str = "decoy-kiwi-token",
        product: str = "Demo Product",
        use_decoy: bool = True,
    ) -> None:
        self.base_url = base_url
        self.username = username
        self.api_key = api_key
        self.product = product
        self.use_decoy = use_decoy

        self._runs: dict[str, TestRun] = {}
        self._test_cases: dict[str, TestCase] = {}

        self._seed_test_cases()
        self._log("KiwiTCMSClient initialised (decoy mode).")

    def _log(self, message: str) -> None:
        print(f"[KIWI DECOY] {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

    def _seed_test_cases(self) -> None:
        for i, name in enumerate(_SAMPLE_TEST_NAMES[:5]):
            tc_id = _next_tc_id()
            key = f"TC-{tc_id:03d}"
            tc = TestCase(
                id=tc_id,
                summary=name,
                text=f"Automated test: {name}",
                steps=_SAMPLE_STEPS[:3],
                tags=["automated", "regression"],
                priority="P1" if i < 2 else "P2",
                created_at=_now(),
                updated_at=_now(),
            )
            self._test_cases[key] = tc

    # ------------------------------------------------------------------
    # Public API  (mirrors Kiwi TCMS XML-RPC methods)
    # ------------------------------------------------------------------

    def create_test_run(
        self,
        summary: str,
        plane_issue_keys: Optional[list[str]] = None,
        version: str = "unspecified",
        product: Optional[str] = None,
    ) -> TestRun:
        """Create a new Kiwi TCMS test run (``TestRun.create``).

        Args:
            summary: Human-readable run summary.
            plane_issue_keys: Plane issue keys this run relates to.
            version: Product version under test.
            product: Product name (defaults to ``self.product``).

        Returns:
            Newly created :class:`TestRun`.
        """
        self._simulate_latency()
        prod = product or self.product
        run_id = _next_run_id()
        issue_keys = list(plane_issue_keys) if plane_issue_keys else []

        self._log("TestRun.create →")
        self._log(f"  summary       : {summary!r}")
        self._log(f"  product       : {prod!r}")
        self._log(f"  version       : {version!r}")
        self._log(f"  plane_issues  : {issue_keys}")

        run = TestRun(
            id=run_id,
            summary=summary,
            product=prod,
            version=version,
            plane_issue_keys=issue_keys,
            created_at=_now(),
            updated_at=_now(),
        )
        self._runs[run_id] = run
        self._log(f"  -> Created {run!r}")
        return run

    def get_test_run(self, run_id: str) -> TestRun:
        """Fetch an existing test run by ID (``TestRun.get``).

        Args:
            run_id: Run identifier (e.g. ``"RUN-0001"``).

        Returns:
            :class:`TestRun` from the decoy store.

        Raises:
            KeyError: If the run is not found.
        """
        self._simulate_latency()
        self._log(f"TestRun.get(run_id={run_id!r})")

        if run_id not in self._runs:
            raise KeyError(f"TestRun {run_id!r} not found in decoy store.")

        run = self._runs[run_id]
        self._log(f"  -> Returning {run!r}")
        return run

    def add_test_cases(self, run_id: str, test_case_keys: list[str]) -> TestRun:
        """Add test cases to an existing test run (``TestRun.add_case``).

        Args:
            run_id: Target run ID.
            test_case_keys: List of test case keys to add.

        Returns:
            Updated :class:`TestRun`.

        Raises:
            KeyError: If the run is not found.
        """
        self._simulate_latency()
        self._log(f"TestRun.add_case(run_id={run_id!r})")
        self._log(f"  adding {len(test_case_keys)} case(s): {test_case_keys}")

        run = self.get_test_run(run_id)
        for key in test_case_keys:
            if key not in run.test_case_keys:
                run.test_case_keys.append(key)
                if key not in self._test_cases:
                    tc_id = _next_tc_id()
                    idx = len(self._test_cases)
                    self._test_cases[key] = TestCase(
                        id=tc_id,
                        summary=_SAMPLE_TEST_NAMES[idx % len(_SAMPLE_TEST_NAMES)],
                        text=f"Auto-created test case {key}",
                        steps=_SAMPLE_STEPS,
                        tags=["automated"],
                        created_at=_now(),
                        updated_at=_now(),
                    )

        run.updated_at = _now()
        self._log(f"  -> Run {run_id} now has {len(run.test_case_keys)} case(s)")
        return run

    def record_test_execution(
        self,
        run_id: str,
        test_case_key: str,
        status: TestStatus | str,
        comment: str = "",
        tested_by: str = "automation",
        duration_ms: Optional[int] = None,
    ) -> TestExecution:
        """Record the execution of a test case within a run (``TestExecution.update``).

        Args:
            run_id: The run the test case belongs to.
            test_case_key: The test case being executed.
            status: Execution status (PASSED/FAILED/BLOCKED/…).
            comment: Optional comment about the execution.
            tested_by: Who ran the test.
            duration_ms: Optional execution duration in milliseconds.

        Returns:
            Newly created :class:`TestExecution`.

        Raises:
            KeyError: If the run is not found.
        """
        self._simulate_latency()
        if isinstance(status, str):
            status = TestStatus(status.upper())

        self._log(
            f"TestExecution.update(run={run_id}, tc={test_case_key}, "
            f"status={status})"
        )

        run = self.get_test_run(run_id)
        tc = self._test_cases.get(test_case_key)
        test_name = tc.summary if tc else f"Test {test_case_key}"
        tc_id = tc.id if tc else 0

        execution = TestExecution(
            id=_next_exec_id(),
            test_case_id=tc_id,
            test_case_key=test_case_key,
            test_name=test_name,
            status=status,
            run_id=run_id,
            comment=comment,
            tested_by=tested_by,
            tested_at=_now(),
            duration_ms=duration_ms if duration_ms is not None else random.randint(200, 5000),
        )
        run.executions.append(execution)
        run.updated_at = _now()
        self._log(
            f"  -> Recorded {execution!r}  (comment: {comment[:50]!r})"
        )
        return execution

    def get_test_executions(self, run_id: str) -> list[TestExecution]:
        """Return all test executions for a given run (``TestExecution.filter``).

        Args:
            run_id: Run identifier.

        Returns:
            List of :class:`TestExecution` objects.

        Raises:
            KeyError: If the run is not found.
        """
        self._simulate_latency()
        self._log(f"TestExecution.filter(run={run_id!r})")

        run = self.get_test_run(run_id)
        self._log(f"  -> {len(run.executions)} execution(s) found")
        return list(run.executions)

    def get_run_summary(self, run_id: str) -> dict[str, Any]:
        """Return a summary dict with pass/fail/total counts and pass rate.

        Args:
            run_id: Run identifier.

        Returns:
            Dict with keys: ``run_id``, ``summary``, ``total``, ``passed``,
            ``failed``, ``blocked``, ``idle``, ``pass_rate``, ``all_passed``.

        Raises:
            KeyError: If the run is not found.
        """
        self._simulate_latency()
        self._log(f"TestRun.get_summary(run_id={run_id!r})")

        run = self.get_test_run(run_id)
        blocked = sum(1 for e in run.executions if e.status == TestStatus.BLOCKED)
        idle = sum(1 for e in run.executions if e.status == TestStatus.IDLE)

        result: dict[str, Any] = {
            "run_id": run_id,
            "summary": run.summary,
            "total": run.total_count,
            "passed": run.pass_count,
            "failed": run.fail_count,
            "blocked": blocked,
            "idle": idle,
            "pass_rate": round(run.pass_rate * 100, 1),
            "plane_issue_keys": run.plane_issue_keys,
            "version": run.version,
        }
        result["all_passed"] = result["failed"] == 0 and result["total"] > 0
        self._log(
            f"  -> Summary: {result['passed']}/{result['total']} passed "
            f"({result['pass_rate']}%)"
        )
        return result

    def run_all_tests_decoy(
        self,
        run_id: str,
        pass_rate: float = 1.0,
    ) -> list[TestExecution]:
        """Execute all test cases in a run with a configurable pass rate.

        Args:
            run_id: The run whose test cases should be executed.
            pass_rate: Fraction of tests that should PASS (0.0–1.0).

        Returns:
            List of :class:`TestExecution` objects, one per test case.

        Raises:
            KeyError: If the run is not found.
        """
        self._simulate_latency()
        self._log(
            f"run_all_tests_decoy: run={run_id!r}, pass_rate={pass_rate:.0%}"
        )
        run = self.get_test_run(run_id)

        if not run.test_case_keys:
            self._log("  No test cases in run — nothing to execute.")
            return []

        n = len(run.test_case_keys)
        pass_count = round(n * pass_rate)
        executions: list[TestExecution] = []

        for i, tc_key in enumerate(run.test_case_keys):
            status = TestStatus.PASSED if i < pass_count else TestStatus.FAILED
            comment = (
                "Automated execution: PASSED."
                if status == TestStatus.PASSED
                else "Automated execution: FAILED — assertion error."
            )
            execution = self.record_test_execution(
                run_id=run_id,
                test_case_key=tc_key,
                status=status,
                comment=comment,
                tested_by="decoy-runner",
            )
            executions.append(execution)

        self._log(
            f"  -> Executed {n} test(s): "
            f"{pass_count} PASSED, {n - pass_count} FAILED"
        )
        return executions

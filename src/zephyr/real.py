"""Real Zephyr Scale client — makes actual HTTP calls to the Zephyr Scale Cloud API v2.

Authentication uses Bearer token auth.
See: https://support.smartbear.com/zephyr-scale-cloud/api-docs/
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from src.exceptions import APIError, AuthenticationError, NotFoundError
from .base import BaseZephyrClient
from .models import TestCase, TestCycle, TestResult, TestStatus

_ZEPHYR_API_BASE = "https://api.zephyrscale.smartbear.com/v2"


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_datetime(s: str | None) -> datetime:
    """Parse an ISO-8601 datetime string to a timezone-aware datetime."""
    if not s:
        return _now()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return _now()


def _parse_status(status_obj: dict | str | None) -> TestStatus:
    """Map a Zephyr Scale status name to a :class:`TestStatus`."""
    if isinstance(status_obj, dict):
        name = status_obj.get("name", "NOT_EXECUTED")
    elif isinstance(status_obj, str):
        name = status_obj
    else:
        name = "NOT_EXECUTED"

    mapping = {
        "Pass": TestStatus.PASS,
        "PASS": TestStatus.PASS,
        "Fail": TestStatus.FAIL,
        "FAIL": TestStatus.FAIL,
        "Blocked": TestStatus.BLOCKED,
        "BLOCKED": TestStatus.BLOCKED,
        "In Progress": TestStatus.IN_PROGRESS,
        "IN_PROGRESS": TestStatus.IN_PROGRESS,
    }
    return mapping.get(name, TestStatus.NOT_EXECUTED)


def _parse_test_cycle(data: dict) -> TestCycle:
    """Map a Zephyr Scale API test cycle dict to a :class:`TestCycle`."""
    return TestCycle(
        id=data.get("key", data.get("id", "")),
        name=data.get("name", ""),
        project_key=data.get("projectKey", ""),
        version=data.get("version", "Unversioned"),
        jira_issue_keys=data.get("jiraIssueKeys", []),
        status=data.get("status", {}).get("name", "Active") if isinstance(data.get("status"), dict) else "Active",
        created=_parse_datetime(data.get("createdOn")),
        updated=_parse_datetime(data.get("updatedOn")),
        created_by=data.get("createdBy", "automation"),
    )


def _parse_test_result(data: dict) -> TestResult:
    """Map a Zephyr Scale API test execution dict to a :class:`TestResult`."""
    tc_obj = data.get("testCase", {})
    tc_key = tc_obj.get("key", "") if isinstance(tc_obj, dict) else str(tc_obj)

    cycle_obj = data.get("testCycle", {})
    cycle_id = cycle_obj.get("key", "") if isinstance(cycle_obj, dict) else str(cycle_obj)

    status_obj = data.get("testExecutionStatus") or data.get("status")
    status = _parse_status(status_obj)

    return TestResult(
        id=str(data.get("id", uuid.uuid4().hex[:8].upper())),
        test_case_key=tc_key,
        test_name=data.get("testCase", {}).get("name", tc_key) if isinstance(data.get("testCase"), dict) else tc_key,
        status=status,
        cycle_id=cycle_id,
        comment=data.get("comment", ""),
        executed_by=data.get("executedById", "automation"),
        executed_at=_parse_datetime(data.get("actualEndDate") or data.get("executionDate")),
        duration_ms=data.get("executionTime", 0) or 0,
    )


class RealZephyrClient(BaseZephyrClient):
    """Real Zephyr Scale client that calls the Zephyr Scale Cloud API v2.

    Args:
        api_token: Zephyr Scale API token (Bearer auth).
        project_key: Default JIRA/Zephyr project key.
        base_url: Zephyr Scale API base URL (override for testing).
        verify_ssl: Set to ``False`` to skip TLS verification.
    """

    def __init__(
        self,
        api_token: str,
        project_key: str = "DEMO",
        base_url: str = _ZEPHYR_API_BASE,
        verify_ssl: bool = True,
        **kwargs,
    ) -> None:
        self.api_token = api_token
        self.project_key = project_key
        self.base_url = base_url.rstrip("/")
        self.use_decoy = False

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        self._session.verify = verify_ssl

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _api(self, method: str, path: str, **kwargs: Any) -> dict:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.request(method, url, **kwargs)
        except requests.ConnectionError as exc:
            raise APIError(f"Connection failed to {url}: {exc}") from exc

        if resp.status_code == 401:
            raise AuthenticationError(
                "Zephyr Scale authentication failed — check api_token."
            )
        if resp.status_code == 404:
            raise NotFoundError(f"Zephyr Scale resource not found: {path}")

        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise APIError(
                str(exc), status_code=resp.status_code, response_body=resp.text
            ) from exc

        return resp.json() if resp.content else {}

    def _log(self, message: str) -> None:
        print(f"[ZEPHYR REAL] {message}")

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
        """Create a new Zephyr Scale test cycle."""
        pk = project_key or self.project_key
        self._log(f"POST /testcycles  name={name!r}  project={pk!r}")

        payload: dict[str, Any] = {"name": name, "projectKey": pk}
        if version and version != "Unversioned":
            payload["version"] = version
        if jira_issue_keys:
            payload["jiraIssueKeys"] = jira_issue_keys

        data = self._api("POST", "/testcycles", json=payload)
        cycle = _parse_test_cycle(data)
        self._log(f"  -> Created {cycle!r}")
        return cycle

    def get_test_cycle(self, cycle_id: str) -> TestCycle:
        """Fetch an existing test cycle by key."""
        self._log(f"GET /testcycles/{cycle_id}")
        data = self._api("GET", f"/testcycles/{cycle_id}")
        cycle = _parse_test_cycle(data)
        self._log(f"  -> Returning {cycle!r}")
        return cycle

    def add_test_cases(self, cycle_id: str, test_case_keys: list[str]) -> TestCycle:
        """Add test cases to an existing test cycle."""
        self._log(f"POST /testcycles/{cycle_id}/testcases  keys={test_case_keys}")
        payload = {"testCaseKeys": test_case_keys}
        self._api("POST", f"/testcycles/{cycle_id}/testcases", json=payload)
        # Fetch updated cycle
        cycle = self.get_test_cycle(cycle_id)
        # Merge keys locally (API may not return them in the cycle response)
        for key in test_case_keys:
            if key not in cycle.test_case_keys:
                cycle.test_case_keys.append(key)
        self._log(f"  -> Added {len(test_case_keys)} test case(s) to {cycle_id}")
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
        """Record a test execution in Zephyr Scale."""
        if isinstance(status, TestStatus):
            status_name = status.value.capitalize()
        else:
            status_name = str(status).capitalize()

        self._log(
            f"POST /testexecutions  cycle={cycle_id}  tc={test_case_key}  status={status_name}"
        )

        payload: dict[str, Any] = {
            "projectKey": self.project_key,
            "testCycleKey": cycle_id,
            "testCaseKey": test_case_key,
            "statusName": status_name,
            "comment": comment,
        }
        if duration_ms is not None:
            payload["executionTime"] = duration_ms

        data = self._api("POST", "/testexecutions", json=payload)
        result = _parse_test_result(data)
        self._log(f"  -> Recorded {result!r}")
        return result

    def get_test_results(self, cycle_id: str) -> list[TestResult]:
        """Return all test results for a given cycle."""
        self._log(f"GET /testexecutions?testCycle={cycle_id}")
        data = self._api(
            "GET", "/testexecutions",
            params={"testCycle": cycle_id, "maxResults": 100}
        )
        items = data.get("values", data.get("results", []))
        results = [_parse_test_result(item) for item in items]
        self._log(f"  -> {len(results)} result(s) found")
        return results

    def get_cycle_summary(self, cycle_id: str) -> dict[str, Any]:
        """Return a summary dict with pass/fail/total counts and pass rate."""
        self._log(f"get_cycle_summary: fetching results for {cycle_id}")
        results = self.get_test_results(cycle_id)
        cycle = self.get_test_cycle(cycle_id)

        passed = sum(1 for r in results if r.status == TestStatus.PASS)
        failed = sum(1 for r in results if r.status == TestStatus.FAIL)
        blocked = sum(1 for r in results if r.status == TestStatus.BLOCKED)
        not_exec = sum(1 for r in results if r.status == TestStatus.NOT_EXECUTED)
        total = len(results)
        pass_rate = round((passed / total * 100) if total else 0, 1)

        summary: dict[str, Any] = {
            "cycle_id": cycle_id,
            "name": cycle.name,
            "total": total,
            "passed": passed,
            "failed": failed,
            "blocked": blocked,
            "not_executed": not_exec,
            "pass_rate": pass_rate,
            "jira_issue_keys": cycle.jira_issue_keys,
            "version": cycle.version,
        }
        summary["all_passed"] = failed == 0 and total > 0
        return summary

    def run_test_suite(
        self,
        cycle_id: str,
        pass_rate: float = 1.0,
    ) -> list[TestResult]:
        """Return existing test results from the API (pass_rate is ignored in real mode).

        In real mode, tests are assumed to have been executed externally.
        This method fetches and returns the current results.

        Args:
            cycle_id: The cycle whose results to retrieve.
            pass_rate: Ignored in real mode.

        Returns:
            List of :class:`TestResult` objects.
        """
        self._log(f"run_test_suite: fetching existing results for {cycle_id}")
        return self.get_test_results(cycle_id)

"""Tests for the real Zephyr Scale client (HTTP calls mocked with responses library)."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import responses as resp_lib
from src.zephyr.real import RealZephyrClient, _ZEPHYR_API_BASE
from src.zephyr.models import TestCycle, TestResult, TestStatus
from src.exceptions import NotFoundError, AuthenticationError

BASE = _ZEPHYR_API_BASE


@pytest.fixture
def client():
    return RealZephyrClient(api_token="test-token", project_key="TEST")


def _cycle_response(key="CYC-0001", name="My Cycle"):
    return {
        "key": key,
        "name": name,
        "projectKey": "TEST",
        "version": "Unversioned",
        "status": {"name": "Active"},
        "jiraIssueKeys": [],
        "createdOn": "2024-01-15T10:00:00.000Z",
        "updatedOn": "2024-01-15T10:00:00.000Z",
        "createdBy": "automation",
    }


def _execution_response(id="EX-1", tc_key="TC-001", cycle_key="CYC-0001", status="Pass"):
    return {
        "id": id,
        "testCase": {"key": tc_key, "name": f"Test {tc_key}"},
        "testCycle": {"key": cycle_key},
        "testExecutionStatus": {"name": status},
        "comment": "Automated",
        "executedById": "automation",
        "actualEndDate": "2024-01-15T11:00:00.000Z",
        "executionTime": 1500,
    }


@resp_lib.activate
def test_create_test_cycle(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/testcycles",
        json=_cycle_response(), status=200
    )
    cycle = client.create_test_cycle(name="My Cycle")
    assert isinstance(cycle, TestCycle)
    assert cycle.name == "My Cycle"
    assert cycle.id == "CYC-0001"


@resp_lib.activate
def test_create_test_cycle_auth_error(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/testcycles",
        json={}, status=401
    )
    with pytest.raises(AuthenticationError):
        client.create_test_cycle(name="My Cycle")


@resp_lib.activate
def test_get_test_cycle(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/testcycles/CYC-0001",
        json=_cycle_response(), status=200
    )
    cycle = client.get_test_cycle("CYC-0001")
    assert isinstance(cycle, TestCycle)
    assert cycle.id == "CYC-0001"


@resp_lib.activate
def test_get_test_cycle_not_found(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/testcycles/CYC-9999",
        json={"message": "Not found"}, status=404
    )
    with pytest.raises(NotFoundError):
        client.get_test_cycle("CYC-9999")


@resp_lib.activate
def test_add_test_cases(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/testcycles/CYC-0001/testcases",
        json={}, status=200
    )
    resp_lib.add(
        resp_lib.GET, f"{BASE}/testcycles/CYC-0001",
        json=_cycle_response(), status=200
    )
    cycle = client.add_test_cases("CYC-0001", ["TC-001", "TC-002"])
    assert isinstance(cycle, TestCycle)
    # Keys are merged locally
    assert "TC-001" in cycle.test_case_keys
    assert "TC-002" in cycle.test_case_keys


@resp_lib.activate
def test_execute_test(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/testexecutions",
        json=_execution_response(), status=200
    )
    result = client.execute_test(
        cycle_id="CYC-0001",
        test_case_key="TC-001",
        status=TestStatus.PASS,
        comment="Looks good",
    )
    assert isinstance(result, TestResult)
    assert result.status == TestStatus.PASS
    assert result.test_case_key == "TC-001"


@resp_lib.activate
def test_execute_test_auth_error(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/testexecutions",
        json={}, status=401
    )
    with pytest.raises(AuthenticationError):
        client.execute_test("CYC-0001", "TC-001", TestStatus.PASS)


@resp_lib.activate
def test_get_test_results(client):
    results_resp = {
        "values": [
            _execution_response("EX-1", "TC-001", "CYC-0001", "Pass"),
            _execution_response("EX-2", "TC-002", "CYC-0001", "Fail"),
        ]
    }
    resp_lib.add(
        resp_lib.GET, f"{BASE}/testexecutions",
        json=results_resp, status=200
    )
    results = client.get_test_results("CYC-0001")
    assert len(results) == 2
    assert all(isinstance(r, TestResult) for r in results)
    statuses = {r.status for r in results}
    assert TestStatus.PASS in statuses
    assert TestStatus.FAIL in statuses


@resp_lib.activate
def test_get_test_results_not_found(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/testexecutions",
        json={"message": "Not found"}, status=404
    )
    with pytest.raises(NotFoundError):
        client.get_test_results("CYC-9999")


@resp_lib.activate
def test_run_test_suite_returns_results(client):
    """In real mode, run_test_suite fetches existing results."""
    results_resp = {
        "values": [
            _execution_response("EX-1", "TC-001", "CYC-0001", "Pass"),
        ]
    }
    resp_lib.add(
        resp_lib.GET, f"{BASE}/testexecutions",
        json=results_resp, status=200
    )
    results = client.run_test_suite("CYC-0001", pass_rate=1.0)
    assert isinstance(results, list)
    assert len(results) == 1

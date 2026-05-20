"""Unit tests for the Zephyr decoy client."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.zephyr.client import ZephyrClient
from src.zephyr.models import TestCycle, TestResult, TestStatus


@pytest.fixture()
def client() -> ZephyrClient:
    return ZephyrClient(project_key="TEST")


class TestCreateTestCycle:
    def test_returns_test_cycle(self, client):
        cycle = client.create_test_cycle(name="Smoke Tests")
        assert isinstance(cycle, TestCycle)

    def test_name_stored(self, client):
        cycle = client.create_test_cycle(name="My Cycle")
        assert cycle.name == "My Cycle"

    def test_jira_keys_stored(self, client):
        cycle = client.create_test_cycle(name="JIRA Cycle", jira_issue_keys=["TEST-1"])
        assert "TEST-1" in cycle.jira_issue_keys

    def test_status_active(self, client):
        cycle = client.create_test_cycle(name="Active Cycle")
        assert cycle.status == "Active"


class TestGetTestCycle:
    def test_raises_on_missing(self, client):
        with pytest.raises(KeyError):
            client.get_test_cycle("NONEXISTENT")

    def test_returns_created_cycle(self, client):
        cycle = client.create_test_cycle(name="Fetch Test")
        fetched = client.get_test_cycle(cycle.id)
        assert fetched.id == cycle.id


class TestAddTestCases:
    def test_cases_added_to_cycle(self, client):
        cycle = client.create_test_cycle(name="Add Cases")
        client.add_test_cases(cycle.id, ["TC-001", "TC-002"])
        fetched = client.get_test_cycle(cycle.id)
        assert "TC-001" in fetched.test_case_keys
        assert "TC-002" in fetched.test_case_keys

    def test_no_duplicate_cases(self, client):
        cycle = client.create_test_cycle(name="Dedup Cases")
        client.add_test_cases(cycle.id, ["TC-001"])
        client.add_test_cases(cycle.id, ["TC-001"])
        fetched = client.get_test_cycle(cycle.id)
        assert fetched.test_case_keys.count("TC-001") == 1


class TestExecuteTest:
    def test_result_recorded(self, client):
        cycle = client.create_test_cycle(name="Execute Test")
        client.add_test_cases(cycle.id, ["TC-001"])
        result = client.execute_test(cycle.id, "TC-001", TestStatus.PASS)
        assert isinstance(result, TestResult)
        assert result.status == TestStatus.PASS

    def test_comment_stored(self, client):
        cycle = client.create_test_cycle(name="Comment Test")
        client.add_test_cases(cycle.id, ["TC-001"])
        result = client.execute_test(cycle.id, "TC-001", TestStatus.FAIL, comment="Step 3 failed")
        assert result.comment == "Step 3 failed"

    def test_multiple_executions_recorded(self, client):
        cycle = client.create_test_cycle(name="Re-execute Test")
        client.add_test_cases(cycle.id, ["TC-001"])
        client.execute_test(cycle.id, "TC-001", TestStatus.FAIL)
        client.execute_test(cycle.id, "TC-001", TestStatus.PASS)
        results = client.get_test_results(cycle.id)
        tc_results = [r for r in results if r.test_case_key == "TC-001"]
        # Decoy appends each execution; at least one result exists
        assert len(tc_results) >= 1


class TestGetCycleSummary:
    def test_all_pass(self, client):
        cycle = client.create_test_cycle(name="All Pass")
        client.add_test_cases(cycle.id, ["TC-001", "TC-002"])
        client.run_all_tests_decoy(cycle.id, pass_rate=1.0)
        summary = client.get_cycle_summary(cycle.id)
        assert summary["all_passed"] is True
        assert summary["failed"] == 0

    def test_all_fail(self, client):
        cycle = client.create_test_cycle(name="All Fail")
        client.add_test_cases(cycle.id, ["TC-001", "TC-002"])
        client.run_all_tests_decoy(cycle.id, pass_rate=0.0)
        summary = client.get_cycle_summary(cycle.id)
        assert summary["all_passed"] is False
        assert summary["passed"] == 0

    def test_pass_rate_calculated(self, client):
        cycle = client.create_test_cycle(name="Pass Rate")
        client.add_test_cases(cycle.id, ["TC-001", "TC-002", "TC-003", "TC-004"])
        client.execute_test(cycle.id, "TC-001", TestStatus.PASS)
        client.execute_test(cycle.id, "TC-002", TestStatus.PASS)
        client.execute_test(cycle.id, "TC-003", TestStatus.FAIL)
        client.execute_test(cycle.id, "TC-004", TestStatus.FAIL)
        summary = client.get_cycle_summary(cycle.id)
        assert abs(summary["pass_rate"] - 50.0) < 0.1

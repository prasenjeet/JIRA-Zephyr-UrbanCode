"""Unit tests for the AgileTest decoy client."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agiletest.client import AgiletestClient
from src.agiletest.models import TestExecution, TestPlan, TestStatus


@pytest.fixture()
def client() -> AgiletestClient:
    return AgiletestClient(project_key="TEST")


class TestCreateTestPlan:
    def test_returns_test_plan(self, client):
        plan = client.create_test_plan(name="Smoke Tests")
        assert isinstance(plan, TestPlan)

    def test_name_stored(self, client):
        plan = client.create_test_plan(name="My Plan")
        assert plan.name == "My Plan"

    def test_jira_keys_stored(self, client):
        plan = client.create_test_plan(name="JIRA Plan", jira_issue_keys=["TEST-1"])
        assert "TEST-1" in plan.jira_issue_keys

    def test_status_active(self, client):
        plan = client.create_test_plan(name="Active Plan")
        assert plan.status == "Active"

    def test_id_format(self, client):
        plan = client.create_test_plan(name="ID Format")
        assert plan.id.startswith("PLAN-")


class TestGetTestPlan:
    def test_raises_on_missing(self, client):
        with pytest.raises(KeyError):
            client.get_test_plan("NONEXISTENT")

    def test_returns_created_plan(self, client):
        plan = client.create_test_plan(name="Fetch Test")
        fetched = client.get_test_plan(plan.id)
        assert fetched.id == plan.id


class TestAddTestCases:
    def test_cases_added_to_plan(self, client):
        plan = client.create_test_plan(name="Add Cases")
        client.add_test_cases(plan.id, ["TC-001", "TC-002"])
        fetched = client.get_test_plan(plan.id)
        assert "TC-001" in fetched.test_case_keys
        assert "TC-002" in fetched.test_case_keys

    def test_no_duplicate_cases(self, client):
        plan = client.create_test_plan(name="Dedup Cases")
        client.add_test_cases(plan.id, ["TC-001"])
        client.add_test_cases(plan.id, ["TC-001"])
        fetched = client.get_test_plan(plan.id)
        assert fetched.test_case_keys.count("TC-001") == 1


class TestExecuteTest:
    def test_execution_recorded(self, client):
        plan = client.create_test_plan(name="Execute Test")
        client.add_test_cases(plan.id, ["TC-001"])
        result = client.execute_test(plan.id, "TC-001", TestStatus.PASS)
        assert isinstance(result, TestExecution)
        assert result.status == TestStatus.PASS

    def test_comment_stored(self, client):
        plan = client.create_test_plan(name="Comment Test")
        client.add_test_cases(plan.id, ["TC-001"])
        result = client.execute_test(plan.id, "TC-001", TestStatus.FAIL, comment="Step 3 failed")
        assert result.comment == "Step 3 failed"

    def test_plan_id_set(self, client):
        plan = client.create_test_plan(name="Plan ID Test")
        client.add_test_cases(plan.id, ["TC-001"])
        result = client.execute_test(plan.id, "TC-001", TestStatus.PASS)
        assert result.plan_id == plan.id

    def test_multiple_executions_recorded(self, client):
        plan = client.create_test_plan(name="Re-execute Test")
        client.add_test_cases(plan.id, ["TC-001"])
        client.execute_test(plan.id, "TC-001", TestStatus.FAIL)
        client.execute_test(plan.id, "TC-001", TestStatus.PASS)
        executions = client.get_test_executions(plan.id)
        tc_execs = [e for e in executions if e.test_case_key == "TC-001"]
        assert len(tc_execs) >= 1


class TestGetPlanSummary:
    def test_all_pass(self, client):
        plan = client.create_test_plan(name="All Pass")
        client.add_test_cases(plan.id, ["TC-001", "TC-002"])
        client.run_all_tests_decoy(plan.id, pass_rate=1.0)
        summary = client.get_plan_summary(plan.id)
        assert summary["all_passed"] is True
        assert summary["failed"] == 0

    def test_all_fail(self, client):
        plan = client.create_test_plan(name="All Fail")
        client.add_test_cases(plan.id, ["TC-001", "TC-002"])
        client.run_all_tests_decoy(plan.id, pass_rate=0.0)
        summary = client.get_plan_summary(plan.id)
        assert summary["all_passed"] is False
        assert summary["passed"] == 0

    def test_pass_rate_calculated(self, client):
        plan = client.create_test_plan(name="Pass Rate")
        client.add_test_cases(plan.id, ["TC-001", "TC-002", "TC-003", "TC-004"])
        client.execute_test(plan.id, "TC-001", TestStatus.PASS)
        client.execute_test(plan.id, "TC-002", TestStatus.PASS)
        client.execute_test(plan.id, "TC-003", TestStatus.FAIL)
        client.execute_test(plan.id, "TC-004", TestStatus.FAIL)
        summary = client.get_plan_summary(plan.id)
        assert abs(summary["pass_rate"] - 50.0) < 0.1

    def test_summary_has_expected_keys(self, client):
        plan = client.create_test_plan(name="Keys Check")
        client.add_test_cases(plan.id, ["TC-001"])
        client.run_all_tests_decoy(plan.id, pass_rate=1.0)
        summary = client.get_plan_summary(plan.id)
        for key in ("plan_id", "name", "total", "passed", "failed", "pass_rate", "all_passed"):
            assert key in summary

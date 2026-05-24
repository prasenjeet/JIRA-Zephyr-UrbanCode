"""Unit tests for the Kiwi TCMS decoy client."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.kiwi.client import KiwiTCMSClient
from src.kiwi.models import TestExecution, TestRun, TestStatus


@pytest.fixture()
def client() -> KiwiTCMSClient:
    return KiwiTCMSClient(product="TestProduct")


class TestCreateTestRun:
    def test_returns_test_run(self, client):
        run = client.create_test_run(summary="Smoke Tests")
        assert isinstance(run, TestRun)

    def test_summary_stored(self, client):
        run = client.create_test_run(summary="My Run")
        assert run.summary == "My Run"

    def test_plane_issue_keys_stored(self, client):
        run = client.create_test_run(summary="Issue Run", plane_issue_keys=["TEST-1"])
        assert "TEST-1" in run.plane_issue_keys

    def test_status_running(self, client):
        run = client.create_test_run(summary="Active Run")
        assert run.status == "RUNNING"

    def test_id_uses_run_prefix(self, client):
        run = client.create_test_run(summary="ID Test")
        assert run.id.startswith("RUN-")


class TestGetTestRun:
    def test_raises_on_missing(self, client):
        with pytest.raises(KeyError):
            client.get_test_run("RUN-9999")

    def test_returns_created_run(self, client):
        run = client.create_test_run(summary="Fetch Test")
        fetched = client.get_test_run(run.id)
        assert fetched.id == run.id


class TestAddTestCases:
    def test_cases_added_to_run(self, client):
        run = client.create_test_run(summary="Add Cases")
        client.add_test_cases(run.id, ["TC-001", "TC-002"])
        fetched = client.get_test_run(run.id)
        assert "TC-001" in fetched.test_case_keys
        assert "TC-002" in fetched.test_case_keys

    def test_no_duplicate_cases(self, client):
        run = client.create_test_run(summary="Dedup Cases")
        client.add_test_cases(run.id, ["TC-001"])
        client.add_test_cases(run.id, ["TC-001"])
        fetched = client.get_test_run(run.id)
        assert fetched.test_case_keys.count("TC-001") == 1


class TestRecordTestExecution:
    def test_execution_recorded(self, client):
        run = client.create_test_run(summary="Execute Test")
        client.add_test_cases(run.id, ["TC-001"])
        result = client.record_test_execution(run.id, "TC-001", TestStatus.PASSED)
        assert isinstance(result, TestExecution)
        assert result.status == TestStatus.PASSED

    def test_comment_stored(self, client):
        run = client.create_test_run(summary="Comment Test")
        client.add_test_cases(run.id, ["TC-001"])
        result = client.record_test_execution(
            run.id, "TC-001", TestStatus.FAILED, comment="Step 3 failed"
        )
        assert result.comment == "Step 3 failed"

    def test_string_status_accepted(self, client):
        run = client.create_test_run(summary="String Status Test")
        client.add_test_cases(run.id, ["TC-001"])
        result = client.record_test_execution(run.id, "TC-001", "PASSED")
        assert result.status == TestStatus.PASSED

    def test_multiple_executions_recorded(self, client):
        run = client.create_test_run(summary="Re-execute Test")
        client.add_test_cases(run.id, ["TC-001"])
        client.record_test_execution(run.id, "TC-001", TestStatus.FAILED)
        client.record_test_execution(run.id, "TC-001", TestStatus.PASSED)
        executions = client.get_test_executions(run.id)
        tc_execs = [e for e in executions if e.test_case_key == "TC-001"]
        assert len(tc_execs) >= 1

    def test_to_dict_has_required_keys(self, client):
        run = client.create_test_run(summary="Dict Test")
        client.add_test_cases(run.id, ["TC-001"])
        result = client.record_test_execution(run.id, "TC-001", TestStatus.PASSED)
        d = result.to_dict()
        assert "test_case_key" in d
        assert "test_name" in d
        assert "status" in d
        assert "comment" in d
        assert "executed_by" in d


class TestGetRunSummary:
    def test_all_pass(self, client):
        run = client.create_test_run(summary="All Pass")
        client.add_test_cases(run.id, ["TC-001", "TC-002"])
        client.run_all_tests_decoy(run.id, pass_rate=1.0)
        summary = client.get_run_summary(run.id)
        assert summary["all_passed"] is True
        assert summary["failed"] == 0

    def test_all_fail(self, client):
        run = client.create_test_run(summary="All Fail")
        client.add_test_cases(run.id, ["TC-001", "TC-002"])
        client.run_all_tests_decoy(run.id, pass_rate=0.0)
        summary = client.get_run_summary(run.id)
        assert summary["all_passed"] is False
        assert summary["passed"] == 0

    def test_pass_rate_calculated(self, client):
        run = client.create_test_run(summary="Pass Rate")
        client.add_test_cases(run.id, ["TC-001", "TC-002", "TC-003", "TC-004"])
        client.record_test_execution(run.id, "TC-001", TestStatus.PASSED)
        client.record_test_execution(run.id, "TC-002", TestStatus.PASSED)
        client.record_test_execution(run.id, "TC-003", TestStatus.FAILED)
        client.record_test_execution(run.id, "TC-004", TestStatus.FAILED)
        summary = client.get_run_summary(run.id)
        assert abs(summary["pass_rate"] - 50.0) < 0.1

    def test_summary_has_run_id(self, client):
        run = client.create_test_run(summary="Run ID Test")
        client.add_test_cases(run.id, ["TC-001"])
        client.run_all_tests_decoy(run.id, pass_rate=1.0)
        summary = client.get_run_summary(run.id)
        assert summary["run_id"] == run.id

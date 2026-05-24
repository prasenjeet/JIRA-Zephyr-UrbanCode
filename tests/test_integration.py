"""Integration tests for the full pipeline."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.plane.client import PlaneClient
from src.kiwi.client import KiwiTCMSClient
from src.wikijs.client import WikiJsClient
from src.harness.client import HarnessClient
from src.integration.pipeline import IntegrationPipeline
from src.harness.models import ExecutionStatus


@pytest.fixture()
def pipeline_passing() -> IntegrationPipeline:
    return IntegrationPipeline(
        plane=PlaneClient(project_identifier="INT"),
        kiwi=KiwiTCMSClient(product="IntProduct"),
        wikijs=WikiJsClient(base_url="https://wiki.test.com"),
        harness=HarnessClient(project="IntProject", environment="Staging"),
        version="3.0.0",
    )


@pytest.fixture()
def pipeline_failing() -> IntegrationPipeline:
    return IntegrationPipeline(
        plane=PlaneClient(project_identifier="INT"),
        kiwi=KiwiTCMSClient(product="IntProduct"),
        wikijs=WikiJsClient(base_url="https://wiki.test.com"),
        harness=HarnessClient(project="IntProject", environment="Staging"),
        version="3.0.0",
    )


class TestRunQaPipelineSuccess:
    def test_returns_result_dict(self, pipeline_passing):
        result = pipeline_passing.run_qa_pipeline("INT-1", pass_rate=1.0)
        assert isinstance(result, dict)

    def test_final_status_deployed(self, pipeline_passing):
        result = pipeline_passing.run_qa_pipeline("INT-10", pass_rate=1.0)
        assert result["final_status"] == "Deployed"

    def test_all_tests_passed_true(self, pipeline_passing):
        result = pipeline_passing.run_qa_pipeline("INT-11", pass_rate=1.0)
        assert result["all_tests_passed"] is True

    def test_deployment_succeeded(self, pipeline_passing):
        result = pipeline_passing.run_qa_pipeline("INT-12", pass_rate=1.0)
        assert result["deployment"] is not None
        assert result["deployment"].status == ExecutionStatus.SUCCESS

    def test_plane_issue_transitioned_to_deployed(self, pipeline_passing):
        result = pipeline_passing.run_qa_pipeline("INT-13", pass_rate=1.0)
        issue = pipeline_passing.plane.get_issue("INT-13")
        assert issue.state == "Deployed"

    def test_wikijs_page_created(self, pipeline_passing):
        result = pipeline_passing.run_qa_pipeline("INT-14", pass_rate=1.0)
        page = result["report_page"]
        assert page is not None
        assert "INT-14" in page.title

    def test_test_run_linked_to_issue(self, pipeline_passing):
        result = pipeline_passing.run_qa_pipeline("INT-15", pass_rate=1.0)
        issue = pipeline_passing.plane.get_issue("INT-15")
        assert result["test_run"].id in issue.linked_runs


class TestRunQaPipelineFailure:
    def test_final_status_in_dev(self, pipeline_failing):
        result = pipeline_failing.run_qa_pipeline("INT-20", pass_rate=0.0)
        assert result["final_status"] == "In Dev"

    def test_all_tests_passed_false(self, pipeline_failing):
        result = pipeline_failing.run_qa_pipeline("INT-21", pass_rate=0.0)
        assert result["all_tests_passed"] is False

    def test_no_deployment_triggered(self, pipeline_failing):
        result = pipeline_failing.run_qa_pipeline("INT-22", pass_rate=0.0)
        assert result["deployment"] is None

    def test_plane_issue_returned_to_in_dev(self, pipeline_failing):
        result = pipeline_failing.run_qa_pipeline("INT-23", pass_rate=0.0)
        issue = pipeline_failing.plane.get_issue("INT-23")
        assert issue.state == "In Dev"

    def test_failure_comment_added(self, pipeline_failing):
        result = pipeline_failing.run_qa_pipeline("INT-24", pass_rate=0.0)
        issue = pipeline_failing.plane.get_issue("INT-24")
        failure_comments = [c for c in issue.comments if "FAILED" in c.body]
        assert len(failure_comments) >= 1

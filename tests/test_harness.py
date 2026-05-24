"""Unit tests for the Harness CD decoy client."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.harness.client import HarnessClient
from src.harness.models import ArtifactBundle, ExecutionStatus, PipelineExecution


@pytest.fixture()
def client() -> HarnessClient:
    return HarnessClient(project="TestProject", environment="Staging")


@pytest.fixture()
def client_failing() -> HarnessClient:
    return HarnessClient(
        project="TestProject", environment="Staging", simulate_failure=True
    )


class TestCreateArtifactBundle:
    def test_returns_bundle(self, client):
        bundle = client.create_artifact_bundle(name="v1.0.0")
        assert isinstance(bundle, ArtifactBundle)

    def test_name_stored(self, client):
        bundle = client.create_artifact_bundle(name="release-1.2.3")
        assert bundle.name == "release-1.2.3"

    def test_artifacts_populated(self, client):
        bundle = client.create_artifact_bundle(name="default-artifacts")
        assert len(bundle.artifacts) > 0

    def test_project_defaults_to_client_project(self, client):
        bundle = client.create_artifact_bundle(name="proj-test")
        assert bundle.project == "TestProject"

    def test_environment_override(self, client):
        bundle = client.create_artifact_bundle(name="env-bundle", environment="QA")
        assert bundle.environment == "QA"


class TestExecutePipeline:
    def test_returns_pipeline_execution(self, client):
        bundle = client.create_artifact_bundle(name="deploy-bundle")
        exec_ = client.execute_pipeline(artifact_bundle=bundle)
        assert isinstance(exec_, PipelineExecution)

    def test_initial_status_queued(self, client):
        bundle = client.create_artifact_bundle(name="queued-bundle")
        exec_ = client.execute_pipeline(artifact_bundle=bundle)
        assert exec_.status == ExecutionStatus.QUEUED

    def test_log_url_set(self, client):
        bundle = client.create_artifact_bundle(name="log-bundle")
        exec_ = client.execute_pipeline(artifact_bundle=bundle)
        assert exec_.id in exec_.log_url

    def test_auto_creates_bundle_when_none(self, client):
        exec_ = client.execute_pipeline()
        assert isinstance(exec_, PipelineExecution)
        assert exec_.artifact_bundle is not None


class TestGetExecutionStatus:
    def test_advances_from_queued_to_running(self, client):
        bundle = client.create_artifact_bundle(name="status-bundle")
        exec_ = client.execute_pipeline(artifact_bundle=bundle)
        status = client.get_execution_status(exec_.id)
        assert status == ExecutionStatus.RUNNING

    def test_advances_from_running_to_success(self, client):
        bundle = client.create_artifact_bundle(name="succeed-bundle")
        exec_ = client.execute_pipeline(artifact_bundle=bundle)
        client.get_execution_status(exec_.id)  # QUEUED → RUNNING
        status = client.get_execution_status(exec_.id)  # RUNNING → SUCCESS
        assert status == ExecutionStatus.SUCCESS

    def test_raises_on_unknown_id(self, client):
        with pytest.raises(KeyError):
            client.get_execution_status("NONEXISTENT")


class TestWaitForExecution:
    def test_succeeds_by_default(self, client):
        bundle = client.create_artifact_bundle(name="success-bundle")
        exec_ = client.execute_pipeline(artifact_bundle=bundle)
        final_status = client.wait_for_execution(exec_.id)
        assert final_status == ExecutionStatus.SUCCESS

    def test_fails_when_simulate_failure(self, client_failing):
        bundle = client_failing.create_artifact_bundle(name="fail-bundle")
        exec_ = client_failing.execute_pipeline(artifact_bundle=bundle)
        final_status = client_failing.wait_for_execution(exec_.id)
        assert final_status == ExecutionStatus.FAILED

    def test_raises_on_unknown_id(self, client):
        with pytest.raises(KeyError):
            client.wait_for_execution("NONEXISTENT")


class TestRollbackExecution:
    def test_rollback_sets_rolled_back_status(self, client_failing):
        bundle = client_failing.create_artifact_bundle(name="rollback-bundle")
        exec_ = client_failing.execute_pipeline(artifact_bundle=bundle)
        client_failing.wait_for_execution(exec_.id)
        rolled_back = client_failing.rollback_execution(exec_.id)
        assert rolled_back.status == ExecutionStatus.ROLLED_BACK

    def test_rollback_returns_execution_object(self, client):
        bundle = client.create_artifact_bundle(name="rb-obj-bundle")
        exec_ = client.execute_pipeline(artifact_bundle=bundle)
        client.wait_for_execution(exec_.id)
        result = client.rollback_execution(exec_.id)
        assert isinstance(result, PipelineExecution)

    def test_rollback_raises_on_unknown(self, client):
        with pytest.raises(KeyError):
            client.rollback_execution("UNKNOWN-ID")


class TestGetServiceDeployments:
    def test_returns_list(self, client):
        deployments = client.get_service_deployments()
        assert isinstance(deployments, list)
        assert len(deployments) > 0

    def test_deployments_have_expected_keys(self, client):
        deployments = client.get_service_deployments()
        for d in deployments:
            assert "service" in d
            assert "artifact_tag" in d

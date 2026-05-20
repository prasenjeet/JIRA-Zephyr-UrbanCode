"""Unit tests for the UrbanCode Deploy decoy client."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.urbancode.client import UrbanCodeClient
from src.urbancode.models import DeploymentRequest, DeploymentStatus, Snapshot


@pytest.fixture()
def client() -> UrbanCodeClient:
    return UrbanCodeClient(application="TestApp", environment="Staging")


@pytest.fixture()
def client_failing() -> UrbanCodeClient:
    return UrbanCodeClient(
        application="TestApp", environment="Staging", simulate_failure=True
    )


class TestCreateSnapshot:
    def test_returns_snapshot(self, client):
        snap = client.create_snapshot(name="v1.0.0")
        assert isinstance(snap, Snapshot)

    def test_name_stored(self, client):
        snap = client.create_snapshot(name="release-1.2.3")
        assert snap.name == "release-1.2.3"

    def test_component_versions_populated(self, client):
        snap = client.create_snapshot(name="default-versions")
        assert len(snap.versions) > 0

    def test_application_defaults_to_client_app(self, client):
        snap = client.create_snapshot(name="app-test")
        assert snap.application == "TestApp"

    def test_environment_override(self, client):
        snap = client.create_snapshot(name="env-snap", environment="QA")
        assert snap.environment == "QA"


class TestRequestDeployment:
    def test_returns_deployment_request(self, client):
        snap = client.create_snapshot(name="deploy-snap")
        req = client.request_deployment(snapshot=snap)
        assert isinstance(req, DeploymentRequest)

    def test_initial_status_pending(self, client):
        snap = client.create_snapshot(name="pending-snap")
        req = client.request_deployment(snapshot=snap)
        assert req.status == DeploymentStatus.PENDING

    def test_log_url_set(self, client):
        snap = client.create_snapshot(name="log-snap")
        req = client.request_deployment(snapshot=snap)
        assert req.id in req.log_url

    def test_auto_creates_snapshot_when_none(self, client):
        """request_deployment auto-creates a snapshot when none is provided."""
        req = client.request_deployment()
        assert isinstance(req, DeploymentRequest)
        assert req.snapshot is not None


class TestGetDeploymentStatus:
    def test_advances_from_pending_to_running(self, client):
        snap = client.create_snapshot(name="status-snap")
        req = client.request_deployment(snapshot=snap)
        # First poll: PENDING → RUNNING
        status = client.get_deployment_status(req.id)
        assert status == DeploymentStatus.RUNNING

    def test_advances_from_running_to_succeeded(self, client):
        snap = client.create_snapshot(name="succeed-snap")
        req = client.request_deployment(snapshot=snap)
        client.get_deployment_status(req.id)  # PENDING → RUNNING
        status = client.get_deployment_status(req.id)  # RUNNING → SUCCEEDED
        assert status == DeploymentStatus.SUCCEEDED

    def test_raises_on_unknown_id(self, client):
        with pytest.raises(KeyError):
            client.get_deployment_status("NONEXISTENT")


class TestWaitForDeployment:
    def test_succeeds_by_default(self, client):
        snap = client.create_snapshot(name="success-snap")
        req = client.request_deployment(snapshot=snap)
        final_status = client.wait_for_deployment(req.id)
        assert final_status == DeploymentStatus.SUCCEEDED

    def test_fails_when_simulate_failure(self, client_failing):
        snap = client_failing.create_snapshot(name="fail-snap")
        req = client_failing.request_deployment(snapshot=snap)
        final_status = client_failing.wait_for_deployment(req.id)
        assert final_status == DeploymentStatus.FAILED

    def test_raises_on_unknown_id(self, client):
        with pytest.raises(KeyError):
            client.wait_for_deployment("NONEXISTENT")


class TestRollbackDeployment:
    def test_rollback_sets_rolled_back_status(self, client_failing):
        snap = client_failing.create_snapshot(name="rollback-snap")
        req = client_failing.request_deployment(snapshot=snap)
        client_failing.wait_for_deployment(req.id)
        rolled_back = client_failing.rollback_deployment(req.id)
        assert rolled_back.status == DeploymentStatus.ROLLED_BACK

    def test_rollback_returns_request_object(self, client):
        snap = client.create_snapshot(name="rb-obj-snap")
        req = client.request_deployment(snapshot=snap)
        client.wait_for_deployment(req.id)
        result = client.rollback_deployment(req.id)
        assert isinstance(result, DeploymentRequest)

    def test_rollback_raises_on_unknown(self, client):
        with pytest.raises(KeyError):
            client.rollback_deployment("UNKNOWN-ID")


class TestGetEnvironmentVersions:
    def test_returns_list(self, client):
        versions = client.get_environment_versions()
        assert isinstance(versions, list)
        assert len(versions) > 0

    def test_versions_have_expected_keys(self, client):
        versions = client.get_environment_versions()
        for v in versions:
            assert "component" in v
            assert "version" in v

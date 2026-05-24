"""Tests for the real UrbanCode Deploy client (HTTP calls mocked with responses library)."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import responses as resp_lib
from src.urbancode.real import RealUrbanCodeClient
from src.urbancode.models import DeploymentRequest, DeploymentStatus, Snapshot
from src.exceptions import AuthenticationError, NotFoundError

BASE = "https://test-ucd-server:8443"


@pytest.fixture
def client():
    return RealUrbanCodeClient(
        base_url=BASE,
        username="admin",
        password="secret",
        application="TestApp",
        environment="Staging",
        verify_ssl=False,
    )


def _snapshot_response(snap_id="SNAP-001", name="TestApp-Staging-20240115"):
    return {
        "id": snap_id,
        "name": name,
        "description": "",
        "created": "1705312800000",
        "createdBy": "admin",
    }


def _deployment_response(req_id="REQ-000001", result="RUNNING"):
    return {
        "requestId": req_id,
        "id": req_id,
        "result": result,
        "status": result,
    }


@resp_lib.activate
def test_create_snapshot(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/deploy/snapshot",
        json=_snapshot_response(), status=200
    )
    snap = client.create_snapshot(name="TestApp-Staging-20240115")
    assert isinstance(snap, Snapshot)
    assert snap.name == "TestApp-Staging-20240115"
    assert snap.application == "TestApp"


@resp_lib.activate
def test_create_snapshot_auth_error(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/deploy/snapshot",
        json={}, status=401
    )
    with pytest.raises(AuthenticationError):
        client.create_snapshot(name="bad-snap")


@resp_lib.activate
def test_request_deployment(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/deploy/snapshot",
        json=_snapshot_response(), status=200
    )
    resp_lib.add(
        resp_lib.PUT, f"{BASE}/rest/deploy/applicationProcessRequest",
        json=_deployment_response(result="SCHEDULED"), status=200
    )
    req = client.request_deployment()
    assert isinstance(req, DeploymentRequest)
    assert req.status == DeploymentStatus.PENDING
    assert req.id == "REQ-000001"


@resp_lib.activate
def test_request_deployment_with_snapshot(client):
    snap = Snapshot(
        id="SNAP-001",
        name="pre-existing",
        application="TestApp",
        environment="Staging",
    )
    resp_lib.add(
        resp_lib.PUT, f"{BASE}/rest/deploy/applicationProcessRequest",
        json=_deployment_response(result="SCHEDULED"), status=200
    )
    req = client.request_deployment(snapshot=snap)
    assert isinstance(req, DeploymentRequest)
    assert req.snapshot.name == "pre-existing"


@resp_lib.activate
def test_get_deployment_status_succeeded(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/deploy/applicationProcessRequest/REQ-000001",
        json=_deployment_response(result="SUCCEEDED"), status=200
    )
    status = client.get_deployment_status("REQ-000001")
    assert status == DeploymentStatus.SUCCEEDED


@resp_lib.activate
def test_get_deployment_status_failed(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/deploy/applicationProcessRequest/REQ-000001",
        json=_deployment_response(result="FAULTED"), status=200
    )
    status = client.get_deployment_status("REQ-000001")
    assert status == DeploymentStatus.FAILED


@resp_lib.activate
def test_get_deployment_status_running(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/deploy/applicationProcessRequest/REQ-000001",
        json=_deployment_response(result="RUNNING"), status=200
    )
    status = client.get_deployment_status("REQ-000001")
    assert status == DeploymentStatus.RUNNING


@resp_lib.activate
def test_get_deployment_status_auth_error(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/deploy/applicationProcessRequest/REQ-000001",
        json={}, status=401
    )
    with pytest.raises(AuthenticationError):
        client.get_deployment_status("REQ-000001")


@resp_lib.activate
def test_wait_for_deployment_succeeds(client):
    # First call: RUNNING, second call: SUCCEEDED
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/deploy/applicationProcessRequest/REQ-000001",
        json=_deployment_response(result="RUNNING"), status=200
    )
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/deploy/applicationProcessRequest/REQ-000001",
        json=_deployment_response(result="SUCCEEDED"), status=200
    )
    status = client.wait_for_deployment("REQ-000001", timeout=10, poll_interval=0.01)
    assert status == DeploymentStatus.SUCCEEDED


@resp_lib.activate
def test_rollback_deployment(client):
    resp_lib.add(
        resp_lib.PUT, f"{BASE}/rest/deploy/applicationProcessRequest/REQ-000001/rollback",
        json={}, status=200
    )
    req = client.rollback_deployment("REQ-000001")
    assert isinstance(req, DeploymentRequest)
    assert req.status == DeploymentStatus.ROLLED_BACK


@resp_lib.activate
def test_rollback_deployment_auth_error(client):
    resp_lib.add(
        resp_lib.PUT, f"{BASE}/rest/deploy/applicationProcessRequest/REQ-000001/rollback",
        json={}, status=401
    )
    with pytest.raises(AuthenticationError):
        client.rollback_deployment("REQ-000001")

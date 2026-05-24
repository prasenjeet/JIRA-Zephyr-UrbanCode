"""Real UrbanCode Deploy client — makes actual HTTP calls to the UCD REST API.

Authentication uses HTTP Basic Auth.
See: https://www.ibm.com/docs/en/urbancode-deploy
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests
from requests.auth import HTTPBasicAuth

from src.exceptions import APIError, AuthenticationError, DeploymentError, NotFoundError
from .base import BaseUrbanCodeClient
from .models import ComponentVersion, DeploymentRequest, DeploymentStatus, Snapshot


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_datetime(s: str | None) -> Optional[datetime]:
    """Parse a UCD timestamp (milliseconds epoch or ISO string) to datetime."""
    if not s:
        return None
    # UCD sometimes returns epoch milliseconds as a string
    try:
        ms = int(s)
        return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    except (ValueError, TypeError):
        pass
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def _map_ucd_status(ucd_result: str) -> DeploymentStatus:
    """Map a UCD result string to a :class:`DeploymentStatus`."""
    mapping = {
        "SUCCEEDED": DeploymentStatus.SUCCEEDED,
        "FAULTED": DeploymentStatus.FAILED,
        "FAILED": DeploymentStatus.FAILED,
        "RUNNING": DeploymentStatus.RUNNING,
        "SCHEDULED": DeploymentStatus.PENDING,
        "PENDING": DeploymentStatus.PENDING,
        "CANCELLED": DeploymentStatus.CANCELLED,
        "CANCELING": DeploymentStatus.CANCELLED,
    }
    return mapping.get(ucd_result.upper(), DeploymentStatus.RUNNING)


class RealUrbanCodeClient(BaseUrbanCodeClient):
    """Real UrbanCode Deploy client that calls the UCD REST API.

    Args:
        base_url: UCD server base URL, e.g. ``https://ucd-server:8443``.
        username: UCD username.
        password: UCD password.
        application: Default application name.
        environment: Default target environment.
        verify_ssl: Set to ``False`` to skip TLS verification (common for
            UCD servers with self-signed certificates).
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        application: str = "MyApp",
        environment: str = "Production",
        verify_ssl: bool = False,
        **kwargs,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.application = application
        self.environment = environment
        self.use_decoy = False

        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(username, password)
        self._session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )
        self._session.verify = verify_ssl

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _api(self, method: str, path: str, **kwargs: Any) -> dict:
        url = f"{self.base_url}/rest/{path}"
        try:
            resp = self._session.request(method, url, **kwargs)
        except requests.ConnectionError as exc:
            raise APIError(f"Connection failed to {url}: {exc}") from exc

        if resp.status_code == 401:
            raise AuthenticationError(
                "UrbanCode Deploy authentication failed — check username and password."
            )
        if resp.status_code == 404:
            raise NotFoundError(f"UCD resource not found: {path}")

        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise APIError(
                str(exc), status_code=resp.status_code, response_body=resp.text
            ) from exc

        return resp.json() if resp.content else {}

    def _log(self, message: str) -> None:
        print(f"[URBANCODE REAL] {message}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_snapshot(
        self,
        application: str | None = None,
        environment: str | None = None,
        name: str | None = None,
        description: str = "",
    ) -> Snapshot:
        """Create an application snapshot in UCD."""
        app = application or self.application
        env = environment or self.environment
        snap_name = name or f"{app}-{env}-{_now().strftime('%Y%m%d-%H%M%S')}"

        self._log(f"POST /rest/deploy/snapshot  app={app!r}  env={env!r}  name={snap_name!r}")

        payload = {
            "name": snap_name,
            "description": description,
            "application": {"name": app},
            "environment": {"name": env},
        }
        data = self._api("POST", "deploy/snapshot", json=payload)

        snapshot = Snapshot(
            id=data.get("id", snap_name),
            name=data.get("name", snap_name),
            application=app,
            environment=env,
            description=description,
            created=_parse_datetime(data.get("created")) or _now(),
            created_by=data.get("createdBy", self.username),
        )
        self._log(f"  -> Created {snapshot!r}")
        return snapshot

    def request_deployment(
        self,
        application: str | None = None,
        environment: str | None = None,
        snapshot: Optional[Snapshot] = None,
        process: str = "Deploy",
    ) -> DeploymentRequest:
        """Submit a deployment request to UCD."""
        app = application or self.application
        env = environment or self.environment

        if snapshot is None:
            snapshot = self.create_snapshot(application=app, environment=env)

        self._log(
            f"PUT /rest/deploy/applicationProcessRequest  "
            f"app={app!r}  env={env!r}  process={process!r}  snapshot={snapshot.name!r}"
        )

        payload = {
            "application": {"name": app},
            "applicationProcess": {"name": process},
            "environment": {"name": env},
            "snapshot": {"name": snapshot.name},
        }
        data = self._api("PUT", "deploy/applicationProcessRequest", json=payload)

        req_id = data.get("requestId") or data.get("id", "")
        log_url = f"{self.base_url}/#application/{app}/deployments/{req_id}"

        req = DeploymentRequest(
            id=req_id,
            application=app,
            environment=env,
            snapshot=snapshot,
            process=process,
            status=DeploymentStatus.PENDING,
            submitted_at=_now(),
            submitted_by=self.username,
            log_url=log_url,
        )
        self._log(f"  -> Submitted deployment request {req_id!r}")
        return req

    def get_deployment_status(self, request_id: str) -> DeploymentStatus:
        """Return the current status of a UCD deployment request."""
        self._log(f"GET /rest/deploy/applicationProcessRequest/{request_id}")
        data = self._api("GET", f"deploy/applicationProcessRequest/{request_id}")
        result = data.get("result", data.get("status", "RUNNING"))
        status = _map_ucd_status(result)
        self._log(f"  -> Status: {result!r} -> {status}")
        return status

    def wait_for_deployment(
        self,
        request_id: str,
        timeout: int = 300,
        poll_interval: float = 2.0,
    ) -> DeploymentStatus:
        """Poll until a UCD deployment reaches a terminal status or timeout."""
        self._log(
            f"Waiting for deployment {request_id!r} "
            f"(timeout={timeout}s, poll={poll_interval}s) ..."
        )
        deadline = _now() + timedelta(seconds=timeout)
        while _now() < deadline:
            status = self.get_deployment_status(request_id)
            self._log(f"  [poll] status={status}")
            if status.is_terminal:
                self._log(f"  -> Deployment reached terminal status: {status}")
                return status
            time.sleep(poll_interval)

        raise DeploymentError(
            f"Deployment {request_id!r} did not complete within {timeout}s."
        )

    def rollback_deployment(self, request_id: str) -> DeploymentRequest:
        """Trigger a rollback for a UCD deployment."""
        self._log(f"PUT /rest/deploy/applicationProcessRequest/{request_id}/rollback")
        data = self._api("PUT", f"deploy/applicationProcessRequest/{request_id}/rollback")

        req = DeploymentRequest(
            id=request_id,
            application=self.application,
            environment=self.environment,
            snapshot=Snapshot(
                id="rollback",
                name="rollback",
                application=self.application,
                environment=self.environment,
            ),
            process="Rollback",
            status=DeploymentStatus.ROLLED_BACK,
            submitted_at=_now(),
            submitted_by=self.username,
        )
        self._log(f"  -> Rollback initiated for {request_id!r}")
        return req

    def get_environment_versions(
        self,
        application: str | None = None,
        environment: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the currently deployed component versions for a UCD environment."""
        app = application or self.application
        env = environment or self.environment
        self._log(
            f"GET /rest/deploy/environment/{app}/{env}/latestDesiredInventory"
        )
        data = self._api("GET", f"deploy/environment/{app}/{env}/latestDesiredInventory")

        items = data if isinstance(data, list) else data.get("versions", [])
        versions = [
            {
                "component": item.get("component", {}).get("name", "unknown"),
                "version": item.get("version", {}).get("name", "unknown"),
                "deployed_at": item.get("lastModifiedDate", ""),
                "status": item.get("status", "ACTIVE"),
            }
            for item in items
        ]
        self._log(f"  -> Returning {len(versions)} component version(s) for {app}/{env}")
        return versions

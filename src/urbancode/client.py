"""UrbanCode Deploy Decoy Client - simulates the UCD REST API.

All methods print "[URBANCODE DECOY]" prefixed messages and return realistic mock data.
Simulated network latency of ~100ms is included via time.sleep(0.1).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from .models import ComponentVersion, DeploymentRequest, DeploymentStatus, Snapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REQUEST_COUNTER: int = 0
_SNAPSHOT_COUNTER: int = 0

_SAMPLE_COMPONENTS = [
    ("api-service", "2.4.1"),
    ("web-frontend", "1.9.3"),
    ("auth-service", "3.1.0"),
    ("data-processor", "1.2.7"),
    ("notification-service", "0.8.5"),
]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _short_id() -> str:
    return uuid.uuid4().hex[:8].upper()


def _next_request_id() -> str:
    global _REQUEST_COUNTER
    _REQUEST_COUNTER += 1
    return f"REQ-{_REQUEST_COUNTER:06d}"


def _next_snapshot_id() -> str:
    global _SNAPSHOT_COUNTER
    _SNAPSHOT_COUNTER += 1
    return f"SNAP-{_SNAPSHOT_COUNTER:04d}"


# ---------------------------------------------------------------------------
# UrbanCodeClient
# ---------------------------------------------------------------------------


class UrbanCodeClient:
    """Decoy UrbanCode Deploy client that simulates the UCD REST API.

    All operations are performed in-memory.  Deployments are simulated to
    progress through PENDING → RUNNING → SUCCEEDED automatically.

    Args:
        base_url: UCD server base URL (e.g. ``https://ucd-server:8443``).
        username: UCD username.
        password: UCD password.
        application: Default application name.
        environment: Default target environment.
        use_decoy: When ``True`` all methods use in-memory mock data.
        simulate_failure: When ``True`` deployments will randomly fail ~20% of
            the time (useful for testing failure paths).
    """

    def __init__(
        self,
        base_url: str = "https://your-urbancode-server:8443",
        username: str = "admin",
        password: str = "decoy-password",
        application: str = "MyApp",
        environment: str = "Production",
        use_decoy: bool = True,
        simulate_failure: bool = False,
    ) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password
        self.application = application
        self.environment = environment
        self.use_decoy = use_decoy
        self.simulate_failure = simulate_failure

        self._snapshots: dict[str, Snapshot] = {}
        self._requests: dict[str, DeploymentRequest] = {}

        self._log("UrbanCodeClient initialised (decoy mode).")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        print(f"[URBANCODE DECOY] {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

    def _ucd_url(self, path: str) -> str:
        return f"{self.base_url}/rest/{path}"

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
        """Create an application snapshot capturing current component versions.

        Args:
            application: Application name (defaults to ``self.application``).
            environment: Environment name (defaults to ``self.environment``).
            name: Snapshot name (auto-generated if not provided).
            description: Optional description.

        Returns:
            Newly created :class:`Snapshot`.
        """
        self._simulate_latency()
        app = application or self.application
        env = environment or self.environment
        snap_id = _next_snapshot_id()
        snap_name = name or f"{app}-{env}-{_now().strftime('%Y%m%d-%H%M%S')}"

        self._log(
            f"POST {self._ucd_url('deploy/snapshot')}  "
            f"(app={app!r}, env={env!r})"
        )
        self._log(f"  name: {snap_name!r}")

        versions = [
            ComponentVersion(
                component=comp,
                version=ver,
                description=f"Auto-captured version of {comp}",
                created=_now(),
            )
            for comp, ver in _SAMPLE_COMPONENTS
        ]

        snapshot = Snapshot(
            id=snap_id,
            name=snap_name,
            application=app,
            environment=env,
            versions=versions,
            description=description,
            created=_now(),
        )
        self._snapshots[snap_id] = snapshot
        self._log(
            f"  -> Created {snapshot!r} with {len(versions)} component version(s)"
        )
        return snapshot

    def request_deployment(
        self,
        application: str | None = None,
        environment: str | None = None,
        snapshot: Snapshot | None = None,
        process: str = "Deploy",
    ) -> DeploymentRequest:
        """Submit a deployment request to UrbanCode Deploy.

        If no snapshot is provided a new one is automatically created.

        Args:
            application: Application name (defaults to ``self.application``).
            environment: Target environment (defaults to ``self.environment``).
            snapshot: Snapshot to deploy (auto-created if not provided).
            process: UCD process name to execute.

        Returns:
            :class:`DeploymentRequest` in PENDING status.
        """
        self._simulate_latency()
        app = application or self.application
        env = environment or self.environment

        if snapshot is None:
            self._log("  No snapshot provided — creating one automatically.")
            snapshot = self.create_snapshot(application=app, environment=env)

        req_id = _next_request_id()
        self._log(
            f"PUT {self._ucd_url('deploy/applicationProcessRequest')}  "
            f"(app={app!r}, env={env!r}, process={process!r})"
        )
        self._log(f"  snapshot : {snapshot.name!r} ({snapshot.id})")

        log_url = (
            f"{self.base_url}/#application/{app}/deployments/{req_id}"
        )

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
        self._requests[req_id] = req
        self._log(f"  -> Submitted {req!r}")
        return req

    def get_deployment_status(self, request_id: str) -> DeploymentStatus:
        """Return the current status of a deployment request.

        The decoy client advances PENDING → RUNNING → SUCCEEDED automatically
        with each successive call to simulate a real deployment lifecycle.

        Args:
            request_id: Deployment request identifier.

        Returns:
            Current :class:`DeploymentStatus`.

        Raises:
            KeyError: If the request is not found.
        """
        self._simulate_latency()
        self._log(
            f"GET {self._ucd_url(f'deploy/applicationProcessRequest/{request_id}')}"
        )

        if request_id not in self._requests:
            raise KeyError(f"Deployment request {request_id!r} not found.")

        req = self._requests[request_id]

        # Advance the state machine
        if req.status == DeploymentStatus.PENDING:
            req.status = DeploymentStatus.RUNNING
            req.started_at = _now()
            self._log(f"  -> Status advanced to RUNNING")
        elif req.status == DeploymentStatus.RUNNING:
            if self.simulate_failure:
                req.status = DeploymentStatus.FAILED
            else:
                req.status = DeploymentStatus.SUCCEEDED
            req.completed_at = _now()
            self._log(f"  -> Status advanced to {req.status}")
        else:
            self._log(f"  -> Status is {req.status} (terminal)")

        return req.status

    def wait_for_deployment(
        self,
        request_id: str,
        timeout: int = 300,
        poll_interval: float = 2.0,
    ) -> DeploymentStatus:
        """Poll until a deployment reaches a terminal status or timeout.

        In decoy mode the polling loop runs a fixed number of iterations
        (simulating 2-3 status calls) rather than waiting the full timeout.

        Args:
            request_id: Deployment request identifier.
            timeout: Maximum seconds to wait (used for documentation; decoy
                always completes quickly).
            poll_interval: Seconds between polls (reduced to 0.1 in decoy mode).

        Returns:
            Final :class:`DeploymentStatus`.

        Raises:
            KeyError: If the request is not found.
            TimeoutError: If the deployment does not complete within *timeout*.
        """
        self._log(
            f"Waiting for deployment {request_id!r} "
            f"(timeout={timeout}s, poll={poll_interval}s) ..."
        )
        # Decoy: override poll interval to keep things snappy
        effective_poll = 0.15

        deadline = _now() + timedelta(seconds=timeout)
        while _now() < deadline:
            status = self.get_deployment_status(request_id)
            self._log(f"  [poll] status={status}")
            if status.is_terminal:
                self._log(f"  -> Deployment reached terminal status: {status}")
                return status
            time.sleep(effective_poll)

        raise TimeoutError(
            f"Deployment {request_id!r} did not complete within {timeout}s."
        )

    def rollback_deployment(self, request_id: str) -> DeploymentRequest:
        """Trigger a rollback for a failed or completed deployment.

        Args:
            request_id: ID of the deployment request to roll back.

        Returns:
            Updated :class:`DeploymentRequest` now in ROLLING_BACK status.

        Raises:
            KeyError: If the request is not found.
        """
        self._simulate_latency()
        self._log(
            f"PUT {self._ucd_url(f'deploy/applicationProcessRequest/{request_id}/rollback')}"
        )

        if request_id not in self._requests:
            raise KeyError(f"Deployment request {request_id!r} not found.")

        req = self._requests[request_id]
        req.status = DeploymentStatus.ROLLING_BACK
        self._log(f"  -> Initiated rollback for {request_id!r}")

        # Simulate rollback completion immediately in decoy mode
        time.sleep(0.15)
        req.status = DeploymentStatus.ROLLED_BACK
        req.completed_at = _now()
        self._log(f"  -> Rollback complete for {request_id!r}")
        return req

    def get_environment_versions(
        self,
        application: str | None = None,
        environment: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the currently deployed component versions for an environment.

        Args:
            application: Application name (defaults to ``self.application``).
            environment: Environment name (defaults to ``self.environment``).

        Returns:
            List of dicts with keys ``component``, ``version``, ``deployed_at``.
        """
        self._simulate_latency()
        app = application or self.application
        env = environment or self.environment
        self._log(
            f"GET {self._ucd_url(f'deploy/environment/{app}/{env}/latestDesiredInventory')}"
        )

        versions = [
            {
                "component": comp,
                "version": ver,
                "deployed_at": (_now() - timedelta(hours=i * 2)).isoformat(),
                "status": "ACTIVE",
            }
            for i, (comp, ver) in enumerate(_SAMPLE_COMPONENTS)
        ]
        self._log(f"  -> Returning {len(versions)} component version(s) for {app}/{env}")
        return versions

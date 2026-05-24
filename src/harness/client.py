"""Harness CD Decoy Client - simulates the Harness NextGen REST API.

All methods print "[HARNESS DECOY]" prefixed messages and return realistic mock data.
Simulated network latency of ~100ms is included via time.sleep(0.1).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from .models import ArtifactBundle, ExecutionStatus, PipelineExecution, ServiceArtifact

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EXECUTION_COUNTER: int = 0
_BUNDLE_COUNTER: int = 0

_SAMPLE_SERVICES = [
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


def _next_execution_id() -> str:
    global _EXECUTION_COUNTER
    _EXECUTION_COUNTER += 1
    return f"EXEC-{_EXECUTION_COUNTER:06d}"


def _next_bundle_id() -> str:
    global _BUNDLE_COUNTER
    _BUNDLE_COUNTER += 1
    return f"BNDL-{_BUNDLE_COUNTER:04d}"


# ---------------------------------------------------------------------------
# HarnessClient
# ---------------------------------------------------------------------------


class HarnessClient:
    """Decoy Harness CD client that simulates the Harness NextGen REST API.

    All operations are performed in-memory.  Executions are simulated to
    progress through QUEUED → RUNNING → SUCCESS automatically.

    Args:
        base_url: Harness server base URL (e.g. ``https://app.harness.io``).
        api_key: Harness API key.
        account_id: Harness account identifier.
        org_id: Harness organisation identifier.
        project: Default Harness project identifier.
        pipeline_id: Default pipeline to execute.
        environment: Default target environment.
        use_decoy: When ``True`` all methods use in-memory mock data.
        simulate_failure: When ``True`` executions will fail (useful for testing
            failure paths).
    """

    def __init__(
        self,
        base_url: str = "https://app.harness.io",
        api_key: str = "decoy-api-key",
        account_id: str = "myAccount",
        org_id: str = "myOrg",
        project: str = "MyProject",
        pipeline_id: str = "deploy",
        environment: str = "Production",
        use_decoy: bool = True,
        simulate_failure: bool = False,
    ) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.account_id = account_id
        self.org_id = org_id
        self.project = project
        self.pipeline_id = pipeline_id
        self.environment = environment
        self.use_decoy = use_decoy
        self.simulate_failure = simulate_failure

        self._bundles: dict[str, ArtifactBundle] = {}
        self._executions: dict[str, PipelineExecution] = {}

        self._log("HarnessClient initialised (decoy mode).")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        print(f"[HARNESS DECOY] {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

    def _api_url(self, path: str) -> str:
        return f"{self.base_url}/{path}"

    def _qs(self) -> str:
        return (
            f"accountIdentifier={self.account_id}"
            f"&orgIdentifier={self.org_id}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_artifact_bundle(
        self,
        project: str | None = None,
        pipeline_id: str | None = None,
        environment: str | None = None,
        name: str | None = None,
        description: str = "",
    ) -> ArtifactBundle:
        """Create an artifact bundle capturing the current service artifact versions.

        Args:
            project: Harness project identifier (defaults to ``self.project``).
            pipeline_id: Pipeline identifier (defaults to ``self.pipeline_id``).
            environment: Environment name (defaults to ``self.environment``).
            name: Bundle name (auto-generated if not provided).
            description: Optional description.

        Returns:
            Newly created :class:`ArtifactBundle`.
        """
        self._simulate_latency()
        proj = project or self.project
        pipe = pipeline_id or self.pipeline_id
        env = environment or self.environment
        bundle_id = _next_bundle_id()
        bundle_name = name or f"{proj}-{env}-{_now().strftime('%Y%m%d-%H%M%S')}"

        self._log(
            f"POST {self._api_url('ng/api/artifactBundles')}?{self._qs()}"
            f"&projectIdentifier={proj}  (pipeline={pipe!r}, env={env!r})"
        )
        self._log(f"  name: {bundle_name!r}")

        artifacts = [
            ServiceArtifact(
                service=svc,
                artifact_tag=tag,
                description=f"Auto-captured artifact for {svc}",
                created=_now(),
            )
            for svc, tag in _SAMPLE_SERVICES
        ]

        bundle = ArtifactBundle(
            id=bundle_id,
            name=bundle_name,
            project=proj,
            pipeline_id=pipe,
            environment=env,
            artifacts=artifacts,
            description=description,
            created=_now(),
        )
        self._bundles[bundle_id] = bundle
        self._log(
            f"  -> Created {bundle!r} with {len(artifacts)} service artifact(s)"
        )
        return bundle

    def execute_pipeline(
        self,
        project: str | None = None,
        environment: str | None = None,
        artifact_bundle: ArtifactBundle | None = None,
        pipeline_id: str | None = None,
    ) -> PipelineExecution:
        """Submit a pipeline execution to Harness CD.

        If no artifact bundle is provided a new one is automatically created.

        Args:
            project: Harness project identifier (defaults to ``self.project``).
            environment: Target environment (defaults to ``self.environment``).
            artifact_bundle: Bundle to deploy (auto-created if not provided).
            pipeline_id: Pipeline to execute (defaults to ``self.pipeline_id``).

        Returns:
            :class:`PipelineExecution` in QUEUED status.
        """
        self._simulate_latency()
        proj = project or self.project
        env = environment or self.environment
        pipe = pipeline_id or self.pipeline_id

        if artifact_bundle is None:
            self._log("  No artifact bundle provided — creating one automatically.")
            artifact_bundle = self.create_artifact_bundle(
                project=proj, pipeline_id=pipe, environment=env
            )

        exec_id = _next_execution_id()
        self._log(
            f"POST {self._api_url('pipeline/api/pipelines/execution/v2')}"
            f"?{self._qs()}&projectIdentifier={proj}&pipelineIdentifier={pipe}"
            f"  (env={env!r})"
        )
        self._log(f"  bundle : {artifact_bundle.name!r} ({artifact_bundle.id})")

        log_url = (
            f"{self.base_url}/ng/#/account/{self.account_id}/cd/orgs/{self.org_id}"
            f"/projects/{proj}/pipelines/{pipe}/executions/{exec_id}/pipeline"
        )

        execution = PipelineExecution(
            id=exec_id,
            project=proj,
            pipeline_id=pipe,
            environment=env,
            artifact_bundle=artifact_bundle,
            status=ExecutionStatus.QUEUED,
            submitted_at=_now(),
            submitted_by=self.api_key[:8] + "...",
            log_url=log_url,
        )
        self._executions[exec_id] = execution
        self._log(f"  -> Submitted {execution!r}")
        return execution

    def get_execution_status(self, execution_id: str) -> ExecutionStatus:
        """Return the current status of a pipeline execution.

        The decoy client advances QUEUED → RUNNING → SUCCESS automatically
        with each successive call to simulate a real execution lifecycle.

        Args:
            execution_id: Pipeline execution identifier.

        Returns:
            Current :class:`ExecutionStatus`.

        Raises:
            KeyError: If the execution is not found.
        """
        self._simulate_latency()
        self._log(
            f"GET {self._api_url(f'pipeline/api/pipelines/execution/v2/{execution_id}')}"
            f"?{self._qs()}"
        )

        if execution_id not in self._executions:
            raise KeyError(f"Pipeline execution {execution_id!r} not found.")

        exec_ = self._executions[execution_id]

        if exec_.status == ExecutionStatus.QUEUED:
            exec_.status = ExecutionStatus.RUNNING
            exec_.started_at = _now()
            self._log("  -> Status advanced to RUNNING")
        elif exec_.status == ExecutionStatus.RUNNING:
            if self.simulate_failure:
                exec_.status = ExecutionStatus.FAILED
            else:
                exec_.status = ExecutionStatus.SUCCESS
            exec_.completed_at = _now()
            self._log(f"  -> Status advanced to {exec_.status}")
        else:
            self._log(f"  -> Status is {exec_.status} (terminal)")

        return exec_.status

    def wait_for_execution(
        self,
        execution_id: str,
        timeout: int = 300,
        poll_interval: float = 2.0,
    ) -> ExecutionStatus:
        """Poll until a pipeline execution reaches a terminal status or timeout.

        In decoy mode the polling loop runs a fixed number of iterations
        (simulating 2–3 status calls) rather than waiting the full timeout.

        Args:
            execution_id: Pipeline execution identifier.
            timeout: Maximum seconds to wait.
            poll_interval: Seconds between polls (reduced to 0.15 in decoy mode).

        Returns:
            Final :class:`ExecutionStatus`.

        Raises:
            KeyError: If the execution is not found.
            TimeoutError: If the execution does not complete within *timeout*.
        """
        self._log(
            f"Waiting for execution {execution_id!r} "
            f"(timeout={timeout}s, poll={poll_interval}s) ..."
        )
        effective_poll = 0.15

        deadline = _now() + timedelta(seconds=timeout)
        while _now() < deadline:
            status = self.get_execution_status(execution_id)
            self._log(f"  [poll] status={status}")
            if status.is_terminal:
                self._log(f"  -> Execution reached terminal status: {status}")
                return status
            time.sleep(effective_poll)

        raise TimeoutError(
            f"Execution {execution_id!r} did not complete within {timeout}s."
        )

    def rollback_execution(self, execution_id: str) -> PipelineExecution:
        """Trigger a rollback for a failed or completed pipeline execution.

        Args:
            execution_id: ID of the execution to roll back.

        Returns:
            Updated :class:`PipelineExecution` now in ROLLING_BACK status.

        Raises:
            KeyError: If the execution is not found.
        """
        self._simulate_latency()
        self._log(
            f"POST {self._api_url(f'pipeline/api/pipelines/execution/v2/{execution_id}/rollback')}"
            f"?{self._qs()}"
        )

        if execution_id not in self._executions:
            raise KeyError(f"Pipeline execution {execution_id!r} not found.")

        exec_ = self._executions[execution_id]
        exec_.status = ExecutionStatus.ROLLING_BACK
        self._log(f"  -> Initiated rollback for {execution_id!r}")

        time.sleep(0.15)
        exec_.status = ExecutionStatus.ROLLED_BACK
        exec_.completed_at = _now()
        self._log(f"  -> Rollback complete for {execution_id!r}")
        return exec_

    def get_service_deployments(
        self,
        project: str | None = None,
        environment: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return the currently deployed service artifact versions for an environment.

        Args:
            project: Harness project identifier (defaults to ``self.project``).
            environment: Environment name (defaults to ``self.environment``).

        Returns:
            List of dicts with keys ``service``, ``artifact_tag``, ``deployed_at``,
            ``status``.
        """
        self._simulate_latency()
        proj = project or self.project
        env = environment or self.environment
        self._log(
            f"GET {self._api_url('ng/api/services/deployments')}"
            f"?{self._qs()}&projectIdentifier={proj}&environmentIdentifier={env}"
        )

        deployments = [
            {
                "service": svc,
                "artifact_tag": tag,
                "deployed_at": (_now() - timedelta(hours=i * 2)).isoformat(),
                "status": "ACTIVE",
            }
            for i, (svc, tag) in enumerate(_SAMPLE_SERVICES)
        ]
        self._log(
            f"  -> Returning {len(deployments)} service deployment(s) for {proj}/{env}"
        )
        return deployments

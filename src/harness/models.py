"""Harness CD data models using Python 3.10+ dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ExecutionStatus(str, Enum):
    """Possible statuses for a Harness pipeline execution."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"

    def __str__(self) -> str:  # noqa: D105
        return self.value

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` if the status is a terminal (final) state."""
        return self in (
            ExecutionStatus.SUCCESS,
            ExecutionStatus.FAILED,
            ExecutionStatus.ABORTED,
            ExecutionStatus.ROLLED_BACK,
        )


@dataclass
class ServiceArtifact:
    """Represents a specific artifact version for a service."""

    service: str
    artifact_tag: str
    description: str = ""
    created: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"ServiceArtifact({self.service!r} @ {self.artifact_tag!r})"


@dataclass
class ArtifactBundle:
    """Represents a Harness artifact bundle — a pinned set of service artifact versions."""

    id: str
    name: str
    project: str
    pipeline_id: str
    environment: str
    artifacts: list[ServiceArtifact] = field(default_factory=list)
    description: str = ""
    created: Optional[datetime] = None
    created_by: str = "automation"

    def __repr__(self) -> str:
        return (
            f"ArtifactBundle(id={self.id!r}, name={self.name!r}, "
            f"project={self.project!r})"
        )


@dataclass
class PipelineExecution:
    """Represents a Harness CD pipeline execution."""

    id: str
    project: str
    pipeline_id: str
    environment: str
    artifact_bundle: ArtifactBundle
    status: ExecutionStatus
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    submitted_by: str = "automation"
    log_url: str = ""

    def __repr__(self) -> str:
        return (
            f"PipelineExecution(id={self.id!r}, "
            f"project={self.project!r}, env={self.environment!r}, "
            f"status={self.status!r})"
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Return the execution duration in seconds, or ``None`` if not complete."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

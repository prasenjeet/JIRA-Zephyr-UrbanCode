"""UrbanCode Deploy data models using Python 3.10+ dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class DeploymentStatus(str, Enum):
    """Possible statuses for a UrbanCode deployment request."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"

    def __str__(self) -> str:  # noqa: D105
        return self.value

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` if the status is a terminal (final) state."""
        return self in (
            DeploymentStatus.SUCCEEDED,
            DeploymentStatus.FAILED,
            DeploymentStatus.CANCELLED,
            DeploymentStatus.ROLLED_BACK,
        )


@dataclass
class ComponentVersion:
    """Represents a specific version of a component."""

    component: str
    version: str
    description: str = ""
    created: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"ComponentVersion({self.component!r} @ {self.version!r})"


@dataclass
class Snapshot:
    """Represents an UrbanCode application snapshot (a set of component versions)."""

    id: str
    name: str
    application: str
    environment: str
    versions: list[ComponentVersion] = field(default_factory=list)
    description: str = ""
    created: Optional[datetime] = None
    created_by: str = "automation"

    def __repr__(self) -> str:
        return (
            f"Snapshot(id={self.id!r}, name={self.name!r}, "
            f"app={self.application!r})"
        )


@dataclass
class DeploymentRequest:
    """Represents a deployment request submitted to UrbanCode Deploy."""

    id: str
    application: str
    environment: str
    snapshot: Snapshot
    process: str
    status: DeploymentStatus
    submitted_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    submitted_by: str = "automation"
    log_url: str = ""

    def __repr__(self) -> str:
        return (
            f"DeploymentRequest(id={self.id!r}, "
            f"app={self.application!r}, env={self.environment!r}, "
            f"status={self.status!r})"
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Return the deployment duration in seconds, or ``None`` if not complete."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

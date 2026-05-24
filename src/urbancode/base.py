"""Abstract base class for UrbanCode Deploy clients."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .models import DeploymentRequest, DeploymentStatus, Snapshot


class BaseUrbanCodeClient(ABC):
    """Defines the interface all UrbanCode Deploy client implementations must satisfy."""

    @abstractmethod
    def create_snapshot(
        self,
        application: str | None = None,
        environment: str | None = None,
        name: str | None = None,
        description: str = "",
    ) -> Snapshot: ...

    @abstractmethod
    def request_deployment(
        self,
        application: str | None = None,
        environment: str | None = None,
        snapshot: Optional[Snapshot] = None,
        process: str = "Deploy",
    ) -> DeploymentRequest: ...

    @abstractmethod
    def get_deployment_status(self, request_id: str) -> DeploymentStatus: ...

    @abstractmethod
    def wait_for_deployment(
        self,
        request_id: str,
        timeout: int = 300,
        poll_interval: float = 2.0,
    ) -> DeploymentStatus: ...

    @abstractmethod
    def rollback_deployment(self, request_id: str) -> DeploymentRequest: ...

    @abstractmethod
    def get_environment_versions(
        self,
        application: str | None = None,
        environment: str | None = None,
    ) -> list[dict[str, Any]]: ...

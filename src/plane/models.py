"""Plane project management data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Issue:
    """Represents a Plane issue."""

    key: str
    name: str
    description: str
    state: str
    issue_type: str
    priority: str
    assignee: Optional[str]
    created_by: str
    created_at: datetime
    updated_at: datetime
    labels: list[str] = field(default_factory=list)
    linked_runs: list[str] = field(default_factory=list)
    comments: list["Comment"] = field(default_factory=list)
    fix_version: Optional[str] = None

    def __repr__(self) -> str:
        return f"Issue(key={self.key!r}, name={self.name!r}, state={self.state!r})"


@dataclass
class Comment:
    """Represents a comment on a Plane issue."""

    id: str
    body: str
    actor: str
    created_at: datetime
    updated_at: datetime

    def __repr__(self) -> str:
        return f"Comment(id={self.id!r}, actor={self.actor!r})"


@dataclass
class StateTransition:
    """Represents a Plane issue state change."""

    id: str
    name: str
    from_state: str
    to_state: str
    performed_at: datetime
    performed_by: str

    def __repr__(self) -> str:
        return (
            f"StateTransition(name={self.name!r}, "
            f"{self.from_state!r} -> {self.to_state!r})"
        )

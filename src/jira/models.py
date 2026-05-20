"""JIRA data models using Python 3.10+ dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Issue:
    """Represents a JIRA issue."""

    key: str
    summary: str
    description: str
    status: str
    issue_type: str
    priority: str
    assignee: Optional[str]
    reporter: str
    created: datetime
    updated: datetime
    labels: list[str] = field(default_factory=list)
    linked_cycles: list[str] = field(default_factory=list)
    comments: list["Comment"] = field(default_factory=list)
    fix_version: Optional[str] = None

    def __repr__(self) -> str:
        return f"Issue(key={self.key!r}, summary={self.summary!r}, status={self.status!r})"


@dataclass
class Comment:
    """Represents a comment on a JIRA issue."""

    id: str
    body: str
    author: str
    created: datetime
    updated: datetime

    def __repr__(self) -> str:
        return f"Comment(id={self.id!r}, author={self.author!r})"


@dataclass
class Transition:
    """Represents a JIRA issue status transition."""

    id: str
    name: str
    from_status: str
    to_status: str
    performed_at: datetime
    performed_by: str

    def __repr__(self) -> str:
        return (
            f"Transition(name={self.name!r}, "
            f"{self.from_status!r} -> {self.to_status!r})"
        )

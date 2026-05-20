"""Confluence data models using Python 3.10+ dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Page:
    """Represents a Confluence page."""

    id: str
    title: str
    content: str
    space_key: str
    version: int
    created: datetime
    updated: datetime
    author: str
    url: str
    parent_id: Optional[str] = None
    labels: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"Page(id={self.id!r}, title={self.title!r}, "
            f"space={self.space_key!r}, version={self.version})"
        )

"""Wiki.js data models using Python dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class WikiPage:
    """Represents a Wiki.js page."""

    id: int
    path: str
    title: str
    content: str
    locale: str
    description: str
    created: datetime
    updated: datetime
    author: str
    url: str
    tags: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"WikiPage(id={self.id!r}, title={self.title!r}, "
            f"path={self.path!r}, locale={self.locale!r})"
        )

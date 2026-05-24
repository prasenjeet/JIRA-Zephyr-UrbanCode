"""Abstract base class for JIRA clients."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import Comment, Issue, Transition


class BaseJiraClient(ABC):
    """Defines the interface all JIRA client implementations must satisfy."""

    @abstractmethod
    def get_issue(self, issue_key: str) -> Issue: ...

    @abstractmethod
    def create_issue(
        self,
        summary: str,
        description: str = "",
        issue_type: str = "Story",
        priority: str = "Medium",
        assignee: Optional[str] = None,
        labels: Optional[list[str]] = None,
        fix_version: Optional[str] = None,
    ) -> Issue: ...

    @abstractmethod
    def transition_issue(self, issue_key: str, status: str) -> Transition: ...

    @abstractmethod
    def add_comment(self, issue_key: str, comment: str) -> Comment: ...

    @abstractmethod
    def get_issues_by_status(self, status: str) -> list[Issue]: ...

    @abstractmethod
    def link_test_cycle(self, issue_key: str, cycle_id: str) -> None: ...

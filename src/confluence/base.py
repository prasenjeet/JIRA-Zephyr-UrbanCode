"""Abstract base class for Confluence clients."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .models import Page


class BaseConfluenceClient(ABC):
    """Defines the interface all Confluence client implementations must satisfy."""

    @abstractmethod
    def create_page(
        self,
        title: str,
        content: str,
        parent_id: Optional[str] = None,
        space_key: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> Page: ...

    @abstractmethod
    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        labels: Optional[list[str]] = None,
    ) -> Page: ...

    @abstractmethod
    def get_page(self, page_id: str) -> Page: ...

    @abstractmethod
    def get_pages_in_space(self, space_key: Optional[str] = None) -> list[Page]: ...

    @abstractmethod
    def create_test_report_page(
        self,
        title: str,
        test_results: list[dict[str, Any]],
        parent_id: Optional[str] = None,
        space_key: Optional[str] = None,
    ) -> Page: ...

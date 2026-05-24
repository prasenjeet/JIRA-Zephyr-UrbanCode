"""Abstract base class for Zephyr Scale clients."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import TestCase, TestCycle, TestResult, TestStatus


class BaseZephyrClient(ABC):
    """Defines the interface all Zephyr Scale client implementations must satisfy."""

    @abstractmethod
    def create_test_cycle(
        self,
        name: str,
        jira_issue_keys: list[str] | None = None,
        version: str = "Unversioned",
        project_key: str | None = None,
    ) -> TestCycle: ...

    @abstractmethod
    def get_test_cycle(self, cycle_id: str) -> TestCycle: ...

    @abstractmethod
    def add_test_cases(self, cycle_id: str, test_case_keys: list[str]) -> TestCycle: ...

    @abstractmethod
    def execute_test(
        self,
        cycle_id: str,
        test_case_key: str,
        status: TestStatus | str,
        comment: str = "",
        executed_by: str = "automation",
        duration_ms: int | None = None,
    ) -> TestResult: ...

    @abstractmethod
    def get_test_results(self, cycle_id: str) -> list[TestResult]: ...

    @abstractmethod
    def get_cycle_summary(self, cycle_id: str) -> dict[str, Any]: ...

    @abstractmethod
    def run_test_suite(
        self,
        cycle_id: str,
        pass_rate: float = 1.0,
    ) -> list[TestResult]: ...

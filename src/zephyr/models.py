"""Zephyr Scale data models using Python 3.10+ dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TestStatus(str, Enum):
    """Possible execution statuses for a test case."""

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    NOT_EXECUTED = "NOT_EXECUTED"
    IN_PROGRESS = "IN_PROGRESS"

    def __str__(self) -> str:  # noqa: D105
        return self.value


@dataclass
class TestCase:
    """Represents a single Zephyr test case definition."""

    key: str
    name: str
    description: str
    steps: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    priority: str = "Normal"
    folder: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"TestCase(key={self.key!r}, name={self.name!r})"


@dataclass
class TestResult:
    """Represents the execution result of a single test case within a cycle."""

    id: str
    test_case_key: str
    test_name: str
    status: TestStatus
    cycle_id: str
    comment: str = ""
    executed_by: str = "automation"
    executed_at: Optional[datetime] = None
    duration_ms: int = 0

    def __repr__(self) -> str:
        return (
            f"TestResult(test_case_key={self.test_case_key!r}, "
            f"status={self.status!r})"
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dict (useful for Confluence report generation)."""
        return {
            "test_case_key": self.test_case_key,
            "test_name": self.test_name,
            "status": str(self.status),
            "comment": self.comment,
            "executed_by": self.executed_by,
            "executed_at": self.executed_at.isoformat() if self.executed_at else "",
            "duration_ms": self.duration_ms,
        }


@dataclass
class TestCycle:
    """Represents a Zephyr test cycle (a collection of test executions)."""

    id: str
    name: str
    project_key: str
    version: str
    jira_issue_keys: list[str] = field(default_factory=list)
    test_case_keys: list[str] = field(default_factory=list)
    results: list[TestResult] = field(default_factory=list)
    status: str = "Active"
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    created_by: str = "automation"

    def __repr__(self) -> str:
        return (
            f"TestCycle(id={self.id!r}, name={self.name!r}, "
            f"status={self.status!r})"
        )

    @property
    def pass_count(self) -> int:
        """Number of passing test results in this cycle."""
        return sum(1 for r in self.results if r.status == TestStatus.PASS)

    @property
    def fail_count(self) -> int:
        """Number of failing test results in this cycle."""
        return sum(1 for r in self.results if r.status == TestStatus.FAIL)

    @property
    def total_count(self) -> int:
        """Total number of executed test results."""
        return len(self.results)

    @property
    def pass_rate(self) -> float:
        """Pass rate as a fraction between 0.0 and 1.0."""
        if self.total_count == 0:
            return 0.0
        return self.pass_count / self.total_count

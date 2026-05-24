"""Kiwi TCMS data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TestStatus(str, Enum):
    """Kiwi TCMS test execution statuses."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAIVED = "WAIVED"

    def __str__(self) -> str:
        return self.value


@dataclass
class TestCase:
    """Represents a Kiwi TCMS test case definition."""

    id: int
    summary: str
    text: str
    steps: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    priority: str = "P2"
    category: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __repr__(self) -> str:
        return f"TestCase(id={self.id!r}, summary={self.summary!r})"


@dataclass
class TestExecution:
    """Represents the execution result of a single test case within a test run."""

    id: int
    test_case_id: int
    test_case_key: str
    test_name: str
    status: TestStatus
    run_id: str
    comment: str = ""
    tested_by: str = "automation"
    tested_at: Optional[datetime] = None
    duration_ms: int = 0

    def __repr__(self) -> str:
        return (
            f"TestExecution(test_case_key={self.test_case_key!r}, "
            f"status={self.status!r})"
        )

    def to_dict(self) -> dict:
        """Serialize to a plain dict (for Wiki.js report generation)."""
        return {
            "test_case_key": self.test_case_key,
            "test_name": self.test_name,
            "status": str(self.status),
            "comment": self.comment,
            "executed_by": self.tested_by,
            "executed_at": self.tested_at.isoformat() if self.tested_at else "",
            "duration_ms": self.duration_ms,
        }


@dataclass
class TestRun:
    """Represents a Kiwi TCMS test run (a set of test case executions)."""

    id: str
    summary: str
    product: str
    version: str
    plane_issue_keys: list[str] = field(default_factory=list)
    test_case_keys: list[str] = field(default_factory=list)
    executions: list[TestExecution] = field(default_factory=list)
    status: str = "RUNNING"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    manager: str = "automation"

    def __repr__(self) -> str:
        return (
            f"TestRun(id={self.id!r}, summary={self.summary!r}, "
            f"status={self.status!r})"
        )

    @property
    def pass_count(self) -> int:
        return sum(1 for e in self.executions if e.status == TestStatus.PASSED)

    @property
    def fail_count(self) -> int:
        return sum(1 for e in self.executions if e.status == TestStatus.FAILED)

    @property
    def total_count(self) -> int:
        return len(self.executions)

    @property
    def pass_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.pass_count / self.total_count

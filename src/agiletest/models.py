"""AgileTest data models using Python 3.10+ dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TestStatus(str, Enum):
    """Possible execution statuses for an AgileTest test execution."""

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    UNEXECUTED = "UNEXECUTED"
    IN_PROGRESS = "IN_PROGRESS"

    def __str__(self) -> str:  # noqa: D105
        return self.value


@dataclass
class TestCase:
    """Represents a single AgileTest test case (backed by a JIRA issue of type Test)."""

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
class TestExecution:
    """Represents the execution result of a single test case within a test plan."""

    id: str
    test_case_key: str
    test_name: str
    status: TestStatus
    plan_id: str
    comment: str = ""
    executed_by: str = "automation"
    executed_at: Optional[datetime] = None
    duration_ms: int = 0

    def __repr__(self) -> str:
        return (
            f"TestExecution(test_case_key={self.test_case_key!r}, "
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
class TestPlan:
    """Represents an AgileTest test plan — a collection of test cases to be executed."""

    id: str
    name: str
    project_key: str
    version: str
    jira_issue_keys: list[str] = field(default_factory=list)
    test_case_keys: list[str] = field(default_factory=list)
    executions: list[TestExecution] = field(default_factory=list)
    status: str = "Active"
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    created_by: str = "automation"

    def __repr__(self) -> str:
        return (
            f"TestPlan(id={self.id!r}, name={self.name!r}, "
            f"status={self.status!r})"
        )

    @property
    def pass_count(self) -> int:
        """Number of passing executions in this plan."""
        return sum(1 for e in self.executions if e.status == TestStatus.PASS)

    @property
    def fail_count(self) -> int:
        """Number of failing executions in this plan."""
        return sum(1 for e in self.executions if e.status == TestStatus.FAIL)

    @property
    def total_count(self) -> int:
        """Total number of recorded executions."""
        return len(self.executions)

    @property
    def pass_rate(self) -> float:
        """Pass rate as a fraction between 0.0 and 1.0."""
        if self.total_count == 0:
            return 0.0
        return self.pass_count / self.total_count

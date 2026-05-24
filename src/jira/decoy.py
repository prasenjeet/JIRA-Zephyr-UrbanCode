"""JIRA Decoy Client - simulates the JIRA REST API without real credentials.

All methods print "[JIRA DECOY]" prefixed messages and return realistic mock data.
Simulated network latency of ~100ms is included via time.sleep(0.1).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from .base import BaseJiraClient
from .models import Comment, Issue, Transition

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ISSUE_COUNTER: dict[str, int] = {}

_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "Open": ["In Dev", "Closed"],
    "In Dev": ["Ready for QA", "Open"],
    "Ready for QA": ["In QA", "In Dev"],
    "In QA": ["Deployed", "In Dev"],
    "Deployed": ["Closed"],
    "Closed": [],
}

_MOCK_USERS = ["alice@example.com", "bob@example.com", "carol@example.com"]

_PRIORITIES = ["Highest", "High", "Medium", "Low", "Lowest"]

_SAMPLE_ISSUES: dict[str, Issue] = {}


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _next_issue_key(project_key: str) -> str:
    _ISSUE_COUNTER[project_key] = _ISSUE_COUNTER.get(project_key, 100) + 1
    return f"{project_key}-{_ISSUE_COUNTER[project_key]}"


def _short_id() -> str:
    return uuid.uuid4().hex[:8].upper()


# ---------------------------------------------------------------------------
# DecoyJiraClient
# ---------------------------------------------------------------------------


class DecoyJiraClient(BaseJiraClient):
    """Decoy JIRA client that simulates the JIRA REST API.

    All operations are performed in-memory.

    Args:
        base_url: JIRA instance base URL (e.g. ``https://org.atlassian.net``).
        username: Atlassian account email.
        api_token: Atlassian API token.
        project_key: Default project key (e.g. ``"DEMO"``).
    """

    def __init__(
        self,
        base_url: str = "https://your-org.atlassian.net",
        username: str = "decoy@example.com",
        api_token: str = "decoy-token",
        project_key: str = "DEMO",
        **kwargs,
    ) -> None:
        self.base_url = base_url
        self.username = username
        self.api_token = api_token
        self.project_key = project_key
        self.use_decoy = True

        # In-memory store shared across this client instance
        self._issues: dict[str, Issue] = {}
        self._transitions: list[Transition] = []

        self._log("DecoyJiraClient initialised.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        print(f"[JIRA DECOY] {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_issue(self, issue_key: str) -> Issue:
        """Fetch a JIRA issue by key.

        Args:
            issue_key: Issue key such as ``"DEMO-101"``.

        Returns:
            :class:`Issue` dataclass populated with mock data.

        Raises:
            KeyError: If the issue does not exist in the decoy store.
        """
        self._simulate_latency()
        self._log(f"GET /rest/api/3/issue/{issue_key}")

        if issue_key not in self._issues:
            # Auto-create a plausible issue on first fetch
            issue = Issue(
                key=issue_key,
                summary=f"[Auto-created] Feature work for {issue_key}",
                description="This issue was auto-created by the decoy client on first fetch.",
                status="Open",
                issue_type="Story",
                priority="Medium",
                assignee=_MOCK_USERS[0],
                reporter=_MOCK_USERS[1],
                created=_now(),
                updated=_now(),
                labels=["decoy", "auto-created"],
            )
            self._issues[issue_key] = issue
            self._log(f"  -> Auto-created issue {issue_key} (not found in store).")

        issue = self._issues[issue_key]
        self._log(f"  -> Returning {issue!r}")
        return issue

    def create_issue(
        self,
        summary: str,
        description: str = "",
        issue_type: str = "Story",
        priority: str = "Medium",
        assignee: Optional[str] = None,
        labels: Optional[list[str]] = None,
        fix_version: Optional[str] = None,
    ) -> Issue:
        """Create a new JIRA issue.

        Args:
            summary: One-line summary of the issue.
            description: Detailed description (plain text or ADF).
            issue_type: JIRA issue type (Story, Bug, Task, Epic, …).
            priority: Priority level.
            assignee: Assignee email address.
            labels: List of label strings.
            fix_version: Target fix version string.

        Returns:
            Newly created :class:`Issue`.
        """
        self._simulate_latency()
        key = _next_issue_key(self.project_key)
        self._log(f"POST /rest/api/3/issue  ->  {key}")
        self._log(f"  summary   : {summary}")
        self._log(f"  type      : {issue_type}  priority: {priority}")

        issue = Issue(
            key=key,
            summary=summary,
            description=description,
            status="Open",
            issue_type=issue_type,
            priority=priority,
            assignee=assignee or _MOCK_USERS[0],
            reporter=self.username,
            created=_now(),
            updated=_now(),
            labels=labels or [],
            fix_version=fix_version,
        )
        self._issues[key] = issue
        self._log(f"  -> Created {issue!r}")
        return issue

    def transition_issue(self, issue_key: str, status: str) -> Transition:
        """Transition a JIRA issue to a new status.

        Args:
            issue_key: The issue to transition.
            status: Target status name.

        Returns:
            :class:`Transition` record describing the state change.

        Raises:
            KeyError: If the issue is not found.
            ValueError: If the transition is not valid from the current status.
        """
        self._simulate_latency()
        self._log(f"POST /rest/api/3/issue/{issue_key}/transitions  ->  {status!r}")

        issue = self.get_issue(issue_key)
        from_status = issue.status

        allowed = _STATUS_TRANSITIONS.get(from_status, [])
        if status not in allowed:
            # In decoy mode we allow the transition anyway but warn
            self._log(
                f"  [WARN] Transition {from_status!r} -> {status!r} not in "
                f"allowed list {allowed}. Forcing (decoy)."
            )

        transition = Transition(
            id=_short_id(),
            name=f"{from_status} -> {status}",
            from_status=from_status,
            to_status=status,
            performed_at=_now(),
            performed_by=self.username,
        )
        issue.status = status
        issue.updated = _now()
        self._transitions.append(transition)
        self._log(f"  -> Transitioned {issue_key}: {from_status!r} -> {status!r}")
        return transition

    def add_comment(self, issue_key: str, comment: str) -> Comment:
        """Add a comment to a JIRA issue.

        Args:
            issue_key: Target issue key.
            comment: Comment body text.

        Returns:
            Newly created :class:`Comment`.
        """
        self._simulate_latency()
        self._log(f"POST /rest/api/3/issue/{issue_key}/comment")
        self._log(f"  body (first 80 chars): {comment[:80]!r}")

        issue = self.get_issue(issue_key)
        c = Comment(
            id=_short_id(),
            body=comment,
            author=self.username,
            created=_now(),
            updated=_now(),
        )
        issue.comments.append(c)
        self._log(f"  -> Added comment {c.id} to {issue_key}")
        return c

    def get_issues_by_status(self, status: str) -> list[Issue]:
        """Return all issues in the given status.

        Args:
            status: Status name to filter by.

        Returns:
            List of :class:`Issue` objects.
        """
        self._simulate_latency()
        self._log(f"GET /rest/api/3/search?jql=status={status!r}")

        results = [i for i in self._issues.values() if i.status == status]

        # Seed a couple of dummy issues if the store is empty for realism
        if not results and not self._issues:
            for n in range(1, 4):
                key = f"{self.project_key}-{n}"
                seed = Issue(
                    key=key,
                    summary=f"Sample issue #{n} in status {status}",
                    description="Seeded by decoy client.",
                    status=status,
                    issue_type="Story",
                    priority=_PRIORITIES[n % len(_PRIORITIES)],
                    assignee=_MOCK_USERS[n % len(_MOCK_USERS)],
                    reporter=_MOCK_USERS[0],
                    created=_now(),
                    updated=_now(),
                )
                self._issues[key] = seed
                results.append(seed)

        self._log(f"  -> Found {len(results)} issue(s) with status {status!r}")
        return results

    def link_test_cycle(self, issue_key: str, cycle_id: str) -> None:
        """Link a Zephyr test cycle to a JIRA issue.

        Stores the cycle ID in the issue's ``linked_cycles`` list.

        Args:
            issue_key: JIRA issue key.
            cycle_id: Zephyr test cycle identifier.
        """
        self._simulate_latency()
        self._log(
            f"POST /rest/api/3/issue/{issue_key}/remotelink  "
            f"(Zephyr cycle {cycle_id})"
        )

        issue = self.get_issue(issue_key)
        if cycle_id not in issue.linked_cycles:
            issue.linked_cycles.append(cycle_id)
            issue.updated = _now()

        self._log(f"  -> Linked cycle {cycle_id} to {issue_key}")

"""Plane Decoy Client - simulates the Plane REST API without real credentials.

All methods print "[PLANE DECOY]" prefixed messages and return realistic mock data.
Simulated network latency of ~100ms is included via time.sleep(0.1).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from .models import Comment, Issue, StateTransition

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ISSUE_COUNTER: dict[str, int] = {}

_STATE_TRANSITIONS: dict[str, list[str]] = {
    "Open": ["In Dev", "Closed"],
    "In Dev": ["Ready for QA", "Open"],
    "Ready for QA": ["In QA", "In Dev"],
    "In QA": ["Deployed", "In Dev"],
    "Deployed": ["Closed"],
    "Closed": [],
}

_MOCK_USERS = ["alice@example.com", "bob@example.com", "carol@example.com"]
_PRIORITIES = ["urgent", "high", "medium", "low", "none"]


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _short_id() -> str:
    return uuid.uuid4().hex[:8].upper()


def _next_issue_key(project_identifier: str) -> str:
    _ISSUE_COUNTER[project_identifier] = (
        _ISSUE_COUNTER.get(project_identifier, 100) + 1
    )
    return f"{project_identifier}-{_ISSUE_COUNTER[project_identifier]}"


# ---------------------------------------------------------------------------
# PlaneClient
# ---------------------------------------------------------------------------


class PlaneClient:
    """Decoy Plane client that simulates the Plane REST API.

    All operations are performed in-memory.

    Args:
        base_url: Plane instance base URL (e.g. ``https://app.plane.so``).
        api_token: Plane API token.
        workspace_slug: Plane workspace slug.
        project_id: Default Plane project UUID (or identifier string).
        project_identifier: Short project code used in issue keys (e.g. ``"DEMO"``).
        use_decoy: When ``True`` all methods use in-memory mock data.
    """

    def __init__(
        self,
        base_url: str = "https://app.plane.so",
        api_token: str = "decoy-plane-token",
        workspace_slug: str = "my-workspace",
        project_id: str = "demo-project",
        project_identifier: str = "DEMO",
        use_decoy: bool = True,
    ) -> None:
        self.base_url = base_url
        self.api_token = api_token
        self.workspace_slug = workspace_slug
        self.project_id = project_id
        self.project_identifier = project_identifier
        self.use_decoy = use_decoy

        self._issues: dict[str, Issue] = {}
        self._transitions: list[StateTransition] = []

        self._log("PlaneClient initialised (decoy mode).")

    def _log(self, message: str) -> None:
        print(f"[PLANE DECOY] {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

    def _api(self, method: str, path: str) -> str:
        return (
            f"{method} /api/v1/workspaces/{self.workspace_slug}"
            f"/projects/{self.project_id}{path}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_issue(self, issue_key: str) -> Issue:
        """Fetch a Plane issue by key (e.g. ``"DEMO-101"``).

        Auto-creates a plausible issue on first fetch if not found.

        Args:
            issue_key: Issue key such as ``"DEMO-101"``.

        Returns:
            :class:`Issue` from the decoy store.
        """
        self._simulate_latency()
        self._log(self._api("GET", f"/issues/{issue_key}/"))

        if issue_key not in self._issues:
            issue = Issue(
                key=issue_key,
                name=f"[Auto-created] Feature work for {issue_key}",
                description="Auto-created by the Plane decoy client on first fetch.",
                state="Open",
                issue_type="Feature",
                priority="medium",
                assignee=_MOCK_USERS[0],
                created_by=_MOCK_USERS[1],
                created_at=_now(),
                updated_at=_now(),
                labels=["decoy", "auto-created"],
            )
            self._issues[issue_key] = issue
            self._log(f"  -> Auto-created issue {issue_key} (not found in store).")

        issue = self._issues[issue_key]
        self._log(f"  -> Returning {issue!r}")
        return issue

    def create_issue(
        self,
        name: str,
        description: str = "",
        issue_type: str = "Feature",
        priority: str = "medium",
        assignee: Optional[str] = None,
        labels: Optional[list[str]] = None,
        fix_version: Optional[str] = None,
    ) -> Issue:
        """Create a new Plane issue.

        Args:
            name: One-line issue name / title.
            description: Detailed description.
            issue_type: Issue type (Feature, Bug, Improvement, …).
            priority: Priority level (urgent/high/medium/low/none).
            assignee: Assignee email address.
            labels: List of label strings.
            fix_version: Target release version string.

        Returns:
            Newly created :class:`Issue`.
        """
        self._simulate_latency()
        key = _next_issue_key(self.project_identifier)
        self._log(self._api("POST", "/issues/") + f"  ->  {key}")
        self._log(f"  name      : {name}")
        self._log(f"  type      : {issue_type}  priority: {priority}")

        issue = Issue(
            key=key,
            name=name,
            description=description,
            state="Open",
            issue_type=issue_type,
            priority=priority,
            assignee=assignee or _MOCK_USERS[0],
            created_by=self.api_token[:8],
            created_at=_now(),
            updated_at=_now(),
            labels=labels or [],
            fix_version=fix_version,
        )
        self._issues[key] = issue
        self._log(f"  -> Created {issue!r}")
        return issue

    def transition_issue(self, issue_key: str, state: str) -> StateTransition:
        """Transition a Plane issue to a new state.

        Args:
            issue_key: The issue to transition.
            state: Target state name.

        Returns:
            :class:`StateTransition` record describing the state change.

        Raises:
            KeyError: If the issue is not found.
        """
        self._simulate_latency()
        self._log(self._api("PATCH", f"/issues/{issue_key}/") + f"  state={state!r}")

        issue = self.get_issue(issue_key)
        from_state = issue.state

        allowed = _STATE_TRANSITIONS.get(from_state, [])
        if state not in allowed:
            self._log(
                f"  [WARN] Transition {from_state!r} -> {state!r} not in "
                f"allowed list {allowed}. Forcing (decoy)."
            )

        transition = StateTransition(
            id=_short_id(),
            name=f"{from_state} -> {state}",
            from_state=from_state,
            to_state=state,
            performed_at=_now(),
            performed_by=self.api_token[:8],
        )
        issue.state = state
        issue.updated_at = _now()
        self._transitions.append(transition)
        self._log(f"  -> Transitioned {issue_key}: {from_state!r} -> {state!r}")
        return transition

    def add_comment(self, issue_key: str, comment: str) -> Comment:
        """Add a comment to a Plane issue.

        Args:
            issue_key: Target issue key.
            comment: Comment body text.

        Returns:
            Newly created :class:`Comment`.
        """
        self._simulate_latency()
        self._log(self._api("POST", f"/issues/{issue_key}/comments/"))
        self._log(f"  body (first 80 chars): {comment[:80]!r}")

        issue = self.get_issue(issue_key)
        c = Comment(
            id=_short_id(),
            body=comment,
            actor=self.api_token[:8],
            created_at=_now(),
            updated_at=_now(),
        )
        issue.comments.append(c)
        self._log(f"  -> Added comment {c.id} to {issue_key}")
        return c

    def get_issues_by_state(self, state: str) -> list[Issue]:
        """Return all issues in the given state.

        Args:
            state: State name to filter by.

        Returns:
            List of :class:`Issue` objects.
        """
        self._simulate_latency()
        self._log(self._api("GET", f"/issues/?state={state!r}"))

        results = [i for i in self._issues.values() if i.state == state]

        if not results and not self._issues:
            for n in range(1, 4):
                key = f"{self.project_identifier}-{n}"
                seed = Issue(
                    key=key,
                    name=f"Sample issue #{n} in state {state}",
                    description="Seeded by Plane decoy client.",
                    state=state,
                    issue_type="Feature",
                    priority=_PRIORITIES[n % len(_PRIORITIES)],
                    assignee=_MOCK_USERS[n % len(_MOCK_USERS)],
                    created_by=_MOCK_USERS[0],
                    created_at=_now(),
                    updated_at=_now(),
                )
                self._issues[key] = seed
                results.append(seed)

        self._log(f"  -> Found {len(results)} issue(s) with state {state!r}")
        return results

    def link_test_run(self, issue_key: str, run_id: str) -> None:
        """Link a Kiwi TCMS test run to a Plane issue.

        Stores the run ID in the issue's ``linked_runs`` list.

        Args:
            issue_key: Plane issue key.
            run_id: Kiwi TCMS test run identifier.
        """
        self._simulate_latency()
        self._log(
            self._api("POST", f"/issues/{issue_key}/external-links/")
            + f"  (Kiwi run {run_id})"
        )

        issue = self.get_issue(issue_key)
        if run_id not in issue.linked_runs:
            issue.linked_runs.append(run_id)
            issue.updated_at = _now()

        self._log(f"  -> Linked run {run_id} to {issue_key}")

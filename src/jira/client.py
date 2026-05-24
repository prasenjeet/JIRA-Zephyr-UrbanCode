"""JIRA Client - supports both real REST API and in-memory decoy mode.

Set use_decoy=True (default) for zero-credential simulation.
Set use_decoy=False to hit the real JIRA Cloud REST API v3.
"""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import requests

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


def _parse_dt(s: str) -> datetime:
    """Parse ISO 8601 string (including +0000 and Z variants) to aware datetime."""
    s = re.sub(r"Z$", "+00:00", s)
    s = re.sub(r"([+-])(\d{2})(\d{2})$", r"\1\2:\3", s)
    return datetime.fromisoformat(s)


def _plain_to_adf(text: str) -> dict:
    """Wrap plain text in Atlassian Document Format."""
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}],
    }


# ---------------------------------------------------------------------------
# JiraClient
# ---------------------------------------------------------------------------


class JiraClient:
    """JIRA client supporting real REST API and in-memory decoy mode.

    Args:
        base_url: JIRA instance base URL (e.g. ``https://org.atlassian.net``).
        username: Atlassian account email.
        api_token: Atlassian API token.
        project_key: Default project key (e.g. ``"DEMO"``).
        use_decoy: ``True`` → in-memory simulation; ``False`` → real HTTP calls.
    """

    def __init__(
        self,
        base_url: str = "https://your-org.atlassian.net",
        username: str = "decoy@example.com",
        api_token: str = "decoy-token",
        project_key: str = "DEMO",
        use_decoy: bool = True,
    ) -> None:
        self.base_url = base_url
        self.username = username
        self.api_token = api_token
        self.project_key = project_key
        self.use_decoy = use_decoy

        self._issues: dict[str, Issue] = {}
        self._transitions: list[Transition] = []

        self._session: requests.Session | None = None
        if not use_decoy:
            self._session = requests.Session()
            self._session.auth = (username, api_token)
            self._session.headers.update(
                {"Accept": "application/json", "Content-Type": "application/json"}
            )

        self._log("JiraClient initialised (decoy mode)." if use_decoy else "JiraClient initialised (live mode).")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        prefix = "[JIRA DECOY]" if self.use_decoy else "[JIRA]"
        print(f"{prefix} {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

    def _api(self, path: str) -> str:
        return f"{self.base_url}/rest/api/3/{path}"

    def _parse_issue(self, data: dict) -> Issue:
        fields = data["fields"]
        assignee = fields.get("assignee")
        fix_versions = fields.get("fixVersions", [])
        desc = fields.get("description") or ""
        if isinstance(desc, dict):
            texts: list[str] = []
            for block in desc.get("content", []):
                for node in block.get("content", []):
                    if node.get("type") == "text":
                        texts.append(node.get("text", ""))
            desc = " ".join(texts)
        return Issue(
            key=data["key"],
            summary=fields["summary"],
            description=desc,
            status=fields["status"]["name"],
            issue_type=fields["issuetype"]["name"],
            priority=(fields.get("priority") or {}).get("name", "Medium"),
            assignee=assignee["emailAddress"] if assignee else None,
            reporter=fields["reporter"]["emailAddress"],
            created=_parse_dt(fields["created"]),
            updated=_parse_dt(fields["updated"]),
            labels=fields.get("labels", []),
            fix_version=fix_versions[0]["name"] if fix_versions else None,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_issue(self, issue_key: str) -> Issue:
        """Fetch a JIRA issue by key.

        Args:
            issue_key: Issue key such as ``"DEMO-101"``.

        Returns:
            :class:`Issue` dataclass.

        Raises:
            KeyError: (decoy) If the issue does not exist in the decoy store.
            requests.HTTPError: (live) On non-2xx response.
        """
        if not self.use_decoy:
            assert self._session is not None
            self._log(f"GET {self._api(f'issue/{issue_key}')}")
            resp = self._session.get(self._api(f"issue/{issue_key}"))
            resp.raise_for_status()
            issue = self._parse_issue(resp.json())
            self._log(f"  -> {issue!r}")
            return issue

        self._simulate_latency()
        self._log(f"GET /rest/api/3/issue/{issue_key}")

        if issue_key not in self._issues:
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
            description: Detailed description (plain text).
            issue_type: JIRA issue type (Story, Bug, Task, Epic, …).
            priority: Priority level.
            assignee: Assignee email address.
            labels: List of label strings.
            fix_version: Target fix version string.

        Returns:
            Newly created :class:`Issue`.
        """
        if not self.use_decoy:
            assert self._session is not None
            body: dict = {
                "fields": {
                    "project": {"key": self.project_key},
                    "summary": summary,
                    "issuetype": {"name": issue_type},
                    "priority": {"name": priority},
                    "labels": labels or [],
                }
            }
            if description:
                body["fields"]["description"] = _plain_to_adf(description)
            if fix_version:
                body["fields"]["fixVersions"] = [{"name": fix_version}]
            if assignee:
                body["fields"]["assignee"] = {"emailAddress": assignee}

            self._log(f"POST {self._api('issue')}")
            self._log(f"  summary: {summary!r}  type: {issue_type}  priority: {priority}")
            resp = self._session.post(self._api("issue"), json=body)
            resp.raise_for_status()
            key = resp.json()["key"]
            self._log(f"  -> Created {key}")
            return self.get_issue(key)

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
        """
        if not self.use_decoy:
            assert self._session is not None
            self._log(f"GET {self._api(f'issue/{issue_key}/transitions')}")
            resp = self._session.get(self._api(f"issue/{issue_key}/transitions"))
            resp.raise_for_status()
            transitions = resp.json()["transitions"]

            transition_id = None
            for t in transitions:
                if t["to"]["name"].lower() == status.lower():
                    transition_id = t["id"]
                    break

            if not transition_id:
                available = [(t["name"], t["to"]["name"]) for t in transitions]
                raise ValueError(
                    f"No transition to {status!r} found. Available: {available}"
                )

            issue = self.get_issue(issue_key)
            from_status = issue.status

            self._log(f"POST {self._api(f'issue/{issue_key}/transitions')}  ->  {status!r}")
            resp = self._session.post(
                self._api(f"issue/{issue_key}/transitions"),
                json={"transition": {"id": transition_id}},
            )
            resp.raise_for_status()
            self._log(f"  -> Transitioned {issue_key}: {from_status!r} -> {status!r}")
            return Transition(
                id=transition_id,
                name=f"{from_status} -> {status}",
                from_status=from_status,
                to_status=status,
                performed_at=_now(),
                performed_by=self.username,
            )

        self._simulate_latency()
        self._log(f"POST /rest/api/3/issue/{issue_key}/transitions  ->  {status!r}")

        issue = self.get_issue(issue_key)
        from_status = issue.status

        allowed = _STATUS_TRANSITIONS.get(from_status, [])
        if status not in allowed:
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
        if not self.use_decoy:
            assert self._session is not None
            self._log(f"POST {self._api(f'issue/{issue_key}/comment')}")
            self._log(f"  body (first 80 chars): {comment[:80]!r}")
            resp = self._session.post(
                self._api(f"issue/{issue_key}/comment"),
                json={"body": _plain_to_adf(comment)},
            )
            resp.raise_for_status()
            data = resp.json()
            c = Comment(
                id=data["id"],
                body=comment,
                author=data["author"]["emailAddress"],
                created=_parse_dt(data["created"]),
                updated=_parse_dt(data["updated"]),
            )
            self._log(f"  -> Added comment {c.id}")
            return c

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
        if not self.use_decoy:
            assert self._session is not None
            jql = f'project = "{self.project_key}" AND status = "{status}"'
            self._log(f"GET {self._api('search')}?jql={jql!r}")
            resp = self._session.get(
                self._api("search"), params={"jql": jql, "maxResults": 50}
            )
            resp.raise_for_status()
            issues = [self._parse_issue(i) for i in resp.json()["issues"]]
            self._log(f"  -> Found {len(issues)} issue(s) with status {status!r}")
            return issues

        self._simulate_latency()
        self._log(f"GET /rest/api/3/search?jql=status={status!r}")

        results = [i for i in self._issues.values() if i.status == status]

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
        """Link an AgileTest test plan to a JIRA issue.

        Args:
            issue_key: JIRA issue key.
            cycle_id: AgileTest test plan identifier.
        """
        if not self.use_decoy:
            assert self._session is not None
            self._log(
                f"POST {self._api(f'issue/{issue_key}/remotelink')}  "
                f"(AgileTest plan {cycle_id})"
            )
            body = {
                "object": {
                    "url": f"{self.base_url}/rest/agiletest/1.0/testplan/{cycle_id}",
                    "title": f"AgileTest Test Plan {cycle_id}",
                }
            }
            resp = self._session.post(
                self._api(f"issue/{issue_key}/remotelink"), json=body
            )
            resp.raise_for_status()
            self._log(f"  -> Linked plan {cycle_id} to {issue_key}")
            return

        self._simulate_latency()
        self._log(
            f"POST /rest/api/3/issue/{issue_key}/remotelink  "
            f"(AgileTest plan {cycle_id})"
        )

        issue = self.get_issue(issue_key)
        if cycle_id not in issue.linked_cycles:
            issue.linked_cycles.append(cycle_id)
            issue.updated = _now()

        self._log(f"  -> Linked cycle {cycle_id} to {issue_key}")

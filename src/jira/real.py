"""Real JIRA client — makes actual HTTP calls to the JIRA REST API v3.

Authentication uses HTTP Basic Auth with an Atlassian account email and API token.
See: https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, Any

import requests
from requests.auth import HTTPBasicAuth

from src.exceptions import APIError, AuthenticationError, NotFoundError, TransitionError
from .base import BaseJiraClient
from .models import Comment, Issue, Transition


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_datetime(s: str | None) -> datetime:
    """Parse a JIRA ISO-8601 datetime string to a timezone-aware datetime."""
    if not s:
        return _now()
    # JIRA returns "2024-01-15T10:30:00.000+0000" — normalize to +00:00
    s = s.replace("+0000", "+00:00").replace(".000+00:00", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return _now()


def _extract_adf_text(adf: dict | None) -> str:
    """Recursively extract plain text from an Atlassian Document Format (ADF) node."""
    if not adf:
        return ""
    if adf.get("type") == "text":
        return adf.get("text", "")
    return " ".join(_extract_adf_text(c) for c in adf.get("content", []))


def _parse_issue(data: dict) -> Issue:
    """Map a JIRA REST API issue dict to an :class:`Issue` dataclass."""
    fields = data["fields"]
    assignee_obj = fields.get("assignee") or {}
    reporter_obj = fields.get("reporter") or {}
    priority_obj = fields.get("priority") or {}
    fix_versions = fields.get("fixVersions") or []

    return Issue(
        key=data["key"],
        summary=fields.get("summary", ""),
        description=_extract_adf_text(fields.get("description")),
        status=fields["status"]["name"],
        issue_type=fields["issuetype"]["name"],
        priority=priority_obj.get("name", "None"),
        assignee=assignee_obj.get("emailAddress"),
        reporter=reporter_obj.get("emailAddress", "unknown"),
        created=_parse_datetime(fields.get("created")),
        updated=_parse_datetime(fields.get("updated")),
        labels=fields.get("labels") or [],
        fix_version=fix_versions[0]["name"] if fix_versions else None,
    )


def _text_to_adf(text: str) -> dict:
    """Convert a plain-text string to minimal Atlassian Document Format."""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


class RealJiraClient(BaseJiraClient):
    """Real JIRA client that calls the Atlassian JIRA REST API v3.

    Args:
        base_url: JIRA Cloud base URL, e.g. ``https://yourorg.atlassian.net``.
        username: Atlassian account email address.
        api_token: Atlassian API token (generate at id.atlassian.com).
        project_key: Default project key used when creating issues.
        verify_ssl: Set to ``False`` to skip TLS verification (not recommended).
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        project_key: str = "DEMO",
        verify_ssl: bool = True,
        **kwargs,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.project_key = project_key
        self.use_decoy = False  # always real

        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(username, api_token)
        self._session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )
        self._session.verify = verify_ssl

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _api(self, method: str, path: str, **kwargs: Any) -> dict:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.request(method, url, **kwargs)
        except requests.ConnectionError as exc:
            raise APIError(f"Connection failed to {url}: {exc}") from exc

        if resp.status_code == 401:
            raise AuthenticationError("JIRA authentication failed — check username and api_token.")
        if resp.status_code == 404:
            raise NotFoundError(f"JIRA resource not found: {path}")

        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise APIError(
                str(exc), status_code=resp.status_code, response_body=resp.text
            ) from exc

        return resp.json() if resp.content else {}

    def _log(self, message: str) -> None:
        print(f"[JIRA REAL] {message}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_issue(self, issue_key: str) -> Issue:
        """Fetch a JIRA issue by key from the live API."""
        self._log(f"GET /rest/api/3/issue/{issue_key}")
        data = self._api("GET", f"/rest/api/3/issue/{issue_key}")
        issue = _parse_issue(data)
        self._log(f"  -> {issue!r}")
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
        """Create a new issue in JIRA."""
        self._log(f"POST /rest/api/3/issue  summary={summary!r}")
        fields: dict[str, Any] = {
            "project": {"key": self.project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
            "labels": labels or [],
        }
        if description:
            fields["description"] = _text_to_adf(description)
        if assignee:
            fields["assignee"] = {"emailAddress": assignee}
        if fix_version:
            fields["fixVersions"] = [{"name": fix_version}]

        data = self._api("POST", "/rest/api/3/issue", json={"fields": fields})
        # POST returns only id+key; fetch the full issue
        return self.get_issue(data["key"])

    def transition_issue(self, issue_key: str, status: str) -> Transition:
        """Transition a JIRA issue to the named status."""
        self._log(f"POST /rest/api/3/issue/{issue_key}/transitions  target={status!r}")

        # Resolve current status for the Transition record
        current_issue = self.get_issue(issue_key)
        from_status = current_issue.status

        # Fetch available transitions
        trans_data = self._api("GET", f"/rest/api/3/issue/{issue_key}/transitions")
        transitions = trans_data.get("transitions", [])

        transition_id: Optional[str] = None
        for t in transitions:
            if t["to"]["name"].lower() == status.lower():
                transition_id = t["id"]
                break

        if transition_id is None:
            available = [t["to"]["name"] for t in transitions]
            raise TransitionError(
                f"No transition to '{status}' found for {issue_key}. "
                f"Available: {available}"
            )

        self._api(
            "POST",
            f"/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}},
        )

        self._log(f"  -> Transitioned {issue_key}: {from_status!r} -> {status!r}")
        return Transition(
            id=transition_id,
            name=f"{from_status} -> {status}",
            from_status=from_status,
            to_status=status,
            performed_at=_now(),
            performed_by=self.username,
        )

    def add_comment(self, issue_key: str, comment: str) -> Comment:
        """Add a comment to a JIRA issue."""
        self._log(f"POST /rest/api/3/issue/{issue_key}/comment")
        payload = {"body": _text_to_adf(comment)}
        data = self._api("POST", f"/rest/api/3/issue/{issue_key}/comment", json=payload)
        return Comment(
            id=data["id"],
            body=comment,
            author=data.get("author", {}).get("emailAddress", "unknown"),
            created=_parse_datetime(data.get("created")),
            updated=_parse_datetime(data.get("updated")),
        )

    def get_issues_by_status(self, status: str) -> list[Issue]:
        """Search for issues in the given status via JQL."""
        jql = f'project = "{self.project_key}" AND status = "{status}" ORDER BY created DESC'
        self._log(f"GET /rest/api/3/search  jql={jql!r}")
        data = self._api("GET", "/rest/api/3/search", params={"jql": jql, "maxResults": 50})
        issues = [_parse_issue(item) for item in data.get("issues", [])]
        self._log(f"  -> {len(issues)} issue(s) in status {status!r}")
        return issues

    def link_test_cycle(self, issue_key: str, cycle_id: str) -> None:
        """Attach a Zephyr test cycle remote link to a JIRA issue."""
        self._log(f"POST /rest/api/3/issue/{issue_key}/remotelink  cycle={cycle_id!r}")
        payload = {
            "object": {
                "url": f"https://zephyrscale.smartbear.com/testcycles/{cycle_id}",
                "title": f"Zephyr Test Cycle: {cycle_id}",
                "icon": {
                    "url16x16": "https://zephyrscale.smartbear.com/favicon.ico",
                    "title": "Zephyr Scale",
                },
            }
        }
        self._api("POST", f"/rest/api/3/issue/{issue_key}/remotelink", json=payload)
        self._log(f"  -> Linked cycle {cycle_id} to {issue_key}")

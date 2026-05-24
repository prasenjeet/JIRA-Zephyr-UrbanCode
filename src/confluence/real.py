"""Real Confluence client — makes actual HTTP calls to the Confluence REST API v1.

Authentication uses HTTP Basic Auth with an Atlassian account email and API token.
See: https://developer.atlassian.com/cloud/confluence/rest/v1/intro/
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import requests
from requests.auth import HTTPBasicAuth

from src.exceptions import APIError, AuthenticationError, NotFoundError
from .base import BaseConfluenceClient
from .models import Page


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _parse_datetime(s: str | None) -> datetime:
    """Parse a Confluence ISO-8601 datetime string."""
    if not s:
        return _now()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return _now()


def _parse_page(data: dict, base_url: str) -> Page:
    """Map a Confluence REST API page dict to a :class:`Page` dataclass."""
    body = data.get("body", {})
    storage = body.get("storage", {})
    content = storage.get("value", "")

    version_obj = data.get("version", {})
    version_num = version_obj.get("number", 1)

    history = data.get("history", {})
    created_by = history.get("createdBy", {}) if history else {}
    author = (
        created_by.get("email")
        or created_by.get("displayName", "unknown")
    )

    space_obj = data.get("space", {})
    space_key = space_obj.get("key", "")

    links = data.get("_links", {})
    webui = links.get("webui", "")
    url = f"{base_url.rstrip('/')}{webui}" if webui else ""

    ancestors = data.get("ancestors", [])
    parent_id = ancestors[-1]["id"] if ancestors else None

    metadata = data.get("metadata", {})
    labels_obj = metadata.get("labels", {})
    label_results = labels_obj.get("results", []) if isinstance(labels_obj, dict) else []
    labels = [lbl.get("name", "") for lbl in label_results]

    created_str = history.get("createdDate") if history else None
    updated_str = version_obj.get("when") if version_obj else None

    return Page(
        id=data["id"],
        title=data.get("title", ""),
        content=content,
        space_key=space_key,
        version=version_num,
        created=_parse_datetime(created_str),
        updated=_parse_datetime(updated_str),
        author=author,
        url=url,
        parent_id=parent_id,
        labels=labels,
    )


def _build_test_report_html(title: str, test_results: list[dict[str, Any]]) -> str:
    """Render a simple HTML table for a Confluence test report page."""
    passed = sum(1 for r in test_results if r.get("status", "").upper() == "PASS")
    failed = sum(1 for r in test_results if r.get("status", "").upper() == "FAIL")
    total = len(test_results)

    rows = ""
    for r in test_results:
        status = r.get("status", "UNKNOWN").upper()
        colour = "#00875A" if status == "PASS" else "#DE350B"
        rows += (
            f"<tr>"
            f"<td>{r.get('test_case_key', 'N/A')}</td>"
            f"<td>{r.get('test_name', 'N/A')}</td>"
            f'<td><strong><span style="color:{colour}">{status}</span></strong></td>'
            f"<td>{r.get('comment', '')}</td>"
            f"<td>{r.get('executed_by', 'automation')}</td>"
            f"</tr>\n"
        )

    summary_colour = "#00875A" if failed == 0 else "#DE350B"
    return f"""<h1>{title}</h1>
<p><strong>Generated:</strong> {_now().strftime("%Y-%m-%d %H:%M UTC")}</p>
<h2>Summary</h2>
<table>
  <tr><th>Total</th><th>Passed</th><th>Failed</th><th>Pass Rate</th></tr>
  <tr>
    <td>{total}</td>
    <td><span style="color:#00875A"><strong>{passed}</strong></span></td>
    <td><span style="color:#DE350B"><strong>{failed}</strong></span></td>
    <td><strong><span style="color:{summary_colour}">{(passed / total * 100) if total else 0:.1f}%</span></strong></td>
  </tr>
</table>
<h2>Test Case Results</h2>
<table>
  <tr><th>Key</th><th>Test Name</th><th>Status</th><th>Comment</th><th>Executed By</th></tr>
  {rows}
</table>
"""


class RealConfluenceClient(BaseConfluenceClient):
    """Real Confluence client that calls the Atlassian Confluence REST API v1.

    Args:
        base_url: Confluence Cloud base URL, e.g. ``https://yourorg.atlassian.net/wiki``.
        username: Atlassian account email address.
        api_token: Atlassian API token.
        space_key: Default Confluence space key.
        verify_ssl: Set to ``False`` to skip TLS verification (not recommended).
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        api_token: str,
        space_key: str = "DEMO",
        verify_ssl: bool = True,
        **kwargs,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.space_key = space_key
        self.use_decoy = False

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
            raise AuthenticationError(
                "Confluence authentication failed — check username and api_token."
            )
        if resp.status_code == 404:
            raise NotFoundError(f"Confluence resource not found: {path}")

        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            raise APIError(
                str(exc), status_code=resp.status_code, response_body=resp.text
            ) from exc

        return resp.json() if resp.content else {}

    def _log(self, message: str) -> None:
        print(f"[CONFLUENCE REAL] {message}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_page(
        self,
        title: str,
        content: str,
        parent_id: Optional[str] = None,
        space_key: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> Page:
        """Create a new Confluence page via the REST API."""
        sk = space_key or self.space_key
        self._log(f"POST /rest/api/content  title={title!r}  space={sk!r}")

        body: dict[str, Any] = {
            "type": "page",
            "title": title,
            "space": {"key": sk},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage",
                }
            },
        }
        if parent_id:
            body["ancestors"] = [{"id": parent_id}]

        data = self._api("POST", "/rest/api/content", json=body)
        page = _parse_page(data, self.base_url)

        # Add labels in a separate call if requested
        if labels:
            label_payload = [{"prefix": "global", "name": lbl} for lbl in labels]
            self._api("POST", f"/rest/api/content/{page.id}/label", json=label_payload)
            page.labels = labels

        self._log(f"  -> Created {page!r}")
        return page

    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        labels: Optional[list[str]] = None,
    ) -> Page:
        """Update an existing Confluence page."""
        self._log(f"PUT /rest/api/content/{page_id}  title={title!r}")

        # Fetch current version number
        current = self._api(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": "version"},
        )
        current_version = current.get("version", {}).get("number", 1)

        body: dict[str, Any] = {
            "type": "page",
            "title": title,
            "version": {"number": current_version + 1},
            "body": {
                "storage": {
                    "value": content,
                    "representation": "storage",
                }
            },
        }

        data = self._api("PUT", f"/rest/api/content/{page_id}", json=body)
        page = _parse_page(data, self.base_url)

        if labels is not None:
            label_payload = [{"prefix": "global", "name": lbl} for lbl in labels]
            self._api("POST", f"/rest/api/content/{page_id}/label", json=label_payload)
            page.labels = labels

        self._log(f"  -> Updated {page!r}")
        return page

    def get_page(self, page_id: str) -> Page:
        """Fetch a Confluence page by ID."""
        self._log(f"GET /rest/api/content/{page_id}")
        data = self._api(
            "GET",
            f"/rest/api/content/{page_id}",
            params={"expand": "body.storage,version,ancestors,metadata.labels,history,space"},
        )
        page = _parse_page(data, self.base_url)
        self._log(f"  -> Returning {page!r}")
        return page

    def get_pages_in_space(self, space_key: Optional[str] = None) -> list[Page]:
        """Return all pages in a Confluence space."""
        sk = space_key or self.space_key
        self._log(f"GET /rest/api/content  spaceKey={sk!r}")
        data = self._api(
            "GET",
            "/rest/api/content",
            params={"spaceKey": sk, "type": "page", "limit": 50,
                    "expand": "body.storage,version,ancestors,metadata.labels,history,space"},
        )
        pages = [_parse_page(item, self.base_url) for item in data.get("results", [])]
        self._log(f"  -> Found {len(pages)} page(s) in space {sk!r}")
        return pages

    def create_test_report_page(
        self,
        title: str,
        test_results: list[dict[str, Any]],
        parent_id: Optional[str] = None,
        space_key: Optional[str] = None,
    ) -> Page:
        """Create a formatted HTML test report Confluence page."""
        self._log(f"create_test_report_page: building report for {len(test_results)} result(s)")
        html_content = _build_test_report_html(title, test_results)
        page = self.create_page(
            title=title,
            content=html_content,
            parent_id=parent_id,
            space_key=space_key,
            labels=["test-report", "automation"],
        )
        self._log(f"  -> Test report page created: {page.url}")
        return page

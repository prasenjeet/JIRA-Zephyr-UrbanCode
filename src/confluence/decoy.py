"""Confluence Decoy Client - simulates the Confluence REST API without credentials.

All methods print "[CONFLUENCE DECOY]" prefixed messages and return realistic mock data.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .base import BaseConfluenceClient
from .models import Page

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _short_id() -> str:
    return str(uuid.uuid4().int)[:9]


def _page_url(base_url: str, space_key: str, page_id: str, title: str) -> str:
    slug = title.replace(" ", "+")
    return f"{base_url}/spaces/{space_key}/pages/{page_id}/{slug}"


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
  <tr>
    <th>Total</th>
    <th>Passed</th>
    <th>Failed</th>
    <th>Pass Rate</th>
  </tr>
  <tr>
    <td>{total}</td>
    <td><span style="color:#00875A"><strong>{passed}</strong></span></td>
    <td><span style="color:#DE350B"><strong>{failed}</strong></span></td>
    <td><strong>
      <span style="color:{summary_colour}">
        {(passed / total * 100) if total else 0:.1f}%
      </span>
    </strong></td>
  </tr>
</table>

<h2>Test Case Results</h2>
<table>
  <tr>
    <th>Key</th>
    <th>Test Name</th>
    <th>Status</th>
    <th>Comment</th>
    <th>Executed By</th>
  </tr>
  {rows}
</table>
"""


# ---------------------------------------------------------------------------
# DecoyConfluenceClient
# ---------------------------------------------------------------------------


class DecoyConfluenceClient(BaseConfluenceClient):
    """Decoy Confluence client that simulates the Confluence REST API.

    All operations are performed in-memory.

    Args:
        base_url: Confluence base URL (e.g. ``https://org.atlassian.net/wiki``).
        space_key: Default Confluence space key.
        username: Atlassian account email.
        api_token: Atlassian API token.
    """

    def __init__(
        self,
        base_url: str = "https://your-org.atlassian.net/wiki",
        space_key: str = "DEMO",
        username: str = "decoy@example.com",
        api_token: str = "decoy-token",
        **kwargs,
    ) -> None:
        self.base_url = base_url
        self.space_key = space_key
        self.username = username
        self.api_token = api_token
        self.use_decoy = True

        self._pages: dict[str, Page] = {}

        self._log("DecoyConfluenceClient initialised.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str) -> None:
        print(f"[CONFLUENCE DECOY] {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

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
        """Create a new Confluence page.

        Args:
            title: Page title (must be unique within the space).
            content: Page body as storage-format HTML or plain text.
            parent_id: Optional parent page ID for nesting.
            space_key: Target space (defaults to ``self.space_key``).
            labels: Optional list of label strings.

        Returns:
            Newly created :class:`Page`.
        """
        self._simulate_latency()
        sk = space_key or self.space_key
        page_id = _short_id()
        self._log(f"POST /wiki/rest/api/content  (space={sk!r})")
        self._log(f"  title    : {title!r}")
        self._log(f"  parent   : {parent_id!r}")
        self._log(f"  content  : {len(content)} chars")

        page = Page(
            id=page_id,
            title=title,
            content=content,
            space_key=sk,
            version=1,
            created=_now(),
            updated=_now(),
            author=self.username,
            url=_page_url(self.base_url, sk, page_id, title),
            parent_id=parent_id,
            labels=labels or [],
        )
        self._pages[page_id] = page
        self._log(f"  -> Created page {page!r}")
        return page

    def update_page(
        self,
        page_id: str,
        title: str,
        content: str,
        labels: Optional[list[str]] = None,
    ) -> Page:
        """Update an existing Confluence page.

        Args:
            page_id: ID of the page to update.
            title: New title (can be the same as existing).
            content: New body content.
            labels: Optional new labels to set.

        Returns:
            Updated :class:`Page`.

        Raises:
            KeyError: If the page does not exist.
        """
        self._simulate_latency()
        self._log(f"PUT /wiki/rest/api/content/{page_id}")
        self._log(f"  title   : {title!r}")

        if page_id not in self._pages:
            raise KeyError(f"Page {page_id!r} not found in decoy store.")

        page = self._pages[page_id]
        page.title = title
        page.content = content
        page.version += 1
        page.updated = _now()
        if labels is not None:
            page.labels = labels

        self._log(f"  -> Updated {page!r}")
        return page

    def get_page(self, page_id: str) -> Page:
        """Fetch a Confluence page by ID.

        Args:
            page_id: Page identifier.

        Returns:
            :class:`Page` from the decoy store.

        Raises:
            KeyError: If the page does not exist.
        """
        self._simulate_latency()
        self._log(f"GET /wiki/rest/api/content/{page_id}")

        if page_id not in self._pages:
            raise KeyError(f"Page {page_id!r} not found in decoy store.")

        page = self._pages[page_id]
        self._log(f"  -> Returning {page!r}")
        return page

    def get_pages_in_space(self, space_key: Optional[str] = None) -> list[Page]:
        """Return all pages in a Confluence space.

        Args:
            space_key: Space to list.  Defaults to ``self.space_key``.

        Returns:
            List of :class:`Page` objects.
        """
        self._simulate_latency()
        sk = space_key or self.space_key
        self._log(f"GET /wiki/rest/api/content?spaceKey={sk}")

        results = [p for p in self._pages.values() if p.space_key == sk]
        self._log(f"  -> Found {len(results)} page(s) in space {sk!r}")
        return results

    def create_test_report_page(
        self,
        title: str,
        test_results: list[dict[str, Any]],
        parent_id: Optional[str] = None,
        space_key: Optional[str] = None,
    ) -> Page:
        """Create a formatted HTML test report Confluence page.

        Convenience wrapper that converts a list of test result dicts into
        a nicely formatted HTML table and creates a page.

        Args:
            title: Page title.
            test_results: List of dicts with keys:
                ``test_case_key``, ``test_name``, ``status`` (PASS/FAIL),
                ``comment``, ``executed_by``.
            parent_id: Optional parent page ID.
            space_key: Target space (defaults to ``self.space_key``).

        Returns:
            Newly created :class:`Page`.
        """
        self._log(
            f"create_test_report_page: building report for {len(test_results)} result(s)"
        )
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

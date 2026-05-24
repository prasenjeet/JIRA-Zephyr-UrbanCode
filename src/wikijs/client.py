"""Wiki.js Decoy Client - simulates the Wiki.js GraphQL API without credentials.

All methods print "[WIKIJS DECOY]" prefixed messages and return realistic mock data.
Wiki.js uses a GraphQL API; method names reflect the underlying mutations/queries.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .models import WikiPage


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _next_id() -> int:
    return abs(hash(str(uuid.uuid4()))) % 100_000 + 1


def _page_url(base_url: str, locale: str, path: str) -> str:
    return f"{base_url}/{locale}/{path}"


def _slugify(text: str) -> str:
    return text.lower().replace(" ", "-").replace("/", "-")


def _build_test_report_markdown(title: str, test_results: list[dict[str, Any]]) -> str:
    """Render a Markdown test report for a Wiki.js page."""

    passed = sum(1 for r in test_results if r.get("status", "").upper() == "PASS")
    failed = sum(1 for r in test_results if r.get("status", "").upper() == "FAIL")
    total = len(test_results)
    pass_rate = (passed / total * 100) if total else 0.0

    rows = ""
    for r in test_results:
        status = r.get("status", "UNKNOWN").upper()
        icon = ":white_check_mark:" if status == "PASS" else ":x:"
        rows += (
            f"| {r.get('test_case_key', 'N/A')} "
            f"| {r.get('test_name', 'N/A')} "
            f"| {icon} {status} "
            f"| {r.get('comment', '')} "
            f"| {r.get('executed_by', 'automation')} |\n"
        )

    return f"""# {title}

**Generated:** {_now().strftime("%Y-%m-%d %H:%M UTC")}

## Summary

| Total | Passed | Failed | Pass Rate |
|-------|--------|--------|-----------|
| {total} | {passed} | {failed} | {pass_rate:.1f}% |

## Test Case Results

| Key | Test Name | Status | Comment | Executed By |
|-----|-----------|--------|---------|-------------|
{rows}
"""


class WikiJsClient:
    """Decoy Wiki.js client that simulates the Wiki.js GraphQL API.

    All operations are performed in-memory; no real Wiki.js instance is required.

    Args:
        base_url: Wiki.js base URL (e.g. ``https://wiki.example.com``).
        locale: Default page locale (default ``"en"``).
        api_key: Wiki.js API key.
        use_decoy: When ``True`` all methods use in-memory mock data.
    """

    def __init__(
        self,
        base_url: str = "https://wiki.example.com",
        locale: str = "en",
        api_key: str = "decoy-api-key",
        use_decoy: bool = True,
    ) -> None:
        self.base_url = base_url
        self.locale = locale
        self.api_key = api_key
        self.use_decoy = use_decoy

        self._pages: dict[int, WikiPage] = {}

        self._log("WikiJsClient initialised (decoy mode).")

    def _log(self, message: str) -> None:
        print(f"[WIKIJS DECOY] {message}")

    def _simulate_latency(self) -> None:
        time.sleep(0.1)

    # ------------------------------------------------------------------
    # Public API (mirrors Wiki.js GraphQL mutations/queries)
    # ------------------------------------------------------------------

    def create_page(
        self,
        title: str,
        content: str,
        path: Optional[str] = None,
        locale: Optional[str] = None,
        description: str = "",
        tags: Optional[list[str]] = None,
    ) -> WikiPage:
        """Create a new Wiki.js page (GraphQL ``pages { create }`` mutation).

        Args:
            title: Page title.
            content: Page body in Markdown.
            path: URL path slug (auto-derived from title when omitted).
            locale: Page locale (defaults to ``self.locale``).
            description: Short page description / excerpt.
            tags: Optional list of tag strings.

        Returns:
            Newly created :class:`WikiPage`.
        """
        self._simulate_latency()
        loc = locale or self.locale
        resolved_path = path or _slugify(title)
        page_id = _next_id()

        self._log("mutation pages { create } →")
        self._log(f"  title       : {title!r}")
        self._log(f"  path        : {resolved_path!r}")
        self._log(f"  locale      : {loc!r}")
        self._log(f"  content     : {len(content)} chars (Markdown)")

        page = WikiPage(
            id=page_id,
            path=resolved_path,
            title=title,
            content=content,
            locale=loc,
            description=description,
            created=_now(),
            updated=_now(),
            author="decoy-user",
            url=_page_url(self.base_url, loc, resolved_path),
            tags=tags or [],
        )
        self._pages[page_id] = page
        self._log(f"  -> Created {page!r}")
        return page

    def update_page(
        self,
        page_id: int,
        title: str,
        content: str,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> WikiPage:
        """Update an existing Wiki.js page (GraphQL ``pages { update }`` mutation).

        Args:
            page_id: Numeric ID of the page to update.
            title: New title.
            content: New Markdown body.
            description: Updated description (unchanged if omitted).
            tags: Updated tag list (unchanged if omitted).

        Returns:
            Updated :class:`WikiPage`.

        Raises:
            KeyError: If the page does not exist.
        """
        self._simulate_latency()
        self._log(f"mutation pages {{ update }} → id={page_id}")
        self._log(f"  title   : {title!r}")

        if page_id not in self._pages:
            raise KeyError(f"WikiPage id={page_id!r} not found in decoy store.")

        page = self._pages[page_id]
        page.title = title
        page.content = content
        page.updated = _now()
        if description is not None:
            page.description = description
        if tags is not None:
            page.tags = tags

        self._log(f"  -> Updated {page!r}")
        return page

    def get_page(self, page_id: int) -> WikiPage:
        """Fetch a Wiki.js page by ID (GraphQL ``pages { single }`` query).

        Args:
            page_id: Numeric page identifier.

        Returns:
            :class:`WikiPage` from the decoy store.

        Raises:
            KeyError: If the page does not exist.
        """
        self._simulate_latency()
        self._log(f"query pages {{ single(id: {page_id}) }}")

        if page_id not in self._pages:
            raise KeyError(f"WikiPage id={page_id!r} not found in decoy store.")

        page = self._pages[page_id]
        self._log(f"  -> Returning {page!r}")
        return page

    def get_pages_in_locale(self, locale: Optional[str] = None) -> list[WikiPage]:
        """List all pages in a locale (GraphQL ``pages { list }`` query).

        Args:
            locale: Locale to filter by. Defaults to ``self.locale``.

        Returns:
            List of :class:`WikiPage` objects.
        """
        self._simulate_latency()
        loc = locale or self.locale
        self._log(f"query pages {{ list(locale: {loc!r}) }}")

        results = [p for p in self._pages.values() if p.locale == loc]
        self._log(f"  -> Found {len(results)} page(s) in locale {loc!r}")
        return results

    def create_test_report_page(
        self,
        title: str,
        test_results: list[dict[str, Any]],
        path: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> WikiPage:
        """Create a formatted Markdown test report page.

        Convenience wrapper that converts a list of test result dicts into a
        Markdown table and creates a page.

        Args:
            title: Page title.
            test_results: List of dicts with keys:
                ``test_case_key``, ``test_name``, ``status`` (PASS/FAIL),
                ``comment``, ``executed_by``.
            path: URL path slug (auto-derived from title when omitted).
            locale: Page locale.

        Returns:
            Newly created :class:`WikiPage`.
        """
        self._log(
            f"create_test_report_page: building report for {len(test_results)} result(s)"
        )
        markdown_content = _build_test_report_markdown(title, test_results)
        page = self.create_page(
            title=title,
            content=markdown_content,
            path=path or f"test-reports/{_slugify(title)}",
            locale=locale,
            description=f"Automated test report: {title}",
            tags=["test-report", "automation"],
        )
        self._log(f"  -> Test report page created: {page.url}")
        return page

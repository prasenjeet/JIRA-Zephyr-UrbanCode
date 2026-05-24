"""Unit tests for the Wiki.js decoy client."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.wikijs.client import WikiJsClient
from src.wikijs.models import WikiPage


@pytest.fixture()
def client() -> WikiJsClient:
    return WikiJsClient(base_url="https://wiki.test.com", locale="en")


class TestCreatePage:
    def test_returns_wiki_page(self, client):
        page = client.create_page(title="My Page", content="# Hello")
        assert isinstance(page, WikiPage)

    def test_title_stored(self, client):
        page = client.create_page(title="Stored Title", content="")
        assert page.title == "Stored Title"

    def test_path_auto_derived_from_title(self, client):
        page = client.create_page(title="Auto Path Test", content="")
        assert page.path == "auto-path-test"

    def test_explicit_path_stored(self, client):
        page = client.create_page(title="Any Title", content="", path="custom/path")
        assert page.path == "custom/path"

    def test_tags_stored(self, client):
        page = client.create_page(title="Tag Test", content="", tags=["qa", "demo"])
        assert "qa" in page.tags
        assert "demo" in page.tags

    def test_url_contains_path(self, client):
        page = client.create_page(title="URL Test", content="", path="foo/bar")
        assert "foo/bar" in page.url

    def test_url_contains_locale(self, client):
        page = client.create_page(title="Locale Test", content="", locale="fr")
        assert "/fr/" in page.url

    def test_locale_defaults_to_client_locale(self, client):
        page = client.create_page(title="Default Locale", content="")
        assert page.locale == "en"

    def test_id_is_integer(self, client):
        page = client.create_page(title="ID Test", content="")
        assert isinstance(page.id, int)


class TestGetPage:
    def test_raises_on_missing(self, client):
        with pytest.raises(KeyError):
            client.get_page(99999)

    def test_returns_created_page(self, client):
        page = client.create_page(title="Fetch Test", content="body")
        fetched = client.get_page(page.id)
        assert fetched.id == page.id

    def test_content_matches(self, client):
        page = client.create_page(title="Content Match", content="# Hello World")
        fetched = client.get_page(page.id)
        assert fetched.content == "# Hello World"


class TestUpdatePage:
    def test_title_updated(self, client):
        page = client.create_page(title="Original", content="v1")
        client.update_page(page.id, title="Updated", content="v2")
        fetched = client.get_page(page.id)
        assert fetched.title == "Updated"

    def test_content_updated(self, client):
        page = client.create_page(title="Content Update", content="old")
        client.update_page(page.id, title="Content Update", content="new content")
        fetched = client.get_page(page.id)
        assert fetched.content == "new content"

    def test_tags_updated(self, client):
        page = client.create_page(title="Tag Update", content="", tags=["old-tag"])
        client.update_page(page.id, title="Tag Update", content="", tags=["new-tag"])
        fetched = client.get_page(page.id)
        assert "new-tag" in fetched.tags
        assert "old-tag" not in fetched.tags

    def test_raises_on_missing(self, client):
        with pytest.raises(KeyError):
            client.update_page(99999, title="T", content="C")

    def test_updated_timestamp_changes(self, client):
        import time
        page = client.create_page(title="Timestamp", content="")
        original_updated = page.updated
        time.sleep(0.05)
        client.update_page(page.id, title="Timestamp", content="changed")
        fetched = client.get_page(page.id)
        assert fetched.updated >= original_updated


class TestGetPagesInLocale:
    def test_returns_pages_in_locale(self, client):
        client.create_page(title="Page A", content="")
        client.create_page(title="Page B", content="")
        pages = client.get_pages_in_locale("en")
        assert len(pages) >= 2

    def test_different_locale_excluded(self, client):
        client.create_page(title="French Page", content="", locale="fr")
        pages = client.get_pages_in_locale("en")
        assert all(p.locale == "en" for p in pages)

    def test_defaults_to_client_locale(self, client):
        client.create_page(title="Default Locale Page", content="")
        pages = client.get_pages_in_locale()
        assert all(p.locale == "en" for p in pages)


class TestCreateTestReportPage:
    def test_page_created_with_results(self, client):
        results = [
            {"test_case_key": "TC-001", "test_name": "Login test", "status": "PASS", "comment": "", "executed_by": "bot"},
            {"test_case_key": "TC-002", "test_name": "Logout test", "status": "FAIL", "comment": "Timeout", "executed_by": "bot"},
        ]
        page = client.create_test_report_page(title="My Report", test_results=results)
        assert isinstance(page, WikiPage)
        assert "PASS" in page.content
        assert "FAIL" in page.content

    def test_report_has_automation_tag(self, client):
        page = client.create_test_report_page(title="Tag Report", test_results=[])
        assert "automation" in page.tags

    def test_report_path_under_test_reports(self, client):
        page = client.create_test_report_page(title="Path Report", test_results=[])
        assert page.path.startswith("test-reports/")

    def test_content_is_markdown(self, client):
        results = [
            {"test_case_key": "TC-001", "test_name": "T1", "status": "PASS", "comment": "", "executed_by": "bot"},
        ]
        page = client.create_test_report_page(title="Markdown Check", test_results=results)
        assert "#" in page.content
        assert "|" in page.content

    def test_summary_counts_correct(self, client):
        results = [
            {"test_case_key": "TC-001", "test_name": "T1", "status": "PASS", "comment": "", "executed_by": "bot"},
            {"test_case_key": "TC-002", "test_name": "T2", "status": "PASS", "comment": "", "executed_by": "bot"},
            {"test_case_key": "TC-003", "test_name": "T3", "status": "FAIL", "comment": "err", "executed_by": "bot"},
        ]
        page = client.create_test_report_page(title="Count Check", test_results=results)
        assert "66.7%" in page.content

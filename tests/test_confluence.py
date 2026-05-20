"""Unit tests for the Confluence decoy client."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.confluence.client import ConfluenceClient
from src.confluence.models import Page


@pytest.fixture()
def client() -> ConfluenceClient:
    return ConfluenceClient(space_key="TEST")


class TestCreatePage:
    def test_returns_page(self, client):
        page = client.create_page(title="My Page", content="<p>Hello</p>")
        assert isinstance(page, Page)

    def test_title_stored(self, client):
        page = client.create_page(title="Stored Title", content="")
        assert page.title == "Stored Title"

    def test_version_starts_at_one(self, client):
        page = client.create_page(title="Version Test", content="")
        assert page.version == 1

    def test_labels_stored(self, client):
        page = client.create_page(title="Label Test", content="", labels=["qa"])
        assert "qa" in page.labels

    def test_url_contains_page_id(self, client):
        page = client.create_page(title="URL Test", content="")
        assert page.id in page.url


class TestGetPage:
    def test_raises_on_missing(self, client):
        with pytest.raises(KeyError):
            client.get_page("nonexistent-id")

    def test_returns_created_page(self, client):
        page = client.create_page(title="Fetch Test", content="body")
        fetched = client.get_page(page.id)
        assert fetched.id == page.id


class TestUpdatePage:
    def test_version_increments(self, client):
        page = client.create_page(title="Update Test", content="v1")
        client.update_page(page.id, title="Update Test", content="v2")
        fetched = client.get_page(page.id)
        assert fetched.version == 2

    def test_content_updated(self, client):
        page = client.create_page(title="Content Update", content="old")
        client.update_page(page.id, title="Content Update", content="new content")
        fetched = client.get_page(page.id)
        assert fetched.content == "new content"

    def test_raises_on_missing(self, client):
        with pytest.raises(KeyError):
            client.update_page("bad-id", title="T", content="C")


class TestGetPagesInSpace:
    def test_returns_pages_in_space(self, client):
        client.create_page(title="Page A", content="")
        client.create_page(title="Page B", content="")
        pages = client.get_pages_in_space("TEST")
        assert len(pages) >= 2

    def test_different_space_excluded(self, client):
        client.create_page(title="Other Space Page", content="", space_key="OTHER")
        pages = client.get_pages_in_space("TEST")
        assert all(p.space_key == "TEST" for p in pages)


class TestCreateTestReportPage:
    def test_page_created_with_results(self, client):
        results = [
            {"test_case_key": "TC-001", "test_name": "Login test", "status": "PASS", "comment": "", "executed_by": "bot"},
            {"test_case_key": "TC-002", "test_name": "Logout test", "status": "FAIL", "comment": "Timeout", "executed_by": "bot"},
        ]
        page = client.create_test_report_page(title="My Report", test_results=results)
        assert isinstance(page, Page)
        assert "PASS" in page.content
        assert "FAIL" in page.content

    def test_report_has_automation_label(self, client):
        page = client.create_test_report_page(title="Label Report", test_results=[])
        assert "automation" in page.labels

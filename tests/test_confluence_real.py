"""Tests for the real Confluence client (HTTP calls mocked with responses library)."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import responses as resp_lib
from src.confluence.real import RealConfluenceClient
from src.confluence.models import Page
from src.exceptions import NotFoundError, AuthenticationError

BASE = "https://test.atlassian.net/wiki"


@pytest.fixture
def client():
    return RealConfluenceClient(
        base_url=BASE,
        username="user@test.com",
        api_token="token",
        space_key="TEST",
    )


def _page_response(page_id="123", title="My Page", version=1, space_key="TEST"):
    return {
        "id": page_id,
        "title": title,
        "type": "page",
        "space": {"key": space_key},
        "version": {"number": version, "when": "2024-01-15T10:00:00.000Z"},
        "body": {
            "storage": {
                "value": "<p>Page content</p>",
                "representation": "storage",
            }
        },
        "history": {
            "createdDate": "2024-01-15T10:00:00.000Z",
            "createdBy": {"email": "user@test.com", "displayName": "Test User"},
        },
        "ancestors": [],
        "metadata": {"labels": {"results": [{"name": "qa"}]}},
        "_links": {"webui": f"/spaces/{space_key}/pages/{page_id}/{title.replace(' ', '+')}"},
    }


@resp_lib.activate
def test_create_page_success(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/content",
        json=_page_response(), status=200
    )
    page = client.create_page(title="My Page", content="<p>Hello</p>")
    assert isinstance(page, Page)
    assert page.title == "My Page"
    assert page.id == "123"


@resp_lib.activate
def test_create_page_with_labels(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/content",
        json=_page_response(), status=200
    )
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/content/123/label",
        json={}, status=200
    )
    page = client.create_page(title="My Page", content="<p>Hello</p>", labels=["qa", "automation"])
    assert isinstance(page, Page)
    assert page.labels == ["qa", "automation"]


@resp_lib.activate
def test_create_page_auth_error(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/content",
        json={}, status=401
    )
    with pytest.raises(AuthenticationError):
        client.create_page(title="My Page", content="<p>Hello</p>")


@resp_lib.activate
def test_get_page_success(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/content/123",
        json=_page_response(), status=200
    )
    page = client.get_page("123")
    assert isinstance(page, Page)
    assert page.id == "123"
    assert page.title == "My Page"


@resp_lib.activate
def test_get_page_not_found(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/content/999",
        json={"message": "Not found"}, status=404
    )
    with pytest.raises(NotFoundError):
        client.get_page("999")


@resp_lib.activate
def test_get_page_auth_error(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/content/123",
        json={}, status=401
    )
    with pytest.raises(AuthenticationError):
        client.get_page("123")


@resp_lib.activate
def test_update_page_success(client):
    # First GET to fetch current version
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/content/123",
        json=_page_response(version=1), status=200
    )
    # PUT to update
    resp_lib.add(
        resp_lib.PUT, f"{BASE}/rest/api/content/123",
        json=_page_response(version=2), status=200
    )
    page = client.update_page("123", title="My Page", content="<p>Updated</p>")
    assert isinstance(page, Page)
    assert page.version == 2


@resp_lib.activate
def test_update_page_not_found(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/content/999",
        json={"message": "Not found"}, status=404
    )
    with pytest.raises(NotFoundError):
        client.update_page("999", title="T", content="C")


@resp_lib.activate
def test_get_pages_in_space(client):
    results_resp = {
        "results": [
            _page_response("1", "Page A"),
            _page_response("2", "Page B"),
        ],
        "start": 0,
        "limit": 50,
        "size": 2,
    }
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/content",
        json=results_resp, status=200
    )
    pages = client.get_pages_in_space("TEST")
    assert isinstance(pages, list)
    assert len(pages) == 2
    assert all(isinstance(p, Page) for p in pages)


@resp_lib.activate
def test_get_pages_in_space_auth_error(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/content",
        json={}, status=401
    )
    with pytest.raises(AuthenticationError):
        client.get_pages_in_space("TEST")


@resp_lib.activate
def test_create_test_report_page(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/content",
        json=_page_response(title="Test Report"), status=200
    )
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/content/123/label",
        json={}, status=200
    )
    results = [
        {"test_case_key": "TC-1", "test_name": "Login", "status": "PASS", "comment": "", "executed_by": "bot"},
        {"test_case_key": "TC-2", "test_name": "Logout", "status": "FAIL", "comment": "Error", "executed_by": "bot"},
    ]
    page = client.create_test_report_page(title="Test Report", test_results=results)
    assert isinstance(page, Page)

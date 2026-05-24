"""Tests for the real JIRA client (HTTP calls mocked with responses library)."""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import responses as resp_lib
from src.jira.real import RealJiraClient
from src.jira.models import Issue, Comment, Transition
from src.exceptions import NotFoundError, AuthenticationError, TransitionError

BASE = "https://test.atlassian.net"


@pytest.fixture
def client():
    return RealJiraClient(
        base_url=BASE, username="user@test.com", api_token="token", project_key="TEST"
    )


def _issue_response(key="TEST-1", status="Open", summary="Test issue"):
    return {
        "key": key,
        "fields": {
            "summary": summary,
            "description": None,
            "status": {"name": status},
            "issuetype": {"name": "Story"},
            "priority": {"name": "Medium"},
            "assignee": {"emailAddress": "dev@test.com"},
            "reporter": {"emailAddress": "pm@test.com"},
            "created": "2024-01-15T10:00:00.000+0000",
            "updated": "2024-01-15T11:00:00.000+0000",
            "labels": ["qa"],
            "fixVersions": [{"name": "1.0.0"}],
        },
    }


@resp_lib.activate
def test_get_issue_success(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-1",
        json=_issue_response(), status=200
    )
    issue = client.get_issue("TEST-1")
    assert isinstance(issue, Issue)
    assert issue.key == "TEST-1"
    assert issue.status == "Open"


@resp_lib.activate
def test_get_issue_not_found(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-999",
        json={"errorMessages": ["Not found"]}, status=404
    )
    with pytest.raises(NotFoundError):
        client.get_issue("TEST-999")


@resp_lib.activate
def test_get_issue_auth_error(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-1",
        json={}, status=401
    )
    with pytest.raises(AuthenticationError):
        client.get_issue("TEST-1")


@resp_lib.activate
def test_create_issue(client):
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/3/issue",
        json={"id": "10001", "key": "TEST-1"}, status=201
    )
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-1",
        json=_issue_response(), status=200
    )
    issue = client.create_issue(summary="New feature", issue_type="Story")
    assert issue.key == "TEST-1"


@resp_lib.activate
def test_transition_issue(client):
    transitions = {
        "transitions": [
            {"id": "31", "name": "In Dev", "to": {"name": "In Dev"}},
            {"id": "41", "name": "In QA", "to": {"name": "In QA"}},
        ]
    }
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-1",
        json=_issue_response(), status=200
    )
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-1/transitions",
        json=transitions, status=200
    )
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/3/issue/TEST-1/transitions",
        body="", status=204
    )
    t = client.transition_issue("TEST-1", "In Dev")
    assert isinstance(t, Transition)
    assert t.to_status == "In Dev"


@resp_lib.activate
def test_transition_not_found(client):
    transitions = {
        "transitions": [
            {"id": "31", "name": "In Dev", "to": {"name": "In Dev"}},
        ]
    }
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-1",
        json=_issue_response(), status=200
    )
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-1/transitions",
        json=transitions, status=200
    )
    with pytest.raises(TransitionError):
        client.transition_issue("TEST-1", "Deployed")


@resp_lib.activate
def test_add_comment(client):
    comment_resp = {
        "id": "100",
        "body": {},
        "author": {"emailAddress": "user@test.com"},
        "created": "2024-01-15T12:00:00.000+0000",
        "updated": "2024-01-15T12:00:00.000+0000",
    }
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-1",
        json=_issue_response(), status=200
    )
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/3/issue/TEST-1/comment",
        json=comment_resp, status=201
    )
    c = client.add_comment("TEST-1", "Looks good!")
    assert isinstance(c, Comment)
    assert c.id == "100"


@resp_lib.activate
def test_get_issues_by_status(client):
    search_resp = {
        "issues": [
            _issue_response("TEST-1", "Open"),
            _issue_response("TEST-2", "Open", "Another"),
        ],
        "total": 2,
    }
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/search",
        json=search_resp, status=200
    )
    issues = client.get_issues_by_status("Open")
    assert len(issues) == 2


@resp_lib.activate
def test_link_test_cycle(client):
    resp_lib.add(
        resp_lib.GET, f"{BASE}/rest/api/3/issue/TEST-1",
        json=_issue_response(), status=200
    )
    resp_lib.add(
        resp_lib.POST, f"{BASE}/rest/api/3/issue/TEST-1/remotelink",
        json={}, status=201
    )
    client.link_test_cycle("TEST-1", "CYC-0001")  # should not raise

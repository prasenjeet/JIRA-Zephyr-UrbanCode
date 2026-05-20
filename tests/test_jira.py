"""Unit tests for the JIRA decoy client."""

from __future__ import annotations

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.jira.client import JiraClient
from src.jira.models import Comment, Issue, Transition


@pytest.fixture()
def client() -> JiraClient:
    return JiraClient(project_key="TEST")


class TestCreateIssue:
    def test_returns_issue(self, client):
        issue = client.create_issue(summary="Test feature", issue_type="Story")
        assert isinstance(issue, Issue)

    def test_key_uses_project(self, client):
        issue = client.create_issue(summary="Test")
        assert issue.key.startswith("TEST-")

    def test_initial_status_open(self, client):
        issue = client.create_issue(summary="Test")
        assert issue.status == "Open"

    def test_labels_stored(self, client):
        issue = client.create_issue(summary="Test", labels=["qa", "sprint-1"])
        assert "qa" in issue.labels

    def test_fix_version_stored(self, client):
        issue = client.create_issue(summary="Test", fix_version="1.2.0")
        assert issue.fix_version == "1.2.0"


class TestGetIssue:
    def test_auto_creates_on_miss(self, client):
        issue = client.get_issue("TEST-999")
        assert issue.key == "TEST-999"

    def test_returns_same_instance(self, client):
        client.create_issue(summary="Same instance test")
        issue1 = client.get_issue("TEST-101")
        issue2 = client.get_issue("TEST-101")
        assert issue1 is issue2


class TestTransitionIssue:
    def test_transition_changes_status(self, client):
        issue = client.create_issue(summary="Transition test")
        client.transition_issue(issue.key, "In Dev")
        fetched = client.get_issue(issue.key)
        assert fetched.status == "In Dev"

    def test_returns_transition_record(self, client):
        issue = client.create_issue(summary="Transition record test")
        transition = client.transition_issue(issue.key, "In Dev")
        assert isinstance(transition, Transition)
        assert transition.to_status == "In Dev"

    def test_records_from_status(self, client):
        issue = client.create_issue(summary="From status test")
        transition = client.transition_issue(issue.key, "In Dev")
        assert transition.from_status == "Open"


class TestAddComment:
    def test_comment_appended(self, client):
        issue = client.create_issue(summary="Comment test")
        client.add_comment(issue.key, "This is a test comment")
        fetched = client.get_issue(issue.key)
        assert len(fetched.comments) == 1
        assert fetched.comments[0].body == "This is a test comment"

    def test_returns_comment(self, client):
        issue = client.create_issue(summary="Comment return test")
        comment = client.add_comment(issue.key, "Hello")
        assert isinstance(comment, Comment)


class TestGetIssuesByStatus:
    def test_returns_list(self, client):
        results = client.get_issues_by_status("Open")
        assert isinstance(results, list)

    def test_filters_correctly(self, client):
        client.create_issue(summary="Open issue")
        issue2 = client.create_issue(summary="Dev issue")
        client.transition_issue(issue2.key, "In Dev")
        open_issues = client.get_issues_by_status("Open")
        assert all(i.status == "Open" for i in open_issues)


class TestLinkTestCycle:
    def test_cycle_added_to_issue(self, client):
        issue = client.create_issue(summary="Link cycle test")
        client.link_test_cycle(issue.key, "CYC-ABC123")
        fetched = client.get_issue(issue.key)
        assert "CYC-ABC123" in fetched.linked_cycles

    def test_no_duplicate_links(self, client):
        issue = client.create_issue(summary="Dedup test")
        client.link_test_cycle(issue.key, "CYC-DEDUP")
        client.link_test_cycle(issue.key, "CYC-DEDUP")
        fetched = client.get_issue(issue.key)
        assert fetched.linked_cycles.count("CYC-DEDUP") == 1

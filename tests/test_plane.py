"""Unit tests for the Plane decoy client."""

from __future__ import annotations

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.plane.client import PlaneClient
from src.plane.models import Comment, Issue, StateTransition


@pytest.fixture()
def client() -> PlaneClient:
    return PlaneClient(project_identifier="TEST")


class TestCreateIssue:
    def test_returns_issue(self, client):
        issue = client.create_issue(name="Test feature", issue_type="Feature")
        assert isinstance(issue, Issue)

    def test_key_uses_project_identifier(self, client):
        issue = client.create_issue(name="Test")
        assert issue.key.startswith("TEST-")

    def test_initial_state_open(self, client):
        issue = client.create_issue(name="Test")
        assert issue.state == "Open"

    def test_labels_stored(self, client):
        issue = client.create_issue(name="Test", labels=["qa", "sprint-1"])
        assert "qa" in issue.labels

    def test_fix_version_stored(self, client):
        issue = client.create_issue(name="Test", fix_version="1.2.0")
        assert issue.fix_version == "1.2.0"

    def test_priority_stored(self, client):
        issue = client.create_issue(name="Test", priority="urgent")
        assert issue.priority == "urgent"


class TestGetIssue:
    def test_auto_creates_on_miss(self, client):
        issue = client.get_issue("TEST-999")
        assert issue.key == "TEST-999"

    def test_returns_same_instance(self, client):
        client.create_issue(name="Same instance test")
        issue1 = client.get_issue("TEST-101")
        issue2 = client.get_issue("TEST-101")
        assert issue1 is issue2


class TestTransitionIssue:
    def test_transition_changes_state(self, client):
        issue = client.create_issue(name="Transition test")
        client.transition_issue(issue.key, "In Dev")
        fetched = client.get_issue(issue.key)
        assert fetched.state == "In Dev"

    def test_returns_state_transition(self, client):
        issue = client.create_issue(name="Transition record test")
        transition = client.transition_issue(issue.key, "In Dev")
        assert isinstance(transition, StateTransition)
        assert transition.to_state == "In Dev"

    def test_records_from_state(self, client):
        issue = client.create_issue(name="From state test")
        transition = client.transition_issue(issue.key, "In Dev")
        assert transition.from_state == "Open"


class TestAddComment:
    def test_comment_appended(self, client):
        issue = client.create_issue(name="Comment test")
        client.add_comment(issue.key, "This is a test comment")
        fetched = client.get_issue(issue.key)
        assert len(fetched.comments) == 1
        assert fetched.comments[0].body == "This is a test comment"

    def test_returns_comment(self, client):
        issue = client.create_issue(name="Comment return test")
        comment = client.add_comment(issue.key, "Hello")
        assert isinstance(comment, Comment)


class TestGetIssuesByState:
    def test_returns_list(self, client):
        results = client.get_issues_by_state("Open")
        assert isinstance(results, list)

    def test_filters_correctly(self, client):
        client.create_issue(name="Open issue")
        issue2 = client.create_issue(name="Dev issue")
        client.transition_issue(issue2.key, "In Dev")
        open_issues = client.get_issues_by_state("Open")
        assert all(i.state == "Open" for i in open_issues)


class TestLinkTestRun:
    def test_run_added_to_issue(self, client):
        issue = client.create_issue(name="Link run test")
        client.link_test_run(issue.key, "RUN-0001")
        fetched = client.get_issue(issue.key)
        assert "RUN-0001" in fetched.linked_runs

    def test_no_duplicate_links(self, client):
        issue = client.create_issue(name="Dedup test")
        client.link_test_run(issue.key, "RUN-DEDUP")
        client.link_test_run(issue.key, "RUN-DEDUP")
        fetched = client.get_issue(issue.key)
        assert fetched.linked_runs.count("RUN-DEDUP") == 1

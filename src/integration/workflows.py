"""Standalone workflow functions for common integration scenarios."""

from __future__ import annotations

from typing import Optional

from src.confluence.client import ConfluenceClient
from src.jira.client import JiraClient
from src.jira.models import Issue
from src.urbancode.client import UrbanCodeClient
from src.urbancode.models import DeploymentStatus
from src.zephyr.client import ZephyrClient
from src.zephyr.models import TestStatus


def sync_jira_to_confluence(
    jira_client: JiraClient,
    confluence_client: ConfluenceClient,
    project_key: Optional[str] = None,
    statuses: Optional[list[str]] = None,
) -> list:
    """Create or update Confluence pages for JIRA issues.

    Fetches issues by status and creates one Confluence page per issue,
    containing issue metadata formatted as an HTML table.

    Args:
        jira_client: Connected :class:`JiraClient`.
        confluence_client: Connected :class:`ConfluenceClient`.
        project_key: JIRA project key to filter issues.
        statuses: List of JIRA statuses to include. Defaults to all open statuses.

    Returns:
        List of created/updated :class:`~src.confluence.models.Page` objects.
    """
    target_statuses = statuses or ["Open", "In Dev", "Ready for QA", "In QA"]
    pages = []

    print("[WORKFLOW] sync_jira_to_confluence — starting")

    for status in target_statuses:
        issues = jira_client.get_issues_by_status(status)
        for issue in issues:
            content = _issue_to_html(issue)
            title = f"[{issue.key}] {issue.summary}"
            page = confluence_client.create_page(
                title=title,
                content=content,
                labels=["jira-sync", issue.status.lower().replace(" ", "-")],
            )
            print(f"[WORKFLOW]   -> Synced {issue.key} → Confluence page {page.id}")
            pages.append(page)

    print(f"[WORKFLOW] sync_jira_to_confluence — created {len(pages)} page(s)")
    return pages


def deploy_on_test_pass(
    zephyr_client: ZephyrClient,
    urbancode_client: UrbanCodeClient,
    cycle_id: str,
    app_name: Optional[str] = None,
    environment: str = "Production",
    snapshot_name: Optional[str] = None,
) -> dict:
    """Trigger a UrbanCode Deploy deployment only if all Zephyr tests pass.

    Args:
        zephyr_client: Connected :class:`ZephyrClient`.
        urbancode_client: Connected :class:`UrbanCodeClient`.
        cycle_id: Zephyr test cycle to evaluate.
        app_name: Application name override.
        environment: Deployment target environment.
        snapshot_name: Snapshot name override (defaults to ``"auto-<cycle_id>"``).

    Returns:
        Dict with keys: ``cycle_summary``, ``deployed``, ``deployment`` (or ``None``).
    """
    print(f"[WORKFLOW] deploy_on_test_pass — evaluating cycle {cycle_id!r}")

    summary = zephyr_client.get_cycle_summary(cycle_id)
    print(
        f"[WORKFLOW]   Cycle results: {summary['passed']}/{summary['total']} passed"
    )

    if not summary["all_passed"]:
        print(
            f"[WORKFLOW]   {summary['failed']} test(s) failed — deployment SKIPPED"
        )
        return {"cycle_summary": summary, "deployed": False, "deployment": None}

    print("[WORKFLOW]   All tests passed — proceeding with deployment")
    resolved_app = app_name or urbancode_client.application
    snap = urbancode_client.create_snapshot(
        application=resolved_app,
        environment=environment,
        name=snapshot_name or f"auto-{cycle_id}",
    )
    deployment = urbancode_client.request_deployment(
        application=resolved_app,
        snapshot=snap,
        environment=environment,
    )
    final_status = urbancode_client.wait_for_deployment(request_id=deployment.id)

    success = final_status == DeploymentStatus.SUCCEEDED
    print(
        f"[WORKFLOW]   Deployment {deployment.id}: "
        f"{'SUCCEEDED' if success else 'FAILED'}"
    )
    return {
        "cycle_summary": summary,
        "deployed": success,
        "deployment": deployment,
    }


def generate_release_notes(
    jira_client: JiraClient,
    confluence_client: ConfluenceClient,
    fix_version: str,
    space_key: Optional[str] = None,
) -> object:
    """Auto-generate a release notes Confluence page for a JIRA fix version.

    Collects all issues tagged with ``fix_version`` from the Deployed status
    and formats them into a structured release notes page.

    Args:
        jira_client: Connected :class:`JiraClient`.
        confluence_client: Connected :class:`ConfluenceClient`.
        fix_version: Version string to collect issues for (e.g. ``"1.4.0"``).
        space_key: Target Confluence space.

    Returns:
        Created :class:`~src.confluence.models.Page`.
    """
    print(f"[WORKFLOW] generate_release_notes — version {fix_version!r}")

    deployed_issues = jira_client.get_issues_by_status("Deployed")
    version_issues = [i for i in deployed_issues if i.fix_version == fix_version]

    # If none match fix_version, use all deployed as a demo fallback
    if not version_issues:
        version_issues = deployed_issues
        print("[WORKFLOW]   No exact version match; using all Deployed issues as demo")

    html = _release_notes_html(fix_version, version_issues)
    title = f"Release Notes — v{fix_version}"

    page = confluence_client.create_page(
        title=title,
        content=html,
        space_key=space_key,
        labels=["release-notes", f"v{fix_version}"],
    )
    print(f"[WORKFLOW]   Release notes created: {page.url}")
    return page


# ---------------------------------------------------------------------------
# Internal HTML helpers
# ---------------------------------------------------------------------------

def _issue_to_html(issue: Issue) -> str:
    labels_str = ", ".join(issue.labels) if issue.labels else "—"
    cycles_str = ", ".join(issue.linked_cycles) if issue.linked_cycles else "—"
    return f"""<h1>[{issue.key}] {issue.summary}</h1>
<table>
  <tr><th>Field</th><th>Value</th></tr>
  <tr><td>Key</td><td>{issue.key}</td></tr>
  <tr><td>Status</td><td>{issue.status}</td></tr>
  <tr><td>Type</td><td>{issue.issue_type}</td></tr>
  <tr><td>Priority</td><td>{issue.priority}</td></tr>
  <tr><td>Assignee</td><td>{issue.assignee or '—'}</td></tr>
  <tr><td>Reporter</td><td>{issue.reporter}</td></tr>
  <tr><td>Labels</td><td>{labels_str}</td></tr>
  <tr><td>Linked Cycles</td><td>{cycles_str}</td></tr>
  <tr><td>Created</td><td>{issue.created.strftime('%Y-%m-%d %H:%M UTC')}</td></tr>
</table>
<h2>Description</h2>
<p>{issue.description or 'No description provided.'}</p>
"""


def _release_notes_html(version: str, issues: list) -> str:
    rows = "".join(
        f"<tr><td>{i.key}</td><td>{i.summary}</td>"
        f"<td>{i.issue_type}</td><td>{i.priority}</td></tr>\n"
        for i in issues
    )
    return f"""<h1>Release Notes — v{version}</h1>
<p><strong>Release Date:</strong> {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d')}</p>
<p><strong>Issues resolved:</strong> {len(issues)}</p>

<h2>Changes</h2>
<table>
  <tr><th>Issue</th><th>Summary</th><th>Type</th><th>Priority</th></tr>
  {rows}
</table>

<h2>Upgrade Notes</h2>
<p>No special upgrade steps required for this release.</p>

<h2>Known Issues</h2>
<p>See the <a href="#">JIRA backlog</a> for open issues.</p>
"""

"""Standalone workflow functions for common integration scenarios."""

from __future__ import annotations

from typing import Optional

from src.wikijs.client import WikiJsClient
from src.plane.client import PlaneClient
from src.plane.models import Issue
from src.kiwi.client import KiwiTCMSClient
from src.kiwi.models import TestStatus
from src.harness.client import HarnessClient
from src.harness.models import ExecutionStatus


def sync_plane_to_wikijs(
    plane_client: PlaneClient,
    wikijs_client: WikiJsClient,
    states: Optional[list[str]] = None,
) -> list:
    """Create or update Wiki.js pages for Plane issues.

    Fetches issues by state and creates one Wiki.js page per issue,
    containing issue metadata formatted as a Markdown table.

    Args:
        plane_client: Connected :class:`PlaneClient`.
        wikijs_client: Connected :class:`WikiJsClient`.
        states: List of Plane states to include. Defaults to all open states.

    Returns:
        List of created :class:`~src.wikijs.models.WikiPage` objects.
    """
    target_states = states or ["Open", "In Dev", "Ready for QA", "In QA"]
    pages = []

    print("[WORKFLOW] sync_plane_to_wikijs — starting")

    for state in target_states:
        issues = plane_client.get_issues_by_state(state)
        for issue in issues:
            content = _issue_to_markdown(issue)
            title = f"[{issue.key}] {issue.name}"
            page = wikijs_client.create_page(
                title=title,
                content=content,
                path=f"plane/{issue.key.lower()}",
                tags=["plane-sync", issue.state.lower().replace(" ", "-")],
            )
            print(f"[WORKFLOW]   -> Synced {issue.key} → Wiki.js page {page.id}")
            pages.append(page)

    print(f"[WORKFLOW] sync_plane_to_wikijs — created {len(pages)} page(s)")
    return pages


def deploy_on_test_pass(
    kiwi_client: KiwiTCMSClient,
    harness_client: HarnessClient,
    run_id: str,
    project: Optional[str] = None,
    environment: str = "Production",
    bundle_name: Optional[str] = None,
) -> dict:
    """Trigger a Harness CD pipeline execution only if all Kiwi TCMS tests pass.

    Args:
        kiwi_client: Connected :class:`KiwiTCMSClient`.
        harness_client: Connected :class:`HarnessClient`.
        run_id: Kiwi TCMS test run to evaluate.
        project: Harness project identifier override.
        environment: Deployment target environment.
        bundle_name: Artifact bundle name override (defaults to ``"auto-<run_id>"``).

    Returns:
        Dict with keys: ``run_summary``, ``deployed``, ``deployment`` (or ``None``).
    """
    print(f"[WORKFLOW] deploy_on_test_pass — evaluating run {run_id!r}")

    summary = kiwi_client.get_run_summary(run_id)
    print(
        f"[WORKFLOW]   Run results: {summary['passed']}/{summary['total']} passed"
    )

    if not summary["all_passed"]:
        print(
            f"[WORKFLOW]   {summary['failed']} test(s) failed — deployment SKIPPED"
        )
        return {"run_summary": summary, "deployed": False, "deployment": None}

    print("[WORKFLOW]   All tests passed — proceeding with Harness deployment")
    resolved_project = project or harness_client.project
    bundle = harness_client.create_artifact_bundle(
        project=resolved_project,
        environment=environment,
        name=bundle_name or f"auto-{run_id}",
    )
    deployment = harness_client.execute_pipeline(
        project=resolved_project,
        artifact_bundle=bundle,
        environment=environment,
    )
    final_status = harness_client.wait_for_execution(execution_id=deployment.id)

    success = final_status == ExecutionStatus.SUCCESS
    print(
        f"[WORKFLOW]   Execution {deployment.id}: "
        f"{'SUCCEEDED' if success else 'FAILED'}"
    )
    return {
        "run_summary": summary,
        "deployed": success,
        "deployment": deployment,
    }


def generate_release_notes(
    plane_client: PlaneClient,
    wikijs_client: WikiJsClient,
    fix_version: str,
    locale: Optional[str] = None,
) -> object:
    """Auto-generate a release notes Wiki.js page for a Plane fix version.

    Collects all issues in the Deployed state tagged with ``fix_version``
    and formats them into a structured Markdown release notes page.

    Args:
        plane_client: Connected :class:`PlaneClient`.
        wikijs_client: Connected :class:`WikiJsClient`.
        fix_version: Version string to collect issues for (e.g. ``"1.4.0"``).
        locale: Target Wiki.js locale.

    Returns:
        Created :class:`~src.wikijs.models.WikiPage`.
    """
    print(f"[WORKFLOW] generate_release_notes — version {fix_version!r}")

    deployed_issues = plane_client.get_issues_by_state("Deployed")
    version_issues = [i for i in deployed_issues if i.fix_version == fix_version]

    if not version_issues:
        version_issues = deployed_issues
        print("[WORKFLOW]   No exact version match; using all Deployed issues as demo")

    md = _release_notes_markdown(fix_version, version_issues)
    title = f"Release Notes — v{fix_version}"

    page = wikijs_client.create_page(
        title=title,
        content=md,
        path=f"releases/v{fix_version}",
        locale=locale,
        description=f"Release notes for version {fix_version}",
        tags=["release-notes", f"v{fix_version}"],
    )
    print(f"[WORKFLOW]   Release notes created: {page.url}")
    return page


# ---------------------------------------------------------------------------
# Internal Markdown helpers
# ---------------------------------------------------------------------------

def _issue_to_markdown(issue: Issue) -> str:
    labels_str = ", ".join(issue.labels) if issue.labels else "—"
    runs_str = ", ".join(issue.linked_runs) if issue.linked_runs else "—"
    return f"""# [{issue.key}] {issue.name}

| Field | Value |
|-------|-------|
| Key | {issue.key} |
| State | {issue.state} |
| Type | {issue.issue_type} |
| Priority | {issue.priority} |
| Assignee | {issue.assignee or '—'} |
| Created By | {issue.created_by} |
| Labels | {labels_str} |
| Linked Test Runs | {runs_str} |
| Created | {issue.created_at.strftime('%Y-%m-%d %H:%M UTC')} |

## Description

{issue.description or 'No description provided.'}
"""


def _release_notes_markdown(version: str, issues: list) -> str:
    import datetime
    rows = "".join(
        f"| {i.key} | {i.name} | {i.issue_type} | {i.priority} |\n"
        for i in issues
    )
    return f"""# Release Notes — v{version}

**Release Date:** {datetime.datetime.utcnow().strftime('%Y-%m-%d')}
**Issues resolved:** {len(issues)}

## Changes

| Issue | Summary | Type | Priority |
|-------|---------|------|----------|
{rows}

## Upgrade Notes

No special upgrade steps required for this release.

## Known Issues

See the Plane backlog for open issues.
"""

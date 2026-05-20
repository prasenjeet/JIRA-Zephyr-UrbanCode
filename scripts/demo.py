#!/usr/bin/env python3
"""Rich CLI demo: runs the full JIRA → Zephyr → Confluence → UrbanCode pipeline."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import print as rprint

from src.jira.client import JiraClient
from src.confluence.client import ConfluenceClient
from src.zephyr.client import ZephyrClient
from src.urbancode.client import UrbanCodeClient
from src.integration.pipeline import IntegrationPipeline

console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════════════════════════╗[/]
[bold cyan]║   JIRA · Confluence · Zephyr · UrbanCode  Integration    ║[/]
[bold cyan]║                  Decoy Demo v1.0                         ║[/]
[bold cyan]╚══════════════════════════════════════════════════════════╝[/]
"""


def pause(seconds: float = 0.6) -> None:
    time.sleep(seconds)


def show_client_init() -> tuple:
    console.print("\n[bold yellow]Initialising clients...[/]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        t = progress.add_task("Connecting to JIRA...", total=None)
        jira = JiraClient(project_key="DEMO")
        progress.update(t, description="[green]JIRA client ready[/]")
        pause(0.4)

        t2 = progress.add_task("Connecting to Confluence...", total=None)
        confluence = ConfluenceClient(space_key="DEMO")
        progress.update(t2, description="[green]Confluence client ready[/]")
        pause(0.4)

        t3 = progress.add_task("Connecting to Zephyr Scale...", total=None)
        zephyr = ZephyrClient(project_key="DEMO")
        progress.update(t3, description="[green]Zephyr client ready[/]")
        pause(0.4)

        t4 = progress.add_task("Connecting to UrbanCode Deploy...", total=None)
        urbancode = UrbanCodeClient(application="DemoApp", environment="Production")
        progress.update(t4, description="[green]UrbanCode client ready[/]")
        pause(0.4)

    console.print("[bold green]All clients initialised.[/]\n")
    return jira, confluence, zephyr, urbancode


def show_create_issue(jira: JiraClient) -> object:
    console.print(Panel("[bold]Step 1 — Create JIRA Issue[/]", style="blue"))
    issue = jira.create_issue(
        summary="Implement OAuth2 login flow",
        description=(
            "As a user I want to log in with my corporate SSO credentials "
            "so that I don't need a separate password."
        ),
        issue_type="Story",
        priority="High",
        labels=["auth", "security", "sprint-42"],
        fix_version="2.0.0",
    )
    pause()

    t = Table(title=f"Created Issue: {issue.key}", show_header=True)
    t.add_column("Field", style="cyan")
    t.add_column("Value")
    t.add_row("Key", issue.key)
    t.add_row("Summary", issue.summary)
    t.add_row("Status", f"[yellow]{issue.status}[/]")
    t.add_row("Type", issue.issue_type)
    t.add_row("Priority", issue.priority)
    t.add_row("Labels", ", ".join(issue.labels))
    console.print(t)
    return issue


def show_pipeline(
    jira: JiraClient,
    confluence: ConfluenceClient,
    zephyr: ZephyrClient,
    urbancode: UrbanCodeClient,
    issue_key: str,
    pass_rate: float,
) -> dict:
    console.print(Panel(
        f"[bold]Full QA Pipeline — {issue_key}[/]\n"
        f"Pass rate: {pass_rate*100:.0f}%",
        style="magenta",
    ))

    pipeline = IntegrationPipeline(
        jira=jira,
        confluence=confluence,
        zephyr=zephyr,
        urbancode=urbancode,
        version="2.0.0",
    )

    result = pipeline.run_qa_pipeline(
        jira_issue_key=issue_key,
        pass_rate=pass_rate,
        target_environment="Production",
    )
    return result


def show_results(result: dict) -> None:
    console.print(Panel("[bold]Pipeline Results[/]", style="green"))

    summary = result["summary"]
    cycle = result["cycle"]
    page = result["report_page"]
    deployment = result["deployment"]
    final_status = result["final_status"]
    all_passed = result["all_tests_passed"]

    # Test results table
    t = Table(title=f"Zephyr Cycle: {cycle.id}", show_header=True)
    t.add_column("Metric", style="cyan")
    t.add_column("Value")
    t.add_row("Total Tests", str(summary["total"]))
    t.add_row("Passed", f"[green]{summary['passed']}[/]")
    t.add_row("Failed", f"[red]{summary['failed']}[/]")
    t.add_row("Pass Rate", f"{summary['pass_rate']:.1f}%")
    t.add_row("Result", "[green]PASS[/]" if all_passed else "[red]FAIL[/]")
    console.print(t)

    # Confluence report
    console.print(f"\n[cyan]Confluence report:[/] {page.url}")

    # Deployment
    if deployment:
        status_colour = "green" if deployment.status.value == "SUCCEEDED" else "red"
        console.print(
            f"[cyan]Deployment {deployment.id}:[/] "
            f"[{status_colour}]{deployment.status.value}[/]"
        )
        if deployment.log_url:
            console.print(f"[cyan]Log:[/] {deployment.log_url}")

    # Final JIRA status
    final_colour = "green" if final_status == "Deployed" else "yellow"
    console.print(
        f"\n[cyan]Final JIRA status:[/] [{final_colour}]{final_status}[/]"
    )


def show_release_notes(jira: JiraClient, confluence: ConfluenceClient) -> None:
    console.print(Panel("[bold]Bonus — Generate Release Notes[/]", style="cyan"))
    from src.integration.workflows import generate_release_notes
    page = generate_release_notes(
        jira_client=jira,
        confluence_client=confluence,
        fix_version="2.0.0",
    )
    console.print(f"[green]Release notes page created:[/] {page.url}")


def main(pass_rate: float = 0.8) -> None:
    console.print(BANNER)
    pause()

    jira, confluence, zephyr, urbancode = show_client_init()

    issue = show_create_issue(jira)
    pause()

    # Run with partial pass rate first (to show failure path), then success
    console.print("\n[bold yellow]--- Demo Run 1: Some tests FAIL ---[/]")
    result_fail = show_pipeline(jira, confluence, zephyr, urbancode, issue.key, pass_rate=0.6)
    show_results(result_fail)
    pause()

    console.print("\n[bold yellow]--- Demo Run 2: All tests PASS ---[/]")
    result_pass = show_pipeline(jira, confluence, zephyr, urbancode, issue.key, pass_rate=1.0)
    show_results(result_pass)
    pause()

    show_release_notes(jira, confluence)

    console.print(Panel(
        "[bold green]Demo complete![/]\n\n"
        "This demo showed:\n"
        "  • JIRA issue creation and status transitions\n"
        "  • Zephyr test cycle creation and execution\n"
        "  • Confluence test report generation\n"
        "  • UrbanCode Deploy triggered on test success\n"
        "  • Automatic release notes generation\n\n"
        "All interactions used [bold cyan]decoy clients[/] — no real credentials needed.",
        style="green",
    ))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="JIRA-Zephyr-UrbanCode integration demo")
    parser.add_argument("--pass-rate", type=float, default=0.8, help="Test pass rate for demo (0.0-1.0)")
    args = parser.parse_args()
    main(pass_rate=args.pass_rate)

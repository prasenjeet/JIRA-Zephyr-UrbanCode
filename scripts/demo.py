#!/usr/bin/env python3
"""Rich CLI demo: runs the full Plane → Kiwi TCMS → Wiki.js → Harness CD pipeline."""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from src.plane.client import PlaneClient
from src.kiwi.client import KiwiTCMSClient
from src.wikijs.client import WikiJsClient
from src.harness.client import HarnessClient
from src.integration.pipeline import IntegrationPipeline

console = Console()

BANNER = """
[bold cyan]╔══════════════════════════════════════════════════════════╗[/]
[bold cyan]║    Plane · Kiwi TCMS · Wiki.js · Harness CD Integration  ║[/]
[bold cyan]║                  Decoy Demo v3.0                         ║[/]
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
        t = progress.add_task("Connecting to Plane...", total=None)
        plane = PlaneClient(project_identifier="DEMO")
        progress.update(t, description="[green]Plane client ready[/]")
        pause(0.4)

        t2 = progress.add_task("Connecting to Kiwi TCMS...", total=None)
        kiwi = KiwiTCMSClient(product="DemoProduct")
        progress.update(t2, description="[green]Kiwi TCMS client ready[/]")
        pause(0.4)

        t3 = progress.add_task("Connecting to Wiki.js...", total=None)
        wikijs = WikiJsClient(base_url="https://wiki.example.com", locale="en")
        progress.update(t3, description="[green]Wiki.js client ready[/]")
        pause(0.4)

        t4 = progress.add_task("Connecting to Harness CD...", total=None)
        harness = HarnessClient(project="DemoProject", environment="Production")
        progress.update(t4, description="[green]Harness CD client ready[/]")
        pause(0.4)

    console.print("[bold green]All clients initialised.[/]\n")
    return plane, kiwi, wikijs, harness


def show_create_issue(plane: PlaneClient) -> object:
    console.print(Panel("[bold]Step 1 — Create Plane Issue[/]", style="blue"))
    issue = plane.create_issue(
        name="Implement OAuth2 login flow",
        description=(
            "As a user I want to log in with my corporate SSO credentials "
            "so that I don't need a separate password."
        ),
        issue_type="Feature",
        priority="high",
        labels=["auth", "security", "sprint-42"],
        fix_version="2.0.0",
    )
    pause()

    t = Table(title=f"Created Issue: {issue.key}", show_header=True)
    t.add_column("Field", style="cyan")
    t.add_column("Value")
    t.add_row("Key", issue.key)
    t.add_row("Name", issue.name)
    t.add_row("State", f"[yellow]{issue.state}[/]")
    t.add_row("Type", issue.issue_type)
    t.add_row("Priority", issue.priority)
    t.add_row("Labels", ", ".join(issue.labels))
    console.print(t)
    return issue


def show_pipeline(
    plane: PlaneClient,
    kiwi: KiwiTCMSClient,
    wikijs: WikiJsClient,
    harness: HarnessClient,
    issue_key: str,
    pass_rate: float,
) -> dict:
    console.print(Panel(
        f"[bold]Full QA Pipeline — {issue_key}[/]\n"
        f"Pass rate: {pass_rate*100:.0f}%",
        style="magenta",
    ))

    pipeline = IntegrationPipeline(
        plane=plane,
        kiwi=kiwi,
        wikijs=wikijs,
        harness=harness,
        version="2.0.0",
    )

    return pipeline.run_qa_pipeline(
        issue_key=issue_key,
        pass_rate=pass_rate,
        target_environment="Production",
    )


def show_results(result: dict) -> None:
    console.print(Panel("[bold]Pipeline Results[/]", style="green"))

    summary = result["summary"]
    test_run = result["test_run"]
    page = result["report_page"]
    deployment = result["deployment"]
    final_status = result["final_status"]
    all_passed = result["all_tests_passed"]

    t = Table(title=f"Kiwi TCMS Run: {test_run.id}", show_header=True)
    t.add_column("Metric", style="cyan")
    t.add_column("Value")
    t.add_row("Total Tests", str(summary["total"]))
    t.add_row("Passed", f"[green]{summary['passed']}[/]")
    t.add_row("Failed", f"[red]{summary['failed']}[/]")
    t.add_row("Pass Rate", f"{summary['pass_rate']:.1f}%")
    t.add_row("Result", "[green]PASS[/]" if all_passed else "[red]FAIL[/]")
    console.print(t)

    console.print(f"\n[cyan]Wiki.js report:[/] {page.url}")

    if deployment:
        status_colour = "green" if deployment.status.value == "SUCCESS" else "red"
        console.print(
            f"[cyan]Deployment {deployment.id}:[/] "
            f"[{status_colour}]{deployment.status.value}[/]"
        )
        if deployment.log_url:
            console.print(f"[cyan]Log:[/] {deployment.log_url}")

    final_colour = "green" if final_status == "Deployed" else "yellow"
    console.print(f"\n[cyan]Final Plane state:[/] [{final_colour}]{final_status}[/]")


def show_release_notes(plane: PlaneClient, wikijs: WikiJsClient) -> None:
    console.print(Panel("[bold]Bonus — Generate Release Notes[/]", style="cyan"))
    from src.integration.workflows import generate_release_notes
    page = generate_release_notes(
        plane_client=plane,
        wikijs_client=wikijs,
        fix_version="2.0.0",
    )
    console.print(f"[green]Release notes page created:[/] {page.url}")


def main(pass_rate: float = 0.8) -> None:
    console.print(BANNER)
    pause()

    plane, kiwi, wikijs, harness = show_client_init()

    issue = show_create_issue(plane)
    pause()

    console.print("\n[bold yellow]--- Demo Run 1: Some tests FAIL ---[/]")
    result_fail = show_pipeline(plane, kiwi, wikijs, harness, issue.key, pass_rate=0.6)
    show_results(result_fail)
    pause()

    console.print("\n[bold yellow]--- Demo Run 2: All tests PASS ---[/]")
    result_pass = show_pipeline(plane, kiwi, wikijs, harness, issue.key, pass_rate=1.0)
    show_results(result_pass)
    pause()

    show_release_notes(plane, wikijs)

    console.print(Panel(
        "[bold green]Demo complete![/]\n\n"
        "This demo showed:\n"
        "  • Plane issue creation and state transitions\n"
        "  • Kiwi TCMS test run creation and execution\n"
        "  • Wiki.js test report generation (Markdown)\n"
        "  • Harness CD pipeline triggered on test success\n"
        "  • Automatic release notes generation\n\n"
        "All interactions used [bold cyan]decoy clients[/] — no real credentials needed.",
        style="green",
    ))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Plane-KiwiTCMS-HarnessCD integration demo")
    parser.add_argument("--pass-rate", type=float, default=0.8, help="Test pass rate (0.0-1.0)")
    args = parser.parse_args()
    main(pass_rate=args.pass_rate)

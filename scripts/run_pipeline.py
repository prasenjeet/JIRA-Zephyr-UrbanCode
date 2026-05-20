#!/usr/bin/env python3
"""CI/CD-friendly pipeline runner with argparse interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.jira.client import JiraClient
from src.confluence.client import ConfluenceClient
from src.zephyr.client import ZephyrClient
from src.urbancode.client import UrbanCodeClient
from src.integration.pipeline import IntegrationPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the JIRA→Zephyr→Confluence→UrbanCode integration pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--issue",
        required=True,
        help="JIRA issue key to run the pipeline for (e.g. DEMO-101)",
    )
    parser.add_argument(
        "--env",
        default="Production",
        help="UrbanCode Deploy target environment",
    )
    parser.add_argument(
        "--version",
        default="1.0.0",
        help="Software version under test",
    )
    parser.add_argument(
        "--pass-rate",
        type=float,
        default=1.0,
        help="(Decoy) fraction of tests that pass (0.0–1.0)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Initialise clients and validate config but do not run the pipeline",
    )
    parser.add_argument(
        "--project",
        default="DEMO",
        help="JIRA/Zephyr project key",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    print(f"[RUN_PIPELINE] issue={args.issue!r} env={args.env!r} version={args.version!r}")

    jira = JiraClient(project_key=args.project)
    confluence = ConfluenceClient(space_key=args.project)
    zephyr = ZephyrClient(project_key=args.project)
    urbancode = UrbanCodeClient(environment=args.env)

    if args.dry_run:
        print("[RUN_PIPELINE] --dry-run: clients initialised, skipping pipeline execution.")
        return 0

    pipeline = IntegrationPipeline(
        jira=jira,
        confluence=confluence,
        zephyr=zephyr,
        urbancode=urbancode,
        version=args.version,
    )

    result = pipeline.run_qa_pipeline(
        jira_issue_key=args.issue,
        pass_rate=args.pass_rate,
        target_environment=args.env,
    )

    if result["all_tests_passed"] and result.get("deployment") and \
            result["deployment"].status.value == "SUCCEEDED":
        print(f"\n[RUN_PIPELINE] SUCCESS — {args.issue} deployed to {args.env}")
        return 0
    elif not result["all_tests_passed"]:
        print(f"\n[RUN_PIPELINE] FAILURE — tests failed, {args.issue} returned to In Dev")
        return 1
    else:
        print(f"\n[RUN_PIPELINE] FAILURE — deployment failed")
        return 2


if __name__ == "__main__":
    sys.exit(main())

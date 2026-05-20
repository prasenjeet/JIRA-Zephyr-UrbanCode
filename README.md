# JIRA · Confluence · Zephyr · UrbanCode Integration

A sample Python project demonstrating end-to-end integration between **Atlassian JIRA**, **Confluence**, **Zephyr Scale** (test management), and **IBM UrbanCode Deploy** using realistic decoy clients — no real credentials required to run.

## Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║               JIRA · Zephyr · Confluence · UrbanCode                ║
║                    CI/CD Integration Architecture                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║   ┌─────────┐    ┌─────────────┐    ┌─────────────┐                 ║
║   │  JIRA   │───►│   Zephyr    │───►│  Confluence │                 ║
║   │ Issues  │    │ Test Cycles │    │   Reports   │                 ║
║   └────┬────┘    └──────┬──────┘    └─────────────┘                 ║
║        │                │                                            ║
║        │         (all tests pass?)                                   ║
║        │                │                                            ║
║        │          YES   ▼                                            ║
║        │       ┌──────────────┐                                      ║
║        └──────►│  UrbanCode   │  trigger deployment                  ║
║                │   Deploy     │  snapshot → environment              ║
║                └──────┬───────┘                                      ║
║                       │                                              ║
║              SUCCEEDED ▼ FAILED                                      ║
║          ┌─────────────┐  ┌──────────────┐                          ║
║          │ JIRA:       │  │ JIRA:        │                          ║
║          │ Deployed    │  │ In Dev +     │                          ║
║          └─────────────┘  │ rollback     │                          ║
║                           └──────────────┘                          ║
╚══════════════════════════════════════════════════════════════════════╝
```

### Integration Workflow

```
Developer pushes code
        │
        ▼
[JIRA] Issue transitions: Open → In Dev → Ready for QA
        │
        ▼
[ZEPHYR] Test cycle created and linked to JIRA issue
        │
        ▼
[ZEPHYR] Test cases executed (5 standard cases by default)
        │
        ├── Tests PASS ──► [CONFLUENCE] Test report published
        │                          │
        │                          ▼
        │                  [URBANCODE] Deployment triggered
        │                          │
        │                          ▼
        │                  [JIRA] Issue → Deployed ✓
        │
        └── Tests FAIL ──► [CONFLUENCE] Failure report published
                                   │
                                   ▼
                           [JIRA] Comment added + Issue → In Dev
```

## Project Structure

```
JIRA-Zephyr-UrbanCode/
├── config/
│   └── settings.yaml          # Connection configuration template
├── scripts/
│   ├── demo.py                # Rich CLI demo (run this first!)
│   └── run_pipeline.py        # CI/CD-friendly pipeline runner
├── src/
│   ├── jira/
│   │   ├── client.py          # JiraClient (decoy)
│   │   └── models.py          # Issue, Comment, Transition
│   ├── confluence/
│   │   ├── client.py          # ConfluenceClient (decoy)
│   │   └── models.py          # Page
│   ├── zephyr/
│   │   ├── client.py          # ZephyrClient (decoy)
│   │   └── models.py          # TestCycle, TestCase, TestResult, TestStatus
│   ├── urbancode/
│   │   ├── client.py          # UrbanCodeClient (decoy)
│   │   └── models.py          # Snapshot, DeploymentRequest, DeploymentStatus
│   └── integration/
│       ├── pipeline.py        # IntegrationPipeline orchestrator
│       └── workflows.py       # Standalone workflow functions
└── tests/
    ├── test_jira.py
    ├── test_confluence.py
    ├── test_zephyr.py
    ├── test_urbancode.py
    └── test_integration.py
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the demo

```bash
python scripts/demo.py
```

This runs the full pipeline twice — first with 60% pass rate (failure path) then 100% (success + deployment), with rich terminal output.

### 3. Run the pipeline for a specific issue

```bash
python scripts/run_pipeline.py --issue DEMO-101 --env Staging --version 2.1.0
```

Options:
| Flag | Default | Description |
|------|---------|-------------|
| `--issue` | required | JIRA issue key |
| `--env` | `Production` | UrbanCode target environment |
| `--version` | `1.0.0` | Software version under test |
| `--pass-rate` | `1.0` | Fraction of tests that pass (0.0–1.0) |
| `--dry-run` | false | Validate config without executing |
| `--project` | `DEMO` | JIRA/Zephyr project key |

### 4. Run the tests

```bash
pytest tests/ -v
```

## Configuration

Copy `.env.example` to `.env` and fill in your credentials to use real APIs:

```bash
cp .env.example .env
# Edit .env with your credentials
```

Edit `config/settings.yaml` to point at your instances. When `use_decoy=True` (the default), no network calls are made.

## Client API Reference

### JiraClient

| Method | Description |
|--------|-------------|
| `get_issue(key)` | Fetch an issue by key |
| `create_issue(summary, ...)` | Create a new issue |
| `transition_issue(key, status)` | Change issue status |
| `add_comment(key, body)` | Add a comment |
| `get_issues_by_status(status)` | Filter issues by status |
| `link_test_cycle(key, cycle_id)` | Link a Zephyr cycle |

### ZephyrClient

| Method | Description |
|--------|-------------|
| `create_test_cycle(name, ...)` | Create a test cycle |
| `add_test_cases(cycle_id, keys)` | Add test cases to cycle |
| `execute_test(cycle_id, key, status)` | Record test execution |
| `get_test_results(cycle_id)` | Get all results |
| `get_cycle_summary(cycle_id)` | Pass/fail summary |
| `run_all_tests_decoy(cycle_id, pass_rate)` | Run all tests with simulated results |

### ConfluenceClient

| Method | Description |
|--------|-------------|
| `create_page(title, content, ...)` | Create a page |
| `update_page(id, title, content)` | Update a page |
| `get_page(id)` | Fetch a page |
| `get_pages_in_space(space_key)` | List pages in space |
| `create_test_report_page(title, results)` | Create formatted test report |

### UrbanCodeClient

| Method | Description |
|--------|-------------|
| `create_snapshot(name, ...)` | Create an app snapshot |
| `get_environment_versions(app, env)` | Current deployed versions |
| `request_deployment(snapshot, ...)` | Submit deployment request |
| `get_deployment_status(id)` | Poll deployment status |
| `wait_for_deployment(id, ...)` | Block until deployment completes |
| `rollback_deployment(id)` | Trigger rollback |

### IntegrationPipeline

```python
from src.jira.client import JiraClient
from src.confluence.client import ConfluenceClient
from src.zephyr.client import ZephyrClient
from src.urbancode.client import UrbanCodeClient
from src.integration.pipeline import IntegrationPipeline

pipeline = IntegrationPipeline(
    jira=JiraClient(),
    confluence=ConfluenceClient(),
    zephyr=ZephyrClient(),
    urbancode=UrbanCodeClient(),
    version="1.0.0",
)

result = pipeline.run_qa_pipeline(
    jira_issue_key="DEMO-101",
    pass_rate=1.0,           # decoy: fraction of tests that pass
    target_environment="Production",
)
```

### Standalone Workflows

```python
from src.integration.workflows import (
    sync_jira_to_confluence,
    deploy_on_test_pass,
    generate_release_notes,
)

# Sync all open JIRA issues to Confluence pages
pages = sync_jira_to_confluence(jira, confluence, project_key="DEMO")

# Deploy only if a Zephyr cycle fully passes
result = deploy_on_test_pass(zephyr, urbancode, cycle_id="CYC-ABC123")

# Auto-generate release notes from deployed issues
page = generate_release_notes(jira, confluence, fix_version="2.0.0")
```

## Decoy Mode

All clients default to `use_decoy=True`. In decoy mode:

- No real HTTP calls are made
- All state is stored in-memory within the client instance
- Each method prints a `[JIRA DECOY]` / `[ZEPHYR DECOY]` / etc. prefixed log message showing the simulated REST endpoint and payload
- Simulated network latency of ~100 ms per call via `time.sleep(0.1)` gives a realistic feel
- IDs are generated with realistic formats: `DEMO-101`, `CYC-0001`, `REQ-000001`, `SNAP-0001`
- Status machines advance predictably: PENDING → RUNNING → SUCCEEDED (or FAILED if `simulate_failure=True`)
- Fetching an unknown JIRA issue auto-creates a plausible one rather than raising

To switch to real API calls, pass `use_decoy=False` and provide credentials via environment variables or `config/settings.yaml`.

## Requirements

- Python 3.10+
- Dependencies listed in `requirements.txt`:

| Package | Version | Purpose |
|---------|---------|---------|
| `requests` | >=2.31.0 | HTTP client (for real API mode) |
| `PyYAML` | >=6.0 | Config file parsing |
| `python-dotenv` | >=1.0.0 | `.env` file support |
| `rich` | >=13.0.0 | Terminal UI for the demo script |
| `pytest` | >=7.4.0 | Test runner |
| `pytest-mock` | >=3.11.0 | Mock helpers for unit tests |

## Data Models

### JIRA

| Class | Key Fields |
|-------|-----------|
| `Issue` | `key`, `summary`, `status`, `issue_type`, `priority`, `labels`, `linked_cycles`, `comments` |
| `Comment` | `id`, `body`, `author`, `created` |
| `Transition` | `id`, `from_status`, `to_status`, `performed_at` |

### Zephyr

| Class | Key Fields |
|-------|-----------|
| `TestCycle` | `id`, `name`, `project_key`, `version`, `jira_issue_keys`, `results` |
| `TestCase` | `key`, `name`, `description`, `steps`, `labels` |
| `TestResult` | `id`, `test_case_key`, `status`, `comment`, `executed_at` |
| `TestStatus` | `PASS`, `FAIL`, `BLOCKED`, `NOT_EXECUTED`, `IN_PROGRESS` |

### Confluence

| Class | Key Fields |
|-------|-----------|
| `Page` | `id`, `title`, `content`, `space_key`, `version`, `url`, `labels` |

### UrbanCode

| Class | Key Fields |
|-------|-----------|
| `Snapshot` | `id`, `name`, `application`, `environment`, `versions` |
| `DeploymentRequest` | `id`, `application`, `environment`, `snapshot`, `status`, `log_url` |
| `DeploymentStatus` | `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `ROLLING_BACK`, `ROLLED_BACK` |
| `ComponentVersion` | `component`, `version`, `description` |

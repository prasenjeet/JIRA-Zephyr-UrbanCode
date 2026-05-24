# Plane · Kiwi TCMS · Wiki.js · Harness CD Integration

A sample Python project demonstrating end-to-end integration between **Plane** (project management), **Kiwi TCMS** (test case management), **Wiki.js** (documentation wiki), and **Harness CD** using realistic decoy clients — no real credentials required to run. A full Docker stack is included for local testing against live instances.

## Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║          Plane · Kiwi TCMS · Wiki.js · Harness CD                   ║
║                    CI/CD Integration Architecture                    ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║   ┌─────────┐    ┌─────────────┐    ┌─────────────┐                 ║
║   │  Plane  │───►│  Kiwi TCMS  │───►│   Wiki.js   │                 ║
║   │ Issues  │    │  Test Runs  │    │   Reports   │                 ║
║   └────┬────┘    └──────┬──────┘    └─────────────┘                 ║
║        │                │                                            ║
║        │         (all tests pass?)                                   ║
║        │                │                                            ║
║        │          YES   ▼                                            ║
║        │       ┌──────────────┐                                      ║
║        └──────►│  Harness CD  │  trigger pipeline execution          ║
║                │  Pipeline    │  artifact bundle → environment       ║
║                └──────┬───────┘                                      ║
║                       │                                              ║
║              SUCCESS  ▼ FAILED                                       ║
║          ┌─────────────┐  ┌──────────────┐                          ║
║          │ Plane:      │  │ Plane:       │                          ║
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
[PLANE] Issue transitions: Open → In Dev → In QA
        │
        ▼
[KIWI TCMS] Test run created and linked to Plane issue
        │
        ▼
[KIWI TCMS] Test cases executed (5 standard cases by default)
        │
        ├── Tests PASS ──► [WIKI.JS] Test report page published
        │                          │
        │                          ▼
        │                  [HARNESS CD] Pipeline execution triggered
        │                          │
        │                          ▼
        │                  [PLANE] Issue → Deployed ✓
        │
        └── Tests FAIL ──► [WIKI.JS] Failure report page published
                                   │
                                   ▼
                           [PLANE] Comment added + Issue → In Dev
```

## Project Structure

```
JIRA-Zephyr-UrbanCode/
├── config/
│   ├── settings.yaml              # Decoy-mode config template
│   ├── settings.docker.yaml       # Real-service config (Docker stack)
│   └── plane-nginx.conf           # nginx reverse-proxy for Plane
├── scripts/
│   ├── demo.py                    # Rich CLI demo (run this first!)
│   ├── run_pipeline.py            # CI/CD-friendly pipeline runner
│   └── docker-setup.sh            # Start the full Docker stack
├── src/
│   ├── plane/
│   │   ├── client.py              # PlaneClient (decoy)
│   │   └── models.py              # Issue, Comment, StateTransition
│   ├── kiwi/
│   │   ├── client.py              # KiwiTCMSClient (decoy)
│   │   └── models.py              # TestRun, TestExecution, TestStatus
│   ├── wikijs/
│   │   ├── client.py              # WikiJsClient (decoy)
│   │   └── models.py              # WikiPage
│   ├── harness/
│   │   ├── client.py              # HarnessClient (decoy)
│   │   └── models.py              # ArtifactBundle, PipelineExecution, ExecutionStatus
│   └── integration/
│       ├── pipeline.py            # IntegrationPipeline orchestrator
│       └── workflows.py           # Standalone workflow functions
├── tests/
│   ├── test_plane.py
│   ├── test_kiwi.py
│   ├── test_wikijs.py
│   ├── test_harness.py
│   └── test_integration.py
├── docker-compose.yml             # Plane + Kiwi TCMS + Wiki.js stack
└── .env.docker                    # Environment variable template
```

## Quick Start

### Option A — Decoy mode (no Docker required)

#### 1. Install dependencies

```bash
pip install -r requirements.txt
```

#### 2. Run the demo

```bash
python scripts/demo.py
```

Runs the full pipeline twice — first with 60% pass rate (failure path), then 100% (success + deployment) — with rich terminal output. No credentials needed.

#### 3. Run the pipeline for a specific issue

```bash
python scripts/run_pipeline.py --issue DEMO-101 --env Staging --version 2.1.0
```

| Flag | Default | Description |
|------|---------|-------------|
| `--issue` | required | Plane issue key |
| `--env` | `Production` | Harness CD target environment |
| `--version` | `1.0.0` | Software version under test |
| `--pass-rate` | `1.0` | Fraction of tests that pass (0.0–1.0) |
| `--dry-run` | false | Validate config without executing |
| `--project` | `DEMO` | Plane project identifier |

#### 4. Run the tests

```bash
pytest tests/ -v
```

---

### Option B — Live Docker stack

#### 1. Start the stack

```bash
bash scripts/docker-setup.sh
```

This pulls images, starts all containers, waits for health checks, runs Kiwi TCMS migrations, and creates the Kiwi admin user. First run takes a few minutes.

#### 2. Complete first-time setup in your browser

| Service | URL | Steps |
|---------|-----|-------|
| **Plane** | `http://localhost:80` | Create account → workspace → project (identifier `DEMO`) → Settings → API Tokens → create token |
| **Kiwi TCMS** | `https://localhost:8443` (accept self-signed cert) | Login `admin / admin1234!` → top-right menu → Settings → API → Generate API Key |
| **Wiki.js** | `http://localhost:3000` | Complete setup wizard (PostgreSQL already running) → Administration → API Access → Generate token |

#### 3. Configure credentials

Edit `.env` (auto-created from `.env.docker`) and fill in the tokens:

```bash
PLANE_API_TOKEN=your-plane-token
PLANE_WORKSPACE_SLUG=your-workspace-slug
PLANE_PROJECT_ID=your-project-uuid
KIWI_API_KEY=your-kiwi-api-key
WIKIJS_API_KEY=your-wikijs-token
```

#### 4. Run the pipeline against live services

```bash
python scripts/run_pipeline.py \
  --config config/settings.docker.yaml \
  --issue DEMO-101 --env Production --version 1.0.0
```

#### Useful Docker commands

```bash
docker compose logs -f plane-api    # Plane backend logs
docker compose logs -f kiwi         # Kiwi TCMS logs
docker compose logs -f wikijs       # Wiki.js logs
docker compose ps                   # container status
docker compose down                 # stop stack
docker compose down -v              # stop and delete all data
```

## Configuration

When `use_decoy: true` (default), no network calls are made. To connect to real services, set `use_decoy: false` and provide credentials.

`config/settings.yaml` (decoy defaults):

```yaml
plane:
  base_url: "http://localhost:80"
  api_token: ""
  workspace_slug: "my-workspace"
  project_id: ""
  use_decoy: true

kiwi:
  base_url: "https://localhost:8443"
  username: "admin"
  api_key: ""
  verify_ssl: false
  use_decoy: true

wikijs:
  base_url: "http://localhost:3000"
  api_key: ""
  locale: "en"
  use_decoy: true
```

## Client API Reference

### PlaneClient

| Method | Description |
|--------|-------------|
| `get_issue(key)` | Fetch an issue by key (auto-creates on miss) |
| `create_issue(name, ...)` | Create a new issue |
| `transition_issue(key, state)` | Change issue state |
| `add_comment(key, body)` | Add a comment |
| `get_issues_by_state(state)` | Filter issues by state |
| `link_test_run(key, run_id)` | Link a Kiwi TCMS test run |

### KiwiTCMSClient

| Method | Description |
|--------|-------------|
| `create_test_run(summary, ...)` | Create a test run |
| `get_test_run(run_id)` | Fetch a test run |
| `add_test_cases(run_id, keys)` | Add test cases to a run |
| `record_test_execution(run_id, key, status, ...)` | Record a test execution |
| `get_test_executions(run_id)` | Get all executions for a run |
| `get_run_summary(run_id)` | Pass/fail summary dict |
| `run_all_tests_decoy(run_id, pass_rate)` | Simulate all tests with given pass rate |

### WikiJsClient

| Method | Description |
|--------|-------------|
| `create_page(title, content, path, ...)` | Create a Markdown page |
| `update_page(page_id, title, content, ...)` | Update a page |
| `get_page(page_id)` | Fetch a page by ID |
| `get_pages_in_locale(locale)` | List pages for a locale |
| `create_test_report_page(title, results, ...)` | Create formatted test report (Markdown table) |

### HarnessClient

| Method | Description |
|--------|-------------|
| `create_artifact_bundle(name, ...)` | Create an artifact bundle with pinned service versions |
| `get_service_deployments(project, env)` | Currently deployed service artifact versions |
| `execute_pipeline(artifact_bundle, ...)` | Submit a pipeline execution |
| `get_execution_status(id)` | Poll execution status |
| `wait_for_execution(id, ...)` | Block until execution completes |
| `rollback_execution(id)` | Trigger rollback |

### IntegrationPipeline

```python
from src.plane.client import PlaneClient
from src.kiwi.client import KiwiTCMSClient
from src.wikijs.client import WikiJsClient
from src.harness.client import HarnessClient
from src.integration.pipeline import IntegrationPipeline

pipeline = IntegrationPipeline(
    plane=PlaneClient(project_identifier="DEMO"),
    kiwi=KiwiTCMSClient(product="MyProduct"),
    wikijs=WikiJsClient(),
    harness=HarnessClient(),
    version="1.0.0",
)

result = pipeline.run_qa_pipeline(
    issue_key="DEMO-101",
    pass_rate=1.0,                 # decoy: fraction of tests that pass
    target_environment="Production",
)
# result keys: issue, test_run, report_page, deployment,
#              all_tests_passed, final_status, summary
```

### Standalone Workflows

```python
from src.integration.workflows import (
    sync_plane_to_wikijs,
    deploy_on_test_pass,
    generate_release_notes,
)

# Sync all open Plane issues to Wiki.js pages
pages = sync_plane_to_wikijs(plane, wikijs, states=["In Dev", "In QA"])

# Deploy only if a Kiwi TCMS run fully passes
result = deploy_on_test_pass(kiwi, harness, run_id="RUN-0001")

# Auto-generate release notes from deployed issues
page = generate_release_notes(plane, wikijs, fix_version="2.0.0")
```

## Decoy Mode

All clients default to `use_decoy=True`. In decoy mode:

- No real HTTP calls are made
- All state is stored in-memory within the client instance
- Each method prints a `[PLANE DECOY]` / `[KIWI DECOY]` / `[WIKIJS DECOY]` / `[HARNESS DECOY]` prefixed log showing the simulated REST/GraphQL endpoint and payload
- Simulated network latency of ~100 ms per call via `time.sleep(0.1)`
- IDs use realistic formats: `DEMO-101`, `RUN-0001`, `REQ-000001`, `SNAP-0001`
- Plane states advance: `Open → In Dev → In QA → Deployed` (or `In Dev` on failure)
- Fetching an unknown Plane issue auto-creates a plausible one rather than raising

To use real APIs, pass `use_decoy=False` and supply credentials via `.env` or `config/settings.yaml`.

## Data Models

### Plane

| Class | Key Fields |
|-------|-----------|
| `Issue` | `key`, `name`, `state`, `issue_type`, `priority`, `labels`, `linked_runs`, `comments`, `fix_version` |
| `Comment` | `id`, `body`, `author`, `created` |
| `StateTransition` | `id`, `name`, `from_state`, `to_state`, `performed_at`, `performed_by` |

### Kiwi TCMS

| Class | Key Fields |
|-------|-----------|
| `TestRun` | `id`, `summary`, `product`, `version`, `plane_issue_keys`, `test_case_keys`, `executions`, `status` |
| `TestExecution` | `id`, `test_case_key`, `test_name`, `status`, `comment`, `tested_by`, `tested_at`, `duration_ms` |
| `TestStatus` | `PASSED`, `FAILED`, `BLOCKED`, `IDLE`, `RUNNING`, `WAIVED` |

### Wiki.js

| Class | Key Fields |
|-------|-----------|
| `WikiPage` | `id`, `path`, `title`, `content` (Markdown), `locale`, `description`, `tags`, `author`, `url` |

### Harness CD

| Class | Key Fields |
|-------|-----------|
| `ArtifactBundle` | `id`, `name`, `project`, `pipeline_id`, `environment`, `artifacts` |
| `PipelineExecution` | `id`, `project`, `pipeline_id`, `environment`, `artifact_bundle`, `status`, `log_url` |
| `ExecutionStatus` | `QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`, `ROLLING_BACK`, `ROLLED_BACK` |
| `ServiceArtifact` | `service`, `artifact_tag`, `description` |

## Requirements

- Python 3.10+
- Docker + Docker Compose (for the live stack)

| Package | Version | Purpose |
|---------|---------|---------|
| `requests` | >=2.31.0 | HTTP client (real API mode) |
| `PyYAML` | >=6.0 | Config file parsing |
| `python-dotenv` | >=1.0.0 | `.env` file support |
| `rich` | >=13.0.0 | Terminal UI for the demo script |
| `pytest` | >=7.4.0 | Test runner |
| `pytest-mock` | >=3.11.0 | Mock helpers for unit tests |

---

## JIRA · Confluence · AgileTest · Harness CD Integration

This project also includes a full **Atlassian + Harness CD** integration stack using the same decoy-client pattern. It mirrors the Plane/Kiwi/Wiki.js workflow but targets enterprise tooling: JIRA for issue tracking, **AgileTest for JIRA** for test management, Confluence for documentation, and Harness CD for continuous deployment.

> **AgileTest for JIRA** is a JIRA-native test management app available on the Atlassian Marketplace. Test cases are JIRA issues of type "Test"; test plans collect them for coordinated execution runs. Its REST API lives at `/rest/agiletest/1.0/`.

### Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║        JIRA · AgileTest · Confluence · Harness CD                   ║
║                  CI/CD Integration Architecture                      ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║   ┌──────────┐   ┌──────────────┐   ┌───────────────┐               ║
║   │   JIRA   │──►│  AgileTest   │──►│  Confluence   │               ║
║   │  Issues  │   │  Test Plans  │   │ Test Reports  │               ║
║   └────┬─────┘   └──────┬───────┘   └───────────────┘               ║
║        │                │                                            ║
║        │         (all tests pass?)                                   ║
║        │                │                                            ║
║        │          YES   ▼                                            ║
║        │       ┌──────────────┐                                      ║
║        └──────►│  Harness CD  │  execute pipeline                    ║
║                │  Pipeline    │  artifact bundle → environment       ║
║                └──────┬───────┘                                      ║
║                       │                                              ║
║              SUCCESS  ▼ FAILED                                       ║
║          ┌─────────────┐  ┌────────────────┐                        ║
║          │ JIRA:       │  │ JIRA:          │                        ║
║          │ Deployed ✓  │  │ In Dev +       │                        ║
║          └─────────────┘  │ rollback       │                        ║
║                           └────────────────┘                        ║
╚══════════════════════════════════════════════════════════════════════╝
```

**Tool responsibilities:**

| Tool | Role | Key Concepts |
|------|------|-------------|
| **JIRA** | Issue tracking & project management | Issues, status transitions, comments, fix versions |
| **AgileTest** | JIRA-native test management & execution | Test plans, test cases, test executions, pass/fail reporting |
| **Confluence** | Documentation & test reporting | HTML pages, test report tables, release notes |
| **Harness CD** | Continuous deployment pipeline | Artifact bundles, pipeline executions, rollback |

### Integration Workflow

```
Developer completes feature
          │
          ▼
[JIRA] Issue transitions: Open → In Dev → Ready for QA → In QA
          │
          ▼
[AGILETEST] Test plan created and linked to JIRA issue
          │
          ▼
[AGILETEST] Test cases executed (5 standard cases by default)
          │
          │── Tests PASS ──► [CONFLUENCE] Test report page published (HTML)
          │                              │
          │                              ▼
          │                   [JIRA] Comment added with report URL
          │                              │
          │                              ▼
          │                   [HARNESS CD] Artifact bundle created
          │                              │
          │                              ▼
          │                   [HARNESS CD] Pipeline execution submitted
          │                              │
          │                   SUCCESS ───┤─── FAILED
          │                    │               │
          │                    ▼               ▼
          │             [JIRA] Deployed   [HARNESS CD] Rollback
          │                               [JIRA] In Dev + comment
          │
          └── Tests FAIL ──► [CONFLUENCE] Failure report page published
                                          │
                                          ▼
                              [JIRA] Failed test list comment
                                          │
                                          ▼
                              [JIRA] Issue → In Dev
```

### JIRA Issue States

```
Open ──► In Dev ──► Ready for QA ──► In QA ──► Deployed
                                       │
                                       └──► In Dev  (on test/deploy failure)
```

### Project Structure (JIRA/AgileTest/Confluence modules)

```
src/
├── jira/
│   ├── client.py        # JiraClient (decoy) — REST API simulation
│   └── models.py        # Issue, Comment, Transition
├── agiletest/
│   ├── client.py        # AgiletestClient (decoy) — AgileTest REST API simulation
│   └── models.py        # TestCase, TestPlan, TestExecution, TestStatus
├── confluence/
│   ├── client.py        # ConfluenceClient (decoy) — Confluence REST API simulation
│   └── models.py        # Page
└── harness/
    ├── client.py        # HarnessClient (decoy) — Harness NextGen API simulation
    └── models.py        # ArtifactBundle, PipelineExecution, ExecutionStatus

tests/
├── test_jira.py
├── test_agiletest.py
├── test_confluence.py
└── test_harness.py
```

### Quick Start

#### 1. Install dependencies

```bash
pip install -r requirements.txt
```

#### 2. Run the JIRA + AgileTest + Confluence + Harness pipeline (decoy mode)

```python
from src.jira.client import JiraClient
from src.agiletest.client import AgiletestClient
from src.confluence.client import ConfluenceClient
from src.harness.client import HarnessClient

# Initialise clients (all in decoy mode — no credentials needed)
jira       = JiraClient(base_url="https://prasenjeet-tembhurne.atlassian.net", project_key="Prasen")
agiletest  = AgiletestClient(base_url="https://prasenjeet-tembhurne.atlassian.net", project_key="Prasen")
confluence = ConfluenceClient(base_url="https://prasenjeet-tembhurne.atlassian.net/wiki", space_key="Prasen")
harness    = HarnessClient(project="MyProject", environment="Production")

# Step 1 — create / fetch a JIRA issue
issue = jira.create_issue(
    summary="Implement OAuth2 login flow",
    issue_type="Story",
    priority="High",
    labels=["auth", "sprint-42"],
    fix_version="2.0.0",
)
jira.transition_issue(issue.key, "In QA")

# Step 2 — create an AgileTest test plan linked to the issue
plan = agiletest.create_test_plan(
    name=f"{issue.key} — v2.0.0 QA Plan",
    jira_issue_keys=[issue.key],
    version="2.0.0",
)
agiletest.add_test_cases(plan.id, ["DEMO-T1", "DEMO-T2", "DEMO-T3", "DEMO-T4", "DEMO-T5"])
jira.link_test_cycle(issue.key, plan.id)   # stores plan ID on the JIRA issue

# Step 3 — execute all tests (decoy, 100% pass rate)
executions = agiletest.run_all_tests_decoy(plan.id, pass_rate=1.0)
summary = agiletest.get_plan_summary(plan.id)
print(f"Results: {summary['passed']}/{summary['total']} passed ({summary['pass_rate']}%)")

# Step 4 — publish Confluence test report
report = confluence.create_test_report_page(
    title=f"Test Report — {issue.key} — v2.0.0",
    test_results=[e.to_dict() for e in executions],
)
jira.add_comment(
    issue.key,
    f"Test report: {report.url}\n{summary['passed']}/{summary['total']} passed",
)

# Step 5 — deploy if all tests passed
if summary["all_passed"]:
    bundle = harness.create_artifact_bundle(
        name="MyProject-v2.0.0",
        environment="Production",
    )
    execution = harness.execute_pipeline(artifact_bundle=bundle, environment="Production")
    final_status = harness.wait_for_execution(execution.id)

    if final_status.value == "SUCCESS":
        jira.transition_issue(issue.key, "Deployed")
        jira.add_comment(issue.key, f"Deployed via Harness. Execution: {execution.id}")
    else:
        harness.rollback_execution(execution.id)
        jira.add_comment(
            issue.key,
            f"Deployment FAILED. Rollback triggered. ID: {execution.id}",
        )
        jira.transition_issue(issue.key, "In Dev")
else:
    jira.transition_issue(issue.key, "In Dev")
```

#### 3. Run the tests

```bash
# All tests
pytest tests/ -v

# Just the Atlassian/Harness stack
pytest tests/test_jira.py tests/test_agiletest.py tests/test_confluence.py tests/test_harness.py -v
```

### Credentials Configuration

To connect to real Atlassian + Harness services, add to `.env`:

```bash
# JIRA / AgileTest / Confluence — same Atlassian account API token
JIRA_BASE_URL=https://prasenjeet-tembhurne.atlassian.net
JIRA_USERNAME=you@example.com
JIRA_API_TOKEN=your-atlassian-api-token
JIRA_PROJECT_KEY=Prasen

CONFLUENCE_BASE_URL=https://prasenjeet-tembhurne.atlassian.net/wiki
CONFLUENCE_SPACE_KEY=Prasen

# AgileTest API key — generated in JIRA → Apps → AgileTest → Settings → API Keys
AGILETEST_API_KEY=your-agiletest-api-key

# Harness CD
HARNESS_BASE_URL=https://app.harness.io
HARNESS_API_KEY=your-harness-api-key
HARNESS_ACCOUNT_ID=your-account-id
HARNESS_ORG_ID=your-org-id
HARNESS_PROJECT=your-project-identifier
HARNESS_PIPELINE_ID=deploy
```


And initialise clients with `use_decoy=False`:

```python
import os
from src.jira.client import JiraClient
from src.agiletest.client import AgiletestClient
from src.confluence.client import ConfluenceClient
from src.harness.client import HarnessClient

jira = JiraClient(
    base_url=os.environ["JIRA_BASE_URL"],
    username=os.environ["JIRA_USERNAME"],
    api_token=os.environ["JIRA_API_TOKEN"],
    project_key=os.environ["JIRA_PROJECT_KEY"],
    use_decoy=False,
)
agiletest = AgiletestClient(
    base_url=os.environ["JIRA_BASE_URL"],
    api_key=os.environ["AGILETEST_API_KEY"],
    project_key=os.environ["JIRA_PROJECT_KEY"],
    use_decoy=False,
)
confluence = ConfluenceClient(
    base_url=os.environ["CONFLUENCE_BASE_URL"],
    space_key=os.environ["CONFLUENCE_SPACE_KEY"],
    username=os.environ["JIRA_USERNAME"],
    api_token=os.environ["JIRA_API_TOKEN"],
    use_decoy=False,
)
harness = HarnessClient(
    base_url=os.environ["HARNESS_BASE_URL"],
    api_key=os.environ["HARNESS_API_KEY"],
    account_id=os.environ["HARNESS_ACCOUNT_ID"],
    org_id=os.environ["HARNESS_ORG_ID"],
    project=os.environ["HARNESS_PROJECT"],
    pipeline_id=os.environ["HARNESS_PIPELINE_ID"],
    use_decoy=False,
)
```

### Client API Reference

#### JiraClient

| Method | REST Endpoint | Description |
|--------|--------------|-------------|
| `get_issue(key)` | `GET /rest/api/3/issue/{key}` | Fetch issue by key (auto-creates on miss) |
| `create_issue(summary, ...)` | `POST /rest/api/3/issue` | Create a new issue |
| `transition_issue(key, status)` | `POST /rest/api/3/issue/{key}/transitions` | Change issue status |
| `add_comment(key, comment)` | `POST /rest/api/3/issue/{key}/comment` | Add a comment |
| `get_issues_by_status(status)` | `GET /rest/api/3/search?jql=status=...` | Filter issues by status |
| `link_test_cycle(key, plan_id)` | `POST /rest/api/3/issue/{key}/remotelink` | Link an AgileTest plan to an issue |

#### AgiletestClient

| Method | REST Endpoint | Description |
|--------|--------------|-------------|
| `create_test_plan(name, ...)` | `POST /rest/agiletest/1.0/testplan` | Create a test plan |
| `get_test_plan(plan_id)` | `GET /rest/agiletest/1.0/testplan/{id}` | Fetch a test plan |
| `add_test_cases(plan_id, keys)` | `POST /rest/agiletest/1.0/testplan/{id}/testcases` | Add test cases to a plan |
| `execute_test(plan_id, key, status, ...)` | `POST /rest/agiletest/1.0/testexecution` | Record a test execution |
| `get_test_executions(plan_id)` | `GET /rest/agiletest/1.0/testexecution?planId=...` | Get all executions for a plan |
| `get_plan_summary(plan_id)` | `GET /rest/agiletest/1.0/testplan/{id}/summary` | Pass/fail summary dict |
| `run_all_tests_decoy(plan_id, pass_rate)` | *(decoy only)* | Execute all tests with a given pass rate |

#### ConfluenceClient

| Method | REST Endpoint | Description |
|--------|--------------|-------------|
| `create_page(title, content, ...)` | `POST /wiki/rest/api/content` | Create a Confluence page |
| `update_page(page_id, title, content, ...)` | `PUT /wiki/rest/api/content/{id}` | Update an existing page |
| `get_page(page_id)` | `GET /wiki/rest/api/content/{id}` | Fetch a page by ID |
| `get_pages_in_space(space_key)` | `GET /wiki/rest/api/content?spaceKey=...` | List pages in a space |
| `create_test_report_page(title, results, ...)` | `POST /wiki/rest/api/content` | Create a formatted HTML test report page |

#### HarnessClient

| Method | REST Endpoint | Description |
|--------|--------------|-------------|
| `create_artifact_bundle(name, ...)` | `POST /ng/api/artifactBundles` | Create a bundle of pinned service artifact versions |
| `execute_pipeline(artifact_bundle, ...)` | `POST /pipeline/api/pipelines/execution/v2` | Submit a pipeline execution |
| `get_execution_status(execution_id)` | `GET /pipeline/api/pipelines/execution/v2/{id}` | Poll execution status |
| `wait_for_execution(execution_id, ...)` | *(polls above)* | Block until execution reaches terminal status |
| `rollback_execution(execution_id)` | `POST /pipeline/api/pipelines/execution/v2/{id}/rollback` | Trigger rollback |
| `get_service_deployments(project, env)` | `GET /ng/api/services/deployments` | Currently deployed service artifact versions |

### Data Models

#### JIRA

| Class | Key Fields |
|-------|-----------|
| `Issue` | `key`, `summary`, `description`, `status`, `issue_type`, `priority`, `assignee`, `reporter`, `labels`, `linked_cycles`, `comments`, `fix_version` |
| `Comment` | `id`, `body`, `author`, `created`, `updated` |
| `Transition` | `id`, `name`, `from_status`, `to_status`, `performed_at`, `performed_by` |

#### AgileTest

| Class | Key Fields |
|-------|-----------|
| `TestCase` | `key`, `name`, `description`, `steps`, `labels`, `priority`, `folder` |
| `TestPlan` | `id`, `name`, `project_key`, `version`, `jira_issue_keys`, `test_case_keys`, `executions`, `status` |
| `TestExecution` | `id`, `test_case_key`, `test_name`, `status`, `plan_id`, `comment`, `executed_by`, `executed_at`, `duration_ms` |
| `TestStatus` | `PASS`, `FAIL`, `BLOCKED`, `UNEXECUTED`, `IN_PROGRESS` |

#### Confluence

| Class | Key Fields |
|-------|-----------|
| `Page` | `id`, `title`, `content` (HTML), `space_key`, `version`, `author`, `url`, `parent_id`, `labels` |

#### Harness CD

| Class | Key Fields |
|-------|-----------|
| `ArtifactBundle` | `id`, `name`, `project`, `pipeline_id`, `environment`, `artifacts` |
| `PipelineExecution` | `id`, `project`, `pipeline_id`, `environment`, `artifact_bundle`, `status`, `log_url` |
| `ExecutionStatus` | `QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`, `ROLLING_BACK`, `ROLLED_BACK` |
| `ServiceArtifact` | `service`, `artifact_tag`, `description` |

### Decoy Mode Behaviour

| Client | ID format | Log prefix | Auto-seeding |
|--------|-----------|-----------|-------------|
| `JiraClient` | `DEMO-101` | `[JIRA DECOY]` | Auto-creates issue on first `get_issue()` miss |
| `AgiletestClient` | `PLAN-0001`, `DEMO-T1` | `[AGILETEST DECOY]` | Seeds 5 realistic test cases on init |
| `ConfluenceClient` | 9-digit numeric | `[CONFLUENCE DECOY]` | None — pages are created explicitly |
| `HarnessClient` | `BNDL-0001`, `EXEC-000001` | `[HARNESS DECOY]` | None — bundles/executions created explicitly |

All clients simulate ~100 ms network latency per call via `time.sleep(0.1)`. No real HTTP calls are made in decoy mode.

### Comparison: Atlassian Stack vs Open-Source Stack

| Capability | Atlassian + Harness | Open-Source |
|-----------|---------------------|-------------|
| Issue tracking | JIRA | Plane |
| Test management | AgileTest for JIRA | Kiwi TCMS |
| Documentation | Confluence | Wiki.js |
| Deployment | Harness CD | Harness CD |
| Hosting | Cloud (SaaS) or Data Center | Self-hosted (Docker) |
| Auth | Atlassian API token + AgileTest API key | Per-service API key/token |
| Test report format | HTML (Confluence storage format) | Markdown (Wiki.js) |
| Test plan concept | Test Plan (`PLAN-0001`) | Test Run (`RUN-0001`) |

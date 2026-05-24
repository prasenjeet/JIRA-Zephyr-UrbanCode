import os
from src.jira.client import JiraClient
from src.agiletest.client import AgiletestClient
from src.confluence.client import ConfluenceClient
from src.harness.client import HarnessClient

# Initialise clients (all in decoy mode — no credentials needed)
#jira       = JiraClient(base_url="https://prasenjeet-tembhurne.atlassian.net", project_key="Prasen")
#agiletest  = AgiletestClient(base_url="https://prasenjeet-tembhurne.atlassian.net", project_key="Prasen")
#confluence = ConfluenceClient(base_url="https://prasenjeet-tembhurne.atlassian.net/wiki", space_key="Prasen")
#harness    = HarnessClient(project="Prasen", environment="Production")



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
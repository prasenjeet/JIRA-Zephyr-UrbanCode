"""JIRA client factory.

Usage::

    from src.jira.client import JiraClient

    # Decoy mode (default) — no real credentials needed
    client = JiraClient(project_key="DEMO")

    # Real mode — calls the live Atlassian JIRA REST API
    client = JiraClient(
        base_url="https://yourorg.atlassian.net",
        username="you@company.com",
        api_token="your-api-token",
        use_decoy=False,
    )
"""
from __future__ import annotations

from typing import Optional

from .base import BaseJiraClient
from .decoy import DecoyJiraClient
from .real import RealJiraClient


def JiraClient(
    base_url: str = "https://your-org.atlassian.net",
    username: str = "decoy@example.com",
    api_token: str = "decoy-token",
    project_key: str = "DEMO",
    use_decoy: bool = True,
    **kwargs,
) -> BaseJiraClient:
    """Factory that returns a :class:`DecoyJiraClient` or :class:`RealJiraClient`.

    Args:
        base_url: JIRA instance URL.
        username: Atlassian account email (ignored in decoy mode).
        api_token: Atlassian API token (ignored in decoy mode).
        project_key: Default project key.
        use_decoy: When ``True`` (default), returns an in-memory mock client.
            Set to ``False`` to call the live JIRA REST API.
        **kwargs: Extra keyword arguments forwarded to the concrete client.

    Returns:
        A :class:`BaseJiraClient` implementation.
    """
    if use_decoy:
        return DecoyJiraClient(
            base_url=base_url,
            username=username,
            api_token=api_token,
            project_key=project_key,
            **kwargs,
        )
    return RealJiraClient(
        base_url=base_url,
        username=username,
        api_token=api_token,
        project_key=project_key,
        **kwargs,
    )


__all__ = ["JiraClient", "BaseJiraClient", "DecoyJiraClient", "RealJiraClient"]

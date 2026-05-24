"""Confluence client factory.

Usage::

    from src.confluence.client import ConfluenceClient

    # Decoy mode (default) — no real credentials needed
    client = ConfluenceClient(space_key="DEMO")

    # Real mode — calls the live Atlassian Confluence REST API
    client = ConfluenceClient(
        base_url="https://yourorg.atlassian.net/wiki",
        username="you@company.com",
        api_token="your-api-token",
        use_decoy=False,
    )
"""
from __future__ import annotations

from typing import Optional

from .base import BaseConfluenceClient
from .decoy import DecoyConfluenceClient
from .real import RealConfluenceClient


def ConfluenceClient(
    base_url: str = "https://your-org.atlassian.net/wiki",
    space_key: str = "DEMO",
    username: str = "decoy@example.com",
    api_token: str = "decoy-token",
    use_decoy: bool = True,
    **kwargs,
) -> BaseConfluenceClient:
    """Factory that returns a :class:`DecoyConfluenceClient` or :class:`RealConfluenceClient`.

    Args:
        base_url: Confluence instance URL.
        space_key: Default Confluence space key.
        username: Atlassian account email (ignored in decoy mode).
        api_token: Atlassian API token (ignored in decoy mode).
        use_decoy: When ``True`` (default), returns an in-memory mock client.
            Set to ``False`` to call the live Confluence REST API.
        **kwargs: Extra keyword arguments forwarded to the concrete client.

    Returns:
        A :class:`BaseConfluenceClient` implementation.
    """
    if use_decoy:
        return DecoyConfluenceClient(
            base_url=base_url,
            space_key=space_key,
            username=username,
            api_token=api_token,
            **kwargs,
        )
    return RealConfluenceClient(
        base_url=base_url,
        username=username,
        api_token=api_token,
        space_key=space_key,
        **kwargs,
    )


__all__ = [
    "ConfluenceClient",
    "BaseConfluenceClient",
    "DecoyConfluenceClient",
    "RealConfluenceClient",
]

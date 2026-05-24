"""Zephyr Scale client factory.

Usage::

    from src.zephyr.client import ZephyrClient

    # Decoy mode (default) — no real credentials needed
    client = ZephyrClient(project_key="DEMO")

    # Real mode — calls the live Zephyr Scale Cloud API
    client = ZephyrClient(
        api_token="your-zephyr-token",
        project_key="DEMO",
        use_decoy=False,
    )
"""
from __future__ import annotations

from .base import BaseZephyrClient
from .decoy import DecoyZephyrClient
from .real import RealZephyrClient


def ZephyrClient(
    base_url: str = "https://your-org.atlassian.net",
    api_token: str = "decoy-zephyr-token",
    project_key: str = "DEMO",
    use_decoy: bool = True,
    **kwargs,
) -> BaseZephyrClient:
    """Factory that returns a :class:`DecoyZephyrClient` or :class:`RealZephyrClient`.

    Args:
        base_url: Zephyr/JIRA instance base URL (used in decoy mode).
        api_token: Zephyr Scale API token.
        project_key: Default JIRA/Zephyr project key.
        use_decoy: When ``True`` (default), returns an in-memory mock client.
            Set to ``False`` to call the live Zephyr Scale Cloud API.
        **kwargs: Extra keyword arguments forwarded to the concrete client.

    Returns:
        A :class:`BaseZephyrClient` implementation.
    """
    if use_decoy:
        return DecoyZephyrClient(
            base_url=base_url,
            api_token=api_token,
            project_key=project_key,
            **kwargs,
        )
    return RealZephyrClient(
        api_token=api_token,
        project_key=project_key,
        **kwargs,
    )


__all__ = ["ZephyrClient", "BaseZephyrClient", "DecoyZephyrClient", "RealZephyrClient"]

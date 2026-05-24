"""UrbanCode Deploy client factory.

Usage::

    from src.urbancode.client import UrbanCodeClient

    # Decoy mode (default) — no real credentials needed
    client = UrbanCodeClient(application="MyApp", environment="Production")

    # Real mode — calls the live UrbanCode Deploy REST API
    client = UrbanCodeClient(
        base_url="https://ucd-server:8443",
        username="admin",
        password="secret",
        use_decoy=False,
    )
"""
from __future__ import annotations

from .base import BaseUrbanCodeClient
from .decoy import DecoyUrbanCodeClient
from .real import RealUrbanCodeClient


def UrbanCodeClient(
    base_url: str = "https://your-urbancode-server:8443",
    username: str = "admin",
    password: str = "decoy-password",
    application: str = "MyApp",
    environment: str = "Production",
    use_decoy: bool = True,
    **kwargs,
) -> BaseUrbanCodeClient:
    """Factory that returns a :class:`DecoyUrbanCodeClient` or :class:`RealUrbanCodeClient`.

    Args:
        base_url: UCD server base URL.
        username: UCD username.
        password: UCD password (ignored in decoy mode).
        application: Default application name.
        environment: Default target environment.
        use_decoy: When ``True`` (default), returns an in-memory mock client.
            Set to ``False`` to call the live UCD REST API.
        **kwargs: Extra keyword arguments forwarded to the concrete client.

    Returns:
        A :class:`BaseUrbanCodeClient` implementation.
    """
    if use_decoy:
        return DecoyUrbanCodeClient(
            base_url=base_url,
            username=username,
            password=password,
            application=application,
            environment=environment,
            **kwargs,
        )
    return RealUrbanCodeClient(
        base_url=base_url,
        username=username,
        password=password,
        application=application,
        environment=environment,
        **kwargs,
    )


__all__ = [
    "UrbanCodeClient",
    "BaseUrbanCodeClient",
    "DecoyUrbanCodeClient",
    "RealUrbanCodeClient",
]

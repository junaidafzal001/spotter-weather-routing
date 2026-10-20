"""Shared outbound HTTP client."""
from __future__ import annotations

import httpx
from django.conf import settings


def client() -> httpx.Client:
    return httpx.Client(
        timeout=httpx.Timeout(settings.PROVIDER_TIMEOUT_SECONDS),
        headers={"User-Agent": settings.APP_USER_AGENT, "Accept": "application/json"},
        follow_redirects=True,
    )

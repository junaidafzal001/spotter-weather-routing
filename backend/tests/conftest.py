"""Shared test helpers: fixture loading, cache isolation, throttling."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture(autouse=True)
def _no_nominatim_throttle(monkeypatch):
    from services.geocoding import nominatim

    monkeypatch.setattr(nominatim, "_throttle", lambda: None)


@pytest.fixture(autouse=True)
def _isolated_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()

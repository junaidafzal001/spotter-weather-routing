"""Nominatim adapter with request throttling."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from django.conf import settings

from services.errors import GeocodingError
from services.http import client

_MIN_INTERVAL_S = 1.05  # keep us safely under the public 1 req/s cap
_throttle_lock = threading.Lock()
_last_call_monotonic = 0.0


@dataclass(frozen=True)
class GeoPlace:
    query: str
    display_name: str
    lat: float
    lon: float
    provider: str = "nominatim"

    @property
    def coord(self) -> tuple[float, float]:  # (lon, lat)
        return (self.lon, self.lat)


def _throttle() -> None:
    global _last_call_monotonic
    with _throttle_lock:
        wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call_monotonic)
        if wait > 0:
            time.sleep(wait)
        _last_call_monotonic = time.monotonic()


def _search(query: str, limit: int) -> list[GeoPlace]:
    params = {
        "q": query,
        "format": "jsonv2",
        "limit": limit,
        "addressdetails": 0,
    }
    _throttle()
    try:
        with client() as c:
            resp = c.get(f"{settings.NOMINATIM_BASE_URL}/search", params=params)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:  # network, timeout, HTTP, JSON errors
        raise GeocodingError(f"Nominatim geocoding failed: {exc}") from exc

    places: list[GeoPlace] = []
    for item in payload[:limit]:
        try:
            places.append(
                GeoPlace(
                    query=query,
                    display_name=item["display_name"],
                    lat=float(item["lat"]),
                    lon=float(item["lon"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return places


def geocode(query: str) -> GeoPlace | None:
    places = _search(query, limit=1)
    return places[0] if places else None


def suggest(query: str, limit: int = 5) -> list[GeoPlace]:
    if len(query.strip()) < 3:
        return []
    return _search(query.strip(), limit=limit)

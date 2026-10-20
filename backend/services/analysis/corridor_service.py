"""0-48h corridor heatmap lattice."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from django.conf import settings
from django.core.cache import cache

from services.errors import ServiceError
from services.geo.corridor import CorridorPoint, build_corridor_points
from services.risk.engine import assess_checkpoint
from services.weather import open_meteo

logger = logging.getLogger(__name__)

SLIDER_HOURS = 48  # 0..48 inclusive -> 49 slices
_CORRIDOR_CACHE_TTL = settings.WEATHER_CACHE_TTL


def _load_analysis(analysis_id: str) -> dict:
    cached = cache.get(f"analysis:{analysis_id}")
    if cached is None:
        raise ServiceError(
            "Analysis not found or expired — re-run the trip analysis.",
            code="analysis_not_found",
            status=404,
        )
    return cached


def build_corridor(analysis_id: str, route_id: str) -> dict:
    analysis = _load_analysis(analysis_id)
    routes = analysis.get("routes") or {}
    if route_id not in routes:
        raise ServiceError(
            f"Unknown route_id '{route_id}' for this analysis.",
            code="route_not_found",
            status=404,
        )
    entry = routes[route_id]
    coords = [tuple(c) for c in entry["coordinates"]]
    load_weight_lbs = int(analysis["inputs"]["load_weight_lbs"])

    cache_key = f"corridor:{analysis_id}:{route_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    points: list[CorridorPoint] = build_corridor_points(coords)
    if not points:
        raise ServiceError("Route geometry too short to build a corridor.", code="corridor_empty", status=422)

    now = datetime.now(UTC)
    forecasts = open_meteo.fetch_hourly_forecasts([(p.lat, p.lon) for p in points], forecast_days=3)

    # Anchor at the current hour; each slider position keeps its own forecast hour.
    t0 = forecasts[0].times_utc[0]
    start_idx = max(0, int((now.replace(minute=0, second=0, microsecond=0) - t0).total_seconds() // 3600))
    max_start = max(0, len(forecasts[0].times_utc) - (SLIDER_HOURS + 1))
    start_idx = min(start_idx, max_start)
    n_hours = min(SLIDER_HOURS + 1, len(forecasts[0].times_utc) - start_idx)
    if n_hours <= 0:
        raise ServiceError("Forecast window is not available yet.", code="forecast_unavailable", status=503)

    hours = [forecasts[0].times_utc[start_idx + i] for i in range(n_hours)]

    point_payloads: list[dict] = []
    for pt, fc in zip(points, forecasts, strict=True):
        severity_by_hour: list[str] = []
        values_by_hour: list[dict] = []
        for i in range(n_hours):
            wind = fc.wind_mph[start_idx + i]
            rain = fc.rain_in_hr[start_idx + i]
            snow = fc.snow_in_hr[start_idx + i]
            risk = assess_checkpoint(
                wind_mph=wind, rain_in_hr=rain, snow_in_hr=snow, load_weight_lbs=load_weight_lbs
            )
            severity_by_hour.append(risk.level if risk.available else "UNKNOWN")
            values_by_hour.append(
                {
                    "wind_mph": _round(wind, 1),
                    "rain_in_hr": _round(rain, 3),
                    "snow_in_hr": _round(snow, 3),
                }
            )
        point_payloads.append(
            {
                "lat": round(pt.lat, 5),
                "lon": round(pt.lon, 5),
                "mile": pt.mile,
                "offset_miles": pt.offset_miles,
                "severity_by_hour": severity_by_hour,
                "values_by_hour": values_by_hour,
            }
        )

    payload = {
        "analysis_id": analysis_id,
        "route_id": route_id,
        "load_weight_lbs": load_weight_lbs,
        "generated_at": now.isoformat(),
        "slider_start_utc": hours[0].isoformat(),
        "hours": [h.isoformat() for h in hours],
        "points": point_payloads,
        "notes": [
            "Heatmap intensity is a spatial interpolation (kernel density) between sample "
            "locations — an estimate of corridor-wide conditions, not point observations.",
            "Each slider hour shows the forecast for its own timestamp; this time-slice view is "
            "independent of the per-checkpoint ETA weather used for route risk.",
        ],
    }
    cache.set(cache_key, payload, _CORRIDOR_CACHE_TTL)
    return payload


def _round(v: float | None, digits: int) -> float | None:
    return None if v is None else round(v, digits)

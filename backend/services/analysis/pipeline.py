"""Trip analysis: geocode, route, checkpoints, weather, risk, recommendation."""
from __future__ import annotations

import hashlib
import logging
import math
import uuid
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.core.cache import cache

from services.analysis.checkpoints import Checkpoint, build_checkpoints
from services.errors import GeocodeNotFoundError, ServiceError, ValidationError
from services.geo.geometry import interpolate_coordinate, meters_to_miles
from services.geocoding import nominatim
from services.recommendation.exposure import RouteExposure, compute_exposure
from services.recommendation.ranker import recommend
from services.risk.engine import assess_checkpoint
from services.risk.severity import Severity
from services.routing import service as routing_service
from services.routing.base import RouteGeometry
from services.weather import open_meteo, selection

logger = logging.getLogger(__name__)

_FORECAST_MAX_DAYS = open_meteo.MAX_FORECAST_DAYS


def _geocode_cached(query: str, role: str) -> nominatim.GeoPlace:
    key = "geocode:" + hashlib.sha1(query.strip().lower().encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return cached
    place = nominatim.geocode(query)
    if place is None:
        raise GeocodeNotFoundError(
            f"Could not resolve {role} location: '{query}'. Try a city, state, or postal code.",
            fields={role: f"No match for '{query}'"},
        )
    cache.set(key, place, settings.GEOCODE_CACHE_TTL)
    return place


def plan_forecast_days(departure_utc: datetime, max_duration_s: float, now: datetime | None = None) -> int | None:
    now = now or datetime.now(UTC)
    lead_h = max(0.0, (departure_utc - now).total_seconds() / 3600.0)
    horizon_h = lead_h + max_duration_s / 3600.0 + 6.0  # 6 h margin
    if horizon_h > _FORECAST_MAX_DAYS * 24:
        return None
    return max(2, min(math.ceil(horizon_h / 24.0), _FORECAST_MAX_DAYS))


def slice_geometry_between(
    coords: list[tuple[float, float]],
    cumdist: list[float],
    m0: float,
    m1: float,
) -> list[tuple[float, float]]:
    m1 = min(m1, cumdist[-1])
    p0 = interpolate_coordinate(coords, cumdist, m0)
    p1 = interpolate_coordinate(coords, cumdist, m1)
    inner = [c for i, c in enumerate(coords) if m0 < cumdist[i] < m1]
    return [p0, *inner, p1]


def run_analysis(
    *,
    origin_query: str,
    destination_query: str,
    departure_time: datetime,
    load_weight_lbs: int,
    checkpoint_interval_miles: int,
) -> dict:
    warnings: list[str] = []
    departure_utc = departure_time.astimezone(UTC)
    now = datetime.now(UTC)

    if departure_utc < now - timedelta(minutes=5):
        raise ValidationError(
            "departure_time must not be in the past",
            fields={"departure_time": "Received a timestamp in the past"},
        )

    origin_place = _geocode_cached(origin_query, "origin")
    dest_place = _geocode_cached(destination_query, "destination")

    if origin_place.coord == dest_place.coord:
        raise ValidationError(
            "Origin and destination resolve to the same location",
            fields={"destination": "Pick a destination different from the origin"},
        )

    routes, route_warnings = routing_service.get_routes(origin_place.coord, dest_place.coord)
    warnings.extend(route_warnings)

    routes_by_id: dict[str, RouteGeometry] = {}
    for i, route in enumerate(routes, start=1):
        routes_by_id[f"route-{i}"] = route

    checkpoints_by_id: dict[str, list[Checkpoint]] = {
        rid: build_checkpoints(
            coords=r.coordinates,
            cumdist_m=r.cumdist_m,
            cumdur_s=r.cumdur_s,
            interval_miles=checkpoint_interval_miles,
            departure_utc=departure_utc,
        )
        for rid, r in routes_by_id.items()
    }

    max_duration_s = max(r.duration_s for r in routes_by_id.values())
    forecast_days = plan_forecast_days(departure_utc, max_duration_s, now)

    forecast_by_pt: dict[tuple[float, float], open_meteo.HourlyForecast] = {}
    if forecast_days is None:
        warnings.append(
            "Departure plus trip duration lies beyond the 16-day forecast horizon; "
            "weather (and therefore risk) is marked UNKNOWN for all checkpoints."
        )
    else:
        wx_points: list[tuple[float, float]] = []
        for cps in checkpoints_by_id.values():
            for cp in cps:
                key = (round(cp.coord[1], 4), round(cp.coord[0], 4))  # (lat, lon)
                if key not in forecast_by_pt:
                    wx_points.append(key)
        try:
            forecasts = open_meteo.fetch_hourly_forecasts(wx_points, forecast_days=forecast_days)
            for (lat, lon), fc in zip(wx_points, forecasts, strict=True):
                forecast_by_pt[(lat, lon)] = fc
            for fc in forecasts:
                warnings.extend(fc.unit_notes)
        except ServiceError as exc:
            warnings.append(f"Weather provider unavailable ({exc.detail}); risk marked UNKNOWN where data is missing.")

    def forecast_for(cp: Checkpoint) -> open_meteo.HourlyForecast | None:
        return forecast_by_pt.get((round(cp.coord[1], 4), round(cp.coord[0], 4)))

    route_payloads: list[dict] = []
    exposures: dict[str, RouteExposure] = {}
    unassessed_any = False

    for rid, route in routes_by_id.items():
        cps = checkpoints_by_id[rid]
        checkpoint_dicts: list[dict] = []
        severities: list[Severity | None] = []

        for cp in cps:
            fc = forecast_for(cp)
            sample = (
                selection.sample_at(fc, cp.eta)
                if fc is not None
                else selection.WeatherSample(
                    available=False, eta_utc=cp.eta, unavailability_reason="no forecast data for this location"
                )
            )
            risk = assess_checkpoint(
                wind_mph=sample.wind_mph,
                rain_in_hr=sample.rain_in_hr,
                snow_in_hr=sample.snow_in_hr,
                load_weight_lbs=load_weight_lbs,
            )
            if not risk.available:
                unassessed_any = True
            severities.append(risk.severity if risk.available else None)
            checkpoint_dicts.append(
                {
                    "index": cp.index,
                    "mile": cp.mile,
                    "coordinates": [round(cp.coord[0], 6), round(cp.coord[1], 6)],
                    "eta": cp.eta.isoformat(),
                    "weather": sample.to_dict(),
                    "risk": {
                        "available": risk.available,
                        "level": risk.level if risk.available else "UNKNOWN",
                        "score": risk.score if risk.available else None,
                        "contributions": {
                            "wind": risk.wind_severity.label if risk.wind_severity is not None else None,
                            "rain": risk.rain_severity.label if risk.rain_severity is not None else None,
                            "snow": risk.snow_severity.label if risk.snow_severity is not None else None,
                        },
                        "load_rule_applied": risk.load_rule_applied,
                        "complete": risk.complete,
                    },
                }
            )

        exposure = compute_exposure(
            checkpoint_miles=[cp.mile for cp in cps],
            checkpoint_severities=severities,
            route_distance_m=route.cumdist_m[-1],
        )
        exposures[rid] = exposure

        # Segments colored by the worse endpoint of each interval
        segments: list[dict] = []
        for i in range(len(cps) - 1):
            s0, s1 = severities[i], severities[i + 1]
            level = max(s0, s1).label if (s0 is not None and s1 is not None) else None
            segments.append(
                {
                    "from_mile": cps[i].mile,
                    "to_mile": cps[i + 1].mile,
                    "level": level,
                    "coordinates": [
                        [round(x, 6), round(y, 6)]
                        for x, y in slice_geometry_between(
                            route.coordinates, route.cumdist_m, cps[i].target_m, cps[i + 1].target_m
                        )
                    ],
                }
            )

        route_warnings = list(route.warnings)
        if exposure.unassessed_share > 0:
            route_warnings.append(
                f"Weather could not be assessed for {exposure.unassessed_share:.0%} of this route "
                "(checkpoints outside the forecast window or provider gaps)."
            )

        route_payloads.append(
            {
                "id": rid,
                "provider": route.provider,
                "profile": route.profile,
                "timing_source": route.timing_source,
                "distance_miles": round(meters_to_miles(route.distance_m), 2),
                "duration_minutes": round(route.duration_s / 60.0, 1),
                "departure_time": departure_utc.isoformat(),
                "arrival_time": (departure_utc + timedelta(seconds=route.duration_s)).isoformat(),
                "checkpoint_count": len(cps),
                "checkpoints": checkpoint_dicts,
                "segments": segments,
                "exposure": exposure.to_dict(),
                "warnings": route_warnings,
            }
        )

    rec = recommend(
        routes={rid: exposures[rid] for rid in exposures},
        durations_s={rid: routes_by_id[rid].duration_s for rid in routes_by_id},
    )

    if unassessed_any:
        warnings.append(
            "Some checkpoints have UNKNOWN weather (outside the forecast range or provider gaps); "
            "UNKNOWN is never counted as safe."
        )

    analysis_id = uuid.uuid4().hex
    cache.set(
        f"analysis:{analysis_id}",
        {
            "inputs": {
                "origin": origin_place.display_name,
                "destination": dest_place.display_name,
                "departure_time_utc": departure_utc.isoformat(),
                "load_weight_lbs": load_weight_lbs,
                "checkpoint_interval_miles": checkpoint_interval_miles,
            },
            "routes": {
                rid: {
                    "coordinates": routes_by_id[rid].coordinates,
                    "cumdist_m": routes_by_id[rid].cumdist_m,
                    "provider": routes_by_id[rid].provider,
                    "profile": routes_by_id[rid].profile,
                }
                for rid in routes_by_id
            },
        },
        settings.ANALYSIS_CACHE_TTL,
    )

    return {
        "analysis_id": analysis_id,
        "request": {
            "origin": {
                "input": origin_query,
                "resolved": origin_place.display_name,
                "lat": origin_place.lat,
                "lon": origin_place.lon,
            },
            "destination": {
                "input": destination_query,
                "resolved": dest_place.display_name,
                "lat": dest_place.lat,
                "lon": dest_place.lon,
            },
            "departure_time_utc": departure_utc.isoformat(),
            "load_weight_lbs": load_weight_lbs,
            "checkpoint_interval_miles": checkpoint_interval_miles,
        },
        "routes": route_payloads,
        "recommendation": rec.to_dict(),
        "warnings": warnings,
        "meta": {
            "generated_at": now.isoformat(),
            "route_count": len(route_payloads),
            "providers": {
                "routing": sorted({r["provider"] for r in route_payloads}),
                "geocoding": ["nominatim"],
                "weather": ["open-meteo"],
            },
        },
    }

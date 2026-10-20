"""Provider fallback chain and route de-duplication."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.cache import cache

from services.errors import NoRouteFoundError, RoutingError
from services.geo.geometry import mean_point_distance_m, resample_by_fraction
from services.routing import graphhopper, ors, osrm
from services.routing.base import RouteGeometry

logger = logging.getLogger(__name__)

DEDUP_THRESHOLD_M = 400.0   # mean distance below this = same road, not an alternative
RESAMPLE_POINTS = 64


def _dedupe(routes: list[RouteGeometry]) -> list[RouteGeometry]:
    kept: list[RouteGeometry] = []
    resampled = []
    for route in routes:
        rs = resample_by_fraction(route.coordinates, RESAMPLE_POINTS)
        if any(mean_point_distance_m(rs, other) < DEDUP_THRESHOLD_M for other in resampled):
            continue
        kept.append(route)
        resampled.append(rs)
    return kept


def _route_cache_key(origin: tuple[float, float], dest: tuple[float, float]) -> str:
    return f"routes:{origin[0]:.4f},{origin[1]:.4f}:{dest[0]:.4f},{dest[1]:.4f}"


def get_routes(origin: tuple[float, float], dest: tuple[float, float]) -> tuple[list[RouteGeometry], list[str]]:
    cached = cache.get(_route_cache_key(origin, dest))
    if cached is not None:
        routes, warnings = cached
        # LocMemCache stores live objects; give callers copies of the warning list.
        return routes, list(warnings)

    warnings: list[str] = []
    candidates: list[RouteGeometry] = []

    if settings.ORS_API_KEY:
        try:
            candidates = ors.fetch_routes(origin, dest)
        except RoutingError as exc:
            warnings.append(f"ORS alternative routes unavailable: {exc.detail}")
            try:
                candidates = [ors.fetch_single_route(origin, dest)]
                warnings.append("Fell back to a single ORS route (no alternatives) for this corridor.")
            except RoutingError as exc2:
                warnings.append(f"ORS single-route fallback failed: {exc2.detail}")

    if not candidates and settings.GRAPHHOPPER_API_KEY:
        try:
            candidates = graphhopper.fetch_routes(origin, dest)
        except RoutingError as exc:
            warnings.append(f"GraphHopper unavailable: {exc.detail}")

    if not candidates:
        try:
            candidates = osrm.fetch_routes(origin, dest)
            if settings.ORS_API_KEY or settings.GRAPHHOPPER_API_KEY:
                warnings.append("Routing fell back to the keyless OSRM public server (car profile, not truck-legal).")
            else:
                warnings.append(
                    "No ORS key configured: routes come from the keyless OSRM demo server (car profile, "
                    "not truck-legal). Add ORS_API_KEY for truck-aware routing."
                )
        except RoutingError as exc:
            raise NoRouteFoundError(
                f"No routing provider could route this origin–destination pair: {exc.detail}"
            ) from exc

    distinct = _dedupe(candidates)[: settings.MAX_ROUTE_ALTERNATIVES]
    if len(distinct) < settings.MAX_ROUTE_ALTERNATIVES:
        warnings.append(
            f"Routing providers returned only {len(distinct)} genuinely distinct route(s) "
            f"of {settings.MAX_ROUTE_ALTERNATIVES} requested for this corridor; no duplicates were fabricated."
        )

    cache.set(_route_cache_key(origin, dest), (distinct, warnings), settings.ROUTE_CACHE_TTL)
    return distinct, list(warnings)

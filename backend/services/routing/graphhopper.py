"""Optional GraphHopper fallback adapter."""
from __future__ import annotations

import logging

from django.conf import settings

from services.errors import RoutingError
from services.geo.geometry import cumulative_distances_m
from services.http import client
from services.routing.base import RouteGeometry

logger = logging.getLogger(__name__)


def fetch_routes(origin_coord: tuple[float, float], dest_coord: tuple[float, float]) -> list[RouteGeometry]:
    if not settings.GRAPHHOPPER_API_KEY:
        raise RoutingError("GRAPHHOPPER_API_KEY is not configured")

    body = {
        "points": [[origin_coord[0], origin_coord[1]], [dest_coord[0], dest_coord[1]]],
        "profile": "car",
        "locale": "en",
        "calc_points": True,
        "points_encoded": False,
        "instructions": False,
        "alternative_route.max_paths": settings.MAX_ROUTE_ALTERNATIVES,
    }
    with client() as c:
        try:
            resp = c.post(
                f"{settings.GRAPHHOPPER_BASE_URL}/route",
                params={"key": settings.GRAPHHOPPER_API_KEY},
                json=body,
            )
        except Exception as exc:
            raise RoutingError(f"GraphHopper request failed: {exc}") from exc

    if resp.status_code != 200:
        raise RoutingError(f"GraphHopper rejected the request (HTTP {resp.status_code})")

    try:
        payload = resp.json()
        paths = payload.get("paths", [])
    except Exception as exc:
        raise RoutingError(f"GraphHopper returned an unexpected payload: {exc}") from exc

    routes: list[RouteGeometry] = []
    for path in paths[: settings.MAX_ROUTE_ALTERNATIVES]:
        try:
            coords = [(float(x), float(y)) for x, y in path["points"]["coordinates"]]
            distance_m = float(path["distance"])
            duration_s = float(path["time"]) / 1000.0
        except (KeyError, TypeError, ValueError) as exc:
            raise RoutingError(f"GraphHopper path malformed: {exc}") from exc
        if len(coords) < 2:
            continue
        from services.routing.base import constant_speed_cumulative

        route = RouteGeometry(
            coordinates=coords,
            distance_m=distance_m,
            duration_s=duration_s,
            cumdist_m=cumulative_distances_m(coords),
            cumdur_s=constant_speed_cumulative(coords, duration_s),  # GH gives no per-vertex timing here
            provider="graphhopper",
            profile="driving-car",
            timing_source="constant_speed_fallback",
        )
        route.validate()
        routes.append(route)

    if not routes:
        raise RoutingError("GraphHopper returned no usable routes")
    return routes

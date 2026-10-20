"""OpenRouteService driving-hgv adapter."""
from __future__ import annotations

import logging

from django.conf import settings

from services.errors import RoutingError
from services.geo.geometry import cumulative_distances_m
from services.http import client
from services.routing.base import RouteGeometry

logger = logging.getLogger(__name__)

PROFILE = "driving-hgv"  # truck-aware profile; see docs for the legality caveat


# Spread each step's duration across the step's vertices.
def _build_cumulative_timing(
    coords: list[tuple[float, float]],
    cumdist: list[float],
    steps: list[dict],
) -> list[float]:
    n = len(coords)
    cumdur = [0.0] * n
    t_prev = 0.0
    cursor = 0
    for step in steps:
        wp = step.get("way_points") or [cursor, cursor]
        a, b = int(wp[0]), int(wp[-1])
        b = max(b, a)
        d = float(step.get("duration") or 0.0)
        seg = cumdist[b] - cumdist[a]
        for v in range(a + 1, b + 1):
            if seg > 0:
                cumdur[v] = t_prev + d * (cumdist[v] - cumdist[a]) / seg
            else:
                cumdur[v] = t_prev + d
        t_prev += d
        cursor = max(cursor, b)
    # fill any tail the steps did not cover
    for v in range(cursor + 1, n):
        cumdur[v] = t_prev
    return cumdur


def fetch_routes(origin_coord: tuple[float, float], dest_coord: tuple[float, float]) -> list[RouteGeometry]:
    if not settings.ORS_API_KEY:
        raise RoutingError("ORS_API_KEY is not configured")

    body = {
        "coordinates": [[origin_coord[0], origin_coord[1]], [dest_coord[0], dest_coord[1]]],
        "preference": "recommended",
        "units": "m",
        "alternative_routes": {
            "target_count": settings.MAX_ROUTE_ALTERNATIVES,
            "share_factor": 0.6,
            "weight_factor": 1.6,
        },
    }

    with client() as c:
        try:
            resp = c.post(
                f"{settings.ORS_BASE_URL}/v2/directions/{PROFILE}/geojson",
                json=body,
                headers={"Authorization": settings.ORS_API_KEY},
            )
        except Exception as exc:
            raise RoutingError(f"OpenRouteService request failed: {exc}") from exc

    if resp.status_code != 200:
        detail = _extract_ors_error(resp)
        raise RoutingError(f"OpenRouteService rejected the request (HTTP {resp.status_code}): {detail}")

    try:
        payload = resp.json()
        features = payload["features"]
    except Exception as exc:
        raise RoutingError(f"OpenRouteService returned an unexpected payload: {exc}") from exc

    routes: list[RouteGeometry] = []
    for feature in features:
        try:
            props = feature["properties"]
            coords = [(float(x), float(y)) for x, y in feature["geometry"]["coordinates"]]
            summary = props["summary"]
            distance_m = float(summary["distance"])
            duration_s = float(summary["duration"])
            steps = [step for seg in props.get("segments", []) for step in seg.get("steps", [])]
        except (KeyError, TypeError, ValueError) as exc:
            raise RoutingError(f"OpenRouteService route feature malformed: {exc}") from exc

        if len(coords) < 2:
            continue
        cumdist = cumulative_distances_m(coords)
        cumdur = _build_cumulative_timing(coords, cumdist, steps) if steps else None

        route = RouteGeometry(
            coordinates=coords,
            distance_m=distance_m,
            duration_s=duration_s,
            cumdist_m=cumdist,
            cumdur_s=cumdur if cumdur is not None else _constant_speed(coords, duration_s),
            provider="openrouteservice",
            profile=PROFILE,
            timing_source="provider" if cumdur is not None else "constant_speed_fallback",
        )
        route.validate()
        routes.append(route)

    if not routes:
        raise RoutingError("OpenRouteService returned no usable routes")
    return routes


def fetch_single_route(origin_coord: tuple[float, float], dest_coord: tuple[float, float]) -> RouteGeometry:
    if not settings.ORS_API_KEY:
        raise RoutingError("ORS_API_KEY is not configured")

    body = {
        "coordinates": [[origin_coord[0], origin_coord[1]], [dest_coord[0], dest_coord[1]]],
        "preference": "recommended",
        "units": "m",
    }
    with client() as c:
        try:
            resp = c.post(
                f"{settings.ORS_BASE_URL}/v2/directions/{PROFILE}/geojson",
                json=body,
                headers={"Authorization": settings.ORS_API_KEY},
            )
        except Exception as exc:
            raise RoutingError(f"OpenRouteService request failed: {exc}") from exc
    if resp.status_code != 200:
        raise RoutingError(
            f"OpenRouteService rejected the request (HTTP {resp.status_code}): {_extract_ors_error(resp)}"
        )

    routes = _parse_geojson_payload(resp.json())
    if not routes:
        raise RoutingError("OpenRouteService returned no usable routes")
    return routes[0]


def _parse_geojson_payload(payload: dict) -> list[RouteGeometry]:
    routes: list[RouteGeometry] = []
    for feature in payload.get("features", []):
        props = feature.get("properties", {})
        try:
            coords = [(float(x), float(y)) for x, y in feature["geometry"]["coordinates"]]
            summary = props["summary"]
            duration_s = float(summary["duration"])
            steps = [step for seg in props.get("segments", []) for step in seg.get("steps", [])]
        except (KeyError, TypeError, ValueError):
            continue
        if len(coords) < 2:
            continue
        cumdist = cumulative_distances_m(coords)
        cumdur = _build_cumulative_timing(coords, cumdist, steps) if steps else None
        routes.append(
            RouteGeometry(
                coordinates=coords,
                distance_m=float(summary["distance"]),
                duration_s=duration_s,
                cumdist_m=cumdist,
                cumdur_s=cumdur if cumdur is not None else _constant_speed(coords, duration_s),
                provider="openrouteservice",
                profile=PROFILE,
                timing_source="provider" if cumdur is not None else "constant_speed_fallback",
            )
        )
    for r in routes:
        r.validate()
    return routes


def _constant_speed(coords: list[tuple[float, float]], duration_s: float) -> list[float]:
    from services.routing.base import constant_speed_cumulative

    return constant_speed_cumulative(coords, duration_s)


def _extract_ors_error(resp) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict):
            err = body.get("error") or body.get("detail")
            if err:
                return str(err)
    except Exception:
        pass
    return resp.text[:200]

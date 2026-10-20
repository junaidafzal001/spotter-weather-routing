"""OSRM adapter (keyless fallback)."""
from __future__ import annotations

from django.conf import settings

from services.errors import RoutingError
from services.geo.geometry import cumulative_distances_m
from services.http import client
from services.routing.base import RouteGeometry


def fetch_routes(origin_coord: tuple[float, float], dest_coord: tuple[float, float]) -> list[RouteGeometry]:
    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/driving/"
        f"{origin_coord[0]:.6f},{origin_coord[1]:.6f};{dest_coord[0]:.6f},{dest_coord[1]:.6f}"
    )
    params = {
        "overview": "full",
        "geometries": "geojson",
        "alternatives": "3",
        "annotations": "duration,distance",
        "steps": "false",
    }
    with client() as c:
        try:
            resp = c.get(url, params=params)
        except Exception as exc:
            raise RoutingError(f"OSRM request failed: {exc}") from exc

    if resp.status_code != 200:
        raise RoutingError(f"OSRM rejected the request (HTTP {resp.status_code})")

    try:
        payload = resp.json()
    except Exception as exc:
        raise RoutingError(f"OSRM returned an unexpected payload: {exc}") from exc

    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError(f"OSRM could not route this pair: {payload.get('code', 'unknown')}")

    routes: list[RouteGeometry] = []
    for raw in payload["routes"][: settings.MAX_ROUTE_ALTERNATIVES]:
        try:
            coords = [(float(x), float(y)) for x, y in raw["geometry"]["coordinates"]]
            distance_m = float(raw["distance"])
            duration_s = float(raw["duration"])
            ann_durs: list[float] = []
            ann_dists: list[float] = []
            for leg in raw.get("legs", []):
                ann = leg.get("annotation") or {}
                ann_durs.extend(float(v) for v in ann.get("duration", []))
                ann_dists.extend(float(v) for v in ann.get("distance", []))
        except (KeyError, TypeError, ValueError) as exc:
            raise RoutingError(f"OSRM route malformed: {exc}") from exc

        if len(coords) < 2:
            continue

        cumdist = cumulative_distances_m(coords)
        if len(ann_durs) == len(coords) - 1 and all(d >= 0 for d in ann_durs):
            cumdur = [0.0]
            for d in ann_durs:
                cumdur.append(cumdur[-1] + d)
            timing_source = "provider"
        else:
            from services.routing.base import constant_speed_cumulative

            cumdur = constant_speed_cumulative(coords, duration_s)
            timing_source = "constant_speed_fallback"

        route = RouteGeometry(
            coordinates=coords,
            distance_m=distance_m,
            duration_s=duration_s,
            cumdist_m=cumdist,
            cumdur_s=cumdur,
            provider="osrm",
            profile="driving-car",
            timing_source=timing_source,
        )
        route.validate()
        routes.append(route)

    if not routes:
        raise RoutingError("OSRM returned no usable routes")
    return routes

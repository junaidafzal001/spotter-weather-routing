"""Corridor lattice sampling around a route."""
from __future__ import annotations

from dataclasses import dataclass

from services.geo.geometry import (
    cumulative_distances_m,
    interpolate_coordinate,
    miles_to_meters,
    offset_point,
    perpendicular_bearing,
)


@dataclass(frozen=True)
class CorridorPoint:
    lat: float
    lon: float
    mile: float            # along-route mile of the centerline anchor
    offset_miles: float    # signed lateral offset from the route (negative = left)


def build_corridor_points(
    coords: list[tuple[float, float]],
    *,
    along_spacing_miles: float = 20.0,
    lateral_offsets_miles: tuple[float, ...] = (0.0, -15.0, 15.0, -30.0, 30.0),
    max_points: int = 120,
) -> list[CorridorPoint]:
    if len(coords) < 2:
        return []
    cumdist = cumulative_distances_m(coords)
    total_m = cumdist[-1]
    if total_m <= 0:
        return []

    max_anchors = max_points // len(lateral_offsets_miles)
    n_anchors = max(2, min(int(total_m // miles_to_meters(along_spacing_miles)) + 1, max_anchors))
    step = total_m / (n_anchors - 1)

    points: list[CorridorPoint] = []
    for i in range(n_anchors):
        target = step * i
        anchor = interpolate_coordinate(coords, cumdist, target)
        ahead = interpolate_coordinate(coords, cumdist, min(target + 500.0, total_m))
        behind = interpolate_coordinate(coords, cumdist, max(target - 500.0, 0.0))
        for off in lateral_offsets_miles:
            if off == 0.0:
                lon, lat = anchor
                points.append(
                    CorridorPoint(
                        lat=lat,
                        lon=lon,
                        mile=round(target / miles_to_meters(1), 2),
                        offset_miles=0.0,
                    )
                )
                continue
            sign = 1 if off > 0 else -1
            brg = perpendicular_bearing(behind, ahead, sign)
            lon, lat = offset_point(anchor, brg, miles_to_meters(abs(off)))
            points.append(
                CorridorPoint(
                    lat=lat,
                    lon=lon,
                    mile=round(target / miles_to_meters(1), 2),
                    offset_miles=round(off, 2),
                )
            )
    return points[:max_points]

"""Normalized route model shared by routing adapters."""
from __future__ import annotations

from dataclasses import dataclass, field

from services.errors import RoutingError
from services.geo.geometry import cumulative_distances_m, haversine_m


@dataclass
class RouteGeometry:
    coordinates: list[tuple[float, float]]          # (lon, lat) vertices
    distance_m: float
    duration_s: float
    cumdist_m: list[float]                          # per-vertex, starts at 0.0
    cumdur_s: list[float]                           # per-vertex, starts at 0.0
    provider: str                                   # "openrouteservice" | "osrm" | "graphhopper"
    profile: str                                    # e.g. "driving-hgv"
    timing_source: str = "provider"                 # "provider" | "constant_speed_fallback"
    warnings: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if len(self.coordinates) < 2:
            raise RoutingError("route geometry has fewer than 2 vertices")
        if not (len(self.cumdist_m) == len(self.cumdur_s) == len(self.coordinates)):
            raise RoutingError("geometry/cumulative array length mismatch")


def constant_speed_cumulative(coords: list[tuple[float, float]], total_duration_s: float) -> list[float]:
    cumdist = cumulative_distances_m(coords)
    total = cumdist[-1]
    if total <= 0:
        return [0.0] * len(coords)
    return [d / total * total_duration_s for d in cumdist]


def cumulative_distance_array(coords: list[tuple[float, float]]) -> list[float]:
    return cumulative_distances_m(coords)


def vertex_distances_match(coord_a: tuple[float, float], coord_b: tuple[float, float], tol_m: float = 5.0) -> bool:
    return haversine_m(coord_a, coord_b) <= tol_m

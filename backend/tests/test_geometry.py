"""Geospatial helper tests: distance, interpolation, polyline decode, corridor."""
from __future__ import annotations

import math

import pytest

from services.geo.corridor import build_corridor_points
from services.geo.geometry import (
    cumulative_distances_m,
    decode_polyline5,
    haversine_m,
    interpolate_coordinate,
    interpolate_scalar,
    mean_point_distance_m,
    meters_to_miles,
    miles_to_meters,
    offset_point,
    resample_by_fraction,
    simplify,
)


def test_haversine_chicago_detroit():
    chicago = (-87.6298, 41.8781)
    detroit = (-83.0458, 42.3314)
    d = haversine_m(chicago, detroit)
    assert 370_000 < d < 400_000  # great-circle is ~383 km


def test_cumulative_distances_simple_line():
    line = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]  # ~111.32 km per degree at equator
    cum = cumulative_distances_m(line)
    assert cum[0] == 0.0
    assert cum[1] == pytest.approx(cum[2] / 2, rel=0.01)
    assert cum[-1] == pytest.approx(222_640, rel=0.01)


def test_interpolate_coordinate_midpoint():
    line = [(0.0, 0.0), (2.0, 0.0)]
    cum = cumulative_distances_m(line)
    lon, lat = interpolate_coordinate(line, cum, cum[-1] / 2)
    assert lon == pytest.approx(1.0, abs=1e-6)
    assert lat == pytest.approx(0.0, abs=1e-6)


def test_interpolate_coordinate_clamps():
    line = [(0.0, 0.0), (2.0, 0.0)]
    cum = cumulative_distances_m(line)
    assert interpolate_coordinate(line, cum, -5) == line[0]
    assert interpolate_coordinate(line, cum, 1e9) == line[-1]


def test_interpolate_scalar_linear():
    cum = [0.0, 100.0]
    values = [10.0, 30.0]
    assert interpolate_scalar(cum, values, 25.0) == pytest.approx(15.0)
    assert interpolate_scalar(cum, values, 0.0) == 10.0
    assert interpolate_scalar(cum, values, 100.0) == 30.0


def _encode_polyline5(coords: list[tuple[float, float]]) -> str:
    out: list[int] = []
    prev_lat = prev_lng = 0

    def _chunk(value: int) -> None:
        v = (value << 1) ^ (value >> 31 if value < 0 else 0)  # zigzag on 32-bit
        v = (value << 1) if value >= 0 else ((-value) * 2 - 1)
        while v >= 0x20:
            out.append((0x20 | (v & 0x1F)) + 63)
            v >>= 5
        out.append(v + 63)

    for lon, lat in coords:
        dlat = round(lat * 1e5) - prev_lat
        dlng = round(lon * 1e5) - prev_lng
        _chunk(dlat)
        _chunk(dlng)
        prev_lat, prev_lng = round(lat * 1e5), round(lon * 1e5)
    return "".join(chr(c) for c in out)


def test_decode_polyline5_classic_example():
    # The canonical 2-point example from the polyline algorithm specification.
    decoded = decode_polyline5("_p~iF~ps|U_ulLnnqC")
    expected = [(-120.2, 38.5), (-120.95, 40.7)]
    for (lon, lat), (elon, elat) in zip(decoded, expected, strict=True):
        assert lon == pytest.approx(elon, abs=1e-4)
        assert lat == pytest.approx(elat, abs=1e-4)


def test_decode_polyline5_roundtrip_with_independent_encoder():
    coords = [(-87.6298, 41.8781), (-86.5264, 41.7151), (-83.0458, 42.3314)]
    decoded = decode_polyline5(_encode_polyline5(coords))
    assert len(decoded) == 3
    for (lon, lat), (elon, elat) in zip(decoded, coords, strict=True):
        assert lon == pytest.approx(elon, abs=1e-5)
        assert lat == pytest.approx(elat, abs=1e-5)


def test_simplify_keeps_endpoints_and_removes_collinear():
    # Fully collinear line collapses to just its endpoints.
    line = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]
    out = simplify(line, tolerance_m=50)
    assert out == [(0.0, 0.0), (3.0, 0.0)]

    # A genuine bend survives thinning.
    bend = [(0.0, 0.0), (1.0, 0.05), (2.0, 0.0)]  # ~5.5 km deviation
    assert len(simplify(bend, tolerance_m=50)) == 3
    assert simplify(bend, tolerance_m=10_000) == [(0.0, 0.0), (2.0, 0.0)]


def test_offset_point_north():
    base = (0.0, 0.0)
    lon, lat = offset_point(base, 0.0, 111_320.0)
    assert lat == pytest.approx(1.0, abs=0.01)
    assert lon == pytest.approx(0.0, abs=0.01)


def test_offset_point_perpendicular_bearing():
    from services.geo.geometry import perpendicular_bearing

    a, b = (0.0, 0.0), (1.0, 0.0)  # heading east (90°)
    assert perpendicular_bearing(a, b, +1) == pytest.approx(180.0)   # right of east = south
    assert perpendicular_bearing(a, b, -1) == pytest.approx(0.0)     # left of east = north


def test_resample_and_mean_distance_detect_duplicates():
    line = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]
    same = list(line)
    shifted = [(lon + 0.05, lat + 0.05) for lon, lat in line]
    a = resample_by_fraction(line, 16)
    assert mean_point_distance_m(a, resample_by_fraction(same, 16)) == pytest.approx(0.0, abs=1.0)
    assert mean_point_distance_m(a, resample_by_fraction(shifted, 16)) > 4_000


def test_mile_conversions_roundtrip():
    assert meters_to_miles(miles_to_meters(37.5)) == pytest.approx(37.5)


# Corridor lattice
def _straight_line_miles(miles: float) -> list[tuple[float, float]]:
    meters_per_deg = math.pi * 6_371_000.0 / 180.0
    total_deg = miles * 1609.344 / meters_per_deg
    n = int(miles) + 1
    return [(-87.63, 41.88 + i * total_deg / miles) for i in range(n)]


def test_corridor_points_include_origin_destination_and_lanes():
    coords = _straight_line_miles(100)
    points = build_corridor_points(coords, along_spacing_miles=25.0, lateral_offsets_miles=(0.0, -15.0, 15.0))
    miles = sorted({p.mile for p in points})
    assert miles[0] == 0.0
    assert miles[-1] == 100.0
    # 5 anchors (0,25,50,75,100) x 3 lanes
    assert len(points) == 15
    offsets = {p.offset_miles for p in points}
    assert offsets == {0.0, -15.0, 15.0}


def test_corridor_points_respect_max_points():
    coords = _straight_line_miles(400)
    points = build_corridor_points(coords, along_spacing_miles=20.0, max_points=40)
    assert len(points) <= 40


def test_corridor_offsets_are_orthogonal_to_route():
    coords = [(-87.63, 41.88), (-86.63, 41.88)]  # due east
    points = build_corridor_points(coords, along_spacing_miles=34.0, lateral_offsets_miles=(0.0, -15.0, 15.0))
    left = next(p for p in points if p.offset_miles < 0)
    right = next(p for p in points if p.offset_miles > 0)
    assert left.lat > 41.88   # left of eastbound = north
    assert right.lat < 41.88  # right of eastbound = south

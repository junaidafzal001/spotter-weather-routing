"""Distance, interpolation, polyline decoding, and thinning helpers."""
from __future__ import annotations

import math

EARTH_RADIUS_M = 6_371_000.0
METERS_PER_MILE = 1609.344
KM_PER_DEG_LAT = 111.32


def haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def cumulative_distances_m(coords: list[tuple[float, float]]) -> list[float]:
    out = [0.0]
    for i in range(1, len(coords)):
        out.append(out[-1] + haversine_m(coords[i - 1], coords[i]))
    return out


def interpolate_coordinate(
    coords: list[tuple[float, float]], cumdist: list[float], target_m: float
) -> tuple[float, float]:
    if target_m <= 0:
        return coords[0]
    if target_m >= cumdist[-1]:
        return coords[-1]
    lo, hi = 0, len(cumdist) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cumdist[mid] <= target_m:
            lo = mid
        else:
            hi = mid
    seg = cumdist[hi] - cumdist[lo]
    if seg <= 0:
        return coords[lo]
    f = (target_m - cumdist[lo]) / seg
    lon = coords[lo][0] + (coords[hi][0] - coords[lo][0]) * f
    lat = coords[lo][1] + (coords[hi][1] - coords[lo][1]) * f
    return (lon, lat)


def interpolate_scalar(cumdist: list[float], values: list[float], target_m: float) -> float:
    if not cumdist:
        raise ValueError("empty route")
    if target_m <= 0:
        return values[0]
    if target_m >= cumdist[-1]:
        return values[-1]
    lo, hi = 0, len(cumdist) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if cumdist[mid] <= target_m:
            lo = mid
        else:
            hi = mid
    seg = cumdist[hi] - cumdist[lo]
    if seg <= 0:
        return values[lo]
    f = (target_m - cumdist[lo]) / seg
    return values[lo] + (values[hi] - values[lo]) * f


def miles_to_meters(miles: float) -> float:
    return miles * METERS_PER_MILE


def meters_to_miles(m: float) -> float:
    return m / METERS_PER_MILE


# Google/ORS encoded polyline; adapters normally request GeoJSON.
def decode_polyline5(encoded: str) -> list[tuple[float, float]]:
    return _decode_polyline(encoded, precision=1e5)


def decode_polyline6(encoded: str) -> list[tuple[float, float]]:
    return _decode_polyline(encoded, precision=1e6)


def _decode_polyline(encoded: str, precision: float) -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    index = lat = lng = 0
    n = len(encoded)
    while index < n:
        for which in (0, 1):
            result = 0
            shift = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(result >> 1) if (result & 1) else (result >> 1)
            if which == 0:
                lat += d
            else:
                lng += d
        coords.append((lng / precision, lat / precision))
    return coords


def _perpendicular_distance(p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
    # Local equirectangular meters are enough for thinning.
    ax, ay = a
    px, py = p
    bx, by = b
    kx = math.cos(math.radians((ay + by) / 2))
    pxx = (px - ax) * kx * KM_PER_DEG_LAT * 1000
    pyy = (py - ay) * KM_PER_DEG_LAT * 1000
    bxx = (bx - ax) * kx * KM_PER_DEG_LAT * 1000
    byy = (by - ay) * KM_PER_DEG_LAT * 1000
    denom = math.hypot(bxx, byy)
    if denom == 0:
        return math.hypot(pxx, pyy)
    t = (pxx * bxx + pyy * byy) / (denom * denom)
    t = max(0.0, min(1.0, t))
    return math.hypot(pxx - t * bxx, pyy - t * byy)


def simplify(coords: list[tuple[float, float]], tolerance_m: float = 5.0) -> list[tuple[float, float]]:
    if len(coords) <= 2:
        return list(coords)

    def _dp(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if len(points) <= 2:
            return points
        a, b = points[0], points[-1]
        dmax, idx = 0.0, 0
        for i in range(1, len(points) - 1):
            d = _perpendicular_distance(points[i], a, b)
            if d > dmax:
                dmax, idx = d, i
        if dmax > tolerance_m:
            left = _dp(points[: idx + 1])
            right = _dp(points[idx:])
            return left[:-1] + right
        return [a, b]

    return _dp(coords)


def bearing_deg(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    dlmb = lon2 - lon1
    x = math.sin(dlmb) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlmb)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def offset_point(p: tuple[float, float], bearing_degrees: float, distance_m: float) -> tuple[float, float]:
    lon1, lat1 = math.radians(p[0]), math.radians(p[1])
    theta = math.radians(bearing_degrees)
    delta = distance_m / EARTH_RADIUS_M
    lat2 = math.asin(math.sin(lat1) * math.cos(delta) + math.cos(lat1) * math.sin(delta) * math.cos(theta))
    lon2 = lon1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(lat1), math.cos(delta) - math.sin(lat1) * math.sin(lat2)
    )
    return (math.degrees(lon2), math.degrees(lat2))


def perpendicular_bearing(a: tuple[float, float], b: tuple[float, float], sign: int) -> float:
    return (bearing_deg(a, b) + 90.0 * sign) % 360.0


# Points spaced evenly by distance fraction, for geometry comparison.
def resample_by_fraction(coords: list[tuple[float, float]], count: int) -> list[tuple[float, float]]:
    cumdist = cumulative_distances_m(coords)
    total = cumdist[-1]
    if total <= 0:
        return [coords[0]] * count
    return [interpolate_coordinate(coords, cumdist, total * i / (count - 1)) for i in range(count)]


def mean_point_distance_m(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    if len(a) != len(b):
        raise ValueError("resampled lists must have equal length")
    if not a:
        return 0.0
    return sum(haversine_m(x, y) for x, y in zip(a, b, strict=True)) / len(a)

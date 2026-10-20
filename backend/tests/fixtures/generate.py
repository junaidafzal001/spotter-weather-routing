"""Generates static provider fixtures for offline tests."""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent


def write(name: str, payload) -> None:
    (HERE / name).write_text(json.dumps(payload, indent=1))
    print("wrote", name)


# Nominatim
def nominatim() -> None:
    write(
        "nominatim_chicago.json",
        [
            {
                "place_id": 122_561_163,
                "osm_type": "relation",
                "osm_id": 122_561,
                "lat": "41.8781136",
                "lon": "-87.6297982",
                "display_name": "Chicago, Cook County, Illinois, United States",
                "class": "place",
                "type": "city",
                "importance": 0.92,
            }
        ],
    )
    write(
        "nominatim_detroit.json",
        [
            {
                "place_id": 135_311_563,
                "osm_type": "relation",
                "osm_id": 135_311,
                "lat": "42.3314270",
                "lon": "-83.0457538",
                "display_name": "Detroit, Wayne County, Michigan, United States",
                "class": "place",
                "type": "city",
                "importance": 0.88,
            }
        ],
    )
    write(
        "nominatim_suggest.json",
        [
            {"display_name": "Chicago, Cook County, Illinois, United States", "lat": 41.8781, "lon": -87.6298},
            {"display_name": "Chicago Heights, Cook County, Illinois, United States", "lat": 41.5075, "lon": -87.5065},
            {"display_name": "Chicago Ridge, Cook County, Illinois, United States", "lat": 41.7014, "lon": -87.7734},
            {
                "display_name": "Chicago Loop, Chicago, Cook County, Illinois, United States",
                "lat": 41.7820,
                "lon": -87.7500,
            },
            {"display_name": "West Chicago, DuPage County, Illinois, United States", "lat": 41.8864, "lon": -88.1945},
        ],
    )


# OpenRouteService (GeoJSON flavour, driving-hgv, alternative routes)
def _ors_feature(coords: list[list[float]], steps: list[dict], distance: float, duration: float) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "segments": [{"distance": distance, "duration": duration, "steps": steps}],
            "summary": {"distance": distance, "duration": duration},
            "way_points": [0, len(coords) - 1],
        },
        "geometry": {"type": "LineString", "coordinates": coords},
    }


def ors() -> None:
    base = [
        [-87.6298, 41.8781],
        [-87.5312, 41.7040],
        [-87.2079, 41.5868],
        [-86.8110, 41.6864],
        [-86.5264, 41.7151],
        [-86.2104, 41.7923],
        [-85.9760, 41.9017],
        [-85.6652, 41.9677],
        [-85.4160, 42.0702],
        [-84.9217, 42.2246],
        [-84.5430, 42.4487],
        [-83.9587, 42.5694],
        [-83.4995, 42.6377],
        [-83.0458, 42.3314],
    ]
    # Alternatives: distinct geometries so dedup keeps all three.
    alt2 = [[lon, lat - (0.25 if 1 <= i <= 11 else 0.0)] for i, (lon, lat) in enumerate(base)]
    alt3 = [[lon + 0.12, lat - (0.55 if 1 <= i <= 11 else 0.0)] for i, (lon, lat) in enumerate(base)]

    steps = [
        {"distance": 45_000.0, "duration": 1_800.0, "type": 11, "name": "I-90", "way_points": [0, 3]},
        {"distance": 80_000.0, "duration": 3_600.0, "type": 1, "name": "I-94", "way_points": [3, 9]},
        {"distance": 35_000.0, "duration": 1_440.0, "type": 1, "name": "I-96", "way_points": [9, 13]},
    ]
    distance, duration = 160_000.0, 6_840.0  # sums: steps 160000 / 6840

    write(
        "ors_alternatives.json",
        {
            "type": "FeatureCollection",
            "features": [
                _ors_feature(base, steps, distance, duration),
                _ors_feature(alt2, steps, 168_000.0, 7_140.0),
                _ors_feature(alt3, steps, 171_500.0, 7_380.0),
            ],
        },
    )
    write("ors_single.json", {"type": "FeatureCollection", "features": [_ors_feature(base, steps, distance, duration)]})
    write("ors_error.json", {"error": {"code": 2010, "message": "Unable to find an alternative route"}})


# OSRM (demo server flavour)
def osrm() -> None:
    base = [
        [-87.6298, 41.8781],
        [-87.4800, 41.6600],
        [-87.1500, 41.6100],
        [-86.7600, 41.6800],
        [-86.3100, 41.7600],
        [-85.8400, 41.8900],
        [-85.3700, 42.0100],
        [-84.8600, 42.1800],
        [-84.3100, 42.4300],
        [-83.6900, 42.5500],
        [-83.0458, 42.3314],
    ]
    alt2 = [[lon, lat - (0.2 if 1 <= i <= 9 else 0.0)] for i, (lon, lat) in enumerate(base)]

    import math

    R = 6_371_000.0

    def _haversine(a, b):
        lon1, lat1 = map(math.radians, a)
        lon2, lat2 = map(math.radians, b)
        h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        return 2 * R * math.asin(math.sqrt(h))

    def route(coords: list[list[float]], speed_kmh: float = 80.0) -> dict:
        seg_dists = [_haversine(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
        distance = sum(seg_dists)
        duration = distance / (speed_kmh * 1000.0 / 3600.0)
        # per-segment durations proportional to distance, summing to route duration
        durs = [round(d / distance * duration, 1) for d in seg_dists]
        dists = [round(d, 1) for d in seg_dists]
        return {
            "distance": round(distance, 1),
            "duration": round(duration, 1),
            "geometry": {"type": "LineString", "coordinates": coords},
            "legs": [{"annotation": {"distance": dists, "duration": durs}}],
        }

    write(
        "osrm_alternatives.json",
        {"code": "Ok", "routes": [route(base, 80.0), route(alt2, 76.0)]},
    )
    write("osrm_error.json", {"code": "NoRoute", "message": "No route found"})


# Open-Meteo
def open_meteo() -> None:
    start = datetime(2026, 1, 10, 0, 0, tzinfo=UTC)
    hours = [start + timedelta(hours=i) for i in range(12)]
    times = [h.strftime("%Y-%m-%dT%H:%M") for h in hours]

    def location(lat: float, lon: float, wind: list, rain: list, snow_cm: list, temp: list, codes: list) -> dict:
        assert len(wind) == len(rain) == len(snow_cm) == len(temp) == len(codes) == len(times)
        precip = [round(r + s / 7.0, 4) for r, s in zip(rain, snow_cm, strict=True)]  # 7cm snow ~ 10mm water per docs
        return {
            "latitude": lat,
            "longitude": lon,
            "generationtime_ms": 0.42,
            "utc_offset_seconds": 0,
            "timezone": "GMT",
            "timezone_abbreviation": "GMT",
            "elevation": 180.0,
            "hourly_units": {
                "time": "iso8601",
                "temperature_2m": "°C",
                "precipitation": "inch",
                "rain": "inch",
                "snowfall": "cm",
                "wind_speed_10m": "mph",
                "wind_gusts_10m": "mph",
            },
            "hourly": {
                "time": times,
                "temperature_2m": temp,
                "precipitation": precip,
                "rain": rain,
                "snowfall": snow_cm,
                "wind_speed_10m": wind,
                "wind_gusts_10m": [round(w * 1.4, 1) for w in wind],
                "weather_code": codes,
            },
        }

    # Location A: escalating storm — rain then snow, wind peaking at 60 mph.
    loc_a = location(
        41.8781, -87.6298,
        wind=[10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 15.0, 10.0, 10.0, 10.0, 10.0, 10.0],
        rain=[0.0, 0.05, 0.15, 0.30, 0.60, 1.20, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        snow_cm=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.54, 5.08, 7.62, 12.70, 17.78, 0.0],
        temp=[4.0, 3.5, 3.0, 2.0, 1.0, 0.0, -1.0, -2.0, -3.0, -4.0, -4.5, -4.0],
        codes=[1, 2, 61, 63, 65, 95, 71, 73, 75, 85, 86, 3],
    )
    # Location B: calm — LOW across the board.
    loc_b = location(
        42.3314, -83.0458,
        wind=[8.0] * 12,
        rain=[0.0] * 12,
        snow_cm=[0.0] * 12,
        temp=[5.0] * 12,
        codes=[0] * 12,
    )

    write("open_meteo_checkpoints.json", [loc_a, loc_b])

    # Corridor lattice fixture: 72 hourly steps (forecast_days=3), 3 points.
    start72 = datetime(2026, 1, 10, 0, 0, tzinfo=UTC)
    times72 = [(start72 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(72)]
    wind72 = [round(10 + 40 * (0.5 - 0.5 * __import__("math").cos(2 * 3.14159 * i / 48)), 2) for i in range(72)]
    rain72 = [round(0.3 * max(0.0, __import__("math").sin(2 * 3.14159 * (i - 6) / 48)), 4) for i in range(72)]

    def loc72(lat: float, lon: float, mult: float) -> dict:
        return {
            "latitude": lat,
            "longitude": lon,
            "utc_offset_seconds": 0,
            "timezone": "GMT",
            "hourly_units": {"snowfall": "cm", "rain": "inch", "wind_speed_10m": "mph"},
            "hourly": {
                "time": times72,
                "temperature_2m": [round(2.0 + mult, 1)] * 72,
                "precipitation": [round(r, 4) for r in rain72],
                "rain": [round(r * mult, 4) for r in rain72],
                "snowfall": [0.0] * 72,
                "wind_speed_10m": [round(w * mult, 2) for w in wind72],
                "wind_gusts_10m": [round(w * 1.35 * mult, 2) for w in wind72],
                "weather_code": [61 if r > 0.05 else 1 for r in rain72],
            },
        }

    write(
        "open_meteo_corridor.json",
        [loc72(41.8781, -87.6298, 1.0), loc72(42.0, -86.2, 0.8), loc72(42.3314, -83.0458, 0.5)],
    )

    write("open_meteo_error.json", {"error": True, "reason": "Parameter 'hourly' is invalid"})


if __name__ == "__main__":
    nominatim()
    ors()
    osrm()
    open_meteo()

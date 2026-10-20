"""Routing adapter parsing, fallback chain, dedup, and failure tests."""
from __future__ import annotations

import pytest
import respx
from django.test import override_settings
from httpx import Response

from services.errors import NoRouteFoundError, RoutingError
from services.routing import service as routing_service
from services.routing.base import RouteGeometry, constant_speed_cumulative
from services.routing.ors import _build_cumulative_timing
from services.routing.ors import fetch_routes as ors_fetch_routes
from services.routing.osrm import fetch_routes as osrm_fetch_routes
from tests.conftest import load_fixture

ORS_URL = "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson"
OSRM_URL = "https://router.project-osrm.org/route/v1/driving/"
ORS_COORDS = "-87.629798,41.878114;-83.045754,42.331427"


def _json(payload) -> Response:
    return Response(200, json=payload)


# ORS adapter parsing
@respx.mock
@override_settings(ORS_API_KEY="test-key")
def test_ors_parses_alternatives_with_provider_timing():
    respx.post(ORS_URL).mock(return_value=_json(load_fixture("ors_alternatives.json")))
    routes = ors_fetch_routes((-87.629798, 41.878114), (-83.045754, 42.331427))
    assert len(routes) == 3
    first = routes[0]
    assert first.provider == "openrouteservice"
    assert first.profile == "driving-hgv"
    assert first.timing_source == "provider"
    assert first.duration_s == pytest.approx(6840.0)
    assert first.cumdur_s[-1] == pytest.approx(6840.0)  # step durations sum
    assert first.cumdist_m[0] == 0.0
    assert first.cumdur_s == sorted(first.cumdur_s)     # monotonic


@respx.mock
@override_settings(ORS_API_KEY="test-key")
def test_ors_step_boundaries_carry_exact_step_durations():
    respx.post(ORS_URL).mock(return_value=_json(load_fixture("ors_alternatives.json")))
    route = ors_fetch_routes((-87.629798, 41.878114), (-83.045754, 42.331427))[0]
    # fixture: step 1 covers way_points [0,3] with duration 1800
    assert route.cumdur_s[3] == pytest.approx(1800.0, abs=1.0)
    # step 2 ends at way_point 9: 1800 + 3600
    assert route.cumdur_s[9] == pytest.approx(5400.0, abs=1.0)


def test_build_cumulative_timing_zero_distance_step():
    coords = [(0.0, 0.0), (0.001, 0.0), (0.002, 0.0)]
    cumdist = [0.0, 111.0, 222.0]
    steps = [
        {"distance": 111.0, "duration": 60.0, "way_points": [0, 1]},
        {"distance": 0.0, "duration": 30.0, "way_points": [1, 1]},   # degenerate
        {"distance": 111.0, "duration": 60.0, "way_points": [1, 2]},
    ]
    cumdur = _build_cumulative_timing(coords, cumdist, steps)
    assert cumdur[1] == pytest.approx(60.0)
    assert cumdur[2] == pytest.approx(150.0)


@respx.mock
@override_settings(ORS_API_KEY="test-key")
def test_ors_error_raises_routing_error():
    respx.post(ORS_URL).mock(return_value=Response(400, json=load_fixture("ors_error.json")))
    with pytest.raises(RoutingError):
        ors_fetch_routes((-87.629798, 41.878114), (-83.045754, 42.331427))


# OSRM adapter parsing
@respx.mock
def test_osrm_parses_alternatives_with_annotation_timing():
    respx.get(OSRM_URL + ORS_COORDS).mock(return_value=_json(load_fixture("osrm_alternatives.json")))
    fixture = load_fixture("osrm_alternatives.json")
    expected_duration = sum(fixture["routes"][0]["legs"][0]["annotation"]["duration"])
    routes = osrm_fetch_routes((-87.629798, 41.878114), (-83.045754, 42.331427))
    assert len(routes) == 2
    assert routes[0].provider == "osrm"
    assert routes[0].timing_source == "provider"
    assert routes[0].cumdur_s[-1] == pytest.approx(expected_duration, rel=0.001)
    assert routes[0].cumdist_m[-1] == pytest.approx(fixture["routes"][0]["distance"], rel=0.01)
    assert routes[0].duration_s == pytest.approx(fixture["routes"][0]["duration"], rel=0.001)


@respx.mock
def test_osrm_no_route_raises():
    respx.get(OSRM_URL + ORS_COORDS).mock(return_value=_json(load_fixture("osrm_error.json")))
    with pytest.raises(RoutingError):
        osrm_fetch_routes((-87.629798, 41.878114), (-83.045754, 42.331427))


# Constant-speed fallback
def test_constant_speed_cumulative():
    coords = [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0)]
    cum = constant_speed_cumulative(coords, 7200.0)
    assert cum[0] == 0.0
    assert cum[-1] == pytest.approx(7200.0)
    assert cum[1] == pytest.approx(3600.0, rel=0.01)


# Deduplication — never present duplicates as alternatives
def test_dedupe_collapses_near_identical():
    line = [(-87.6, 41.8), (-87.0, 41.9), (-86.0, 42.0), (-84.0, 42.2)]
    r1 = RouteGeometry(line, 250_000, 9_000, [0, 80_000, 170_000, 250_000],
                       [0, 3_000, 6_000, 9_000], "osrm", "driving-car")
    r2 = RouteGeometry([(-87.6, 41.8), (-87.0, 41.9005), (-86.0, 42.0005), (-84.0, 42.2)],
                       250_000, 9_000, [0, 80_000, 170_000, 250_000], [0, 3_000, 6_000, 9_000],
                       "osrm", "driving-car")
    r3 = RouteGeometry([(-87.6, 41.3), (-87.0, 41.4), (-86.0, 41.6), (-84.0, 42.2)],
                       260_000, 9_500, [0, 80_000, 170_000, 260_000], [0, 3_100, 6_300, 9_500],
                       "osrm", "driving-car")
    kept = routing_service._dedupe([r1, r2, r3])
    assert len(kept) == 2
    assert kept[0] is r1
    assert kept[1] is r3


# Full fallback chain through routing_service.get_routes
@respx.mock
def test_chain_keyless_uses_osrm_and_warns():
    respx.get(OSRM_URL + ORS_COORDS).mock(return_value=_json(load_fixture("osrm_alternatives.json")))
    routes, warnings = routing_service.get_routes((-87.629798, 41.878114), (-83.045754, 42.331427))
    assert len(routes) == 2
    assert all(r.provider == "osrm" for r in routes)
    assert any("ORS key" in w for w in warnings)
    assert any("distinct route" in w for w in warnings)


@respx.mock
@override_settings(ORS_API_KEY="test-key")
def test_chain_ors_failure_falls_back_to_osrm():
    respx.post(ORS_URL).mock(return_value=Response(500, json={"error": "boom"}))
    respx.get(OSRM_URL + ORS_COORDS).mock(return_value=_json(load_fixture("osrm_alternatives.json")))
    routes, warnings = routing_service.get_routes((-87.629798, 41.878114), (-83.045754, 42.331427))
    assert len(routes) == 2
    assert routes[0].provider == "osrm"
    assert any("ORS alternative routes unavailable" in w for w in warnings)


@respx.mock
@override_settings(ORS_API_KEY="test-key")
def test_chain_all_fail_raises_no_route():
    respx.post(ORS_URL).mock(return_value=Response(500))
    respx.get(OSRM_URL + ORS_COORDS).mock(return_value=Response(500))
    with pytest.raises(NoRouteFoundError):
        routing_service.get_routes((-87.629798, 41.878114), (-83.045754, 42.331427))


@respx.mock
def test_chain_result_is_cached():
    route = respx.get(OSRM_URL + ORS_COORDS).mock(return_value=_json(load_fixture("osrm_alternatives.json")))
    routing_service.get_routes((-87.629798, 41.878114), (-83.045754, 42.331427))
    assert route.call_count == 1
    routing_service.get_routes((-87.629798, 41.878114), (-83.045754, 42.331427))
    assert route.call_count == 1  # second call served from cache

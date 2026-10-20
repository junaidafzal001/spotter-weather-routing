"""End-to-end API tests: analyze, corridor, suggest, health, error contracts."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import respx
from httpx import Response

from tests.conftest import load_fixture
from tests.responders import nominatim_by_query, open_meteo_by_forecast_days

NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSRM = "https://router.project-osrm.org/route/v1/driving/"
ORS = "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson"
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
CHI = "-87.629798,41.878114;-83.045754,42.331427"

VALID_BODY = {
    "origin": "Chicago, IL",
    "destination": "Detroit, MI",
    "departure_time": (datetime.now(UTC) + timedelta(hours=3)).isoformat(),
    "load_weight_lbs": 35_000,
    "checkpoint_interval_miles": 25,
}


def _ok_json(payload) -> Response:
    return Response(200, json=payload)


@pytest.fixture
def api(client):
    class Api:
        def post(self, body, **kw):
            return client.post("/api/routes/analyze/", body, content_type="application/json")

        def get(self, url):
            return client.get(url)

    return Api()


# Happy path (OSRM keyless chain, weather via respx fixtures)
@respx.mock
def test_analyze_returns_envelope_with_routes_checkpoints_and_recommendation(api):
    respx.get(NOMINATIM).mock(side_effect=nominatim_by_query())
    respx.get(OSRM + CHI).mock(return_value=_ok_json(load_fixture("osrm_alternatives.json")))
    respx.get(OPEN_METEO).mock(return_value=_ok_json(load_fixture("open_meteo_checkpoints.json")))

    resp = api.post(VALID_BODY)
    assert resp.status_code == 200, resp.content
    body = resp.json()

    assert set(body) == {"data", "warnings", "meta"}
    data = body["data"]
    assert data["analysis_id"]
    assert data["request"]["origin"]["resolved"].startswith("Chicago")
    assert len(data["routes"]) == 2  # OSRM fixture returns 2 distinct alternatives
    assert any("distinct route" in w for w in body["warnings"])  # only 2 of 3 requested

    osrm_fixture = load_fixture("osrm_alternatives.json")["routes"][0]
    route = data["routes"][0]
    assert route["id"] == "route-1"
    assert route["provider"] == "osrm"
    assert route["distance_miles"] == pytest.approx(osrm_fixture["distance"] / 1609.344, rel=0.01)
    assert route["duration_minutes"] == pytest.approx(osrm_fixture["duration"] / 60, rel=0.01)
    assert route["checkpoint_count"] >= 2
    assert route["checkpoints"][0]["mile"] == 0.0
    assert route["checkpoints"][-1]["mile"] == pytest.approx(route["distance_miles"], abs=1.0)

    # Fixture forecast timestamps are static (2026-01-10) while departure is
    # "now" -> all checkpoint weather is UNKNOWN, and the response must say so
    # rather than pretending it is safe.
    first = route["checkpoints"][0]
    assert first["weather"]["available"] is False
    assert first["risk"]["level"] == "UNKNOWN"
    assert first["risk"]["score"] is None
    assert any("UNKNOWN" in w for w in data["warnings"])

    # Exposure still sums to route miles with everything unassessed
    exposure = route["exposure"]
    accounted = (
        exposure["low_miles"] + exposure["moderate_miles"] + exposure["high_miles"]
        + exposure["severe_miles"] + exposure["no_travel_miles"] + exposure["unassessed_miles"]
    )
    assert accounted == pytest.approx(route["distance_miles"], abs=1.0)
    assert exposure["unassessed_miles"] == pytest.approx(route["distance_miles"], abs=1.0)

    rec = data["recommendation"]
    assert rec["eligible"] is True  # no NO_TRAVEL miles anywhere
    assert rec["recommended_route_id"] in {"route-1", "route-2"}
    assert rec["reason"]


@respx.mock
def test_analyze_maps_segments_with_levels(api):
    respx.get(NOMINATIM).mock(side_effect=nominatim_by_query())
    respx.get(OSRM + CHI).mock(return_value=_ok_json(load_fixture("osrm_alternatives.json")))
    respx.get(OPEN_METEO).mock(return_value=_ok_json(load_fixture("open_meteo_checkpoints.json")))

    resp = api.post(VALID_BODY)
    route = resp.json()["data"]["routes"][0]
    segments = route["segments"]
    assert len(segments) == route["checkpoint_count"] - 1
    # All UNKNOWN weather -> gray (None) segments, never LOW
    assert all(seg["level"] is None for seg in segments)


@respx.mock
def test_corridor_endpoint_serves_heatmap_lattice(api):
    respx.get(NOMINATIM).mock(side_effect=nominatim_by_query())
    respx.get(OSRM + CHI).mock(return_value=_ok_json(load_fixture("osrm_alternatives.json")))
    respx.get(OPEN_METEO).mock(side_effect=open_meteo_by_forecast_days())

    analysis_id = api.post(VALID_BODY).json()["data"]["analysis_id"]
    resp = api.get(f"/api/weather/corridor/?analysis_id={analysis_id}&route_id=route-1")
    assert resp.status_code == 200, resp.content
    data = resp.json()["data"]
    assert len(data["hours"]) == 49
    assert data["hours"][0] != data["hours"][1]  # real per-hour timestamps
    assert len(data["points"]) >= 3
    assert all(len(p["severity_by_hour"]) == 49 for p in data["points"])


def test_corridor_requires_params(api):
    resp = api.get("/api/weather/corridor/")
    assert resp.status_code == 400
    assert "analysis_id" in resp.json()["error"]["fields"]

    resp = api.get("/api/weather/corridor/?analysis_id=nope&route_id=route-1")
    assert resp.status_code == 404


# Validation & error contracts
def test_analyze_validation_errors_are_structured(api):
    resp = api.post({"origin": "Chicago, IL"})  # missing everything else
    assert resp.status_code == 400
    err = resp.json()["error"]
    assert err["code"] == "invalid_request"
    assert set(err["fields"]) >= {"destination", "departure_time", "load_weight_lbs"}

    resp = api.post({**VALID_BODY, "load_weight_lbs": 90_000})
    assert resp.status_code == 400
    assert "load_weight_lbs" in resp.json()["error"]["fields"]

    resp = api.post({**VALID_BODY, "checkpoint_interval_miles": 15})
    assert resp.status_code == 400

    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    resp = api.post({**VALID_BODY, "departure_time": past})
    assert resp.status_code == 400

    resp = api.post({**VALID_BODY, "destination": "Chicago, IL"})
    assert resp.status_code == 400
    assert "destination" in resp.json()["error"]["fields"]


@respx.mock
def test_geocode_failure_maps_to_structured_502(api):
    respx.get(NOMINATIM).mock(return_value=Response(500))
    resp = api.post(VALID_BODY)
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "geocoding_failed"


@respx.mock
def test_geocode_not_found_maps_to_422(api):
    respx.get(NOMINATIM).mock(return_value=_ok_json([]))
    resp = api.post(VALID_BODY)
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "geocode_not_found"
    assert "origin" in err["fields"]


@respx.mock
def test_weather_failure_degrades_to_unknown_not_crash(api):
    respx.get(NOMINATIM).mock(side_effect=nominatim_by_query())
    respx.get(OSRM + CHI).mock(return_value=_ok_json(load_fixture("osrm_alternatives.json")))
    respx.get(OPEN_METEO).mock(return_value=Response(500, json=load_fixture("open_meteo_error.json")))

    resp = api.post(VALID_BODY)
    assert resp.status_code == 200  # degraded, not failed
    data = resp.json()["data"]
    assert any("Weather provider unavailable" in w for w in data["warnings"])
    assert all(cp["risk"]["level"] == "UNKNOWN" for r in data["routes"] for cp in r["checkpoints"])


@respx.mock
def test_fewer_than_three_routes_warns_but_succeeds(api):
    respx.get(NOMINATIM).mock(side_effect=nominatim_by_query())
    respx.get(OSRM + CHI).mock(return_value=_ok_json(load_fixture("osrm_alternatives.json")))
    respx.get(OPEN_METEO).mock(return_value=_ok_json(load_fixture("open_meteo_checkpoints.json")))

    body = {**VALID_BODY, "checkpoint_interval_miles": 10}
    resp = api.post(body)
    assert resp.status_code == 200
    assert any("only 2 genuinely distinct" in w for w in resp.json()["warnings"])


# Suggest & health
@respx.mock
def test_geocode_suggest_returns_labels(api):
    respx.get(NOMINATIM).mock(return_value=_ok_json(load_fixture("nominatim_suggest.json")))
    resp = api.get("/api/geocode/suggest/?q=chicag")
    assert resp.status_code == 200
    suggestions = resp.json()["data"]["suggestions"]
    assert len(suggestions) == 5
    assert "label" in suggestions[0] and "lat" in suggestions[0]

    # cached second call — no new upstream request happens (single mock anyway)
    resp2 = api.get("/api/geocode/suggest/?q=chicag")
    assert resp2.json()["meta"].get("cache") == "hit"


def test_geocode_suggest_short_query_empty(api):
    resp = api.get("/api/geocode/suggest/?q=ch")
    assert resp.json()["data"]["suggestions"] == []


def test_health_reports_provider_config(api):
    resp = api.get("/api/health/")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "ok"
    assert data["providers"]["openrouteservice"] is False  # test settings have no key

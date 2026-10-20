"""Corridor heatmap service tests — per-hour severity lattice, slider mapping."""
from __future__ import annotations

import pytest
import respx
from django.core.cache import cache

from services.analysis import corridor_service
from services.errors import ServiceError
from tests.responders import open_meteo_multi

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _seed_analysis(load_weight_lbs: int = 35_000) -> str:
    coords = [(-87.63, 41.88 + i * (200.0 / 69.0) / 99) for i in range(100)]
    cumdist = [0.0]
    for _i in range(1, len(coords)):
        cumdist.append(cumdist[-1] + 111_320.0 * (200.0 / 69.0) / 99)
    analysis_id = "deadbeefcafe0123456789abcdef0123"
    cache.set(
        f"analysis:{analysis_id}",
        {
            "inputs": {"load_weight_lbs": load_weight_lbs, "checkpoint_interval_miles": 25},
            "routes": {
                "route-1": {"coordinates": coords, "cumdist_m": cumdist, "provider": "osrm", "profile": "driving-car"}
            },
        },
        600,
    )
    return analysis_id


@respx.mock
def test_corridor_returns_49_hourly_slices_with_per_point_severity():
    respx.get(OPEN_METEO_URL).mock(side_effect=open_meteo_multi())
    analysis_id = _seed_analysis(load_weight_lbs=35_000)
    payload = corridor_service.build_corridor(analysis_id, "route-1")

    assert len(payload["hours"]) == 49  # 0..48 inclusive
    assert payload["hours"][0] < payload["hours"][-1]
    assert len(payload["points"]) == corridor_service.SLIDER_HOURS + 1 or len(payload["points"]) >= 3

    for point in payload["points"]:
        assert len(point["severity_by_hour"]) == 49
        assert len(point["values_by_hour"]) == 49
        assert point["offset_miles"] in (0.0, -15.0, 15.0, -30.0, 30.0)


@respx.mock
def test_slider_hours_use_their_own_timestamps_not_one_reused():
    respx.get(OPEN_METEO_URL).mock(side_effect=open_meteo_multi())
    analysis_id = _seed_analysis(load_weight_lbs=0)
    payload = corridor_service.build_corridor(analysis_id, "route-1")

    point = payload["points"][0]  # centerline at origin, mult=1.0 in fixture
    severities = point["severity_by_hour"]
    # fixture wind curve peaks at 50 mph (SEVERE band 45-54) mid-window
    assert "LOW" in severities
    assert "SEVERE" in severities
    assert len(set(severities)) >= 3  # severity actually changes hour to hour


@respx.mock
def test_heatmap_severity_applies_load_overrides():
    respx.get(OPEN_METEO_URL).mock(side_effect=open_meteo_multi())
    # Same fixture wind (peaks 50 mph): with 35,000 lb -> NO_TRAVEL band applies.
    heavy = corridor_service.build_corridor(_seed_analysis(load_weight_lbs=35_000), "route-1")
    cache.clear()
    light = corridor_service.build_corridor(_seed_analysis(load_weight_lbs=10_000), "route-1")

    p_heavy = heavy["points"][0]["severity_by_hour"]
    p_light = light["points"][0]["severity_by_hour"]
    assert "NO_TRAVEL" in p_heavy
    assert "NO_TRAVEL" not in p_light
    assert "SEVERE" in p_light


@respx.mock
def test_corridor_result_is_cached():
    route = respx.get(OPEN_METEO_URL).mock(side_effect=open_meteo_multi())
    analysis_id = _seed_analysis()
    corridor_service.build_corridor(analysis_id, "route-1")
    assert route.call_count == 1
    corridor_service.build_corridor(analysis_id, "route-1")
    assert route.call_count == 1


def test_unknown_route_or_analysis_raise_404():
    with pytest.raises(ServiceError) as e:
        corridor_service.build_corridor("nonexistent0000000000000000000000", "route-1")
    assert e.value.status == 404

    _seed_analysis()
    with pytest.raises(ServiceError) as e:
        corridor_service.build_corridor("deadbeefcafe0123456789abcdef0123", "route-9")
    assert e.value.status == 404

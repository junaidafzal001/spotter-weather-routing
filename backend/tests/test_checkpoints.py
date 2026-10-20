"""Checkpoint interpolation, distance placement, and ETA calculation tests."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from services.analysis.checkpoints import build_checkpoints, checkpoint_interval_targets
from services.geo.geometry import cumulative_distances_m, miles_to_meters


def _straight_route(miles: float, speed_mph: float = 50.0):
    meters = miles_to_meters(miles)
    n = 101
    coords = [(-87.63 - i * (miles / 69.0) / n * 1.0, 41.88) for i in range(n + 1)]
    coords = [(-87.63 - (miles / 69.0) * i / n, 41.88) for i in range(n)]
    coords.append((-87.63 - miles / 69.0, 41.88))
    cumdist = cumulative_distances_m(coords)
    # scale cumdist to exactly the intended distance, keep proportionality
    scale = meters / cumdist[-1]
    cumdist = [d * scale for d in cumdist]
    seconds = miles / speed_mph * 3600.0
    cumdur = [d / cumdist[-1] * seconds for d in cumdist]
    return coords, cumdist, cumdur, seconds


DEPARTURE = datetime(2026, 10, 22, 13, 0, tzinfo=UTC)  # 08:00 CDT


@pytest.mark.parametrize(
    "interval,expected_miles",
    [
        (10, [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]),
        (25, [0, 25, 50, 75, 100]),
        (50, [0, 50, 100]),
        (60, [0, 60, 100]),  # destination always included, no duplicate
    ],
)
def test_checkpoint_placement_at_exact_intervals(interval, expected_miles):
    coords, cumdist, cumdur, _ = _straight_route(100.0)
    cps = build_checkpoints(
        coords=coords, cumdist_m=cumdist, cumdur_s=cumdur,
        interval_miles=interval, departure_utc=DEPARTURE,
    )
    assert [cp.mile for cp in cps] == pytest.approx(expected_miles, abs=0.01)


def test_origin_and_destination_always_checkpoints():
    coords, cumdist, cumdur, _ = _straight_route(15.0)
    cps = build_checkpoints(
        coords=coords, cumdist_m=cumdist, cumdur_s=cumdur,
        interval_miles=50, departure_utc=DEPARTURE,
    )
    assert cps[0].mile == pytest.approx(0.0)
    assert cps[-1].mile == pytest.approx(15.0)
    assert len(cps) == 2


def test_checkpoint_coordinates_interpolated_on_line():
    coords, cumdist, cumdur, _ = _straight_route(100.0)
    cps = build_checkpoints(
        coords=coords, cumdist_m=cumdist, cumdur_s=cumdur,
        interval_miles=25, departure_utc=DEPARTURE,
    )
    mid = cps[2]  # mile 50
    assert mid.coord[1] == pytest.approx(41.88, abs=1e-9)          # due west: lat constant
    assert mid.coord[0] < cps[1].coord[0] < cps[0].coord[0]        # moving west


def test_eta_uses_provider_timing_not_constant_speed():
    coords, cumdist, _, seconds = _straight_route(100.0)
    warped = []
    for d in cumdist:
        f = d / cumdist[-1]
        warped.append((f ** 0.5) * seconds)  # slow start (more time early)
    cps = build_checkpoints(
        coords=coords, cumdist_m=cumdist, cumdur_s=warped,
        interval_miles=25, departure_utc=DEPARTURE,
    )
    assert cps[0].eta == DEPARTURE
    # at half distance, warped timing is sqrt(0.5)≈0.707 of total, NOT 0.5
    expected = DEPARTURE.timestamp() + (seconds * 0.5 ** 0.5)
    assert cps[2].eta.timestamp() == pytest.approx(expected, abs=1.0)
    assert cps[-1].eta.timestamp() == pytest.approx(DEPARTURE.timestamp() + seconds, abs=1.0)


def test_checkpoints_monotonic_in_time_and_distance():
    coords, cumdist, cumdur, _ = _straight_route(250.0)
    cps = build_checkpoints(
        coords=coords, cumdist_m=cumdist, cumdur_s=cumdur,
        interval_miles=10, departure_utc=DEPARTURE,
    )
    miles = [cp.mile for cp in cps]
    etas = [cp.eta for cp in cps]
    assert miles == sorted(miles)
    assert etas == sorted(etas)
    assert cps[-1].eta > cps[0].eta


def test_interval_targets_pure_function():
    assert checkpoint_interval_targets(25, miles_to_meters(100)) == pytest.approx(
        [miles_to_meters(m) for m in (0, 25, 50, 75, 100)]
    )
    # 70-mile route at 50-mile intervals: one intermediate checkpoint + destination
    targets = checkpoint_interval_targets(50, miles_to_meters(70))
    assert targets == pytest.approx([miles_to_meters(m) for m in (0, 50, 70)])
    # route shorter than one interval: origin + destination only
    targets = checkpoint_interval_targets(50, miles_to_meters(30))
    assert targets == pytest.approx([miles_to_meters(0), miles_to_meters(30)])

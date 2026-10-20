"""Distance-weighted exposure aggregation and interval-independence tests."""
from __future__ import annotations

import pytest

from services.recommendation.exposure import compute_exposure
from services.risk.severity import Severity

S = Severity


def _exposure(miles, severities, total):
    return compute_exposure(
        checkpoint_miles=miles, checkpoint_severities=severities, route_distance_m=total * 1609.344
    )


def test_interval_attribution_max_of_endpoints():
    exp = _exposure([0, 25, 50, 75, 100], [S.LOW, S.HIGH, S.SEVERE, S.LOW, S.LOW], 100)
    assert exp.total_miles == pytest.approx(100)
    assert exp.high_miles == pytest.approx(25)      # LOW–HIGH stretch
    assert exp.severe_miles == pytest.approx(50)    # HIGH–SEVERE + SEVERE–LOW
    assert exp.low_miles == pytest.approx(25)       # LOW–LOW
    assert exp.unassessed_miles == pytest.approx(0)
    assert exp.average_risk == pytest.approx((25 * 0 + 25 * 2 + 50 * 3) / 100)
    assert exp.max_severity is S.SEVERE


def test_total_miles_conserved_across_intervals():
    miles10 = list(range(0, 101, 10))
    sev10 = [S.MODERATE if i % 20 == 0 else S.LOW for i in range(len(miles10))]
    miles25 = list(range(0, 101, 25))
    sev25 = [S.MODERATE if i % 20 == 0 else S.LOW for i in range(len(miles25))]
    miles50 = list(range(0, 101, 50))
    sev50 = [S.MODERATE if i % 20 == 0 else S.LOW for i in range(len(miles50))]

    for miles, sevs in ((miles10, sev10), (miles25, sev25), (miles50, sev50)):
        exp = _exposure(miles, sevs, 100)
        accounted = (
            exp.low_miles
            + exp.moderate_miles
            + exp.high_miles
            + exp.severe_miles
            + exp.no_travel_miles
            + exp.unassessed_miles
        )
        assert accounted == pytest.approx(100, abs=0.01)
        assert exp.total_miles == pytest.approx(100)


def test_unknown_endpoints_become_unassessed_not_low():
    exp = _exposure([0, 50, 75, 100], [None, S.LOW, None, S.HIGH], 100)
    # seg1: None–LOW -> unassessed 50; seg2: LOW–None -> unassessed 25; seg3: None–HIGH -> unassessed 25
    assert exp.unassessed_miles == pytest.approx(100)
    assert exp.low_miles == 0
    assert exp.average_risk is None
    assert exp.max_severity is None
    assert exp.unassessed_share == pytest.approx(1.0)


def test_partial_unknown_splits_correctly():
    exp = _exposure([0, 40, 100], [S.LOW, S.LOW, None], 100)
    assert exp.low_miles == pytest.approx(40)
    assert exp.unassessed_miles == pytest.approx(60)
    assert exp.average_risk == pytest.approx(0.0)  # assessed miles are all LOW
    assert exp.unassessed_share == pytest.approx(0.6)


def test_no_travel_miles_tracked_separately():
    exp = _exposure([0, 30, 60], [S.SEVERE, S.NO_TRAVEL, S.LOW], 60)
    # seg1 (SEVERE–NO_TRAVEL): max = NO_TRAVEL; seg2 (NO_TRAVEL–LOW): max = NO_TRAVEL
    assert exp.no_travel_miles == pytest.approx(60)
    assert exp.severe_miles == pytest.approx(0)
    assert int(S.NO_TRAVEL) == 4 and int(S.SEVERE) == 3  # distinct levels
    assert exp.max_severity is S.NO_TRAVEL


def test_no_checkpoints_all_unassessed():
    exp = _exposure([], [], 42)
    assert exp.unassessed_miles == pytest.approx(42)
    assert exp.unassessed_share == 1.0
    assert exp.average_risk is None


def test_weighted_average_uses_miles_not_checkpoint_count():
    # 90 miles LOW + 10 miles NO_TRAVEL: average must be dominated by LOW.
    exp = _exposure([0, 90, 100], [S.LOW, S.LOW, S.NO_TRAVEL], 100)
    assert exp.average_risk == pytest.approx((90 * 0 + 10 * 4) / 100)

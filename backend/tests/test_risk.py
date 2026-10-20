"""Exhaustive tests for the assessment risk rules — every boundary value."""
from __future__ import annotations

import pytest

from services.risk.engine import (
    apply_load_override,
    assess_checkpoint,
    classify_rain_in_hr,
    classify_snow_in_hr,
    classify_wind_mph,
    unknown_risk,
)
from services.risk.severity import Severity

S = Severity


# Wind boundaries: bands are lower-inclusive -> shared boundary = more severe
@pytest.mark.parametrize(
    "mph,expected",
    [
        (0.0, S.LOW),
        (24.99, S.LOW),
        (25.0, S.MODERATE),      # boundary -> more severe band
        (25.01, S.MODERATE),
        (34.99, S.MODERATE),
        (35.0, S.HIGH),          # boundary
        (35.01, S.HIGH),
        (44.99, S.HIGH),
        (45.0, S.SEVERE),        # boundary
        (45.01, S.SEVERE),
        (54.99, S.SEVERE),
        (55.0, S.NO_TRAVEL),     # >= 55
        (65.0, S.NO_TRAVEL),
    ],
)
def test_wind_boundaries(mph, expected):
    assert classify_wind_mph(mph) is expected


# Rain boundaries
@pytest.mark.parametrize(
    "in_hr,expected",
    [
        (0.0, S.LOW),
        (0.099, S.LOW),
        (0.10, S.MODERATE),      # boundary
        (0.10, S.MODERATE),
        (0.249, S.MODERATE),
        (0.25, S.HIGH),          # boundary
        (0.499, S.HIGH),
        (0.50, S.SEVERE),        # boundary
        (1.00, S.SEVERE),        # 1.00 inclusive per ">1.00 No Travel"
        (1.0001, S.NO_TRAVEL),
        (5.0, S.NO_TRAVEL),
    ],
)
def test_rain_boundaries(in_hr, expected):
    assert classify_rain_in_hr(in_hr) is expected


# Snow boundaries
@pytest.mark.parametrize(
    "in_hr,expected",
    [
        (0.0, S.LOW),
        (0.49, S.LOW),
        (0.50, S.MODERATE),      # boundary
        (0.999, S.MODERATE),
        (1.00, S.HIGH),          # boundary
        (1.999, S.HIGH),
        (2.00, S.SEVERE),        # boundary
        (3.00, S.SEVERE),        # 3.00 inclusive per ">3.0 No Travel"
        (3.001, S.NO_TRAVEL),
        (10.0, S.NO_TRAVEL),
    ],
)
def test_snow_boundaries(in_hr, expected):
    assert classify_snow_in_hr(in_hr) is expected


# Load-dependent wind overrides (all three rules)
def test_rule_1_wind_55_any_load():
    for load in (0, 20_000, 30_000, 80_000):
        result = assess_checkpoint(wind_mph=55.0, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=load)
        assert result.severity is S.NO_TRAVEL
        assert result.load_rule_applied is not None


def test_rule_2_wind_45_to_54_over_30000_lb():
    # > 30,000 lb is strict: exactly 30,000 does NOT trigger.
    assert (
        assess_checkpoint(
            wind_mph=50.0, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=30_001
        ).severity
        is S.NO_TRAVEL
    )
    assert (
        assess_checkpoint(
            wind_mph=45.0, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=45_000
        ).severity
        is S.NO_TRAVEL
    )
    assert (
        assess_checkpoint(
            wind_mph=54.99, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=30_001
        ).severity
        is S.NO_TRAVEL
    )
    # boundary: 30,000 lb exactly stays SEVERE from wind alone
    assert assess_checkpoint(wind_mph=50.0, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=30_000).severity is S.SEVERE
    # light load in the same band stays SEVERE
    assert assess_checkpoint(wind_mph=50.0, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=10_000).severity is S.SEVERE


def test_rule_3_wind_35_to_44_over_40000_lb_at_least_severe():
    assert assess_checkpoint(wind_mph=35.0, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=40_001).severity is S.SEVERE
    assert (
        assess_checkpoint(
            wind_mph=44.99, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=80_000
        ).severity
        is S.SEVERE
    )
    # boundary: exactly 40,000 lb does not trigger
    assert assess_checkpoint(wind_mph=40.0, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=40_000).severity is S.HIGH
    # an existing SEVERE stays SEVERE (at least)
    assert assess_checkpoint(wind_mph=40.0, rain_in_hr=0.9, snow_in_hr=0.0, load_weight_lbs=80_000).severity is S.SEVERE


def test_override_requires_wind_data():
    # No wind -> no override, rain alone drives the result.
    result = assess_checkpoint(wind_mph=None, rain_in_hr=0.3, snow_in_hr=None, load_weight_lbs=80_000)
    assert result.severity is S.HIGH
    assert result.load_rule_applied is None


def test_apply_load_override_direct():
    assert apply_load_override(56.0, 0, S.LOW)[0] is S.NO_TRAVEL
    assert apply_load_override(52.0, 30_001, S.SEVERE)[0] is S.NO_TRAVEL
    assert apply_load_override(52.0, 30_000, S.SEVERE)[0] is S.SEVERE
    assert apply_load_override(40.0, 40_001, S.HIGH)[0] is S.SEVERE
    assert apply_load_override(20.0, 80_000, S.LOW)[0] is S.LOW
    assert apply_load_override(None, 80_000, S.HIGH) == (S.HIGH, None)


# Combined conditions: highest severity wins across dimensions
def test_highest_severity_wins():
    result = assess_checkpoint(wind_mph=30.0, rain_in_hr=0.9, snow_in_hr=0.0, load_weight_lbs=0)
    assert result.severity is S.SEVERE            # rain dominates
    assert result.wind_severity is S.MODERATE

    result = assess_checkpoint(wind_mph=60.0, rain_in_hr=0.1, snow_in_hr=1.5, load_weight_lbs=0)
    assert result.severity is S.NO_TRAVEL         # wind dominates

    result = assess_checkpoint(wind_mph=10.0, rain_in_hr=0.05, snow_in_hr=1.5, load_weight_lbs=0)
    assert result.severity is S.HIGH              # snow dominates


def test_no_travel_is_distinct_from_severe():
    result = assess_checkpoint(wind_mph=56.0, rain_in_hr=0.0, snow_in_hr=0.0, load_weight_lbs=0)
    assert result.severity is S.NO_TRAVEL
    assert result.severity is not S.SEVERE
    assert int(result.severity) == 4
    assert int(S.SEVERE) == 3


def test_scores_match_assessment():
    assert [int(s) for s in S] == [0, 1, 2, 3, 4]


# Missing / unknown weather
def test_all_missing_is_unknown_not_low():
    result = assess_checkpoint(wind_mph=None, rain_in_hr=None, snow_in_hr=None, load_weight_lbs=35_000)
    assert result.available is False
    assert not result.complete


def test_partial_data_is_assessed_but_incomplete():
    result = assess_checkpoint(wind_mph=50.0, rain_in_hr=None, snow_in_hr=None, load_weight_lbs=35_000)
    assert result.available is True
    assert result.complete is False
    assert result.severity is S.NO_TRAVEL   # 45–54 + >30,000 lb override applies
    assert result.rain_severity is None


def test_unknown_risk_helper():
    u = unknown_risk("because")
    assert u.available is False
    assert u.complete is False

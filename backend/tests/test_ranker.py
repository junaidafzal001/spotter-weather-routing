"""Recommendation ranking: exact priority order + NO_TRAVEL safety exclusion."""
from __future__ import annotations

from services.recommendation.exposure import RouteExposure
from services.recommendation.ranker import recommend


def _exp(severe=0.0, high=0.0, moderate=0.0, low=100.0, no_travel=0.0, unassessed=0.0, avg=None):
    total = severe + high + moderate + low + no_travel + unassessed
    assessed = total - unassessed
    if avg is None:
        avg = (
            severe * 3 + high * 2 + moderate * 1 + no_travel * 4 + low * 0
        ) / assessed if assessed else None
    return RouteExposure(
        low_miles=low,
        moderate_miles=moderate,
        high_miles=high,
        severe_miles=severe,
        no_travel_miles=no_travel,
        unassessed_miles=unassessed,
        total_miles=total,
        average_risk=avg,
        max_severity=None,
        unassessed_share=(unassessed / total) if total else 0.0,
    )


def test_rule_1_fewest_severe_miles_wins():
    a = _exp(severe=5, high=30, avg=2.0)
    b = _exp(severe=20, high=0, avg=1.0)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 3600, "route-2": 3600})
    assert rec.recommended_route_id == "route-1"
    assert rec.ranking[0] == "route-1"


def test_rule_2_fewest_high_miles_when_severe_tied():
    a = _exp(severe=10, high=40)
    b = _exp(severe=10, high=5)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 3600, "route-2": 3600})
    assert rec.recommended_route_id == "route-2"


def test_rule_3_lowest_average_risk_when_severe_high_tied():
    a = _exp(severe=10, high=20, avg=1.8)
    b = _exp(severe=10, high=20, avg=1.1)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 3600, "route-2": 3600})
    assert rec.recommended_route_id == "route-2"


def test_rule_4_shortest_duration_when_all_risk_tied():
    a = _exp(severe=10, high=20, avg=1.5)
    b = _exp(severe=10, high=20, avg=1.5)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 7200, "route-2": 5400})
    assert rec.recommended_route_id == "route-2"
    assert "faster" in rec.reason or "time" in rec.reason.lower()


def test_no_travel_route_excluded_even_if_best():
    a = _exp(severe=0, high=0, low=100)
    b = _exp(severe=0, high=0, low=95, no_travel=5)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 3600, "route-2": 3000})
    assert rec.recommended_route_id == "route-1"
    assert rec.eligible is True
    assert rec.ranking[-1] == "route-2"


def test_all_no_travel_no_safe_route():
    a = _exp(low=50, no_travel=50)
    b = _exp(low=10, no_travel=90)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 3600, "route-2": 3600})
    assert rec.recommended_route_id is None
    assert rec.eligible is False
    assert rec.least_exposed_route_id == "route-1"
    assert "No safe route is currently available" in rec.reason
    assert "least exposure" in rec.reason


def test_reason_mentioned_when_avoids_severe():
    a = _exp(severe=0, high=10)
    b = _exp(severe=25, high=0)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 3600, "route-2": 3600})
    assert "avoids severe weather" in rec.reason


def test_incomplete_assessment_caveat_added():
    a = _exp(severe=0, high=0, low=40, unassessed=60)
    b = _exp(severe=0, high=0, low=100)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 3600, "route-2": 3600})
    # a and b tie on all four ranking keys; stable sort keeps route-1 first,
    # and its 60% unassessed share must be flagged in the reason.
    assert rec.recommended_route_id == "route-1"
    assert "caution" in rec.reason or "unavailable" in rec.reason


def test_heavily_unassessed_route_still_ranked_but_flagged():
    a = _exp(severe=0, high=0, low=20, unassessed=80)
    b = _exp(severe=30, high=0, low=70)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 3600, "route-2": 3600})
    # a has zero severe/high AND lower avg -> wins under the stated order,
    # but the reason must carry the incomplete-assessment caveat.
    assert rec.recommended_route_id == "route-1"
    assert "caution" in rec.reason


def test_empty_routes():
    rec = recommend({}, {})
    assert rec.recommended_route_id is None
    assert rec.ranking == []


def test_ranking_includes_ineligible_at_end():
    a = _exp(severe=5)
    b = _exp(no_travel=10, low=90)
    rec = recommend({"route-1": a, "route-2": b}, {"route-1": 3600, "route-2": 3600})
    assert rec.ranking == ["route-1", "route-2"]

"""Safety exclusion and route ranking."""
from __future__ import annotations

from dataclasses import dataclass

from services.recommendation.exposure import RouteExposure


@dataclass
class Recommendation:
    recommended_route_id: str | None
    reason: str
    eligible: bool
    ranking: list[str]
    least_exposed_route_id: str | None
    least_exposed_reason: str | None

    def to_dict(self) -> dict:
        return {
            "recommended_route_id": self.recommended_route_id,
            "reason": self.reason,
            "eligible": self.eligible,
            "ranking": self.ranking,
            "least_exposed_route_id": self.least_exposed_route_id,
            "least_exposed_reason": self.least_exposed_reason,
        }


def _avg(exposure: RouteExposure) -> float:
    return float("inf") if exposure.average_risk is None else exposure.average_risk


def _caveat(exposure: RouteExposure) -> str:
    if exposure.unassessed_share > 0.5:
        return (
            f" Weather could not be assessed for {exposure.unassessed_share:.0%} of this route, "
            "so treat this recommendation with caution."
        )
    if exposure.unassessed_share > 0.0:
        return (
            f" Weather data was unavailable for {exposure.unassessed_share:.0%} of this route "
            "(unassessed miles are excluded from the risk averages)."
        )
    return ""


# Rank eligible routes by Severe/High miles, average risk, then duration.
def recommend(routes: dict[str, RouteExposure], durations_s: dict[str, float]) -> Recommendation:
    if not routes:
        return Recommendation(
            recommended_route_id=None,
            reason="No routes were available to assess.",
            eligible=False,
            ranking=[],
            least_exposed_route_id=None,
            least_exposed_reason=None,
        )

    eligible = {rid: exp for rid, exp in routes.items() if exp.no_travel_miles <= 1e-9}

    if eligible:
        ranked_ids = sorted(
            eligible.keys(),
            key=lambda rid: (
                round(eligible[rid].severe_miles, 3),
                round(eligible[rid].high_miles, 3),
                _avg(eligible[rid]),
                round(durations_s.get(rid, float("inf")), 1),
            ),
        )
        best_id = ranked_ids[0]
        best = eligible[best_id]
        runner_up_id = ranked_ids[1] if len(ranked_ids) > 1 else None
        runner_up = eligible[runner_up_id] if runner_up_id else None
        reason = _explain_best(best_id, best, runner_up, runner_up_id, durations_s)
        return Recommendation(
            recommended_route_id=best_id,
            reason=reason,
            eligible=True,
            ranking=ranked_ids + sorted(set(routes) - set(eligible)),
            least_exposed_route_id=None,
            least_exposed_reason=None,
        )

    # Safety exclusion: every route contains No-Travel exposure.
    least_id = sorted(
        routes.keys(),
        key=lambda rid: (
            round(routes[rid].no_travel_miles, 3),
            round(routes[rid].severe_miles, 3),
            round(routes[rid].high_miles, 3),
            _avg(routes[rid]),
            round(durations_s.get(rid, float("inf")), 1),
        ),
    )[0]
    least = routes[least_id]
    reason = (
        "No safe route is currently available under the selected conditions: every alternative "
        f"passes through No-Travel weather. {least_id} has the least exposure "
        f"({least.no_travel_miles:.1f} mi No-Travel, {least.severe_miles:.1f} mi Severe). "
        "Consider delaying departure or waiting for conditions to improve."
    )
    return Recommendation(
        recommended_route_id=None,
        reason=reason,
        eligible=False,
        ranking=sorted(routes.keys(), key=lambda rid: routes[rid].no_travel_miles, reverse=True),
        least_exposed_route_id=least_id,
        least_exposed_reason=reason,
    )


def _explain_best(
    best_id: str,
    best: RouteExposure,
    runner_up: RouteExposure | None,
    runner_up_id: str | None,
    durations_s: dict[str, float],
) -> str:
    EPS = 0.05
    parts: list[str] = []

    if best.severe_miles > EPS:
        parts.append(f"{best_id} minimizes Severe-weather exposure ({best.severe_miles:.1f} mi of Severe conditions)")
    else:
        parts.append("Recommended because this route avoids severe weather")

    if runner_up is not None and runner_up_id is not None:
        severe_tie = abs(runner_up.severe_miles - best.severe_miles) < EPS
        high_tie = abs(runner_up.high_miles - best.high_miles) < EPS
        avg_tie = abs(_avg(runner_up) - _avg(best)) < 0.01
        if severe_tie and runner_up.high_miles > best.high_miles + EPS:
            parts.append(f"it also has fewer High-risk miles ({best.high_miles:.1f} vs {runner_up.high_miles:.1f})")
        elif severe_tie and high_tie and _avg(runner_up) > _avg(best) + 0.01:
            parts.append(f"its distance-weighted average risk is lower ({_avg(best):.2f} vs {_avg(runner_up):.2f})")
        elif severe_tie and high_tie and avg_tie:
            best_min = durations_s.get(best_id, float("inf")) / 60.0
            ru_min = durations_s.get(runner_up_id, float("inf")) / 60.0
            parts.append(f"routes are otherwise equivalent; this one is faster ({best_min:.0f} vs {ru_min:.0f} min)")

    text = "; ".join(parts) + "."
    if best.unassessed_share > 0.0:
        text += _caveat(best)
    return text

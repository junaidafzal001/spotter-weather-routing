"""Distance-weighted exposure over checkpoint intervals."""
from __future__ import annotations

from dataclasses import dataclass, field

from services.geo.geometry import meters_to_miles
from services.risk.severity import Severity


@dataclass
class RouteExposure:
    low_miles: float = 0.0
    moderate_miles: float = 0.0
    high_miles: float = 0.0
    severe_miles: float = 0.0
    no_travel_miles: float = 0.0
    unassessed_miles: float = 0.0
    total_miles: float = 0.0
    average_risk: float | None = None
    max_severity: Severity | None = None          # max over assessed miles
    unassessed_share: float = 0.0
    per_level_miles: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "low_miles": round(self.low_miles, 2),
            "moderate_miles": round(self.moderate_miles, 2),
            "high_miles": round(self.high_miles, 2),
            "severe_miles": round(self.severe_miles, 2),
            "no_travel_miles": round(self.no_travel_miles, 2),
            "unassessed_miles": round(self.unassessed_miles, 2),
            "total_miles": round(self.total_miles, 2),
            "average_risk": None if self.average_risk is None else round(self.average_risk, 3),
            "max_risk": self.max_severity.label if self.max_severity is not None else None,
            "unassessed_share": round(self.unassessed_share, 4),
        }


# Attribute each interval's miles to its worse endpoint; UNKNOWN endpoints become unassessed.
def compute_exposure(
    *,
    checkpoint_miles: list[float],
    checkpoint_severities: list[Severity | None],
    route_distance_m: float,
) -> RouteExposure:
    exposure = RouteExposure()
    buckets: dict[Severity, float] = {s: 0.0 for s in Severity}

    n = len(checkpoint_miles)
    total_miles = meters_to_miles(route_distance_m)
    exposure.total_miles = total_miles

    if n == 0:
        exposure.unassessed_miles = total_miles
        exposure.unassessed_share = 1.0 if total_miles > 0 else 0.0
        return exposure

    for i in range(n - 1):
        seg_miles = max(0.0, checkpoint_miles[i + 1] - checkpoint_miles[i])
        s0, s1 = checkpoint_severities[i], checkpoint_severities[i + 1]
        if s0 is None or s1 is None:
            exposure.unassessed_miles += seg_miles
            continue
        worst = max(s0, s1)
        buckets[worst] += seg_miles

    exposure.low_miles = buckets[Severity.LOW]
    exposure.moderate_miles = buckets[Severity.MODERATE]
    exposure.high_miles = buckets[Severity.HIGH]
    exposure.severe_miles = buckets[Severity.SEVERE]
    exposure.no_travel_miles = buckets[Severity.NO_TRAVEL]
    exposure.per_level_miles = {s.label: round(m, 2) for s, m in buckets.items() if m > 0 or s is Severity.LOW}

    assessed = total_miles - exposure.unassessed_miles
    if assessed > 1e-9:
        weighted = (
            buckets[Severity.LOW] * int(Severity.LOW)
            + buckets[Severity.MODERATE] * int(Severity.MODERATE)
            + buckets[Severity.HIGH] * int(Severity.HIGH)
            + buckets[Severity.SEVERE] * int(Severity.SEVERE)
            + buckets[Severity.NO_TRAVEL] * int(Severity.NO_TRAVEL)
        )
        exposure.average_risk = weighted / assessed
        exposure.max_severity = max((s for s in buckets if buckets[s] > 1e-9), default=Severity.LOW)

    exposure.unassessed_share = 0.0 if total_miles <= 0 else exposure.unassessed_miles / total_miles
    return exposure

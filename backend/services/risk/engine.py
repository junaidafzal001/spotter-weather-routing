"""Weather risk rules (wind, rain, snow, load overrides).

Bands are lower-inclusive: a value on a shared boundary takes the more
severe band. Full table: docs/architecture.md.
"""
from __future__ import annotations

from dataclasses import dataclass

from services.risk.severity import Severity

WIND_NO_TRAVEL_MPH = 55.0
WIND_SEVERE_MPH = 45.0
WIND_HIGH_MPH = 35.0
WIND_MODERATE_MPH = 25.0

RAIN_NO_TRAVEL_IN_HR = 1.00     # strictly greater than this
RAIN_SEVERE_IN_HR = 0.50        # 0.50 <= v <= 1.00 -> SEVERE
RAIN_HIGH_IN_HR = 0.25
RAIN_MODERATE_IN_HR = 0.10

SNOW_NO_TRAVEL_IN_HR = 3.00     # strictly greater than this
SNOW_SEVERE_IN_HR = 2.00        # 2.00 <= v <= 3.00 -> SEVERE
SNOW_HIGH_IN_HR = 1.00
SNOW_MODERATE_IN_HR = 0.50

LOAD_HEAVY_LBS = 30_000         # wind 45-54 + load > this -> NO_TRAVEL
LOAD_VERY_HEAVY_LBS = 40_000    # wind 35-44 + load > this -> at least SEVERE


def classify_wind_mph(wind_mph: float) -> Severity:
    if wind_mph < WIND_MODERATE_MPH:
        return Severity.LOW
    if wind_mph < WIND_HIGH_MPH:
        return Severity.MODERATE
    if wind_mph < WIND_SEVERE_MPH:
        return Severity.HIGH
    if wind_mph < WIND_NO_TRAVEL_MPH:
        return Severity.SEVERE
    return Severity.NO_TRAVEL


def classify_rain_in_hr(rain_in_hr: float) -> Severity:
    if rain_in_hr < RAIN_MODERATE_IN_HR:
        return Severity.LOW
    if rain_in_hr < RAIN_HIGH_IN_HR:
        return Severity.MODERATE
    if rain_in_hr < RAIN_SEVERE_IN_HR:
        return Severity.HIGH
    if rain_in_hr <= RAIN_NO_TRAVEL_IN_HR:
        return Severity.SEVERE
    return Severity.NO_TRAVEL


def classify_snow_in_hr(snow_in_hr: float) -> Severity:
    if snow_in_hr < SNOW_MODERATE_IN_HR:
        return Severity.LOW
    if snow_in_hr < SNOW_HIGH_IN_HR:
        return Severity.MODERATE
    if snow_in_hr < SNOW_SEVERE_IN_HR:
        return Severity.HIGH
    if snow_in_hr <= SNOW_NO_TRAVEL_IN_HR:
        return Severity.SEVERE
    return Severity.NO_TRAVEL


def apply_load_override(wind_mph: float | None, load_weight_lbs: int, current: Severity) -> tuple[Severity, str | None]:
    if wind_mph is None:
        return current, None
    if wind_mph >= WIND_NO_TRAVEL_MPH:
        if current < Severity.NO_TRAVEL:
            return Severity.NO_TRAVEL, "wind >= 55 mph -> No Travel for any load"
        return current, "wind >= 55 mph -> No Travel for any load"
    if WIND_SEVERE_MPH <= wind_mph < WIND_NO_TRAVEL_MPH and load_weight_lbs > LOAD_HEAVY_LBS:
        if current < Severity.NO_TRAVEL:
            return Severity.NO_TRAVEL, "wind 45-54 mph with load > 30,000 lb -> No Travel"
        return current, "wind 45-54 mph with load > 30,000 lb -> No Travel"
    if WIND_HIGH_MPH <= wind_mph < WIND_SEVERE_MPH and load_weight_lbs > LOAD_VERY_HEAVY_LBS:
        if current < Severity.SEVERE:
            return Severity.SEVERE, "wind 35-44 mph with load > 40,000 lb -> at least Severe"
        return current, "wind 35-44 mph with load > 40,000 lb -> at least Severe"
    return current, None


@dataclass(frozen=True)
class RiskAssessment:

    severity: Severity
    wind_severity: Severity | None
    rain_severity: Severity | None
    snow_severity: Severity | None
    load_rule_applied: str | None
    complete: bool          # True when wind, rain and snow were all available
    available: bool         # False when no dimension could be assessed (UNKNOWN)

    @property
    def level(self) -> str:
        return self.severity.label

    @property
    def score(self) -> int:
        return int(self.severity)


def unknown_risk(reason: str) -> RiskAssessment:
    return RiskAssessment(
        severity=Severity.LOW,
        wind_severity=None,
        rain_severity=None,
        snow_severity=None,
        load_rule_applied=None,
        complete=False,
        available=False,
    )


def assess_checkpoint(
    *,
    wind_mph: float | None,
    rain_in_hr: float | None,
    snow_in_hr: float | None,
    load_weight_lbs: int,
) -> RiskAssessment:
    wind_sev = classify_wind_mph(wind_mph) if wind_mph is not None else None
    rain_sev = classify_rain_in_hr(rain_in_hr) if rain_in_hr is not None else None
    snow_sev = classify_snow_in_hr(snow_in_hr) if snow_in_hr is not None else None

    candidates = [s for s in (wind_sev, rain_sev, snow_sev) if s is not None]
    if not candidates:
        return unknown_risk("no weather data available at this checkpoint")

    severity = max(candidates)
    severity, load_rule = apply_load_override(wind_mph, load_weight_lbs, severity)

    return RiskAssessment(
        severity=severity,
        wind_severity=wind_sev,
        rain_severity=rain_sev,
        snow_severity=snow_sev,
        load_rule_applied=load_rule,
        complete=(wind_mph is not None and rain_in_hr is not None and snow_in_hr is not None),
        available=True,
    )

"""Forecast selection at checkpoint ETAs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

WMO_CONDITIONS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    97: "Heavy thunderstorm",
    99: "Thunderstorm with heavy hail",
}


def condition_text(code: int | None) -> str | None:
    if code is None:
        return None
    return WMO_CONDITIONS.get(code, f"Unknown (code {code})")


def celsius_to_fahrenheit(c: float | None) -> float | None:
    return None if c is None else c * 9.0 / 5.0 + 32.0


def _lerp(a: float | None, b: float | None, f: float) -> float | None:
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return a + (b - a) * f


@dataclass
class WeatherSample:

    available: bool
    eta_utc: datetime
    forecast_time: datetime | None = None       # nearest hourly timestamp used
    wind_mph: float | None = None
    wind_gust_mph: float | None = None
    rain_in_hr: float | None = None
    snow_in_hr: float | None = None
    temperature_f: float | None = None
    weather_code: int | None = None
    condition: str | None = None
    source: str = "open-meteo"
    unavailability_reason: str | None = None
    interpolated: bool = False

    def to_dict(self) -> dict:
        def _r(v: float | None, digits: int) -> float | None:
            return None if v is None else round(v, digits)

        return {
            "available": self.available,
            "eta_utc": self.eta_utc.isoformat(),
            "forecast_time": self.forecast_time.isoformat() if self.forecast_time else None,
            "wind_mph": _r(self.wind_mph, 1),
            "wind_gust_mph": _r(self.wind_gust_mph, 1),
            "rain_in_hr": _r(self.rain_in_hr, 3),
            "snow_in_hr": _r(self.snow_in_hr, 3),
            "temperature_f": _r(self.temperature_f, 1),
            "weather_code": self.weather_code,
            "condition": self.condition,
            "source": None if not self.available else self.source,
            "unavailability_reason": self.unavailability_reason,
            "interpolated": self.interpolated,
        }


# Interpolate the hourly series at the ETA; out-of-range ETAs return an unavailable sample.
def sample_at(forecast, eta_utc: datetime) -> WeatherSample:
    times = forecast.times_utc
    if not times:
        return WeatherSample(
            available=False,
            eta_utc=eta_utc,
            unavailability_reason="provider returned no forecast hours",
        )


    eta_cmp = eta_utc if eta_utc.tzinfo else eta_utc.replace(tzinfo=UTC)
    eta_cmp = eta_cmp.astimezone(UTC)

    if eta_cmp < times[0]:
        return WeatherSample(
            available=False,
            eta_utc=eta_utc,
            unavailability_reason=f"checkpoint ETA is before the forecast window start ({times[0].isoformat()})",
        )
    if eta_cmp > times[-1]:
        return WeatherSample(
            available=False,
            eta_utc=eta_utc,
            unavailability_reason=f"checkpoint ETA is beyond the forecast horizon ({times[-1].isoformat()})",
        )

    lo, hi = 0, len(times) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if times[mid] <= eta_cmp:
            lo = mid
        else:
            hi = mid

    t0, t1 = times[lo], times[hi]
    span = (t1 - t0).total_seconds()
    f = 0.0 if span <= 0 else (eta_cmp - t0).total_seconds() / span
    f = max(0.0, min(1.0, f))

    nearest = lo if f < 0.5 else hi

    return WeatherSample(
        available=True,
        eta_utc=eta_utc,
        forecast_time=t0 if f < 0.5 else t1,
        wind_mph=_lerp(forecast.wind_mph[lo], forecast.wind_mph[hi], f),
        wind_gust_mph=_lerp(forecast.wind_gust_mph[lo], forecast.wind_gust_mph[hi], f),
        rain_in_hr=_lerp(forecast.rain_in_hr[lo], forecast.rain_in_hr[hi], f),
        snow_in_hr=_lerp(forecast.snow_in_hr[lo], forecast.snow_in_hr[hi], f),
        temperature_f=celsius_to_fahrenheit(_lerp(forecast.temperature_c[lo], forecast.temperature_c[hi], f)),
        weather_code=forecast.weather_code[nearest],
        condition=condition_text(forecast.weather_code[nearest]),
        interpolated=f > 0.0,
    )

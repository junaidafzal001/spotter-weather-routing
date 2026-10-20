"""Open-Meteo batched hourly forecasts."""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from django.conf import settings
from django.core.cache import cache

from services.errors import WeatherProviderError
from services.http import client

logger = logging.getLogger(__name__)

HOURLY_VARS = [
    "temperature_2m",
    "precipitation",
    "rain",
    "snowfall",
    "wind_speed_10m",
    "wind_gusts_10m",
    "weather_code",
]

CM_PER_INCH = 2.54
MAX_FORECAST_DAYS = 16


@dataclass
class HourlyForecast:

    lat: float
    lon: float
    times_utc: list[datetime]
    temperature_c: list[float | None]
    wind_mph: list[float | None]
    wind_gust_mph: list[float | None]
    rain_in_hr: list[float | None]
    snow_in_hr: list[float | None]
    precipitation_in_hr: list[float | None]
    weather_code: list[int | None]
    source: str = "open-meteo"
    unit_notes: list[str] = field(default_factory=list)


def _round_key(points: list[tuple[float, float]], forecast_days: int) -> str:
    canon = json.dumps(
        {
            "pts": [[round(lat, 4), round(lon, 4)] for lat, lon in points],
            "days": forecast_days,
        },
        sort_keys=True,
    )
    return "wx:" + hashlib.sha1(canon.encode()).hexdigest()


def _parse_times(raw_times: list[str]) -> list[datetime]:
    # GMT times come back naive; attach UTC.
    out = []
    for t in raw_times:
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        out.append(dt.astimezone(UTC))
    return out


def _normalize_location(entry: dict) -> HourlyForecast:
    hourly = entry.get("hourly") or {}
    units = entry.get("hourly_units") or {}
    unit_notes: list[str] = []

    def series(name: str) -> list:
        return hourly.get(name) or []

    n = len(series("time"))
    if n == 0:
        raise WeatherProviderError("Open-Meteo response contained no hourly time series")

    wind = [None if v is None else float(v) for v in series("wind_speed_10m")]
    gust = [None if v is None else float(v) for v in series("wind_gusts_10m")]
    rain = [None if v is None else float(v) for v in series("rain")]
    precip = [None if v is None else float(v) for v in series("precipitation")]
    codes = [None if v is None else int(v) for v in series("weather_code")]

    temps_raw = series("temperature_2m")
    temperature_c = [None if v is None else float(v) for v in temps_raw]

    snow_raw = series("snowfall")
    snow_unit = str(units.get("snowfall", "cm")).lower()
    snow_in: list[float | None] = []
    if snow_unit in ("cm", "centimeter", "centimeters"):
        snow_in = [None if v is None else float(v) / CM_PER_INCH for v in snow_raw]
        unit_notes.append(f"snowfall converted {snow_unit}->inches (÷{CM_PER_INCH})")
    elif snow_unit in ("inch", "inches", "in"):
        snow_in = [None if v is None else float(v) for v in snow_raw]
    else:
        snow_in = [None if v is None else float(v) for v in snow_raw]
        unit_notes.append(f"unrecognized snowfall unit '{snow_unit}'; values passed through")

    rain_unit = str(units.get("rain", "inch")).lower()
    if rain_unit not in ("inch", "inches", "in"):
        unit_notes.append(f"rain unit reported as '{rain_unit}' while 'inch' was requested — verify provider config")

    return HourlyForecast(
        lat=float(entry.get("latitude", 0.0)),
        lon=float(entry.get("longitude", 0.0)),
        times_utc=_parse_times(series("time")),
        temperature_c=temperature_c,
        wind_mph=wind,
        wind_gust_mph=gust,
        rain_in_hr=rain,
        snow_in_hr=snow_in,
        precipitation_in_hr=precip,
        weather_code=codes,
        unit_notes=unit_notes,
    )


def fetch_hourly_forecasts(
    points: list[tuple[float, float]],
    *,
    forecast_days: int,
    use_cache: bool = True,
) -> list[HourlyForecast]:
    if not points:
        return []

    days = max(1, min(int(forecast_days), MAX_FORECAST_DAYS))
    cache_key = _round_key(points, days)
    if use_cache:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    params = {
        "latitude": ",".join(f"{lat:.4f}" for lat, _ in points),
        "longitude": ",".join(f"{lon:.4f}" for _, lon in points),
        "hourly": ",".join(HOURLY_VARS),
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "GMT",
        "forecast_days": days,
        "cell_selection": "land",
    }

    last_exc: Exception | None = None
    for attempt in (1, 2):  # one retry on transient failure
        try:
            with client() as c:
                resp = c.get(f"{settings.OPEN_METEO_BASE_URL}/forecast", params=params)
            if resp.status_code >= 500 and attempt == 1:
                last_exc = WeatherProviderError(f"Open-Meteo server error (HTTP {resp.status_code})")
                continue
            if resp.status_code != 200:
                detail = ""
                try:
                    body = resp.json()
                    detail = str(body.get("reason", ""))[:200]
                except Exception:
                    pass
                raise WeatherProviderError(f"Open-Meteo rejected the request (HTTP {resp.status_code}) {detail}")
            payload = resp.json()
            break
        except WeatherProviderError:
            raise
        except Exception as exc:
            last_exc = exc
            if attempt == 2:
                raise WeatherProviderError(f"Open-Meteo request failed after retry: {exc}") from exc
    else:  # pragma: no cover
        raise WeatherProviderError(f"Open-Meteo request failed: {last_exc}")

    entries = payload if isinstance(payload, list) else [payload]
    if len(entries) != len(points):
        raise WeatherProviderError(
            f"Open-Meteo returned {len(entries)} locations for {len(points)} requested points"
        )

    forecasts = [_normalize_location(entry) for entry in entries]
    if use_cache:
        cache.set(cache_key, forecasts, settings.WEATHER_CACHE_TTL)
    return forecasts

"""Weather unit conversion and forecast timestamp matching tests."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from services.weather import selection
from services.weather.open_meteo import _normalize_location
from services.weather.selection import condition_text, sample_at
from tests.conftest import load_fixture


def _forecast_from_fixture(name: str = "open_meteo_checkpoints.json", index: int = 0):
    return _normalize_location(load_fixture(name)[index])


# Unit conversion
def test_snowfall_cm_converted_to_inches():
    fc = _forecast_from_fixture(index=0)
    # fixture snowfall at hour 6 is 2.54 cm -> exactly 1.0 in/hr
    assert fc.snow_in_hr[6] == pytest.approx(1.0)
    assert fc.snow_in_hr[8] == pytest.approx(3.0)   # 7.62 cm
    assert any("snowfall" in note for note in fc.unit_notes)


def test_wind_stays_mph_and_rain_inches():
    fc = _forecast_from_fixture(index=0)
    assert fc.wind_mph[5] == pytest.approx(60.0)
    assert fc.rain_in_hr[5] == pytest.approx(1.20)


def test_temperature_stored_celsius_converted_fahrenheit_for_display():
    assert selection.celsius_to_fahrenheit(0.0) == 32.0
    assert selection.celsius_to_fahrenheit(100.0) == 212.0
    assert selection.celsius_to_fahrenheit(-40.0) == -40.0
    assert selection.celsius_to_fahrenheit(None) is None


def test_precipitation_crosscheck_separated_from_rain():
    # precipitation = rain + snow-water-equivalent (7cm snow ≈ 10mm water) —
    # the adapter keeps `rain` pure and never uses `precipitation` as rainfall.
    fc = _forecast_from_fixture(index=0)
    assert fc.rain_in_hr[8] == pytest.approx(0.0)          # pure rain is zero...
    assert fc.precipitation_in_hr[8] > 0                   # ...but total precip is not
    assert fc.snow_in_hr[8] == pytest.approx(3.0)


def test_condition_text_mapping():
    assert condition_text(0) == "Clear sky"
    assert condition_text(75) == "Heavy snowfall"
    assert condition_text(None) is None
    assert condition_text(1234).startswith("Unknown")


# Forecast timestamp matching / interpolation
def test_sample_at_interpolates_between_hours():
    fc = _forecast_from_fixture(index=0)
    eta = fc.times_utc[0] + timedelta(minutes=30)  # halfway between hour 0 and 1
    sample = sample_at(fc, eta)
    assert sample.available is True
    assert sample.interpolated is True
    assert sample.wind_mph == pytest.approx(15.0)          # (10 + 20) / 2
    assert sample.rain_in_hr == pytest.approx(0.025)       # (0 + 0.05) / 2
    assert sample.temperature_f == pytest.approx(4.0 * 9 / 5 + 32 - 0.45)


def test_sample_at_exact_hour_no_interpolation():
    fc = _forecast_from_fixture(index=0)
    sample = sample_at(fc, fc.times_utc[5])
    assert sample.available is True
    assert sample.interpolated is False
    assert sample.wind_mph == pytest.approx(60.0)
    assert sample.forecast_time == fc.times_utc[5]


def test_sample_at_before_window_is_unavailable():
    fc = _forecast_from_fixture(index=0)
    early = fc.times_utc[0] - timedelta(hours=2)
    sample = sample_at(fc, early)
    assert sample.available is False
    assert "before" in sample.unavailability_reason
    assert sample.wind_mph is None


def test_sample_at_after_horizon_is_unavailable():
    fc = _forecast_from_fixture(index=0)
    late = fc.times_utc[-1] + timedelta(hours=1)
    sample = sample_at(fc, late)
    assert sample.available is False
    assert "beyond" in sample.unavailability_reason


def test_sample_at_condition_from_nearest_hour():
    fc = _forecast_from_fixture(index=0)
    # 12 minutes past hour 5 -> nearest is hour 5 (thunderstorm, code 95)
    eta = fc.times_utc[5] + timedelta(minutes=12)
    sample = sample_at(fc, eta)
    assert sample.condition == "Thunderstorm"
    assert sample.weather_code == 95


def test_sample_at_handles_none_brackets():
    fc = _forecast_from_fixture(index=1)  # calm location; rain/snow all zero
    eta = fc.times_utc[3] + timedelta(minutes=30)
    sample = sample_at(fc, eta)
    assert sample.available
    assert sample.rain_in_hr == pytest.approx(0.0)
    assert sample.snow_in_hr == pytest.approx(0.0)


def test_sample_never_fabricates_missing_data():
    fc = _forecast_from_fixture(index=0)
    # Simulate a provider gap: wipe wind at both bracketing hours.
    fc.wind_mph[4] = None
    fc.wind_mph[5] = None
    sample = sample_at(fc, fc.times_utc[4] + timedelta(minutes=30))
    assert sample.available is True
    assert sample.wind_mph is None  # gap stays a gap


def test_naive_eta_treated_as_utc():
    fc = _forecast_from_fixture(index=0)
    naive = (fc.times_utc[2] + timedelta(minutes=15)).replace(tzinfo=None)
    sample = sample_at(fc, naive)
    assert sample.available is True
    assert sample.wind_mph == pytest.approx(32.5)


def test_empty_forecast_is_unavailable():
    from services.weather.open_meteo import HourlyForecast

    fc = HourlyForecast(
        lat=0, lon=0, times_utc=[], temperature_c=[], wind_mph=[], wind_gust_mph=[],
        rain_in_hr=[], snow_in_hr=[], precipitation_in_hr=[], weather_code=[],
    )
    sample = sample_at(fc, datetime.now(UTC))
    assert sample.available is False
    assert sample.to_dict()["source"] is None

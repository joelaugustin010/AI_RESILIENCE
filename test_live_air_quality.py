import json

import pandas as pd
import pytest

from src.live_air_quality import (
    LiveAirQualityError,
    fetch_open_meteo,
    freshness_label,
    parse_open_meteo_response,
    aqi_category,
)


def fake_opener(payload):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(payload).encode()

    return lambda request, timeout: FakeResponse()


def sample_payload():
    times = ["2026-11-03T10:00Z", "2026-11-03T11:00Z"]
    return {
        "latitude": 9.9312,
        "longitude": 76.2673,
        "timezone": "UTC",
        "current": {
            "time": times[-1], "european_aqi": 42, "us_aqi": 55,
            "pm2_5": 18, "pm10": 44, "carbon_monoxide": 210,
            "nitrogen_dioxide": 12, "sulphur_dioxide": 3, "ozone": 64,
            "carbon_dioxide": 421,
        },
        "current_units": {"pm2_5": "µg/m³", "european_aqi": "EAQI"},
        "hourly": {
            "time": times,
            "european_aqi": [40, 42], "us_aqi": [52, 55],
            "pm2_5": [17, 18], "pm10": [43, 44],
            "carbon_monoxide": [200, 210], "nitrogen_dioxide": [11, 12],
            "sulphur_dioxide": [2, 3], "ozone": [62, 64],
            "carbon_dioxide": [420, 421],
        },
    }


def test_successful_response_normalizes_current_and_hourly_values():
    result = parse_open_meteo_response(sample_payload())
    assert result["current"]["European AQI"]["value"] == 42
    assert result["current"]["PM2.5"]["unit"] == "µg/m³"
    assert set(result["hourly"]["pollutant"]) == {
        "European AQI", "US AQI", "PM2.5", "PM10", "CO", "NO2", "SO2", "O3", "CO2"
    }
    assert result["observed_at"].tz is not None


def test_fetch_uses_no_key_api_and_returns_live_result():
    result = fetch_open_meteo(opener=fake_opener(sample_payload()))
    assert result["status"] == "live"
    assert "latitude=9.9312" in result["request_url"]
    assert "european_aqi" in result["request_url"]


def test_request_includes_all_required_variables():
    result = fetch_open_meteo(opener=fake_opener(sample_payload()))
    for variable in ("european_aqi", "us_aqi", "pm2_5", "pm10", "carbon_monoxide",
                     "nitrogen_dioxide", "sulphur_dioxide", "ozone", "carbon_dioxide"):
        assert variable in result["request_url"]


def test_invalid_response_and_mismatched_series_are_rejected():
    with pytest.raises(LiveAirQualityError):
        parse_open_meteo_response({"hourly": {"time": ["2026-11-03T10:00Z"], "pm2_5": []}})
    with pytest.raises(LiveAirQualityError):
        parse_open_meteo_response({"hourly": {"time": ["2026-11-03T10:00Z"]}})


def test_timeout_is_reported_without_cached_or_fabricated_values():
    def fail(request, timeout):
        raise TimeoutError("timed out")

    with pytest.raises(LiveAirQualityError, match="connection failed"):
        fetch_open_meteo(opener=fail, timeout=1)


def test_stale_observation_is_explicitly_labelled():
    frame = pd.DataFrame({"observed_at": ["2026-11-01T00:00:00Z"]})
    assert freshness_label(frame, now=pd.Timestamp("2026-11-03T00:00:00Z")) == "Stale · 48.0 h old"


def test_aqi_standards_have_separate_breakpoints():
    assert aqi_category("US AQI", 88)["label"] == "Moderate"
    assert aqi_category("EAQI", 46)["label"] == "Moderate"
    assert aqi_category("US AQI", 151)["label"] == "Unhealthy"

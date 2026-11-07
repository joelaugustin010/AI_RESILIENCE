from __future__ import annotations

import pytest

from scripts.acquire_kerala_weather_transfer_data import validate_payload


def payload():
    return {
        "timezone": "Asia/Kolkata",
        "daily": {
            "time": [f"2020-01-{day:02d}" for day in range(1, 32)] * 10 + ["2020-11-01"],
            "units": {"precipitation_sum": "mm"},
            "temperature_2m_max": [30.0] * 311,
            "temperature_2m_min": [20.0] * 311,
            "precipitation_sum": [0.0] * 311,
            "wind_speed_10m_max": [10.0] * 311,
            "wind_gusts_10m_max": [20.0] * 311,
        },
    }


def test_weather_payload_checks_aligned_numeric_daily_fields():
    data = payload()
    # Use a monotonic, unique daily date index of sufficient length.
    import pandas as pd
    dates = pd.date_range("2020-01-01", periods=311, freq="D").strftime("%Y-%m-%d").tolist()
    data["daily"]["time"] = dates
    result = validate_payload(data, start_date=dates[0], end_date=dates[-1])
    assert result["rows"] == 311
    assert result["first_date"] == dates[0]


def test_weather_payload_rejects_duplicate_dates():
    data = payload()
    data["daily"]["time"] = ["2020-01-01"] * 311
    with pytest.raises(ValueError, match="unique"):
        validate_payload(data, start_date="2020-01-01", end_date="2020-01-01")


def test_weather_payload_rejects_negative_precipitation():
    data = payload()
    import pandas as pd
    dates = pd.date_range("2020-01-01", periods=311, freq="D").strftime("%Y-%m-%d").tolist()
    data["daily"]["time"] = dates
    data["daily"]["precipitation_sum"][0] = -1.0
    with pytest.raises(ValueError, match="negative"):
        validate_payload(data, start_date=dates[0], end_date=dates[-1])

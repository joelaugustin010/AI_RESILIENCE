import pandas as pd
import pytest

from src.air_quality_dashboard import (
    HEALTH_INFORMATION,
    aggregate_co2_trend,
    assess_pollutant,
    co2_context,
    compare_pollutant,
    evidence_category,
    disaster_air_intelligence,
    scenario_aqi_summary,
    scenario_pollutant_values,
)
from src.live_air_quality import AQI_VARIABLES


def test_hourly_model_reading_is_not_misrepresented_as_daily_guideline_assessment():
    result = compare_pollutant("PM2.5", 24.7, "µg/m³", averaging_period="hourly")
    assert result["status"] == "Cannot assess"


def test_units_and_missing_values_are_validated():
    assert compare_pollutant("CO", 2, "mg/m³", averaging_period="24-hour")["status"] == "Cannot assess"
    assert compare_pollutant("PM10", None, "µg/m³", averaging_period="24-hour")["status"] == "Cannot assess"


def test_facility_presence_is_not_attribution():
    assert evidence_category(documented_facility_presence=True) == "Documented potential contributor"
    assert evidence_category() == "Insufficient evidence"
    assert evidence_category(measured_facility_emissions=True) == "Confirmed emissions evidence"


def test_compatible_trailing_window_gets_colour_classification():
    times = pd.date_range("2026-11-03", periods=24, freq="h", tz="UTC")
    hourly = pd.DataFrame({"observed_at": times, "pollutant": "PM2.5", "value": [10.0] * 24})
    result = assess_pollutant("PM2.5", 10, "µg/m³", hourly)
    assert result["status"] == "Within WHO health guideline"
    assert result["color"] == "#198754"


def test_elevated_and_red_classifications_are_distinct():
    times = pd.date_range("2026-11-03", periods=24, freq="h", tz="UTC")
    hourly = pd.DataFrame({"observed_at": times, "pollutant": "PM10", "value": [55.0] * 24})
    assert assess_pollutant("PM10", 55, "µg/m³", hourly)["status"] == "Elevated"
    hourly["value"] = 120.0
    assert assess_pollutant("PM10", 120, "µg/m³", hourly)["status"] == "Very high — reduce exposure"


def test_health_information_covers_all_displayed_pollutants():
    assert set(("PM2.5", "PM10", "NO2", "SO2", "CO", "O3")) <= set(HEALTH_INFORMATION)


def test_co2_is_context_only_and_not_an_aqi_pollutant():
    context = co2_context(447)
    assert context["status"] == "Outdoor context only"
    assert "carbon_dioxide" not in AQI_VARIABLES


def test_co2_trends_aggregate_returned_observations_without_fabricating_periods():
    observations = pd.DataFrame({
        "observed_at": pd.to_datetime(["2026-11-01T01:00Z", "2026-11-01T03:00Z", "2026-11-03T01:00Z"]),
        "pollutant": ["CO2", "CO2", "CO2"],
        "value": [440, 450, 460],
    })
    daily = aggregate_co2_trend(observations, "daily")
    assert len(daily) == 2
    assert daily.iloc[0]["value"] == 445
    assert daily.iloc[0]["observations"] == 2


def test_co2_trend_rejects_unknown_period():
    with pytest.raises(ValueError):
        aggregate_co2_trend(pd.DataFrame(), "yearly")


def test_scenario_values_preserve_external_and_user_provenance():
    current = {"PM2.5": {"value": 20, "unit": "µg/m³"}, "CO2": {"value": 420, "unit": "ppm"}}
    hourly = pd.DataFrame({
        "observed_at": pd.to_datetime(["2026-11-04T01:00Z", "2026-11-04T03:00Z"]),
        "pollutant": ["PM2.5", "PM10"], "value": [25, 45], "unit": ["µg/m³", "µg/m³"],
    })
    values = scenario_pollutant_values(
        current, hourly, mode="forecast", observed_at=pd.Timestamp("2026-11-04T00:00Z"),
        overrides={"PM2.5": 60},
    )
    assert values["PM2.5"]["source"] == "User-entered simulated value"
    assert values["PM10"]["source"] == "External CAMS/Open-Meteo forecast"
    assert values["CO2"]["source"] == "External CAMS/Open-Meteo model estimate"


def test_scenario_aqi_requires_cpcb_eligibility_and_uses_subindices():
    insufficient = scenario_aqi_summary({"PM2.5": {"value": 60, "unit": "µg/m³"}})
    assert insufficient["scenario_index"] is None
    available = scenario_aqi_summary({
        "PM2.5": {"value": 60, "unit": "µg/m³"},
        "PM10": {"value": 100, "unit": "µg/m³"},
        "NO2": {"value": 80, "unit": "µg/m³"},
    })
    assert available["scenario_index"] is not None
    assert available["status"] == "scenario_index_available"


def test_disaster_air_intelligence_does_not_claim_disaster_probability():
    result = disaster_air_intelligence(
        {"PM2.5": {"value": 60, "unit": "µg/m³", "source": "User-entered simulated value"}},
        "Flood / waterlogging",
    )
    assert result["status"] == "Air-quality precaution signal"
    assert result["signals"][0]["pollutant"] == "PM2.5"
    assert "probability" not in result

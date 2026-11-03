import pytest
from src.air_quality_dashboard import classify_reference, period_matches

@pytest.mark.parametrize(
    ("pollutant", "value", "period", "unit", "expected"),
    [
        ("PM2.5", 35, "24-hour average", "µg/m³", "within"),
        ("PM2.5", 75, "24-hour average", "µg/m³", "above"),
        ("PM10", 80, "24-hour", "ug/m3", "within"),
        ("NO₂", 90, "24-hour average", "µg/m³", "above"),
        ("SO₂", 70, "24-hour average", "µg/m³", "within"),
        ("CO", 1.5, "8-hour average", "mg/m³", "within"),
        ("O₃", 110, "8-hour average", "µg/m³", "above"),
    ],
)
def test_classifies_only_matching_valid_observations(pollutant, value, period, unit, expected):
    status, _ = classify_reference(value, period, "valid", pollutant, unit)
    assert status == expected

@pytest.mark.parametrize(
    ("period", "expected"),
    [("24-hour average", True), ("8-hour average", True), ("daily", False), ("hourly", False), ("", False)],
)
def test_period_matching_is_explicit(period, expected):
    target = "24-hour" if period.startswith("24") else "8-hour"
    assert period_matches(period, target) is expected

def test_unassessed_quality_never_gets_a_colour_classification():
    status, message = classify_reference(25, "24-hour average", "unassessed", "PM2.5", "µg/m³")
    assert status == "unavailable"
    assert "quality" in message.lower()

def test_mismatched_period_never_gets_a_colour_classification():
    status, message = classify_reference(25, "daily", "valid", "PM2.5", "µg/m³")
    assert status == "unavailable"
    assert "24-hour" in message

def test_co2_is_not_an_aqi_pollutant_reference():
    status, _ = classify_reference(447, "24-hour average", "valid", "CO2", "ppm")
    assert status == "unavailable"

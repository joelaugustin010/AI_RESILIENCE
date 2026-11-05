import pytest

from src.disaster_air_dispersion import (
    DispersionInputError,
    gaussian_plume_concentration,
    run_gaussian_plume,
    validate_inputs,
)


def valid_inputs():
    return {
        "incident_type": "Industrial chemical accident",
        "source_latitude": 10.079692,
        "source_longitude": 76.296766,
        "pollutant": "SO2",
        "release_rate_g_s": 10.0,
        "duration_min": 30.0,
        "release_height_m": 10.0,
        "wind_speed_m_s": 2.0,
        "wind_from_deg": 90.0,
        "stability_class": "D",
    }


def test_gaussian_plume_is_finite_and_decreases_downwind():
    near = gaussian_plume_concentration(
        release_rate_g_s=10, wind_speed_m_s=2, release_height_m=10,
        distance_m=100, stability_class="D"
    )
    far = gaussian_plume_concentration(
        release_rate_g_s=10, wind_speed_m_s=2, release_height_m=10,
        distance_m=2000, stability_class="D"
    )
    assert near > 0
    assert far < near


def test_missing_release_information_prevents_prediction():
    validation = validate_inputs({"incident_type": "Industrial chemical accident"})
    assert validation["valid"] is False
    result = run_gaussian_plume({"incident_type": "Industrial chemical accident"})
    assert result["status"] == "missing_essentials"
    assert result["rows"] == []


def test_volcanic_and_wildfire_are_not_run_through_industrial_plume():
    for incident_type in ("Volcanic eruption", "Wildfire"):
        result = run_gaussian_plume({"incident_type": incident_type})
        assert result["status"] == "specialized_model_unavailable"
        assert result["rows"] == []


def test_valid_incident_returns_traceable_receptors_and_arrival_times():
    result = run_gaussian_plume(valid_inputs(), distances_m=[100, 500])
    assert result["status"] == "modelled"
    assert len(result["rows"]) == 2
    assert result["rows"][0]["source"].startswith("Gaussian plume model")
    assert result["rows"][0]["arrival_min"] < result["rows"][1]["arrival_min"]
    assert result["rows"][0]["longitude"] < valid_inputs()["source_longitude"]
    assert result["timeline"][-1]["concentration_mg_m3"] == 0.0
    assert any(item["concentration_mg_m3"] > 0 for item in result["timeline"])


def test_invalid_wind_and_distance_are_rejected():
    with pytest.raises(DispersionInputError):
        gaussian_plume_concentration(release_rate_g_s=1, wind_speed_m_s=0, release_height_m=0, distance_m=100, stability_class="D")
    with pytest.raises(DispersionInputError):
        run_gaussian_plume(valid_inputs(), distances_m=[0])

"""Validation and model-gating tests for the Ernakulam input predictor."""

import pytest

from src.ernakulam_disaster_dashboard import load_location_registry, location_options
from src.ernakulam_input_predictions import (
    HAZARD_MODELS,
    INPUTS,
    InputValidationError,
    predict_all_hazards,
    predict_hazard,
    load_hazard_evidence_context,
    validated_probability,
    validate_environmental_inputs,
    validate_location,
    validate_simple_observations,
)


VALID_INPUTS = {
    "rainfall_intensity_mm_h": 12.5,
    "water_level_m": 1.4,
    "wind_speed_kmh": 20.0,
    "pressure_hpa": 1008.0,
    "soil_moisture_percent": 61.0,
    "temperature_c": 27.5,
    "accumulated_rainfall_24h_mm": 84.0,
    "accumulated_rainfall_72h_mm": 152.0,
    "rainfall_duration_h": 2.5,
    "water_level_rise_m_h": 0.2,
    "wind_gust_kmh": 34.0,
    "relative_humidity_percent": 82.0,
    "rainfall_deficit_30d_percent": 12.0,
    "rainfall_deficit_90d_percent": 18.0,
    "rainfall_forecast_24h_mm": 36.0,
    "storm_distance_km": 180.0,
    "coastal_surge_m": 0.4,
    "slope_degrees": 18.0,
}
WATER_LEVEL_REFERENCE = "Neeleshwaram station / published local datum"


class FixedProbabilityModel:
    classes_ = [0, 1]

    def predict_proba(self, frame):
        assert len(frame) == 1
        return [[0.35, 0.65]]


def _validated_bundle(hazard_id, location, *, evaluation=None, training=None):
    features = list(HAZARD_MODELS[hazard_id]["features"])
    simple_feature_map = {
        "rainfall_intensity_mm_h": {
            "answer_field": "rain",
            "value_map": {"Heavy": 12.5},
        },
        "accumulated_rainfall_24h_mm": {
            "answer_field": "rain",
            "value_map": {"Heavy": 84.0},
        },
        "accumulated_rainfall_72h_mm": {
            "answer_field": "rain",
            "value_map": {"Heavy": 152.0},
        },
        "rainfall_duration_h": {
            "answer_field": "duration",
            "value_map": {"1–3 hours": 2.5},
        },
        "water_level_m": {
            "answer_field": "water_rising",
            "value_map": {"Rising quickly": 1.4},
        },
        "water_level_rise_m_h": {
            "answer_field": "water_rising",
            "value_map": {"Rising quickly": 0.2},
        },
    }
    return {
        "hazard_id": hazard_id,
        "model": FixedProbabilityModel(),
        "metadata": {
            "hazard_id": hazard_id,
            "district": "Ernakulam",
            "model_status": "validated",
            "evidence_status": "verified",
            "geographic_scope": (
                "district"
                if location == "Ernakulam district (all areas)"
                else "locality"
            ),
            "supported_locations": [location],
            "feature_names": features,
            "simple_mode_mapping": {
                "validated": True,
                "mapping_id": f"reviewed_{hazard_id}_simple_mapping_v1",
                "evidence_reference": "Independent local calibration study, report v1.",
                "feature_mappings": {
                    feature: simple_feature_map[feature]
                    for feature in features
                    if feature in simple_feature_map
                },
            },
            "target_definition": "Verified event starts within the next 24 hours.",
            "forecast_horizon": "Next 24 hours",
            "plain_language_explanation": (
                "This evaluated model uses the submitted, measured conditions."
            ),
            "confidence": "Moderate; based on held-out calibration.",
            "evaluation": evaluation
            or {
                "chronological_validation": True,
                "calibration_checked": True,
                "probabilities_calibrated": True,
                "beats_baselines": True,
            },
            "training": training
            or {
                "dataset_id": f"verified_{hazard_id}_observations_v1",
                "source_manifest_verified": True,
                "genuine_records": 200,
                "positive_records": 50,
                "negative_records": 150,
            },
            "metrics": {
                "precision": 0.7,
                "recall": 0.65,
                "f1": 0.67,
                "roc_auc": 0.8,
                "pr_auc": 0.72,
                "brier_score": 0.15,
            },
            "baseline_metrics": {
                "f1": 0.5,
                "pr_auc": 0.5,
                "brier_score": 0.25,
            },
            "risk_thresholds": {
                "moderate": 0.25,
                "high": 0.5,
                "very_high": 0.75,
            },
            "risk_threshold_basis": "Predefined on a separate validation period.",
        },
    }


def test_all_verified_ernakulam_locations_resolve_and_reject_other_districts():
    options = location_options(load_location_registry())
    assert len(options) == 97
    for location in options:
        validate_location(location)
    with pytest.raises(ValueError, match="within Ernakulam"):
        validate_location("Kottayam")


def test_input_validation_preserves_measured_values_and_requires_water_datum():
    values = validate_environmental_inputs(
        VALID_INPUTS, "Neeleshwaram station / published local datum"
    )
    assert values == {key: float(value) for key, value in VALID_INPUTS.items()}

    with pytest.raises(InputValidationError) as error:
        validate_environmental_inputs(VALID_INPUTS, "")
    assert "water_level_reference" in error.value.errors


@pytest.mark.parametrize(
    "field,value",
    [
        ("rainfall_intensity_mm_h", -1),
        ("water_level_m", 51),
        ("wind_speed_kmh", float("inf")),
        ("pressure_hpa", float("nan")),
        ("soil_moisture_percent", 101),
        ("temperature_c", 61),
        ("temperature_c", True),
        ("temperature_c", "not a measurement"),
    ],
)
def test_input_validation_rejects_invalid_or_out_of_range_values(field, value):
    values = dict(VALID_INPUTS)
    values[field] = value
    with pytest.raises(InputValidationError):
        validate_environmental_inputs(values, "local station datum")


def test_missing_environmental_readings_are_never_defaulted():
    values = dict(VALID_INPUTS)
    del values["pressure_hpa"]
    validated = validate_environmental_inputs(values, "local station datum")
    assert "pressure_hpa" not in validated
    assert "pressure_hpa" not in values


def test_simple_answers_are_validated_without_numeric_conversion():
    observations = {
        "rain": "Heavy",
        "water_rising": "I don't know",
        "wind": "Strong",
        "weather": "Humid",
        "ground": "Wet",
        "duration": "1–3 hours",
        "water_collecting": "No",
        "unusual_changes": "I don't know",
        "storm_warning": "I don't know",
        "slope_signs": "I don't know",
        "recent_rainfall": "I don't know",
        "water_shortage": "I don't know",
    }
    assert validate_simple_observations(observations) == observations
    with pytest.raises(InputValidationError, match="Choose an answer"):
        validate_simple_observations({**observations, "wind": None})


def test_all_hazards_return_distinct_model_gaps_without_fake_probabilities():
    results = predict_all_hazards(
        "Ernakulam district (all areas)",
        VALID_INPUTS,
        "Neeleshwaram station / published local datum",
    )
    assert {result["hazard_id"] for result in results} == set(HAZARD_MODELS)
    assert set(HAZARD_MODELS) == {"flood", "cyclone", "landslide", "drought"}
    assert len({result["additional_requirements"] for result in results}) == 4
    assert all(result["reference_evidence"] for result in results)
    assert all(result["probability"] is None for result in results)
    assert all(result["status"] == "preliminary_assessment" for result in results)
    assert all(result["assessment_method"].startswith("Preliminary") for result in results)
    assert all(result["probability"] is None for result in results)


def test_reference_evidence_is_scoped_and_flood_scenarios_are_context_only():
    flood_evidence = load_hazard_evidence_context("flood")

    assert "Ernakulam district aggregate" in flood_evidence["spatial_coverage"]
    assert len(flood_evidence["historical_scenario"]) == 6
    assert flood_evidence["historical_scenario"][0]["return_period_years"] == 10
    assert flood_evidence["historical_scenario"][0]["area_affected_sq_km"] == 458.67
    assert flood_evidence["source_retrieved_on"] == "2026-10-31"

    with pytest.raises(ValueError, match="Unsupported"):
        load_hazard_evidence_context("unknown_hazard")


def test_four_hazards_return_preliminary_assessments_for_relevant_simple_observations():
    observations = {
        "rain": "Very heavy",
        "water_rising": "Rising quickly",
        "wind": "Very strong",
        "weather": "Stormy",
        "ground": "Saturated",
        "duration": "More than 6 hours",
        "water_collecting": "Across roads or near homes",
        "unusual_changes": "Yes",
        "storm_warning": "I heard an official warning",
        "slope_signs": "Yes",
        "recent_rainfall": "Much less than usual",
        "water_shortage": "Serious shortage",
    }
    results = predict_all_hazards(
        "Aluva Municipality",
        {},
        input_mode="simple",
        simple_observations=observations,
    )

    assert len(results) == 4
    assert all(result["status"] == "preliminary_assessment" for result in results)
    assert all(result["risk_label"] in {"Low", "Moderate", "High", "Very High"} for result in results)
    assert all(result["probability"] is None for result in results)
    assert all(result["risk_score"] is None for result in results)
    assert {result["hazard_id"]: result["risk_label"] for result in results} == {
        "flood": "Very High",
        "cyclone": "Very High",
        "landslide": "Very High",
        "drought": "Very High",
    }
    assert "overflowing water" in results[0]["explanation"]
    assert "official storm warning" in results[1]["explanation"]
    assert "new cracks or ground movement" in results[2]["explanation"]
    assert "serious local water shortage" in results[3]["explanation"]


def test_missing_inputs_are_not_treated_as_zero_or_as_low_risk():
    results = predict_all_hazards(
        "Ernakulam district (all areas)",
        {},
        input_mode="advanced",
    )
    by_hazard = {result["hazard_id"]: result for result in results}

    assert len(by_hazard) == 4
    assert all(item["status"] == "preliminary_assessment" for item in results)
    assert all(item["probability"] is None and item["risk_score"] is None for item in results)
    assert by_hazard["flood"]["risk_label"] == "Not enough evidence"
    assert not any(
        "0 mm" in condition
        for item in results
        for condition in item["contributing_conditions"]
    )
    assert all(item["missing_information"] for item in results)


def test_hazard_fallbacks_use_distinct_inputs_and_official_rainfall_categories():
    results = predict_all_hazards(
        "Aluva Municipality",
        {
            "accumulated_rainfall_24h_mm": 120.0,
            "water_level_rise_m_h": 0.1,
            "rainfall_deficit_30d_percent": 25,
            "rainfall_deficit_90d_percent": 30,
            "wind_speed_kmh": 20,
            "slope_degrees": 25,
        },
        "Aluva gauge / local datum",
        input_mode="advanced",
        assessment_observations={
            "storm_warning": "No warning that I know of",
            "slope_signs": "No",
            "recent_rainfall": "Less than usual",
            "water_shortage": "Some shortage",
        },
    )
    by_hazard = {result["hazard_id"]: result for result in results}

    assert by_hazard["flood"]["risk_label"] == "Moderate"
    assert by_hazard["drought"]["risk_label"] == "Moderate"
    assert by_hazard["cyclone"]["risk_label"] == "Not enough evidence"
    assert all(result["assessment_basis"] for result in results)


def test_simple_and_advanced_modes_use_the_same_four_prediction_pipelines(monkeypatch):
    calls = []

    def missing_model(hazard_id):
        calls.append(hazard_id)
        return None

    monkeypatch.setattr(
        "src.ernakulam_input_predictions.load_hazard_model",
        missing_model,
    )
    location = "Aluva Municipality"
    simple = predict_all_hazards(
        location,
        {},
        input_mode="simple",
        simple_observations={
            "rain": "Heavy",
            "water_rising": "Rising quickly",
            "wind": "Strong",
            "weather": "Humid",
            "ground": "Wet",
            "duration": "1–3 hours",
            "water_collecting": "No",
            "unusual_changes": "I don't know",
            "storm_warning": "I don't know",
            "slope_signs": "I don't know",
            "recent_rainfall": "I don't know",
            "water_shortage": "I don't know",
        },
    )
    advanced = predict_all_hazards(
        location,
        VALID_INPUTS,
        "Neeleshwaram station / local datum",
        input_mode="advanced",
    )

    assert len(calls) == 8
    assert len(HAZARD_MODELS) == 4
    assert [item["hazard_id"] for item in simple] == list(HAZARD_MODELS)
    assert [item["hazard_id"] for item in advanced] == list(HAZARD_MODELS)
    assert all(item["probability"] is None for item in simple + advanced)
    assert {item["input_mode"] for item in simple} == {"simple"}
    assert {item["input_mode"] for item in advanced} == {"advanced"}
    assert all(item["assessment_method"].startswith("Preliminary") for item in simple + advanced)


def test_prediction_rejects_unknown_hazards_and_non_ernakulam_locations():
    with pytest.raises(ValueError, match="Unsupported"):
        predict_hazard("earthquake", "Aluva Municipality", VALID_INPUTS)
    with pytest.raises(ValueError, match="within Ernakulam"):
        predict_hazard("flood", "Thrissur", VALID_INPUTS)


def test_unqualified_model_cannot_return_a_probability():
    bundle = _validated_bundle(
        "flood",
        "Aluva Municipality",
        evaluation={
            "chronological_validation": False,
            "calibration_checked": True,
            "probabilities_calibrated": True,
            "beats_baselines": True,
        },
    )
    result = predict_hazard(
        "flood",
        "Aluva Municipality",
        VALID_INPUTS,
        bundle,
        water_level_reference=WATER_LEVEL_REFERENCE,
    )
    assert result["probability"] is None
    assert result["status"] == "preliminary_assessment"
    assert "checks failed" in result["status_reason"]


def test_validated_probability_display_contract_accepts_only_validated_values():
    assert validated_probability(
        {"status": "validated_prediction", "probability": 0.65}
    ) == pytest.approx(0.65)
    assert validated_probability(
        {"status": "preliminary_assessment", "probability": 0.65}
    ) is None
    assert validated_probability(
        {"status": "validated_prediction", "probability": None}
    ) is None
    assert validated_probability(
        {"status": "validated_prediction", "probability": 1.2}
    ) is None


def test_model_without_calibrated_probabilities_is_rejected():
    bundle = _validated_bundle("flood", "Aluva Municipality")
    bundle["metadata"]["evaluation"]["probabilities_calibrated"] = False
    result = predict_hazard(
        "flood",
        "Aluva Municipality",
        VALID_INPUTS,
        bundle,
        water_level_reference=WATER_LEVEL_REFERENCE,
    )
    assert result["probability"] is None
    assert "checks failed" in result["status_reason"]


def test_validated_matching_model_uses_its_own_inputs_and_thresholds():
    location = "Aluva Municipality"
    bundle = _validated_bundle("flood", location)
    result = predict_hazard(
        "flood",
        location,
        VALID_INPUTS,
        bundle,
        water_level_reference=WATER_LEVEL_REFERENCE,
    )
    assert result["probability"] == pytest.approx(0.65)
    assert result["risk_label"] == "High"
    assert result["forecast_horizon"] == "Next 24 hours"
    assert result["status"] == "validated_prediction"


def test_simple_mode_only_converts_answers_with_validated_model_mapping():
    location = "Aluva Municipality"
    observations = {
        "rain": "Heavy",
        "water_rising": "Rising quickly",
        "wind": "I don't know",
        "weather": "I don't know",
        "ground": "I don't know",
        "duration": "1–3 hours",
        "water_collecting": "I don't know",
        "unusual_changes": "I don't know",
        "storm_warning": "I don't know",
        "slope_signs": "I don't know",
        "recent_rainfall": "I don't know",
        "water_shortage": "I don't know",
    }
    bundle = _validated_bundle("flood", location)
    result = predict_hazard(
        "flood",
        location,
        {},
        bundle,
        input_mode="simple",
        simple_observations=observations,
    )
    assert result["probability"] == pytest.approx(0.65)

    del bundle["metadata"]["simple_mode_mapping"]
    result = predict_hazard(
        "flood",
        location,
        {},
        bundle,
        input_mode="simple",
        simple_observations=observations,
    )
    assert result["probability"] is None
    assert "not converted to measurements" in result["status_reason"]


def test_simple_mode_does_not_convert_i_dont_know_to_a_measurement():
    location = "Aluva Municipality"
    observations = {
        "rain": "Heavy",
        "water_rising": "I don't know",
        "wind": "I don't know",
        "weather": "I don't know",
        "ground": "I don't know",
        "duration": "1–3 hours",
        "water_collecting": "I don't know",
        "unusual_changes": "I don't know",
        "storm_warning": "I don't know",
        "slope_signs": "I don't know",
        "recent_rainfall": "I don't know",
        "water_shortage": "I don't know",
    }
    result = predict_hazard(
        "flood",
        location,
        {},
        _validated_bundle("flood", location),
        input_mode="simple",
        simple_observations=observations,
    )
    assert result["probability"] is None
    assert "missing or marked unknown" in result["status_reason"]


def test_district_model_is_not_mislabeled_as_locality_prediction():
    bundle = _validated_bundle("flood", "Ernakulam district (all areas)")
    result = predict_hazard(
        "flood",
        "Aluva Municipality",
        VALID_INPUTS,
        bundle,
        water_level_reference=WATER_LEVEL_REFERENCE,
    )
    assert result["probability"] is None
    assert "selected location" in result["status_reason"]


def test_model_feature_schema_is_hazard_specific():
    bundle = _validated_bundle("cyclone", "Aluva Municipality")
    bundle["metadata"]["feature_names"] = list(INPUTS)
    result = predict_hazard(
        "cyclone",
        "Aluva Municipality",
        VALID_INPUTS,
        bundle,
        water_level_reference=WATER_LEVEL_REFERENCE,
    )
    assert result["probability"] is None
    assert "feature schema" in result["status_reason"]

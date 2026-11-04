"""End-to-end evidence and geographic safeguards for the Ernakulam dashboard."""

import json
from pathlib import Path

import pytest

from src.ernakulam_disaster_dashboard import (
    HAZARDS,
    SUMMARY_PATH,
    build_assessment_cards,
    build_prediction_card,
    format_probability,
    load_assessment_data,
    load_location_registry,
    location_options,
)


ROOT = Path(__file__).resolve().parents[1]
LOCATION_PATH = ROOT / "data" / "reference" / "ernakulam_locations.json"


@pytest.fixture(scope="module")
def assessment_data():
    return load_assessment_data()


def _validated_result(hazard_id, location, probability=0.65):
    return {
        "model_status": "validated",
        "hazard_id": hazard_id,
        "district": "Ernakulam",
        "location": location,
        "evidence_status": "verified",
        "probability": probability,
        "forecast_period": "Next 24 hours",
        "confidence": "Moderate",
        "confidence_basis": "Held-out calibration and interval coverage.",
        "risk_thresholds": {
            "moderate": 0.25,
            "high": 0.50,
            "very_high": 0.75,
        },
        "risk_threshold_basis": "Documented thresholds evaluated on validation data.",
        "plain_language_explanation": "A verified local forecast is available.",
        "evaluation": {
            "chronological_validation": True,
            "calibration_checked": True,
            "beats_baselines": True,
        },
    }


def test_location_reference_contains_only_verified_ernakulam_local_bodies():
    registry = load_location_registry()
    options = location_options(registry)

    assert registry["district"] == "Ernakulam"
    assert registry["register_vintages"]["municipalities"] == 2020
    assert registry["register_vintages"]["grama_panchayats"] == 2020
    assert len(registry["municipalities"]) == 13
    assert len(registry["corporations"]) == 1
    assert len(registry["grama_panchayats"]) == 82
    assert len(options) == 97
    assert len(options) == len(set(options))
    assert options[0] == "Ernakulam district (all areas)"
    assert "Kochi Corporation" in options
    assert "Aluva Municipality" in options
    assert "Chendamangalam Grama Panchayat" in options
    assert all(
        registry["sources"][key]["url"].startswith("https://")
        for key in ("municipality", "corporation", "grama_panchayat")
    )


def test_location_reference_rejects_non_ernakulam_membership(tmp_path):
    registry = json.loads(LOCATION_PATH.read_text(encoding="utf-8"))
    registry["municipalities"][0] = "Kottayam"
    bad_reference = tmp_path / "locations.json"
    bad_reference.write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate|Ernakulam"):
        load_location_registry(bad_reference)


def test_all_locations_resolve_to_four_evidence_cards(assessment_data):
    options = location_options(load_location_registry())

    for location in options:
        cards = build_assessment_cards(location, options, assessment_data)
        assert {card["hazard_id"] for card in cards} == set(HAZARDS)
        assert all(card["location"] == location for card in cards)
        assert all(card["explanation"].strip() for card in cards)
        assert all(card["scope"].strip() for card in cards)


def test_all_four_hazards_load_distinct_evidence_and_results(assessment_data):
    options = location_options(load_location_registry())
    cards = build_assessment_cards(options[0], options, assessment_data)
    by_hazard = {card["hazard_id"]: card for card in cards}

    assert set(by_hazard) == set(HAZARDS)
    assert all(card["primary_value"] for card in cards)
    assert all(card["sources"] for card in cards)
    assert len({card["result_level"] for card in cards}) > 1
    assert by_hazard["flood"]["probability"] == pytest.approx(0.10)
    assert by_hazard["flood"]["result_level"] == "source_model_scenario"
    assert "district aggregate" in by_hazard["flood"]["scope"]
    assert by_hazard["cyclone"]["probability"] is None
    assert by_hazard["landslide"]["probability"] is None
    assert "2012" in by_hazard["landslide"]["explanation"]
    assert "2013" in by_hazard["landslide"]["explanation"]
    assert by_hazard["drought"]["result_level"] == "evidence_gap"
    assert set(by_hazard) == {"flood", "cyclone", "landslide", "drought"}


def test_local_source_data_are_loaded_and_quality_limits_are_reported(assessment_data):
    rainfall = assessment_data["rainfall"]
    cyclone = assessment_data["cyclone_tracks"]
    landslide_reports = assessment_data["landslide_reports"]

    assert rainfall["source_row_count"] == 2938
    assert rainfall["single_record_station_time_count"] == 1960
    assert rainfall["conflicting_station_time_groups"] == 103
    assert rainfall["station_names"] == ["Neeleshwaram EE, SWRD, Kochi"]
    assert cyclone["track_row_count"] > 0
    assert cyclone["storm_count"] > 0
    assert len(landslide_reports) == 3
    assert len({item["date"] for item in landslide_reports}) == 2


def test_only_source_reported_flood_scenario_has_a_probability(assessment_data):
    options = location_options(load_location_registry())
    cards = build_assessment_cards("Aluva Municipality", options, assessment_data)

    assert {
        card["hazard_id"] for card in cards if card["probability"] is not None
    } == {"flood"}
    flood = next(card for card in cards if card["hazard_id"] == "flood")
    assert flood["probability_text"] == "10.0%"
    assert "not the selected locality" in flood["scope"]
    assert flood["risk_label"] == "Not rated"


@pytest.mark.parametrize(
    "change",
    [
        {"district": "Kottayam"},
        {"location": "Kochi grid point"},
        {"evidence_status": "unverified"},
        {"model_status": "experimental"},
        {"evaluation": {"chronological_validation": False}},
        {"evaluation": {"calibration_checked": False}},
        {"evaluation": {"beats_baselines": False}},
    ],
)
def test_unqualified_model_outputs_fall_back_to_evidence_not_fake_probability(
    change, assessment_data
):
    options = location_options(load_location_registry())
    area = "Aluva Municipality"
    result = _validated_result("flood", area)
    result.update(change)

    card = build_prediction_card(
        "flood",
        area,
        options,
        result,
        assessment_data,
    )

    assert card["probability"] == pytest.approx(0.10)
    assert card["result_level"] == "source_model_scenario"
    assert card["risk_label"] == "Not rated"


def test_qualified_forecast_is_used_only_for_matching_location(assessment_data):
    options = location_options(load_location_registry())
    area = "Aluva Municipality"
    card = build_prediction_card(
        "flood",
        area,
        options,
        _validated_result("flood", area),
        assessment_data,
    )

    assert card["probability"] == 0.65
    assert card["probability_text"] == "65.0%"
    assert card["risk_label"] == "High"
    assert card["assessment_label"] == "Validated prediction"
    assert card["scope"] == area


def test_unknown_hazard_and_location_are_rejected(assessment_data):
    options = location_options(load_location_registry())

    with pytest.raises(ValueError, match="Unsupported"):
        build_prediction_card("earthquake", options[0], options, assessment_data=assessment_data)
    with pytest.raises(ValueError, match="verified"):
        build_prediction_card("flood", "Kottayam", options, assessment_data=assessment_data)


@pytest.mark.parametrize(
    "probability,expected",
    [(0, "0.0%"), (0.65, "65.0%"), (1, "100.0%")],
)
def test_probability_formatting(probability, expected):
    assert format_probability(probability) == expected


def test_missing_probability_is_not_converted_to_zero():
    assert format_probability(None) == "Not available"


@pytest.mark.parametrize(
    "probability",
    [-0.01, 1.01, float("nan"), float("inf"), True, "0.5"],
)
def test_invalid_probability_values_are_rejected(probability):
    with pytest.raises(ValueError):
        format_probability(probability)


def test_regenerated_summary_contains_actual_assessments_not_empty_cards():
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))

    assert summary["schema_version"] == 3
    assert summary["district"] == "Ernakulam"
    assert summary["location_count"] == 97
    assert {item["hazard_id"] for item in summary["hazards"]} == set(HAZARDS)
    assert all(item["primary_value"] for item in summary["hazards"])
    assert next(
        item for item in summary["hazards"] if item["hazard_id"] == "flood"
    )["probability"] == pytest.approx(0.10)

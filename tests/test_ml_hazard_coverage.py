"""Tests for truthful, task-aware coverage across all ten workflow hazards."""

from unittest.mock import patch

from src.hazard_registry import WORKFLOW_HAZARDS
from src.ml.coverage import HAZARD_MODEL_MAP, build_coverage_matrix


def _cards(status_by_id):
    return [
        {"model_id": model_id, "status": status}
        for model_id, status in status_by_id.items()
    ]


def test_model_map_covers_exactly_the_ten_authoritative_hazards():
    assert tuple(HAZARD_MODEL_MAP) == WORKFLOW_HAZARDS
    assert len(HAZARD_MODEL_MAP) == 10
    assert all(isinstance(model_ids, tuple) for model_ids in HAZARD_MODEL_MAP.values())


def test_missing_cards_are_not_reported_as_trained_or_predictive_coverage():
    with patch("src.ml.coverage.list_model_cards", return_value=[]):
        coverage = build_coverage_matrix(write=False)

    assert coverage["workflow_registry_complete"] is True
    assert coverage["coverage_complete"] is True  # registry representation only
    assert coverage["predictive_model_coverage_complete"] is False
    assert coverage["n_hazards_with_registered_model_cards"] == 0
    assert coverage["n_hazards_without_ml"] == 10
    assert coverage["n_hazards_with_any_usable_research_model"] == 0

    cyclone = next(row for row in coverage["entries"] if row["hazard"] == "Cyclone")
    assert cyclone["support_level"] == "not_trained"
    assert cyclone["registered_model_ids"] == []
    assert cyclone["model_ids_missing_cards"] == list(HAZARD_MODEL_MAP["Cyclone"])


def test_usable_secondary_model_is_not_hidden_by_failed_primary_model():
    cyclone_ids = HAZARD_MODEL_MAP["Cyclone"]
    cards = _cards({
        cyclone_ids[0]: "NO_SKILL",
        cyclone_ids[1]: "RESEARCH_SIGNAL_NOT_VALIDATED",
    })
    with patch("src.ml.coverage.list_model_cards", return_value=cards):
        coverage = build_coverage_matrix(write=False)

    cyclone = next(row for row in coverage["entries"] if row["hazard"] == "Cyclone")
    assert cyclone["support_level"] == "screening_model"
    assert cyclone["usable_research_model_ids"] == [cyclone_ids[1]]
    assert "Cyclone" in coverage["hazards_with_any_usable_research_model"]
    assert "Cyclone" in coverage["hazards_with_usable_research_model"]


def test_all_failed_screening_models_are_not_labelled_usable():
    cyclone_ids = HAZARD_MODEL_MAP["Cyclone"]
    cards = _cards({model_id: "NO_SKILL" for model_id in cyclone_ids})
    with patch("src.ml.coverage.list_model_cards", return_value=cards):
        coverage = build_coverage_matrix(write=False)

    cyclone = next(row for row in coverage["entries"] if row["hazard"] == "Cyclone")
    assert cyclone["support_level"] == "no_skill_model"
    assert cyclone["usable_research_model_ids"] == []
    assert "Cyclone" not in coverage["hazards_with_usable_research_model"]



def test_not_trained_cards_do_not_count_as_ml_evidence():
    all_ids = {
        model_id: "NOT_TRAINED"
        for model_ids in HAZARD_MODEL_MAP.values()
        for model_id in model_ids
    }
    with patch("src.ml.coverage.list_model_cards", return_value=_cards(all_ids)):
        coverage = build_coverage_matrix(write=False)

    assert coverage["n_hazards_with_registered_model_cards"] == 7
    assert coverage["n_hazards_with_ml_evidence"] == 0
    assert coverage["n_hazards_without_ml"] == 10
    assert coverage["n_hazards_with_any_usable_research_model"] == 0

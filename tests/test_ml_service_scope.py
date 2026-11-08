"""Geographic scope guards for location-specific disaster research models."""

from src.ml import service
from src.ml.service import _geographic_scope_problem


def _kochi_card():
    return {"provenance": {"location": "kochi"}}


def test_kochi_weather_model_accepts_explicit_kochi_location():
    assert _geographic_scope_problem(
        _kochi_card(),
        {"location": "Kochi Municipal Corporation — area not specified"},
    ) is None


def test_kochi_weather_model_rejects_other_city():
    problem = _geographic_scope_problem(
        _kochi_card(), {"location": "Thiruvananthapuram, Kerala"}
    )

    assert problem is not None
    assert "cannot be applied" in problem


def test_kochi_weather_model_requires_explicit_location():
    problem = _geographic_scope_problem(_kochi_card(), {"rainfall_mm": 100})

    assert problem is not None
    assert "explicit location is required" in problem


def test_non_local_model_without_location_scope_is_not_restricted():
    card = {"provenance": {"source": "IBTrACS North Indian Ocean"}}

    assert _geographic_scope_problem(card, {}) is None



def test_ml_evidence_can_be_restricted_to_selected_registered_model(monkeypatch):
    monkeypatch.setattr(service, "WORKFLOW_HAZARDS", {"Test Hazard"})
    monkeypatch.setattr(
        service,
        "coverage_entry",
        lambda hazard: {
            "model_ids": ["model-a", "model-b"],
            "support_level": "research",
            "interpretation": "research only",
            "limitations": [],
        },
    )
    called = []

    def fake_model_entry(model_id, inputs):
        called.append(model_id)
        return (
            {
                "model_id": model_id,
                "status": "WEAK_RESEARCH_SIGNAL",
                "context": {"missing_features": []},
            },
            None,
        )

    monkeypatch.setattr(service, "_model_entry", fake_model_entry)
    monkeypatch.setattr(service, "load_model_card", lambda model_id: None)

    result = service.ml_evidence_for(
        "Test Hazard",
        {"ml_context": {"feature": 1}},
        selected_model_id="model-b",
    )

    assert called == ["model-b"]
    assert [row["model_id"] for row in result["models"]] == ["model-b"]


def test_ml_evidence_rejects_model_not_registered_for_selected_hazard(monkeypatch):
    monkeypatch.setattr(service, "WORKFLOW_HAZARDS", {"Test Hazard"})
    monkeypatch.setattr(
        service,
        "coverage_entry",
        lambda hazard: {
            "model_ids": ["model-a"],
            "support_level": "research",
            "interpretation": "research only",
            "limitations": [],
        },
    )

    try:
        service.ml_evidence_for(
            "Test Hazard",
            {},
            selected_model_id="model-outside-hazard",
        )
    except ValueError as error:
        assert "not registered for hazard" in str(error)
    else:
        raise AssertionError("An unregistered model must not be applied to a hazard.")

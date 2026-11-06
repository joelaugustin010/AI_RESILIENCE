"""Service boundary between the shared ML engine and hazard assessments.

``ml_evidence_for`` is deliberately fail-closed.  It reports what models exist
and what context is missing rather than inventing a prediction from partial
inputs.  The deterministic hazard assessment remains authoritative; ML output
is supplementary evidence with an explicit scientific boundary.
"""

from __future__ import annotations

from typing import Any

from src.hazard_registry import WORKFLOW_HAZARDS
from src.ml.coverage import coverage_entry
from src.ml.features import FeatureContractError, context_from_inputs
from src.ml.inference import context_gaps, predict_from_context
from src.ml.registry import list_model_cards, load_model_card

USABLE_STATUSES = {"WEAK_RESEARCH_SIGNAL", "RESEARCH_SIGNAL_NOT_VALIDATED"}


def _model_entry(model_id: str, inputs: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    card = load_model_card(model_id)
    if card is None:
        return (
            {
                "model_id": model_id,
                "status": "NOT_TRAINED",
                "evidence_tier": None,
                "intended_use": None,
                "validation_status": None,
                "context": {
                    "required_features": None,
                    "supplied_features": 0,
                    "missing_features": [],
                    "complete": False,
                },
                "note": "No model card or artifact is available in this deployment.",
            },
            None,
        )
    features = [str(name) for name in card.get("feature_columns", [])]
    try:
        context = context_from_inputs(features, inputs)
    except FeatureContractError as exc:
        return (
            {
                "model_id": model_id,
                "status": "invalid_context",
                "evidence_tier": card.get("evidence_tier"),
                "intended_use": card.get("intended_use"),
                "validation_status": card.get("validation_status"),
                "context": {
                    "required_features": len(features),
                    "supplied_features": 0,
                    "missing_features": features,
                    "complete": False,
                },
                "note": str(exc),
            },
            None,
        )
    missing = context_gaps(card, context)
    status = str(card.get("status", "UNKNOWN"))
    entry: dict[str, Any] = {
        "model_id": model_id,
        "status": status,
        "evidence_tier": card.get("evidence_tier"),
        "intended_use": card.get("intended_use"),
        "validation_status": card.get("validation_status"),
        "target_definition": card.get("target_definition"),
        "context": {
            "required_features": len(features),
            "supplied_features": len(context),
            "missing_features": missing,
            "complete": not missing,
        },
        "note": None,
    }
    if missing:
        entry["note"] = (
            "Inference withheld: supply every required context feature explicitly. "
            "Values are never defaulted or imputed from unrelated inputs."
        )
        return entry, None
    if status not in USABLE_STATUSES:
        entry["note"] = (
            "Inference withheld because the model card does not support a usable "
            f"decision output (status {status})."
        )
        return entry, None
    try:
        prediction = predict_from_context(model_id, context)
    except Exception as exc:  # fail closed on any artifact/runtime problem
        entry["status"] = "application_error"
        entry["note"] = f"{type(exc).__name__}: {exc}"
        return entry, None
    return entry, prediction


def ml_evidence_for(hazard: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the shared ML evidence contract for one workflow hazard."""
    if hazard not in WORKFLOW_HAZARDS:
        raise ValueError(f"{hazard!r} is not an authoritative workflow hazard.")
    inputs = inputs or {}
    if not isinstance(inputs, dict):
        raise ValueError("Assessment inputs must be a mapping.")
    coverage = coverage_entry(hazard)
    model_ids = list(coverage.get("model_ids", []))
    if not model_ids:
        return {
            "hazard": hazard,
            "status": "no_model_available",
            "support_level": coverage["support_level"],
            "models": [],
            "applications": [],
            "interpretation": coverage["interpretation"],
            "limitations": coverage["limitations"],
            "validated_prediction_available": False,
            "note": (
                "No shared ML model is released for this hazard. The deterministic "
                "evidence-gated assessment remains in force."
            ),
        }

    models: list[dict[str, Any]] = []
    applications: list[dict[str, Any]] = []
    for model_id in model_ids:
        entry, prediction = _model_entry(model_id, inputs)
        models.append(entry)
        if prediction is not None:
            applications.append(prediction)

    if applications:
        status = "applied"
    elif any(entry["status"] not in {"NOT_TRAINED", "application_error"} for entry in models):
        if any(entry["context"]["missing_features"] for entry in models):
            status = "available_context_incomplete"
        else:
            status = "available_not_applied"
    elif any(entry["status"] == "application_error" for entry in models):
        status = "application_error"
    else:
        status = "not_trained"

    limitations: list[str] = list(coverage.get("limitations", []))
    for entry in models:
        card = load_model_card(entry["model_id"])
        if card:
            limitations.extend(str(item) for item in card.get("limitations", []))
    limitations = list(dict.fromkeys(limitations))

    return {
        "hazard": hazard,
        "status": status,
        "support_level": coverage["support_level"],
        "models": models,
        "applications": applications,
        "interpretation": coverage["interpretation"],
        "limitations": limitations,
        "validated_prediction_available": False,
        "note": (
            "ML evidence is supplementary. The deterministic hazard assessment, "
            "its data gaps and its uncertainty statements remain authoritative. "
            "No model here is independently validated for operational use."
        ),
    }


def ml_registry_summary() -> dict[str, Any]:
    """Return a compact status summary for the model-lab UI."""
    cards = list_model_cards()
    return {
        "n_models": len(cards),
        "models": [
            {
                "model_id": card.get("model_id"),
                "hazard": card.get("hazard"),
                "status": card.get("status"),
                "evidence_tier": card.get("evidence_tier"),
                "selected_model_type": card.get("selected_model_type"),
                "test_events": card.get("test_events"),
                "test_rows": card.get("test_rows"),
                "intended_use": card.get("intended_use"),
                "validation_status": card.get("validation_status"),
            }
            for card in cards
        ],
    }


__all__ = ["USABLE_STATUSES", "ml_evidence_for", "ml_registry_summary"]

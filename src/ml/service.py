"""Service boundary between the shared ML engine and hazard assessments.

``ml_evidence_for`` is deliberately fail-closed.  It reports what models exist
and what context is missing rather than inventing a prediction from partial
inputs.  The deterministic hazard assessment remains authoritative; ML output
is supplementary evidence with an explicit scientific boundary.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.hazard_registry import WORKFLOW_HAZARDS
from src.ml.coverage import coverage_entry
from src.ml.data import (
    build_aftershock_dataset,
    build_compound_cyclone_rainfall_dataset,
    build_cyclone_intensification_dataset,
    build_weather_target_dataset,
)
from src.ml.features import FeatureContractError, context_from_inputs
from src.ml.inference import context_gaps, predict_from_context, predict_regression_from_context
from src.ml.registry import list_model_cards, load_model_card

USABLE_STATUSES = {"WEAK_RESEARCH_SIGNAL", "RESEARCH_SIGNAL_NOT_VALIDATED"}


def _geographic_scope_problem(card: dict[str, Any], inputs: dict[str, Any]) -> str | None:
    """Prevent a location-specific weather model being applied to another place."""
    provenance = card.get("provenance", {})
    if not isinstance(provenance, dict):
        return None
    expected = str(provenance.get("location") or "").strip().casefold()
    if expected != "kochi":
        return None
    supplied = inputs.get("location") or inputs.get("city") or inputs.get("place")
    if not isinstance(supplied, str) or not supplied.strip():
        return (
            "This model is trained for the Kochi reanalysis grid point. "
            "An explicit location is required; no location is inferred."
        )
    normalized = supplied.casefold()
    if "kochi" not in normalized and "cochin" not in normalized:
        return (
            "This model is trained for the Kochi reanalysis grid point and cannot "
            f"be applied to {supplied!r}. Use a separately trained and evaluated "
            "model for another location."
        )
    return None


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
    scope_problem = _geographic_scope_problem(card, inputs)
    if scope_problem:
        return (
            {
                "model_id": model_id,
                "status": "geographic_scope_mismatch",
                "evidence_tier": card.get("evidence_tier"),
                "intended_use": card.get("intended_use"),
                "validation_status": card.get("validation_status"),
                "geographic_scope": card.get("provenance", {}).get("location"),
                "context": {
                    "required_features": len(features),
                    "supplied_features": 0,
                    "missing_features": features,
                    "complete": False,
                },
                "note": scope_problem,
            },
            None,
        )
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
        "geographic_scope": card.get("provenance", {}).get("location") if isinstance(card.get("provenance"), dict) else None,
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
        prediction = (
            predict_regression_from_context(model_id, context)
            if card.get("task_type") == "regression"
            else predict_from_context(model_id, context)
        )
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



def historical_replay_context(model_id: str) -> dict[str, Any]:
    """Build an exact feature row from the model's documented temporal test period.

    This is a retrospective inference demonstration, never a current forecast.
    The selected row comes from the same traceable source builder used for
    research training; the future target is returned separately for comparison
    and is never passed to the model as an input.
    """
    card = load_model_card(model_id)
    if card is None:
        raise ValueError(f"Model {model_id!r} is not registered.")
    dataset_name = str(card.get("dataset_name") or "")
    provenance = card.get("provenance") or {}
    if dataset_name.startswith("weather_"):
        target = str(provenance.get("target") or "")
        location = str(provenance.get("location") or "kochi")
        if target not in {"extreme_rainfall", "high_temperature", "drought_onset"}:
            raise ValueError(f"Unsupported weather target for historical replay: {target!r}.")
        dataset = build_weather_target_dataset(location=location, target=target)
    elif dataset_name == "cyclone_rapid_intensification_24h":
        dataset = build_cyclone_intensification_dataset()
    elif dataset_name == "earthquake_aftershock_occurrence":
        dataset = build_aftershock_dataset()
    elif dataset_name == "compound_cyclone_rainfall_interaction":
        dataset = build_compound_cyclone_rainfall_dataset()
    else:
        raise ValueError(f"No historical replay builder is registered for {dataset_name!r}.")

    split = card.get("temporal_split") or {}
    cutoff = split.get("test_start") or split.get("test_target_dates_from")
    if not cutoff:
        raise ValueError("The model card does not document a temporal test-period start.")
    features = [str(name) for name in card.get("feature_columns", [])]
    target_column = str(card.get("target_column") or dataset.target_column)
    date_column = str(dataset.date_column)
    required = [date_column, target_column, *features]
    missing = [name for name in required if name not in dataset.frame.columns]
    if missing:
        raise ValueError(f"Historical dataset is missing model-contract columns: {missing}")

    frame = dataset.frame.copy()
    # Normalize naive and timezone-aware source timestamps to UTC-naive before
    # applying the card cutoff, so earthquake and weather datasets compare safely.
    frame[date_column] = pd.to_datetime(
        frame[date_column], errors="coerce", utc=True
    ).dt.tz_convert(None)
    cutoff_timestamp = pd.to_datetime(cutoff, utc=True).tz_convert(None)
    frame = frame.loc[frame[date_column] >= cutoff_timestamp]
    frame = frame.dropna(subset=required)
    # Select a held-out row inside every recorded feature domain so the same
    # out-of-training-range gate used by inference will not reject the replay.
    for name in features:
        bounds = (card.get("feature_ranges") or {}).get(name, {})
        if isinstance(bounds, dict) and bounds.get("min") is not None and bounds.get("max") is not None:
            values = pd.to_numeric(frame[name], errors="coerce")
            frame = frame.loc[
                values.between(float(bounds["min"]), float(bounds["max"]), inclusive="both")
            ]
    if frame.empty:
        raise ValueError(
            "No complete historical test-period row is available inside the recorded feature domains."
        )
    row = frame.sort_values(date_column).iloc[-1]
    context: dict[str, float] = {}
    for name in features:
        value = float(row[name])
        if not np.isfinite(value):
            raise ValueError(f"Historical feature {name!r} is not finite.")
        context[name] = value
    observed_target = float(row[target_column])
    if not np.isfinite(observed_target):
        raise ValueError("Historical target is not finite.")
    return {
        "model_id": model_id,
        "context": context,
        "case_date": row[date_column].date().isoformat(),
        "target_column": target_column,
        "observed_target": observed_target,
        "target_definition": card.get("target_definition"),
        "source": provenance.get("source") or dataset.provenance.get("source"),
        "source_type": provenance.get("source_type") or dataset.provenance.get("source_type"),
        "location": provenance.get("location"),
        "case_role": "latest complete in-domain row in the documented temporal test holdout",
        "warning": (
            "Retrospective historical replay only. The observed target is shown "
            "separately and is never supplied to the model."
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


__all__ = ["USABLE_STATUSES", "historical_replay_context", "ml_evidence_for", "ml_registry_summary"]

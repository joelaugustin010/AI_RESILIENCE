"""Hazard-specific, evidence-gated scientific assessment models."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.disaster_models import (
    compound_cyclone_flood,
    compound_rainfall_drainage,
    cyclone,
    drought,
    earthquake,
    flood,
    heatwave,
    industrial_incident,
    infrastructure_failure,
    landslide,
)
from src.hazard_registry import MODEL_DISPATCH_KEYS, WORKFLOW_HAZARDS

_MODEL_FUNCTIONS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "Flood": flood.assess,
    "Cyclone": cyclone.assess,
    "Earthquake": earthquake.assess,
    "Landslide": landslide.assess,
    "Heatwave": heatwave.assess,
    "Drought": drought.assess,
    "Industrial incident": industrial_incident.assess,
    "Infrastructure failure": infrastructure_failure.assess,
    "Compound: cyclone + flood": compound_cyclone_flood.assess,
    "Compound: heavy rainfall + drainage failure": compound_rainfall_drainage.assess,
}

# Build the dispatch table from the registry so a new workflow hazard cannot be
# added without an explicit model, and a model cannot silently target a label
# the workflow does not offer.
MODEL_DISPATCH: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    hazard: _MODEL_FUNCTIONS[MODEL_DISPATCH_KEYS[hazard]]
    for hazard in WORKFLOW_HAZARDS
}


def assess_disaster(inputs: dict[str, Any]) -> dict[str, Any]:
    """Run the exact selected model; never substitute a generic or default hazard.

    Shared ML evidence is attached as a supplementary block.  A failure to load
    the ML engine or its artifacts must not change or block the deterministic
    hazard assessment, and it must never be presented as a prediction.
    """
    if not isinstance(inputs, dict):
        raise ValueError("Assessment inputs must be a mapping.")
    hazard = inputs.get("hazard")
    model = MODEL_DISPATCH.get(hazard)
    if model is None:
        raise ValueError(f"No disaster model is registered for {hazard!r}.")
    assessment = model(inputs)
    try:
        from src.ml.service import ml_evidence_for

        assessment["ml_evidence"] = ml_evidence_for(hazard, inputs)
    except Exception as exc:  # keep the deterministic assessment available
        assessment["ml_evidence"] = {
            "hazard": hazard,
            "status": "ml_engine_unavailable",
            "support_level": "unknown",
            "models": [],
            "applications": [],
            "interpretation": (
                "The shared ML evidence block could not be loaded. This does not "
                "change the deterministic hazard assessment."
            ),
            "limitations": [f"{type(exc).__name__}: {exc}"],
            "validated_prediction_available": False,
            "note": (
                "ML evidence is optional and supplementary. Its absence is not "
                "evidence that a hazard or exposure is absent."
            ),
        }
    return assessment


def disaster_model_mapping() -> list[dict[str, str]]:
    """Return exact workflow-option to model mappings for UI and documentation."""
    names = {
        "Flood": "Rainfall descriptor and optional Rational Method runoff",
        "Cyclone": "Wind-speed/dynamic-pressure physical indicator",
        "Earthquake": "Reported Modified Mercalli Intensity review",
        "Landslide": "Rainfall intensity-duration context; no uncalibrated threshold",
        "Heatwave": "NOAA/NWS Rothfusz heat-index regression",
        "Drought": "Station-level SPI-1 with a 30-year monthly gamma reference",
        "Industrial incident": "Pollutant-specific matched concentration/reference comparison",
        "Infrastructure failure": "Qualitative FMEA and dependency review",
        "Compound: cyclone + flood": "Separate component indicators; unresolved compound dependency",
        "Compound: heavy rainfall + drainage failure": "Rational Method flow/capacity scenario comparison",
    }
    return [
        {"workflow_option": hazard, "model_id": MODEL_DISPATCH[hazard].__module__, "method": names[hazard]}
        for hazard in MODEL_DISPATCH
    ]

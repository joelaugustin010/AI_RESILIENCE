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
    """Run the exact selected model; never substitute a generic or default hazard."""
    if not isinstance(inputs, dict):
        raise ValueError("Assessment inputs must be a mapping.")
    hazard = inputs.get("hazard")
    model = MODEL_DISPATCH.get(hazard)
    if model is None:
        raise ValueError(f"No disaster model is registered for {hazard!r}.")
    return model(inputs)


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

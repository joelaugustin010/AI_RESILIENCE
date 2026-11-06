"""Coverage of the exact ten Decision Workflow hazards by shared ML evidence.

Coverage is not a promise that every hazard has a predictive model.  It records
which hazards have a screening model, which receive forcing evidence only, and
which remain without a defensible supervised model because the labels or the
representative non-event sample are missing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.hazard_registry import HAZARD_REGISTRY, WORKFLOW_HAZARDS
from src.ml.paths import COVERAGE_PATH
from src.ml.persistence import write_json
from src.ml.registry import list_model_cards

HAZARD_MODEL_MAP: dict[str, tuple[str, ...]] = {
    "Flood": ("weather_extreme_rainfall_kochi_nextday",),
    "Cyclone": ("cyclone_rapid_intensification_24h",),
    "Earthquake": ("earthquake_aftershock_occurrence",),
    "Landslide": (),
    "Heatwave": ("weather_high_temperature_kochi_nextday",),
    "Drought": ("weather_drought_onset_kochi_30day",),
    "Industrial incident": (),
    "Infrastructure failure": (),
    "Compound: cyclone + flood": (
        "compound_cyclone_rainfall_interaction",
        "weather_extreme_rainfall_kochi_nextday",
        "cyclone_rapid_intensification_24h",
    ),
    "Compound: heavy rainfall + drainage failure": (
        "weather_extreme_rainfall_kochi_nextday",
    ),
}

SUPPORT_LEVEL: dict[str, str] = {
    "Flood": "forcing_evidence_only",
    "Cyclone": "screening_model",
    "Earthquake": "screening_model",
    "Landslide": "no_defensible_model",
    "Heatwave": "screening_model",
    "Drought": "screening_model",
    "Industrial incident": "no_defensible_model",
    "Infrastructure failure": "no_defensible_model",
    "Compound: cyclone + flood": "exploratory_association",
    "Compound: heavy rainfall + drainage failure": "forcing_evidence_only",
}

INTERPRETATION: dict[str, str] = {
    "Flood": (
        "Shared ML contributes extreme-rainfall screening as forcing evidence only. "
        "It is not a flood-occurrence, inundation, depth, or impact prediction."
    ),
    "Cyclone": (
        "Shared ML screens 24-hour rapid intensification from best-track history. "
        "It does not predict track, landfall, surge, or local wind."
    ),
    "Earthquake": (
        "The previous aftershock model is invalidated because its seven-day outcome windows could cross temporal split boundaries. "
        "It does not predict mainshocks; no usable output is available until embargo retraining."
    ),
    "Landslide": (
        "No defensible supervised landslide model is released: the inventory is a "
        "reported-event catalogue without a representative non-event sample."
    ),
    "Heatwave": (
        "Shared ML screens next-day high temperature at the Kochi reanalysis grid "
        "point. It is not an official heatwave declaration or warning."
    ),
    "Drought": (
        "The previous 30-day rainfall-deficit model was invalidated after a target-window construction defect. "
        "No usable drought ML output is available until corrected future-only training and validation."
    ),
    "Industrial incident": (
        "No defensible supervised model is released: facility-level release labels, "
        "controls, and representative non-events are unavailable."
    ),
    "Infrastructure failure": (
        "No defensible supervised model is released: asset condition, network state, "
        "and outage/recovery labels are unavailable."
    ),
    "Compound: cyclone + flood": (
        "Shared ML provides an exploratory concurrent cyclone-proximity/rainfall "
        "association. It is not a joint probability, lead-time forecast, or compound "
        "impact estimate."
    ),
    "Compound: heavy rainfall + drainage failure": (
        "Shared ML contributes rainfall screening as forcing evidence only. The "
        "deterministic Rational Method flow/capacity comparison remains the decision "
        "calculation."
    ),
}

LIMITATIONS: dict[str, list[str]] = {
    "Flood": [
        "Rainfall is not a flood observation; drainage, river level, and inundation outcomes are absent.",
        "The weather model is trained at one reanalysis grid point and does not transfer automatically.",
    ],
    "Cyclone": [
        "IBTrACS is a post-event best-track reanalysis, not an operational forecast.",
        "Rapid intensification is rare; held-out event counts are small.",
    ],
    "Earthquake": [
        "The prior temporal split did not embargo the full seven-day future label window; previous metrics are invalidated pending retraining.",
        "The USGS catalogue is regionally clipped and capped at 20,000 events.",
        "Aftershock screening does not predict mainshock occurrence or ground shaking.",
    ],
    "Landslide": [
        "Reported-event catalogues are biased toward populated areas and accessible roads.",
        "No background/non-event sample exists in the repository.",
    ],
    "Heatwave": [
        "Reanalysis grid-point temperature is not a station observation or an official heatwave index.",
        "Humidity, night-time temperature, and local exposure are not modelled.",
    ],
    "Drought": [
        "The previous target builder overlapped most of the supposed future rainfall window with historical features; prior model metrics are invalidated.",
        "A 30-day rainfall deficit is a meteorological indicator, not agricultural or hydrological drought.",
        "Soil moisture, evaporative demand, storage, and demand are absent.",
    ],
    "Industrial incident": [
        "No quality-controlled release inventory or facility control data are available.",
        "Permits do not establish current emissions or causal source contribution.",
    ],
    "Infrastructure failure": [
        "No verified asset condition, dependency, outage, or restoration dataset is joined.",
        "Mapped roads and facility directories are not an exposure or vulnerability model.",
    ],
    "Compound: cyclone + flood": [
        "Cyclone proximity and rainfall are concurrent; the association model has no lead time.",
        "Only 128 cyclone-near days and about 20 compound extreme-rain days are available.",
        "Separate component indicators are not added into a joint probability.",
    ],
    "Compound: heavy rainfall + drainage failure": [
        "Drainage capacity and failure state are user-supplied assumptions, not observed.",
        "The Rational Method comparison is a scenario calculation, not a validated flood forecast.",
    ],
}


def _card_status(cards_by_id: dict[str, dict[str, Any]], model_id: str) -> str:
    card = cards_by_id.get(model_id)
    return str(card.get("status", "NOT_TRAINED")) if card else "NOT_TRAINED"


def build_coverage_matrix(*, write: bool = True) -> dict[str, Any]:
    """Build and optionally persist coverage for all ten workflow hazards."""
    cards_by_id = {
        str(card.get("model_id")): card for card in list_model_cards() if card.get("model_id")
    }
    entries: list[dict[str, Any]] = []
    for hazard in WORKFLOW_HAZARDS:
        definition = HAZARD_REGISTRY[hazard]
        model_ids = list(HAZARD_MODEL_MAP[hazard])
        support = SUPPORT_LEVEL[hazard]
        statuses = {model_id: _card_status(cards_by_id, model_id) for model_id in model_ids}
        if any(status == "NO_SKILL" for status in statuses.values()):
            support = "no_skill_model"
        elif any(status == "INSUFFICIENT_TEST_EVENTS" for status in statuses.values()):
            support = "insufficient_validation"
        entries.append(
            {
                "hazard": hazard,
                "kind": definition.kind,
                "components": list(definition.components),
                "support_level": support,
                "model_ids": model_ids,
                "model_statuses": statuses,
                "evidence_role": (
                    "supplementary"
                    if support in {"screening_model", "forcing_evidence_only", "exploratory_association"}
                    else "none"
                ),
                "interpretation": INTERPRETATION[hazard],
                "limitations": LIMITATIONS[hazard],
                "deterministic_model_retained": True,
            }
        )
    hazards_with_ml = [entry["hazard"] for entry in entries if entry["model_ids"]]
    hazards_without_ml = [entry["hazard"] for entry in entries if not entry["model_ids"]]
    usable_statuses = {"WEAK_RESEARCH_SIGNAL", "RESEARCH_SIGNAL_NOT_VALIDATED"}
    hazards_with_component_research_evidence = [
        entry["hazard"] for entry in entries
        if any(status in usable_statuses for status in entry["model_statuses"].values())
    ]
    hazards_with_usable_research_model = [
        entry["hazard"] for entry in entries
        if entry["support_level"] == "screening_model"
        and bool(entry["model_ids"])
        and entry["model_statuses"].get(entry["model_ids"][0]) in usable_statuses
    ]
    hazards_without_usable_research_model = [
        entry["hazard"] for entry in entries
        if entry["hazard"] not in hazards_with_usable_research_model
    ]
    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "workflow_hazards": list(WORKFLOW_HAZARDS),
        "n_hazards": len(entries),
        "n_hazards_with_ml_evidence": len(hazards_with_ml),
        "n_hazards_without_ml": len(hazards_without_ml),
        "n_hazards_with_usable_research_model": len(hazards_with_usable_research_model),
        "hazards_with_usable_research_model": hazards_with_usable_research_model,
        "n_hazards_with_component_research_evidence": len(hazards_with_component_research_evidence),
        "hazards_with_component_research_evidence": hazards_with_component_research_evidence,
        "hazards_without_usable_research_model": hazards_without_usable_research_model,
        "hazards_with_ml_evidence": hazards_with_ml,
        "hazards_without_ml_evidence": hazards_without_ml,
        "coverage_complete": set(entry["hazard"] for entry in entries) == set(WORKFLOW_HAZARDS),
        "validated_models": 0,
        "interpretation": (
            f"Every workflow hazard is represented. {len(hazards_with_ml)} hazards have a registered ML artifact, "
            f"{len(hazards_with_usable_research_model)} have a usable hazard-specific research model, "
            f"{len(hazards_with_component_research_evidence)} have usable component research evidence, "
            f"and {len(hazards_without_ml)} have no registered ML artifact. "
            "Zero models are independently validated for operational use. Coverage is not predictive validity."
        ),
        "entries": entries,
    }
    if write:
        write_json(COVERAGE_PATH, payload)
    return payload


def coverage_entry(hazard: str) -> dict[str, Any]:
    for entry in build_coverage_matrix(write=False)["entries"]:
        if entry["hazard"] == hazard:
            return entry
    raise KeyError(f"Hazard {hazard!r} is not in the authoritative workflow registry.")


__all__ = [
    "HAZARD_MODEL_MAP",
    "LIMITATIONS",
    "SUPPORT_LEVEL",
    "build_coverage_matrix",
    "coverage_entry",
]

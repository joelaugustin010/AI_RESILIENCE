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
    "Flood": ("weather_extreme_rainfall_kochi_nextday", "weather_precipitation_kochi_nextday_regression"),
    "Cyclone": ("cyclone_rapid_intensification_24h", "cyclone_wind_change_24h_regression"),
    "Earthquake": ("earthquake_aftershock_occurrence",),
    "Landslide": (),
    "Heatwave": ("weather_high_temperature_kochi_nextday", "weather_tmax_kochi_nextday_regression"),
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
        "Shared ML contributes next-day rainfall screening and a continuous precipitation estimate as forcing evidence only. "
        "Neither is a flood-occurrence, inundation, depth, or impact prediction."
    ),
    "Cyclone": (
        "Shared ML screens 24-hour rapid intensification and estimates continuous wind change from storm-grouped best-track research. "
        "It does not predict track, landfall, surge, or local wind at a specific place."
    ),
    "Earthquake": (
        "The aftershock model uses a seven-day future-label-window embargo at temporal split boundaries. "
        "Any reported score is research-only on a single temporal holdout, not independent validation. "
        "It screens aftershock occurrence only after an observed mainshock; it does not predict mainshocks or ground shaking."
    ),
    "Landslide": (
        "No defensible supervised landslide model is released: the inventory is a "
        "reported-event catalogue without a representative non-event sample."
    ),
    "Heatwave": (
        "Shared ML screens high-temperature events and estimates next-day maximum temperature at the Kochi reanalysis grid point. "
        "Neither is an official heatwave declaration, health-impact estimate, or warning."
    ),
    "Drought": (
        "The retrained model uses a future-only 30-observation rainfall-deficit target. "
        "Its single temporal holdout is research evidence only, not independent validation or a drought declaration. "
        "It represents meteorological rainfall deficit, not agricultural or hydrological drought."
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
        "The corrected split purges labels whose seven-day outcome windows cross train/validation/test boundaries; results still have only one temporal holdout.",
        "The USGS catalogue is regionally clipped and capped at 20,000 events.",
        "Aftershock screening applies only after an observed mainshock and does not predict mainshock occurrence or ground shaking.",
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
        "The corrected target sums the next 30 observations only; it is a meteorological rainfall-deficit proxy, not a validated drought-impact target.",
        "A 30-day rainfall deficit is not agricultural or hydrological drought.",
        "Soil moisture, evaporative demand, storage, and water demand are absent.",
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
        registered_ids = [
            model_id for model_id in model_ids
            if model_id in cards_by_id
        ]
        trained_ids = [
            model_id for model_id in registered_ids
            if statuses[model_id] != "NOT_TRAINED"
        ]
        usable_ids = [
            model_id for model_id in trained_ids
            if statuses[model_id] in {"WEAK_RESEARCH_SIGNAL", "RESEARCH_SIGNAL_NOT_VALIDATED"}
        ]
        trained_statuses = [statuses[model_id] for model_id in trained_ids]

        # A hazard can have more than one model task (for example, a binary
        # cyclone screening model and a continuous wind-change model).  Never
        # let a failed primary model hide a usable secondary task.
        if support == "screening_model":
            if usable_ids:
                support = "screening_model"
            elif not trained_ids:
                support = "not_trained"
            elif all(status == "NO_SKILL" for status in trained_statuses):
                support = "no_skill_model"
            elif all(status == "INSUFFICIENT_TEST_EVENTS" for status in trained_statuses):
                support = "insufficient_validation"
            else:
                support = "model_evidence_unavailable"
        elif support == "forcing_evidence_only":
            if usable_ids:
                support = "forcing_evidence_only"
            elif not trained_ids:
                support = "forcing_model_not_trained"
            elif all(status == "NO_SKILL" for status in trained_statuses):
                support = "no_skill_forcing_model"
            else:
                support = "forcing_model_evidence_unavailable"
        elif support == "exploratory_association":
            if not any(status == "EXPLORATORY_ASSOCIATION" for status in trained_statuses):
                support = "exploratory_model_unavailable"
        entries.append(
            {
                "hazard": hazard,
                "kind": definition.kind,
                "components": list(definition.components),
                "support_level": support,
                "model_ids": model_ids,
                "registered_model_ids": registered_ids,
                "trained_model_ids": trained_ids,
                "usable_research_model_ids": usable_ids,
                "model_ids_missing_cards": [model_id for model_id in model_ids if model_id not in cards_by_id],
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
    hazards_with_ml = [
        entry["hazard"] for entry in entries if entry["trained_model_ids"]
    ]
    hazards_with_usable_models = [
        entry["hazard"] for entry in entries if entry["usable_research_model_ids"]
    ]
    hazards_without_ml = [entry["hazard"] for entry in entries if not entry["trained_model_ids"]]
    usable_statuses = {"WEAK_RESEARCH_SIGNAL", "RESEARCH_SIGNAL_NOT_VALIDATED"}
    hazards_with_component_research_evidence = [
        entry["hazard"] for entry in entries
        if any(status in usable_statuses for status in entry["model_statuses"].values())
    ]
    hazards_with_usable_research_model = [
        entry["hazard"] for entry in entries
        if entry["support_level"] == "screening_model"
        and bool(entry["usable_research_model_ids"])
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
        "n_hazards_with_registered_model_cards": sum(bool(entry["registered_model_ids"]) for entry in entries),
        "hazards_with_registered_model_cards": [
            entry["hazard"] for entry in entries if entry["registered_model_ids"]
        ],
        "n_hazards_with_any_usable_research_model": len(hazards_with_usable_models),
        "hazards_with_any_usable_research_model": hazards_with_usable_models,
        "workflow_registry_complete": set(entry["hazard"] for entry in entries) == set(WORKFLOW_HAZARDS),
        "predictive_model_coverage_complete": set(hazards_with_usable_research_model) == set(WORKFLOW_HAZARDS),
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
            f"Every workflow hazard is represented. {len(hazards_with_ml)} hazards have at least one trained model card, "
            f"{len(hazards_with_usable_research_model)} have a usable hazard-specific research model, "
            f"{len(hazards_with_component_research_evidence)} have usable component research evidence, "
            f"{len(hazards_with_usable_models)} have at least one usable research model, "
            f"and {len(hazards_without_ml)} have no trained model evidence. "
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

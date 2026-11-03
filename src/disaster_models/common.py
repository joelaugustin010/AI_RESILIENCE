"""Shared validation and report contract for transparent disaster assessments."""

from __future__ import annotations

import math
from typing import Any


INPUT_CLASSIFICATIONS = {
    "Hypothetical scenario assumption",
    "Historical event (source not independently verified)",
    "User-reported observation (source not independently verified)",
    "Forecast supplied by user (not checked by app)",
    "Unknown / unverified",
}

RAINFALL_PERIOD_HOURS = {
    "Last 1 hour": 1.0,
    "Last 24 hours": 24.0,
    "Last 3 days": 72.0,
}

DATASET_RELEVANCE = {
    "Flood": [
        ("IMD 0.25-degree daily grids", "data/raw/experimental/imd_daily_gridded_rainfall_{2018,2021,2024}_025deg.nc", "Context only: fixed nearest-cell grid is not linked to the entered area or a local flood threshold."),
        ("NWDP CWC telemetry rainfall", "data/raw/experimental/nwdp_cwc_rainfall_2021_2025.csv", "Excluded from calculations: 324 conflicting station-time groups and no verified scenario-location/time match."),
        ("JRC GloFAS RP100 tiles", "data/raw/jrc_glofas_rp100_*_depth.tif", "Modeled scenario context; no verified site join or observed flood outcome."),
        ("INDOFLOODS event-severity baseline", "reports/flood_event_severity_baseline.json", "Historical exploratory benchmark only; not a current flood forecast, validated local severity estimate, or compound-event model."),
    ],
    "Cyclone": [
        ("NASA POWER daily meteorology", "data/raw/experimental/nasa_power_kochi_center_daily_20200101_20250101.json", "Context only: fixed point/daily model-derived values do not establish event wind, track, or surge."),
        ("NOAA IBTrACS", "Not acquired", "No storm-track dataset was joined; regional/time-matched event data are still needed."),
    ],
    "Earthquake": [
        ("USGS FDSN regional query", "data/raw/experimental/usgs_earthquakes_kerala_bbox_1900_present_m0.geojson", "Query returned zero events; not a complete seismicity or site-hazard layer."),
        ("GSI/NCS site and building evidence", "Unavailable", "No verified site shaking, soil, structural inventory, or vulnerability data."),
    ],
    "Landslide": [
        ("IMD daily rainfall grids", "data/raw/experimental/imd_daily_gridded_rainfall_{2018,2021,2024}_025deg.nc", "Non-contiguous annual nearest-cell context; insufficient for a local intensity-duration threshold."),
        ("NWDP rainfall observations", "data/raw/experimental/nwdp_*.csv", "Station/time metadata and scenario matching are unresolved; conflicts remain."),
    ],
    "Heatwave": [
        ("NASA POWER daily meteorology", "data/raw/experimental/nasa_power_kochi_center_daily_20200101_20250101.json", "Not joined: fixed-point daily product does not provide verified co-located temperature and humidity for the assessed event."),
        ("KSPCB air-quality reports", "data/raw/air_quality_reports/", "Not a heat-exposure or humidity dataset."),
    ],
    "Drought": [
        ("NWDP manual rainfall", "data/raw/experimental/nwdp_manual_rainfall_1991_2020.csv", "Observed records span 2000-2014 and do not provide a complete 30-year same-station monthly climatology."),
        ("IMD daily rainfall grids", "data/raw/experimental/imd_daily_gridded_rainfall_{2018,2021,2024}_025deg.nc", "Three non-contiguous years are insufficient for SPI climatology."),
    ],
    "Industrial incident": [
        ("KSPCB AQI summaries and reports", "data/raw/air_quality/", "Existing reports do not provide a source-attributed, quality-controlled pollutant series for this scenario."),
        ("Industrial consent/permit records", "data/raw/industrial/", "Permits do not establish current emissions, release, or causal source contribution."),
    ],
    "Infrastructure failure": [
        ("OpenStreetMap road snapshot", "data/raw/experimental/openstreetmap_roads_provisional_kochi_bounds.json", "Mapped roads only; not joined to verified condition, facilities, utilities, or a hazard footprint."),
        ("NIHFW hospital directory and provisional boundaries", "data/raw/nihfw_national_hospital_directory.csv; data/reference/kochi_corporation_boundary.geojson", "Coordinates/boundary are not validated for exposure or dependency analysis."),
    ],
    "Compound: cyclone + flood": [
        ("IMD/NWDP rainfall, river, NASA POWER and JRC flood scenario", "Multiple sources listed above", "No common event-time, spatially matched cyclone/coastal/flood/service outcome dataset; interaction unresolved."),
    ],
    "Compound: heavy rainfall + drainage failure": [
        ("IMD/NWDP rainfall", "data/raw/experimental/imd_daily_gridded_rainfall_*.nc; data/raw/experimental/nwdp_*.csv", "Not automatically joined: grid point and station records are not verified for user-selected catchment/time."),
        ("KSDMA flood archive and drainage inventory", "data/raw/ksdma_flood_return_probability_historical_10_25_50.zip; drainage inventory unavailable", "Raster semantics and drainage network/capacity are unresolved; only user-entered scenario inputs can drive the simplified flow comparison."),
    ],
}


def numeric_input(
    inputs: dict[str, Any],
    field: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    value = inputs.get(field)
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite number.")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{field} must be a finite number.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be a finite number.")
    if minimum is not None and number < minimum:
        raise ValueError(f"{field} must be at least {minimum}.")
    if maximum is not None and number > maximum:
        raise ValueError(f"{field} must be at most {maximum}.")
    return number


def rainfall_intensity(inputs: dict[str, Any]) -> dict[str, Any]:
    depth = numeric_input(inputs, "rainfall_mm", minimum=0, maximum=5000)
    period = inputs.get("rainfall_period")
    if depth is None:
        return {
            "status": "unavailable",
            "value": None,
            "unit": "mm/h",
            "reason": "No rainfall depth was supplied.",
        }
    if period not in RAINFALL_PERIOD_HOURS:
        return {
            "status": "unavailable",
            "value": None,
            "unit": "mm/h",
            "reason": "Rainfall duration is not a supported, explicit interval.",
        }
    hours = RAINFALL_PERIOD_HOURS[period]
    return {
        "status": "calculated_from_user_input",
        "value": depth / hours,
        "unit": "mm/h",
        "reason": f"Arithmetic mean over the user-stated {period.lower()} interval; not a peak intensity.",
        "depth_mm": depth,
        "duration_hours": hours,
    }


def recommendation(
    phase: str,
    action: str,
    trigger: str,
    evidence_needed: str,
    *,
    category: str | None = None,
    limitations: str = (
        "General planning guidance, not a location-specific instruction; "
        "follow competent-authority direction."
    ),
) -> dict[str, str]:
    default_category = {
        "before": "preparedness",
        "during": "response",
        "after": "recovery",
    }.get(phase)
    if category is None:
        category = default_category or phase
    return {
        "phase": phase,
        "category": category,
        "action": action,
        "trigger": trigger,
        "relevance": trigger,
        "evidence_or_authority": evidence_needed,
        "scope": "General; not location-specific.",
        "limitations": limitations,
        "priority": "Unranked; follow competent authority guidance.",
    }


def build_assessment(
    *,
    hazard: str,
    model_id: str,
    method: str,
    scientific_basis: str,
    inputs: dict[str, Any],
    result_status: str,
    hazard_assessment: dict[str, Any],
    calculation: dict[str, Any],
    consequence_pathways: list[str],
    recommendations: dict[str, list[dict[str, str]]],
    uncertainty: list[str],
    data_gaps: list[str],
    sources: list[dict[str, str]],
    assumptions: list[str] | None = None,
) -> dict[str, Any]:
    classification = inputs.get("input_classification", "Unknown / unverified")
    if classification == "User-reported observation (source not independently verified)":
        assessment_type = "Observational assessment (user-reported, unverified)"
    elif classification == "Unknown / unverified":
        assessment_type = "Evidence review; no classified observation or scenario"
    else:
        assessment_type = "Scenario assessment (not a prediction)"

    population = inputs.get("affected_population")
    assets = inputs.get("assets", [])
    if not isinstance(assets, (list, tuple)):
        assets = []
    population_statement = (
        {
            "status": "user_supplied_context_not_estimated",
            "value_people": population,
            "interpretation": "User-entered context only; not independently verified, spatially matched, or estimated by this model.",
        }
        if population is not None
        else {
            "status": "unavailable",
            "value_people": None,
            "interpretation": "No validated population layer or spatial hazard overlay is available; exposed population is not estimated.",
        }
    )
    infrastructure_statement = {
        "status": "user_nominated_not_spatially_verified" if assets else "unavailable",
        "nominated_assets": list(assets),
        "interpretation": (
            "Nominated assets/services only; no verified coordinates, condition, exposure, or service loss is inferred."
            if assets
            else "No verified infrastructure inventory is joined to a compatible hazard footprint."
        ),
    }
    consequence_categories = {
        "human": {
            "status": "INSUFFICIENT EVIDENCE",
            "observed_impacts": {"status": "unavailable", "value": None},
            "modelled_estimate": {"status": "not calculated", "value": None},
            "user_supplied_context": population_statement,
            "location_specific": False,
            "validated": False,
            "data_requirements": [
                "Time-matched, verified hazard footprint and population distribution.",
                "Exposure duration/activity and locally relevant vulnerability data.",
                "Independent event-specific impact observations.",
            ],
        },
        "infrastructure": {
            "status": "INSUFFICIENT EVIDENCE",
            "observed_impacts": {"status": "unavailable", "value": None},
            "modelled_estimate": {"status": "not calculated", "value": None},
            "user_supplied_context": infrastructure_statement,
            "location_specific": False,
            "validated": False,
            "data_requirements": [
                "Current, owner-confirmed asset locations, condition and service status.",
                "Compatible hazard footprint and asset-specific vulnerability evidence.",
                "Independent outage, damage and restoration records.",
            ],
        },
        "environmental": {
            "status": "INSUFFICIENT EVIDENCE",
            "observed_impacts": {"status": "unavailable", "value": None},
            "modelled_estimate": {"status": "not calculated", "value": None},
            "user_supplied_context": None,
            "location_specific": False,
            "validated": False,
            "data_requirements": [
                "Hazard-specific, time-matched environmental monitoring and baseline.",
                "Verified source/transport evidence where contamination attribution is relevant.",
                "Independent ecosystem or environmental impact observations.",
            ],
        },
        "economic": {
            "status": "INSUFFICIENT EVIDENCE",
            "observed_impacts": {"status": "unavailable", "value": None},
            "modelled_estimate": {"status": "not calculated", "value": None},
            "user_supplied_context": None,
            "location_specific": False,
            "validated": False,
            "data_requirements": [
                "Verified asset inventory and replacement/repair values.",
                "Observed service interruption, duration and affected activity.",
                "Documented, independently reviewed loss records.",
            ],
        },
    }
    recommendations = {
        phase: list(items)
        for phase, items in recommendations.items()
    }
    recommendations["long_term"] = [
        recommendation(
            "long_term",
            (
                f"Use verified {hazard.lower()} footprints, asset/exposure records, "
                "and independently reviewed outcomes to update long-term standards "
                "and resilience plans before selecting location-specific investments."
            ),
            f"A long-term {hazard.lower()} risk-reduction or capital-planning decision is being considered.",
            "; ".join(
                source["title"]
                for source in sources
                if source.get("title")
            )
            or "Relevant competent authority and independently reviewed local evidence.",
            category="long_term",
            limitations=(
                "General planning advice only. This assessment does not identify "
                "a site, establish an investment need, rank projects, or estimate "
                "risk-reduction benefit."
            ),
        )
    ]
    return {
        "disaster": hazard,
        "model_id": model_id,
        "assessment_type": assessment_type,
        "result_status": result_status,
        "validated_prediction_available": False,
        "input_conditions": {
            key: value
            for key, value in inputs.items()
            if key not in {"monthly_precipitation_csv"}
        },
        "hazard_assessment": hazard_assessment,
        "methodology": {
            "name": method,
            "scientific_basis": scientific_basis,
            "calculation": calculation,
        },
        "potential_consequences": {
            "status": "pathways_only_unquantified",
            "human_population": population_statement,
            "infrastructure": infrastructure_statement,
            "environment_and_economy": "Not quantified; no compatible local consequence data are available.",
            "categories": consequence_categories,
            "cascading_or_compound_pathways": consequence_pathways,
        },
        "recommendations": recommendations,
        "evidence": {
            "sources": sources,
            "dataset_use": (
                "Only the explicitly entered scenario/observation values drive calculations. "
                "These repository datasets are contextual or excluded for the stated reasons."
            ),
            "dataset_relevance": [
                {"dataset": name, "file_or_source": path, "use_status": status}
                for name, path, status in DATASET_RELEVANCE.get(hazard, [])
            ],
        },
        "uncertainty": list(uncertainty),
        "data_gaps": list(data_gaps),
        "assumptions": list(assumptions or []),
        "validation": {
            "historical_validation": "Not performed; no independently matched event outcomes.",
            "software_test_status": "Tests verify implementation behavior only, not scientific validity.",
            "prediction_status": "No calibrated, independently validated prediction is available.",
        },
    }


def record_scenario_consequence(
    assessment: dict[str, Any],
    *,
    category: str,
    value: dict[str, Any],
    interpretation: str,
) -> None:
    """Attach an input-derived scenario indicator without asserting an impact."""
    categories = assessment["potential_consequences"]["categories"]
    if category not in categories:
        raise ValueError(f"Unknown consequence category: {category!r}.")
    consequence = categories[category]
    consequence["status"] = "SCENARIO INDICATOR AVAILABLE — NO IMPACT ESTIMATE"
    consequence["modelled_estimate"] = {
        "status": "SIMULATED SCENARIO — not observed or independently validated",
        "value": value,
        "interpretation": interpretation,
    }
    consequence["location_specific"] = False
    consequence["validated"] = False
    assessment["potential_consequences"]["status"] = (
        "scenario_indicators_only_observed_impacts_unavailable"
    )


def validate_top_level(inputs: dict[str, Any]) -> None:
    if not isinstance(inputs, dict):
        raise ValueError("Assessment inputs must be a mapping.")
    classification = inputs.get("input_classification", "Unknown / unverified")
    if classification not in INPUT_CLASSIFICATIONS:
        raise ValueError("input_classification is not a supported evidence classification.")
    population = numeric_input(inputs, "affected_population", minimum=0, maximum=10_000_000_000)
    if population is not None and not population.is_integer():
        raise ValueError("affected_population must be a whole number of people.")

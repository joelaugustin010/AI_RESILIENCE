"""Alternative evidence methods for hazards with incomplete local labels.

This module makes defensible use of public satellite inventories, supplied
background samples and administrative records without converting them into
false observations. It does not download data or invent labels.
"""
from __future__ import annotations

from typing import Any, Mapping
import hashlib
import math

import numpy as np
import pandas as pd
from shapely.geometry import shape as shapely_shape

EARTH_RADIUS_KM = 6371.0088

ALTERNATIVE_EVIDENCE: dict[str, dict[str, Any]] = {
    "flood_satellite": {
        "title": "Satellite-observed flood extent",
        "method": "Reconstruct historical event extent and progression from NRSC flood maps and Sentinel-1 SAR observations.",
        "sources": [
            {"publisher": "NRSC/ISRO", "title": "Flood Affected Area Atlas of India (1998-2022)", "url": "https://ndrf.nrsc.gov.in/documents/downloads/allindia_flood_techdoc.pdf", "access": "public_reference"},
            {"publisher": "Copernicus Data Space", "title": "Sentinel-1 data access", "url": "https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1", "access": "catalogue_and_API; account_or_terms_may_apply"},
        ],
        "supports": ["observed_inundation_footprints", "event_dates", "multi_date_progression_when_acquisitions_exist"],
        "does_not_support": ["flood_depth_without_independent_depth_measurements", "casualties", "future_flood_probability_by_itself"],
        "status": "PUBLIC_SOURCE_IDENTIFIED_DATA_ACQUISITION_AND_LOCAL_COVERAGE_AUDIT_REQUIRED",
    },
    "landslide_inventory": {
        "title": "Regional landslide inventories and cautious pseudo-absence modelling",
        "method": "Use NRSC/ISRO, SILAAS and Kerala event inventories; generate explicitly labelled pseudo-absence samples from eligible background points and use spatial-block validation.",
        "sources": [
            {"publisher": "NRSC/ISRO", "title": "Landslide Atlas of India", "url": "https://www.nrsc.gov.in/nrscnew/resources_atlas_landslide.php", "access": "atlas_public; vector reuse/access must be verified"},
            {"publisher": "KSREC", "title": "SILAAS landslide inventory and monitoring", "url": "https://ksrec.kerala.gov.in/website/website_english/HomeController/silaas", "access": "programme_information_public; data access must be verified"},
            {"publisher": "NRSC Bhuvan", "title": "Landslide inventory and event layers", "url": "https://bhuvan-app1.nrsc.gov.in/disaster/usrtasks/landslide/landslide.php", "access": "portal_public; service terms and layer metadata must be checked"},
        ],
        "supports": ["regional_susceptibility_research", "spatial_holdout_evaluation_if_geometries_are_available"],
        "does_not_support": ["confirmed_true_absence_from_pseudo_absence", "exact_event_timing_without_triggering_observations"],
        "status": "PUBLIC_INVENTORY_CATALOGUES_IDENTIFIED_GEOMETRY_AND_REUSE_CHECK_REQUIRED",
    },
    "industrial_process_risk": {
        "title": "Industrial process-safety and consequence screening",
        "method": "Use regulator safety-reporting context, facility records lawfully supplied, and engineering scenario assessment; keep incident probability separate from consequence scenarios.",
        "sources": [
            {"publisher": "DGFASLI", "title": "Major accident reporting and safety duties", "url": "https://dgfasli.gov.in/en/faq", "access": "public_guidance_not_facility_training_data"},
            {"publisher": "Labour Bureau", "title": "Reports on Statistics of Factories", "url": "https://labourbureau.gov.in/reportsonstatisticsoffactories", "access": "public_aggregate_reports"},
        ],
        "supports": ["aggregate_safety_trend_context", "facility_scenario_screening_when_verified_facility_inputs_exist"],
        "does_not_support": ["facility_specific_incident_probability_from_aggregate_statistics", "source_attribution_from_nearby_AQI"],
        "status": "AGGREGATE_SAFETY_EVIDENCE_AND_ENGINEERING_ALTERNATIVE_AVAILABLE",
    },
    "intervention_effectiveness": {
        "title": "Empirical and simulated intervention evidence",
        "method": "Keep randomized anticipatory-assistance evaluations, observational physical works and hydraulic intervention simulations in separate evidence tracks.",
        "sources": [
            {"publisher": "World Bank Microdata Library", "title": "Bangladesh Forecast Based Anticipatory Action Impact Evaluation 2024", "url": "https://microdata.worldbank.org/catalog/8009", "access": "licensed_microdata_human_approval_required"},
            {"publisher": "World Bank Reproducibility Repository", "title": "Fast Action for Floods reproducibility package", "url": "https://reproducibility.worldbank.org/catalog/374", "access": "code_public_some_microdata_licensed_and_not_included"},
            {"publisher": "Zenodo", "title": "Geul intervention simulation archive", "url": "https://zenodo.org/records/15488420", "access": "simulation_outputs_not_observed_outcomes"},
        ],
        "supports": ["causal_method_reproduction_for_anticipatory_cash_assistance_if_authorized_data_are_obtained", "separate_simulation_surrogate_research_for_engineered_interventions"],
        "does_not_support": ["transfer_of_cash_assistance_effects_to_drainage_or_embankment_works", "treating_simulated_outcomes_as_observed_effectiveness", "Kochi_physical_intervention_effects_without_local_outcomes"],
        "status": "EMPIRICAL_CASH_ASSISTANCE_AND_SIMULATION_ALTERNATIVES_IDENTIFIED_KEEP_SEPARATE",
    },
    "infrastructure_reliability": {
        "title": "Utility reliability indicators",
        "method": "Use KSEB Urjadooth feeder/DTR outage and SAIFI/SAIDI indicators for system-level reliability context; do not infer individual asset failure rates from aggregates.",
        "sources": [
            {"publisher": "KSEB", "title": "Urjadooth operational dashboard", "url": "https://hris.kseb.in/oms/", "access": "public_dashboard_live_snapshot; historical export and definitions require verification"},
            {"publisher": "KSEB", "title": "Reliability KPI dashboard", "url": "https://hris.kseb.in/kpi/index.html", "access": "public_dashboard; aggregation level must be recorded"},
        ],
        "supports": ["system_level_reliability_context", "outage_preparedness_and_dependency_screening"],
        "does_not_support": ["asset_level_failure_probability_without_asset_event_history", "causal_effect_of_maintenance_without_comparison_data"],
        "status": "PUBLIC_AGGREGATE_RELIABILITY_INDICATORS_IDENTIFIED",
    },
    "kochi_intervention_reconstruction": {
        "title": "Kochi intervention evidence reconstruction",
        "method": "Reconstruct intervention timelines from government orders and departmental reports, then link commissioning dates and work footprints to independent satellite/event outcomes.",
        "sources": [
            {"publisher": "KSDMA", "title": "Kochi 2019 flood and Operation Breakthrough", "url": "https://sdma.kerala.gov.in/kochi-2019/", "access": "public_event_and_programme_record"},
            {"publisher": "Kerala Irrigation Department", "title": "Operation Breakthrough Phase I and II report", "url": "https://www.irrigation.kerala.gov.in/sites/default/files/2021-08/kochiflood.pdf", "access": "public_report; completion evidence must be separately checked"},
            {"publisher": "Government of Kerala", "title": "GO(Rt) 474/2024/DMD", "url": "https://document.kerala.gov.in/documents/governmentorders/govtorder1707202414%3A45%3A51.pdf", "access": "public_order; technical sanction is not proof of completion"},
        ],
        "supports": ["documented_project_timeline", "candidate_treated_and_comparison_site_design"],
        "does_not_support": ["causal_effect_without_verified_completion_and_repeated_outcomes", "assuming_technical_sanction_equals_completed_work"],
        "status": "DOCUMENTARY_RECONSTRUCTION_POSSIBLE_CAUSAL_ESTIMATION_STILL_GATED",
    },
}


HAZARD_ALTERNATIVE_TRACKS: dict[str, tuple[str, ...]] = {
    "Flood": ("flood_satellite", "intervention_effectiveness", "kochi_intervention_reconstruction"),
    "Landslide": ("landslide_inventory",),
    "Industrial incident": ("industrial_process_risk",),
    "Infrastructure failure": ("infrastructure_reliability", "intervention_effectiveness"),
    "Compound: cyclone + flood": ("flood_satellite", "intervention_effectiveness", "kochi_intervention_reconstruction"),
    "Compound: heavy rainfall + drainage failure": (
        "flood_satellite", "infrastructure_reliability", "intervention_effectiveness", "kochi_intervention_reconstruction"
    ),
}


def alternative_evidence_for_hazard(hazard: str) -> list[dict[str, Any]]:
    """Return relevant alternative evidence routes for one workflow hazard."""
    return [
        {"track_id": track_id, **ALTERNATIVE_EVIDENCE[track_id]}
        for track_id in HAZARD_ALTERNATIVE_TRACKS.get(str(hazard), ())
    ]


def _coordinates(frame: pd.DataFrame, lat_col: str, lon_col: str) -> tuple[np.ndarray, np.ndarray]:
    if lat_col not in frame or lon_col not in frame:
        raise ValueError(f"Required coordinate columns are missing: {lat_col}, {lon_col}")
    lat = pd.to_numeric(frame[lat_col], errors="coerce").to_numpy(dtype=float)
    lon = pd.to_numeric(frame[lon_col], errors="coerce").to_numpy(dtype=float)
    if len(lat) == 0 or not np.isfinite(lat).all() or not np.isfinite(lon).all():
        raise ValueError("Coordinates must be non-empty and finite.")
    if ((lat < -90) | (lat > 90) | (lon < -180) | (lon > 180)).any():
        raise ValueError("Coordinates are outside valid latitude/longitude bounds.")
    return lat, lon


def _haversine_matrix(lat_a: np.ndarray, lon_a: np.ndarray, lat_b: np.ndarray, lon_b: np.ndarray) -> np.ndarray:
    a_lat = np.radians(lat_a)[:, None]
    b_lat = np.radians(lat_b)[None, :]
    dlat = b_lat - a_lat
    dlon = np.radians(lon_b)[None, :] - np.radians(lon_a)[:, None]
    term = np.sin(dlat / 2) ** 2 + np.cos(a_lat) * np.cos(b_lat) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(term, 0, 1)))


def generate_pseudo_absence_samples(
    positives: pd.DataFrame,
    eligible_background: pd.DataFrame,
    *,
    min_distance_km: float = 1.0,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    sample_size: int | None = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """Select background candidates away from mapped positives.

    The input background must already represent the study's eligible/surveyed
    domain. Returned rows are labelled PSEUDO_ABSENCE, never verified absence.
    No coordinates or negative labels are fabricated.
    """
    if not math.isfinite(float(min_distance_km)) or min_distance_km <= 0:
        raise ValueError("min_distance_km must be a finite positive number.")
    if positives.empty or eligible_background.empty:
        raise ValueError("Positive inventory and eligible background candidates are both required.")
    pos_lat, pos_lon = _coordinates(positives, lat_col, lon_col)
    bg_lat, bg_lon = _coordinates(eligible_background, lat_col, lon_col)
    distances = _haversine_matrix(bg_lat, bg_lon, pos_lat, pos_lon)
    nearest = distances.min(axis=1)
    eligible = np.flatnonzero(nearest >= float(min_distance_km))
    if not len(eligible):
        raise ValueError("No eligible background points remain outside the positive-inventory buffer.")
    requested = len(eligible) if sample_size is None else int(sample_size)
    if requested < 1:
        raise ValueError("sample_size must be at least one.")
    rng = np.random.default_rng(int(random_state))
    chosen = rng.choice(eligible, size=min(requested, len(eligible)), replace=False)
    result = eligible_background.iloc[chosen].copy().reset_index(drop=True)
    result["label"] = 0
    result["label_type"] = "PSEUDO_ABSENCE_NOT_VERIFIED_NEGATIVE"
    result["nearest_mapped_positive_km"] = nearest[chosen]
    result["pseudo_absence_buffer_km"] = float(min_distance_km)
    result["sampling_seed"] = int(random_state)
    return result


def assign_spatial_block_splits(
    frame: pd.DataFrame,
    *,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    block_size_km: float = 10.0,
    random_state: int = 42,
    proportions: tuple[float, float, float] = (0.70, 0.15, 0.15),
) -> pd.DataFrame:
    """Assign whole spatial blocks to train/validation/test without block leakage."""
    if not math.isfinite(float(block_size_km)) or block_size_km <= 0:
        raise ValueError("block_size_km must be a finite positive number.")
    if len(proportions) != 3 or any(not math.isfinite(float(p)) or p <= 0 for p in proportions):
        raise ValueError("Three positive split proportions are required.")
    if not math.isclose(sum(proportions), 1.0, rel_tol=0, abs_tol=1e-8):
        raise ValueError("Split proportions must sum to one.")
    lat, lon = _coordinates(frame, lat_col, lon_col)
    mean_lat = float(np.mean(lat))
    x_km = lon * (111.32 * math.cos(math.radians(mean_lat)))
    y_km = lat * 110.574
    bx = np.floor(x_km / block_size_km).astype(int)
    by = np.floor(y_km / block_size_km).astype(int)
    block_ids = np.array([f"{x}:{y}" for x, y in zip(bx, by)])
    unique = np.unique(block_ids)
    if len(unique) < 3:
        raise ValueError("At least three distinct spatial blocks are required for train/validation/test.")
    rng = np.random.default_rng(int(random_state))
    shuffled = rng.permutation(unique)
    n = len(shuffled)
    n_train = max(1, int(math.floor(n * proportions[0])))
    n_validation = max(1, int(math.floor(n * proportions[1])))
    if n_train + n_validation >= n:
        n_train = n - 2
        n_validation = 1
    assignment = {}
    for block in shuffled[:n_train]:
        assignment[block] = "train"
    for block in shuffled[n_train:n_train + n_validation]:
        assignment[block] = "validation"
    for block in shuffled[n_train + n_validation:]:
        assignment[block] = "test"
    result = frame.copy()
    result["spatial_block_id"] = block_ids
    result["spatial_split"] = [assignment[block] for block in block_ids]
    return result



def audit_intervention_evidence(frame: pd.DataFrame) -> dict[str, Any]:
    """Audit intervention records while separating empirical and simulated domains.

    This is a schema/evidence-classification gate only. It never estimates a
    treatment effect and never transfers an effect between intervention types.
    """
    required = {
        "intervention_domain", "evidence_type", "treatment",
        "assignment_method", "outcome_value", "outcome_unit", "source_url",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        return {
            "schema_version": "intervention-evidence-audit/1.0.0",
            "status": "BLOCKED_SCHEMA",
            "missing_columns": missing,
            "causal_effect_estimated": False,
            "transferability_claimed": False,
        }
    if frame.empty:
        return {
            "schema_version": "intervention-evidence-audit/1.0.0",
            "status": "BLOCKED_EMPTY_DATA",
            "causal_effect_estimated": False,
            "transferability_claimed": False,
        }
    data = frame.copy()
    domains = set(data["intervention_domain"].dropna().astype(str).str.strip())
    evidence = set(data["evidence_type"].dropna().astype(str).str.strip().str.lower())
    problems: list[str] = []
    if len(domains) != 1 or "" in domains:
        problems.append("Do not pool different intervention domains in one evidence table.")
    if len(evidence) != 1 or "" in evidence:
        problems.append("Do not mix observed empirical outcomes and simulation outputs.")
    treatment = pd.to_numeric(data["treatment"], errors="coerce")
    if treatment.isna().any() or not set(treatment.dropna().unique()).issubset({0, 1}):
        problems.append("treatment must contain only binary 0/1 values.")
    elif set(treatment.unique()) != {0, 1}:
        problems.append("Both treated and comparison observations are required.")
    outcomes = pd.to_numeric(data["outcome_value"], errors="coerce")
    if outcomes.isna().any() or not np.isfinite(outcomes.to_numpy(dtype=float)).all():
        problems.append("outcome_value must contain finite numeric observations.")
    if data["outcome_unit"].isna().any() or data["outcome_unit"].astype(str).str.strip().eq("").any():
        problems.append("outcome_unit must be complete.")
    elif data["outcome_unit"].nunique(dropna=True) != 1:
        problems.append("Outcome units differ; standardise or split the evidence table.")
    if not data["source_url"].astype(str).str.match(r"^https://").all():
        problems.append("Every source_url must be an HTTPS provenance link.")
    if data["assignment_method"].isna().any() or data["assignment_method"].astype(str).str.strip().eq("").any():
        problems.append("assignment_method must be documented; use 'not_reported' when unknown.")
    status = "BLOCKED_EVIDENCE_MIX_OR_QUALITY" if problems else "DESIGN_REVIEW_ONLY"
    domain = next(iter(domains)) if len(domains) == 1 else "mixed"
    evidence_type = next(iter(evidence)) if len(evidence) == 1 else "mixed"
    if not problems:
        if evidence_type == "simulated" or domain == "simulation":
            status = "SIMULATION_ONLY_KEEP_SEPARATE_FROM_EMPIRICAL_OUTCOMES"
        elif domain == "cash_assistance":
            status = "EMPIRICAL_CASH_ASSISTANCE_CANDIDATE_NOT_TRANSFERABLE_TO_PHYSICAL_WORKS"
        elif domain == "physical_infrastructure":
            status = "PHYSICAL_INFRASTRUCTURE_DESIGN_REVIEW_ONLY_NOT_CAUSAL_PROOF"
        else:
            status = "UNREGISTERED_INTERVENTION_DOMAIN_REQUIRES_REVIEW"
    return {
        "schema_version": "intervention-evidence-audit/1.0.0",
        "status": status,
        "row_count": int(len(data)),
        "intervention_domain": domain,
        "evidence_type": evidence_type,
        "assignment_methods": sorted(set(data["assignment_method"].astype(str).str.strip())),
        "treated_rows": int(treatment.eq(1).sum()) if not treatment.isna().any() else 0,
        "comparison_rows": int(treatment.eq(0).sum()) if not treatment.isna().any() else 0,
        "outcome_units": sorted(set(data["outcome_unit"].dropna().astype(str))),
        "problems": problems,
        "causal_effect_estimated": False,
        "transferability_claimed": False,
        "interpretation": (
            "Passing this audit only classifies a structurally coherent evidence table. "
            "It does not establish randomization, exchangeability, parallel trends, "
            "no spillovers, a causal effect, or transferability to Kochi."
        ),
    }



def audit_satellite_flood_geojson(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Audit event-labelled satellite flood polygons without inferring depth."""
    if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
        raise ValueError("Expected a GeoJSON FeatureCollection.")
    features = payload["features"]
    if not features:
        raise ValueError("GeoJSON FeatureCollection contains no features.")
    event_ids: set[str] = set()
    dates: set[str] = set()
    sensors: set[str] = set()
    evidence_types: set[str] = set()
    issues: list[str] = []
    accepted = 0
    for index, feature in enumerate(features):
        if not isinstance(feature, Mapping) or feature.get("type") != "Feature":
            issues.append(f"Feature {index} is not a valid GeoJSON Feature.")
            continue
        geometry = feature.get("geometry")
        if not isinstance(geometry, Mapping) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            issues.append(f"Feature {index} must contain Polygon or MultiPolygon geometry.")
            continue
        try:
            spatial = shapely_shape(geometry)
            if spatial.is_empty or not spatial.is_valid or spatial.area <= 0:
                raise ValueError("empty, invalid or zero-area geometry")
            min_lon, min_lat, max_lon, max_lat = spatial.bounds
            if min_lon < -180 or max_lon > 180 or min_lat < -90 or max_lat > 90:
                raise ValueError("coordinates outside longitude/latitude bounds")
        except Exception as exc:
            issues.append(f"Feature {index} has invalid polygon geometry: {exc}")
            continue
        properties = feature.get("properties") or {}
        event_id = str(properties.get("event_id", "")).strip()
        observed_at = str(properties.get("observed_at", "")).strip()
        source_url = str(properties.get("source_url", "")).strip()
        sensor = str(properties.get("sensor", "")).strip()
        evidence_type = str(properties.get("evidence_type", "")).strip().lower()
        if not event_id or not observed_at or not sensor or not source_url.startswith("https://"):
            issues.append(f"Feature {index} requires event_id, observed_at, sensor and an HTTPS source_url.")
            continue
        try:
            date = pd.Timestamp(observed_at)
            if pd.isna(date) or date.tzinfo is None:
                raise ValueError("observed_at must be an ISO timestamp with an explicit timezone")
        except Exception:
            issues.append(f"Feature {index} has an invalid observed_at date.")
            continue
        if evidence_type not in {"observed_satellite", "simulated"}:
            issues.append(f"Feature {index} evidence_type must be observed_satellite or simulated.")
            continue
        event_ids.add(event_id)
        dates.add(date.isoformat())
        sensors.add(sensor)
        evidence_types.add(evidence_type)
        accepted += 1
    if issues:
        status = "BLOCKED_METADATA_OR_GEOMETRY_ISSUES"
    elif evidence_types == {"simulated"}:
        status = "SIMULATION_ONLY_NOT_OBSERVED_FLOOD_EVIDENCE"
    elif evidence_types == {"observed_satellite"}:
        status = "OBSERVED_SATELLITE_EXTENT_ONLY_NOT_DEPTH_OR_FLOOD_FORECAST"
    else:
        status = "BLOCKED_MIXED_OBSERVED_AND_SIMULATED_EVIDENCE"
        issues.append("Observed and simulated polygons must be stored and evaluated separately.")
    return {
        "schema_version": "satellite-flood-evidence-audit/1.0.0",
        "status": status,
        "feature_count": accepted,
        "event_count": len(event_ids),
        "observation_count": len(dates),
        "sensors": sorted(sensors),
        "evidence_types": sorted(evidence_types),
        "issues": issues,
        "depth_available": False,
        "forecast_available": False,
        "causal_effect_estimated": False,
    }


__all__ = [
    "ALTERNATIVE_EVIDENCE",
    "HAZARD_ALTERNATIVE_TRACKS",
    "alternative_evidence_for_hazard",
    "assign_spatial_block_splits",
    "audit_intervention_evidence",
    "audit_satellite_flood_geojson",
    "generate_pseudo_absence_samples",
]

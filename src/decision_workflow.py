"""Pure, transparent helpers for the connected disaster decision workflow."""

from __future__ import annotations

import html
import json
import math
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

from src.evidence_quality import evidence_quality_inventory
from src.hazard_registry import HAZARD_NOTES, WORKFLOW_HAZARDS, components_for
from src.infrastructure_dependencies import dependency_review_table
from src.uncertainty import build_uncertainty_register


HAZARD_OPTIONS = list(WORKFLOW_HAZARDS)

INPUT_CLASSIFICATIONS = {
    "Hypothetical scenario assumption",
    "Historical event (source not independently verified)",
    "User-reported observation (source not independently verified)",
    "Forecast supplied by user (not checked by app)",
    "Unknown / unverified",
}
RAINFALL_PERIOD_OPTIONS = {
    "Not supplied",
    "Last 1 hour",
    "Last 24 hours",
    "Last 3 days",
    "Other / state in notes",
}
ASSET_OPTIONS = (
    "Hospitals",
    "Roads and bridges",
    "Electricity",
    "Drinking water",
    "Communications",
    "Shelters",
    "Schools",
    "Drainage",
    "Industrial facilities",
    "Residential buildings",
)
DRAINAGE_STATUS_OPTIONS = (
    "Not supplied",
    "Reported functioning",
    "Reported partially impaired",
    "Reported failed",
    "Hypothetical partial failure",
    "Not applicable",
)
INFRASTRUCTURE_STATUS_OPTIONS = (
    "Not supplied",
    "No disruption reported",
    "Possible / hypothetical disruption",
    "Disruption reported by user",
    "Not applicable",
)

MITIGATION_CATALOG = {
    "Flood": [
        ("Drainage inspection and maintenance", "Can identify blocked or damaged assets before heavy rain.", "Verified asset register, inspection route, maintenance logs, disposal plan."),
        ("Drainage capacity improvement study", "Can identify locations for engineered capacity changes; no local benefit is quantified.", "Hydraulic survey/model, design review, permits, lifecycle maintenance plan."),
        ("Hospital continuity and flood preparedness", "Can improve continuity planning for essential care during access or utility disruption.", "Verified facility list, site-specific flood review, backup power/water duration."),
        ("Evacuation route and shelter review", "Can identify route and shelter gaps for planning; no routes are verified in this app.", "Authoritative road/shelter layers, accessibility review, local drills."),
    ],
    "Heavy rainfall": [
        ("Rainfall-source and accumulation verification", "Confirms whether rainfall values, units, timing, and station context are suitable for local review.", "Authoritative observation or forecast, station/location, timezone, averaging period, and quality flags."),
    ],
    "Drainage failure": [
        ("Drainage inspection and maintenance", "Can identify blocked or damaged assets before heavy rain.", "Verified asset register, inspection route, maintenance logs, disposal plan."),
        ("Drainage capacity improvement study", "Can identify locations for engineered capacity changes; no local benefit is quantified.", "Hydraulic survey/model, design review, permits, lifecycle maintenance plan."),
    ],
    "Cyclone": [
        ("Emergency communication readiness", "Supports timely coordination if communications are disrupted.", "Operator contacts, backup channels, tested procedures."),
        ("Hospital continuity and cyclone preparedness", "Supports continuity of essential care during wind or utility disruption.", "Verified facilities, structural review, backup-duration records."),
        ("Evacuation and shelter readiness", "Supports preparedness where official warnings and local plans call for action.", "Official routes/shelters, accessibility and capacity review, drills."),
    ],
    "Earthquake": [
        ("Critical-building structural inspection", "Documents condition and retrofit needs; this app does not assess structural safety.", "Qualified engineering inspection and building inventory."),
        ("Utility isolation and emergency drills", "Supports safer response and continuity after a damaging event.", "Facility plans, responsible operators, tested drill records."),
    ],
    "Landslide": [
        ("Slope and drainage inspection", "Supports site monitoring and maintenance where a local assessment identifies concern.", "Verified slope/hazard map, field inspection, geotechnical review."),
        ("Safe-route and response planning", "Supports response planning around access disruption.", "Verified routes, local authority review, accessible alternatives."),
    ],
    "Heatwave": [
        ("Heat-health preparedness", "Supports early outreach, cooling access, and continuity of care.", "Local heat-health plan, population and facility data, service capacity."),
        ("Water and power continuity review", "Supports continuity of essential cooling and water services.", "Utility dependency inventory and backup-duration checks."),
    ],
    "Drought": [
        ("Water-source and demand contingency planning", "Supports staged response to supply constraints.", "Reservoir/source data, demand records, official trigger/action plan."),
        ("Essential-service water continuity", "Supports continued operation of health and emergency services.", "Facility inventory, storage and replenishment records."),
    ],
    "Industrial incident": [
        ("Pollutant-specific monitoring and source investigation", "Can improve evidence for investigation; AQI alone cannot identify a source.", "Verified station data, pollutant-specific observations, facility emissions and meteorology."),
        ("Industrial incident response coordination", "Supports coordinated notification, isolation, and response.", "Facility-specific emergency plans, official contacts, drills."),
    ],
    "Infrastructure failure": [
        ("Critical-infrastructure dependency review", "Can identify service dependencies and continuity gaps.", "Verified asset/utility inventory, operators, backup duration and failure logs."),
        ("Infrastructure inspection and resilience study", "Can prioritize engineering review; no benefit is quantified here.", "Condition survey, engineering scope, design review and lifecycle costs."),
        ("Emergency communications readiness", "Supports coordination through service disruptions.", "Tested backup channels and responsible operators."),
    ],
}


def expand_hazards(selection: str) -> list[str]:
    """Expand compound labels into distinct drivers without scoring or combining them.

    The mapping lives in :mod:`src.hazard_registry`; this helper exists only so
    callers do not need to know the registry layout.
    """
    return components_for(selection)


def validate_workflow_inputs(inputs: dict[str, Any]) -> list[str]:
    """Return clear validation messages for user-entered scenario values."""
    problems: list[str] = []
    hazard = inputs.get("hazard")
    if hazard not in HAZARD_OPTIONS:
        problems.append("Select a hazard from the available list.")
    location = inputs.get("location")
    if not isinstance(location, str) or not location.strip():
        problems.append("Enter a location or area name. Coordinates are not required.")
    classification = inputs.get("input_classification")
    if not isinstance(classification, str) or classification not in INPUT_CLASSIFICATIONS:
        problems.append("Choose how the entered conditions should be classified.")

    assets = inputs.get("assets", [])
    if not isinstance(assets, (list, tuple)) or any(not isinstance(asset, str) for asset in assets):
        problems.append("Assets must be provided as a list of names or left empty.")
    elif any(asset not in ASSET_OPTIONS for asset in assets):
        problems.append("Select assets from the available list.")
    for field, label, options in (
        ("drainage_status", "Drainage condition", DRAINAGE_STATUS_OPTIONS),
        ("infrastructure_status", "Infrastructure condition", INFRASTRUCTURE_STATUS_OPTIONS),
    ):
        value = inputs.get(field)
        if value is not None and (not isinstance(value, str) or value not in options):
            problems.append(f"Select a valid {label.lower()} or leave it blank.")

    for field, label in (
        ("rainfall_mm", "Rainfall"),
        ("river_level_m", "River level"),
        ("wind_speed_kmh", "Wind speed"),
        ("temperature_c", "Temperature"),
        ("affected_population", "Affected population"),
    ):
        value = inputs.get(field)
        if value is None:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            problems.append(f"{label} must be a number or left blank.")
            continue
        if not math.isfinite(numeric) or (numeric < 0 and field in {"rainfall_mm", "wind_speed_kmh", "affected_population"}):
            qualifier = "non-negative " if field in {"rainfall_mm", "wind_speed_kmh", "affected_population"} else ""
            problems.append(f"{label} must be a finite, {qualifier}value.")
        elif field == "affected_population" and not numeric.is_integer():
            problems.append("Affected population must be a whole number of people.")

    if inputs.get("rainfall_mm") is not None:
        rainfall_period = str(inputs.get("rainfall_period", "")).strip()
        if rainfall_period not in RAINFALL_PERIOD_OPTIONS:
            problems.append("Choose a valid rainfall time period for the entered rainfall value.")
        elif rainfall_period == "Not supplied":
            problems.append("Choose a rainfall time period for the entered rainfall value.")
        elif rainfall_period == "Other / state in notes" and not str(inputs.get("condition_notes", "")).strip():
            problems.append("Describe the rainfall time period in the condition notes.")
    return problems


def describe_entered_conditions(inputs: dict[str, Any]) -> str:
    """Describe inputs with their units and provenance class for scenario tables."""
    entries = [f"Classification: {inputs.get('input_classification', 'not supplied')}."]
    for field, label, unit in (
        ("rainfall_mm", "rainfall", "mm"),
        ("river_level_m", "river-level reading", "m"),
        ("wind_speed_kmh", "wind speed", "km/h"),
        ("temperature_c", "temperature", "°C"),
        ("affected_population", "affected population context", "people"),
    ):
        value = inputs.get(field)
        if value is not None:
            period = f" over {inputs.get('rainfall_period')}" if field == "rainfall_mm" else ""
            entries.append(f"{label}: {value} {unit}{period} (user-entered).")
    if inputs.get("river_level_m") is not None:
        station = str(inputs.get("river_station", "")).strip() or "station not supplied"
        reference = str(inputs.get("river_reference", "")).strip() or "gauge reference not supplied"
        entries.append(f"River context: {station}; {reference}. This reading is not used in a threshold comparison.")
    if inputs.get("drainage_status"):
        entries.append(f"Drainage condition: {inputs['drainage_status']} (user-described).")
    if inputs.get("infrastructure_status"):
        entries.append(f"Infrastructure condition: {inputs['infrastructure_status']} (user-described).")
    if str(inputs.get("source_and_time", "")).strip():
        entries.append(f"Source/time notes: {inputs['source_and_time'].strip()}")
    if str(inputs.get("condition_notes", "")).strip():
        entries.append(f"Additional notes: {inputs['condition_notes'].strip()}")
    if len(entries) == 1:
        entries.append("No measured numeric conditions entered.")
    return " ".join(entries)


def build_scenario_comparison(inputs: dict[str, Any]) -> pd.DataFrame:
    """Build three qualitative scenario variants; no impacts are numerically modeled."""
    selected = str(inputs.get("hazard", ""))
    components = expand_hazards(selected)
    component_text = ", ".join(components) if components else selected
    assets = inputs.get("assets", [])
    asset_text = ", ".join(assets) if assets else "No assets selected"
    conditions = describe_entered_conditions(inputs)
    pathways = " ".join(HAZARD_NOTES.get(hazard, "") for hazard in components).strip()

    cases = [
        {
            "Scenario": "1 — Entered conditions",
            "Classification": "User-described baseline; not a forecast",
            "Assumptions": f"Hazard(s): {component_text}. Use the conditions and classifications entered by the user. {conditions}",
            "Possible consequences to review": f"Review these pathways: {pathways} No local consequences are calculated.",
            "Assets nominated for review": asset_text,
            "Preparedness checks": "Confirm data sources and timing; check current official information and local response plans.",
        },
        {
            "Scenario": "2 — Service degradation",
            "Classification": "Hypothetical comparison",
            "Assumptions": f"Keep the entered hazard conditions the same; assume partial impairment of a relevant service (for example, drainage, power, communications, or access). {conditions}",
            "Possible consequences to review": f"Review these pathways: {pathways} Partial service impairment may constrain response or access; scale, extent, and affected population are unknown.",
            "Assets nominated for review": asset_text,
            "Preparedness checks": "Identify service dependencies, backup duration, alternate access, responsible operators, and repair resources.",
        },
        {
            "Scenario": "3 — Compound hazard and infrastructure disruption",
            "Classification": "Hypothetical compound scenario",
            "Assumptions": f"Consider {component_text} together with a second hazard or infrastructure failure. For flood-related selections, explicitly review cyclone plus flood and heavy rainfall plus drainage failure as separate possibilities. {conditions}",
            "Possible consequences to review": f"Review these pathways: {pathways} Overlapping hazards may coincide with reduced power, communications, transport, water, or drainage service; no combined impact is estimated.",
            "Assets nominated for review": asset_text,
            "Preparedness checks": "Review event sequence, common dependencies, accessible alternatives, and coordination between service operators.",
        },
    ]
    return pd.DataFrame(cases)


def mitigation_actions_for(hazard: str) -> pd.DataFrame:
    """Return qualitative action candidates with blank user-supplied cost fields."""
    components = expand_hazards(hazard)
    entries: list[tuple[str, str, str, str]] = []
    for component in components:
        for action, rationale, prerequisite in MITIGATION_CATALOG.get(component, []):
            if action not in {row[0] for row in entries}:
                entries.append((action, component, rationale, prerequisite))
    if not entries:
        entries = [("Add an action after local review", hazard, "No hazard-specific action template is available.", "Document local evidence, responsible owner, and prerequisites.")]
    return pd.DataFrame(
        [
            {
                "Action": action,
                "Hazard": component,
                "Rationale (qualitative)": rationale,
                "Prerequisite / evidence needed": prerequisite,
                "Cost INR": None,
                "Cost source / date / scope": "",
                "Funding source": "",
                "User priority (1=highest)": None,
            }
            for action, component, rationale, prerequisite in entries
        ]
    )


def recommendation_candidates(inputs: dict[str, Any]) -> pd.DataFrame:
    """Create unranked planning candidates linked to entered conditions and evidence gaps."""
    selected_hazard = str(inputs.get("hazard", ""))
    components = expand_hazards(selected_hazard)
    assets = inputs.get("assets", [])
    nominated_assets = (
        {asset for asset in assets if isinstance(asset, str)}
        if isinstance(assets, (list, tuple))
        else set()
    )
    classification = str(inputs.get("input_classification", "Unknown / unverified"))
    rows: list[dict[str, str]] = []

    def add(
        action: str,
        basis: str,
        trigger: str,
        rationale: str,
        prerequisites: str,
    ) -> None:
        rows.append(
            {
                "Action candidate": action,
                "Basis": basis,
                "Assessment evidence / trigger": trigger,
                "Why it may help": rationale,
                "Evidence or authority needed": prerequisites,
                "Priority": "Not ranked; local review required",
            }
        )

    for component in components:
        for action, rationale, prerequisites in MITIGATION_CATALOG.get(component, []):
            action_lower = action.casefold()
            if "hospital" in action_lower and "Hospitals" not in nominated_assets:
                continue
            if ("evacuation" in action_lower or "route" in action_lower) and not nominated_assets.intersection(
                {"Roads and bridges", "Shelters"}
            ):
                continue

            trigger = (
                f"Selected scenario: {selected_hazard}; conditions are classified as "
                f"{classification} and are not independently verified."
            )
            if "drainage" in action_lower:
                drainage_status = str(inputs.get("drainage_status", "Not supplied"))
                if drainage_status not in {"", "Not supplied", "Not applicable"}:
                    trigger += f" User-described drainage condition: {drainage_status}."
                else:
                    trigger += " Drainage condition was not supplied; verify locally before selecting an intervention."
            if "hospital" in action_lower:
                trigger += " Hospitals were nominated for review; their locations and hazard exposure are not verified."
            if "evacuation" in action_lower or "route" in action_lower:
                trigger += " Roads/bridges or shelters were nominated; route accessibility and exposure are not verified."
            add(action, "Selected hazard scenario", trigger, rationale, prerequisites)

    source_and_time = str(inputs.get("source_and_time", "")).strip()
    provenance_detail = (
        "Source/time notes were supplied but have not been independently checked."
        if source_and_time
        else "Source/time notes are absent."
    )
    add(
        "Verify condition source, location, units, and time",
        "Input provenance gap",
        f"Input classification: {classification}. {provenance_detail} User-entered values are never authenticated by this workflow.",
        "Establishes whether the scenario inputs can be compared with authoritative local observations, forecasts, or warnings.",
        "Record publisher, source URL or identifier, station/location, timestamp and timezone, units, averaging period, and quality flags.",
    )

    if inputs.get("river_level_m") is not None and (
        not str(inputs.get("river_station", "")).strip()
        or not str(inputs.get("river_reference", "")).strip()
    ):
        add(
            "Confirm river gauge identity and reference",
            "River-level metadata gap",
            "A river-level value was entered without both a station name and gauge reference/datum.",
            "Prevents an unreferenced level from being mistaken for a comparable water-surface elevation or warning threshold.",
            "Confirm station identity, gauge zero/datum, provider, timestamp, units, and applicable official thresholds.",
        )

    if nominated_assets:
        add(
            "Verify asset locations and hazard overlap",
            "Exposure evidence gap",
            f"User-nominated assets/services: {', '.join(sorted(nominated_assets))}; no location-specific exposure join is performed by this workflow.",
            "Determines whether the nominated assets are actually within the relevant hazard footprint and which access or service dependencies matter.",
            "Use an authoritative asset register and a dated, spatially compatible hazard layer; verify coordinate reference system and positional quality.",
        )

    if not rows:
        add(
            "Collect location-specific hazard and impact evidence",
            "Evidence gap",
            "The selected scenario has no available action template in the current catalog.",
            "Provides the minimum local evidence needed for a responsible review without assigning a risk level.",
            "Consult the relevant disaster-management authority and document hazard, exposed assets, vulnerability, and response capacity evidence.",
        )
    return pd.DataFrame(
        rows,
        columns=[
            "Action candidate",
            "Basis",
            "Assessment evidence / trigger",
            "Why it may help",
            "Evidence or authority needed",
            "Priority",
        ],
    )


PRIORITIZATION_CRITERIA = (
    "expected_risk_reduction",
    "population_affected",
    "infrastructure_importance",
    "feasibility",
    "implementation_cost",
    "implementation_time",
    "uncertainty",
)


def recommendation_priority_readiness(
    criteria: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Gate prioritization on sourced evidence; never produce an implicit score."""
    blockers: list[str] = []
    benefit_status = "Not supplied"
    for criterion in PRIORITIZATION_CRITERIA:
        detail = criteria.get(criterion)
        if not isinstance(detail, dict):
            blockers.append(f"{criterion}: no evidence record supplied")
            continue
        if detail.get("value") is None or str(detail.get("value")).strip() == "":
            blockers.append(f"{criterion}: value missing")
        if not str(detail.get("unit", "")).strip():
            blockers.append(f"{criterion}: unit or scale definition missing")
        if not str(detail.get("source", "")).strip():
            blockers.append(f"{criterion}: evidence source missing")
        if detail.get("evidence_state") != "Verified":
            blockers.append(f"{criterion}: evidence is not Verified")
        if criterion == "expected_risk_reduction":
            benefit_status = str(detail.get("benefit_status", "Not supplied"))
            if benefit_status not in {"Validated estimate", "Demonstrated benefit"}:
                blockers.append("expected_risk_reduction: distinguish a validated estimate from a demonstrated benefit")

    if blockers:
        return {
            "status": "Not ranked; evidence is insufficient",
            "blockers": blockers,
            "benefit_status": benefit_status,
            "ranking_basis": "No score or priority order produced.",
        }
    return {
        "status": "Evidence gate passed; stakeholder weighting still required",
        "blockers": [],
        "benefit_status": benefit_status,
        "ranking_basis": (
            "No score or priority order produced. Authorities and affected communities must "
            "define transparent, comparable scales and policy weights before prioritization."
        ),
    }


def _as_decimal(value: Any) -> Decimal | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite() or amount < 0:
        return None
    return amount


def budget_summary(cost_values: list[Any] | pd.Series, budget: Any) -> dict[str, Any]:
    """Sum only entered valid costs, flag unknown/invalid entries, and compare to budget."""
    costs = [_as_decimal(value) for value in list(cost_values)]
    entered = [value for value in costs if value is not None]
    total = sum(entered, Decimal("0"))
    limit = _as_decimal(budget)
    return {
        "entered_total": total,
        "unknown_or_invalid_count": len(costs) - len(entered),
        "budget": limit,
        "remaining": (limit - total) if limit is not None else None,
        "within_budget": (total <= limit) if limit is not None and len(entered) == len(costs) else None,
    }


def compare_action_combinations(
    actions: pd.DataFrame,
    budget: Any,
    combinations: dict[str, list[str]],
) -> pd.DataFrame:
    """Compare user-selected action combinations using costs only, never efficacy."""
    rows = []
    action_names = actions.get("Action", pd.Series(dtype=object)).fillna("").astype(str).str.strip()
    available_names = set(action_names[action_names.ne("")])
    duplicate_names = sorted(name for name in available_names if int(action_names.eq(name).sum()) > 1)
    for label, selected_names in combinations.items():
        # Do not silently treat misspelled/renamed actions as a valid affordable plan.
        requested = [str(name).strip() for name in selected_names if str(name).strip()]
        unknown_names = sorted(set(requested) - available_names)
        repeated_names = sorted(name for name in set(requested) if requested.count(name) > 1)
        chosen = actions.loc[action_names.isin(requested)] if requested else actions.iloc[0:0]
        summary = budget_summary(chosen.get("Cost INR", pd.Series(dtype=object)), budget)
        if not requested:
            status = "No actions selected"
        elif unknown_names:
            status = "Cannot confirm fit: one or more selected action names are not in the action table"
        elif repeated_names:
            status = "Review duplicate selections before comparing costs"
        elif duplicate_names:
            status = "Cannot confirm fit: action table contains duplicate action names"
        elif summary["budget"] is None:
            status = "Enter a budget to compare affordability"
        elif summary["unknown_or_invalid_count"]:
            status = f"Cannot confirm fit: {summary['unknown_or_invalid_count']} selected cost(s) missing or invalid"
        elif summary["within_budget"]:
            status = "Fits entered budget"
        else:
            status = "Exceeds entered budget"
        rows.append(
            {
                "Combination": label,
                "Actions selected by user": "; ".join(requested) if requested else "None",
                "Entered cost total INR": float(summary["entered_total"]),
                "Missing / invalid costs": summary["unknown_or_invalid_count"],
                "Budget remaining INR": float(summary["remaining"]) if summary["remaining"] is not None else None,
                "Budget status": status,
                "Selection issues": "; ".join(
                    [*(f"Unknown action: {name}" for name in unknown_names),
                     *(f"Repeated selection: {name}" for name in repeated_names),
                     *(f"Duplicate action row: {name}" for name in duplicate_names)]
                ) or "None",
                "Basis": "Arithmetic from user-selected actions and entered costs only; no risk reduction estimated.",
            }
        )
    return pd.DataFrame(rows)


@lru_cache(maxsize=24)
def _timestamp_summary(path_text: str, file_size: int, modified_ns: int) -> tuple[str, int, int]:
    """Read timestamps in chunks and cache by file identity for the app session."""
    del file_size, modified_ns  # These are cache-key inputs; values are intentionally unused.
    earliest = latest = None
    valid_count = invalid_count = 0
    try:
        for chunk in pd.read_csv(path_text, usecols=["Data Acquisition Time"], chunksize=250_000):
            timestamps = pd.to_datetime(chunk["Data Acquisition Time"], dayfirst=True, errors="coerce")
            valid = timestamps.dropna()
            valid_count += len(valid)
            invalid_count += int(timestamps.isna().sum())
            if not valid.empty:
                chunk_min, chunk_max = valid.min(), valid.max()
                earliest = chunk_min if earliest is None else min(earliest, chunk_min)
                latest = chunk_max if latest is None else max(latest, chunk_max)
    except (OSError, UnicodeError, ValueError, KeyError, pd.errors.ParserError):
        return "Timestamp range could not be read", valid_count, invalid_count
    if earliest is None:
        return "No valid timestamps", valid_count, invalid_count
    range_text = f"{earliest:%Y-%m-%d %H:%M} to {latest:%Y-%m-%d %H:%M} (as recorded; timezone not documented)"
    return range_text, valid_count, invalid_count


def evidence_inventory(
    project_root: Path,
    rainfall_backtest: dict[str, Any] | None = None,
) -> pd.DataFrame:
    """Summarize available evidence and its limits for this assessment."""
    descriptions = [
        ("data/raw/kerala.csv", "CWC telemetry hourly rainfall (mm); shown as raw station-time observations in the evidence explorer", "Data Acquisition Time", "1,471 duplicate station-time groups include 324 conflicts; no deduplication or accumulation; not fed into a risk score or model"),
        ("data/raw/rainfall_manual_hr_kerala-sw_kl_1991_2020.csv", "Kerala SW manual hourly rainfall (mm); used by the separate, retrospective next-record measurement benchmark", "Data Acquisition Time", "Local rows cover 2000–2014 despite the filename's 1991–2020 label; no exact zero values; irregular coverage; benchmark results are not used in a flood or disaster assessment"),
        ("data/raw/rwl_manual_hr_kerala_sw_031_2021_2025.csv", "Kerala SW manual river level (meter); shown as source-reported values", "Data Acquisition Time", "Gauge reference and some River/Basin metadata need provider confirmation; no threshold or cross-station risk comparison"),
        ("data/raw/rwl_tel_hr_kerala_sw_031_2021_2025.csv", "Kerala SW telemetry river level (meter); shown as source-reported values", "Data Acquisition Time", "F.C.S. Mananthavadi has a known large change across a 69-day gap; gauge reference and some River/Basin metadata are unconfirmed; no threshold or cross-station risk comparison"),
        ("data/raw/air_pollution_data.csv", "Five sample facility / pollutant records", "Observation timestamps are present; provenance is undocumented", "Includes unverified sample rows; AQI does not attribute a source; not used in numerical assessment"),
        ("data/raw/hospital_vulnerability_data.csv", "Five sample hospital rows and scores", "Date range unavailable", "Coordinates, scores, hazard labels, and measurements are undocumented; not used in numerical assessment"),
        ("data/raw/disaster_probability_data.csv", "Five flood-label example rows", "Observation dates are present; provenance is undocumented", "Too small and undocumented for reliable probability or model evaluation; not used in numerical assessment"),
        ("data/raw/compound_disaster_data.csv", "Five compound-event example rows", "Event dates are present; provenance is undocumented", "Unverified labels; not used in scenario calculations"),
        ("data/reference/kochi_corporation_boundary.geojson", "One provisional Kochi Corporation polygon", "Retrieved 2026-10-20; upstream publication date unknown", "Administrative boundary only; not a hazard/exposure layer and not used to infer asset exposure"),
        ("data/raw/koch_wards_2022.geojson", "Community ward snapshot; three invalid source geometries and six missing ward identifiers", "Retrieved 2026-10-20; README describes wards as of 2022", "Context layer only; not a legal boundary, validated coverage mask, or exposure input"),
        ("data/raw/nihfw_national_hospital_directory.csv", "NIHFW national hospital directory; coordinates retained for review only", "Portal says updated 2025-06-02; local retrieval 2026-10-20", "Coordinate order/CRS and positional quality are unresolved; not a hospital exposure layer"),
        ("data/raw/jrc_glofas_rp100_ID185_N20_E70_depth.tif", "JRC GloFAS RP100 modeled river-flood depth tile (paired with ID186)", "Version 2.1.2; tile modified 2025-12-18; retrieved 2026-10-20", "Modeled scenario, not observation or current forecast; artifacts and NoData treatment limit exposure interpretation"),
        ("data/raw/ksdma_flood_return_probability_historical_10_25_50.zip", "KSDMA historical return-period raster archive", "Exact ZIP publication date not stated; retrieved 2026-10-20", "Pixel units/meaning and NoData semantics and reuse permission unresolved; not used for risk or exposure estimates"),
    ]
    rows = []
    for relative_path, content, timestamp_column, limitation in descriptions:
        source_path = project_root / relative_path
        exists = source_path.is_file()
        dates = "Not available"
        if exists and timestamp_column == "Data Acquisition Time":
            stat = source_path.stat()
            dates, valid_count, invalid_count = _timestamp_summary(
                str(source_path), stat.st_size, stat.st_mtime_ns
            )
            dates += f"; {valid_count:,} valid timestamp rows"
            if invalid_count:
                dates += f"; {invalid_count:,} invalid/missing timestamps"
        rows.append(
            {
                "Dataset / file": relative_path,
                "Available": "Yes" if exists else "No",
                "Contents / units": content,
                "Date information": dates,
                "Known limitation / role in this assessment": limitation if exists else "File not present in this workspace.",
            }
        )
    if rainfall_backtest:
        summary = rainfall_backtest["summary"]
        scores = rainfall_backtest["metrics"]
        model = scores["gradient_boosting"]
        median = scores["station_median"]
        persistence = scores["persistence"]
        backtest_contents = (
            f"Gradient-boosting candidate next-record rainfall benchmark (mm): "
            f"MAE {model['mae_mm']:.3f}, RMSE {model['rmse_mm']:.3f}; "
            f"station-median baseline MAE {median['mae_mm']:.3f}, RMSE {median['rmse_mm']:.3f}; "
            f"persistence baseline MAE {persistence['mae_mm']:.3f}, RMSE {persistence['rmse_mm']:.3f}."
        )
        backtest_dates = (
            f"Training before {summary['train_end_exclusive']}; test "
            f"{summary['test_period_start']} to {summary['test_period_end']}"
        )
        backtest_limitation = (
            f"{summary['test_pairs']:,} exact one-hour held-out pairs from "
            f"{summary['test_stations']} of {summary['all_stations']} stations; "
            "retrospective only, dry-hour representation is unknown, and there are no linked flood outcomes. "
            "Not used by the scenario assessment and not a current rainfall/flood forecast."
        )
        benchmark_status = "Yes — completed historical benchmark"
    else:
        backtest_contents = "Historical one-hour rainfall benchmark; run from the evidence explorer to calculate test metrics."
        backtest_dates = "Not run in this session"
        benchmark_source_exists = (
            project_root / "data" / "raw" / "rainfall_manual_hr_kerala-sw_kl_1991_2020.csv"
        ).is_file()
        backtest_limitation = (
            "The local manual rainfall series ends in 2014. The optional model check is not used by the decision assessment; "
            "no current rainfall forecast or flood prediction is available."
            if benchmark_source_exists
            else "Manual rainfall source file is not present in this workspace."
        )
        benchmark_status = "Source available; benchmark not run" if benchmark_source_exists else "No"
    rows.append(
        {
            "Dataset / file": "Historical manual-rainfall benchmark",
            "Available": benchmark_status,
            "Contents / units": backtest_contents,
            "Date information": backtest_dates,
            "Known limitation / role in this assessment": backtest_limitation,
        }
    )
    quality_by_path = {
        row["Dataset / file"]: row
        for row in evidence_quality_inventory(project_root)
    }
    for row in rows:
        quality = quality_by_path.get(row["Dataset / file"])
        if quality:
            row.update(quality)
        else:
            row.update(
                {
                    "Evidence ID": "historical_rainfall_benchmark",
                    "Evidence state": "Incomplete" if benchmark_status != "No" else "Unavailable",
                    "Source authority": "Kerala Surface Water Department as listed by NWDP",
                    "Source URL": "https://nwdp.nwic.gov.in/en/dataset/rainfall-manual-hourly-kerala-sw-department/resource/ceb9ffcf-927b-4b34-8ab5-6c3098dd95a9",
                    "Publication / update date": "Portal resource updated 2025-03-05",
                    "Retrieval / review date": "Unknown for local copy; portal metadata reviewed 2026-10-20",
                    "Geographic relevance": "Kerala station series; no validated Kochi spatial match",
                    "Temporal relevance": "Retrospective measurement benchmark only",
                    "Measurement quality": "Irregular records; benchmark selects exact one-hour pairs only",
                    "Spatial resolution / CRS": "Station series; location/CRS not used in benchmark",
                    "Completeness": "Partial station/time coverage; not a flood-outcome dataset",
                    "Licence": "NWDP metadata says Other (Open); check current terms",
                    "Verification status": "Benchmark results are separate from disaster assessment",
                    "Limitations": "Not a flood model or current rainfall forecast.",
                }
            )
    return pd.DataFrame(rows)


def hazard_evidence_checklist(inputs: dict[str, Any], project_root: Path) -> pd.DataFrame:
    """Explain the evidence needed for the selected hazard without calculating a risk score.

    Status labels are conservative: file presence alone never establishes scientific
    suitability, local coverage, legal reuse, or independent verification.
    """
    hazard = str(inputs.get("hazard", ""))
    components = expand_hazards(hazard)

    evidence_needs = {
        "Flood": [
            ("Time-matched rainfall and river/coastal observations", "data/raw/kerala.csv", "Raw rainfall file is present, but 324 station-time groups have conflicting values; telemetry datum and time zone require confirmation.", "Keep raw rows; reconcile against provider documentation and use verified local observations with timestamps and units."),
            ("Local flood-hazard/depth evidence with permitted reuse", "data/raw/jrc_flood_depth", "JRC 100-year river-flood tiles are reviewed as modeled hazard data, but preview/use is withheld pending licence clarification.", "Resolve licence statements, inspect raster semantics and study-area overlap, then validate before analysis."),
            ("Verified drainage, terrain and catchment context", "data/processed/spatial_layers", "No independently validated local drainage/terrain evidence is established by the current workflow.", "Acquire authoritative layers with provenance, CRS, units, coverage and licence; validate geometry and completeness."),
            ("Verified exposed assets and safe access routes", "data/processed/spatial_layers", "Hospital and critical-facility locations/exposure are not independently validated; the ward boundary is provisional.", "Verify facility identities and coordinates and suitable road layers before any asset-level exposure claim."),
        ],
        "Cyclone": [
            ("Current official cyclone/wind/rainfall bulletin", None, "No live official warning feed is connected to this assessment.", "Check the latest IMD bulletin and local authority instructions outside this prototype; record issue time and validity."),
            ("Local wind, coastal-water and rainfall context", None, "User-entered values are not verified by the app and no local impact model is validated.", "Record station/source, observation or forecast time, units, averaging period and location."),
            ("Verified shelters, access and critical-service continuity", None, "Shelter, road and service availability is not verified by this workflow.", "Use current authority-maintained inventories and verify capacity, accessibility and backup arrangements."),
        ],
        "Earthquake": [
            ("Authoritative seismic context and site conditions", None, "No site-specific seismic or geotechnical assessment is connected.", "Use authoritative hazard sources and qualified engineering review for site-specific decisions."),
            ("Verified building inventory and structural assessments", None, "The app cannot certify building safety or estimate building damage.", "Obtain qualified inspection records and verified building attributes."),
            ("Critical-service continuity and safe access", None, "Facility backup duration and route availability are not verified.", "Confirm utility dependencies, emergency plans, backup capacity and alternate access."),
        ],
        "Landslide": [
            ("Authoritative local landslide/slope and geology evidence", None, "No verified site-specific slope or geotechnical layer is established here.", "Acquire authoritative hazard layers and seek qualified geotechnical review."),
            ("Time-matched rainfall and field observations", "data/raw/kerala.csv", "Rainfall observations contain conflicting station-time groups and are not independently reconciled.", "Resolve data-quality issues and confirm local station coverage, units and timing."),
            ("Verified roads, settlements and response access", None, "Local exposure and access are not verified by this workflow.", "Validate authoritative asset and transport layers before identifying exposed places."),
        ],
        "Heatwave": [
            ("Current official heat/weather bulletin", None, "No live official warning feed is connected.", "Check current IMD and local health-authority information and record issue time."),
            ("Local temperature, humidity and health vulnerability evidence", None, "No validated local heat-exposure or health-outcome dataset is linked to this assessment.", "Use quality-controlled observations and approved health-planning data with clear units and coverage."),
            ("Cooling, water and healthcare service capacity", None, "Service availability and backup duration are not verified.", "Confirm current facility inventories, operating status and continuity plans."),
        ],
        "Drought": [
            ("Time-series rainfall and water-supply/reservoir evidence", "data/raw/rainfall_manual_hr_kerala-sw_kl_1991_2020.csv", "The local manual rainfall series covers 2000–2014 despite the filename label; it is historical and not a current supply indicator.", "Use current, authoritative rainfall and water-resource observations with documented temporal coverage."),
            ("Local demand, supply and operational thresholds", None, "No verified local demand/supply balance or official trigger thresholds are connected.", "Obtain provider data and use approved local response plans."),
            ("Essential-service water continuity", None, "Facility storage and replenishment capacity are not verified.", "Verify service-specific storage, demand, backup duration and replenishment plans."),
        ],
        "Industrial incident": [
            ("Verified facility identity, hazard inventory and emissions/incident records", "data/raw/industrial", "Facility records in the current evidence inventory are incomplete or unverified; no source attribution is established.", "Use regulator/operator records with dates, facility identifiers, provenance and licence."),
            ("Pollutant-specific monitoring and meteorology", "data/raw/air_pollution_data.csv", "Five sample rows have undocumented provenance; AQI alone cannot identify a source.", "Use quality-controlled station measurements, pollutant, units, averaging period, time and meteorology."),
            ("Official response protocols and responsible contacts", None, "Facility-specific emergency procedures are not verified here.", "Use current regulator/operator emergency plans and official response channels."),
        ],
        "Infrastructure failure": [
            ("Verified asset inventory and condition/maintenance records", None, "No validated, complete local infrastructure inventory is established by this workflow.", "Acquire authoritative asset registers and inspection/maintenance records."),
            ("Service dependencies and backup capacity", None, "Power, water, communications and access dependencies are not mapped or verified.", "Confirm dependency links, responsible operators, backup duration and alternate routes."),
            ("Failure history and response procedures", None, "No validated local failure/repair time series is linked.", "Use dated operator records and approved continuity plans."),
        ],
    }
    rows: list[dict[str, str]] = []
    for component in components:
        needs = evidence_needs.get(component, [
            ("Hazard-specific authoritative observations and validated method", None, "No hazard-specific evidence requirements are configured for this selection.", "Consult the responsible authority and document a reviewable method before quantifying risk.")
        ])
        for required, relative_path, limitation, next_step in needs:
            if relative_path is None:
                availability = "Not connected / not verified"
            else:
                path = project_root / relative_path
                exists = path.exists()
                availability = "File/path present; suitability unverified" if exists else "Not present at expected path"
            rows.append({
                "Hazard component": component,
                "Evidence needed": required,
                "Workspace check": availability,
                "Known limitation": limitation,
                "Next verification step": next_step,
            })
    return pd.DataFrame(rows, columns=[
        "Hazard component", "Evidence needed", "Workspace check",
        "Known limitation", "Next verification step"
    ])


def evidence_provenance_summary(inputs: dict[str, Any]) -> dict[str, str]:
    """Classify user-entered evidence conservatively; never certify it from notes alone."""
    classification = str(inputs.get("input_classification", "")).strip()
    source_notes = str(inputs.get("source_and_time", "")).strip()

    if classification == "Hypothetical scenario assumption":
        provenance = "Hypothetical assumption — not an observation or forecast"
        interpretation = "Use only for conditional what-if discussion; it is not evidence that the event or condition exists."
        verification = "No real-world claim can be made from this assumption."
    elif classification == "Historical event (source not independently verified)":
        provenance = "Historical event — source not independently verified"
        interpretation = "Treat as an event claim to verify; it does not establish current conditions or local impacts."
        verification = "Confirm the event record, source, date, location, measured variables, units, and independently documented outcomes."
    elif classification == "User-reported observation (source not independently verified)":
        provenance = "User-reported observation — unverified"
        interpretation = "Treat as a report to investigate, not as a quality-controlled measurement."
        verification = "Confirm the original provider, station/location, timestamp and time zone, units, measurement period, and any quality flags."
    elif classification == "Forecast supplied by user (not checked by app)":
        provenance = "User-supplied forecast — not checked by the app"
        interpretation = "Do not present it as the latest or official forecast, or infer a local impact from it."
        verification = "Check the issuing authority/provider, issue time, valid period, location, units, update status, and relevant official instructions."
    else:
        provenance = "Unknown / unverified evidence class"
        interpretation = "Do not treat the entered values as measured facts or an official forecast."
        verification = "Identify the evidence class and verify its origin, timing, units, location, and suitability before relying on it."

    return {
        "Input evidence class": classification or "Unknown / unverified",
        "Provenance status": provenance,
        "Source/time notes": (
            f"User-entered (not independently verified; not independently checked): {source_notes}"
            if source_notes else "Not supplied"
        ),
        "Permitted interpretation": interpretation,
        "Verification gate": verification,
    }


def decision_readiness_summary(inputs: dict[str, Any], input_quality: dict[str, Any]) -> dict[str, Any]:
    """Translate hazard-specific evidence gaps into an ordered, non-numeric decision plan."""
    hazard = str(inputs.get("hazard", "Unknown hazard"))
    missing = list(dict.fromkeys(
        str(item).strip()
        for item in input_quality.get("evidence_factors_missing_or_unverified", [])
        if str(item).strip()
    ))
    errors = list(dict.fromkeys(str(item) for item in input_quality.get("errors", [])))
    warnings = list(dict.fromkeys(str(item) for item in input_quality.get("warnings", [])))
    classification = str(inputs.get("input_classification", "")).strip()
    source_notes = str(inputs.get("source_and_time", "")).strip()

    next_steps = []
    next_steps.append({
        "Priority": 1,
        "Action": "Verify the input provenance",
        "Why it matters": (
            "The scenario is hypothetical; keep it explicitly conditional."
            if classification == "Hypothetical scenario assumption"
            else "Source notes are absent; the entered values cannot be independently traced."
            if not source_notes
            else "Source notes were user-entered and have not been independently checked."
        ),
        "Completion evidence": "Original source/provider, issue or observation time, location, units, valid period, and quality flags recorded.",
    })
    if missing:
        next_steps.append({
            "Priority": 2,
            "Action": f"Resolve {len(missing)} hazard-specific evidence gap(s)",
            "Why it matters": "; ".join(missing),
            "Completion evidence": "Each item is supported by a suitable source or clearly marked unavailable; no gap is silently treated as absence.",
        })
    next_steps.append({
        "Priority": 3 if missing else 2,
        "Action": "Check exposed assets and vulnerability",
        "Why it matters": "A hazard signal alone does not establish which people, hospitals, roads, or services are exposed or vulnerable.",
        "Completion evidence": "Suitable geospatial layers or facility records with coverage, date, coordinate reference system, provenance, and quality checks.",
    })
    next_steps.append({
        "Priority": 4 if missing else 3,
        "Action": "Establish model and outcome validation",
        "Why it matters": "A complete form and plausible values do not validate a consequence model or produce a reliable probability.",
        "Completion evidence": "Documented local event/outcome labels, appropriate baseline comparison, held-out evaluation, uncertainty analysis, and independent review.",
    })
    next_steps.append({
        "Priority": 5 if missing else 4,
        "Action": "Review actions, owners, prerequisites, and documented costs",
        "Why it matters": "Budget fit is arithmetic only; it does not demonstrate effectiveness, optimality, or risk reduction.",
        "Completion evidence": "Named responsible owner, evidence-backed prerequisites, dated cost source/scope, and locally approved plan.",
    })

    if errors:
        status = "INPUT REVIEW REQUIRED — do not rely on this scenario until errors are resolved"
    elif classification == "Hypothetical scenario assumption":
        status = "WHAT-IF PLANNING ONLY — assumptions are not evidence of current conditions"
    elif missing or warnings:
        status = "EVIDENCE GAPS REMAIN — use for preparation planning, not real-world prediction"
    else:
        status = "QUALITATIVE REVIEW ONLY — numerical prediction is not validated"

    return {
        "hazard": hazard,
        "decision_status": status,
        "numerical_prediction_gate": "CLOSED — no validated local hazard-specific consequence model is enabled",
        "critical_input_errors": errors,
        "hazard_specific_gaps": missing,
        "input_warnings": warnings,
        "next_steps": next_steps,
        "interpretation": "This is an ordered work plan, not a risk score, forecast, official warning, or estimate of mitigation effectiveness.",
    }


def assessment_summary(inputs: dict[str, Any]) -> dict[str, str]:
    """Return a qualified status without assigning an unsupported risk category."""
    hazards = expand_hazards(str(inputs.get("hazard", "")))
    joined = ", ".join(hazards) if hazards else str(inputs.get("hazard", "Not selected"))
    return {
        "status": "Insufficient evidence for a validated numerical prediction; numerical prediction not validated; qualitative scenario review only",
        "method": "Qualitative evidence and preparedness review. Hazard, exposure, vulnerability and response capacity, and consequences remain distinct. No locally validated model or compatible spatial and temporal evidence join is available; no probability, flood depth, affected-area, casualty, damage, or risk-reduction estimate is produced.",
        "hazards": joined,
        "interpretation": (
            "Hypothetical values are valid inputs for a conditional what-if review only; they are not observations or evidence that an event exists. The workflow organizes evidence, identifies gaps, and does not estimate event probability or impacts."
            if inputs.get("input_classification") == "Hypothetical scenario assumption"
            else "Submitted values remain observations or forecasts as labelled by the user. The workflow organizes evidence, identifies gaps, and supports preparedness review; it does not establish that an event will occur or estimate its probability or impacts."
        ),
        "additional_caution": "Numerical prediction not validated. No numerical risk score or risk class is assigned. Compound hazards are not treated as additive scores. The legacy demonstration thresholds in assessment.py are not used here and are not official warning thresholds. The separate historical rainfall model predicts recorded rainfall only; it is not a flood model. Unresolved river-level references and rainfall conflicts prevent threshold comparisons."
    }


def assessment_evidence_matrix(
    inputs: dict[str, Any],
    evidence: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Show which risk dimensions are supported, unverified, or still unassessed."""
    input_problems = validate_workflow_inputs(inputs)
    classification = str(inputs.get("input_classification", "Unknown / unverified"))
    source_and_time = str(inputs.get("source_and_time", "")).strip()
    components = expand_hazards(str(inputs.get("hazard", "")))
    assets = inputs.get("assets", [])
    nominated_assets = [asset for asset in assets if isinstance(asset, str)] if isinstance(assets, (list, tuple)) else []
    user_conditions = []
    for field, label in (
        ("rainfall_mm", "rainfall"),
        ("river_level_m", "river level"),
        ("wind_speed_kmh", "wind speed"),
        ("temperature_c", "temperature"),
    ):
        if inputs.get(field) is not None:
            user_conditions.append(f"{label} supplied")
    for field, label in (
        ("drainage_status", "drainage"),
        ("infrastructure_status", "infrastructure"),
    ):
        value = str(inputs.get(field, "Not supplied"))
        if value not in {"", "Not supplied", "Not applicable"}:
            user_conditions.append(f"{label}: {value}")

    evidence_status = "Evidence register not supplied to this review."
    evidence_quality_status = "No item-level quality states available."
    if evidence is not None and {"Available", "Dataset / file"}.issubset(evidence.columns):
        available_count = int(evidence["Available"].eq("Yes").sum())
        evidence_status = (
            f"{available_count} of {len(evidence)} listed evidence records are present in the workspace; "
            "presence does not mean they are validated or used in this assessment."
        )
        if "Evidence state" in evidence.columns:
            state_counts = evidence["Evidence state"].value_counts().to_dict()
            evidence_quality_status = f"Evidence-state counts: {state_counts}."
            conflicts = evidence.loc[
                evidence["Evidence state"].eq("Conflicting"), "Dataset / file"
            ].astype(str).tolist()
            if conflicts:
                evidence_quality_status += f" Conflicting records: {', '.join(conflicts)}."

    hazard_text = ", ".join(components) if components else "No valid hazard selected"
    conditions_text = ", ".join(user_conditions) if user_conditions else "No hazard-condition measurements supplied"
    if nominated_assets:
        exposure_text = f"Nominated by user: {', '.join(nominated_assets)}."
    else:
        exposure_text = "No assets or services nominated."
    population = inputs.get("affected_population")
    if population is not None:
        exposure_text += f" Population context entered: {population}; not independently verified."
    vulnerability_text = "; ".join(
        f"{label}: {inputs.get(field)}"
        for field, label in (
            ("drainage_status", "Drainage"),
            ("infrastructure_status", "Other infrastructure"),
        )
        if str(inputs.get(field, "Not supplied")) not in {"", "Not supplied", "Not applicable"}
    ) or "No vulnerability or service-condition information supplied."

    compound_status = "No compound interaction assessed for this single-hazard selection."
    compound_evidence = "No event interaction or cascading effect is calculated."
    if len(components) > 1:
        compound_status = "Components identified separately; interaction not modeled."
        compound_evidence = f"Selected components: {hazard_text}. Components are not converted into or added as scores."

    rows = [
        {
            "Dimension": "Input validation and provenance",
            "Status": "Blocked by invalid input" if input_problems else "Structurally valid; provenance unverified",
            "Evidence available": (
                "; ".join(input_problems)
                if input_problems
                else f"Classification: {classification}. "
                + (f"Source/time notes supplied: {source_and_time}" if source_and_time else "No source/time notes supplied.")
            ),
            "Gap / uncertainty": "User-entered values and source details are not independently authenticated.",
            "Required next check": "Verify source identity, timestamp/timezone, units, location, and measurement/forecast meaning.",
        },
        {
            "Dimension": "Data availability and quality",
            "Status": "Catalogued; conflicts or gaps remain" if "Conflicting" in evidence_quality_status or "Incomplete" in evidence_quality_status else "Catalogued only",
            "Evidence available": f"{evidence_status} {evidence_quality_status}",
            "Gap / uncertainty": "Available files may be unverified, conflicting, stale, incomplete, or spatially incompatible; the inventory does not imply suitability for this assessment.",
            "Required next check": "Check each source's metadata, quality flags, coverage, units, licence, and provenance before analysis.",
        },
        {
            "Dimension": "Hazard",
            "Status": "Scenario supplied; event not independently verified",
            "Evidence available": f"Selected scenario: {hazard_text}; {conditions_text}.",
            "Gap / uncertainty": "No current official warning, locally calibrated hazard intensity, or validated threshold is applied.",
            "Required next check": "Match event conditions to an authoritative, location- and time-relevant hazard source.",
        },
        {
            "Dimension": "Exposure",
            "Status": "User-nominated only; spatial exposure not assessed",
            "Evidence available": exposure_text,
            "Gap / uncertainty": "No verified population/asset inventory is joined to a compatible hazard footprint.",
            "Required next check": "Validate asset/population locations, dates, coverage, and coordinate reference system; perform a documented spatial join.",
        },
        {
            "Dimension": "Vulnerability",
            "Status": "User-described only" if vulnerability_text != "No vulnerability or service-condition information supplied." else "Not assessed",
            "Evidence available": vulnerability_text,
            "Gap / uncertainty": "No validated structural, social, health, service-condition, or fragility evidence is available for this location.",
            "Required next check": "Collect asset-specific condition and vulnerability evidence with a documented method and responsible authority.",
        },
        {
            "Dimension": "Compound interactions",
            "Status": compound_status,
            "Evidence available": compound_evidence,
            "Gap / uncertainty": (
                "Temporal overlap, spatial overlap, hazard dependence, and shared infrastructure failure pathways are unknown; "
                "component scores must not be added."
            ),
            "Required next check": "Establish event sequence, compatible hazard footprints, dependencies, and observed cascading outcomes.",
        },
        {
            "Dimension": "Consequences",
            "Status": "Pathways for review only; impacts not calculated",
            "Evidence available": "Hazard-specific planning prompts and user-nominated assets only.",
            "Gap / uncertainty": "No location-linked impact, service-loss, casualty, damage, or recovery data supports an estimate.",
            "Required next check": "Link validated event footprints to exposed assets and observed impact records.",
        },
        {
            "Dimension": "Risk",
            "Status": "Not estimated; no risk class assigned",
            "Evidence available": "No calibrated combination of hazard, exposure, vulnerability, and capacity is used.",
            "Gap / uncertainty": "Missing compatible, validated inputs prevent a defensible probability, severity, or risk category.",
            "Required next check": "Develop and validate a suitable method only after the required local evidence and target outcomes are available.",
        },
        {
            "Dimension": "Capacity and resilience",
            "Status": "Not assessed",
            "Evidence available": "No response, service continuity, coping, or recovery capacity data is measured.",
            "Gap / uncertainty": "Preparedness prompts do not establish resilience or intervention effectiveness.",
            "Required next check": "Document locally verified response plans, service dependencies, backup capacity, and recovery indicators.",
        },
        {
            "Dimension": "Infrastructure dependencies",
            "Status": "Conceptual pathways only; local links unverified",
            "Evidence available": (
                f"{len(dependency_review_table())} candidate physical, co-occurrence, service, and exposure relationships "
                "are listed for investigation; no local evidence is attached."
            ),
            "Gap / uncertainty": "A road-to-hospital or utility cascade is not an observed vulnerability claim.",
            "Required next check": "Verify asset topology, service dependencies, redundancy, event timing, and disruption records.",
        },
    ]
    return pd.DataFrame(
        rows,
        columns=["Dimension", "Status", "Evidence available", "Gap / uncertainty", "Required next check"],
    )


def report_rows(
    inputs: dict[str, Any],
    evidence: pd.DataFrame,
    scenarios: pd.DataFrame,
    actions: pd.DataFrame,
    budget: Any,
    combinations: pd.DataFrame,
    project_root: Path,
    evidence_checklist: pd.DataFrame | None = None,
    readiness_summary: dict[str, Any] | None = None,
    disaster_assessment: dict[str, Any] | None = None,
    compound_assessment: dict[str, Any] | None = None,
    scenario_prediction: dict[str, Any] | None = None,
    scenario_screening: pd.DataFrame | None = None,
    consequence_assessment: dict[str, Any] | None = None,
    scientific_frame: dict[str, Any] | None = None,
    input_quality: dict[str, Any] | None = None,
    uncertainty_register: pd.DataFrame | None = None,
    dependency_review: pd.DataFrame | None = None,
    validation_checklist: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build a flat, exportable report that records actual inputs and calculations."""
    rows: list[dict[str, str]] = []

    def add(section: str, field: str, value: Any) -> None:
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value, ensure_ascii=False, default=str)
        rows.append({"Section": section, "Field": field, "Value": "" if value is None else str(value)})

    add("Report", "Generated date", date.today().isoformat())
    add("Report", "System limitation", "Exploratory prototype; not an official warning or validated decision system.")
    for key, value in inputs.items():
        add("User inputs", key, value)
    for key, value in assessment_summary(inputs).items():
        add("Assessment", key, value)
    for key, value in evidence_provenance_summary(inputs).items():
        add("Evidence provenance gate", key, value)
    if readiness_summary is not None:
        for key, value in readiness_summary.items():
            add("Decision readiness", key, value)
    if scenario_prediction is not None:
        for key, value in scenario_prediction.items():
            add("Conditional scenario screening", key, value)
    if disaster_assessment is not None:
        for key, value in disaster_assessment.items():
            if key != "component_assessments":
                add("Hazard-specific scientific assessment", key, value)
        for component, result in disaster_assessment.get("component_assessments", {}).items():
            add("Compound component assessment", component, result)
    if compound_assessment is not None:
        for key, value in compound_assessment.items():
            add("Compound cyclone-flood evidence assessment", key, value)
    if consequence_assessment is not None:
        for key, value in consequence_assessment.items():
            add("Consequence assessment", key, value)
    for _, row in assessment_evidence_matrix(inputs, evidence).iterrows():
        add("Assessment dimensions", str(row["Dimension"]), row.to_dict())
    if scenario_screening is not None:
        for index, row in scenario_screening.iterrows():
            add("Scenario screening evidence", f"Finding {index + 1}", row.to_dict())
    if scientific_frame is not None:
        for key, value in scientific_frame.items():
            add("Scientific scenario frame", key, value)
    if input_quality is not None:
        for key, value in input_quality.items():
            add("Hazard-specific input quality", key, value)
    uncertainty = uncertainty_register if uncertainty_register is not None else build_uncertainty_register(inputs, evidence)
    for _, row in uncertainty.iterrows():
        add("Uncertainty register", str(row.get("Uncertainty type", "Uncertainty")), row.to_dict())
    dependencies = dependency_review if dependency_review is not None else dependency_review_table()
    for _, row in dependencies.iterrows():
        add("Conceptual infrastructure dependency", f"{row.get('From', '')} -> {row.get('To', '')}", row.to_dict())
    if validation_checklist is not None:
        for index, row in validation_checklist.iterrows():
            add("Historical validation requirements", f"Stage {index + 1}", row.to_dict())
    for _, row in evidence.iterrows():
        add("Evidence", str(row["Dataset / file"]), {k: row[k] for k in evidence.columns if k != "Dataset / file"})
    if evidence_checklist is not None:
        for index, row in evidence_checklist.iterrows():
            add("Evidence readiness checklist", f"Requirement {index + 1}", row.to_dict())
    for _, row in scenarios.iterrows():
        add("Scenario comparison", str(row["Scenario"]), row.to_dict())
    for index, row in recommendation_candidates(inputs).iterrows():
        add("Evidence-linked recommendation candidate", f"Candidate {index + 1}", row.to_dict())
    priority_gate = recommendation_priority_readiness({})
    add("Recommendation prioritization", "Evidence gate", priority_gate)
    for index, row in actions.iterrows():
        add("Mitigation action", f"Action {index + 1}", row.to_dict())
    budget_result = budget_summary(actions.get("Cost INR", pd.Series(dtype=object)), budget)
    add("Budget", "User-entered budget INR", budget_result["budget"])
    add("Budget", "Sum of valid entered action costs INR", budget_result["entered_total"])
    add("Budget", "Remaining after entered costs INR", budget_result["remaining"])
    add("Budget", "Missing or invalid cost count", budget_result["unknown_or_invalid_count"])
    add("Budget", "Fit status", "Complete-cost actions fit budget" if budget_result["within_budget"] is True else "Complete-cost actions exceed budget" if budget_result["within_budget"] is False else "Cannot confirm fit; budget or one or more costs are missing/invalid")
    for _, row in combinations.iterrows():
        add("User-selected budget comparison", str(row["Combination"]), row.to_dict())
    add("Data quality", "Assessment handling", "Evidence inventory and historical validation artifacts are context only; no listed dataset is automatically joined to the selected scenario or used to calculate disaster risk.")
    add("Priority explanation", "Basis", "Action priority and combination selection are user-entered. Budget-fit results are arithmetic and do not imply effectiveness or optimality.")
    return pd.DataFrame(rows, columns=["Section", "Field", "Value"])


def report_html(report: pd.DataFrame) -> str:
    """Render a safe, readable standalone HTML report from flat report rows."""
    table_rows = "".join(
        "<tr><td>{}</td><td>{}</td><td>{}</td></tr>".format(
            html.escape(str(row["Section"])),
            html.escape(str(row["Field"])),
            html.escape(str(row["Value"])),
        )
        for _, row in report.iterrows()
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>AI RESILIENCE decision report</title>"
        "<style>body{font:16px system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18212b}"
        "table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd3da;text-align:left;vertical-align:top;padding:.55rem}"
        "th{background:#edf2f7}tr:nth-child(even){background:#f8fafb}.notice{border-left:4px solid #b45309;padding:.8rem;background:#fff7ed}</style>"
        "</head><body><h1>AI RESILIENCE decision report</h1>"
        "<p class='notice'>Exploratory prototype only. This report is not an official warning, validated prediction, or guaranteed mitigation plan.</p>"
        "<table><thead><tr><th>Section</th><th>Item</th><th>Value</th></tr></thead><tbody>"
        + table_rows
        + "</tbody></table></body></html>"
    )

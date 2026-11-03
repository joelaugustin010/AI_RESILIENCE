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


HAZARD_OPTIONS = [
    "Flood",
    "Cyclone",
    "Earthquake",
    "Landslide",
    "Heatwave",
    "Drought",
    "Industrial incident",
    "Infrastructure failure",
    "Compound: cyclone + flood",
    "Compound: heavy rainfall + drainage failure",
]

HAZARD_NOTES = {
    "Flood": "Review local inundation evidence, drainage condition, safe access, water and sanitation continuity.",
    "Cyclone": "Review wind-related damage pathways, shelter access, and timing with rainfall or coastal water.",
    "Earthquake": "Review structural and non-structural building safety, utility isolation, and response access.",
    "Landslide": "Review locally verified slope/ground evidence, rainfall context, access routes, and safe-area plans.",
    "Heatwave": "Review heat-health plans, cooling access, water supply, outdoor worker exposure, and backup power.",
    "Drought": "Review water-source reliability, demand management, and health and livelihood dependencies.",
    "Industrial incident": "Review facility-specific hazard information, monitoring, isolation procedures, and official response protocols.",
    "Infrastructure failure": "Review dependencies and cascading failures across power, water, transport, drainage, and communications.",
}

MITIGATION_CATALOG = {
    "Flood": [
        ("Drainage inspection and maintenance", "Can identify blocked or damaged assets before heavy rain.", "Verified asset register, inspection route, maintenance logs, disposal plan."),
        ("Drainage capacity improvement study", "Can identify locations for engineered capacity changes; no local benefit is quantified.", "Hydraulic survey/model, design review, permits, lifecycle maintenance plan."),
        ("Hospital continuity and flood preparedness", "Can improve continuity planning for essential care during access or utility disruption.", "Verified facility list, site-specific flood review, backup power/water duration."),
        ("Evacuation route and shelter review", "Can identify route and shelter gaps for planning; no routes are verified in this app.", "Authoritative road/shelter layers, accessibility review, local drills."),
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
    """Expand compound labels into their component hazards without scoring them."""
    if selection == "Compound: cyclone + flood":
        return ["Cyclone", "Flood"]
    if selection == "Compound: heavy rainfall + drainage failure":
        return ["Flood", "Infrastructure failure"]
    return [selection] if selection in HAZARD_NOTES else []


def validate_workflow_inputs(inputs: dict[str, Any]) -> list[str]:
    """Return clear validation messages for user-entered scenario values."""
    problems: list[str] = []
    hazard = inputs.get("hazard")
    if hazard not in HAZARD_OPTIONS:
        problems.append("Select a hazard from the available list.")
    if not str(inputs.get("location", "")).strip():
        problems.append("Enter a location or area name. Coordinates are not required.")

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

    if inputs.get("rainfall_mm") is not None and str(inputs.get("rainfall_period", "")).strip() in {"", "Not supplied"}:
        problems.append("Choose a rainfall time period for the entered rainfall value.")
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
    if inputs.get("source_checked_by_user"):
        entries.append(
            "User attests that they reviewed the supplied source/time/location/units where available; "
            "this self-attestation is not independently verified by the app."
        )
    else:
        entries.append(
            "Source review not confirmed by user; all entered values remain unverified by the app."
        )
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
    return pd.DataFrame(rows)


def hazard_evidence_checklist(inputs: dict[str, Any], project_root: Path) -> pd.DataFrame:
    """Explain the evidence needed for the selected hazard without calculating a risk score.

    Status labels are conservative: file presence alone never establishes scientific
    suitability, local coverage, legal reuse, or independent verification.
    """
    hazard = str(inputs.get("hazard", ""))
    if hazard == "Compound: cyclone + flood":
        components = ["Flood", "Cyclone"]
    elif hazard == "Compound: heavy rainfall + drainage failure":
        components = ["Flood", "Infrastructure failure"]
    else:
        components = [hazard]

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
    """Return a qualified non-numeric status; no unsupported estimates are generated."""
    hazards = expand_hazards(str(inputs.get("hazard", "")))
    joined = ", ".join(hazards) if hazards else str(inputs.get("hazard", "Not selected"))
    return {
        "status": "Qualitative scenario assessment completed — numerical prediction not validated",
        "method": "Conditional, rule-transparent scenario review based on the values and assumptions entered by the user, plus evidence and preparedness checks. No calibrated probability, flood depth, affected-area estimate, casualty/damage estimate, or risk-reduction estimate is produced.",
        "hazards": joined,
        "interpretation": "Hypothetical values are valid inputs for exploring what-if consequences and preparedness actions. Findings are conditional on those assumptions and do not mean the event will occur. Real-world prediction remains unavailable until suitable local data, a hazard-specific model, and independent validation are established.",
        "additional_caution": "The legacy demonstration thresholds in assessment.py are not used here and are not official warning thresholds. The historical rainfall model predicts recorded rainfall values only and is not a flood model. Unresolved river-level references and rainfall conflicts prevent threshold comparisons.",
    }


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
    for _, row in evidence.iterrows():
        add("Evidence", str(row["Dataset / file"]), {k: row[k] for k in evidence.columns if k != "Dataset / file"})
    if evidence_checklist is not None:
        for index, row in evidence_checklist.iterrows():
            add("Evidence readiness checklist", f"Requirement {index + 1}", row.to_dict())
    for _, row in scenarios.iterrows():
        add("Scenario comparison", str(row["Scenario"]), row.to_dict())
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

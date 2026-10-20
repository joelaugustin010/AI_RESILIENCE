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
    for label, selected_names in combinations.items():
        chosen = actions.loc[actions["Action"].astype(str).isin(selected_names)] if selected_names else actions.iloc[0:0]
        summary = budget_summary(chosen.get("Cost INR", pd.Series(dtype=object)), budget)
        if not selected_names:
            status = "No actions selected"
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
                "Actions selected by user": "; ".join(selected_names) if selected_names else "None",
                "Entered cost total INR": float(summary["entered_total"]),
                "Missing / invalid costs": summary["unknown_or_invalid_count"],
                "Budget remaining INR": float(summary["remaining"]) if summary["remaining"] is not None else None,
                "Budget status": status,
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


def assessment_summary(inputs: dict[str, Any]) -> dict[str, str]:
    """Return a qualified non-numeric status; no unsupported estimates are generated."""
    hazards = expand_hazards(str(inputs.get("hazard", "")))
    joined = ", ".join(hazards) if hazards else str(inputs.get("hazard", "Not selected"))
    return {
        "status": "Insufficient evidence for a reliable numerical prediction",
        "method": "Qualitative evidence review only. The separate historical rainfall measurement benchmark is not used here; no verified local exposure join or validated numerical hazard method is available.",
        "hazards": joined,
        "interpretation": "The submitted values are scenario inputs (observations, forecasts, or assumptions as labelled by the user). The workflow organizes evidence and preparedness questions; it does not estimate probability, severity, depth, casualties, damage, or risk reduction.",
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
    for _, row in evidence.iterrows():
        add("Evidence", str(row["Dataset / file"]), {k: row[k] for k in evidence.columns if k != "Dataset / file"})
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
    add("Data quality", "Rainfall", "Audit found 324 station-time groups with conflicting rainfall values; raw observations remain unchanged.")
    add("Data quality", "River level", "F.C.S. Mananthavadi telemetry has a 701.962 m value change across a 69-day gap; datum/reference is unconfirmed. No correction or threshold comparison was applied.")
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

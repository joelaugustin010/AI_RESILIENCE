"""Connected evidence-to-budget workflow for the AI RESILIENCE prototype."""

from pathlib import Path
import re
import json
import hashlib

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.dataframe_display import display_dataframe

from src.scientific_scenario_engine import build_scientific_scenario_frame
from src.source_registry import build_source_registry, source_fitness_summary
from src.disaster_data_catalog import get_catalog, validate_catalog_record
from src.consequence_data_requirements import HAZARD_REQUIREMENTS, requirements_for_hazard, requirements_table
from src.consequence_assessment import build_consequence_assessment
from src.scenario_input_quality import evaluate_scenario_readiness
from src.scenario_screening import build_scenario_screening
from src.scenario_output_model import HAZARDS as PREDICTABLE_HAZARDS, predict_scenario_outcome

from src.decision_workflow import (
    ASSET_OPTIONS,
    DRAINAGE_STATUS_OPTIONS,
    HAZARD_OPTIONS,
    INFRASTRUCTURE_STATUS_OPTIONS,
    assessment_evidence_matrix,
    assessment_summary,
    build_scenario_comparison,
    budget_summary,
    compare_action_combinations,
    data_quality_confidence_statement,
    decision_readiness_summary,
    evidence_inventory,
    evidence_provenance_summary,
    expand_hazards,
    hazard_evidence_checklist,
    mitigation_actions_for,
    missing_information_register,
    recommendation_candidates,
    recommendation_priority_readiness,
    report_html,
    report_rows,
    validate_workflow_inputs,
)
from src.disaster_models import assess_disaster
from src.prevention_intelligence import generate_prevention_actions
from src.intervention_effectiveness import intervention_effectiveness_for_hazards
from src.ml.presentation import application_rows, model_rows
from src.compound_hazard_assessment import assess_compound_scenario
from src.historical_validation import historical_validation_checklist
from src.disaster_models.drought import parse_monthly_precipitation_csv
from src.hydrology_analytics import (
    DATASETS,
    HydrologyDataError,
    filter_observations,
    load_observations,
    rainfall_station_comparison,
    station_gap_summary,
)
from src.infrastructure_dependencies import dependency_review_table
from src.map_integration import MAP_CONTEXT_KEY, build_map_context, hazard_has_flood_component
from src.ui_theme import research_status_notice, section_intro
from src.evidence_alternatives import alternative_evidence_for_hazard
from src.phase2_data import (
    Phase2DataError,
    Phase2DataUnavailable,
    load_imd_rainfall_cell,
    load_nasa_power,
    load_osm_road_snapshot,
    load_usgs_earthquake_query,
)
from src.rainfall_forecast import RainfallForecastError, run_manual_rainfall_backtest
from src.uncertainty import build_uncertainty_register
from src.population_exposure import PopulationExposureError, estimate_population_exposure
from src.flood_footprint import FloodFootprintError, summarize_flood_depth_geojson


ROOT = Path(__file__).resolve().parents[1]


@st.cache_data(show_spinner="Loading hydrology observations…")
def _cached_hydrology(dataset_id: str):
    return load_observations(dataset_id, ROOT)


@st.cache_data(show_spinner="Evaluating the historical rainfall benchmark…")
def _cached_rainfall_backtest(root: str, source_size: int, source_mtime_ns: int):
    # The file signature is part of the cache key, so a changed source is rechecked.
    return run_manual_rainfall_backtest(root)


def _get_rainfall_backtest():
    path = ROOT / "data" / "raw" / DATASETS["rainfall_manual"].file_name
    try:
        stat = path.stat()
    except OSError as exc:
        raise RainfallForecastError(f"Could not inspect source file {path}: {exc}") from exc
    return _cached_rainfall_backtest(str(ROOT), stat.st_size, stat.st_mtime_ns)


def _snapshot_signature(filename: str) -> tuple[tuple[int, int] | None, ...]:
    path = ROOT / "data" / "raw" / "experimental" / filename
    signature = []
    for candidate in (path, path.with_name(path.name + ".metadata.json")):
        try:
            stat = candidate.stat()
        except FileNotFoundError:
            signature.append(None)
        except OSError as exc:
            raise Phase2DataError(
                f"Could not inspect optional snapshot {candidate}: {exc}"
            ) from exc
        else:
            signature.append((stat.st_size, stat.st_mtime_ns))
    return tuple(signature)


def _assert_snapshot_unchanged(
    filename: str,
    signature: tuple[tuple[int, int] | None, ...],
) -> None:
    if signature != _snapshot_signature(filename):
        raise Phase2DataError(f"Dataset snapshot changed while preparing to load: {filename}")


@st.cache_data(show_spinner=False)
def _cached_phase2_imd(
    root: str,
    year: int,
    _signature: tuple[tuple[int, int] | None, ...],
):
    _assert_snapshot_unchanged(
        f"imd_daily_gridded_rainfall_{year}_025deg.nc",
        _signature,
    )
    return load_imd_rainfall_cell(root, year)


@st.cache_data(show_spinner=False)
def _cached_phase2_nasa(
    root: str,
    _signature: tuple[tuple[int, int] | None, ...],
):
    _assert_snapshot_unchanged(
        "nasa_power_kochi_center_daily_20200101_20250101.json",
        _signature,
    )
    return load_nasa_power(root)


@st.cache_data(show_spinner=False)
def _cached_phase2_osm(
    root: str,
    _signature: tuple[tuple[int, int] | None, ...],
):
    _assert_snapshot_unchanged(
        "openstreetmap_roads_provisional_kochi_bounds.json",
        _signature,
    )
    return load_osm_road_snapshot(root)


@st.cache_data(show_spinner=False)
def _cached_phase2_usgs(
    root: str,
    _signature: tuple[tuple[int, int] | None, ...],
):
    _assert_snapshot_unchanged(
        "usgs_earthquakes_kerala_bbox_1900_present_m0.geojson",
        _signature,
    )
    return load_usgs_earthquake_query(root)


def _render_rainfall_backtest(station: str) -> None:
    """Offer a reproducible, out-of-time benchmark in the existing evidence explorer."""
    with st.expander("Historical rainfall model check (measurement only)", expanded=False):
        st.caption(
            "This evaluates the next recorded manual rainfall amount when consecutive station records are exactly "
            "one hour apart. It is not a current forecast and does not predict flooding."
        )
        if st.button("Run the historical holdout evaluation", key="run_rainfall_backtest"):
            try:
                st.session_state["rainfall_backtest_result"] = _get_rainfall_backtest()
                st.session_state.pop("rainfall_backtest_error", None)
            except (RainfallForecastError, OSError, ValueError) as exc:
                st.session_state["rainfall_backtest_result"] = None
                st.session_state["rainfall_backtest_error"] = str(exc)

        error = st.session_state.get("rainfall_backtest_error")
        if error:
            st.error(f"Backtest unavailable: {error}")
            return
        result = st.session_state.get("rainfall_backtest_result")
        if not result:
            st.info("Run the evaluation to see measured holdout performance. No model is trained during the disaster assessment.")
            return

        summary = result["summary"]
        metrics = result["metrics"]
        st.info(
            "HISTORICAL RECONSTRUCTION — retrospective prediction of the next "
            "source-recorded rainfall value for an exact one-hour station interval. "
            "NOT YET VALIDATED for operational rainfall or flood forecasting."
        )
        metric_rows = [
            {
                "Method": "Persistence (previous hour)",
                "Test pairs": metrics["persistence"]["n"],
                "MAE (mm)": metrics["persistence"]["mae_mm"],
                "RMSE (mm)": metrics["persistence"]["rmse_mm"],
            },
            {
                "Method": "Training station median",
                "Test pairs": metrics["station_median"]["n"],
                "MAE (mm)": metrics["station_median"]["mae_mm"],
                "RMSE (mm)": metrics["station_median"]["rmse_mm"],
            },
            {
                "Method": "Gradient boosting candidate",
                "Test pairs": metrics["gradient_boosting"]["n"],
                "MAE (mm)": metrics["gradient_boosting"]["mae_mm"],
                "RMSE (mm)": metrics["gradient_boosting"]["rmse_mm"],
            },
        ]
        display_dataframe(
            pd.DataFrame(metric_rows), hide_index=True, width="stretch",
            alt="Chronological holdout errors for rainfall persistence, station-median, and gradient-boosting methods",
        )
        st.caption(
            f"Training: {summary['train_pairs']:,} exact one-hour pairs ending before "
            f"{summary['train_end_exclusive']}; test: {summary['test_pairs']:,} pairs from "
            f"{summary['test_period_start']} to {summary['test_period_end']}. A global chronological "
            f"80/20 timestamp split and {summary['embargo_days']}-day embargo were used; "
            f"test coverage is {summary['test_stations']} of {summary['all_stations']} stations."
        )
        st.write("**Per-station holdout metrics**")
        display_dataframe(
            result["per_station"], hide_index=True, width="stretch",
            alt="Per-station rainfall model holdout metrics",
        )
        selected_station = result["predictions"].loc[
            result["predictions"]["station"].eq(station)
        ].copy()
        if selected_station.empty:
            st.info(f"No qualifying one-hour holdout pairs for {station}.")
        else:
            chart = selected_station.set_index("timestamp")[[
                "actual_mm",
                "persistence_prediction_mm",
                "station_median_prediction",
                "model_prediction_mm",
            ]].rename(columns={
                "actual_mm": "Observed rainfall (mm)",
                "persistence_prediction_mm": "Previous-hour baseline (mm)",
                "station_median_prediction": "Training median baseline (mm)",
                "model_prediction_mm": "Gradient-boosting candidate (mm)",
            })
            st.line_chart(chart, height=300, width="stretch")
        for warning in result["warnings"]:
            st.warning(warning)
        st.markdown(
            f"[Manual rainfall source metadata]({DATASETS['rainfall_manual'].source_url})"
        )


def _render_phase2_imd_context(year: int) -> None:
    try:
        rainfall, metadata, summary = _cached_phase2_imd(
            str(ROOT),
            year,
            _snapshot_signature(f"imd_daily_gridded_rainfall_{year}_025deg.nc"),
        )
    except Phase2DataUnavailable as exc:
        st.info(f"IMD rainfall grid unavailable in this checkout: {exc}")
        return
    except Phase2DataError as exc:
        st.error(f"IMD rainfall grid could not be validated: {exc}")
        return

    st.markdown(
        f"**IMD 0.25-degree daily rainfall - {year}.** "
        f"Grid cell center: {summary['grid_cell_center']['latitude']:.2f} N, "
        f"{summary['grid_cell_center']['longitude']:.2f} E; "
        f"{summary['valid_days']} valid days and {summary['missing_days']} missing days. "
        "This is a coarse gridded rainfall series, not a local gauge or flood observation."
    )
    if not rainfall["rainfall_mm"].notna().any():
        st.warning("No valid daily rainfall values are available for this grid cell/year.")
        return

    st.line_chart(
        rainfall.set_index("date")[["rainfall_mm"]].rename(
            columns={"rainfall_mm": "IMD gridded rainfall (mm/day)"}
        ),
        height=260,
        width="stretch",
    )
    peak = rainfall.loc[rainfall["rainfall_mm"].idxmax()]
    st.caption(
        f"Maximum at this selected grid cell: {peak['rainfall_mm']:.2f} mm/day "
        f"on {peak['date'].date().isoformat()}. The selected point is fixed and is not geocoded "
        "from the user-entered assessment area. "
        f"[IMD product information]({metadata['source_url']}). "
        "The source page does not state a data reuse licence; terms require confirmation."
    )


def _render_phase2_nasa_context() -> None:
    try:
        data, metadata, summary = _cached_phase2_nasa(
            str(ROOT),
            _snapshot_signature("nasa_power_kochi_center_daily_20200101_20250101.json"),
        )
    except Phase2DataUnavailable as exc:
        st.info(f"NASA POWER snapshot unavailable in this checkout: {exc}")
        return
    except Phase2DataError as exc:
        st.error(f"NASA POWER snapshot could not be validated: {exc}")
        return

    parameter = st.selectbox(
        "NASA POWER daily variable",
        ["PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "WS10M"],
        format_func=lambda name: f"{name} ({summary['parameter_metadata'][name]['units']})",
        key="phase2_nasa_parameter",
    )
    unit = summary["parameter_metadata"][parameter]["units"]
    st.markdown(
        f"**NASA POWER daily gridded/model-derived data, {summary['start']} to "
        f"{summary['end']}.** Fixed request coordinate: 9.93 N, 76.27 E; "
        f"{summary['row_count']:,} daily records; "
        f"{summary['missing_values_by_parameter'][parameter]} fill/missing values. "
        "Not a station observation or forecast."
    )
    st.line_chart(
        data.set_index("date")[[parameter]].rename(
            columns={parameter: f"{parameter} ({unit})"}
        ),
        height=260,
        width="stretch",
    )
    st.caption(
        f"[NASA POWER API source]({metadata['source_url']}). "
        "No local flood threshold, event impact, or verified station comparison is available."
    )


def _render_phase2_other_context() -> None:
    columns = st.columns(2)
    with columns[0]:
        try:
            metadata, summary = _cached_phase2_osm(
                str(ROOT),
                _snapshot_signature("openstreetmap_roads_provisional_kochi_bounds.json"),
            )
        except Phase2DataUnavailable as exc:
            st.info(f"OpenStreetMap road snapshot unavailable: {exc}")
        except Phase2DataError as exc:
            st.error(f"OpenStreetMap road snapshot could not be validated: {exc}")
        else:
            st.markdown(
                f"**OpenStreetMap road context:** {summary['road_way_count']:,} mapped road ways "
                f"within a provisional bounding box; map snapshot {summary['snapshot_timestamp']}. "
                "This does not establish road condition, passability, hospital access, or flood exposure."
            )
            st.caption(
                f"[OpenStreetMap source query]({metadata['source_url']}). "
                "ODbL attribution and share-alike terms may apply."
            )

    with columns[1]:
        try:
            metadata, summary = _cached_phase2_usgs(
                str(ROOT),
                _snapshot_signature("usgs_earthquakes_kerala_bbox_1900_present_m0.geojson"),
            )
        except Phase2DataUnavailable as exc:
            st.info(f"USGS earthquake query unavailable: {exc}")
        except Phase2DataError as exc:
            st.error(f"USGS earthquake query could not be validated: {exc}")
        else:
            st.markdown(
                f"**USGS catalog query:** {summary['catalogue_event_count']} events returned "
                f"for {summary['time_range']['start']} to {summary['time_range']['end']} "
                f"at magnitude >= {summary['minimum_magnitude']}. "
                "An empty result is not evidence of zero hazard."
            )
            st.caption(f"[USGS query source]({metadata['source_url']}).")


def _render_phase2_data_context() -> None:
    with st.expander("Additional gridded climate and context snapshots", expanded=False):
        st.caption(
            "These optional, research-only snapshots are not automatically joined to the assessment location, "
            "hospital records, flood maps, or one another. A valid checksum establishes byte integrity only."
        )
        year = st.selectbox(
            "IMD daily rainfall grid year",
            [2018, 2021, 2024],
            key="phase2_imd_year",
        )
        if not st.button("Load research-only context snapshots", key="load_phase2_context"):
            st.info("Load the optional data to view their coverage and limitations.")
            return
        _render_phase2_imd_context(year)
        _render_phase2_nasa_context()
        _render_phase2_other_context()


def _render_disaster_assessment(result: dict) -> None:
    st.header("4. Hazard-specific scientific assessment")
    st.caption(
        "This is an observation review or scenario calculation, never a validated prediction. "
        "Only supplied inputs are used; missing exposure and impact evidence stays unavailable. "
        "NOT YET VALIDATED for local predictive use."
    )
    input_classification = result["input_conditions"].get(
        "input_classification", "Unknown / unverified"
    )
    if input_classification == "Hypothetical scenario assumption":
        evidence_label = "SIMULATED SCENARIO"
    elif input_classification == "Historical event (source not independently verified)":
        evidence_label = "HISTORICAL EVENT — SOURCE NOT INDEPENDENTLY VERIFIED"
    elif input_classification == "User-reported observation (source not independently verified)":
        evidence_label = "OBSERVED — USER-REPORTED, NOT INDEPENDENTLY VERIFIED"
    elif input_classification == "Forecast supplied by user (not checked by app)":
        evidence_label = "FORECAST — USER-SUPPLIED, NOT VERIFIED BY THE APP"
    else:
        evidence_label = "INSUFFICIENT EVIDENCE"
    st.write("**Evidence label:**", evidence_label)
    st.write("**Predictive validation:**", "NOT YET VALIDATED")
    st.write("**Assessment type:**", result["assessment_type"])
    st.write("**Model status:**", result["result_status"])
    st.write("**Method:**", result["methodology"]["name"])
    st.write("**Scientific basis:**", result["methodology"]["scientific_basis"])
    st.write("**Hazard assessment:**", result["hazard_assessment"]["severity"])

    indicators = result["hazard_assessment"].get("indicators", {})
    components = result["hazard_assessment"].get("components")
    if components:
        rows = [
            {"Component": name, "Status": component["status"], "Indicators": json.dumps(component["indicators"], ensure_ascii=False, default=str)}
            for name, component in components.items()
        ]
        display_dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", alt="Separate cyclone and flood component indicators")
        st.info("Compound interaction remains unresolved. Component indicators are separate and are not added.")
    elif indicators:
        rows = [
            {"Indicator": key.replace("_", " ").capitalize(), "Result": json.dumps(value, ensure_ascii=False, default=str)}
            for key, value in indicators.items()
        ]
        display_dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", alt="Hazard-specific physical indicators and their user-supplied values")

    consequences = result["potential_consequences"]
    st.write("**Potential consequences:**", consequences["status"])
    st.caption(consequences["human_population"]["interpretation"])
    st.caption(consequences["infrastructure"]["interpretation"])
    category_rows = []
    for name, category in consequences["categories"].items():
        category_rows.append(
            {
                "Consequence category": name.capitalize(),
                "Evidence status": category["status"],
                "Observed impacts": category["observed_impacts"]["status"],
                "Model estimate": category["modelled_estimate"]["status"],
                "Model output": json.dumps(
                    category["modelled_estimate"]["value"],
                    ensure_ascii=False,
                    default=str,
                ),
                "Interpretation": category["modelled_estimate"].get(
                    "interpretation", "No consequence estimate is available."
                ),
                "User-supplied context": json.dumps(
                    category["user_supplied_context"],
                    ensure_ascii=False,
                    default=str,
                ),
                "Evidence required": "; ".join(category["data_requirements"]),
            }
        )
    display_dataframe(
        pd.DataFrame(category_rows),
        hide_index=True,
        width="stretch",
        alt="Evidence-gated human, infrastructure, environmental, and economic consequences",
    )
    st.caption(
        "No observed impacts or modelled consequence values are available here. "
        "User-entered population or asset names are context only, not exposure estimates."
    )
    st.write("**Pathways requiring review:**")
    for pathway in consequences["cascading_or_compound_pathways"]:
        st.markdown(f"- {pathway}")

    columns = st.columns(3)
    phase_labels = {
        "before": "Before: prevention and preparedness",
        "during": "During: response",
        "after": "After: recovery",
    }
    for column, phase in zip(columns, ("before", "during", "after")):
        with column:
            st.markdown(f"**{phase_labels[phase]}**")
            for item in result["recommendations"][phase]:
                st.markdown(f"- **{item['category'].capitalize()}:** {item['action']}")
                st.caption(
                    f"Why relevant: {item['relevance']} Evidence/authority: "
                    f"{item['evidence_or_authority']} Scope: {item['scope']} "
                    f"Limitations: {item['limitations']}"
                )
    with st.expander("Long-term risk reduction and resilience planning"):
        for item in result["recommendations"]["long_term"]:
            st.markdown(f"- {item['action']}")
            st.caption(
                f"Why relevant: {item['relevance']} Evidence/authority: "
                f"{item['evidence_or_authority']} Scope: {item['scope']} "
                f"Limitations: {item['limitations']}"
            )

    with st.expander("Scientific assumptions, uncertainty, data gaps and validation"):
        st.write("**Calculation:**", result["methodology"]["calculation"])
        st.write("**Assumptions:**", result["assumptions"])
        st.write("**Uncertainty:**", result["uncertainty"])
        st.write("**Data gaps:**", result["data_gaps"])
        st.write("**Validation:**", result["validation"])
        st.write("**Evidence-source role:**", result["evidence"]["dataset_use"])
        st.write("**Repository dataset relevance:**")
        for dataset in result["evidence"]["dataset_relevance"]:
            st.markdown(
                f"- **{dataset['dataset']}** (`{dataset['file_or_source']}`): "
                f"{dataset['use_status']}"
            )
        for source in result["evidence"]["sources"]:
            st.markdown(f"- [{source['title']}]({source['url']}) — {source['role']}")



def _render_ml_evidence(evidence: dict) -> None:
    """Render supplementary shared-ML evidence without implying validation."""
    st.markdown("### Shared ML evidence (supplementary)")
    if not evidence:
        st.info("No shared ML evidence block is attached to this assessment.")
        return
    status = str(evidence.get("status", "unknown")).replace("_", " ").capitalize()
    support = str(evidence.get("support_level", "unknown")).replace("_", " ").capitalize()
    st.write("**ML status:**", status)
    st.write("**ML support level:**", support)
    st.caption(evidence.get("interpretation", "No interpretation is available."))
    st.caption(evidence.get("note", ""))

    rows = model_rows(evidence)
    if rows:
        display_dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            width="stretch",
            alt="Registered shared ML models, context completeness, and evidence tier",
        )
    else:
        st.info("No shared ML model is registered for this hazard.")

    applications = application_rows(evidence)
    if applications:
        display_dataframe(
            pd.DataFrame(applications),
            hide_index=True,
            width="stretch",
            alt="Supplementary shared ML model outputs and calibration diagnostics",
        )
        st.warning(
            "Model probability estimates are research outputs for a documented event, "
            "not calibrated probabilities of harm. They do not replace the deterministic "
            "hazard assessment, official warnings, or local verification."
        )
    else:
        st.info(
            "No model output was produced. Missing scenario context or a non-usable model "
            "status prevents a decision output; values are never defaulted or invented."
        )
        for model in evidence.get("models", []):
            missing = (model.get("context") or {}).get("missing_features") or []
            if not missing:
                continue
            with st.expander(
                f"Required context for {model.get('model_id', 'model')} "
                f"({len(missing)} missing feature(s))",
                expanded=False,
            ):
                st.caption(
                    "Supply every field explicitly through an advanced ML context if "
                    "you have a complete, time-matched feature vector. Partial values "
                    "are not filled from unrelated scenario inputs."
                )
                st.code(", ".join(missing), language="text")

    with st.expander("ML limitations and validation boundary"):
        st.write("**Independently validated predictive model available:**", "No")
        st.write("**Validation status:**", "Single temporal holdout; not independently validated.")
        for limitation in evidence.get("limitations", []):
            st.write(f"- {limitation}")


def _compound_scenario_inputs(inputs: dict) -> dict:
    """Adapt shared workflow inputs to the compound evidence review."""
    wind_kmh = inputs.get("wind_speed_kmh")
    wind_knots = float(wind_kmh) / 1.852 if wind_kmh is not None else None
    return {
        "area": inputs.get("location", ""),
        "hazards": ["Flood", "Cyclone"],
        "services": inputs.get("assets", []),
        "evidence_type": inputs.get("input_classification", "Unknown / unverified"),
        "period_start": inputs.get("compound_period_start"),
        "period_end": inputs.get("compound_period_end"),
        "observation_time": inputs.get("compound_observation_time", ""),
        "evidence_source": inputs.get("compound_source_reference", ""),
        "forecast_issue_time": inputs.get("compound_forecast_issue_time", ""),
        "forecast_valid_time": inputs.get("compound_forecast_valid_time", ""),
        "rainfall_mm": inputs.get("rainfall_mm"),
        "rainfall_period": "" if inputs.get("rainfall_period") == "Not supplied" else inputs.get("rainfall_period", ""),
        "rainfall_station_id": inputs.get("compound_rainfall_station_id", ""),
        "rainfall_reference_mm": inputs.get("compound_rainfall_reference_mm"),
        "rainfall_reference_station_id": inputs.get("compound_rainfall_reference_station_id", ""),
        "rainfall_reference_period": inputs.get("compound_rainfall_reference_period", ""),
        "river_level_m": inputs.get("river_level_m"),
        "river_gauge_id": inputs.get("river_station", ""),
        "river_gauge_datum": inputs.get("river_reference", ""),
        "river_reference_level_m": inputs.get("compound_river_reference_level_m"),
        "cyclone_distance_km": inputs.get("compound_cyclone_distance_km"),
        "cyclone_fix_time": inputs.get("compound_cyclone_fix_time", ""),
        "cyclone_storm_id": inputs.get("compound_cyclone_storm_id", ""),
        "cyclone_wind_knots": wind_knots,
        "coastal_water_notes": inputs.get("compound_coastal_water_notes", ""),
    }


def _render_compound_assessment(result: dict) -> None:
    st.subheader("Cyclone + flood evidence review")
    st.warning(
        result["interpretation"],
        title="Scenario review only; compound interaction is not validated",
    )
    st.write("**Evidence context:**", result["evidence_type"])
    st.write("**Source reference:**", result["evidence_source"] or "Not supplied")
    st.write("**Observation time:**", result["observation_time"] or "Not supplied")
    st.write("**Scenario dates:**", f"{result['period_start'] or 'Not supplied'} to {result['period_end'] or 'Not supplied'}")
    display_dataframe(
        pd.DataFrame(result["pathways"]), hide_index=True, width="stretch",
        alt="Separate flood, cyclone, and compound interaction pathways",
    )
    if result["reference_comparisons"]:
        st.markdown("**User-supplied reference comparisons**")
        display_dataframe(
            pd.DataFrame(result["reference_comparisons"]), hide_index=True, width="stretch",
            alt="Rainfall and river readings compared only with user-supplied matched references",
        )
        st.caption("Reference comparisons are conditional arithmetic; independently confirm the source, units, station/gauge, datum, period, and time.")
    else:
        st.caption("No threshold or baseline was assumed. A comparison is withheld when the source, period, station, gauge, or datum does not match.")
    st.markdown("**Critical services and infrastructure to review**")
    for item in result["service_reviews"]:
        with st.expander(item["service"], expanded=False):
            for point in item["review_points"]:
                st.markdown(f"- {point}")
    action_rows = [
        {"Phase": phase.capitalize(), "General preparedness action": action}
        for phase, actions in result["actions"].items()
        for action in actions
    ]
    display_dataframe(
        pd.DataFrame(action_rows), hide_index=True, width="stretch",
        alt="General before, during, and after preparedness actions for cyclone and flood planning",
    )
    st.markdown("**Evidence still required**")
    display_dataframe(
        pd.DataFrame({"Missing or unverified evidence": result["data_gaps"]}),
        hide_index=True, width="stretch",
        alt="Evidence gaps that prevent a validated cyclone and flood assessment",
    )
    st.caption("The component indicators are not added. No joint probability, flood depth, affected population, casualties, damage, or predictive accuracy is reported.")

def _render_hydrology_explorer() -> None:
    """Show raw station trends and separately sourced event context."""
    with st.expander("Explore measured rainfall and river-level observations", expanded=False):
        st.caption(
            "The observation charts are descriptive; the separate rainfall benchmark below is a historical measurement model, not a flood forecast. "
            "Each plotted point is one source row: no values are deduplicated, interpolated, or aggregated. "
            "Source time zones are undocumented."
        )
        dataset_id = st.selectbox(
            "Observation dataset",
            list(DATASETS),
            format_func=lambda item: DATASETS[item].label,
            key="hydrology_dataset",
        )
        spec = DATASETS[dataset_id]
        try:
            observations, qa = _cached_hydrology(dataset_id)
        except (HydrologyDataError, OSError) as exc:
            st.error(f"This dataset cannot be displayed: {exc}")
            return

        if observations.empty:
            st.warning("No valid timestamped measurements are available in this file.")
            return

        st.caption(
            f"Source file: `data/raw/{spec.file_name}` · {qa['raw_rows']:,} rows · "
            f"{qa['station_count']} stations · valid row dates {qa['start'][:10]} to {qa['end'][:10]} · unit {spec.unit}. "
            f"{spec.source_note}"
        )
        st.markdown(f"[Official NWDP resource metadata]({spec.source_url})")
        # Detailed dataset QA warnings are kept out of the user-facing explorer.
        if qa["invalid_timestamp_rows"] or qa["invalid_measurement_rows"]:
            st.warning(
                f"Chart excludes {qa['invalid_timestamp_rows']} rows with invalid timestamps and "
                f"{qa['invalid_measurement_rows']} rows with invalid measurements; source files remain unchanged."
            )
        stations = sorted(observations["station"].unique().tolist())
        station = st.selectbox("Station", stations, key=f"hydrology_station_{dataset_id}")
        station_data = observations.loc[observations["station"].eq(station)]
        if "district" in station_data:
            districts = sorted(station_data["district"].dropna().unique().tolist())
            district_text = ", ".join(districts) if districts else "not recorded"
            st.caption(f"Source-reported district: {district_text}. Station coordinates and district metadata are not independently validated here.")
        minimum = station_data["timestamp"].min().date()
        maximum = station_data["timestamp"].max().date()
        date_range = st.date_input(
            "Date range",
            value=(minimum, maximum),
            min_value=minimum,
            max_value=maximum,
            key=f"hydrology_dates_{dataset_id}_{station}",
        )
        if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
            start_date, end_date = date_range
        elif isinstance(date_range, (tuple, list)) and len(date_range) == 1:
            start_date = end_date = date_range[0]
        else:
            start_date = end_date = date_range
        selected = filter_observations(observations, station, start_date, end_date)
        if selected.empty:
            st.info("No source measurements fall inside the selected date range.")
        else:
            gaps = station_gap_summary(selected)
            stat_cols = st.columns(4)
            stat_cols[0].metric("Source rows shown", f"{len(selected):,}")
            stat_cols[1].metric("Median recorded value", f"{selected['value'].median():.3f} {spec.unit}")
            stat_cols[2].metric("Maximum recorded value", f"{selected['value'].max():.3f} {spec.unit}")
            stat_cols[3].metric(
                "Largest observed gap",
                "Not available" if gaps["maximum_observed_gap_hours"] is None else f"{gaps['maximum_observed_gap_hours']:,.1f} h",
            )
            st.scatter_chart(
                selected,
                x="timestamp",
                y="value",
                x_label="Source timestamp (timezone not stated)",
                y_label=f"{spec.measurement_column} ({spec.unit})",
                height=320,
                width="stretch",
            )
            st.caption(
                "The largest gap is the longest interval between rows present in this selection. "
                "It is not a count of missing observations because the expected sampling schedule is not documented."
            )
            st.caption("Extrema are raw reported values; the application has not independently quality-approved each reading.")

        if spec.mode == "rainfall" and qa["duplicate_station_time_groups"] == 0:
            st.markdown("**Station comparison (raw recorded values)**")
            display_dataframe(rainfall_station_comparison(observations), hide_index=True, width="stretch")
            st.caption("Stations share the mm unit. Uneven time coverage means the table compares recorded samples, not complete-period rainfall totals.")
            if dataset_id == "rainfall_manual":
                _render_rainfall_backtest(station)
        elif spec.mode == "river":
            st.info(
                "River-level metres are shown as source-reported values. Gauge zero/datum conventions and "
                "official local thresholds are not verified, so the chart cannot be read as a danger scale. "
                "Absolute values across stations are not compared."
            )

        event_path = ROOT / "data" / "reference" / "historical_flood_events.json"
        try:
            events = json.loads(event_path.read_text(encoding="utf-8"))["events"]
        except (OSError, ValueError, KeyError):
            events = []
        st.markdown("**Documented historical context**")
        for event in events:
            st.markdown(
                f"- **{event['title']}** ({event['period_start']} to {event['period_end']}): "
                f"{event['evidence']} [Source: {event['source_title']}]({event['source_url']}).  \n"
                f"  *Relationship to this data:* {event['relationship_to_local_observations']}"
            )
            start = pd.Timestamp(event["period_start"])
            end = pd.Timestamp(event["period_end"]) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1)
            overlap_count = int(selected["timestamp"].between(start, end).sum()) if not selected.empty else 0
            if overlap_count:
                st.caption(
                    f"Selected station/date filter contains {overlap_count:,} source row(s) during this "
                    "state-level event period. These rows are not labeled as flood outcomes by the event record."
                )
        st.caption("Data-source and limitation register: `data/reference/hydrology_data_sources.json`.")


st.markdown("""
<style>
.wf-hero{position:relative;overflow:hidden;padding:clamp(1.6rem,3vw,2.4rem) clamp(1.4rem,3vw,2.6rem);border-radius:26px;color:#f8fafc;background:linear-gradient(90deg,rgba(4,18,28,.95),rgba(7,35,47,.70) 58%,rgba(7,34,43,.84)),radial-gradient(ellipse at 92% -10%,rgba(66,224,193,.18),transparent 24rem),url('app/static/images/hero-kerala-flood-road.jpg') center/cover no-repeat;border:1px solid rgba(120,220,208,.24);box-shadow:0 24px 60px rgba(2,12,20,.34);margin:.2rem 0 1.1rem;isolation:isolate}
.wf-hero:before{content:"";position:absolute;z-index:-1;width:280px;height:280px;right:-100px;top:-160px;border-radius:50%;border:1px solid rgba(66,224,193,.30);box-shadow:0 0 0 28px rgba(66,224,193,.05),0 0 0 58px rgba(66,224,193,.03);pointer-events:none}
.wf-hero:after{content:"";position:absolute;inset:0 auto auto 0;width:100%;height:3px;background:linear-gradient(90deg,#42e0c1,transparent 62%);opacity:.85}
.wf-kicker{display:inline-flex;align-items:center;gap:.55rem;font-size:.71rem;letter-spacing:.16em;text-transform:uppercase;font-weight:800;color:#8cf3df;margin-bottom:.7rem}
.wf-kicker:before{content:"";width:.5rem;height:.5rem;border-radius:50%;background:#42e0c1;box-shadow:0 0 0 4px rgba(66,224,193,.16);animation:arSoftPulse 2.8s ease-in-out infinite}
.wf-title{font-size:clamp(2rem,3.5vw,3.15rem);font-weight:820;letter-spacing:-.045em;line-height:1.05;color:#f6ffff;margin:0 0 .75rem}
.wf-copy{max-width:850px;color:#c8dfe2;font-size:clamp(.95rem,1.15vw,1.04rem);line-height:1.68;margin:0}
.wf-steps{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:.6rem;margin:1rem 0 1.4rem}
.wf-step{border:1px solid rgba(23,78,85,.16);background:linear-gradient(150deg,#FFFFFF,#DCE7E8);border-radius:15px;padding:.9rem 1rem;color:#52666A;font-size:.8rem;line-height:1.5;box-shadow:0 8px 22px rgba(23,78,85,.06);transition:transform .2s var(--ar-ease),border-color .2s var(--ar-ease),box-shadow .2s var(--ar-ease)}
.wf-step:hover{transform:translateY(-2px);border-color:rgba(41,155,145,.34);box-shadow:0 12px 28px rgba(23,78,85,.10)}
.wf-step strong{display:block;color:#174E55;font-size:.9rem;margin-bottom:.22rem;letter-spacing:-.01em}
@media(max-width:900px){.wf-steps{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:520px){.wf-steps{grid-template-columns:1fr}.wf-hero{padding:1.3rem;border-radius:18px}}
@media(prefers-reduced-motion:reduce){.wf-step:hover{transform:none}.wf-kicker:before{animation:none}}
</style>
<section class="wf-hero">
<div class="wf-kicker">AI RESILIENCE · KOCHI · PLANNING WORKSPACE</div>
<div class="wf-title">Disaster decision workflow</div>
<p class="wf-copy">Turn a clearly described scenario into an evidence checklist, compare possible preparedness actions, review budget arithmetic, and export a traceable report. The workflow supports planning—not official warnings or validated predictions.</p>
</section>
<div class="wf-steps">
<div class="wf-step"><strong>01 · Describe</strong>Choose hazard and area</div>
<div class="wf-step"><strong>02 · Review</strong>Check inputs and evidence</div>
<div class="wf-step"><strong>03 · Assess</strong>Understand missing proof</div>
<div class="wf-step"><strong>04 · Plan</strong>Compare actions and costs</div>
<div class="wf-step"><strong>05 · Export</strong>Keep a report record</div>
</div>
""", unsafe_allow_html=True)
st.caption("A historical rainfall measurement benchmark is available in the evidence explorer. It is separate from the assessment and is not a current rainfall or flood forecast.")
nav_left, nav_right = st.columns(2)
with nav_left:
    st.page_link(
        ROOT / "app_pages" / "compound_scenario.py",
        label="Open Cyclone + Flood workspace",
        icon=":material/thunderstorm:",
        width="stretch",
    )
with nav_right:
    st.page_link(
        ROOT / "app_pages" / "kochi_map.py",
        label="Open Kochi hazard map",
        icon=":material/map:",
        width="stretch",
    )
st.info(
    "Kochi evidence update: JRC 100-year river-flood depth tiles are licensed (ODbL 1.0 applied; CC BY 4.0 also stated) and displayed on the map as modelled scenario context with attribution. They are not observed flooding or an official warning. "
    "Operational asset-level flood exposure remains unavailable because there is no independently validated hospital or critical-facility location layer. "
    "See the map for source details and the broader data gaps."
)
with st.expander("Longer-term AI RESILIENCE roadmap"):
    st.markdown(
        "- **Pollution sources:** combine pollutant-specific station observations, weather, and verified facility/emissions records; AQI alone cannot identify a factory.\n"
        "- **Local hazard validation:** connect the screening models below to verified location/time-specific observations, exposure layers, local thresholds, and independently reviewed impacts.\n"
        "- **Historical-event-informed preparedness:** use sourced event records and documented impacts before estimating likelihoods or consequences.\n"
        "- **Budget prioritisation:** compare documented intervention costs and defensible outcome evidence; leave benefits unquantified when evidence is missing."
    )

_render_phase2_data_context()
_render_hydrology_explorer()

# Preserve the semantic page title for screen readers and existing Streamlit
# integrations while the visible workflow uses the richer hero/section system.
st.markdown(
    "<style>.st-key-wf-semantic-title{position:absolute!important;width:1px!important;height:1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;}</style>",
    unsafe_allow_html=True,
)
with st.container(key="wf-semantic-title"):
    st.title("Unified disaster decision workflow")
research_status_notice("Decision Workflow · ten-scenario evidence review")

section_intro(
    "Start here",
    "1. Select a hazard and describe conditions",
    "Capture the scenario context first. The workflow keeps user-supplied conditions separate from verified evidence and model outputs.",
)
# Keep the hazard selector outside the form so Streamlit reruns immediately when
# the user changes hazards; the visible inputs then update before submission.
hazard = st.selectbox("Hazard or compound scenario", HAZARD_OPTIONS, key="wf_hazard")

# A result belongs to the hazard it was submitted for.  When the selector
# changes, discard the stored submission and the map context so an old
# assessment can never appear beneath a newly selected hazard.
_PREVIOUS_HAZARD_KEY = "wf_previous_hazard"
if _PREVIOUS_HAZARD_KEY not in st.session_state:
    # First visit in this session: remember the selection without discarding a
    # result that is being restored after navigating away and back.
    st.session_state[_PREVIOUS_HAZARD_KEY] = hazard
elif st.session_state[_PREVIOUS_HAZARD_KEY] != hazard:
    st.session_state[_PREVIOUS_HAZARD_KEY] = hazard
    st.session_state["decision_workflow_inputs"] = None
    st.session_state.pop(MAP_CONTEXT_KEY, None)

with st.form("decision_workflow_intake"):
    location = st.text_input(
        "Location or area name",
        value="Kochi Municipal Corporation — area not specified",
        help="Enter an area name; do not guess coordinates. The map currently has only a provisional corporation outline.",
        key="wf_location",
    )
    input_classification = st.selectbox(
        "How should these conditions be treated?",
        [
            "Hypothetical scenario assumption",
            "Historical event (source not independently verified)",
            "User-reported observation (source not independently verified)",
            "Forecast supplied by user (not checked by app)",
            "Unknown / unverified",
        ],
        key="wf_classification",
    )
    source_and_time = st.text_area(
        "Source, observation/forecast time, and units (if known)",
        key="wf_source_time",
        height=90,
        placeholder="Example: IMD bulletin; issued 31 Oct 2026, 10:00 IST; valid until 31 Oct 2026, 20:30 IST; wind in km/h; station/area: Kochi.",
        help="Enter the provider/source, observation time or forecast issue and valid times, timezone, station/area, units, and averaging period where known. Leave unknown details blank. This app does not independently verify the entry.",
    )

    # Show only fields relevant to the selected hazard. Keep hidden fields explicitly
    # unset so stale values from a previous selection cannot influence this assessment.
    show_rainfall = hazard in {
        "Flood", "Cyclone", "Landslide", "Drought",
        "Compound: cyclone + flood",
        "Compound: heavy rainfall + drainage failure",
    }
    show_river = hazard in {"Flood", "Compound: cyclone + flood"}
    show_wind = hazard in {"Cyclone", "Compound: cyclone + flood"}
    show_temperature = hazard == "Heatwave"
    show_drainage = hazard in {
        "Flood", "Compound: cyclone + flood",
        "Compound: heavy rainfall + drainage failure",
    }
    show_earthquake = hazard == "Earthquake"
    show_landslide = hazard == "Landslide"
    show_drought = hazard == "Drought"
    show_industrial = hazard == "Industrial incident"
    show_infrastructure = hazard == "Infrastructure failure"
    show_population = hazard in {
        "Flood", "Cyclone", "Earthquake", "Landslide", "Heatwave",
        "Drought", "Industrial incident", "Infrastructure failure",
        "Compound: cyclone + flood",
        "Compound: heavy rainfall + drainage failure",
    }

    # Hazard-specific inputs are optional context, not validated model inputs.
    earthquake_magnitude = None
    earthquake_depth_km = None
    slope_condition = "Not supplied"
    soil_condition = "Not supplied"
    drought_indicator = "Not supplied"
    water_supply_status = "Not supplied"
    industrial_substance = ""
    industrial_release_status = "Not supplied"
    industrial_wind_direction = ""
    failed_asset_type = "Not supplied"
    failure_status = "Not supplied"

    rainfall_mm = None
    rainfall_period = "Not supplied"
    river_level_m = None
    river_station = ""
    river_reference = ""
    wind_speed_kmh = None
    temperature_c = None
    normal_max_temperature_c = None
    heatwave_consecutive_days = None
    heatwave_station_count = None
    affected_population = None
    drainage_status = "Not supplied"
    infrastructure_status = "Not supplied"

    st.caption("Only fields relevant to the selected hazard are shown. Empty means not supplied; the app does not fill in values.")
    col1, col2 = st.columns(2)
    with col1:
        if show_rainfall:
            st.markdown("**Rainfall evidence**")
            rainfall_mm = st.number_input("Rainfall (mm)", min_value=0.0, value=None, step=1.0, key="wf_rainfall")
            rainfall_period = st.selectbox("Rainfall period", ["Not supplied", "Last 1 hour", "Last 24 hours", "Last 3 days", "Other / state in notes"], key="wf_rainfall_period")
        if show_river:
            st.markdown("**River evidence**")
            river_level_m = st.number_input("River-level reading (m)", value=None, step=0.1, key="wf_river", help="Gauge readings can be below zero depending on the reference datum. The app does not compare this with a threshold.")
            river_station = st.text_input("River station (if applicable)", key="wf_river_station")
            river_reference = st.text_input("Gauge zero / datum reference (if known)", key="wf_river_reference")
        if show_wind:
            wind_speed_kmh = st.number_input("Wind speed (km/h)", min_value=0.0, value=None, step=1.0, key="wf_wind")
        if show_drainage:
            drainage_status = st.selectbox("Drainage condition", ["Not supplied", "Reported functioning", "Reported partially impaired", "Reported failed", "Hypothetical partial failure", "Not applicable"], key="wf_drainage")
        if show_landslide:
            st.markdown("**Slope and ground evidence**")
            slope_condition = st.selectbox("Slope condition", ["Not supplied", "Stable / no movement reported", "Cracks or movement reported", "Recent slope failure reported", "Unknown"], key="wf_slope")
            soil_condition = st.selectbox("Ground / soil condition", ["Not supplied", "Dry", "Saturated / waterlogged", "Loose / disturbed", "Unknown"], key="wf_soil")
        if show_drought:
            st.markdown("**Drought and water-supply evidence**")
            drought_indicator = st.selectbox("Drought indicator", ["Not supplied", "SPI", "SPEI", "Standardised soil-moisture index", "Official drought category", "Other / specify in notes"], key="wf_drought_indicator")
            water_supply_status = st.selectbox("Water supply status", ["Not supplied", "Normal", "Restricted", "Severely disrupted", "Unknown"], key="wf_water_supply")
        if show_earthquake:
            st.markdown("**Earthquake evidence**")
            earthquake_magnitude = st.number_input("Reported magnitude (Mw; if sourced)", min_value=0.0, max_value=10.0, value=None, step=0.1, key="wf_eq_magnitude")
            earthquake_depth_km = st.number_input("Reported focal depth (km; if sourced)", min_value=0.0, max_value=800.0, value=None, step=1.0, key="wf_eq_depth")
        if show_industrial:
            st.markdown("**Industrial incident evidence**")
            industrial_substance = st.text_input("Substance or material involved (if known)", key="wf_industrial_substance")
            industrial_release_status = st.selectbox("Release / incident status", ["Not supplied", "Suspected", "Reported by user", "Confirmed by cited authority", "No release reported", "Unknown"], key="wf_industrial_status")
            industrial_wind_direction = st.text_input("Wind direction / weather context (if known)", key="wf_industrial_wind")
        if show_infrastructure:
            st.markdown("**Infrastructure failure evidence**")
            failed_asset_type = st.selectbox("Asset type", ["Not supplied", "Road / bridge", "Electricity", "Drinking water", "Communications", "Drainage", "Building", "Other"], key="wf_failed_asset")
            failure_status = st.selectbox("Failure status", ["Not supplied", "Suspected", "Reported by user", "Confirmed by cited authority", "Hypothetical", "Unknown"], key="wf_failure_status")
        if hazard in {"Flood", "Cyclone", "Earthquake", "Infrastructure failure", "Compound: cyclone + flood", "Compound: heavy rainfall + drainage failure"}:
            infrastructure_status = st.selectbox("Other infrastructure condition", ["Not supplied", "No disruption reported", "Possible / hypothetical disruption", "Disruption reported by user", "Not applicable"], key="wf_infrastructure")
    with col2:
        if show_temperature:
            st.markdown("**Heatwave evidence**")
            temperature_c = st.number_input("Maximum temperature (°C)", value=None, step=0.5, key="wf_temperature")
            normal_max_temperature_c = st.number_input("Normal daily maximum for this station (°C; heatwave screening)", value=None, step=0.5, key="wf_normal_temperature", help="Use an official station normal for the relevant date/period; leave blank if unknown.")
            heatwave_consecutive_days = st.number_input("Consecutive days meeting the heatwave criteria (if verified)", min_value=0, value=None, step=1, key="wf_heatwave_days")
            heatwave_station_count = st.number_input("Stations in the meteorological subdivision meeting criteria (if verified)", min_value=0, value=None, step=1, key="wf_heatwave_stations")
        if show_population:
            affected_population = st.number_input("Affected population context (people; optional)", min_value=0, value=None, step=1, key="wf_population")

    model_inputs = {}
    if hazard == "Heatwave":
        model_inputs["relative_humidity_percent"] = st.number_input(
            "Relative humidity (%)",
            min_value=0.0,
            max_value=100.0,
            value=None,
            key="wf_relative_humidity",
        )
    if hazard == "Earthquake":
        model_inputs["earthquake_mmi"] = st.selectbox(
            "Reported Modified Mercalli Intensity (MMI)",
            ["Not supplied", *range(1, 13)],
            key="wf_earthquake_mmi",
            help="Enter an official or field-reported intensity only; the app does not estimate shaking.",
        )
    if hazard == "Landslide":
        model_inputs["antecedent_rainfall_mm"] = st.number_input(
            "Antecedent rainfall total (mm; optional)",
            min_value=0.0,
            value=None,
            key="wf_antecedent_rainfall",
        )
    if hazard == "Drought":
        model_inputs["monthly_precipitation_csv"] = st.text_area(
            "Optional monthly precipitation history CSV",
            placeholder="month,precipitation_mm\n1991-01,123.4\n1991-02,45.6",
            height=110,
            key="wf_drought_monthly_csv",
            help="One location, consecutive monthly totals in mm, and at least 30 complete years are required for SPI-1. Values are not authenticated.",
        )
    if hazard == "Industrial incident":
        with st.expander("Optional pollutant measurement comparison"):
            model_inputs["pollutant_name"] = st.text_input("Pollutant name", key="wf_pollutant_name")
            model_inputs["pollutant_concentration"] = st.number_input(
                "Measured concentration",
                min_value=0.0,
                value=None,
                key="wf_pollutant_concentration",
            )
            model_inputs["pollutant_unit"] = st.selectbox(
                "Measurement unit",
                ["Not supplied", "µg/m³", "mg/m³", "ppm", "ppb"],
                key="wf_pollutant_unit",
            )
            model_inputs["pollutant_averaging_period"] = st.selectbox(
                "Observation averaging period",
                ["Not supplied", "1-hour", "8-hour", "24-hour", "annual"],
                key="wf_pollutant_period",
            )
            model_inputs["pollutant_reference_value"] = st.number_input(
                "Applicable reference value (optional)",
                min_value=0.0,
                value=None,
                key="wf_pollutant_reference",
                help="Supply a documented pollutant-, unit- and averaging-period-matched reference; no benchmark is assumed.",
            )
            model_inputs["pollutant_reference_unit"] = st.selectbox(
                "Reference unit",
                ["Not supplied", "µg/m³", "mg/m³", "ppm", "ppb"],
                key="wf_pollutant_reference_unit",
            )
            model_inputs["pollutant_reference_averaging_period"] = st.selectbox(
                "Reference averaging period",
                ["Not supplied", "1-hour", "8-hour", "24-hour", "annual"],
                key="wf_pollutant_reference_period",
            )
    if hazard in {"Flood", "Compound: heavy rainfall + drainage failure"}:
        with st.expander("Optional catchment inputs for Rational Method screening"):
            model_inputs["catchment_area_ha"] = st.number_input(
                "Catchment area (hectares)",
                min_value=0.0,
                value=None,
                key="wf_catchment_area",
            )
            model_inputs["runoff_coefficient"] = st.number_input(
                "Runoff coefficient C (0-1)",
                min_value=0.0,
                max_value=1.0,
                value=None,
                key="wf_runoff_coefficient",
            )
            if hazard == "Compound: heavy rainfall + drainage failure":
                model_inputs["drainage_capacity_m3_s"] = st.number_input(
                    "Drainage design capacity (m³/s)",
                    min_value=0.0,
                    value=None,
                    key="wf_drainage_capacity",
                )
    if hazard == "Infrastructure failure":
        model_inputs["failed_service"] = st.text_input(
            "Service or infrastructure failure mode",
            key="wf_failed_service",
        )

    compound_context_inputs = {}
    if hazard == "Compound: cyclone + flood":
        st.markdown("**Cyclone + flood timing and evidence**")
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            compound_period_start = st.date_input("Scenario start date (optional)", value=None, key="wf_compound_period_start")
        with date_col2:
            compound_period_end = st.date_input("Scenario end date (optional)", value=None, key="wf_compound_period_end")
        compound_source_reference = st.text_input(
            "Compound source URL, bulletin ID, or document reference",
            key="wf_compound_source",
            help="A source reference is not independently checked by this app.",
        )
        compound_observation_time = st.text_input(
            "Observation or event time, including timezone", key="wf_compound_observation_time"
        )
        time_col1, time_col2 = st.columns(2)
        with time_col1:
            compound_forecast_issue_time = st.text_input("Forecast issue time (if applicable)", key="wf_compound_forecast_issue")
        with time_col2:
            compound_forecast_valid_time = st.text_input("Forecast valid time (if applicable)", key="wf_compound_forecast_valid")
        flood_col1, flood_col2 = st.columns(2)
        with flood_col1:
            compound_rainfall_station_id = st.text_input("Rainfall station ID", key="wf_compound_rain_station")
            compound_rainfall_reference_mm = st.number_input(
                "Documented rainfall reference (mm; optional)", min_value=0.0, value=None,
                key="wf_compound_rain_reference",
                help="Compared only when its station and accumulation period exactly match the observation.",
            )
            compound_rainfall_reference_station_id = st.text_input("Reference station ID", key="wf_compound_rain_reference_station")
            compound_rainfall_reference_period = st.text_input("Reference accumulation period", key="wf_compound_rain_reference_period")
        with flood_col2:
            compound_river_reference_level_m = st.number_input(
                "Documented river reference level (m; optional)", value=None, step=0.1,
                key="wf_compound_river_reference",
                help="No warning threshold is assumed; comparison requires the same gauge and datum above.",
            )
            compound_cyclone_distance_km = st.number_input(
                "Cyclone track distance from the study area (km; optional)", min_value=0.0,
                value=None, step=1.0, key="wf_compound_cyclone_distance",
            )
            compound_cyclone_fix_time = st.text_input("Cyclone track-fix time and timezone", key="wf_compound_cyclone_fix")
            compound_cyclone_storm_id = st.text_input("Cyclone storm ID or name", key="wf_compound_storm_id")
        st.caption("Wind speed uses the shared intake above in km/h. The evidence review converts units to knots using 1 knot = 1.852 km/h; this is unit conversion only, not a forecast.")
        compound_coastal_water_notes = st.text_area(
            "Coastal water, tide, surge, or outfall evidence (optional)",
            key="wf_compound_coastal_notes",
        )
        compound_context_inputs = {
            "compound_period_start": compound_period_start,
            "compound_period_end": compound_period_end,
            "compound_source_reference": compound_source_reference,
            "compound_observation_time": compound_observation_time,
            "compound_forecast_issue_time": compound_forecast_issue_time,
            "compound_forecast_valid_time": compound_forecast_valid_time,
            "compound_rainfall_station_id": compound_rainfall_station_id,
            "compound_rainfall_reference_mm": compound_rainfall_reference_mm,
            "compound_rainfall_reference_station_id": compound_rainfall_reference_station_id,
            "compound_rainfall_reference_period": compound_rainfall_reference_period,
            "compound_river_reference_level_m": compound_river_reference_level_m,
            "compound_cyclone_distance_km": compound_cyclone_distance_km,
            "compound_cyclone_fix_time": compound_cyclone_fix_time,
            "compound_cyclone_storm_id": compound_cyclone_storm_id,
            "compound_coastal_water_notes": compound_coastal_water_notes,
        }

    assets = st.multiselect(
        "Services or assets to review (user-nominated; location/exposure not verified)",
        ASSET_OPTIONS,
        default=["Hospitals", "Roads and bridges"],
        key="wf_assets",
    )
    condition_notes = st.text_area("Other conditions, sequence, or assumptions", key="wf_notes")
    submitted = st.form_submit_button("Review evidence and build the workflow", type="primary")

if submitted:
    submitted_inputs = {
        "hazard": hazard,
        "location": location,
        "input_classification": input_classification,
        "source_and_time": source_and_time,
        "rainfall_mm": rainfall_mm,
        "rainfall_period": rainfall_period if rainfall_mm is not None else "Not supplied",
        "river_level_m": river_level_m,
        "river_station": river_station,
        "river_reference": river_reference,
        "wind_speed_kmh": wind_speed_kmh,
        "temperature_c": temperature_c,
        "normal_max_temperature_c": normal_max_temperature_c,
        "heatwave_consecutive_days": heatwave_consecutive_days,
        "heatwave_station_count": heatwave_station_count,
        "earthquake_magnitude": earthquake_magnitude,
        "earthquake_depth_km": earthquake_depth_km,
        "slope_condition": slope_condition,
        "soil_condition": soil_condition,
        "drought_indicator": drought_indicator,
        "water_supply_status": water_supply_status,
        "industrial_substance": industrial_substance,
        "industrial_release_status": industrial_release_status,
        "industrial_wind_direction": industrial_wind_direction,
        "failed_asset_type": failed_asset_type,
        "failure_status": failure_status,
        "affected_population": affected_population,
        "drainage_status": drainage_status,
        "infrastructure_status": infrastructure_status,
        "assets": assets,
        "condition_notes": condition_notes,
        **compound_context_inputs,
        **model_inputs,
    }
    if submitted_inputs["hazard"] == "Earthquake" and submitted_inputs.get("earthquake_mmi") == "Not supplied":
        submitted_inputs["earthquake_mmi"] = None
    for field in ("pollutant_unit", "pollutant_reference_unit"):
        if submitted_inputs.get(field) == "Not supplied":
            submitted_inputs[field] = ""
    for field in ("pollutant_averaging_period", "pollutant_reference_averaging_period"):
        if submitted_inputs.get(field) == "Not supplied":
            submitted_inputs[field] = ""
    problems = validate_workflow_inputs(submitted_inputs)
    if submitted_inputs["hazard"] == "Drought" and submitted_inputs.get("monthly_precipitation_csv", "").strip():
        try:
            submitted_inputs["monthly_precipitation_records"] = parse_monthly_precipitation_csv(
                submitted_inputs["monthly_precipitation_csv"]
            )
        except ValueError as exc:
            problems.append(str(exc))
    if problems:
        st.session_state["decision_workflow_inputs"] = None
        for problem in problems:
            st.error(problem)
    else:
        st.session_state["decision_workflow_inputs"] = submitted_inputs
        # Any previously generated map context belongs to the previous result.
        st.session_state.pop(MAP_CONTEXT_KEY, None)

inputs = st.session_state.get("decision_workflow_inputs")
if inputs is None:
    # Keep the page focused on the scenario form until the user submits it.
    # The evidence inventory is shown in the results section after submission.
    st.stop()

st.header("2. Immediate scenario result")
try:
    disaster_assessment = assess_disaster(inputs)
except ValueError as exc:
    disaster_assessment = None
    st.error(f"Hazard-specific assessment input error: {exc}")
else:
    _render_ml_evidence(disaster_assessment.get("ml_evidence", {}))

st.caption(
    "Your submitted hypothetical values are assessed here first. This output explains conditional consequences and, " 
    "where an official threshold applies, the corresponding screening category. It is not a calibrated flood probability, " 
    "flood-depth estimate, affected-area map, or official warning."
)
prediction = predict_scenario_outcome(inputs)
if prediction.get("input_validation", {}).get("valid") is False:
    st.error("Scenario assessment blocked: correct the invalid measurements below, then rerun the assessment.")
    for problem in prediction["input_validation"].get("problems", []):
        st.write(f"**{problem['field']}** — {problem['message']}")
st.subheader("Conditional scenario output")
st.metric("Scenario concern", prediction["concern_level"])
st.markdown("**Potential outcome**")
st.write(prediction["conditional_outcome"])
st.caption(f"Scenario engine: {prediction['model_type']}. This immediate conditional outcome is rule-based; it is not the output of a trained ML model. Separate shared-ML inference is displayed below when a registered model's complete feature contract and evidence gates are satisfied. No official warning is produced.")
with st.expander("Why the model produced this output", expanded=True):
    st.markdown("**Evidence used**")
    for item in prediction["evidence_used"]:
        st.markdown(f"- {item}")
    st.markdown("**Recommended verification / next checks**")
    for item in prediction["recommended_checks"]:
        st.markdown(f"- {item}")
    st.markdown("**Basis and limitations**")
    st.write(prediction["basis"])
    for item in prediction["limitations"]:
        st.caption(f"• {item}")

scenario_screen = build_scenario_screening(inputs)
display_dataframe(scenario_screen, hide_index=True, width="stretch")

st.header("3. Review evidence")
evidence = evidence_inventory(ROOT, st.session_state.get("rainfall_backtest_result"))
st.caption("The separate historical benchmark uses only the manual rainfall observations. Its results do not enter this qualitative assessment; conflicted CWC rainfall, unverified sample rows, and unresolved river levels remain excluded from model calculations.")
display_dataframe(evidence, hide_index=True, width="stretch")

with st.expander("Dataset provenance and scientific fitness register", expanded=True):
    st.caption(
        "A listed source is not automatically suitable for every claim. Unknown licence, time-zone, "
        "datum, checksum, or spatial metadata stays unresolved; this register does not certify data."
    )
    registry = build_source_registry()
    registry_view = []
    for record in registry:
        fitness = source_fitness_summary(record)
        registry_view.append({
            "Dataset": record["name"],
            "Publisher / source attribution": record["publisher"],
            "Observation type": record["data_type"],
            "Unit": record["unit"],
            "Retrieval date": record["retrieval_date"],
            "Licence status": record["license_status"],
            "Checksum match": record["checksum_match"],
            "Time zone": record["time_zone"],
            "Spatial reference / datum": record["spatial_reference"],
            "Validation status": record["validation_status"],
            "Scientific fitness": fitness["scientific_fitness"],
            "Permitted use": record["permitted_use"],
            "Known limitation": record["known_limitation"],
            "Source URL": record["source_url"],
        })
    display_dataframe(pd.DataFrame(registry_view), hide_index=True, width="stretch")
    st.warning(
        "No dataset in this registry is approved by this app for numerical disaster prediction or official warnings. "
        "Source metadata completeness and scientific validation are different checks."
    )

with st.expander("Kochi multi-hazard data acquisition board", expanded=True):
    st.caption(
        "This is the parallel acquisition queue. 'Discovered' means a credible source page was identified, "
        "not that its files have been downloaded or validated. Restricted or unclear sources are not scraped."
    )
    catalog_records = get_catalog()
    catalog_issues = {
        row["id"]: validate_catalog_record(row)
        for row in catalog_records
        if validate_catalog_record(row)
    }
    if catalog_issues:
        st.error(f"Data catalog metadata structure needs review for {len(catalog_issues)} record(s).")
        st.json(catalog_issues)
    selected_hazards = set(expand_hazards(inputs["hazard"])) | {inputs["hazard"]}
    # Show highest-priority data relevant to the selected hazard while keeping
    # all other disaster sources available for project planning.
    relevant_records = [
        row for row in catalog_records
        if selected_hazards.intersection(row["hazards"])
    ]
    all_records = relevant_records + [
        row for row in catalog_records if row not in relevant_records
    ]
    st.markdown("**Priority order:** P0 = core baseline evidence; P1 = important supporting evidence; P2 = later extension.")
    display_dataframe(pd.DataFrame([{
        "Priority": row["priority"],
        "Hazard(s)": ", ".join(row["hazards"]),
        "Theme": row["theme"],
        "Dataset": row["dataset"],
        "Publisher": row["publisher"],
        "Acquisition status": row["status"],
        "Access conditions": row["access"],
        "Required QA before use": row["required_checks"],
        "Known limitations": row["limitations"],
        "Official source": row["url"],
        "Direct resource URLs": "; ".join(row.get("resource_urls", [])) or "No direct file link confirmed",
    } for row in all_records]), hide_index=True, width="stretch")
    for row in relevant_records:
        with st.expander(f"{row['priority']} · {row['dataset']}"):
            st.markdown(f"**Publisher:** {row['publisher']}")
            st.markdown(f"**Source:** [{row['url']}]({row['url']})")
            if row.get("resource_urls"):
                st.markdown("**Direct source files:**")
                for resource_url in row["resource_urls"]:
                    st.markdown(f"- [{resource_url.rsplit('/', 1)[-1]}]({resource_url})")
            st.markdown(f"**Current status:** {row['status']}")
            st.markdown(f"**Access:** {row['access']}")
            st.markdown(f"**Required checks:** {row['required_checks']}")
            st.markdown(f"**Limitations:** {row['limitations']}")
    st.info(
        "The catalog is a verified-source discovery queue, not a downloaded-data inventory. "
        "A dataset moves to 'acquired' only after its file, publisher metadata, retrieval date, "
        "licence/access terms, checksum, schema, spatial coverage and QA results are recorded."
    )

with st.expander("Consequence-model data requirements by disaster", expanded=True):
    st.caption(
        "This matrix defines the evidence needed to estimate local consequences—not just whether a hazard exists. "
        "It separates hazard intensity, physical processes, exposure, vulnerability and observed outcomes. "
        "It is a requirements plan, not a working consequence predictor."
    )
    requirement_hazard = st.selectbox(
        "Inspect data requirements for",
        list(HAZARD_REQUIREMENTS),
        index=list(HAZARD_REQUIREMENTS).index(inputs["hazard"]) if inputs["hazard"] in HAZARD_REQUIREMENTS else 0,
        key="consequence_requirements_hazard",
    )
    req = requirements_for_hazard(requirement_hazard)
    st.markdown(f"**Candidate model family:** {req['model_family']}")
    display_dataframe(pd.DataFrame(requirements_table(requirement_hazard)), hide_index=True, width="stretch")
    st.markdown("**Specific blockers before consequence estimates:**")
    st.warning(req["current_blockers"])
    st.markdown("**Potential authoritative starting sources:**")
    st.write(req["starter_sources"])
    st.markdown("**Validation rule:** every hazard needs independent event/outcome evidence, a baseline comparison, event- or time-separated evaluation, uncertainty reporting, and a documented intended-use boundary.")
    with st.expander("Shared minimum requirements across every hazard"):
        display_dataframe(pd.DataFrame(req["common_requirements"]), hide_index=True, width="stretch")

st.subheader("Evidence readiness checklist for this hazard")
st.caption(
    "This checklist identifies evidence needed before stronger conclusions are justified. "
    "A file/path being present does not prove its contents are suitable, current, licensed for reuse, or independently verified."
)
evidence_checklist = hazard_evidence_checklist(inputs, ROOT)
display_dataframe(evidence_checklist, hide_index=True, width="stretch")
st.info(
    "Readiness status is descriptive, not a numerical risk score. Items marked not connected or unverified "
    "must not be treated as evidence that the hazard or exposure is absent."
)


st.subheader("Alternative evidence routes for this hazard")
alternative_routes = alternative_evidence_for_hazard(inputs["hazard"])
if alternative_routes:
    st.caption(
        "These are practical additional evidence routes. They do not automatically "
        "make a dataset training-ready; access, coverage, metadata and validation remain required."
    )
    for route in alternative_routes:
        with st.expander(route["title"]):
            st.write(route["method"])
            st.markdown("**Useful for**")
            for capability in route["supports"]:
                st.write(f"- {capability.replace('_', ' ')}")
            st.markdown("**Not sufficient for**")
            for limitation in route["does_not_support"]:
                st.write(f"- {limitation.replace('_', ' ')}")
            st.caption(route["status"])
            for source in route["sources"]:
                st.markdown(f"- [{source['publisher']} — {source['title']}]({source['url']})")
else:
    st.caption("No additional alternative-evidence route is registered for this hazard yet.")

st.subheader("Evidence provenance gate")
provenance = evidence_provenance_summary(inputs)
st.warning(f"**{provenance['Provenance status']}**")
st.write("**Source/time notes:**", provenance["Source/time notes"])
st.write("**Permitted interpretation:**", provenance["Permitted interpretation"])
st.write("**Required verification:**", provenance["Verification gate"])
st.caption("Typing a source name or selecting a classification does not independently verify the source, its freshness, or its fitness for this hazard.")

st.header("4. Assessment status")
assessment = assessment_summary(inputs)
if disaster_assessment is not None:
    _render_disaster_assessment(disaster_assessment)
compound_assessment = None
if inputs.get("hazard") == "Compound: cyclone + flood":
    try:
        compound_assessment = assess_compound_scenario(_compound_scenario_inputs(inputs))
    except ValueError as exc:
        st.error(f"Compound evidence review input error: {exc}")
    else:
        _render_compound_assessment(compound_assessment)

if st.button(
    "Open Kochi map and available hazard evidence",
    icon=":material/map:",
    key="wf_open_kochi_map",
    help="Opens the Kochi map with this scenario. A modelled flood-context layer is available for flood-component scenarios; other hazards remain explicitly unavailable until suitable local spatial evidence is approved.",
):
    st.session_state[MAP_CONTEXT_KEY] = build_map_context(inputs, disaster_assessment)
    map_hazard = inputs.get("hazard")
    if isinstance(map_hazard, str) and hazard_has_flood_component(map_hazard):
        # A previous manual toggle may have left the per-hazard checkbox off.
        # Re-entering the map from a flood scenario should enable its preview.
        st.session_state[f"kochimap_jrc_{map_hazard}"] = True
    st.switch_page(ROOT / "app_pages" / "kochi_map.py")
st.warning(assessment["status"], icon=":material/priority_high:")
st.write("**Method:**", assessment["method"])
st.write("**Selected hazard(s):**", assessment["hazards"])
st.write("**Interpretation:**", assessment["interpretation"])
st.warning(assessment["additional_caution"])
st.caption("No user-entered value is treated as verified. River-level values are recorded but never compared with a threshold in this workflow.")
st.subheader("Evidence by decision dimension")
st.caption("Statuses below describe evidence readiness, not hazard severity or risk class.")
dimension_matrix = assessment_evidence_matrix(inputs, evidence)
display_dataframe(dimension_matrix, hide_index=True, width="stretch", alt="Evidence readiness by hazard decision dimension")
st.subheader("Uncertainty register")
uncertainty_register = build_uncertainty_register(inputs, evidence)
st.caption("Measurement, data quality, spatial, temporal, model, and scenario uncertainty are reported separately. Unknown values are not interpreted as zero risk.")
display_dataframe(uncertainty_register, hide_index=True, width="stretch", alt="Measurement, data quality, spatial, temporal, model, and scenario uncertainties")
st.subheader("Conceptual infrastructure dependencies")
st.caption("These are generic pathways to investigate, not verified Kochi networks or claims of actual vulnerability. Simultaneous occurrence and causal/service dependencies are distinct; every listed local link remains unverified.")
infrastructure_dependency_review = dependency_review_table()
display_dataframe(
    infrastructure_dependency_review, hide_index=True, width="stretch",
    alt="Conceptual infrastructure and service dependency pathways requiring local verification",
)
st.subheader("Historical validation requirements")
st.caption("Local predictive validation has not been performed. This checklist records the independent evidence, time and location matching, leakage-safe splits, and error review required before any predictive claim.")
validation_checklist = historical_validation_checklist()
display_dataframe(
    validation_checklist, hide_index=True, width="stretch",
    alt="Minimum independent historical validation evidence and evaluation stages",
)

st.subheader("Scientific scenario frame and evidence gates")
scientific_frame = build_scientific_scenario_frame(inputs)
st.info(scientific_frame["evidence_gate"])
st.caption(
    "This frame structures the reasoning into hazard, exposure, vulnerability, and consequences to investigate. "
    "It does not calculate a probability, impact estimate, or warning."
)
if scientific_frame["pathways"]:
    display_dataframe(pd.DataFrame(scientific_frame["pathways"]), hide_index=True, width="stretch")
else:
    st.warning("No pathway template exists for this selection. The app will not guess one.")
st.markdown("**Evidence required before stronger conclusions:**")
for item in scientific_frame["required_evidence"]:
    st.markdown(f"- {item}")
st.markdown("**Interpretation safeguards:**")
for item in scientific_frame["limitations"]:
    st.markdown(f"- {item}")

st.subheader("Input quality and hazard-specific evidence gate")
input_quality = evaluate_scenario_readiness(inputs["hazard"], inputs)
if input_quality["input_status"] == "Review required":
    st.warning("Input review required before interpreting this scenario.")
else:
    st.success(input_quality["input_status"])
for item in input_quality["errors"]:
    st.error(item)
for item in input_quality["warnings"]:
    st.warning(item)
st.markdown("**Hazard-specific evidence checklist**")
for item in input_quality["evidence_factors_present"]:
    st.markdown(f"- ✓ Supplied in the form: {item}")
for item in input_quality["evidence_factors_missing_or_unverified"]:
    st.markdown(f"- ☐ Missing or not independently verified: {item}")

st.subheader("Data quality and confidence")
data_quality_confidence = data_quality_confidence_statement(
    inputs,
    input_quality=input_quality,
    evidence_checklist=evidence_checklist,
    project_root=ROOT,
)
st.info(data_quality_confidence["Quantitative confidence"])
for field in (
    "Input evidence class",
    "Input quality status",
    "Hazard evidence requirements",
    "User-supplied evidence factors",
    "Blocking input errors",
    "Input warnings",
    "Known data-quality defects",
    "What would change the conclusion",
):
    st.write(f"**{field}:**", data_quality_confidence[field])
st.caption(data_quality_confidence["Interpretation"])

st.subheader("Missing information register")
missing_information = missing_information_register(
    inputs,
    evidence_checklist=evidence_checklist,
    input_quality=input_quality,
    project_root=ROOT,
)
if missing_information.empty:
    st.success(
        "No checklist items are currently missing or unverified. This means the "
        "checklist is satisfied, not that the scenario is validated or safe."
    )
else:
    st.caption(
        "Each row records information the workflow cannot supply or verify. "
        "Absence of evidence is not evidence that the hazard, exposure, or impact is absent."
    )
    display_dataframe(
        missing_information,
        hide_index=True,
        width="stretch",
        alt="Missing or unverified information, its consequences, and how to resolve it",
    )

readiness_plan = decision_readiness_summary(inputs, input_quality)
st.subheader("Decision readiness and next actions")
st.warning(f"**{readiness_plan['decision_status']}**")
st.write("**Numerical prediction gate:**", readiness_plan["numerical_prediction_gate"])
if readiness_plan["critical_input_errors"]:
    st.error("Resolve these input errors before interpreting the scenario:")
    for item in readiness_plan["critical_input_errors"]:
        st.markdown(f"- {item}")
if readiness_plan["hazard_specific_gaps"]:
    st.warning("Hazard-specific evidence gaps:")
    for item in readiness_plan["hazard_specific_gaps"]:
        st.markdown(f"- {item}")
display_dataframe(pd.DataFrame(readiness_plan["next_steps"]), hide_index=True, width="stretch")
st.caption(readiness_plan["interpretation"])
st.info(
    "Numerical prediction is not enabled because the required calibrated model and verified local evidence are not available. "
    "Your hypothetical scenario has still been assessed qualitatively in the section above."
)

st.subheader("Consequence assessment: probability, affected areas and impacts")
consequence_assessment = build_consequence_assessment(
    inputs["hazard"],
    inputs["location"],
    inputs["input_classification"],
    inputs,
)
st.caption(
    "This is the required output structure for every selected disaster. Numerical probability and affected-area results "
    "will appear only after the corresponding validated model and spatial evidence are connected."
)
st.write("**Scenario type:**", consequence_assessment["scenario_type"])
st.write("**Current model status:**", consequence_assessment["model_status"])
if consequence_assessment["heatwave_screening"] is not None:
    heat = consequence_assessment["heatwave_screening"]
    st.markdown("**Heatwave criteria screen (not a forecast or official warning)**")
    st.write("**Station-level screening:**", heat["station_status"])
    if heat["departure_from_normal_c"] is not None:
        st.metric("Supplied maximum-temperature departure from normal", f"{heat['departure_from_normal_c']:.1f} °C")
    st.write("**Duration and multi-station check:**", heat["declaration_status"])
    st.caption(heat["source"])
col_prob, col_area = st.columns(2)
with col_prob:
    st.markdown("**Probability of occurrence**")
    st.info(consequence_assessment["occurrence_probability"])
with col_area:
    st.markdown("**Affected-area estimate**")
    st.info(consequence_assessment["affected_area"])
st.markdown("**Consequences this assessment must examine**")
for item in consequence_assessment["consequence_categories"]:
    st.markdown(f"- {item}")
st.markdown("**Required evidence for this scenario**")
for item in consequence_assessment["required_evidence"]:
    st.markdown(f"- {item}")
st.warning(consequence_assessment["scientific_guardrail"])
st.caption(consequence_assessment["probability_semantics"])

if inputs.get("hazard") == "Flood":
    with st.expander("Flood extent and depth analysis (upload a measured/modelled depth layer)", expanded=False):
        st.caption(
            "This tool makes extent and depth summaries available when you provide a quality-checked "
            "flood-depth GeoJSON. It measures supplied data; it does not simulate or forecast flooding."
        )
        depth_file = st.file_uploader(
            "Flood-depth GeoJSON (polygon features with a numeric depth_m property)",
            type=["geojson", "json"],
            key="flood_depth_geojson_upload",
        )
        depth_field = st.text_input("Depth property name", value="depth_m", key="flood_depth_property")
        depth_source = st.text_input(
            "Flood-depth dataset source URL", key="flood_depth_source_url", placeholder="https://…"
        )
        depth_event_date = st.text_input(
            "Event / model reference date", key="flood_depth_event_date", placeholder="YYYY-MM-DD"
        )
        depth_provenance = st.checkbox(
            "I verified the source, event date, horizontal CRS, vertical datum, depth units, coverage and reuse terms.",
            key="flood_depth_provenance_confirmed",
        )
        if st.button("Summarize supplied flood extent and depth", key="summarize_flood_depth"):
            if not depth_file:
                st.error("Upload a flood-depth GeoJSON file.")
            elif not depth_source.startswith("https://"):
                st.error("Provide the dataset's HTTPS source URL.")
            elif not depth_event_date.strip():
                st.error("Provide the event or model reference date.")
            elif not depth_provenance:
                st.error("Verify the dataset metadata before calculating.")
            else:
                try:
                    depth_payload = json.loads(depth_file.getvalue().decode("utf-8-sig"))
                    depth_summary = summarize_flood_depth_geojson(
                        depth_payload, depth_field=depth_field.strip() or "depth_m"
                    )
                    st.session_state["flood_depth_summary"] = {
                        **depth_summary,
                        "source_url": depth_source.strip(),
                        "event_date": depth_event_date.strip(),
                        "file_sha256": hashlib.sha256(depth_file.getvalue()).hexdigest(),
                        "hazard": str(inputs.get("hazard", "")),
                    }
                    st.session_state.pop("flood_depth_error", None)
                except (UnicodeDecodeError, json.JSONDecodeError, FloodFootprintError, ValueError) as exc:
                    st.session_state.pop("flood_depth_summary", None)
                    st.session_state["flood_depth_error"] = str(exc)

        if st.session_state.get("flood_depth_error"):
            st.error(f"Flood-depth analysis blocked: {st.session_state['flood_depth_error']}")
        saved_depth = st.session_state.get("flood_depth_summary")
        current_depth_hash = hashlib.sha256(depth_file.getvalue()).hexdigest() if depth_file else None
        if saved_depth and (
            saved_depth.get("file_sha256") != current_depth_hash
            or saved_depth.get("source_url") != depth_source.strip()
            or saved_depth.get("event_date") != depth_event_date.strip()
            or saved_depth.get("hazard") != str(inputs.get("hazard", ""))
        ):
            st.warning("The saved flood-depth summary no longer matches the selected file or metadata. Recalculate it.")
        elif saved_depth:
            st.warning(
                "MEASURED / MODEL-SUPPLIED LAYER SUMMARY — not a new flood prediction. "
                "Do not use this output as an evacuation or route-safety instruction."
            )
            st.caption("Status: SUMMARIZED_NOT_FORECAST · Supplied depth-layer measurement only; not a forecast or simulated inundation.")
            st.metric("Flood extent in supplied layer", f"{saved_depth['flooded_extent_km2']:.4f} km²")
            st.metric("Area-weighted mean supplied depth", f"{saved_depth['area_weighted_mean_depth_m']:.3f} m")
            st.metric("Maximum supplied polygon depth", f"{saved_depth['maximum_polygon_depth_m']:.3f} m")
            st.write("**Area by descriptive depth band (not damage/safety thresholds)**")
            display_dataframe(
                pd.DataFrame([
                    {"Depth band": key.replace("_", " ").replace("m", "m"), "Area (km²)": value}
                    for key, value in saved_depth["area_by_depth_band_km2"].items()
                ]),
                hide_index=True, width="stretch",
                alt="Area of supplied flood-depth polygons by descriptive depth band",
            )
            st.caption(
                f"Reference date: {saved_depth['event_date']} · "
                f"{saved_depth['polygon_count']:,} polygons · "
                f"Source: {saved_depth['source_url']}"
            )
            for limitation in saved_depth["limitations"]:
                st.caption(f"• {limitation}")

with st.expander("Population exposure calculator (GeoJSON evidence inputs)", expanded=False):
    st.caption(
        "Upload a population grid and a hazard-footprint polygon dataset in EPSG:4326 GeoJSON. "
        "The calculator estimates residents inside the supplied footprint by equal-area polygon "
        "intersection. It does not estimate casualties, displacement or actual damage."
    )
    population_file = st.file_uploader(
        "Population grid GeoJSON (each polygon needs a population count)",
        type=["geojson", "json"],
        key="population_exposure_grid_upload",
    )
    footprint_file = st.file_uploader(
        "Hazard footprint GeoJSON (validated polygon features)",
        type=["geojson", "json"],
        key="population_exposure_footprint_upload",
    )
    population_field_name = st.text_input(
        "Population-count property name",
        value="population",
        key="population_exposure_population_field",
    )
    grid_id_field_name = st.text_input(
        "Grid-cell ID property name",
        value="grid_id",
        key="population_exposure_grid_id_field",
    )
    ward_field_name = st.text_input(
        "Ward-label property name (optional)",
        value="ward_name",
        key="population_exposure_ward_field",
    )
    population_year = st.text_input(
        "Population grid reference year",
        key="population_exposure_year",
        placeholder="e.g. 2025",
    )
    population_source_url = st.text_input(
        "Population dataset source URL",
        key="population_exposure_source",
        placeholder="https://…",
    )
    footprint_source_url = st.text_input(
        "Hazard footprint source URL",
        key="population_exposure_footprint_source",
        placeholder="https://…",
    )
    population_provenance_confirmed = st.checkbox(
        "I have checked the source attribution, reuse terms, CRS, date and geographic coverage for both files.",
        key="population_exposure_provenance_confirmed",
    )
    if st.button("Calculate population inside footprint", key="calculate_population_exposure"):
        if not population_file or not footprint_file:
            st.error("Upload both GeoJSON files before calculating.")
        elif not population_year.strip().isdigit():
            st.error("Enter the population dataset reference year.")
        elif not population_source_url.startswith("https://") or not footprint_source_url.startswith("https://"):
            st.error("Provide HTTPS source URLs for both datasets.")
        elif not population_provenance_confirmed:
            st.error("Confirm source, licence, CRS, date and coverage review before calculating.")
        else:
            try:
                population_payload = json.loads(population_file.getvalue().decode("utf-8-sig"))
                footprint_payload = json.loads(footprint_file.getvalue().decode("utf-8-sig"))
                exposure_result = estimate_population_exposure(
                    population_payload,
                    footprint_payload,
                    population_field=population_field_name.strip() or "population",
                    grid_id_field=grid_id_field_name.strip() or "grid_id",
                    ward_field=ward_field_name.strip() or None,
                    source_crs="EPSG:4326",
                )
                st.session_state["population_exposure_result"] = {
                    **exposure_result,
                    "population_year": population_year.strip(),
                    "population_field": population_field_name.strip() or "population",
                    "grid_id_field": grid_id_field_name.strip() or "grid_id",
                    "ward_field": ward_field_name.strip() or None,
                    "population_source_url": population_source_url.strip(),
                    "footprint_source_url": footprint_source_url.strip(),
                    "population_file_sha256": hashlib.sha256(population_file.getvalue()).hexdigest(),
                    "footprint_file_sha256": hashlib.sha256(footprint_file.getvalue()).hexdigest(),
                    "footprint_geojson": footprint_payload,
                    "scenario_hazard": str(inputs.get("hazard", "")),
                    "scenario_location": str(inputs.get("location", "")),
                }
                st.session_state.pop("population_exposure_error", None)
            except (UnicodeDecodeError, json.JSONDecodeError, PopulationExposureError, ValueError) as exc:
                st.session_state.pop("population_exposure_result", None)
                st.session_state["population_exposure_error"] = str(exc)

    exposure_error = st.session_state.get("population_exposure_error")
    if exposure_error:
        st.error(f"Population exposure calculation blocked: {exposure_error}")
    exposure_result = st.session_state.get("population_exposure_result")
    current_population_hash = (
        hashlib.sha256(population_file.getvalue()).hexdigest() if population_file else None
    )
    current_footprint_hash = (
        hashlib.sha256(footprint_file.getvalue()).hexdigest() if footprint_file else None
    )
    if exposure_result and (
        exposure_result.get("scenario_hazard") != str(inputs.get("hazard", ""))
        or exposure_result.get("scenario_location") != str(inputs.get("location", ""))
        or exposure_result.get("population_file_sha256") != current_population_hash
        or exposure_result.get("footprint_file_sha256") != current_footprint_hash
        or exposure_result.get("population_year") != population_year.strip()
        or exposure_result.get("population_source_url") != population_source_url.strip()
        or exposure_result.get("footprint_source_url") != footprint_source_url.strip()
        or exposure_result.get("population_field") != (population_field_name.strip() or "population")
        or exposure_result.get("grid_id_field") != (grid_id_field_name.strip() or "grid_id")
        or exposure_result.get("ward_field") != (ward_field_name.strip() or None)
    ):
        st.warning(
            "The saved exposure estimate no longer matches the selected scenario, uploaded files or source metadata. "
            "Recalculate before using it in this scenario."
        )
    elif exposure_result:
        st.caption(
            f"Scenario: {exposure_result['scenario_hazard']} · "
            f"Location: {exposure_result['scenario_location']}"
        )
        st.warning(
            "APPROXIMATE POPULATION-EXPOSURE SCREENING — not a count of people harmed, "
            "displaced, injured or killed. Uniform population within each grid cell is assumed."
        )
        st.caption("Evidence status: screening estimate only · Source grid year, spatial coverage, CRS and population allocation assumption govern interpretation.")
        if exposure_result["population_grid_covers_full_footprint"]:
            st.metric(
                "Estimated population inside supplied footprint",
                f"{exposure_result['estimated_population_in_footprint']:,}",
            )
        else:
            st.metric(
                "Estimated population in covered portion only",
                f"{exposure_result['estimated_population_in_covered_part']:,}",
            )
            st.error(
                f"The uploaded population grid covers only "
                f"{exposure_result['hazard_footprint_area_covered_percent']}% of the hazard footprint. "
                "A total exposed-population estimate is withheld because uncovered areas could contain residents."
            )
        st.caption(
            f"Population reference year: {exposure_result['population_year']}; "
            f"{exposure_result['intersecting_population_cells']:,} intersecting cells out of "
            f"{exposure_result['population_grid_cells']:,}. "
            f"Share of uploaded grid population: {exposure_result['exposure_share_of_grid_percent']}%."
        )
        if exposure_result["ward_screening_estimates"]:
            st.markdown("**Ward-level screening estimates**")
            display_dataframe(
                pd.DataFrame(exposure_result["ward_screening_estimates"]),
                hide_index=True,
                width="stretch",
                alt="Estimated population inside the uploaded hazard footprint by source-provided ward label",
            )
        bounds = exposure_result["footprint_bounds_wgs84"]
        center_lon = (bounds[0] + bounds[2]) / 2
        center_lat = (bounds[1] + bounds[3]) / 2
        st.markdown("**Supplied hazard footprint**")
        st.metric(
            "Area covered by supplied hazard footprint",
            f"{exposure_result['hazard_footprint_area_km2']:,.3f} km²",
        )
        st.caption(
            f"Population-grid coverage: {exposure_result['hazard_footprint_area_covered_percent']}% "
            f"({exposure_result['population_grid_covered_area_km2']:,.3f} km²)."
        )
        st.pydeck_chart(
            pdk.Deck(
                layers=[
                    pdk.Layer(
                        "GeoJsonLayer",
                        data=exposure_result["footprint_geojson"],
                        get_fill_color=[220, 53, 69, 65],
                        get_line_color=[170, 25, 40, 220],
                        get_line_width=2,
                        line_width_min_pixels=2,
                        pickable=True,
                        stroked=True,
                        filled=True,
                    )
                ],
                initial_view_state=pdk.ViewState(
                    latitude=center_lat,
                    longitude=center_lon,
                    zoom=11,
                    pitch=0,
                ),
                map_style=None,
                tooltip={"text": "Hazard exposure footprint"},
            ),
            use_container_width=True,
        )
        st.caption(exposure_result["method"])
        for limitation in exposure_result["limitations"]:
            st.caption(f"• {limitation}")
        st.markdown(
            f"[Population source]({exposure_result['population_source_url']}) · "
            f"[Hazard footprint source]({exposure_result['footprint_source_url']})"
        )

st.markdown("**Additional impact and response outputs**")
st.caption(
    "These outputs are part of every assessment. Values remain explicitly unavailable until "
    "the required hazard, population, asset and outcome evidence is validated; no generic "
    "percentages or casualty figures are invented."
)
impact_register = consequence_assessment.get("impact_outputs", [])
if impact_register:
    display_dataframe(
        pd.DataFrame(impact_register).rename(columns={
            "output": "Impact / prediction output",
            "unit": "Unit",
            "status": "Current estimate status",
            "required_evidence": "Evidence needed to calculate it",
        }),
        hide_index=True,
        width="stretch",
        alt="Evidence-gated population, displacement, casualty, building, infrastructure, economic and hazard-intensity outputs",
    )

st.header("5. Compare hypothetical scenarios")
st.caption("The following cases differ only by their stated assumptions. Possible pathways are planning prompts, not calculated impacts.")
scenarios = build_scenario_comparison(inputs)
display_dataframe(scenarios, hide_index=True, width="stretch")

st.header("6. Preventive action intelligence")
preventive_actions = generate_prevention_actions(
    str(inputs.get("hazard", "")),
    inputs,
)
st.caption(
    "These are hazard-specific prevention and preparedness options. Each item shows its "
    "activation trigger, intended benefit, responsible owner, evidence required and safety caveat. "
    "They are not ranked, do not quantify risk reduction, and never replace official instructions."
)
if preventive_actions:
    display_dataframe(
        pd.DataFrame(preventive_actions)[
            ["action_id", "phase", "hazard", "action", "trigger", "benefit", "owner", "evidence", "caution"]
        ].rename(
            columns={
                "action_id": "Action ID",
                "phase": "When",
                "hazard": "Hazard",
                "action": "Recommended precaution",
                "trigger": "When it applies",
                "benefit": "How it may reduce harm",
                "owner": "Responsible party",
                "evidence": "Evidence / verification needed",
                "caution": "Safety boundary",
            }
        ),
        hide_index=True,
        width="stretch",
        alt="Evidence-aware disaster prevention and preparedness actions",
    )
else:
    st.info("Select a registered hazard to generate hazard-specific preparedness options.")

st.subheader("Intervention-effectiveness ML")
effectiveness = intervention_effectiveness_for_hazards(
    [str(inputs.get("hazard", ""))] if inputs.get("hazard") else [],
    inputs,
)
hazard_effect = effectiveness.get("by_hazard", {}).get(str(inputs.get("hazard", "")), {})
if hazard_effect.get("ranked_actions"):
    st.caption(
        "Preliminary observational ML estimates of expected damage reduction. "
        "These are not guarantees, causal proof or instructions."
    )
    display_dataframe(
        pd.DataFrame([
            {
                "Recommended precaution": next(
                    (action["action"] for action in preventive_actions if action["action_id"] == item["action_id"]),
                    item["action_id"],
                ),
                "Estimated damage reduction (research units)": item["estimated_damage_reduction"],
                "Outcome unit": item["outcome_unit"],
                "Evidence status": item["status"],
            }
            for item in hazard_effect["ranked_actions"]
        ]),
        hide_index=True,
        width="stretch",
        alt="Preliminary ML ranking of intervention effectiveness",
    )
    st.warning(hazard_effect.get("warning", effectiveness.get("warning", "")))
else:
    st.info(
        "ML action-effect ranking is currently withheld. The project needs verified, "
        "comparable intervention episodes (implemented and not implemented), measured "
        "damage outcomes and pre-intervention conditions before it can estimate which "
        "precaution reduces damage most."
    )
    if hazard_effect.get("reason"):
        st.caption(hazard_effect["reason"])

st.header("6. Evidence-linked recommendation candidates")
recommendations = recommendation_candidates(inputs)
st.caption("Candidates are linked to the selected scenario, entered conditions, or evidence gaps. They are unranked planning prompts; no benefit or risk reduction is quantified.")
display_dataframe(recommendations, hide_index=True, width="stretch", alt="Evidence-linked preparedness and mitigation recommendation candidates")
priority_gate = recommendation_priority_readiness({})
st.info(
    f"Recommendation priority: {priority_gate['status']}. "
    "Expected risk reduction, affected population, infrastructure importance, feasibility, cost, time, and uncertainty "
    "lack complete verified evidence. No score or ranking is produced."
)

st.header("7. Plan prevention and preparedness actions")
st.write(
    "Hazard-specific risk-reduction and preparedness options are planning candidates, "
    "not site-specific prescriptions. Costs and impact estimates start blank and must "
    "be supported by documented evidence."
)
slug = re.sub(r"[^a-z0-9]+", "_", inputs["hazard"].lower()).strip("_")
starter_actions = mitigation_actions_for(inputs["hazard"])
starter_actions["Cost INR"] = pd.Series([None] * len(starter_actions), dtype="object")
starter_actions["User priority (1=highest)"] = pd.Series([None] * len(starter_actions), dtype="object")
actions = st.data_editor(
    starter_actions,
    key=f"workflow_actions_{slug}",
    num_rows="dynamic",
    hide_index=True,
    width="stretch",
    column_config={
        "Cost INR": st.column_config.NumberColumn(min_value=0, step=1000, format="%.0f", help="Leave blank until a documented estimate is available."),
        "User priority (1=highest)": st.column_config.NumberColumn(min_value=1, max_value=10, step=1, help="This is your own priority order; the app does not rank effectiveness."),
    },
)
st.caption("No risk-reduction percentages or guaranteed benefits are estimated. Entered cost and priority values remain user-supplied.")

st.header("8. Compare action combinations within a budget")
budget = st.number_input("Available budget (INR)", min_value=0, value=None, step=100000, key=f"workflow_budget_{slug}", help="Leave blank if a budget has not yet been set.")
action_names = actions["Action"].fillna("").astype(str).str.strip().tolist()
action_names = [name for name in action_names if name]
combo_col1, combo_col2 = st.columns(2)
with combo_col1:
    combination_a = st.multiselect("Combination A", action_names, key=f"workflow_combo_a_{slug}")
with combo_col2:
    combination_b = st.multiselect("Combination B", action_names, key=f"workflow_combo_b_{slug}")

overall_budget = budget_summary(actions.get("Cost INR", pd.Series(dtype=object)), budget)
metric_col1, metric_col2, metric_col3 = st.columns(3)
metric_col1.metric("Total of entered action costs", f"₹{overall_budget['entered_total']:,.0f}")
metric_col2.metric("Rows with missing / invalid cost", overall_budget["unknown_or_invalid_count"])
metric_col3.metric("Budget after entered costs", "Not set" if overall_budget["remaining"] is None else f"₹{overall_budget['remaining']:,.0f}")
if overall_budget["budget"] is None:
    st.info("Enter a budget to check affordability. Missing action costs are excluded from the total, so the total and balance are incomplete.")
elif overall_budget["unknown_or_invalid_count"]:
    st.warning("Some action costs are blank or invalid. A full-plan budget fit cannot be confirmed.")
elif overall_budget["within_budget"]:
    st.success("All action rows with entered costs fit arithmetically within the budget; this says nothing about effectiveness or optimality.")
else:
    st.warning("Entered action costs exceed the available budget.")
combinations = compare_action_combinations(actions, budget, {"A": combination_a, "B": combination_b})
display_dataframe(combinations, hide_index=True, width="stretch")
st.caption("A combination is shown because you selected its actions. Affordability is cost arithmetic only; priority numbers are supplied by you.")

st.header("9. Generate a report")
report = report_rows(
    inputs,
    evidence,
    scenarios,
    actions,
    budget,
    combinations,
    ROOT,
    evidence_checklist=evidence_checklist,
    readiness_summary=readiness_plan,
    disaster_assessment=disaster_assessment,
    compound_assessment=compound_assessment,
    scenario_prediction=prediction,
    scenario_screening=scenario_screen,
    consequence_assessment=consequence_assessment,
    scientific_frame=scientific_frame,
    input_quality=input_quality,
    uncertainty_register=uncertainty_register,
    dependency_review=infrastructure_dependency_review,
    validation_checklist=validation_checklist,
    missing_information=missing_information,
    data_quality_confidence=data_quality_confidence,
)
report_slug = slug or "scenario"
csv_bytes = report.to_csv(index=False).encode("utf-8-sig")
html_bytes = report_html(report).encode("utf-8")
download_col1, download_col2 = st.columns(2)
download_col1.download_button(
    "Download CSV report",
    csv_bytes,
    file_name=f"ai_resilience_{report_slug}_report.csv",
    mime="text/csv",
    width="stretch",
)
download_col2.download_button(
    "Download readable HTML report",
    html_bytes,
    file_name=f"ai_resilience_{report_slug}_report.html",
    mime="text/html",
    width="stretch",
)
with st.expander("Preview report contents"):
    display_dataframe(report, hide_index=True, width="stretch")

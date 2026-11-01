"""Connected evidence-to-budget workflow for the AI RESILIENCE prototype."""

from pathlib import Path
import re
import json

import pandas as pd
import streamlit as st

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
    evidence_inventory,
    mitigation_actions_for,
    recommendation_candidates,
    recommendation_priority_readiness,
    report_html,
    report_rows,
    validate_workflow_inputs,
)
from src.disaster_models import assess_disaster
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
from src.map_integration import MAP_CONTEXT_KEY, build_map_context
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
        display_dataframe(pd.DataFrame(metric_rows), hide_index=True, width="stretch")
        st.caption(
            f"Training: {summary['train_pairs']:,} exact one-hour pairs ending before "
            f"{summary['train_end_exclusive']}; test: {summary['test_pairs']:,} pairs from "
            f"{summary['test_period_start']} to {summary['test_period_end']}. A global chronological "
            f"80/20 timestamp split and {summary['embargo_days']}-day embargo were used; "
            f"test coverage is {summary['test_stations']} of {summary['all_stations']} stations."
        )
        st.write("**Per-station holdout metrics**")
        display_dataframe(result["per_station"], hide_index=True, width="stretch")
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
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.info("Compound interaction remains unresolved. Component indicators are separate and are not added.")
    elif indicators:
        rows = [
            {"Indicator": key.replace("_", " ").capitalize(), "Result": json.dumps(value, ensure_ascii=False, default=str)}
            for key, value in indicators.items()
        ]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

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
    st.dataframe(
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


st.title("Unified disaster decision workflow")
st.caption("Select a hazard → describe the area and conditions → review evidence → compare scenarios and actions → check budget fit → export a report.")
st.warning("This prototype does not issue official warnings or validated predictions. Inputs are user-described and are not verified observations unless the user supplies and checks their source.")
st.caption("A historical rainfall measurement benchmark is available in the evidence explorer. It is separate from the assessment and is not a current rainfall or flood forecast.")
st.info(
    "Kochi evidence update: an official JRC 100-year river-flood depth scenario is available as map context. "
    "Asset-level flood exposure remains unknown because there is no independently validated hospital or critical-facility location layer. "
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

st.header("1. Select a hazard and describe conditions")
with st.form("decision_workflow_intake"):
    hazard = st.selectbox("Hazard or compound scenario", HAZARD_OPTIONS, key="wf_hazard")
    location = st.text_input(
        "Location or area name",
        value="Kochi Municipal Corporation — area not specified",
        help="Enter an area name; do not guess coordinates. The map currently has only a provisional corporation outline.",
        key="wf_location",
    )
    input_classification = st.selectbox(
        "How should these conditions be treated?",
        ["Hypothetical scenario assumption", "User-reported observation (source not independently verified)", "Forecast supplied by user (not checked by app)", "Unknown / unverified"],
        key="wf_classification",
    )
    source_and_time = st.text_input(
        "Source, observation/forecast time, and units (if known)",
        key="wf_source_time",
        help="Example: source name, timestamp, timezone, station, and averaging period. This app does not verify them.",
    )

    st.caption("All numeric fields are optional. Empty means not supplied; the app does not fill in values.")
    col1, col2 = st.columns(2)
    with col1:
        rainfall_mm = st.number_input("Rainfall (mm)", min_value=0.0, value=None, step=1.0, key="wf_rainfall")
        rainfall_period = st.selectbox("Rainfall period", ["Not supplied", "Last 1 hour", "Last 24 hours", "Last 3 days", "Other / state in notes"], key="wf_rainfall_period")
        river_level_m = st.number_input("River-level reading (m)", value=None, step=0.1, key="wf_river", help="Gauge readings can be below zero depending on the reference datum. The app does not compare this with a threshold.")
        river_station = st.text_input("River station (if applicable)", key="wf_river_station")
        river_reference = st.text_input("Gauge zero / datum reference (if known)", key="wf_river_reference")
    with col2:
        wind_speed_kmh = st.number_input("Wind speed (km/h)", min_value=0.0, value=None, step=1.0, key="wf_wind")
        temperature_c = st.number_input("Temperature (°C)", value=None, step=0.5, key="wf_temperature")
        affected_population = st.number_input("Affected population context (people; optional)", min_value=0, value=None, step=1, key="wf_population")
        drainage_status = st.selectbox("Drainage condition", DRAINAGE_STATUS_OPTIONS, key="wf_drainage")
        infrastructure_status = st.selectbox("Other infrastructure condition", INFRASTRUCTURE_STATUS_OPTIONS, key="wf_infrastructure")

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
        "affected_population": affected_population,
        "drainage_status": drainage_status,
        "infrastructure_status": infrastructure_status,
        "assets": assets,
        "condition_notes": condition_notes,
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

inputs = st.session_state.get("decision_workflow_inputs")
if inputs is None:
    st.header("2. Evidence available to review")
    st.dataframe(
        evidence_inventory(ROOT, st.session_state.get("rainfall_backtest_result")),
        hide_index=True,
        width="stretch",
    )
    st.info("Submit the form to continue. Missing GIS layers do not block a qualitative assessment; missing evidence does block a reliable numerical prediction.")
    st.stop()

st.header("2. Review evidence")
evidence = evidence_inventory(ROOT, st.session_state.get("rainfall_backtest_result"))
st.caption("The separate historical benchmark uses only the manual rainfall observations. Its results do not enter this qualitative assessment; conflicted CWC rainfall, unverified sample rows, and unresolved river levels remain excluded from model calculations.")
st.dataframe(evidence, hide_index=True, width="stretch")

st.header("3. Assessment status")
assessment = assessment_summary(inputs)
try:
    disaster_assessment = assess_disaster(inputs)
except ValueError as exc:
    disaster_assessment = None
    st.error(f"Hazard-specific assessment input error: {exc}")
else:
    _render_disaster_assessment(disaster_assessment)
if st.button(
    "View prone areas on the Kochi map",
    icon=":material/map:",
    key="wf_open_kochi_map",
    help="Opens the existing map with this submitted scenario. Available map evidence may not support the selected hazard.",
):
    st.session_state[MAP_CONTEXT_KEY] = build_map_context(inputs, disaster_assessment)
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
st.dataframe(dimension_matrix, hide_index=True, width="stretch")
st.subheader("Uncertainty register")
uncertainty_register = build_uncertainty_register(inputs, evidence)
st.caption("Measurement, data quality, spatial, temporal, model, and scenario uncertainty are reported separately. Unknown values are not interpreted as zero risk.")
st.dataframe(uncertainty_register, hide_index=True, width="stretch")
st.subheader("Conceptual infrastructure dependencies")
st.caption("These are generic pathways to investigate, not verified Kochi networks or claims of actual vulnerability. Simultaneous occurrence and causal/service dependencies are distinct; every listed local link remains unverified.")
st.dataframe(dependency_review_table(), hide_index=True, width="stretch")

st.header("4. Compare hypothetical scenarios")
st.caption("The following cases differ only by their stated assumptions. Possible pathways are planning prompts, not calculated impacts.")
scenarios = build_scenario_comparison(inputs)
st.dataframe(scenarios, hide_index=True, width="stretch")

st.header("5. Evidence-linked recommendation candidates")
recommendations = recommendation_candidates(inputs)
st.caption("Candidates are linked to the selected scenario, entered conditions, or evidence gaps. They are unranked planning prompts; no benefit or risk reduction is quantified.")
st.dataframe(recommendations, hide_index=True, width="stretch")
priority_gate = recommendation_priority_readiness({})
st.info(
    f"Recommendation priority: {priority_gate['status']}. "
    "Expected risk reduction, affected population, infrastructure importance, feasibility, cost, time, and uncertainty "
    "lack complete verified evidence. No score or ranking is produced."
)

st.header("6. Plan prevention and preparedness actions")
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

st.header("7. Compare action combinations within a budget")
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
st.dataframe(combinations, hide_index=True, width="stretch")
st.caption("A combination is shown because you selected its actions. Affordability is cost arithmetic only; priority numbers are supplied by you.")

st.header("8. Generate a report")
report = report_rows(
    inputs,
    evidence,
    scenarios,
    actions,
    budget,
    combinations,
    ROOT,
    disaster_assessment,
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
    st.dataframe(report, hide_index=True, width="stretch")

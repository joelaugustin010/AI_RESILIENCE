"""Connected evidence-to-budget workflow for the AI RESILIENCE prototype."""

from pathlib import Path
import re
import json

import pandas as pd
import streamlit as st

from src.decision_workflow import (
    HAZARD_OPTIONS,
    assessment_summary,
    build_scenario_comparison,
    budget_summary,
    compare_action_combinations,
    evidence_inventory,
    hazard_evidence_checklist,
    mitigation_actions_for,
    report_html,
    report_rows,
    validate_workflow_inputs,
)
from src.hydrology_analytics import (
    DATASETS,
    HydrologyDataError,
    filter_observations,
    load_observations,
    rainfall_station_comparison,
    station_gap_summary,
)
from src.rainfall_forecast import RainfallForecastError, run_manual_rainfall_backtest


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
        st.dataframe(pd.DataFrame(metric_rows), hide_index=True, width="stretch")
        st.caption(
            f"Training: {summary['train_pairs']:,} exact one-hour pairs ending before "
            f"{summary['train_end_exclusive']}; test: {summary['test_pairs']:,} pairs from "
            f"{summary['test_period_start']} to {summary['test_period_end']}. A global chronological "
            f"80/20 timestamp split and {summary['embargo_days']}-day embargo were used; "
            f"test coverage is {summary['test_stations']} of {summary['all_stations']} stations."
        )
        st.write("**Per-station holdout metrics**")
        st.dataframe(result["per_station"], hide_index=True, width="stretch")
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
        st.warning(spec.warning)
        if qa["invalid_timestamp_rows"] or qa["invalid_measurement_rows"]:
            st.warning(
                f"Chart excludes {qa['invalid_timestamp_rows']} rows with invalid timestamps and "
                f"{qa['invalid_measurement_rows']} rows with invalid measurements; source files remain unchanged."
            )
        if qa["duplicate_station_time_groups"]:
            st.warning(
                f"QA found {qa['duplicate_station_time_groups']:,} duplicate station-time groups, "
                f"including {qa['conflicting_station_time_groups']:,} with conflicting values. "
                "The chart keeps every valid source row at its original timestamp."
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
            st.dataframe(rainfall_station_comparison(observations), hide_index=True, width="stretch")
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
st.page_link("app_pages/kochi_map.py", label="Open the Kochi map", icon=":material/map:")
st.info(
    "Kochi evidence update: JRC 100-year river-flood depth tiles are locally reviewed as modeled hazard data, but the map preview is withheld pending clarification of conflicting licence statements. "
    "Asset-level flood exposure remains unknown because there is no independently validated hospital or critical-facility location layer. "
    "See the map for source details and the broader data gaps."
)
with st.expander("Longer-term AI RESILIENCE roadmap"):
    st.markdown(
        "- **Pollution sources:** combine pollutant-specific station observations, weather, and verified facility/emissions records; AQI alone cannot identify a factory.\n"
        "- **Multi-hazard and compound scenarios:** add verified flood, cyclone, earthquake, landslide, heat, drought, industrial-incident, and infrastructure-failure evidence.\n"
        "- **Historical-event-informed preparedness:** use sourced event records and documented impacts before estimating likelihoods or consequences.\n"
        "- **Budget prioritisation:** compare documented intervention costs and defensible outcome evidence; leave benefits unquantified when evidence is missing."
    )

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
        drainage_status = st.selectbox("Drainage condition", ["Not supplied", "Reported functioning", "Reported partially impaired", "Reported failed", "Hypothetical partial failure", "Not applicable"], key="wf_drainage")
        infrastructure_status = st.selectbox("Other infrastructure condition", ["Not supplied", "No disruption reported", "Possible / hypothetical disruption", "Disruption reported by user", "Not applicable"], key="wf_infrastructure")

    assets = st.multiselect(
        "Services or assets to review (user-nominated; location/exposure not verified)",
        ["Hospitals", "Roads and bridges", "Electricity", "Drinking water", "Communications", "Shelters", "Schools", "Drainage", "Industrial facilities", "Residential buildings"],
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
    }
    problems = validate_workflow_inputs(submitted_inputs)
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

st.subheader("Evidence readiness checklist for this hazard")
st.caption(
    "This checklist identifies evidence needed before stronger conclusions are justified. "
    "A file/path being present does not prove its contents are suitable, current, licensed for reuse, or independently verified."
)
evidence_checklist = hazard_evidence_checklist(inputs, ROOT)
st.dataframe(evidence_checklist, hide_index=True, width="stretch")
st.info(
    "Readiness status is descriptive, not a numerical risk score. Items marked not connected or unverified "
    "must not be treated as evidence that the hazard or exposure is absent."
)

st.header("3. Assessment status")
assessment = assessment_summary(inputs)
st.error(assessment["status"], icon=":material/priority_high:")
st.write("**Method:**", assessment["method"])
st.write("**Selected hazard(s):**", assessment["hazards"])
st.write("**Interpretation:**", assessment["interpretation"])
st.warning(assessment["additional_caution"])
st.caption("No user-entered value is treated as verified. River-level values are recorded in the report but never compared with a threshold in this workflow.")

st.header("4. Compare hypothetical scenarios")
st.caption("The following cases differ only by their stated assumptions. Possible pathways are planning prompts, not calculated impacts.")
scenarios = build_scenario_comparison(inputs)
st.dataframe(scenarios, hide_index=True, width="stretch")

st.header("5. Compare mitigation actions")
st.write("Candidate actions below are qualitative planning prompts. Costs and impact estimates start blank and must be supported by your own documented evidence.")
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

st.header("6. Compare action combinations within a budget")
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

st.header("7. Generate a report")
report = report_rows(inputs, evidence, scenarios, actions, budget, combinations, ROOT, evidence_checklist=evidence_checklist)
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

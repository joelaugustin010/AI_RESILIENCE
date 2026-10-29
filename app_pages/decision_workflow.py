"""Connected evidence-to-budget workflow for the AI RESILIENCE prototype."""

from pathlib import Path
import re
import json

import pandas as pd
import streamlit as st

from src.scientific_scenario_engine import build_scientific_scenario_frame
from src.source_registry import build_source_registry, source_fitness_summary
from src.disaster_data_catalog import get_catalog, validate_catalog_record
from src.consequence_data_requirements import HAZARD_REQUIREMENTS, requirements_for_hazard, requirements_table
from src.consequence_assessment import build_consequence_assessment
from src.scenario_input_quality import evaluate_scenario_readiness

from src.decision_workflow import (
    HAZARD_OPTIONS,
    assessment_summary,
    build_scenario_comparison,
    budget_summary,
    compare_action_combinations,
    evidence_inventory,
    expand_hazards,
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
    st.dataframe(pd.DataFrame(registry_view), hide_index=True, width="stretch")
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
    st.dataframe(pd.DataFrame([{
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
    st.dataframe(pd.DataFrame(requirements_table(requirement_hazard)), hide_index=True, width="stretch")
    st.markdown("**Specific blockers before consequence estimates:**")
    st.warning(req["current_blockers"])
    st.markdown("**Potential authoritative starting sources:**")
    st.write(req["starter_sources"])
    st.markdown("**Validation rule:** every hazard needs independent event/outcome evidence, a baseline comparison, event- or time-separated evaluation, uncertainty reporting, and a documented intended-use boundary.")
    with st.expander("Shared minimum requirements across every hazard"):
        st.dataframe(pd.DataFrame(req["common_requirements"]), hide_index=True, width="stretch")

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

st.subheader("Scientific scenario frame and evidence gates")
scientific_frame = build_scientific_scenario_frame(inputs)
st.error(scientific_frame["evidence_gate"])
st.caption(
    "This frame structures the reasoning into hazard, exposure, vulnerability, and consequences to investigate. "
    "It does not calculate a probability, impact estimate, or warning."
)
if scientific_frame["pathways"]:
    st.dataframe(pd.DataFrame(scientific_frame["pathways"]), hide_index=True, width="stretch")
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
st.info(input_quality["reason"])

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
# Include the same evidence-gated scientific frame in exports so caveats survive outside the app.
frame_rows = [
    {"Section": "Scientific scenario frame", "Item": row["Reasoning stage"],
     "Detail": f'{row["Hazard component"]}: {row["Question to investigate"]} — {row["Status"]}'}
    for row in scientific_frame["pathways"]
]
frame_rows.extend(
    {"Section": "Scientific evidence gate", "Item": "Required evidence", "Detail": item}
    for item in scientific_frame["required_evidence"]
)
frame_rows.extend(
    {"Section": "Scientific limitation", "Item": "Safeguard", "Detail": item}
    for item in scientific_frame["limitations"]
)
frame_rows.append({"Section": "Scientific evidence gate", "Item": "Status", "Detail": scientific_frame["evidence_gate"]})
report = pd.concat([report, pd.DataFrame(frame_rows)], ignore_index=True, sort=False)
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

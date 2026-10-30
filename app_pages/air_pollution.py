"""AQI monitoring and evidence readiness for Kochi and Ernakulam."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from src.air_quality import (
    CPCB_AQI_CATEGORIES,
    cpcb_aqi_category,
    time_series_summary,
)
from src.air_quality_attribution import assess_industrial_sources
from src.air_quality_readiness import audit_air_quality_datasets
from src.air_quality_monthly_reports import (
    MonthlyReportError,
    compare_monthly_report_values,
    load_eloor_monthly_report,
    monthly_report_coverage,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "reference" / "air_quality_acquisition.json"
SUMMARY = ROOT / "data" / "processed" / "air_quality" / "kspcb_annual_aqi.csv"
SUMMARY_METADATA = ROOT / "data" / "processed" / "air_quality" / "kspcb_annual_aqi.metadata.json"
REPORTS = ROOT / "data" / "processed" / "air_quality"
INDUSTRIAL = ROOT / "data" / "processed" / "industrial"
def load_source_register() -> dict:
    """Load the reviewed source-status record; no sample measurement is used."""
    with REGISTER.open(encoding="utf-8") as source_file:
        return json.load(source_file)


def read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.ParserError):
        return pd.DataFrame()


st.title("Air quality in Kochi")

# This read-only audit is intentionally separate from AQI calculation and
# industrial attribution. A passed file-integrity check is not a data-quality
# certification or approval for forecasting.
air_readiness = audit_air_quality_datasets(ROOT)
st.subheader("Air-quality dataset readiness")
st.caption(
    f"Read-only audit: {air_readiness['dataset_count']} datasets; "
    f"{air_readiness['status_counts']['provisional']} provisional, "
    f"{air_readiness['status_counts']['unavailable']} unavailable, "
    f"{air_readiness['status_counts']['unsuitable']} unsuitable."
)
readiness_rows = [
    {
        "Dataset": item["name"],
        "Status": item["status"],
        "Rows": item["row_count"],
        "Coverage": (
            f"{item['date_start']} to {item['date_end']}"
            if item["date_start"] and item["date_end"] else "Not established"
        ),
        "Permitted use": item["permitted_use"],
    }
    for item in air_readiness["datasets"]
]
st.dataframe(
    pd.DataFrame(readiness_rows),
    hide_index=True,
    width="stretch",
    alt="Read-only readiness audit of processed air-quality datasets",
)
st.info(air_readiness["conclusion"])
with st.expander("Dataset audit details and blockers"):
    for item in air_readiness["datasets"]:
        st.markdown(f"**{item['name']} — {item['status']}**")
        st.caption(
            f"Integrity: {item['integrity_check']} | "
            f"Schema: {item['schema_check']} | "
            f"Forecast eligible: {item['forecast_training_eligible']}"
        )
        for limitation in item["limitations"]:
            st.write(f"- {limitation}")
        for error in item["errors"]:
            st.warning(error)
    for error in air_readiness["catalog_errors"]:
        st.warning(error)


try:
    register = load_source_register()
except (OSError, json.JSONDecodeError) as error:
    st.error(f"Air-pollution acquisition status could not be loaded: {error}")
    st.stop()

st.caption(f"Source review: {register['reviewed_on']}")
st.warning(
    "No live AQI feed is connected to this dashboard. The latest acquired station report is dated "
    "16 October 2026; the values below are historical source reports, not live readings."
)

daily_aqi = read_csv(REPORTS / "kspcb_daily_aqi_2026-10-16.csv")
daily_status = read_csv(REPORTS / "kspcb_daily_aqi_status_2026-10-16.csv")
monthly_reports = {}
monthly_report_errors = {}
for report_month in ("2026-08", "2026-09"):
    try:
        monthly_reports[report_month] = load_eloor_monthly_report(REPORTS, report_month)
    except MonthlyReportError as error:
        monthly_report_errors[report_month] = str(error)

monthly_observations = (
    pd.concat([report["observations"] for report in monthly_reports.values()], ignore_index=True)
    if monthly_reports else pd.DataFrame()
)
monthly_aqi = (
    pd.concat([report["aqi"] for report in monthly_reports.values()], ignore_index=True)
    if monthly_reports else pd.DataFrame()
)
monthly_weather = (
    pd.concat([report["weather"] for report in monthly_reports.values()], ignore_index=True)
    if monthly_reports else pd.DataFrame()
)
verified_monthly = (
    pd.concat([report["validated_observations"] for report in monthly_reports.values()], ignore_index=True)
    if monthly_reports else pd.DataFrame()
)
namp_records = read_csv(REPORTS / "kspcb_namp_ernakulam_2025-06.csv")

st.subheader("Latest available station AQI report")
if daily_aqi.empty:
    st.info("The acquired daily AQI report extract is unavailable in this checkout.")
else:
    display_aqi = daily_aqi.copy()
    display_aqi["CPCB AQI category"] = display_aqi["source_aqi"].map(
        lambda value: cpcb_aqi_category(value)[0]
    )
    st.caption(
        "KSPCB source report date: 16 October 2026. AQI values are source-reported; "
        "the category label is mapped to CPCB's official band. These are historical readings."
    )
    columns = [
        "station", "observed_at", "source_aqi", "CPCB AQI category", "source_remark",
        "SO2_value", "CO_value", "PM2.5_value", "O3_value", "PM10_value", "NH3_value",
        "NOx_value", "NO_value", "NO2_value",
    ]
    display_aqi = display_aqi[columns].rename(
        columns={
            "station": "KSPCB station label",
            "observed_at": "Report date",
            "source_aqi": "Source-reported AQI",
            "source_remark": "KSPCB remark",
            "SO2_value": "SO₂ (µg/m³)",
            "CO_value": "CO (mg/m³)",
            "PM2.5_value": "PM2.5 (µg/m³)",
            "O3_value": "O₃ (µg/m³)",
            "PM10_value": "PM10 (µg/m³)",
            "NH3_value": "NH₃ (µg/m³)",
            "NOx_value": "NOx (µg/m³)",
            "NO_value": "NO (µg/m³)",
            "NO2_value": "NO₂ (µg/m³)",
        }
    )
    st.dataframe(display_aqi, hide_index=True, alt="Historical KSPCB station AQI and pollutant values")
    st.caption(
        "The report does not give exact per-pollutant averaging intervals, data completeness, "
        "station identifiers, or coordinates. Pollutant driver is not calculated. Source: "
        "[KSPCB Water and Air Quality Directory](https://kspcb.kerala.gov.in/water-and-air-quality-directory)."
    )
    if not daily_status.empty:
        st.write("Stations without a reported AQI in this report:")
        st.dataframe(
            daily_status.rename(
                columns={
                    "station": "KSPCB station label",
                    "observed_at": "Report date",
                    "source_status": "Reported status",
                }
            )[["KSPCB station label", "Report date", "Reported status"]],
            hide_index=True,
            alt="Stations marked unavailable in the KSPCB daily AQI report",
        )

st.subheader("Dated Eloor pollutant trends")
st.caption(
    "Historical KSPCB Eloor monthly reports: August and September 2026. These are source-reported "
    "daily values, not live readings. Source units and date-only precision are retained."
)
for report in monthly_reports.values():
    st.markdown(
        f"- [{report['label']} KSPCB CAAQMS report]({report['source_url']}) "
        f"(retrieved {report['source'].get('retrieved_on', 'date not recorded')})."
    )
if monthly_report_errors:
    for report_month, message in monthly_report_errors.items():
        st.warning(f"The {report_month} Eloor report was excluded because its data checks failed: {message}")

if not monthly_reports:
    st.info("No provenance-verified Eloor monthly report extract is available in this checkout.")
else:
    coverage = pd.concat(
        [monthly_report_coverage(report) for report in monthly_reports.values()],
        ignore_index=True,
    )
    st.markdown("**Report coverage and missing observations**")
    st.dataframe(
        coverage,
        hide_index=True,
        alt="Expected, reported, and missing dates for Eloor pollutant, AQI, and weather series",
    )
    st.caption(
        "Coverage counts reflect rows in the preserved extracts. A source value is not independently "
        "quality-certified; row-level quality/completeness information was not supplied."
    )

    if not verified_monthly.empty:
        station_inventory = sorted(verified_monthly["station"].dropna().unique().tolist())
        station = st.selectbox("Monitoring station", station_inventory, key="report_station")
        station_data = verified_monthly.loc[verified_monthly["station"].eq(station)]
        pollutants = sorted(station_data["pollutant"].unique().tolist())
        pollutant = st.selectbox("Pollutant", pollutants, key="report_pollutant")
        dates = pd.to_datetime(station_data["observed_at"])
        start_date, end_date = dates.min().date(), dates.max().date()
        selected_range = st.date_input(
            "Observation date range",
            value=(start_date, end_date),
            min_value=start_date,
            max_value=end_date,
            format="DD/MM/YYYY",
        )
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            selected_start, selected_end = selected_range
        else:
            selected_start = selected_end = selected_range

        series = time_series_summary(
            station_data, pollutant, include_unassessed=True
        )
        series_dates = pd.to_datetime(series["observed_at"]).dt.date
        series = series.loc[(series_dates >= selected_start) & (series_dates <= selected_end)]
        unit = station_data.loc[station_data["pollutant"].eq(pollutant), "unit"].iloc[0]
        if series.empty:
            st.info("No source-reported values are available for the selected pollutant and dates.")
        else:
            st.line_chart(
                series.set_index("observed_at")["mean_value"],
                y_label=f"{pollutant} ({unit})",
                alt=f"Historical daily KSPCB-reported {pollutant} values at Eloor from August through September 2026",
            )

        if not monthly_aqi.empty:
            st.markdown("**Historical source-reported Eloor AQI trend**")
            monthly_aqi_dates = pd.to_datetime(monthly_aqi["observed_at"]).dt.date
            selected_aqi = monthly_aqi.loc[
                (monthly_aqi_dates >= selected_start) & (monthly_aqi_dates <= selected_end)
            ]
            if not selected_aqi.empty:
                st.line_chart(
                    selected_aqi.set_index("observed_at")["source_aqi"],
                    y_label="Source-reported AQI (index)",
                    alt="Historical daily KSPCB-reported Eloor AQI for August and September 2026",
                )
        st.caption(
            "The reports provide one daily value per pollutant, but do not state the precise averaging "
            "interval, Eloor station coordinates, or row-level quality flags. The chart is descriptive. "
            "AQI is shown as published and is not a factory-emissions measurement."
        )
        if not monthly_weather.empty:
            weather_dates = pd.to_datetime(monthly_weather["observed_at"]).dt.date
            selected_weather = monthly_weather.loc[
                (weather_dates >= selected_start) & (weather_dates <= selected_end)
            ]
            with st.expander("Daily Eloor weather summaries for the selected dates"):
                st.dataframe(
                    selected_weather[
                        [
                            "observed_at", "wind_speed", "wind_speed_unit", "wind_direction",
                            "wind_direction_unit", "temperature", "temperature_unit",
                            "relative_humidity", "relative_humidity_unit",
                        ]
                    ],
                    hide_index=True,
                    alt="Historical KSPCB Eloor daily weather summaries by report date",
                )
                st.caption(
                    "Weather values are daily summaries. Exact averaging windows and station coordinates "
                    "are unavailable; same-date summaries alone do not provide subdaily meteorological "
                    "alignment for source attribution."
                )

    if len(monthly_reports) == 2:
        st.markdown("**August–September comparison for matched pollutant fields**")
        comparison = compare_monthly_report_values(monthly_reports.values())
        st.caption(
            "This table compares only Eloor pollutant fields with identical source units and the same "
            "daily-report averaging-period label in both months. Values are derived arithmetic means "
            "of the reported daily entries, not official monthly averages; no unit conversion is applied."
        )
        if comparison.empty:
            st.info("No pollutant fields have matching units and source period labels in both reports.")
        else:
            st.dataframe(
                comparison,
                hide_index=True,
                alt="Descriptive August and September means for matching Eloor pollutant report fields",
            )

st.subheader("NAMP report observations and station references")
if namp_records.empty:
    st.info("The KSPCB NAMP report extract is unavailable in this checkout.")
else:
    st.write(
        "The directory lists this PDF as August 2025, but its Ernakulam pages say June 2025. "
        "It contains dated pollutant values, station codes, coordinates and 24-hour SO₂/NO₂/RSPM "
        "averages, but the PDF does not state concentration units. The values are preserved "
        "in the source PDF and extracted CSV, and are excluded from concentration trends until "
        "units are verified."
    )
    station_rows = []
    for (code, label), group in namp_records.groupby(["station_code", "station"]):
        coordinate_pairs = group[["latitude", "longitude"]].drop_duplicates()
        coordinates_consistent = len(coordinate_pairs) == 1
        station_rows.append(
            {
                "NAMP station label": label,
                "Station code": code,
                "Dated samples": int(len(group)),
                "Latitude": coordinate_pairs.iloc[0]["latitude"] if coordinates_consistent else pd.NA,
                "Longitude": coordinate_pairs.iloc[0]["longitude"] if coordinates_consistent else pd.NA,
                "Coordinate note": "report value; CRS not stated" if coordinates_consistent else "conflicting row-level coordinates",
            }
        )
    st.dataframe(
        pd.DataFrame(station_rows),
        hide_index=True,
        alt="NAMP report station identifiers and source coordinates",
    )
    st.caption(
        "Kuttippadam coordinates vary across report rows, so no station coordinate is displayed. "
        "The report does not state a coordinate reference system or pollutant units."
    )

try:
    annual = pd.read_csv(SUMMARY)
except (OSError, pd.errors.ParserError):
    annual = pd.DataFrame()
try:
    with SUMMARY_METADATA.open(encoding="utf-8") as metadata_file:
        summary_metadata = json.load(metadata_file)
except (OSError, json.JSONDecodeError):
    summary_metadata = {}

if annual.empty:
    st.error("The validated KSPCB annual AQI summary is unavailable in this checkout.")
else:
    st.subheader("Latest source-reported annual AQI summary")
    available_years = sorted(annual["year"].dropna().astype(int).unique().tolist())
    latest_year = max(available_years)
    latest = annual.loc[
        annual["year"].eq(latest_year) & annual["reference_station"].notna()
    ].copy()
    if latest.empty:
        st.info(
            f"KSPCB returned no exact-name NAMP matches for the documented Kochi/Ernakulam "
            f"station reference in year label {latest_year}."
        )
    else:
        st.write(
            f"**Year label:** {latest_year}. KSPCB labels this an annual average, but the "
            "endpoint does not state the exact measurement cutoff or any observation timestamp. "
            "The 2026 summary may be year-to-date. The year label is not a current-reading timestamp."
        )
        st.dataframe(
            latest[["reference_station", "source_station_code", "source_station", "monitoring_mode", "average_aqi"]]
            .rename(
                columns={
                    "reference_station": "Station reference",
                    "source_station_code": "KSPCB station code",
                    "source_station": "KSPCB station label",
                    "monitoring_mode": "Network",
                    "average_aqi": "Source-reported annual average AQI",
                }
            ),
            hide_index=True,
            width="stretch",
        )
    st.caption(
        f"Source: [KSPCB IPAM air-quality dashboard](https://kspcbipam.kerala.gov.in/Dashboard/airQuality) "
        f"and its [year-labeled AQI endpoint](https://kspcbipam.kerala.gov.in/Dashboard/fetch_air_quality_data?year={latest_year}). "
        f"Retrieved {summary_metadata.get('retrieved_at_utc', 'date recorded in dataset metadata')}. "
        "Values are index summaries (unitless), not pollutant concentrations. Station mapping "
        "requires exact normalized name and matching NAMP program; similar station names remain unmatched."
    )
    st.info(
        "CPCB AQI category bands are shown below for interpreting a valid AQI. This page does not "
        "assign daily AQI categories to KSPCB annual averages: an annual mean is not a dated "
        "24-hour/8-hour AQI observation."
    )

    st.subheader("Historical annual summaries")
    matched = annual.loc[annual["reference_station"].notna()].copy()
    if matched.empty:
        st.info("No exact-name station matches are available for historical comparisons.")
    else:
        stations = sorted(matched["reference_station"].unique().tolist())
        selected_station = st.selectbox("Monitoring station", stations)
        selected = matched.loc[matched["reference_station"].eq(selected_station)].sort_values("year")
        st.dataframe(
            selected[["year", "source_station", "source_station_code", "monitoring_mode", "average_aqi"]]
            .rename(
                columns={
                    "year": "Source year label",
                    "source_station": "KSPCB station label",
                    "source_station_code": "KSPCB station code",
                    "monitoring_mode": "Network",
                    "average_aqi": "Annual average AQI",
                }
            ),
            hide_index=True,
            width="stretch",
        )
        if selected["year"].nunique() >= 2:
            st.line_chart(
                selected.set_index("year")["average_aqi"],
                y_label="Source-reported annual average AQI",
            )
        st.caption(
            "These are year-labeled annual summaries only. The source response provides no exact "
            "aggregation cutoff; 2026 may be year-to-date. Retrieval time records when this file "
            "was acquired, not when the air was measured."
        )

st.subheader("AQI categories and CPCB method")
category_table = pd.DataFrame(
    [
        {"AQI range": f"{low}–{high}", "Category": category, "Health meaning": meaning}
        for low, high, category, meaning in CPCB_AQI_CATEGORIES
    ]
)
st.dataframe(category_table, hide_index=True, alt="CPCB AQI categories and health meanings")
st.markdown(
    "CPCB uses 24-hour averages for PM2.5, PM10, SO2, NO2, NH3 and Pb, and 8-hour averages "
    "for CO and O3; the highest sub-index is the AQI. Overall AQI requires at least three "
    "pollutants, including PM2.5 or PM10, and at least 16 hours of data for a sub-index. "
    "KSPCB's daily reports do not state exact pollutant averaging or completeness here, so this "
    "page displays source-reported AQI and does not recalculate AQI or identify a driving pollutant. "
    "See the official [CPCB AQI method](https://www.cpcb.nic.in/displaypdf.php?id=bmF0aW9uYWwtYWlyLXF1YWxpdHktaW5kZXgvSG93X0FRSV9DYWxjdWxhdGVkLnBkZg%3D%3D) "
    "and [CPCB AQI category table](https://airquality.cpcb.gov.in/ccr_docs/About_AQI.pdf)."
)

st.subheader("Documented NAMP network reference")
stations = pd.DataFrame(register["kspcb_namp_ernakulam_stations"])
st.dataframe(stations, hide_index=True, alt="KSPCB Ernakulam NAMP monitoring-station inventory")
st.caption(
    "The KSPCB directory station inventory is a network reference. June 2025 report pages also "
    "contain station codes and row-level coordinates; the report does not specify their coordinate "
    "reference system."
)

st.subheader("Potential industrial contributors: unranked candidates")
facility_candidates = read_csv(INDUSTRIAL / "edayar_candidate_facilities.csv")
industry_type_counts = read_csv(INDUSTRIAL / "edayar_estate_industry_type_counts.csv")
if facility_candidates.empty:
    st.info("The source-linked Edayar candidate-facility inventory is unavailable in this checkout.")
else:
    st.write(
        "The KWA engineering report names these major Edayar industries. They are candidates "
        "by estate presence only; this list does not establish that any facility emitted the "
        "measured pollutant. Individual coordinates, firm-specific types and air-emissions data "
        "were not found in the reviewed records."
    )
    display_candidates = facility_candidates[
        [
            "facility_name_as_published",
            "industry_type_as_individually_documented",
            "historical_consent_or_effluent_record",
            "current_consent_status",
            "air_emissions_data",
            "ranking_status",
        ]
    ].rename(
        columns={
            "facility_name_as_published": "Facility name in KWA report",
            "industry_type_as_individually_documented": "Individual industry type",
            "historical_consent_or_effluent_record": "Historical consent/effluent record",
            "current_consent_status": "Current consent status",
            "air_emissions_data": "Air-emissions data",
            "ranking_status": "Assessment status",
        }
    )
    st.dataframe(
        display_candidates,
        hide_index=True,
        alt="Edayar facilities listed as candidates with current evidence gaps",
    )

if not industry_type_counts.empty:
    st.markdown("**Estate-level trade-effluent industry categories reported by KWA**")
    st.dataframe(
        industry_type_counts,
        hide_index=True,
        alt="Edayar estate industry-type counts from KWA",
    )
    st.caption("These area-level counts are not mapped to the named candidate facilities.")

monthly_provenance_verified = bool(monthly_reports) and not monthly_observations.empty
weather_provenance_verified = bool(monthly_reports) and not monthly_weather.empty

source_assessment = assess_industrial_sources(
    facility_candidates.to_dict("records") if not facility_candidates.empty else [],
    monthly_observations if not monthly_observations.empty else None,
    sorted(monthly_observations["station"].dropna().unique().tolist())
    if not monthly_observations.empty else [],
    monthly_weather if not monthly_weather.empty else None,
    as_of=date.today(),
    ambient_evidence_type="measured",
    ambient_provenance_verified=monthly_provenance_verified,
    meteorology_provenance_verified=weather_provenance_verified,
    # The daily report has unspecified averaging intervals and no verified site
    # coordinates, so its wind series cannot pass the time-matching gate.
    meteorology_site_verified=False,
)
st.subheader("Industrial source assessment readiness")
st.info(
    "No potential-source ranking is supported. "
    + source_assessment["message"]
    + " Ambient concentration reporting is descriptive and remains separate from factory attribution."
)
ambient_evidence = source_assessment["ambient_evidence"]
st.caption(
    "Ambient records: "
    f"{ambient_evidence['validated_record_count']} validated source-reported rows; "
    f"{ambient_evidence['quality_eligible_record_count']} pass the row-level QA filter for attribution. "
    "AQI is an index, not a factory emission measurement. Permit limits are not measured emissions."
)
if ambient_evidence["validation_error"]:
    st.caption("Ambient validation: " + ambient_evidence["validation_error"])
if source_assessment["candidates"]:
    readiness_table = pd.DataFrame(
        [
            {
                "Facility": candidate["facility_name"],
                "Assessment status": candidate["status"],
                "Evidence still needed": "; ".join(candidate["missing_evidence"]),
            }
            for candidate in source_assessment["candidates"]
        ]
    )
    st.dataframe(
        readiness_table,
        hide_index=True,
        alt="Evidence readiness for each unranked Edayar candidate facility",
    )
st.caption(
    "The August and September Eloor values are historical, day-level source-reported concentrations. Their exact "
    "averaging windows are unspecified and row-level QA is unassessed. Facility coordinates, "
    "measured stack-emission results, source signatures, and method-ready time-matched meteorology "
    "are not available. Historical water-effluent permissions are not air-emissions evidence."
)

st.info(
    "Illustrative sample only: `data/raw/air_pollution_data.csv` contains undocumented example "
    "facility rows. It is never used for this assessment and cannot establish a source."
)

st.subheader("Current blockers and next data request")
for item in register["not_obtained"]:
    st.markdown(f"- **Not obtained or not verified:** {item}")
st.markdown(
    "Request from KSPCB/CPCB the exact averaging and completeness metadata for the published "
    "CAAQMS readings and concentration units for the June 2025 NAMP report. Request current "
    "consent certificates, facility-specific coordinates and air-emission/stack records for "
    "Edayar, plus time-matched meteorology and competing-source data, before designing a "
    "potential-source ranking."
)

st.subheader("Sources, retrieval metadata and limitations")
for source in register["sources"]:
    st.markdown(f"- [{source['publisher']}]({source['url']}) — {source['status']}")
with st.expander("Evidence and reuse notes"):
    for source in register["sources"]:
        st.markdown(f"**{source['publisher']}**")
        st.write(source["evidence"])
        st.caption(f"Coverage: {source['geographic_coverage']}")
        st.caption(f"Limitations/blocker: {source['blocker']}")
        st.caption(f"Reuse: {source['reuse_status']} | Reviewed: {source['reviewed_on']}")

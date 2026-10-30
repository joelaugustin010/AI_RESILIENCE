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
from src.cpcb_aqi import calculate_ind_aqi
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


st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.55rem;
        padding-bottom: 3.5rem;
        max-width: 1480px;
    }

    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at 8% 2%, rgba(111, 190, 210, 0.10), transparent 27rem),
            linear-gradient(180deg, rgba(244, 249, 250, 0.45), transparent 24rem);
    }

    .air-hero {
        position: relative;
        overflow: hidden;
        padding: 34px 36px 30px;
        border: 1px solid rgba(91, 164, 190, 0.28);
        border-radius: 22px;
        background: linear-gradient(118deg, #e6f4f8 0%, #f1f8f6 54%, #f8fbfa 100%);
        box-shadow: 0 12px 34px rgba(27, 73, 91, 0.07);
        margin: 4px 0 22px;
    }

    .air-hero:after {
        content: "";
        position: absolute;
        width: 240px;
        height: 240px;
        right: -70px;
        top: -115px;
        border: 1px solid rgba(44, 129, 151, 0.18);
        border-radius: 50%;
        box-shadow: 0 0 0 26px rgba(44, 129, 151, 0.035), 0 0 0 54px rgba(44, 129, 151, 0.025);
        pointer-events: none;
    }

    .air-eyebrow {
        color: #28768b;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 2.2px;
        text-transform: uppercase;
    }

    .air-heading {
        color: #173d50;
        font-size: clamp(2rem, 4vw, 2.7rem);
        font-weight: 800;
        letter-spacing: -1.2px;
        line-height: 1.12;
        margin: 10px 0 12px;
    }

    .air-description {
        color: #496675;
        font-size: 1.02rem;
        line-height: 1.7;
        max-width: 850px;
        margin-bottom: 0;
    }

    .air-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 20px;
    }

    .air-meta span {
        display: inline-block;
        padding: 6px 11px;
        border: 1px solid rgba(47, 119, 139, 0.18);
        border-radius: 999px;
        color: #315e6d;
        background: rgba(255,255,255,0.62);
        font-size: 0.76rem;
        font-weight: 650;
    }

    div[data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.82);
        border: 1px solid rgba(87, 143, 160, 0.19);
        border-radius: 15px;
        padding: 15px 17px;
        box-shadow: 0 5px 18px rgba(31, 76, 92, 0.045);
    }

    div[data-testid="stMetricLabel"] {
        color: #587481;
        font-weight: 650;
    }

    div[data-testid="stMetricValue"] {
        color: #183f51;
        font-weight: 780;
    }

    .air-nav {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 10px 0 18px;
        margin-bottom: 8px;
        border-bottom: 1px solid rgba(92, 148, 164, 0.18);
    }

    .air-nav a {
        display: inline-block;
        padding: 7px 11px;
        border: 1px solid rgba(71, 132, 151, 0.20);
        border-radius: 999px;
        color: #285b6c !important;
        background: rgba(255,255,255,0.78);
        text-decoration: none !important;
        font-size: 0.78rem;
        font-weight: 650;
    }

    .air-nav a:hover {
        background: #e5f3f6;
        border-color: rgba(71, 132, 151, 0.42);
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(100, 160, 180, 0.22);
        border-radius: 13px;
        overflow: hidden;
        background: rgba(255,255,255,0.86);
    }

    div[data-testid="stExpander"] {
        border: 1px solid rgba(100, 160, 180, 0.24);
        border-radius: 13px;
        background: rgba(255,255,255,0.62);
    }

    h2, h3 {
        color: #1d4c5e;
        letter-spacing: -0.35px;
    }

    hr {
        border-color: rgba(92, 148, 164, 0.18);
    }

    @media (max-width: 700px) {
        .air-hero {
            padding: 25px 21px;
        }
        .air-heading {
            font-size: 2rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown(
    """
    <div class="air-hero">
        <div class="air-eyebrow">
            AI RESILIENCE · ENVIRONMENTAL MONITORING
        </div>
        <div class="air-heading">
            Air Quality Intelligence
        </div>
        <p class="air-description">
            Historical air-quality observations, monitoring-network coverage,
            pollutant trends and scientific evidence assessment for
            Kochi, Eloor and Edayar, Kerala.
        </p>
        <div class="air-meta">
            <span>KOCHI · KERALA · INDIA</span>
            <span>ELOOR–EDAYAR INDUSTRIAL BELT</span>
            <span>HISTORICAL EVIDENCE VIEW</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
st.markdown(
    """
    <nav class="air-nav">
        <a href="#latest-report">Latest report</a>
        <a href="#eloor-trends">Eloor trends</a>
        <a href="#namp-network">NAMP network</a>
        <a href="#annual-aqi">Annual AQI</a>
        <a href="#cpcb-method">CPCB method</a>
        <a href="#industrial-evidence">Industrial evidence</a>
        <a href="#sources">Sources</a>
    </nav>
    """,
    unsafe_allow_html=True,
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

# Executive overview: show only facts that are directly available in the loaded extracts.
latest_extract_date = (
    pd.to_datetime(daily_aqi["observed_at"], errors="coerce").max().date()
    if not daily_aqi.empty and "observed_at" in daily_aqi.columns
    and pd.to_datetime(daily_aqi["observed_at"], errors="coerce").notna().any()
    else None
)
station_count = int(daily_aqi["station"].nunique()) if not daily_aqi.empty and "station" in daily_aqi.columns else 0
eloor_daily_rows = (
    daily_aqi.loc[daily_aqi["station"].astype(str).str.strip().str.casefold().eq("eloor")]
    if not daily_aqi.empty and "station" in daily_aqi.columns
    else pd.DataFrame()
)
eloor_source_aqi = "Unavailable"
if not eloor_daily_rows.empty and "source_aqi" in eloor_daily_rows.columns:
    raw_eloor_aqi = pd.to_numeric(
        pd.Series([eloor_daily_rows.iloc[0]["source_aqi"]]), errors="coerce"
    ).iloc[0]
    if pd.notna(raw_eloor_aqi) and 0 <= int(raw_eloor_aqi) <= 500:
        eloor_category = cpcb_aqi_category(int(raw_eloor_aqi))[0]
        eloor_source_aqi = f"{int(raw_eloor_aqi)} · {eloor_category}"
st.markdown("### Air quality at a glance")
overview = st.columns(5)
overview[0].metric("Latest loaded report", latest_extract_date.strftime("%d %b %Y") if latest_extract_date else "Unavailable")
overview[1].metric("Eloor source AQI", eloor_source_aqi, help="Source-reported value from the 16 October 2026 KSPCB daily extract; not a live reading.")
overview[2].metric("Stations in daily extract", station_count)
overview[3].metric("Eloor monthly reports", len(monthly_reports), help="August and September 2026 source reports when both pass ingestion checks.")
overview[4].metric("AQI calculation", "Evidence-gated", help="The app calculates AQI only when averaging period, valid hours and QA flags meet CPCB requirements.")
st.caption(
    "This is a historical research dashboard, not a live public warning service. "
    "Each chart and table retains its source date, unit and evidence limitations."
)
with st.expander("How to read this dashboard"):
    st.markdown(
        """
        - **Source-reported AQI** is reproduced from the cited KSPCB report.
        - **Calculated indicator** is shown only when CPCB input requirements are demonstrated.
        - **Historical pollutant trends** describe reported observations; they do not identify an emitting facility.
        - **Industrial candidates** are evidence leads, not accusations or ranked pollution sources.
        """
    )

st.divider()
st.markdown('<div id="latest-report"></div>', unsafe_allow_html=True)
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

    # A focused Eloor snapshot makes the industrial-belt report easier to scan.
    # Values are copied from the dated KSPCB extract; no unit conversion or averaging is applied.
    eloor_rows = daily_aqi.loc[
        daily_aqi["station"].astype(str).str.strip().str.casefold().eq("eloor")
    ]
    if not eloor_rows.empty:
        eloor_row = eloor_rows.iloc[0]
        st.markdown("#### Eloor pollutant snapshot")
        st.caption("KSPCB source-reported values · 16 October 2026 · historical, not live")
        snapshot_pollutants = (
            ("PM2.5", "PM2.5_value", "unit_PM2.5"),
            ("PM10", "PM10_value", "unit_PM10"),
            ("Nitrogen dioxide (NO₂)", "NO2_value", "unit_NO2"),
            ("Sulphur dioxide (SO₂)", "SO2_value", "unit_SO2"),
            ("Ozone (O₃)", "O3_value", "unit_O3"),
            ("Carbon monoxide (CO)", "CO_value", "unit_CO"),
        )
        available_snapshot = []
        for label, value_column, unit_column in snapshot_pollutants:
            value = pd.to_numeric(pd.Series([eloor_row.get(value_column)]), errors="coerce").iloc[0]
            if pd.notna(value):
                unit = str(eloor_row.get(unit_column, "")).strip()
                available_snapshot.append((label, f"{value:g} {unit}".strip()))
        for start in range(0, len(available_snapshot), 3):
            metric_columns = st.columns(3)
            for metric_column, (label, value) in zip(
                metric_columns, available_snapshot[start:start + 3]
            ):
                metric_column.metric(label, value)
        st.caption(
            "These are the values as published in the daily extract. The report does not identify "
            "the precise averaging interval or provide valid-hour counts and row-level QA; "
            "do not compare them with health thresholds as if those conditions were verified."
        )

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

st.markdown('<div id="eloor-trends"></div>', unsafe_allow_html=True)
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
            ].copy()
            st.markdown("**Meteorological context — source-data quality review**")
            st.caption(
                "KSPCB-published daily weather summaries for Eloor, shown separately from pollutant "
                "measurements. These are contextual observations, not a dispersion model."
            )
            if selected_weather.empty:
                st.info("No weather summaries are available for the selected dates.")
            else:
                numeric_weather = (
                    "wind_speed", "wind_direction", "temperature", "relative_humidity"
                )
                for field in numeric_weather:
                    selected_weather[field] = pd.to_numeric(
                        selected_weather[field], errors="coerce"
                    )

                humidity_invalid = (
                    selected_weather["relative_humidity"].notna()
                    & ~selected_weather["relative_humidity"].between(0, 100)
                )
                direction_invalid = (
                    selected_weather["wind_direction"].notna()
                    & ~selected_weather["wind_direction"].between(0, 360, inclusive="left")
                )
                negative_wind = (
                    selected_weather["wind_speed"].notna()
                    & selected_weather["wind_speed"].lt(0)
                )
                high_wind_review = (
                    selected_weather["wind_speed"].notna()
                    & selected_weather["wind_speed"].gt(20)
                )

                weather_metrics = st.columns(3)
                weather_metrics[0].metric(
                    "Dated weather records", len(selected_weather)
                )
                weather_metrics[1].metric(
                    "Humidity outside 0–100%", int(humidity_invalid.sum())
                )
                weather_metrics[2].metric(
                    "Wind speed >20 m/s · review", int(high_wind_review.sum())
                )

                temperature_series = selected_weather.dropna(
                    subset=["temperature"]
                ).set_index("observed_at")["temperature"]
                wind_series = selected_weather.dropna(
                    subset=["wind_speed"]
                ).set_index("observed_at")["wind_speed"]
                humidity_series = selected_weather.loc[
                    ~humidity_invalid & selected_weather["relative_humidity"].notna()
                ].set_index("observed_at")["relative_humidity"]

                weather_left, weather_right = st.columns(2)
                with weather_left:
                    st.markdown("**Reported daily temperature**")
                    if not temperature_series.empty:
                        st.line_chart(
                            temperature_series,
                            y_label="Temperature (°C)",
                            alt="KSPCB-reported daily Eloor temperature summaries",
                        )
                    else:
                        st.info("No numeric temperature summaries are available.")
                with weather_right:
                    st.markdown("**Reported daily wind speed**")
                    if not wind_series.empty:
                        st.line_chart(
                            wind_series,
                            y_label="Wind speed (m/s)",
                            alt="KSPCB-reported daily Eloor wind-speed summaries",
                        )
                    else:
                        st.info("No numeric wind-speed summaries are available.")

                st.markdown("**Relative humidity — physically valid values only**")
                if not humidity_series.empty:
                    st.line_chart(
                        humidity_series,
                        y_label="Relative humidity (%)",
                        alt="KSPCB-reported Eloor relative humidity after excluding values outside 0 to 100 percent",
                    )
                else:
                    st.info("No relative-humidity values pass the 0–100% physical range check.")

                flagged_weather = selected_weather.loc[
                    humidity_invalid | direction_invalid | negative_wind | high_wind_review
                ].copy()
                if not flagged_weather.empty:
                    flagged_weather["App review note"] = ""
                    flagged_weather.loc[humidity_invalid, "App review note"] += (
                        "Relative humidity outside physical 0–100% range; "
                    )
                    flagged_weather.loc[direction_invalid, "App review note"] += (
                        "Wind direction outside 0–360° range; "
                    )
                    flagged_weather.loc[negative_wind, "App review note"] += (
                        "Negative wind speed; "
                    )
                    flagged_weather.loc[high_wind_review, "App review note"] += (
                        "Wind speed above 20 m/s review threshold; not automatically rejected; "
                    )
                    st.markdown("**Records requiring review**")
                    st.dataframe(
                        flagged_weather[
                            [
                                "observed_at", "wind_speed", "wind_direction",
                                "temperature", "relative_humidity", "App review note",
                            ]
                        ],
                        hide_index=True,
                        alt="Eloor daily weather records flagged by transparent physical-range and review checks",
                    )
                else:
                    st.success("No values triggered the displayed weather review checks.")

                st.caption(
                    "Humidity outside 0–100% is excluded from its chart. Wind speeds above 20 m/s "
                    "are flagged for source review only and remain visible in the wind chart; this "
                    "app threshold is not a KSPCB quality flag. The source does not state exact "
                    "averaging windows or station coordinates. Daily same-date summaries cannot "
                    "establish subdaily wind alignment, atmospheric dispersion, or an industrial "
                    "source relationship."
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

st.markdown('<div id="namp-network"></div>', unsafe_allow_html=True)
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
    st.markdown('<div id="annual-aqi"></div>', unsafe_allow_html=True)
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

st.markdown('<div id="cpcb-method"></div>', unsafe_allow_html=True)
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

st.subheader("CPCB calculation eligibility — acquired daily report")
st.caption(
    "The calculation engine is connected to the acquired station records. It only calculates "
    "an application AQI when each included pollutant has a valid quality flag, the prescribed "
    "averaging period, at least 16 valid hours, and the station has at least three eligible "
    "pollutants including PM2.5 or PM10."
)
if daily_aqi.empty:
    st.info("No acquired daily report is available to assess for CPCB calculation eligibility.")
else:
    eligibility_rows = []
    pollutant_fields = (
        ("PM2.5", "PM2.5_value", "unit_PM2.5"),
        ("PM10", "PM10_value", "unit_PM10"),
        ("NO2", "NO2_value", "unit_NO2"),
        ("SO2", "SO2_value", "unit_SO2"),
        ("CO", "CO_value", "unit_CO"),
        ("O3", "O3_value", "unit_O3"),
        ("NH3", "NH3_value", "unit_NH3"),
    )
    for _, source_row in daily_aqi.iterrows():
        records = []
        for pollutant, value_column, unit_column in pollutant_fields:
            value = source_row.get(value_column)
            if pd.notna(value):
                records.append(
                    {
                        "pollutant": pollutant,
                        "concentration": value,
                        "unit": source_row.get(unit_column),
                        "averaging_period": source_row.get("averaging_period"),
                        "valid_hours": None,
                        "quality_flag": source_row.get("quality_flag"),
                    }
                )
        readiness = calculate_ind_aqi(records)
        eligibility_rows.append(
            {
                "Station": source_row.get("station"),
                "Source-reported AQI": source_row.get("source_aqi"),
                "Application AQI": readiness["aqi"],
                "Calculation status": readiness["status"],
                "Eligible pollutants": readiness["eligible_pollutant_count"],
                "Reason": "; ".join(
                    readiness.get("missing_requirements", [])
                    + [
                        f"{item['pollutant']}: {item['reason']}"
                        for item in readiness.get("excluded_records", [])
                    ]
                ) or "Eligible for CPCB calculation",
            }
        )
    st.dataframe(
        pd.DataFrame(eligibility_rows),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "No application-calculated AQI is produced for the current extract: its averaging "
        "interval is unspecified, row-level quality is unassessed, and valid-hour counts are "
        "not supplied. Source-reported AQI remains displayed separately and is not overwritten."
    )

st.subheader("Documented NAMP network reference")
stations = pd.DataFrame(register["kspcb_namp_ernakulam_stations"])
st.dataframe(stations, hide_index=True, alt="KSPCB Ernakulam NAMP monitoring-station inventory")
st.caption(
    "The KSPCB directory station inventory is a network reference. June 2025 report pages also "
    "contain station codes and row-level coordinates; the report does not specify their coordinate "
    "reference system."
)

st.markdown('<div id="industrial-evidence"></div>', unsafe_allow_html=True)
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

st.markdown('<div id="sources"></div>', unsafe_allow_html=True)
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

"""AQI monitoring and evidence readiness for Kochi and Ernakulam."""

import json
import importlib
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
import streamlit as st

from src.ui_theme import page_header, section_intro

try:
    import altair as alt
except ImportError:  # Streamlit normally installs Altair; retain a chart fallback.
    alt = None

from src.dataframe_display import display_dataframe

from src.air_quality import (
    AirQualityDataError,
    CPCB_AQI_CATEGORIES,
    cpcb_aqi_category,
    safe_cpcb_aqi_category,
    time_series_summary,
)
from src.air_quality_attribution import (
    SOURCE_EVIDENCE_REQUIREMENTS,
    assess_industrial_sources,
    evidence_action_plan,
)
from src.cpcb_aqi import calculate_ind_aqi
from src.air_quality_readiness import audit_air_quality_datasets
from src.air_quality_monthly_reports import (
    MonthlyReportError,
    compare_monthly_report_values,
    load_eloor_monthly_report,
    monthly_report_coverage,
)
from src import live_air_quality as live_air_quality_module
from src import air_quality_dashboard as air_quality_dashboard_module

live_air_quality_module = importlib.reload(live_air_quality_module)
air_quality_dashboard_module = importlib.reload(air_quality_dashboard_module)

from src.live_air_quality import (
    CAMS_ATTRIBUTION_URL,
    MODEL_SOURCE,
    OPEN_METEO_DOCS_URL,
    fetch_open_meteo,
    fetch_open_meteo_weather,
    aqi_category,
)
from src.air_background_model import (
    EVALUATION_PATH,
    BackgroundModelError,
    predict_next_hour,
)
from src.air_quality_dashboard import (
    DISASTER_AIR_INTELLIGENCE,
    HEALTH_INFORMATION,
    POLLUTANT_GUIDELINES,
    aggregate_co2_trend,
    assess_pollutant,
    compare_pollutant,
    co2_context,
    disaster_air_intelligence,
    evidence_category,
    scenario_aqi_summary,
    scenario_pollutant_values,
)
from src.disaster_air_dispersion import (
    INCIDENT_TYPES,
    LOCATION_PRESETS,
    STABILITY_CLASSES,
    SUPPORTED_POLLUTANTS,
    run_gaussian_plume,
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


def audit_daily_extract(data: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Describe completeness and basic validity without certifying source QA."""
    if data.empty:
        return {}, pd.DataFrame()

    parsed_dates = (
        pd.to_datetime(data["observed_at"], errors="coerce")
        if "observed_at" in data.columns
        else pd.Series(pd.NaT, index=data.index)
    )
    station_values = (
        data["station"].astype("string").str.strip().str.casefold()
        if "station" in data.columns
        else pd.Series(pd.NA, index=data.index, dtype="string")
    )
    duplicate_keys = pd.DataFrame(
        {"station": station_values, "date": parsed_dates}, index=data.index
    )
    duplicate_mask = (
        duplicate_keys["station"].notna()
        & duplicate_keys["station"].ne("")
        & duplicate_keys["date"].notna()
        & duplicate_keys.duplicated(keep="first")
    )
    raw_dates = data["observed_at"] if "observed_at" in data.columns else pd.Series(pd.NA, index=data.index)
    missing_date_count = int(raw_dates.isna().sum() + raw_dates.astype("string").str.strip().eq("").sum())
    invalid_date_count = int((raw_dates.notna() & raw_dates.astype("string").str.strip().ne("") & parsed_dates.isna()).sum())
    missing_station_count = int(station_values.isna().sum() + station_values.eq("").sum())

    aqi_values = (
        pd.to_numeric(data["source_aqi"], errors="coerce")
        if "source_aqi" in data.columns
        else pd.Series(float("nan"), index=data.index)
    )
    aqi_raw = data["source_aqi"] if "source_aqi" in data.columns else pd.Series(pd.NA, index=data.index)
    missing_aqi_count = int(aqi_raw.isna().sum() + aqi_raw.astype("string").str.strip().eq("").sum())
    aqi_present = aqi_raw.notna() & aqi_raw.astype("string").str.strip().ne("")
    invalid_aqi_mask = (
        aqi_values.isna()
        | ~aqi_values.between(0, 500)
        | aqi_values.mod(1).ne(0)
    )
    invalid_aqi_count = int((aqi_present & invalid_aqi_mask).sum())

    pollutant_specs = (
        ("PM2.5", "PM2.5_value", "unit_PM2.5", "ug/m3"),
        ("PM10", "PM10_value", "unit_PM10", "ug/m3"),
        ("SO₂", "SO2_value", "unit_SO2", "ug/m3"),
        ("NO₂", "NO2_value", "unit_NO2", "ug/m3"),
        ("NO", "NO_value", "unit_NO", "ug/m3"),
        ("NOx", "NOx_value", "unit_NOx", "ug/m3"),
        ("O₃", "O3_value", "unit_O3", "ug/m3"),
        ("NH₃", "NH3_value", "unit_NH3", "ug/m3"),
        ("CO", "CO_value", "unit_CO", "mg/m3"),
    )
    pollutant_rows = []
    for label, value_column, unit_column, expected_unit in pollutant_specs:
        if value_column not in data.columns:
            pollutant_rows.append({
                "Pollutant": label,
                "Numeric values": 0,
                "Missing values": len(data),
                "Non-numeric values": 0,
                "Negative values": 0,
                "Unit mismatches": len(data),
            })
            continue

        raw_values = data[value_column]
        present = raw_values.notna() & raw_values.astype("string").str.strip().ne("")
        numeric_values = pd.to_numeric(raw_values, errors="coerce")
        missing_count = int((~present).sum())
        nonnumeric_count = int((present & numeric_values.isna()).sum())
        negative_count = int((numeric_values.notna() & numeric_values.lt(0)).sum())

        if unit_column in data.columns:
            units = (
                data[unit_column].astype("string").str.strip().str.casefold()
                .str.replace("μ", "u", regex=False)
                .str.replace("µ", "u", regex=False)
                .str.replace("³", "3", regex=False)
            )
            unit_mismatch_count = int(
                (present & units.ne(expected_unit)).sum()
            )
        else:
            unit_mismatch_count = int(present.sum())

        pollutant_rows.append({
            "Pollutant": label,
            "Numeric values": int(numeric_values.notna().sum()),
            "Missing values": missing_count,
            "Non-numeric values": nonnumeric_count,
            "Negative values": negative_count,
            "Unit mismatches": unit_mismatch_count,
        })

    quality_flags = (
        data["quality_flag"].astype("string").str.strip().str.casefold()
        if "quality_flag" in data.columns
        else pd.Series(pd.NA, index=data.index, dtype="string")
    )
    known_quality_flags = {"valid", "suspect", "invalid", "unassessed"}
    present_quality_flags = quality_flags.notna() & quality_flags.ne("")
    pollutant_audit = pd.DataFrame(pollutant_rows)
    summary = {
        "rows": len(data),
        "stations": int(station_values.dropna().loc[lambda values: values.ne("")].nunique()),
        "duplicate_rows": int(duplicate_mask.sum()),
        "missing_dates": missing_date_count,
        "invalid_dates": invalid_date_count,
        "missing_stations": missing_station_count,
        "missing_aqi": missing_aqi_count,
        "invalid_aqi": invalid_aqi_count,
        "valid_qa_rows": int(quality_flags.eq("valid").sum()),
        "suspect_qa_rows": int(quality_flags.eq("suspect").sum()),
        "invalid_qa_rows": int(quality_flags.eq("invalid").sum()),
        "unassessed_rows": int(quality_flags.eq("unassessed").sum()),
        "missing_qa_rows": int((~present_quality_flags).sum()),
        "unknown_qa_rows": int((present_quality_flags & ~quality_flags.isin(known_quality_flags)).sum()),
        "pollutant_nonnumeric": int(pollutant_audit["Non-numeric values"].sum()),
        "pollutant_negative": int(pollutant_audit["Negative values"].sum()),
        "pollutant_unit_mismatches": int(pollutant_audit["Unit mismatches"].sum()),
    }
    return summary, pollutant_audit


st.markdown(
    """
    <style>
    /* Air-quality module: cyan accent and quiet industrial glass panels. */
    .air-nav {
      display: flex;
      flex-wrap: wrap;
      gap: .45rem;
      padding: .7rem 0 .35rem;
      margin: .1rem 0 1.1rem;
      border-bottom: 1px solid rgba(130, 190, 199, .14);
    }
    .air-nav a {
      display: inline-flex;
      align-items: center;
      min-height: 1.9rem;
      padding: .3rem .7rem;
      border: 1px solid rgba(92, 200, 232, .20);
      border-radius: 999px;
      color: #b9e6f2 !important;
      background: rgba(9, 33, 48, .62);
      text-decoration: none !important;
      font-size: .75rem;
      font-weight: 650;
      transition: background .18s var(--ar-ease), border-color .18s var(--ar-ease),
                  color .18s var(--ar-ease), transform .18s var(--ar-ease);
    }
    .air-nav a:hover {
      background: rgba(92, 200, 232, .12);
      border-color: rgba(92, 200, 232, .44);
      color: #e4fbff !important;
      transform: translateY(-1px);
    }
    .disaster-hero {
      position: relative;
      overflow: hidden;
      padding: 1.55rem 1.7rem;
      border-radius: 20px;
      background:
        radial-gradient(ellipse at 90% -20%, rgba(92, 200, 232, .20), transparent 20rem),
        linear-gradient(120deg, #071d2c 0%, #0a3446 56%, #0a4b55 100%);
      border: 1px solid rgba(92, 200, 232, .24);
      box-shadow: var(--ar-shadow-soft);
      color: #f2ffff;
      margin: 1rem 0 1.1rem;
    }
    .disaster-hero:after {
      content: "";
      position: absolute;
      width: 250px;
      height: 250px;
      right: -70px;
      top: -150px;
      border-radius: 50%;
      border: 1px solid rgba(92, 200, 232, .28);
      box-shadow: 0 0 0 26px rgba(92, 200, 232, .05), 0 0 0 56px rgba(92, 200, 232, .03);
      pointer-events: none;
    }
    .disaster-kicker {
      color: #a8ecf8;
      font-size: .7rem;
      font-weight: 800;
      letter-spacing: .16em;
      text-transform: uppercase;
    }
    .disaster-title {
      color: #f4ffff;
      font-size: clamp(1.7rem, 3.2vw, 2.45rem);
      font-weight: 800;
      letter-spacing: -.035em;
      line-height: 1.1;
      margin: .45rem 0 .45rem;
    }
    .disaster-subtitle {
      color: #c7e4ea;
      font-size: .98rem;
      line-height: 1.62;
      max-width: 790px;
      margin: 0;
    }
    .disaster-step {
      color: #7fdfea;
      font-size: .69rem;
      font-weight: 800;
      letter-spacing: .14em;
      text-transform: uppercase;
      margin: 1.4rem 0 .5rem;
    }
    .disaster-card {
      min-height: 104px;
      padding: .95rem 1rem;
      border: 1px solid rgba(130, 190, 199, .22);
      border-radius: 16px;
      background: linear-gradient(150deg, rgba(15, 44, 60, .95), rgba(9, 30, 44, .95));
      box-shadow: var(--ar-shadow-soft);
    }
    .disaster-card-title {
      color: #c8f4f8;
      font-weight: 750;
      font-size: .9rem;
      margin-bottom: .3rem;
    }
    .disaster-card-copy {
      color: #9fbec6;
      font-size: .78rem;
      line-height: 1.5;
    }
    .disaster-result {
      padding: 1.25rem 1.4rem;
      border-radius: 18px;
      background:
        radial-gradient(ellipse at 100% 0%, rgba(92, 200, 232, .12), transparent 18rem),
        linear-gradient(135deg, rgba(13, 54, 64, .96), rgba(9, 34, 48, .96));
      border: 1px solid rgba(92, 200, 232, .24);
      box-shadow: var(--ar-shadow-soft);
      margin: 1rem 0 .8rem;
    }
    .disaster-result-label {
      color: #9fe6ee;
      font-size: .69rem;
      font-weight: 800;
      letter-spacing: .13em;
      text-transform: uppercase;
    }
    .disaster-result-value {
      color: #f3ffff;
      font-size: clamp(1.8rem, 4vw, 2.7rem);
      font-weight: 800;
      letter-spacing: -.04em;
      line-height: 1.06;
      margin: .3rem 0 .25rem;
    }
    .disaster-result-copy {
      color: #a9c7cd;
      font-size: .82rem;
      line-height: 1.55;
    }
    .disaster-pill {
      display: inline-block;
      padding: .2rem .6rem;
      border-radius: 999px;
      background: rgba(92, 200, 232, .12);
      border: 1px solid rgba(92, 200, 232, .24);
      color: #b7f1fa;
      font-size: .71rem;
      font-weight: 700;
    }
    .disaster-empty {
      padding: 1.2rem 1.3rem;
      border: 1px dashed rgba(92, 200, 232, .32);
      border-radius: 16px;
      background: rgba(9, 33, 48, .55);
      color: #a9c7cd;
    }
    @media (max-width: 700px) {
      .disaster-hero { padding: 1.2rem 1.15rem; border-radius: 16px; }
      .air-nav { gap: .35rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


page_header(
    "AI RESILIENCE · ENVIRONMENTAL MONITORING",
    "Air Quality Intelligence",
    "Historical air-quality observations, monitoring-network coverage, pollutant trends and "
    "scientific evidence assessment for Kochi, Eloor and Edayar, Kerala.",
    meta=("Kochi · Kerala · India", "Eloor–Edayar industrial belt", "Historical evidence view"),
    accent="cyan",
    key="air-quality",
)


@st.cache_data(ttl=900, show_spinner=False)
def load_live_air_quality() -> dict:
    """Cache the model response for 15 minutes; timestamps remain untouched."""
    return fetch_open_meteo()


@st.fragment(run_every="15m")
def render_live_air_quality() -> None:
    st.markdown('<div id="live-feed"></div>', unsafe_allow_html=True)
    st.subheader("Kochi air-quality estimate")
    st.caption(
        "Near-real-time CAMS model estimate for Kochi (9.9312°N, 76.2673°E). "
        "This is not a CPCB/KSPCB monitoring-station measurement."
    )
    refresh = st.button("↻ Refresh live feed", key="air-live-refresh")
    if refresh:
        load_live_air_quality.clear()
    try:
        result = load_live_air_quality()
    except Exception as error:
        st.info(
            f"The Open-Meteo/CAMS model feed is temporarily unavailable: {error} "
            "Historical KSPCB observations remain available below."
        )
        return

    current = result["current"]
    observations = result["hourly"].copy()
    latest_observed = result["observed_at"]
    updated_label = latest_observed.strftime("%d %b %Y, %H:%M UTC") if latest_observed is not None else "Not reported"
    standard = st.radio("AQI standard", ("US AQI", "EAQI"), horizontal=True, key="air-aqi-standard")
    selected_label = "US AQI" if standard == "US AQI" else "European AQI"
    selected = current.get(selected_label)
    category = aqi_category(standard, selected.get("value") if selected else None)
    if selected and category:
        st.markdown(
            f'<div style="border:3px solid {category["color"]};border-radius:16px;padding:14px 18px;'
            f'background:linear-gradient(90deg,{category["color"]}18,transparent);">'
            f'<div style="font-size:.82rem;color:#9fbec6;">{standard} · CAMS/Open-Meteo model estimate</div>'
            f'<div style="font-size:2.7rem;font-weight:750;line-height:1.1;">{selected["value"]:g}</div>'
            f'<div style="font-weight:700;color:{category["color"]};">{category["label"]}</div>'
            f'<div style="font-size:.82rem;color:#9fbec6;">Kochi model grid · observed {updated_label}</div></div>',
            unsafe_allow_html=True,
        )
    top = st.columns(3)
    top[0].metric("Other AQI scale", _model_metric(current, "European AQI" if selected_label == "US AQI" else "US AQI"))
    top[1].metric("Last observed", updated_label)
    top[2].metric("Retrieved", result["retrieved_at"].strftime("%d %b %Y, %H:%M UTC"))
    st.caption(
        f"Source: {MODEL_SOURCE} · model grid response at {result['latitude']}, {result['longitude']} · "
        "hourly model estimate, not a station observation"
    )

    pollutant_order = ("PM2.5", "PM10", "NO2", "SO2", "CO", "O3")
    cards = st.columns(3)
    elevated_pollutants = []
    for index, pollutant in enumerate(pollutant_order):
        with cards[index % 3]:
            item = current.get(pollutant)
            value_label = _model_metric(current, pollutant)
            assessment = assess_pollutant(pollutant, item["value"] if item else None, item["unit"] if item else "", observations)
            status = assessment["status"] if item else "Unavailable"
            color = assessment["color"]
            st.markdown(
                f'<div style="border:2px solid {color};border-radius:12px;padding:10px 12px;margin:4px 0;">'
                f'<div style="font-weight:700;">{pollutant}</div><div style="font-size:1.15rem;">{value_label}</div>'
                f'<span style="font-size:.72rem;color:{color};font-weight:650;">{status}</span></div>',
                unsafe_allow_html=True,
            )
            if st.button("Extra Details", key=f"air-extra-{pollutant}"):
                st.session_state["air-extra-pollutant"] = pollutant
            if item and assessment["status"] not in ("Within WHO health guideline", "Reading available", "Reference unavailable"):
                elevated_pollutants.append((pollutant, assessment))

    if elevated_pollutants:
        with st.expander("Precautions for elevated pollutants", expanded=True):
            for pollutant, assessment in elevated_pollutants:
                st.warning(f"{pollutant}: {HEALTH_INFORMATION[pollutant]['precautions']}")

    extra_pollutant = st.session_state.get("air-extra-pollutant")
    if extra_pollutant in HEALTH_INFORMATION:
        health = HEALTH_INFORMATION[extra_pollutant]
        with st.expander(f"Extra Details · {extra_pollutant}", expanded=True):
            st.write(health["summary"])
            st.write(f"**Main sources:** {health['sources']}")
            st.write(f"**Health context:** {health['effects']}")
            st.write(f"**More sensitive:** {health['sensitive']}")
            st.write(f"**Practical precautions:** {health['precautions']}")
            st.caption("Health effects are associated with concentration and exposure duration; a measured value does not by itself establish that illness will occur.")
    st.markdown("**Recent hourly CAMS model trend · concentration (µg/m³)**")
    chart_data = observations.loc[~observations["pollutant"].isin(("European AQI", "US AQI", "CO2"))].copy()
    chart_data = chart_data.sort_values("observed_at").groupby("pollutant", group_keys=False).tail(24)
    chart_data["is_unusual"] = chart_data.groupby("pollutant")["value"].transform(
        lambda values: values > values.mean() + (2 * values.std(ddof=0) if len(values) > 1 else 0)
    )
    if alt is not None and not chart_data.empty:
        palette = {"PM2.5": "#d97706", "PM10": "#ca8a04", "NO2": "#2563eb", "SO2": "#16a34a", "CO": "#dc2626", "O3": "#7c3aed"}
        lines = alt.Chart(chart_data).mark_line(point=True).encode(
            x=alt.X("observed_at:T", title="Observation time (UTC)"),
            y=alt.Y("value:Q", title="Concentration (µg/m³)"),
            color=alt.Color("pollutant:N", title="Pollutant", scale=alt.Scale(domain=list(palette), range=list(palette.values()))),
            tooltip=[alt.Tooltip("observed_at:T", title="Observed (UTC)"), alt.Tooltip("pollutant:N", title="Pollutant"), alt.Tooltip("value:Q", title="Value", format=".2f"), alt.Tooltip("is_unusual:N", title="Unusually high vs recent series")],
        ).properties(height=280)
        points = alt.Chart(chart_data.loc[chart_data["is_unusual"]]).mark_point(size=90, filled=True, color="#b91c1c").encode(
            x="observed_at:T", y="value:Q", tooltip=[alt.Tooltip("observed_at:T", title="Observed (UTC)"), alt.Tooltip("pollutant:N", title="Pollutant"), alt.Tooltip("value:Q", title="Value", format=".2f")]
        )
        st.altair_chart(lines + points, width="stretch")
    elif not chart_data.empty:
        st.line_chart(chart_data.pivot_table(index="observed_at", columns="pollutant", values="value", aggfunc="last").tail(24))
    else:
        st.info("No hourly pollutant observations are available for the trend chart.")
    st.caption("Points marked as unusually high are statistical flags relative to this recent model series, not proof of a health-limit exceedance. Missing observations are not interpolated.")
    st.caption(
        f"Modelled estimate from [Open-Meteo]({OPEN_METEO_DOCS_URL}) using CAMS data. "
        f"Attribution: [Copernicus Atmosphere Monitoring Service]({CAMS_ATTRIBUTION_URL}) and Open-Meteo."
    )
    _render_background_pm25_forecast()


def _model_metric(current: dict, label: str) -> str:
    item = current.get(label)
    if not item:
        return "Unavailable"
    return f"{item['value']:g} {item['unit']}"


@st.cache_data(ttl=900, show_spinner=False)
def load_background_inputs(latitude: float, longitude: float) -> tuple[dict, dict]:
    """Load matching CAMS pollutants and weather for the surrogate model."""
    air = fetch_open_meteo(latitude=latitude, longitude=longitude)
    weather = fetch_open_meteo_weather(latitude=latitude, longitude=longitude)
    return air["current"], weather


def _render_background_pm25_forecast() -> None:
    st.markdown("### Kerala background PM2.5 model")
    st.caption(
        "Evaluated next-hour surrogate for CAMS/Open-Meteo atmospheric background at three Kerala grid locations. "
        "It is not a station forecast, incident-plume model, health-limit prediction or facility attribution."
    )
    locations = {
        "Kochi": (9.9312, 76.2673),
        "Eloor I": (10.079692, 76.296766),
        "Eloor II": (10.074350, 76.303942),
    }
    selected = st.selectbox("Background-model location", tuple(locations), key="air-background-location")
    try:
        current, weather = load_background_inputs(*locations[selected])
        values = {
            "pm2_5_ug_m3": current["PM2.5"]["value"], "pm10_ug_m3": current["PM10"]["value"],
            "no2_ug_m3": current["NO2"]["value"], "so2_ug_m3": current["SO2"]["value"],
            "co_ug_m3": current["CO"]["value"], "o3_ug_m3": current["O3"]["value"],
            **weather,
        }
        prediction = predict_next_hour(values, selected.replace(" ", "_"))
    except Exception as error:
        st.info(f"The background model is temporarily unavailable: {error}")
        return
    report = json.loads(EVALUATION_PATH.read_text(encoding="utf-8"))
    metrics = report.get("metrics", {})
    cards = st.columns(3)
    cards[0].metric("Predicted next-hour PM2.5", f"{prediction:.1f} µg/m³")
    cards[1].metric("Held-out MAE", f"{metrics.get('model_mae_ug_m3', float('nan')):.2f} µg/m³")
    cards[2].metric("Compared with", "Previous hour baseline")
    st.caption(
        f"Model inputs are current CAMS/Open-Meteo values plus weather at {selected}; "
        f"evaluation R²={metrics.get('model_r2', float('nan')):.3f}. "
        "The prediction describes atmospheric background only and must not be interpreted as a disaster signal."
    )


def _scenario_external_aqi(hourly: pd.DataFrame, current: dict, label: str, *, mode: str, observed_at) -> dict | None:
    """Return an AQI supplied by the external feed; never derive US/EAQI from CPCB."""
    if mode == "Forecast mode" and isinstance(hourly, pd.DataFrame) and not hourly.empty and observed_at is not None:
        cutoff = pd.to_datetime(observed_at, utc=True, errors="coerce")
        rows = hourly.loc[
            hourly.get("pollutant", pd.Series(dtype=str)).eq(label)
            & (pd.to_datetime(hourly.get("observed_at"), utc=True, errors="coerce") > cutoff)
        ].sort_values("observed_at")
        if not rows.empty:
            return {"value": float(rows.iloc[0]["value"]), "source": "External CAMS/Open-Meteo forecast"}
    item = current.get(label)
    if isinstance(item, dict) and item.get("value") is not None:
        return {"value": float(item["value"]), "source": "External CAMS/Open-Meteo model estimate"}
    return None


def _render_scenario_visual_report(values: dict, baseline: dict, hourly: pd.DataFrame, *, mode: str, observed_at, location: str) -> None:
    """Render the scenario outcome as an environmental intelligence report."""
    aqi = scenario_aqi_summary(values)
    subindices = {item["pollutant"]: item for item in aqi["subindices"]}
    concern = max(aqi["subindices"], key=lambda item: item["sub_index"])["pollutant"] if aqi["subindices"] else None
    if concern is None:
        candidates = [(p, float(item["value"]) / POLLUTANT_GUIDELINES[p]["limit"])
                      for p, item in values.items() if p in POLLUTANT_GUIDELINES and item["unit"] == POLLUTANT_GUIDELINES[p]["unit"]]
        concern = max(candidates, key=lambda item: item[1])[0] if candidates else "No compatible pollutant"
    status = "Predicted feed value" if mode == "Forecast mode" else "Hypothetical simulated scenario"
    overall = f"{aqi['scenario_index']} · {aqi['category']}" if aqi["scenario_index"] is not None else "AQI unavailable — insufficient compatible inputs"
    interpretation = HEALTH_INFORMATION.get(concern, {}).get("summary", "No pollutant-specific interpretation is available.")
    precaution = HEALTH_INFORMATION.get(concern, {}).get("precautions", "Use official local guidance and avoid treating this scenario as an alert.")
    st.markdown(
        f'<div style="border:1px solid rgba(130,190,199,.28);border-radius:18px;padding:22px;margin:12px 0;'
        f'background:linear-gradient(135deg,#0b2333,#0b2333);">'
        f'<div style="color:#5cc8e8;font-size:.78rem;font-weight:750;letter-spacing:.08em;text-transform:uppercase;">{status}</div>'
        f'<div style="font-size:1.7rem;font-weight:800;color:#f1fbfb;margin:.25rem 0;">Air-quality scenario report</div>'
        f'<div style="color:#a9c7cd;"><b>Scenario name:</b> {mode} · <b>Location:</b> {location}</div>'
        f'<div style="display:flex;gap:24px;flex-wrap:wrap;margin-top:14px;">'
        f'<div><div style="color:#9fbec6;font-size:.78rem;">OVERALL ASSESSMENT</div><div style="font-size:1.25rem;font-weight:750;">{overall}</div></div>'
        f'<div><div style="color:#9fbec6;font-size:.78rem;">MAIN POLLUTANT OF CONCERN</div><div style="font-size:1.25rem;font-weight:750;">{concern}</div></div>'
        f'<div><div style="color:#9fbec6;font-size:.78rem;">RESULT STATUS</div><div style="font-size:1.25rem;font-weight:750;color:#5cc8e8;">{status}</div></div>'
        f'</div></div>', unsafe_allow_html=True,
    )

    st.markdown("**Pollutant indicators**")
    pollutant_order = ("PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "CO2")
    cards = st.columns(3)
    for index, pollutant in enumerate(pollutant_order):
        item = values.get(pollutant)
        with cards[index % 3]:
            if not item:
                st.markdown(f"<div style='border:1px solid rgba(130,190,199,.22);border-radius:14px;padding:13px;margin:5px 0;color:#9fbec6;'><b>{pollutant}</b><br>Unavailable</div>", unsafe_allow_html=True)
                continue
            base = baseline.get(pollutant)
            comparison = "No compatible baseline"
            if base and base.get("unit") == item.get("unit"):
                delta = float(item["value"]) - float(base["value"])
                comparison = f"{delta:+.1f} vs baseline"
            meaning = "CO₂ is context only; it is not an AQI pollutant." if pollutant == "CO2" else (subindices.get(pollutant, {}).get("category") or "Concentration available")
            st.markdown(
                f"<div style='border:1px solid rgba(130,190,199,.28);border-radius:14px;padding:13px;margin:5px 0;background:#0b2333;'>"
                f"<div style='font-weight:750;color:#d8fbf5;'>{pollutant}</div>"
                f"<div style='font-size:1.45rem;font-weight:800;'>{float(item['value']):.1f} <span style='font-size:.82rem;font-weight:500;'>{item['unit']}</span></div>"
                f"<div style='font-size:.78rem;color:#5cc8e8;'>{item['source']}</div>"
                f"<div style='font-size:.78rem;color:#a9c7cd;'>{comparison} · {meaning}</div></div>", unsafe_allow_html=True,
            )

    st.markdown("**AQI indicators supplied by the external feed**")
    aqi_cols = st.columns(2)
    for column, label, title in zip(aqi_cols, ("European AQI", "US AQI"), ("EAQI", "US AQI")):
        supplied = _scenario_external_aqi(hourly, baseline, label, mode=mode, observed_at=observed_at)
        with column:
            if supplied and mode == "Forecast mode":
                category = aqi_category("EAQI" if label == "European AQI" else "US AQI", supplied["value"])
                colour = category["color"] if category else "#5cc8e8"
                category_label = category["label"] if category else "Category unavailable"
                st.markdown(f"<div style='border:3px solid {colour};border-radius:16px;padding:17px;background:linear-gradient(135deg,{colour}16,transparent);'><div style='color:#9fbec6;font-size:.78rem;font-weight:700;'>{title} · external forecast</div><div style='font-size:2.4rem;font-weight:850;'>{supplied['value']:.0f}</div><div style='font-weight:750;color:{colour};'>{category_label}</div></div>", unsafe_allow_html=True)
            else:
                st.info(f"{title} unavailable for this scenario. No unsupported AQI is calculated.")

    comparison_rows = []
    for pollutant, item in values.items():
        base = baseline.get(pollutant)
        if base and base.get("unit") == item.get("unit"):
            comparison_rows.append({"Pollutant": pollutant, "Baseline": float(base["value"]), "Scenario": float(item["value"]), "Unit": item["unit"]})
    if comparison_rows:
        st.markdown("**Current versus scenario**")
        comparison = pd.DataFrame(comparison_rows)
        if alt is not None:
            chart = alt.Chart(comparison.melt(id_vars=["Pollutant", "Unit"], value_vars=["Baseline", "Scenario"], var_name="Series", value_name="Value")).mark_bar().encode(
                x=alt.X("Pollutant:N", title=None), y=alt.Y("Value:Q", title="Concentration"), color=alt.Color("Series:N", scale=alt.Scale(range=["#8fb3bb", "#42e0c1"])), tooltip=["Pollutant", "Series", "Value", "Unit"]
            ).properties(height=260)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.bar_chart(comparison.set_index("Pollutant")[["Baseline", "Scenario"]])
    if mode == "Forecast mode" and isinstance(hourly, pd.DataFrame) and not hourly.empty and observed_at is not None:
        future = hourly.loc[pd.to_datetime(hourly.get("observed_at"), utc=True, errors="coerce") > pd.to_datetime(observed_at, utc=True, errors="coerce")]
        future = future.loc[future["pollutant"].isin(pollutant_order[:-1])].head(48)
        if not future.empty:
            st.markdown("**Forecast trend from returned time-series values**")
            if alt is not None:
                st.altair_chart(alt.Chart(future).mark_line(point=True).encode(x="observed_at:T", y="value:Q", color="pollutant:N", tooltip=["observed_at:T", "pollutant:N", "value:Q"]).properties(height=260), use_container_width=True)
            else:
                st.line_chart(future.pivot_table(index="observed_at", columns="pollutant", values="value", aggfunc="last"))
    st.markdown("**What changed and what does it mean?**")
    st.write(f"The scenario uses the selected external or user-simulated values. The main concern is {concern}. {interpretation}")
    st.write(f"Practical precaution: {precaution}")
    st.caption("Reliability: this is a transparent scenario display. External values are model estimates; simulated values are assumptions. It is not an official warning, diagnosis, causal attribution, or validated disaster forecast.")
    with st.expander("Detailed pollutant data and AQI calculation"):
        display_dataframe(pd.DataFrame([{"Pollutant": p, "Value": item["value"], "Unit": item["unit"], "Provenance": item["source"]} for p, item in values.items()]), hide_index=True, use_container_width=True, alt="Detailed scenario pollutant values")
        if aqi["subindices"]:
            display_dataframe(pd.DataFrame(aqi["subindices"]), hide_index=True, use_container_width=True, alt="Scenario CPCB pollutant subindices")
        st.caption(aqi["method"])
        if aqi["exclusions"]:
            st.caption("Excluded from CPCB scenario index: " + "; ".join(aqi["exclusions"]))


def _render_air_intelligence_tools() -> None:
    st.markdown('<div id="scenario-simulator"></div>', unsafe_allow_html=True)
    st.header("Predictive Air Pollution — Scenario Simulator")
    st.caption(
        "Forecast mode uses returned future CAMS/Open-Meteo values when available. What-if mode lets you override selected values. "
        "Neither mode is a validated local pollution forecast or an official AQI."
    )
    mode = st.radio(
        "Scenario mode",
        ["Forecast mode", "What-if scenario mode"],
        horizontal=True,
        key="air-scenario-mode",
    )
    location = st.selectbox(
        "Scenario location",
        ["Kochi model grid", "Eloor", "Edayar", "Other / not specified"],
        key="air-scenario-location",
    )
    live = {}
    try:
        live = load_live_air_quality()
    except Exception as error:
        st.info(f"The external CAMS/Open-Meteo feed is unavailable: {error}")
    current = live.get("current", {}) if isinstance(live, dict) else {}
    hourly = live.get("hourly", pd.DataFrame()) if isinstance(live, dict) else pd.DataFrame()
    observed_at = live.get("observed_at") if isinstance(live, dict) else None
    if mode == "Forecast mode":
        st.info(
            "Forecast mode uses only future timestamps returned by the external model. "
            "The current feed supplies air-quality variables, not a validated local dispersion forecast."
        )

    st.markdown("**Optional pollutant and environment overrides**")
    st.caption("Leave a field blank to retain the selected external value, if one exists. CO is entered in mg/m³; CO₂ is ppm.")
    pollutant_specs = (
        ("PM2.5", "PM2.5 (µg/m³)", 0.0, 1000.0, 0.1),
        ("PM10", "PM10 (µg/m³)", 0.0, 2000.0, 0.1),
        ("NO2", "NO₂ (µg/m³)", 0.0, 1000.0, 0.1),
        ("SO2", "SO₂ (µg/m³)", 0.0, 1000.0, 0.1),
        ("CO", "CO (mg/m³)", 0.0, 100.0, 0.01),
        ("O3", "O₃ (µg/m³)", 0.0, 1000.0, 0.1),
        ("CO2", "CO₂ (ppm)", 0.0, 10000.0, 1.0),
    )
    overrides = {}
    pollutant_columns = st.columns(2)
    for index, (key, label, minimum, maximum, step) in enumerate(pollutant_specs):
        with pollutant_columns[index % 2]:
            overrides[key] = st.number_input(
                label,
                min_value=minimum,
                max_value=maximum,
                value=None,
                step=step,
                key=f"air-scenario-{key}",
            )
    context_columns = st.columns(2)
    with context_columns[0]:
        temperature = st.number_input("Temperature (°C, optional)", min_value=-50.0, max_value=60.0, value=None, step=0.1, key="air-scenario-temperature")
        humidity = st.number_input("Relative humidity (% , optional)", min_value=0.0, max_value=100.0, value=None, step=1.0, key="air-scenario-humidity")
        wind_speed = st.number_input("Wind speed (km/h, optional)", min_value=0.0, max_value=250.0, value=None, step=0.1, key="air-scenario-wind-speed")
    with context_columns[1]:
        wind_direction = st.selectbox("Wind direction (optional)", ["Not provided", "N", "NE", "E", "SE", "S", "SW", "W", "NW"], key="air-scenario-wind-direction")
        traffic = st.selectbox("Traffic intensity (optional)", ["Not provided", "Low", "Moderate", "High"], key="air-scenario-traffic")
        industry = st.selectbox("Industrial activity level (optional)", ["Not provided", "Low", "Moderate", "High"], key="air-scenario-industry")
    values = scenario_pollutant_values(
        current,
        hourly,
        mode="forecast" if mode == "Forecast mode" else "what-if",
        overrides=overrides,
        observed_at=observed_at,
    )
    if not values:
        st.warning("No pollutant values are available for this scenario. Enter at least one supported pollutant or restore the external feed.")
    else:
        _render_scenario_visual_report(values, current, hourly, mode=mode, observed_at=observed_at, location=location)
        st.caption(
            f"Context supplied: temperature={temperature if temperature is not None else 'not provided'}, humidity={humidity if humidity is not None else 'not provided'}, "
            f"wind={wind_speed if wind_speed is not None else 'not provided'} km/h from {wind_direction}, traffic={traffic}, industrial activity={industry}. "
            "These context fields are recorded for scenario description only; no unsupported dispersion prediction is calculated."
        )
    return values

def _render_disaster_dispersion_engine(values: dict) -> None:
    st.markdown('<div id="disaster-air-intelligence"></div>', unsafe_allow_html=True)
    st.markdown(
        '<section class="disaster-hero"><div class="disaster-kicker">AI RESILIENCE · INCIDENT MODELLING</div>'
        '<div class="disaster-title">Disaster Air Pollution Intelligence</div>'
        '<p class="disaster-subtitle">Understand and model how hazardous emissions may spread during environmental and industrial disasters.</p></section>',
        unsafe_allow_html=True,
    )
    st.subheader("Air-quality precaution signal")
    hazard = st.selectbox("Disaster context", list(DISASTER_AIR_INTELLIGENCE), key="air-disaster-context")
    intelligence = disaster_air_intelligence(values, hazard)
    st.caption("This preparedness view does not estimate disaster probability, identify a responsible facility, or replace IMD/KSDMA alerts.")
    st.write(intelligence["context"])
    if intelligence["signals"]:
        for signal in intelligence["signals"]:
            st.warning(
                f"{signal['pollutant']}: {signal['value']:g} {signal['unit']} · {signal['source']} · "
                f"above the configured {signal['reference']:g} {POLLUTANT_GUIDELINES[signal['pollutant']]['unit']} health reference."
            )
    else:
        st.info("No compatible elevated pollutant indicator is available for this context. Missing values are not treated as safe or zero.")
    st.markdown(f"**Relevant precaution:** {intelligence['action']}")
    st.caption("Pollutant indicators and disaster conditions are not a validated causal linkage. Source attribution remains evidence-gated below.")
    st.markdown('<div id="disaster-dispersion"></div>', unsafe_allow_html=True)
    incident_options = {
        "🏭 Industrial accident": "Industrial chemical accident",
        "☣️ Toxic gas release": "Toxic gas release",
        "🌋 Volcanic eruption": "Volcanic eruption",
        "🔥 Wildfire": "Wildfire",
        "🌀 Cyclone-related industrial accident": "Cyclone-related industrial accident",
    }
    prior_incident = st.session_state.get("dispersion-incident-selection")
    selection = st.radio(
        "Step 1 · Select incident type",
        list(incident_options),
        horizontal=True,
        key="dispersion-incident-card",
        label_visibility="collapsed",
    )
    incident_type = incident_options[selection]
    if prior_incident != incident_type:
        st.session_state["dispersion-incident-selection"] = incident_type
        st.session_state.pop("disaster_dispersion_result", None)
    st.caption({
        "Industrial chemical accident": "A point-source release from an industrial facility or process.",
        "Toxic gas release": "A hazardous gas release where the source term is known or estimated by authorities.",
        "Volcanic eruption": "Ash and SO₂ require a specialized volcanic plume product; unavailable here.",
        "Wildfire": "Smoke prediction requires a validated fire-emissions or smoke-forecast feed.",
        "Cyclone-related industrial accident": "A steady snapshot only; changing cyclone winds are not modelled.",
    }[incident_type])

    supported = incident_type not in {"Volcanic eruption", "Wildfire"}
    st.markdown('<div class="disaster-step">Step 2 · Locate the incident</div>', unsafe_allow_html=True)
    with st.container(border=True):
        location_name = st.selectbox("Incident location", [*LOCATION_PRESETS, "Custom coordinates"], key="dispersion-location")
        preset = LOCATION_PRESETS.get(location_name)
        location_cols = st.columns(2)
        with location_cols[0]:
            source_lat = st.number_input("Latitude", value=(preset[0] if preset else None), format="%.6f", key="dispersion-latitude", help="WGS84 incident latitude.")
        with location_cols[1]:
            source_lon = st.number_input("Longitude", value=(preset[1] if preset else None), format="%.6f", key="dispersion-longitude", help="WGS84 incident longitude.")
        if preset:
            st.caption(f"Reference: {preset[2]}. Choosing a location does not imply that an incident occurred there.")

    st.markdown('<div class="disaster-step">Step 3 · Describe the incident</div>', unsafe_allow_html=True)
    with st.form("disaster-dispersion-form", clear_on_submit=False):
        if supported:
            incident_cols = st.columns(3)
            with incident_cols[0]:
                pollutant = st.selectbox("Pollutant / chemical", SUPPORTED_POLLUTANTS, key="dispersion-pollutant", help="Use the released pollutant only; unknown chemistry should remain unknown.")
            with incident_cols[1]:
                release_rate = st.number_input("Release rate · g/s", min_value=0.0, value=None, step=0.1, key="dispersion-release-rate", help="Continuous mass release rate. Leave blank if not verified.")
            with incident_cols[2]:
                duration = st.number_input("Duration · minutes", min_value=0.01, value=None, step=1.0, key="dispersion-duration", help="Duration of the continuous release assumption.")
            source_cols = st.columns(2)
            with source_cols[0]:
                release_height = st.number_input("Release height · m", min_value=0.0, value=None, step=1.0, key="dispersion-release-height", help="Height of the source above ground.")
            with source_cols[1]:
                st.caption("Source values are user-entered assumptions unless an official incident record is separately attached.")
        else:
            pollutant = None
            release_rate = duration = release_height = None
            st.info("This incident type is visible for planning, but no validated specialized plume model is connected. No industrial plume calculation will run.")

        st.markdown('<div class="disaster-step">Step 4 · Add meteorology</div>', unsafe_allow_html=True)
        if supported:
            weather_cols = st.columns(3)
            with weather_cols[0]:
                wind_speed = st.number_input("Wind speed · m/s", min_value=0.01, value=None, step=0.1, key="dispersion-wind-speed", help="Sustained wind speed at release height, if known.")
            with weather_cols[1]:
                wind_from = st.number_input("Wind from · degrees", min_value=0.0, max_value=360.0, value=None, step=1.0, key="dispersion-wind-direction", help="Meteorological direction: where the wind comes from.")
            with weather_cols[2]:
                stability = st.selectbox("Stability class", ["Not provided", *STABILITY_CLASSES], key="dispersion-stability", help="Pasquill–Gifford atmospheric stability class.")
        else:
            wind_speed = wind_from = None
            stability = "Not provided"

        inputs = {
            "incident_type": incident_type, "source_latitude": source_lat, "source_longitude": source_lon,
            "pollutant": pollutant, "release_rate_g_s": release_rate, "duration_min": duration,
            "release_height_m": release_height, "wind_speed_m_s": wind_speed, "wind_from_deg": wind_from,
            "stability_class": None if stability == "Not provided" else stability,
        }
        valid_count = sum(value not in (None, "", "Not provided") for value in (source_lat, source_lon, pollutant, release_rate, duration, release_height, wind_speed, wind_from, stability))
        st.progress(min(1.0, valid_count / (9 if supported else 2)), text=f"Input readiness · {valid_count} fields supplied")
        st.caption("Review the location, source term and weather above. Missing critical inputs stay unavailable; they are never inferred.")
        submitted = st.form_submit_button("Run dispersion assessment", type="primary", use_container_width=True)
    if st.button("Reset assessment", key="dispersion-reset"):
        st.session_state.pop("disaster_dispersion_result", None)
        st.rerun()
    if submitted:
        with st.spinner("Calculating traceable plume receptors…"):
            st.session_state["disaster_dispersion_result"] = run_gaussian_plume(inputs)
    result = st.session_state.get("disaster_dispersion_result")
    if not result:
        st.markdown('<div class="disaster-empty"><b>Ready when you are.</b><br>Complete the relevant incident and meteorology fields, then run the assessment to see modelled concentrations, transport timing and the plume map.</div>', unsafe_allow_html=True)
        return
    if result["status"] != "modelled":
        if result["status"] == "specialized_model_unavailable":
            st.warning("No result generated: a verified volcanic-ash/SO₂ or wildfire-smoke model/feed is required for this incident type.")
        else:
            missing = ", ".join(result["validation"]["missing"])
            st.warning(f"Assessment needs more information: {missing}.")
        st.caption("Measured observations, official incident information and user assumptions remain separate from this unavailable model result.")
        return

    rows = pd.DataFrame(result["rows"])
    nearest = rows.iloc[0]
    st.markdown('<div class="disaster-step">Assessment result · modelled only</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="disaster-result"><div class="disaster-result-label">Main pollutant of concern · {result["pollutant"]}</div>'
        f'<div class="disaster-result-value">{nearest["concentration_mg_m3"]:.4g} <span style="font-size:1.1rem;font-weight:700;">mg/m³</span></div>'
        f'<div class="disaster-result-copy">Nearest displayed downwind receptor at {nearest["distance_m"]:.0f} m · centerline arrival estimate {nearest["arrival_min"]:.1f} minutes · <span class="disaster-pill">Gaussian plume model</span></div></div>',
        unsafe_allow_html=True,
    )
    result_cards = st.columns(3)
    result_cards[0].metric("Peak in displayed transect", f"{rows['concentration_mg_m3'].max():.4g} mg/m³")
    result_cards[1].metric("Plume direction", f"{result['wind_to_deg']:.0f}°")
    result_cards[2].metric("Release window", f"{result['release_duration_min']:.0f} min")
    st.caption("The concentration is a modelled incident increment, not a measured observation or a validated AQI value.")

    st.markdown('<div class="disaster-step">Atmospheric dispersion map</div>', unsafe_allow_html=True)
    map_rows = rows[["latitude", "longitude"]].copy()
    map_rows["size"] = 1
    map_rows["role"] = "Modelled downwind receptor"
    source_row = pd.DataFrame([{"latitude": source_lat, "longitude": source_lon, "size": 12, "role": "Incident location"}])
    st.map(pd.concat([source_row, map_rows], ignore_index=True), latitude="latitude", longitude="longitude", size="size", height=500, zoom=10)
    st.caption("Legend: large marker = incident coordinate · small markers = modelled centerline receptors. This is not an affected-settlement boundary or a measured station map.")

    st.markdown('<div class="disaster-step">Concentration profile</div>', unsafe_allow_html=True)
    if alt is not None:
        chart = alt.Chart(rows).mark_line(point=True, color="#42e0c1").encode(
            x=alt.X("distance_m:Q", title="Downwind distance (m)"),
            y=alt.Y("concentration_mg_m3:Q", title="Modelled concentration (mg/m³)"),
            tooltip=[alt.Tooltip("distance_m:Q", title="Distance (m)"), alt.Tooltip("concentration_mg_m3:Q", title="Concentration (mg/m³)", format=".4g"), alt.Tooltip("arrival_min:Q", title="Arrival (min)")],
        ).properties(height=300)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.line_chart(rows.set_index("distance_m")["concentration_mg_m3"])

    timeline = pd.DataFrame(result["timeline"])
    st.markdown("**Projected change at the nearest receptor**")
    if alt is not None:
        timeline_chart = alt.Chart(timeline).mark_line(point=True, color="#5cc8e8").encode(
            x=alt.X("time_min:Q", title="Minutes after incident start"),
            y=alt.Y("concentration_mg_m3:Q", title="Modelled concentration (mg/m³)"),
            tooltip=[alt.Tooltip("time_min:Q", title="Time (min)"), alt.Tooltip("concentration_mg_m3:Q", title="Concentration (mg/m³)", format=".4g")],
        ).properties(height=260)
        st.altair_chart(timeline_chart, use_container_width=True)
    else:
        st.line_chart(timeline.set_index("time_min")["concentration_mg_m3"])

    live_baseline = load_live_air_quality()
    baseline = (live_baseline.get("current", {}) if isinstance(live_baseline, dict) else {}).get(result["pollutant"])
    st.markdown('<div class="disaster-step">Baseline and public impact</div>', unsafe_allow_html=True)
    baseline_cols = st.columns(2)
    with baseline_cols[0]:
        if baseline:
            st.markdown(f'<div class="disaster-card"><div class="disaster-card-title">Ambient baseline</div><div class="disaster-result-value" style="font-size:1.75rem;">{baseline["value"]:g} {baseline["unit"]}</div><div class="disaster-card-copy">External CAMS/Open-Meteo model estimate at the Kochi grid; not a station observation.</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="disaster-card"><div class="disaster-card-title">Ambient baseline</div><div class="disaster-card-copy">No compatible baseline is available for this pollutant. The incident result is shown separately.</div></div>', unsafe_allow_html=True)
    with baseline_cols[1]:
        st.markdown('<div class="disaster-card"><div class="disaster-card-title">Potentially affected locations</div><div class="disaster-card-copy">The model identifies a downwind centerline only. Settlement and station impact cannot be determined from the available geographic data.</div></div>', unsafe_allow_html=True)
    st.caption("No unsupported AQI is calculated. Toxic gases outside CPCB pollutants remain concentration-only results.")
    with st.expander("Monitoring references, assumptions and limitations"):
        st.write("Project-known reference locations are geographic references only; this model assigns no concentration to them.")
        reference_cols = st.columns(3)
        for column, (name, coords) in zip(reference_cols, LOCATION_PRESETS.items()):
            with column:
                st.markdown(f'<div class="disaster-card"><div class="disaster-card-title">{name}</div><div class="disaster-card-copy">{coords[0]:.6f}, {coords[1]:.6f}<br>{coords[2]}</div></div>', unsafe_allow_html=True)
        st.write("Model assumptions: steady continuous point source, flat terrain, centerline receptor, Pasquill–Gifford rural coefficients, no deposition, chemistry, building downwash, terrain, plume rise or exposure-dose calculation.")
        st.warning("Uncertainty is material and not statistically calibrated. Do not use this screening result for evacuation or health decisions without official incident and dispersion guidance.")
        st.caption(f"Model trace: {result['model']} · source: user-supplied incident and meteorology inputs · wind travels toward {result['wind_to_deg']:.0f}°.")


render_live_air_quality()
scenario_values = _render_air_intelligence_tools()
_render_disaster_dispersion_engine(scenario_values or {})

try:
    register = load_source_register()
except (OSError, json.JSONDecodeError) as error:
    st.error(f"Air-pollution acquisition status could not be loaded: {error}")
    st.stop()

register_review_value = register.get("reviewed_on")
try:
    register_review_date = date.fromisoformat(str(register_review_value))
    register_review_age_days = (date.today() - register_review_date).days
    if register_review_age_days < 0:
        st.warning(
            f"The source register review date ({register_review_date:%d %b %Y}) is in the future. "
            "Verify the register metadata before relying on its review status."
        )
    else:
        st.caption(
            f"Source register reviewed: {register_review_date:%d %b %Y} "
            f"({register_review_age_days} days ago)."
        )
except (TypeError, ValueError):
    st.warning(
        "The source register has a missing or invalid top-level reviewed_on date. "
        "Verify the register metadata; individual source review dates are shown below."
    )
st.markdown(
    """
    <nav class="air-nav">
        <a href="#live-feed">Live feed</a>
        <a href="#co2-intelligence">CO2 Intelligence</a>
        <a href="#pollutant-levels">Pollutants</a>
        <a href="#industrial-pollution-sources">Industrial sources</a>
        <a href="#historical-trends-and-kspcb-data">Historical trends</a>
        <a href="#data-sources-and-limitations">Sources</a>
    </nav>
    """,
    unsafe_allow_html=True,
)

# Read-only evidence readiness: integrity is not a certification of measurement quality.
air_readiness = audit_air_quality_datasets(ROOT)
st.subheader("Air-quality dataset readiness")
st.caption(
    f"Read-only audit: {air_readiness['dataset_count']} datasets · "
    f"{air_readiness['status_counts']['provisional']} provisional · "
    f"{air_readiness['status_counts']['unavailable']} unavailable · "
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
display_dataframe(
    pd.DataFrame(readiness_rows),
    hide_index=True,
    width="stretch",
    alt="Air-quality dataset readiness and permitted-use summary",
)
st.info(air_readiness["conclusion"])
with st.expander("Dataset audit details and blockers"):
    for item in air_readiness["datasets"]:
        st.markdown(f"**{item['name']} — {item['status']}**")
        st.caption(
            f"Integrity: {item['integrity_check']} · Schema: {item['schema_check']} · "
            f"Forecast eligible: {item['forecast_training_eligible']}"
        )
        for limitation in item["limitations"]:
            st.write(f"- {limitation}")
        for error in item["errors"]:
            st.warning(error)
    for error in air_readiness["catalog_errors"]:
        st.warning(error)


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


def _render_co2_intelligence(live: dict) -> None:
    """Render CO₂ monitoring, trends and action context without mixing it into AQI."""
    st.markdown('<div id="co2-intelligence"></div>', unsafe_allow_html=True)
    section_intro("Monitoring", "CO2 intelligence")
    co2_item = live.get("current", {}).get("CO2") if isinstance(live, dict) else None
    hourly = live.get("hourly", pd.DataFrame()) if isinstance(live, dict) else pd.DataFrame()
    with st.container(border=True):
        if not co2_item:
            st.info("Verified local ambient CO₂: Unavailable. No validated Kochi monitoring-station concentration is connected.")
        else:
            observed = live.get("observed_at")
            observed_label = observed.strftime("%d %b %Y, %H:%M UTC") if observed is not None else "Timestamp unavailable"
            context = co2_context(co2_item["value"])
            st.markdown(
                f'<div style="border:3px solid {context["color"]};border-radius:18px;padding:16px 20px;'
                f'background:linear-gradient(100deg,{context["color"]}18,transparent);">'
                f'<div style="font-size:.86rem;color:#a9c7cd;">Modelled outdoor CO₂ estimate · {context["status"]}</div>'
                f'<div style="font-size:3rem;font-weight:800;line-height:1.1;">{co2_item["value"]:g} <span style="font-size:1.1rem;font-weight:600;">{co2_item["unit"]}</span></div>'
                f'<div style="font-weight:700;color:{context["color"]};">Kochi model grid · model timestamp {observed_label}</div>'
                f'<div style="font-size:.82rem;color:#a9c7cd;">Source: CAMS via Open-Meteo · near-real-time modelled · cached up to 15 minutes</div></div>',
                unsafe_allow_html=True,
            )
            st.warning("Verified local ambient CO₂: Unavailable. The value above is a model estimate, not a validated station observation; it must not be treated as a measured Kochi concentration or an AQI input.")
            st.write("Outdoor ambient CO₂ is not a factory emission total and is not an AQI pollutant. A model estimate at this level is not an immediate-danger breathing warning; indoor CO₂ can instead help indicate ventilation conditions, but indoor thresholds do not apply here.")

    monitor_tab, trend_tab, action_tab, calculator_tab = st.tabs(["Monitor", "CO2 Trends", "Sources, climate & action", "Carbon footprint calculator"])
    with monitor_tab:
        if co2_item:
            observed = live.get("observed_at")
            st.write(f"**Location:** Kochi model grid (9.9312°N, 76.2673°E)")
            st.write(f"**Timestamp:** {observed.strftime('%d %b %Y, %H:%M UTC') if observed is not None else 'Unavailable'}")
            st.write("**Data type:** Modelled estimate only; verified local ambient CO₂ observation unavailable. The app may serve a cached response for up to 15 minutes.")
            st.write("CO₂ is a greenhouse gas that accumulates globally. A local model value varies with atmospheric transport and is not a direct measurement of local emissions.")
        else:
            st.info("No current CO₂ observation is available to describe.")
    with trend_tab:
        period = st.selectbox("CO₂ trend resolution", ["hourly", "daily", "weekly", "monthly"], key="co2-trend-period")
        # Open-Meteo returns past observations and forecast values in the same
        # hourly payload. Keep the CO₂ trend historical/observed-only; forecast
        # values must not be presented as measured concentrations.
        trend_observations = hourly.copy()
        observed_cutoff = live.get("observed_at")
        if observed_cutoff is not None and not trend_observations.empty:
            trend_observations["observed_at"] = pd.to_datetime(
                trend_observations["observed_at"], utc=True, errors="coerce"
            )
            trend_observations = trend_observations.loc[
                trend_observations["observed_at"] <= pd.Timestamp(observed_cutoff)
            ]
        trend = aggregate_co2_trend(trend_observations, period)
        if trend.empty:
            st.info("No returned CO₂ observations are available for this trend.")
        else:
            summary = st.columns(3)
            summary[0].metric("Maximum", f'{trend["maximum"].max():.1f} ppm')
            summary[1].metric("Minimum", f'{trend["minimum"].min():.1f} ppm')
            summary[2].metric("Average", f'{trend["value"].mean():.1f} ppm')
            if alt is not None:
                co2_chart = alt.Chart(trend).mark_line(point=True, color="#42e0c1").encode(
                    x=alt.X("observed_at:T", title="Observation period (UTC)"),
                    y=alt.Y("value:Q", title="CO₂ concentration (ppm)"),
                    tooltip=[alt.Tooltip("observed_at:T", title="Period (UTC)"), alt.Tooltip("value:Q", title="Average ppm", format=".1f"), alt.Tooltip("minimum:Q", title="Minimum", format=".1f"), alt.Tooltip("maximum:Q", title="Maximum", format=".1f"), alt.Tooltip("observations:Q", title="Returned observations")],
                ).properties(height=260)
                st.altair_chart(co2_chart, width="stretch")
            else:
                st.line_chart(trend.set_index("observed_at")[["value"]])
            st.caption("Only returned timestamps up to the latest current timestamp are included; forecast values, empty periods and missing observations are not shown as measured data.")
    with action_tab:
        st.markdown("**Where Does CO2 Come From?**")
        source_types = {
            "Industrial fuel combustion": "Boilers, furnaces and process heat can emit CO₂ when coal, oil, gas, biomass or other carbon-containing fuels are combusted.",
            "Power generation": "Electricity generation can produce CO₂ when fossil fuels are used; the local contribution depends on the power system and transport of air.",
            "Road transport": "Petrol and diesel engines release CO₂ through fuel combustion; traffic is a general possible source, not attribution of this model value.",
            "Commercial and residential energy": "Buildings can contribute through cooking, heating, backup generators and purchased electricity.",
        }
        source_columns = st.columns(2)
        for index, (title, description) in enumerate(source_types.items()):
            with source_columns[index % 2]:
                st.markdown(f'<div style="border:1px solid rgba(130,190,199,.32);border-radius:11px;padding:10px;margin:5px 0;"><b>{title}</b><br><span style="font-size:.83rem;color:#a9c7cd;">{description}</span></div>', unsafe_allow_html=True)

        st.markdown("**Documented Edayar fuel-use evidence**")
        candidates = read_csv(INDUSTRIAL / "edayar_candidate_facilities.csv")
        fuel_records = candidates.loc[candidates["documented_fuel_use"].fillna("").astype(str).str.strip().ne("")].head(6) if not candidates.empty and "documented_fuel_use" in candidates.columns else pd.DataFrame()
        if fuel_records.empty:
            st.info("No facility-specific fuel-use record is available in the reviewed Edayar inventory.")
        else:
            for _, record in fuel_records.iterrows():
                facility = record.get("official_name") or record.get("facility_name_as_published")
                with st.expander(f"{facility} · Documented potential contributor"):
                    st.write(f'**Location:** {record.get("address_as_published") or record.get("industrial_area")}')
                    st.write(f'**Industry:** {record.get("industry_type_as_individually_documented") or "Not specified"}')
                    st.write(f'**Documented fuel-use information:** {record.get("documented_fuel_use")}')
                    st.write(f'**Evidence date:** {record.get("retrieved_on")}')
                    st.markdown(f'[Open reviewed source record]({record.get("source_url")})')
                    st.caption("This is evidence of a historical or documented fuel-use record, not a measured ambient CO₂ contribution or proof of responsibility for the current reading.")

        with st.expander("Climate impact and local-versus-global context"):
            st.write("CO₂ absorbs outgoing infrared radiation and is a long-lived greenhouse gas. Human emissions contribute to warming and long-term changes in climate, oceans, ice and ecosystems.")
            st.write("Local air pollution describes concentrations people may encounter near a place and time. Climate change is driven by the accumulated global balance of greenhouse-gas emissions and removals; a local ambient ppm reading cannot be converted into a local emissions total.")
            st.markdown("For comparison with a reliable global background series, use [NOAA Global Monitoring Laboratory global monthly CO₂ means](https://www.gml.noaa.gov/ccgg/trends/global.html). NOAA's global product is a marine-surface network average and is not the same measurement as this Kochi model-grid estimate; no global value is substituted into the local chart.")

        with st.expander("Carbon mitigation action tracker"):
            st.caption("These are practical actions, not quantified claims of emissions reduction.")
            for group, actions in {
                "Residents": ["Reduce unnecessary fuel use and prefer efficient or shared transport.", "Use energy-efficient appliances and avoid unnecessary generator use."],
                "Industries": ["Improve energy efficiency and assess cleaner fuels or electrification where technically appropriate.", "Maintain verified stack/fuel monitoring and publish time-stamped emissions records."],
                "Local authorities": ["Support efficient public transport and electrification where appropriate.", "Request verified facility-level emissions monitoring and preserve accessible records."],
            }.items():
                st.markdown(f"**{group}**")
                for index, action in enumerate(actions):
                    st.checkbox(action, key=f"co2-action-{group}-{index}")

        with st.expander("CO₂ versus carbon emissions and carbon footprint"):
            st.write("Ambient CO₂ concentration is measured in ppm. Carbon emissions are a mass quantity such as tonnes of CO₂. A carbon footprint is the total emissions associated with an activity, product, household or organisation. An ambient ppm reading cannot be used to calculate a carbon footprint.")


    with calculator_tab:
        st.markdown(
            """
            <div class="disaster-hero" style="margin-top:.25rem;">
              <div class="disaster-kicker">Kochi · household energy estimate</div>
              <div class="disaster-title">Your Carbon Footprint</div>
              <p class="disaster-subtitle">Turn a typical month's electricity and fuel use into a transparent CO₂ estimate. Adjust the inputs and review the result instantly.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("HOUSEHOLD CALCULATOR  /  MONTHLY ACTIVITY  /  INDICATIVE CO₂")

        with st.container(border=True):
            st.markdown("#### 01 · Enter monthly household activity")
            st.caption("Use your latest electricity bill and a typical month's fuel use. Enter zero for any source you do not use.")
            input_left, input_right = st.columns(2, gap="large")
            with input_left:
                st.markdown("**⚡ Electricity**")
                electricity_kwh = st.number_input(
                    "Grid electricity (kWh/month)",
                    min_value=0.0, max_value=100000.0, value=150.0, step=10.0,
                    help="Use the active energy consumption in kWh from your KSEB bill.",
                    key="co2-calc-electricity",
                )
                st.markdown("**🚗 Petrol**")
                petrol_litres = st.number_input(
                    "Petrol (litres/month)",
                    min_value=0.0, max_value=10000.0, value=20.0, step=1.0,
                    help="Estimate the petrol used by household vehicles in one month.",
                    key="co2-calc-petrol",
                )
            with input_right:
                st.markdown("**🚙 Diesel**")
                diesel_litres = st.number_input(
                    "Diesel (litres/month)",
                    min_value=0.0, max_value=10000.0, value=0.0, step=1.0,
                    help="Estimate the diesel used by household vehicles or generators.",
                    key="co2-calc-diesel",
                )
                st.markdown("**🔥 LPG cooking gas**")
                lpg_cylinders = st.number_input(
                    "14.2 kg LPG cylinders/month",
                    min_value=0.0, max_value=100.0, value=1.0, step=0.5,
                    help="Enter the number of standard 14.2 kg domestic cylinders used per month.",
                    key="co2-calc-lpg",
                )
            household_size = st.number_input(
                "People in household",
                min_value=1, max_value=30, value=4, step=1,
                help="Used only to calculate an equal per-person allocation.",
                key="co2-calc-household-size",
            )

        # Default factors: CEA FY 2025-26 grid average; fuel factors are
        # rounded indicative combustion factors. They are not lifecycle factors.
        emission_factors = {
            "Grid electricity": 0.675,
            "Petrol": 2.31,
            "Diesel": 2.68,
            "LPG": 2.98,
        }
        monthly_emissions = {
            "Electricity": electricity_kwh * emission_factors["Grid electricity"],
            "Petrol": petrol_litres * emission_factors["Petrol"],
            "Diesel": diesel_litres * emission_factors["Diesel"],
            "LPG": lpg_cylinders * 14.2 * emission_factors["LPG"],
        }
        total_monthly = sum(monthly_emissions.values())
        total_annual = total_monthly * 12
        per_person_monthly = total_monthly / household_size
        largest_source = max(monthly_emissions, key=monthly_emissions.get)
        largest_amount = monthly_emissions[largest_source]
        largest_share = largest_amount / total_monthly * 100 if total_monthly > 0 else 0.0

        st.markdown("#### 02 · Your estimated emissions")
        result_columns = st.columns([1.25, 1, 1], gap="medium")
        with result_columns[0]:
            st.markdown(
                f'<div class="disaster-result"><div class="disaster-result-label">Monthly household CO₂</div>'
                f'<div class="disaster-result-value">{total_monthly:,.1f}</div>'
                f'<div class="disaster-result-copy">kg CO₂ / month · indicative estimate</div></div>',
                unsafe_allow_html=True,
            )
        result_columns[1].metric("Annualised estimate", f"{total_annual / 1000:,.2f} t CO₂")
        result_columns[2].metric("Per person / month", f"{per_person_monthly:,.1f} kg CO₂")
        st.caption("Annualised estimate = monthly activity × 12. Per-person result divides the household total equally; it is not an individual measurement.")

        with st.container(border=True):
            st.markdown("#### 03 · Emissions breakdown")
            breakdown_left, breakdown_right = st.columns([1.5, 1], gap="large")
            breakdown = pd.DataFrame(
                {
                    "Source": list(monthly_emissions.keys()),
                    "Estimated CO₂ (kg/month)": list(monthly_emissions.values()),
                }
            )
            with breakdown_left:
                if alt is not None and total_monthly > 0:
                    breakdown_chart = alt.Chart(breakdown).mark_bar(
                        cornerRadiusEnd=6
                    ).encode(
                        x=alt.X("Estimated CO₂ (kg/month):Q", title="kg CO₂ / month"),
                        y=alt.Y("Source:N", sort="-x", title=None),
                        color=alt.Color(
                            "Source:N",
                            scale=alt.Scale(
                                domain=["Electricity", "Petrol", "Diesel", "LPG"],
                                range=["#38bdf8", "#34d399", "#f59e0b", "#a78bfa"],
                            ),
                            legend=None,
                        ),
                        tooltip=[
                            alt.Tooltip("Source:N"),
                            alt.Tooltip("Estimated CO₂ (kg/month):Q", format=",.1f"),
                        ],
                    ).properties(height=190)
                    st.altair_chart(breakdown_chart, width="stretch")
                elif total_monthly > 0:
                    st.bar_chart(breakdown.set_index("Source"))
                else:
                    st.info("Enter a non-zero activity value to display the emissions breakdown.")
            with breakdown_right:
                st.markdown("**Largest category**")
                if total_monthly > 0:
                    st.metric(largest_source, f"{largest_amount:,.1f} kg CO₂", f"{largest_share:.1f}% of total")
                    st.progress(min(max(largest_share / 100, 0.0), 1.0))
                else:
                    st.metric("No activity entered", "0.0 kg CO₂")
                st.caption("The largest category is based only on the four inputs included in this calculator.")

            share_rows = []
            for name, amount in monthly_emissions.items():
                share_rows.append({
                    "Source": name,
                    "Monthly CO₂ (kg)": round(amount, 2),
                    "Share of included total (%)": round(amount / total_monthly * 100, 1) if total_monthly else 0.0,
                })
            st.dataframe(pd.DataFrame(share_rows), hide_index=True, use_container_width=True)

        with st.container(border=True):
            st.markdown("#### 04 · Practical reduction ideas")
            suggestions = {
                "Electricity": "Review high-use appliances, choose efficient equipment, and switch off devices that do not need to run.",
                "Petrol": "Combine errands, avoid unnecessary trips, and consider walking, cycling or shared transport for suitable journeys.",
                "Diesel": "Reduce avoidable generator or vehicle use where practical and keep engines maintained.",
                "LPG": "Use appropriately sized cookware, keep burners maintained and avoid unnecessary fuel use while cooking.",
            }
            active_suggestions = [
                (name, suggestions[name])
                for name, amount in monthly_emissions.items()
                if amount > 0
            ]
            if active_suggestions:
                suggestion_columns = st.columns(2)
                for index, (name, suggestion) in enumerate(active_suggestions):
                    with suggestion_columns[index % 2]:
                        st.markdown(
                            f'<div class="disaster-card"><div class="disaster-card-title">{name}</div>'
                            f'<div class="disaster-card-copy">{suggestion}</div></div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.info("Add a monthly activity value to see relevant reduction ideas.")

        report_rows = [
            {
                "Item": name,
                "Monthly activity / basis": value,
                "Emission factor": factor,
                "Estimated emissions (kg CO2)": monthly_emissions[label],
            }
            for name, value, factor, label in [
                ("Grid electricity", electricity_kwh, "0.675 kg CO2/kWh (CEA FY 2025-26)", "Electricity"),
                ("Petrol", petrol_litres, "2.31 kg CO2/litre (indicative direct combustion)", "Petrol"),
                ("Diesel", diesel_litres, "2.68 kg CO2/litre (indicative direct combustion)", "Diesel"),
                ("LPG", lpg_cylinders, "2.98 kg CO2/kg × 14.2 kg per cylinder (indicative)", "LPG"),
            ]
        ]
        report_rows.extend([
            {"Item": "Household total", "Monthly activity / basis": "Monthly estimate",
             "Emission factor": "Sum of categories", "Estimated emissions (kg CO2)": total_monthly},
            {"Item": "Annual household total", "Monthly activity / basis": "Monthly estimate × 12",
             "Emission factor": "Annualised estimate", "Estimated emissions (kg CO2)": total_annual},
            {"Item": "Household size", "Monthly activity / basis": household_size,
             "Emission factor": "People", "Estimated emissions (kg CO2)": ""},
            {"Item": "Per-person monthly estimate", "Monthly activity / basis": "Household total ÷ household size",
             "Emission factor": "Equal allocation; not a separate measurement",
             "Estimated emissions (kg CO2)": per_person_monthly},
        ])
        report = pd.DataFrame(report_rows)
        download_left, download_right = st.columns([1, 2], gap="medium")
        with download_left:
            st.download_button(
                "↓ Download household report (CSV)",
                data=report.to_csv(index=False).encode("utf-8-sig"),
                file_name="AI_RESILIENCE_Kochi_Household_Carbon_Footprint.csv",
                mime="text/csv",
                key="co2-footprint-download",
                use_container_width=True,
            )
        with download_right:
            st.caption("The report includes your entered activity, emission factors, category totals, annualised total and equal per-person allocation.")

        with st.expander("Calculation method, emission factors and limitations"):
            st.markdown(
                "- **Electricity:** kWh × 0.675 kg CO₂/kWh. CEA all-India weighted-average grid factor for FY 2025–26 (database v22.0); update when a newer factor is published.\n"
                "- **Petrol:** litres × 2.31 kg CO₂/litre (rounded indicative direct-combustion factor).\n"
                "- **Diesel:** litres × 2.68 kg CO₂/litre (rounded indicative direct-combustion factor).\n"
                "- **LPG:** cylinders × 14.2 kg × 2.98 kg CO₂/kg (rounded indicative direct-combustion factor)."
            )
            st.caption(
                "Fuel factors are rounded educational defaults, not product-specific or lifecycle factors. "
                "The estimate excludes food, shopping, flights, public transport, construction, upstream fuel supply "
                "and other indirect emissions. This calculator reports CO₂ only; it is not a complete CO₂e or lifecycle inventory."
            )
            st.markdown(
                "References: [Central Electricity Authority — CO₂ Baseline Database]("
                "https://cea.nic.in/divisionPage/510?lang=en) · "
                "[Kerala Environment Department — Energy and fuel emission-factor reference]("
                "https://climatechange.envt.kerala.gov.in/wp-content/uploads/2024/06/Energy.pdf)"
            )


def _render_compact_dashboard() -> None:
    """Render the short resident-facing view; legacy long sections are not reached."""
    section_intro("Monitoring", "Pollutant levels")
    st.caption("The cards above are hourly CAMS/Open-Meteo model estimates. Statuses below use compatible trailing averages and show a plain-language limitation when a complete reference window is unavailable.")
    live = {}
    try:
        live = load_live_air_quality()
        current = live.get("current", {})
    except Exception:
        current = {}
    _render_co2_intelligence(live)
    pollutant_names = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
    selected = st.selectbox("Pollutant details", ["All pollutants", *pollutant_names], key="air-pollutant-detail")
    if selected == "All pollutants":
        rows = []
        for pollutant in pollutant_names:
            item = current.get(pollutant)
            guide = POLLUTANT_GUIDELINES.get(pollutant)
            assessment = assess_pollutant(pollutant, item["value"] if item else None, item["unit"] if item else "", live.get("hourly", pd.DataFrame()))
            rows.append({
                "Pollutant": pollutant,
                "Latest": item["value"] if item else "Unavailable",
                "Unit": item["unit"] if item else "—",
                "Reference": f'{guide["limit"]:g} {guide["unit"]} ({guide["averaging"]})' if guide else "Unavailable",
                "Status": assessment["status"] if item else "Unavailable",
            })
        display_dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", alt="Live pollutant readings and reference status")
    else:
        item = current.get(selected)
        guide = POLLUTANT_GUIDELINES.get(selected)
        explanation, sources = {
            "PM2.5": ("Fine particles that can enter the lungs and bloodstream.", "Traffic, combustion, industry and fuel burning."),
            "PM10": ("Coarser particles affecting breathing and visibility.", "Road dust, construction and industrial dust."),
            "NO2": ("A combustion gas that irritates airways and helps form ozone.", "Traffic, generators and industrial combustion."),
            "SO2": ("A sulphur combustion gas that can irritate lungs and form particles.", "Sulphur-containing fuels and industrial processes."),
            "CO": ("A colourless gas that reduces oxygen transport in the body.", "Incomplete combustion, traffic and generators."),
            "O3": ("A secondary pollutant formed by sunlight-driven chemistry.", "Atmospheric reactions involving traffic and industry."),
        }[selected]
        if not item:
            st.info(f"{selected} is unavailable in the current response.")
        else:
            st.metric(selected, f'{item["value"]:g} {item["unit"]}')
            assessment = assess_pollutant(selected, item["value"], item["unit"], live.get("hourly", pd.DataFrame()))
            st.markdown(f'<span style="border:2px solid {assessment["color"]};border-radius:999px;padding:4px 10px;color:{assessment["color"]};font-weight:650;">{assessment["status"]}</span>', unsafe_allow_html=True)
            if assessment.get("assessed_value") is not None:
                st.caption(f'Assessment uses {assessment["window"]}: {assessment["assessed_value"]:.1f} {item["unit"]} compared with {guide["limit"]:g} {guide["unit"]}.')
            else:
                st.caption(assessment["reason"])
            if guide:
                st.caption(f'Reference: {guide["limit"]:g} {guide["unit"]}, {guide["averaging"]} · {guide["source"]}. This is a health guideline, not a CPCB legal limit.')
            health = HEALTH_INFORMATION[selected]
            with st.expander(f"Health and practical guidance for {selected}", expanded=True):
                st.write(health["summary"])
                st.write(health["effects"])
                st.write(f'**More sensitive:** {health["sensitive"]}')
                st.write(f'**Possible sources:** {health["sources"]}')
                st.write(f'**What residents can do:** {health["precautions"]}')
            if st.button("Investigate Reasons", key="air-investigate"):
                st.session_state["air-investigate-pollutant"] = selected

    with st.expander("🏭 Industrial Pollution Sources", expanded=bool(st.session_state.get("air-investigate-pollutant"))):
        st.markdown('<div id="industrial-pollution-sources"></div>', unsafe_allow_html=True)
        st.subheader("Industrial Pollution Sources")
        pollutant = st.selectbox("Select a pollutant to investigate", ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"], key="air-source-pollutant")
        st.caption("These are evidence leads for Kochi, Eloor and Edayar—not a ranking of responsibility for the current model estimate.")
        st.warning("No facility-specific current source-attribution measurement is available. A documented potential contributor is not proof that a facility caused a particular reading.")
        candidates = read_csv(INDUSTRIAL / "edayar_candidate_facilities.csv")
        if candidates.empty:
            st.info("No verified facility evidence record is available.")
        else:
            aliases = {"PM2.5": ("pm", "particulate", "dust"), "PM10": ("pm", "particulate", "dust"), "SO2": ("so2", "sulphur", "sulfur"), "CO": ("carbon monoxide", "co "), "NO2": ("no2", "nitrogen oxide", "combustion"), "O3": ("ozone", "voc", "nox")}
            matches = []
            for _, record in candidates.iterrows():
                text = " ".join(str(record.get(column, "")) for column in ("air_emissions_data", "emissions_limits_value", "measured_emissions_value", "documented_fuel_use", "candidate_basis")).casefold()
                measured = bool(str(record.get("measured_emissions_value", "")).strip()) and str(record.get("measured_emissions_status", "")).casefold() not in ("", "unavailable", "unverified")
                relevant = any(alias in text for alias in aliases.get(pollutant, ()))
                if measured or relevant:
                    associated = [name for name, terms in aliases.items() if any(term in text for term in terms)] or [pollutant]
                    row = {
                        "Facility": record.get("official_name") or record.get("facility_name_as_published"),
                        "Location": record.get("address_as_published") or record.get("industrial_area"),
                        "Industry type": record.get("industry_type_as_individually_documented"),
                        "Pollutant": pollutant,
                        "Associated pollutants": ", ".join(associated),
                        "Evidence category": evidence_category(measured_facility_emissions=measured, documented_facility_presence=relevant),
                        "Reported evidence": record.get("emissions_limits_value") or record.get("documented_fuel_use") or record.get("candidate_basis"),
                        "Evidence date": record.get("retrieved_on"),
                        "Source": record.get("source_url"),
                        "Current measured emissions verified": "Yes" if measured else "No",
                    }
                    matches.append(row)
            if matches:
                for match in matches:
                    evidence_color = {"Confirmed emissions evidence": "#dc3545", "Documented potential contributor": "#e67e22", "General possible source": "#d6a700", "Insufficient evidence": "#64748b"}.get(match["Evidence category"], "#64748b")
                    st.markdown(
                        f'<div style="border:1px solid {evidence_color};border-left:5px solid {evidence_color};border-radius:12px;padding:11px 14px;margin:8px 0;">'
                        f'<div style="font-weight:750;font-size:1.02rem;">{match["Facility"]}</div>'
                        f'<div style="font-size:.84rem;color:#a9c7cd;">{match["Location"]} · {match["Industry type"]}</div>'
                        f'<div style="margin-top:5px;"><span style="color:{evidence_color};font-weight:700;">{match["Evidence category"]}</span> · {match["Pollutant"]} · associated: {match["Associated pollutants"]}</div></div>',
                        unsafe_allow_html=True,
                    )
                    with st.expander(f"View Evidence · {match['Facility']}"):
                        st.write(f"**Reported evidence:** {match['Reported evidence']}")
                        st.write(f"**Evidence date:** {match['Evidence date']} · **Current measured emissions verified:** {match['Current measured emissions verified']}")
                        st.markdown(f"[Open source record]({match['Source']})")
            else:
                st.info(f"No facility-specific {pollutant} emissions measurement or permit detail was found in the reviewed Edayar records.")
            st.caption("A documented potential contributor is not proof of responsibility for the current model estimate. O₃ is generally formed in the atmosphere; no direct factory attribution is made.")

    with st.expander("Historical trends and KSPCB data"):
        if monthly_observations.empty:
            st.info("Historical monthly observations are unavailable in this checkout.")
        else:
            history = monthly_observations.copy()
            if {"observed_at", "pollutant", "value"}.issubset(history.columns):
                chart = history.pivot_table(index="observed_at", columns="pollutant", values="value", aggfunc="mean")
                st.line_chart(chart)
        if not daily_aqi.empty:
            st.caption("Historical KSPCB station extract — not live and not a model estimate.")
            columns = [c for c in ("station", "observed_at", "source_aqi", "PM2.5_value", "PM10_value", "NO2_value", "SO2_value", "CO_value", "O3_value") if c in daily_aqi.columns]
            display_dataframe(daily_aqi[columns].head(20), hide_index=True, width="stretch", alt="Historical KSPCB station AQI and pollutant values")
        else:
            st.info("Historical KSPCB station data is unavailable.")

    with st.expander("📚 Data Sources and Limitations"):
        st.markdown("**Sources**")
        observed = live.get("observed_at") if isinstance(live, dict) else None
        observed_label = observed.strftime("%d %b %Y, %H:%M UTC") if observed is not None else "Unavailable"
        historical_latest = pd.to_datetime(daily_aqi.get("observed_at"), errors="coerce").max() if not daily_aqi.empty and "observed_at" in daily_aqi else pd.NaT
        source_cards = [
            {"name": "CAMS via Open-Meteo", "link": OPEN_METEO_DOCS_URL, "station": "Kochi model grid (9.9312°N, 76.2673°E)", "timestamp": observed_label, "type": "Near-real-time modelled · app cache up to 15 minutes", "limit": "Not a CPCB/KSPCB station measurement."},
            {"name": "KSPCB historical extract", "link": "https://kspcb.kerala.gov.in/", "station": "Ernakulam/KSPCB records; Eloor history retained", "timestamp": historical_latest.strftime("%d %b %Y") if pd.notna(historical_latest) else "Unavailable", "type": "Historical observations", "limit": "Observation windows, completeness and some units are not fully specified in the published extracts."},
        ]
        for source in source_cards:
            st.markdown(
                f'<div style="border:1px solid rgba(130,190,199,.32);border-radius:11px;padding:10px 13px;margin:7px 0;">'
                f'<div style="font-weight:750;">{source["name"]}</div>'
                f'<div style="font-size:.85rem;">[{source["station"]}]({source["link"]}) · {source["type"]}</div>'
                f'<div style="font-size:.8rem;color:#a9c7cd;">Last observed: {source["timestamp"]} · {source["limit"]}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("**Limitations**")
        st.caption("The live feed is a CAMS/Open-Meteo model estimate and has no monitoring-station identity. CO₂ is modelled outdoor context, not a verified observation. PM1, NH₃ and facility-specific current emissions are unavailable in the live response. Missing values are left unavailable; no observations are invented or interpolated.")
        sources = register.get("sources", []) if isinstance(register, dict) else []
        if sources:
            with st.expander("Reviewed source register", expanded=False):
                source_rows = [{key: source.get(key) for key in ("id", "publisher", "status", "reviewed_on")} for source in sources if isinstance(source, dict)]
                if source_rows:
                    display_dataframe(pd.DataFrame(source_rows), hide_index=True, width="stretch", alt="Reviewed air-quality source register")


try:
    _render_compact_dashboard()
except Exception as error:
    st.warning(f"The compact historical dashboard could not render completely: {error}")
st.stop()

# Executive overview: show only facts that are directly available in the loaded extracts.
latest_extract_date = (
    pd.to_datetime(daily_aqi["observed_at"], errors="coerce").max().date()
    if not daily_aqi.empty and "observed_at" in daily_aqi.columns
    and pd.to_datetime(daily_aqi["observed_at"], errors="coerce").notna().any()
    else None
)

# Report freshness is calculated from the source observation date, not retrieval time.
report_age_days = (date.today() - latest_extract_date).days if latest_extract_date else None
if report_age_days is None:
    st.caption("No dated KSPCB station report is available in the historical extract.")
elif report_age_days < 0:
    st.warning(
        f"The latest source report is dated {latest_extract_date:%d %b %Y}, which is in the future "
        "relative to the application date. Check the source date before interpreting this extract."
    )
else:
    st.caption(
        f"Historical KSPCB station report: {latest_extract_date:%d %b %Y} "
        f"({report_age_days} days old). It is separate from the CAMS model estimate above."
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
    if (
        pd.notna(raw_eloor_aqi)
        and float(raw_eloor_aqi).is_integer()
        and 0 <= float(raw_eloor_aqi) <= 500
    ):
        eloor_category = cpcb_aqi_category(int(raw_eloor_aqi))[0]
        eloor_source_aqi = f"{int(raw_eloor_aqi)} · {eloor_category}"
section_intro("Overview", "Air quality at a glance")
overview = st.columns(6)
overview[0].metric("Latest loaded report", latest_extract_date.strftime("%d %b %Y") if latest_extract_date else "Unavailable")
overview[1].metric("Report age", f"{report_age_days} days" if report_age_days is not None and report_age_days >= 0 else "Review date", help="Days since the source observation date; this is a freshness indicator, not a pollution measure.")
overview[2].metric("Eloor source AQI", eloor_source_aqi, help="Source-reported value from the dated KSPCB daily extract; not a live reading.")
overview[3].metric("Stations in daily extract", station_count)
overview[4].metric("Eloor monthly reports", len(monthly_reports), help="August and September 2026 source reports when both pass ingestion checks.")
overview[5].metric("AQI calculation", "Evidence-gated", help="The app calculates AQI only when averaging period, valid hours and QA flags meet CPCB requirements.")
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
    if "source_aqi" in display_aqi.columns:
        display_aqi["CPCB AQI category"] = display_aqi["source_aqi"].map(
            safe_cpcb_aqi_category
        )
    else:
        st.warning(
            "The daily extract has no source_aqi column. AQI categories are unavailable "
            "for this file; pollutant fields will be displayed only when present."
        )
    report_date_label = (
        latest_extract_date.strftime("%d %B %Y")
        if latest_extract_date else "date unavailable"
    )
    st.caption(
        f"KSPCB source report date: {report_date_label}. AQI values are source-reported; "
        "the category label is mapped to CPCB's official band. These are historical readings."
    )
    columns = [
        "station", "observed_at", "source_aqi", "CPCB AQI category", "source_remark",
        "SO2_value", "CO_value", "PM2.5_value", "O3_value", "PM10_value", "NH3_value",
        "NOx_value", "NO_value", "NO2_value",
    ]
    available_display_columns = [
        column for column in columns if column in display_aqi.columns
    ]
    missing_display_columns = [
        column for column in columns
        if column not in display_aqi.columns and column != "CPCB AQI category"
    ]
    if missing_display_columns:
        st.caption(
            "Optional report fields absent from this extract: "
            + ", ".join(missing_display_columns)
        )
    if not available_display_columns:
        st.warning("No recognised station-report columns are available to display.")
    display_aqi = display_aqi[available_display_columns].rename(
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
    display_dataframe(display_aqi, hide_index=True, alt="Historical KSPCB station AQI and pollutant values")

    # A focused Eloor snapshot makes the industrial-belt report easier to scan.
    # Values are copied from the dated KSPCB extract; no unit conversion or averaging is applied.
    eloor_rows = (
        daily_aqi.loc[
            daily_aqi["station"].astype(str).str.strip().str.casefold().eq("eloor")
        ]
        if "station" in daily_aqi.columns
        else pd.DataFrame()
    )
    if not eloor_rows.empty:
        eloor_row = eloor_rows.iloc[0]
        st.markdown("#### Eloor pollutant snapshot")
        st.caption(
            f"KSPCB source-reported values · {report_date_label} · historical, not live"
        )
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
    st.markdown("**Daily extract data-quality audit**")
    audit_summary, pollutant_audit = audit_daily_extract(daily_aqi)
    audit_metrics = st.columns(4)
    audit_metrics[0].metric("Extract rows", audit_summary.get("rows", 0))
    audit_metrics[1].metric("Duplicate station-date rows", audit_summary.get("duplicate_rows", 0))
    audit_metrics[2].metric(
        "Missing / invalid dates",
        audit_summary.get("missing_dates", 0) + audit_summary.get("invalid_dates", 0),
    )
    audit_metrics[3].metric(
        "Missing / invalid AQI",
        audit_summary.get("missing_aqi", 0) + audit_summary.get("invalid_aqi", 0),
    )
    detail_metrics = st.columns(4)
    detail_metrics[0].metric("Non-numeric pollutants", audit_summary.get("pollutant_nonnumeric", 0))
    detail_metrics[1].metric("Negative pollutant values", audit_summary.get("pollutant_negative", 0))
    detail_metrics[2].metric("Unit mismatches", audit_summary.get("pollutant_unit_mismatches", 0))
    detail_metrics[3].metric("Rows QA-unassessed", audit_summary.get("unassessed_rows", 0))
    qa_metrics = st.columns(4)
    qa_metrics[0].metric("QA valid", audit_summary.get("valid_qa_rows", 0))
    qa_metrics[1].metric("QA suspect", audit_summary.get("suspect_qa_rows", 0))
    qa_metrics[2].metric("QA invalid", audit_summary.get("invalid_qa_rows", 0))
    qa_metrics[3].metric("Unknown QA flags", audit_summary.get("unknown_qa_rows", 0))
    if not pollutant_audit.empty:
        display_dataframe(
            pollutant_audit,
            hide_index=True,
            width="stretch",
            alt="Missing, non-numeric, negative and unit-mismatch counts in the daily pollutant extract",
        )
    st.caption(
        "This is a structural audit of the preserved CSV, not independent certification of "
        "the KSPCB measurements. Missing means no value is present; non-numeric means a "
        "non-empty value could not be parsed. Duplicate counts represent extra rows sharing "
        "the same station and report date. QA flags are counted exactly as recorded; unknown "
        "flags are not silently treated as valid, and suspect/invalid rows are not promoted."
    )
    if (
        audit_summary.get("duplicate_rows", 0)
        or audit_summary.get("missing_dates", 0)
        or audit_summary.get("invalid_dates", 0)
        or audit_summary.get("missing_aqi", 0)
        or audit_summary.get("invalid_aqi", 0)
        or audit_summary.get("missing_stations", 0)
        or audit_summary.get("pollutant_nonnumeric", 0)
        or audit_summary.get("pollutant_negative", 0)
        or audit_summary.get("pollutant_unit_mismatches", 0)
        or audit_summary.get("invalid_qa_rows", 0)
        or audit_summary.get("unknown_qa_rows", 0)
    ):
        st.warning(
            "The daily extract has structural issues that should be reviewed before "
            "using it in comparisons or calculations."
        )
    elif (
        audit_summary.get("unassessed_rows", 0)
        or audit_summary.get("missing_qa_rows", 0)
        or audit_summary.get("suspect_qa_rows", 0)
    ):
        st.info(
            "Basic structural checks did not identify the listed issues, but source QA is "
            "unassessed or incomplete. These records are not certified as validated measurements."
        )
    else:
        st.success(
            "No issues were detected by these basic structural checks. This does not replace "
            "the monitoring agency's quality-assurance review."
        )

    if not daily_status.empty:
        # Summarise only the station records present in these two dated extracts.
        # A missing AQI is a reporting-availability issue, not evidence of clean air.
        aqi_station_labels = (
            daily_aqi["station"].dropna().astype(str).str.strip()
            if "station" in daily_aqi.columns else pd.Series(dtype="string")
        )
        status_station_labels = (
            daily_status["station"].dropna().astype(str).str.strip()
            if "station" in daily_status.columns else pd.Series(dtype="string")
        )
        aqi_station_keys = set(aqi_station_labels.str.casefold())
        status_station_keys = set(status_station_labels.str.casefold())
        status_only_count = len(status_station_keys - aqi_station_keys)
        station_record_count = len(aqi_station_keys | status_station_keys)

        st.markdown("**Monitoring-network reporting coverage in this extract**")
        coverage_columns = st.columns(3)
        coverage_columns[0].metric("Stations with AQI rows", len(aqi_station_keys))
        coverage_columns[1].metric("Status-only stations", status_only_count)
        coverage_columns[2].metric("Distinct station records", station_record_count)
        st.caption(
            "Counts describe station labels in this dated report pair only; they are not a "
            "complete inventory of all operating KSPCB monitors."
        )

        if "source_status" in daily_status.columns:
            if "station" in daily_status.columns:
                status_summary = (
                    daily_status.assign(
                        _station_key=daily_status["station"].astype("string").str.strip().str.casefold(),
                        _status_label=daily_status["source_status"].astype("string").str.strip(),
                    )
                    .dropna(subset=["_status_label"])
                    .drop_duplicates(subset=["_station_key", "_status_label"])
                    .groupby("_status_label")["_station_key"]
                    .nunique()
                    .sort_values(ascending=False)
                )
            else:
                status_summary = pd.Series(dtype="int64")
                st.warning(
                    "The station-status extract has no station column, so station-level "
                    "status counts cannot be calculated."
                )
            if not status_summary.empty:
                status_columns = st.columns(min(3, len(status_summary)))
                for column, (status_label, count) in zip(status_columns, status_summary.items()):
                    column.metric(str(status_label).title(), int(count))

        st.write("Stations without a reported AQI in this report:")
        status_display = daily_status.rename(
            columns={
                "station": "KSPCB station label",
                "observed_at": "Report date",
                "source_status": "Reported status",
            }
        )
        status_display_columns = [
            column for column in (
                "KSPCB station label", "Report date", "Reported status"
            )
            if column in status_display.columns
        ]
        if status_display_columns:
            display_dataframe(
                status_display[status_display_columns],
                hide_index=True,
                alt="Stations marked unavailable in the KSPCB daily AQI report",
            )
        else:
            st.warning(
                "The station-status extract is present but contains none of the recognised "
                "station, date or status columns."
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
    display_dataframe(
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
        qa_counts = (
            station_data["quality_flag"].astype("string").str.strip().str.casefold()
            .value_counts()
        )
        st.markdown("**Source QA status for the selected station**")
        qa_columns = st.columns(4)
        for column, flag, label in zip(
            qa_columns,
            ("valid", "unassessed", "suspect", "invalid"),
            ("QA-valid rows", "Unassessed rows", "Suspect rows", "Invalid rows"),
        ):
            column.metric(label, int(qa_counts.get(flag, 0)))
        st.caption(
            "Schema validation confirms that records can be parsed for descriptive review; "
            "it does not turn source-unassessed records into QA-valid measurements."
        )
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

        trend_basis = st.radio(
            "Trend inclusion",
            (
                "All eligible source rows (includes unassessed)",
                "Only source QA-valid rows",
            ),
            horizontal=True,
            key="air_trend_qa_basis",
        )
        include_unassessed = trend_basis.startswith("All eligible")
        series_error = None
        try:
            series = time_series_summary(
                station_data, pollutant, include_unassessed=include_unassessed
            )
        except AirQualityDataError as error:
            series = pd.DataFrame()
            series_error = str(error)
        if not series.empty:
            series_dates = pd.to_datetime(series["observed_at"]).dt.date
            series = series.loc[
                (series_dates >= selected_start) & (series_dates <= selected_end)
            ]
        unit = station_data.loc[
            station_data["pollutant"].eq(pollutant), "unit"
        ].iloc[0]
        if series.empty:
            st.info(
                series_error
                or "No source-reported values are available for the selected pollutant and dates."
            )
        else:
            st.line_chart(
                series.set_index("observed_at")["mean_value"],
                y_label=f"{pollutant} ({unit})",
                alt=f"Historical daily KSPCB-reported {pollutant} values at Eloor from August through September 2026",
            )
            if include_unassessed:
                st.caption(
                    "Trend includes source rows marked valid or unassessed. Unassessed values "
                    "remain visibly unassessed in the QA summary above and must not be treated "
                    "as certified measurements."
                )
            else:
                st.caption(
                    "Trend includes only rows explicitly marked QA-valid by the source. "
                    "This filter does not independently certify the monitoring programme."
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
                    & ~selected_weather["wind_direction"].between(0, 360, inclusive="both")
                )
                negative_wind = (
                    selected_weather["wind_speed"].notna()
                    & selected_weather["wind_speed"].lt(0)
                )
                high_wind_review = (
                    selected_weather["wind_speed"].notna()
                    & selected_weather["wind_speed"].gt(20)
                )

                weather_metrics = st.columns(5)
                weather_metrics[0].metric(
                    "Dated weather records", len(selected_weather)
                )
                weather_metrics[1].metric(
                    "Humidity outside 0–100%", int(humidity_invalid.sum())
                )
                weather_metrics[2].metric(
                    "Invalid wind direction", int(direction_invalid.sum())
                )
                weather_metrics[3].metric(
                    "Negative wind speed", int(negative_wind.sum())
                )
                weather_metrics[4].metric(
                    "Wind speed >20 m/s · review", int(high_wind_review.sum())
                )

                temperature_series = selected_weather.dropna(
                    subset=["temperature"]
                ).set_index("observed_at")["temperature"]
                # Negative wind speed is physically invalid and is excluded from
                # the chart; unusually high positive speeds remain visible for review.
                wind_series = selected_weather.loc[
                    selected_weather["wind_speed"].notna()
                    & selected_weather["wind_speed"].ge(0)
                ].set_index("observed_at")["wind_speed"]
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
                    display_dataframe(
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
                    "Humidity outside 0–100% and negative wind speeds are excluded from their "
                    "charts, but the original source-reported values remain unchanged in the "
                    "review table. No values are silently corrected or replaced. Wind speeds above "
                    "20 m/s are flagged for source review only and remain visible in the wind chart; "
                    "this app threshold is not a KSPCB quality flag. The source does not state exact "
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
            august_mean = "August 2026 mean of daily report values"
            september_mean = "September 2026 mean of daily report values"
            if august_mean in comparison.columns and september_mean in comparison.columns:
                august_values = pd.to_numeric(comparison[august_mean], errors="coerce")
                september_values = pd.to_numeric(comparison[september_mean], errors="coerce")
                comparison["Change in mean (%)"] = (
                    (september_values - august_values)
                    .div(august_values.where(august_values.ne(0)))
                    .mul(100)
                    .round(1)
                )
                comparison["Descriptive direction"] = "No change"
                comparison.loc[
                    september_values.gt(august_values), "Descriptive direction"
                ] = "Higher in September"
                comparison.loc[
                    september_values.lt(august_values), "Descriptive direction"
                ] = "Lower in September"
                comparison.loc[
                    august_values.eq(0) & september_values.ne(0),
                    "Descriptive direction",
                ] = "Change not expressed as % (August mean is zero)"
                comparison.loc[
                    august_values.eq(0) & september_values.eq(0),
                    "Change in mean (%)",
                ] = 0.0

            display_dataframe(
                comparison,
                hide_index=True,
                alt="Descriptive August and September means and percentage changes for matching Eloor pollutant report fields",
            )
            st.caption(
                "Percentage change is calculated from the two arithmetic means of dated report values. "
                "It is descriptive only: the reports do not provide row-level QA, exact averaging "
                "intervals, or a basis for statistical significance or source attribution."
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
    display_dataframe(
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
        display_dataframe(
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
        display_dataframe(
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
display_dataframe(category_table, hide_index=True, alt="CPCB AQI categories and health meanings")
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
    display_dataframe(
        pd.DataFrame(eligibility_rows),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "No application-calculated AQI is produced for the current extract: its averaging "
        "interval is unspecified, row-level quality is unassessed, and valid-hour counts are "
        "not supplied. Source-reported AQI remains displayed separately and is not overwritten."
    )

st.markdown('<div id="evidence-timeline"></div>', unsafe_allow_html=True)
st.subheader("Eloor–Edayar pollution evidence timeline")
st.caption(
    "Chronology of dated ambient-air reporting and documented consent events. "
    "Timeline proximity is not evidence that a facility caused an ambient concentration."
)

timeline_events = []
for report_month, report in monthly_reports.items():
    # Derive the observed date span from the verified day-precision extract.
    # Do not require optional metadata fields that older source records lack.
    report_dates = pd.to_datetime(
        report["observations"]["observed_at"], format="%Y-%m-%d", errors="coerce"
    ).dropna()
    start_date = report_dates.min().strftime("%Y-%m-%d") if not report_dates.empty else None
    end_date = report_dates.max().strftime("%Y-%m-%d") if not report_dates.empty else None
    if start_date and end_date:
        timeline_events.append(
            {
                "Date": start_date,
                "Evidence stream": "Ambient monitoring",
                "Event": (
                    f"Eloor CAAQMS daily report period: {start_date} to {end_date}"
                ),
                "Evidence note": (
                    "KSPCB source-reported daily ambient observations; exact averaging "
                    "interval and row-level QA/completeness are not stated."
                ),
                "Source / record": report.get("source_url", ""),
            }
        )

consent_records = read_csv(INDUSTRIAL / "edayar_consent_records.csv")
if not consent_records.empty:
    for _, record in consent_records.iterrows():
        facility_name = str(record.get("facility_name_in_record", "")).strip()
        consent_type = str(record.get("consent_type", "")).strip()
        decision = str(record.get("decision", "")).strip()
        submitted_on = str(record.get("application_submitted_on", "")).strip()
        decision_date = str(record.get("decision_or_issue_date", "")).strip()
        valid_until = str(record.get("valid_until", "")).strip()
        source_url = str(record.get("source_url", "")).strip()
        record_id = str(record.get("record_id", "")).strip()

        if submitted_on and submitted_on.casefold() != "nan":
            timeline_events.append(
                {
                    "Date": submitted_on,
                    "Evidence stream": "Consent application",
                    "Event": f"{facility_name}: {consent_type} application submitted",
                    "Evidence note": f"Application {record.get('application_number', '')}; submission date as transcribed in the reviewed register.",
                    "Source / record": source_url,
                }
            )
        if decision_date and decision_date.casefold() != "nan":
            timeline_events.append(
                {
                    "Date": decision_date,
                    "Evidence stream": "Consent decision",
                    "Event": f"{facility_name}: {consent_type} — {decision}",
                    "Evidence note": (
                        f"Record {record_id}. This records the application decision, "
                        "not proof of present operation or ambient emissions."
                    ),
                    "Source / record": source_url,
                }
            )
        if valid_until and valid_until.casefold() != "nan":
            timeline_events.append(
                {
                    "Date": valid_until,
                    "Evidence stream": "Consent validity date",
                    "Event": f"{facility_name}: stated validity end for {consent_type}",
                    "Evidence note": (
                        "Expiry date printed in the indexed record; later renewal, "
                        "revocation or replacement may not be represented here."
                    ),
                    "Source / record": source_url,
                }
            )

if timeline_events:
    timeline = pd.DataFrame(timeline_events)
    timeline["_sort_date"] = pd.to_datetime(
        timeline["Date"], format="%Y-%m-%d", errors="coerce"
    )
    undated_event_count = int(timeline["_sort_date"].isna().sum())
    timeline = timeline.loc[timeline["_sort_date"].notna()].copy()

    if timeline.empty:
        st.warning(
            f"{undated_event_count} timeline record(s) were found, but none had a valid "
            "YYYY-MM-DD date. They are excluded from the chronological display."
        )
    else:
        timeline = timeline.sort_values(
            ["_sort_date", "Evidence stream", "Event"]
        ).drop(columns="_sort_date")
        stream_options = ["All evidence streams"] + sorted(
            timeline["Evidence stream"].unique().tolist()
        )
        selected_stream = st.selectbox(
            "Filter timeline",
            stream_options,
            key="evidence_timeline_stream",
        )
        visible_timeline = (
            timeline if selected_stream == "All evidence streams"
            else timeline.loc[timeline["Evidence stream"].eq(selected_stream)]
        )
        display_dataframe(
            visible_timeline,
            hide_index=True,
            width="stretch",
            column_config={
                "Source / record": st.column_config.LinkColumn(
                    "Source / record",
                    display_text="Open source record",
                )
            },
            alt="Chronological timeline of Eloor ambient monitoring periods and Edayar consent records",
        )
        st.caption(
            f"Showing {len(visible_timeline)} dated events from the records currently available "
            "in this project. Dates describe the source record; they are not continuous monitoring "
            "coverage. Consent-to-establish (CTE), consent-to-operate (CTO), rejected applications, "
            "and stated expiry dates remain distinct."
        )
        if undated_event_count:
            st.warning(
                f"{undated_event_count} timeline record(s) had missing or invalid dates and "
                "were excluded from the chronological display. Check the source register before "
                "using those records in a date-based comparison."
            )
else:
    st.info(
        "No dated ambient-report or facility consent events are available to build the timeline."
    )

st.info(
    "Evidence boundary: the Eloor reports contain ambient station summaries, while the Edayar "
    "register contains consent/application history. The reviewed inventory has no verified "
    "facility coordinates or measured stack-emission results. This chronology cannot establish "
    "a facility-to-ambient pollution link."
)

st.subheader("Documented NAMP network reference")
stations = pd.DataFrame(register["kspcb_namp_ernakulam_stations"])
display_dataframe(stations, hide_index=True, alt="KSPCB Ernakulam NAMP monitoring-station inventory")
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
    display_dataframe(
        display_candidates,
        hide_index=True,
        alt="Edayar facilities listed as candidates with current evidence gaps",
    )

    # Summarise the newer facility-level evidence fields without treating
    # historical records or permit limits as current measured emissions.
    st.markdown("**Facility evidence coverage**")
    evidence_columns = st.columns(4)
    evidence_columns[0].metric("Candidate facilities", len(facility_candidates))
    evidence_columns[1].metric(
        "Identity records verified",
        int(facility_candidates["identity_status"].eq("verified").sum()),
    )
    evidence_columns[2].metric(
        "Verified facility coordinates",
        int(facility_candidates["coordinates_status"].eq("verified").sum()),
    )
    evidence_columns[3].metric(
        "Measured stack results verified",
        int(facility_candidates["measured_emissions_status"].eq("verified").sum()),
    )

    evidence_fields = [
        "official_name",
        "address_as_published",
        "coordinates_status",
        "current_consent_evidence_status",
        "emissions_limits_status",
        "measured_emissions_status",
        "environmental_clearance_evidence_status",
        "ranking_evidence_status",
    ]
    evidence_labels = {
        "official_name": "Registered / matched name",
        "address_as_published": "Published facility address",
        "coordinates_status": "Facility coordinates",
        "current_consent_evidence_status": "Current consent evidence",
        "emissions_limits_status": "Emission limits",
        "measured_emissions_status": "Measured stack emissions",
        "environmental_clearance_evidence_status": "Environmental clearance",
        "ranking_evidence_status": "Source-ranking evidence",
    }
    evidence_table = facility_candidates[evidence_fields].rename(
        columns=evidence_labels
    )
    display_dataframe(
        evidence_table,
        hide_index=True,
        width="stretch",
        alt="Facility-level evidence status for eight Edayar candidate facilities",
    )
    st.caption(
        "Status labels describe the evidence located in this project’s reviewed records. "
        "A historical consent or emission limit is not a current consent verification or "
        "an actual stack measurement. No facility coordinates or measured stack results "
        "are currently verified in this inventory."
    )

    st.markdown("**Pollutant-by-pollutant evidence comparison**")
    st.caption(
        "Ambient counts below come from the provenance-checked Eloor monthly extracts. "
        "A dated row is not automatically a QA-validated measurement. Facility stack evidence "
        "is assessed separately and is not inferred from ambient concentrations or permit limits."
    )
    pollutant_inventory = [
        ("PM2.5", ("PM2.5", "PM2_5")),
        ("PM10", ("PM10",)),
        ("NO₂", ("NO2",)),
        ("NO", ("NO",)),
        ("NOx", ("NOx",)),
        ("SO₂", ("SO2",)),
        ("O₃", ("O3",)),
        ("CO", ("CO",)),
        ("NH₃", ("NH3",)),
    ]
    comparison_rows = []
    for display_name, source_names in pollutant_inventory:
        ambient_rows = (
            monthly_observations.loc[
                monthly_observations["pollutant"].astype(str).str.upper().isin(
                    {name.upper() for name in source_names}
                )
            ].copy()
            if not monthly_observations.empty
            else pd.DataFrame()
        )
        numeric_values = (
            pd.to_numeric(ambient_rows["value"], errors="coerce")
            if not ambient_rows.empty else pd.Series(dtype="float64")
        )
        dated_values = int(numeric_values.notna().sum())
        qa_valid_values = (
            int(
                (
                    numeric_values.notna()
                    & ambient_rows["quality_flag"].astype(str).str.casefold().eq("valid")
                ).sum()
            )
            if not ambient_rows.empty else 0
        )
        report_month_count = (
            int(ambient_rows["observed_at"].astype(str).str.slice(0, 7).nunique())
            if not ambient_rows.empty else 0
        )
        source_units = (
            ", ".join(sorted(ambient_rows["unit"].dropna().astype(str).unique()))
            if not ambient_rows.empty else "—"
        )
        comparison_rows.append(
            {
                "Pollutant": display_name,
                "Eloor dated ambient values": dated_values,
                "Months represented": report_month_count,
                "Source unit(s)": source_units,
                "Rows explicitly QA-valid": qa_valid_values,
                "Facility measured stack results": "Not located",
                "Evidence interpretation": (
                    "Historical ambient records; QA unassessed"
                    if dated_values else "No dated ambient values in loaded extracts"
                ),
            }
        )
    pollutant_comparison = pd.DataFrame(comparison_rows)
    display_dataframe(
        pollutant_comparison,
        hide_index=True,
        width="stretch",
        alt="Pollutant-level comparison of Eloor ambient report coverage and Edayar facility stack evidence",
    )
    st.caption(
        "The current Edayar inventory records no actual measured stack-emission results for "
        "the candidate facilities. Historical permit limits, where present, are not measurements "
        "and are not substituted into this table. ‘Not located’ means absent from the reviewed "
        "project records, not proof that measurements do not exist elsewhere."
    )

if not industry_type_counts.empty:
    st.markdown("**Estate-level trade-effluent industry categories reported by KWA**")
    display_dataframe(
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
    display_dataframe(
        readiness_table,
        hide_index=True,
        alt="Evidence readiness for each unranked Edayar candidate facility",
    )

    st.markdown("**Actionable evidence-gap register**")
    st.caption(
        "This register translates each evidence gate into a specific data request. "
        "It is a research checklist, not a facility score or source ranking."
    )
    action_rows = []
    for candidate in source_assessment["candidates"]:
        required_evidence = {
            field: candidate["evidence"].get(field)
            for field in SOURCE_EVIDENCE_REQUIREMENTS
        }
        for item in evidence_action_plan(required_evidence):
            action_rows.append(
                {
                    "Candidate facility": candidate["facility_name"],
                    "Evidence domain": item["evidence_domain"].replace("_", " ").title(),
                    "Status": item["status"],
                    "Evidence requirement": item["requirement"],
                    "Recommended next action": item["next_action"],
                }
            )
    action_plan = pd.DataFrame(action_rows)
    if not action_plan.empty:
        missing_actions = action_plan.loc[action_plan["Status"].eq("Missing")].copy()
        total_gates = len(action_plan)
        available_gates = total_gates - len(missing_actions)
        action_metrics = st.columns(3)
        action_metrics[0].metric("Evidence checks", total_gates)
        action_metrics[1].metric("Available for review", available_gates)
        action_metrics[2].metric("Open evidence gaps", len(missing_actions))
        if missing_actions.empty:
            st.success(
                "All minimum evidence domains are marked available. Independent scientific "
                "method review is still required; this is not permission to attribute pollution."
            )
        else:
            display_dataframe(
                missing_actions,
                hide_index=True,
                width="stretch",
                alt="Actionable missing evidence requests for each industrial candidate",
            )
            st.warning(
                f"{len(missing_actions)} evidence requirement(s) remain open across "
                f"{len(source_assessment['candidates'])} candidate record(s). No source ranking "
                "or causal attribution is produced."
            )
        with st.expander("View all evidence requirements"):
            display_dataframe(
                action_plan,
                hide_index=True,
                width="stretch",
                alt="Complete industrial source evidence checklist",
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

source_review_rows = []
for source in register["sources"]:
    reviewed_value = source.get("reviewed_on")
    try:
        reviewed_date = date.fromisoformat(str(reviewed_value))
        review_age_days = (date.today() - reviewed_date).days
        review_date_check = (
            "Future date — check register" if review_age_days < 0 else "Valid date"
        )
    except (TypeError, ValueError):
        reviewed_date = None
        review_age_days = None
        review_date_check = "Missing or invalid date"

    source_review_rows.append(
        {
            "Publisher": source.get("publisher", "Publisher not recorded"),
            "Evidence status": source.get("evidence_status", "Not classified"),
            "Source status": source.get("status", "Status not recorded"),
            "Reviewed on": reviewed_value or "Not recorded",
            "Days since review": review_age_days if review_age_days is not None else "—",
            "Date check": review_date_check,
        }
    )

source_review_table = pd.DataFrame(source_review_rows)
if not source_review_table.empty:
    display_dataframe(
        source_review_table,
        hide_index=True,
        width="stretch",
        alt="Source register review dates and evidence status",
    )
    invalid_review_dates = int(
        source_review_table["Date check"].ne("Valid date").sum()
    )
    st.caption(
        f"{len(source_review_table)} source records are listed in the register. "
        "Review age is calculated from each record's reviewed_on date; it is not "
        "the publication date or the age of the underlying observation."
    )
    if invalid_review_dates:
        st.warning(
            f"{invalid_review_dates} source record(s) have a missing, invalid or future "
            "review date. Check the source register before relying on their review metadata."
        )

for source in register["sources"]:
    publisher = source.get("publisher", "Publisher not recorded")
    source_url = str(source.get("url") or "").strip()
    try:
        parsed_source_url = urlsplit(source_url)
        valid_https_url = (
            parsed_source_url.scheme == "https"
            and bool(parsed_source_url.hostname)
            and parsed_source_url.username is None
            and parsed_source_url.password is None
        )
    except ValueError:
        valid_https_url = False

    if valid_https_url:
        st.markdown(
            f"- [{publisher}]({source_url}) — {source.get('status', 'Status not recorded')}"
        )
    else:
        st.warning(
            f"{publisher}: the source URL is missing or is not a valid HTTPS web address. "
            "Verify the register entry before using the link."
        )

with st.expander("Evidence and reuse notes"):
    for source in register["sources"]:
        st.markdown(f"**{source.get('publisher', 'Publisher not recorded')}**")
        st.write(source.get("evidence", "No evidence description recorded."))
        st.caption(f"Coverage: {source.get('geographic_coverage', 'Not recorded')}")
        st.caption(f"Limitations/blocker: {source.get('blocker', 'Not recorded')}")
        st.caption(
            f"Reuse: {source.get('reuse_status', 'Not recorded')} | "
            f"Reviewed: {source.get('reviewed_on', 'Not recorded')}"
        )

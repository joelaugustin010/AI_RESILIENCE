"""Evidence-aware pollutant, CO2 and industrial-source dashboard components."""
from __future__ import annotations
import re
from pathlib import Path
from typing import Any
import pandas as pd
import streamlit as st

POLLUTANTS: dict[str, dict[str, Any]] = {
    "PM2.5": {"aliases": {"PM2.5", "PM2_5"}, "unit": "µg/m³", "limit": 60.0, "period": "24-hour",
        "health": "Fine particles can travel deep into the lungs. Exposure is associated with worsened asthma and other respiratory symptoms, and increased cardiovascular risk, especially with repeated exposure.",
        "precautions": "When levels are elevated, reduce prolonged strenuous outdoor activity, avoid smoky or dusty areas, and follow local health advisories. People with heart or lung conditions should follow their clinician's advice."},
    "PM10": {"aliases": {"PM10"}, "unit": "µg/m³", "limit": 100.0, "period": "24-hour",
        "health": "Inhalable particles can irritate the nose, throat and airways and may worsen asthma or other breathing problems.",
        "precautions": "Limit time near road dust, construction and dusty industrial areas. Reduce strenuous outdoor activity during elevated episodes."},
    "NO₂": {"aliases": {"NO2"}, "unit": "µg/m³", "limit": 80.0, "period": "24-hour",
        "health": "Nitrogen dioxide irritates airways and can worsen asthma and other respiratory conditions. It is commonly associated with fuel combustion.",
        "precautions": "Avoid prolonged strenuous activity beside busy roads or visible combustion plumes when levels are elevated. Follow official local advisories."},
    "SO₂": {"aliases": {"SO2"}, "unit": "µg/m³", "limit": 80.0, "period": "24-hour",
        "health": "Sulphur dioxide can irritate the respiratory system and trigger breathing symptoms. People with asthma may be particularly sensitive.",
        "precautions": "Move away from suspected smoke or industrial plumes, reduce strenuous outdoor activity during elevated episodes, and follow prescribed asthma action plans."},
    "CO": {"aliases": {"CO"}, "unit": "mg/m³", "limit": 2.0, "period": "8-hour",
        "health": "Carbon monoxide reduces the blood's ability to carry oxygen. High exposure can be dangerous. It is colourless and odourless.",
        "precautions": "Never rely on smell to detect carbon monoxide. If a CO alarm sounds or exposure is suspected, move to fresh air and contact emergency services."},
    "O₃": {"aliases": {"O3"}, "unit": "µg/m³", "limit": 100.0, "period": "8-hour",
        "health": "Ground-level ozone can irritate the lungs, cause coughing or discomfort, and worsen respiratory conditions. It is different from the protective ozone layer high in the atmosphere.",
        "precautions": "When ozone is elevated, reduce strenuous outdoor activity and consider exercising at a time when levels are lower. Follow official air-quality advisories."},
}

def _safe_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()

def _normalise_unit(value: Any) -> str:
    return _safe_text(value).casefold().replace("μ", "u").replace("µ", "u").replace("³", "3").replace(" ", "")

def period_matches(actual: Any, expected: str) -> bool:
    """Match only explicit 8-hour or 24-hour averaging-period labels."""
    text = _safe_text(actual).casefold().replace("_", "-")
    if expected == "24-hour":
        return bool(re.search(r"(?:24\s*[- ]?hour|24\s*h(?:r|rs)?)", text))
    if expected == "8-hour":
        return bool(re.search(r"(?:8\s*[- ]?hour|8\s*h(?:r|rs)?)", text))
    return False

def classify_reference(value: Any, averaging_period: Any, quality_flag: Any, pollutant: str, unit: Any) -> tuple[str, str]:
    """Compare only numeric, QA-valid observations with matching period and unit."""
    spec = POLLUTANTS.get(pollutant)
    if spec is None:
        return "unavailable", "No reference configured"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "unavailable", "No numeric observation"
    if not pd.notna(numeric) or numeric < 0:
        return "unavailable", "No valid numeric observation"
    if _safe_text(quality_flag).casefold() != "valid":
        return "unavailable", "Measurement quality is not marked valid"
    if not period_matches(averaging_period, spec["period"]):
        return "unavailable", f"Needs a {spec['period']} observation"
    if _normalise_unit(unit) != _normalise_unit(spec["unit"]):
        return "unavailable", f"Unit must be {spec['unit']}"
    if numeric <= spec["limit"]:
        return "within", f"Within CPCB {spec['period']} standard"
    return "above", f"Above CPCB {spec['period']} standard"

def _latest_rows(observations: pd.DataFrame) -> dict[str, dict[str, Any]]:
    required = {"pollutant", "observed_at", "value"}
    if observations.empty or not required.issubset(observations.columns):
        return {}
    data = observations.copy()
    data["_date"] = pd.to_datetime(data["observed_at"], errors="coerce")
    data = data.loc[data["_date"].notna()].sort_values("_date")
    result: dict[str, dict[str, Any]] = {}
    for label, spec in POLLUTANTS.items():
        rows = data.loc[data["pollutant"].astype(str).str.upper().isin({str(x).upper() for x in spec["aliases"]})]
        if not rows.empty:
            result[label] = rows.iloc[-1].to_dict()
    return result

def _render_pollutant_card(name: str, spec: dict[str, Any], row: dict[str, Any] | None) -> None:
    if row is None:
        st.markdown(f"**{name}**")
        st.caption("No dated observation in the currently loaded extracts.")
        return
    value = pd.to_numeric(pd.Series([row.get("value")]), errors="coerce").iloc[0]
    unit = _safe_text(row.get("unit")) or spec["unit"]
    status, label = classify_reference(value, row.get("averaging_period"), row.get("quality_flag"), name, unit)
    st.metric(name, f"{value:g} {unit}" if pd.notna(value) else "No numeric value")
    if status == "within":
        st.success(label)
    elif status == "above":
        st.warning(label)
    else:
        st.info("Reference comparison not available")
        st.caption(label)
    st.caption(f"Observation date: {row.get('observed_at', 'Not recorded')}")
    with st.expander(f"Why {name} matters · Precautions"):
        st.write(spec["health"])
        st.markdown("**What people can do**")
        st.write(spec["precautions"])
        st.caption(f"CPCB reference: {spec['period']} value {spec['limit']:g} {spec['unit']}. Comparison requires matching source period, unit and QA.")

def render_air_pollution_intelligence(observations: pd.DataFrame, industrial_csv: Path) -> None:
    """Render the compact pollutant, CO2 and industrial-source intelligence area."""
    st.markdown("## Air Quality & CO₂ Intelligence")
    st.caption("Interpretation of acquired observations. Historical day-level reports are not presented as live or hourly measurements.")
    st.markdown("### CO₂ Intelligence")
    left, right = st.columns([1, 2])
    with left:
        st.metric("Outdoor CO₂", "Unavailable", help="No verified ambient CO₂ observation is currently connected.")
        st.caption("Unit: ppm · No measurement source loaded")
    with right:
        st.info("CO₂ monitoring is not yet connected to a verified local observation source. No demonstration value is substituted.")
        st.markdown("**Why CO₂ matters:** Outdoor carbon dioxide is important mainly because it accumulates in the atmosphere and strengthens the greenhouse effect. An ordinary outdoor concentration reading is not an AQI value or an immediate-poisoning warning.")
    with st.expander("CO₂ details, sources and actions"):
        st.markdown("- **Ambient concentration:** parts per million (ppm).\n- **Emissions:** a separate quantity, usually mass such as tonnes of CO₂.\n- **Common sources:** fossil-fuel combustion for electricity, industry and transport, plus land-use and natural processes.\n- **Climate significance:** sustained increases in atmospheric CO₂ contribute to long-term global warming.\n- **Actions:** improve energy efficiency, use lower-carbon electricity and fuels, reduce avoidable fuel use, and monitor industrial greenhouse-gas emissions.")
        st.caption("Ambient ppm cannot be converted directly into a factory's tonnes of emissions or a person's carbon footprint. Indoor ventilation guidance is not applied to outdoor air.")
    st.markdown("### Pollutant levels")
    st.caption("Green means the observation meets the stated CPCB reference; yellow means it is above that reference. If period, units or source QA are insufficient, no traffic-light judgement is shown.")
    latest = _latest_rows(observations)
    cols = st.columns(3)
    for index, (name, spec) in enumerate(POLLUTANTS.items()):
        with cols[index % 3]:
            _render_pollutant_card(name, spec, latest.get(name))
    if not observations.empty:
        chart = observations.copy()
        chart["value"] = pd.to_numeric(chart["value"], errors="coerce")
        chart["observed_at"] = pd.to_datetime(chart["observed_at"], errors="coerce")
        chart = chart.loc[chart["value"].notna() & chart["observed_at"].notna()]
        if not chart.empty:
            st.markdown("### Historical pollutant trends")
            st.caption("The loaded Eloor extracts have day-level dates, not verified hourly timestamps.")
            options = sorted(chart["pollutant"].dropna().astype(str).unique().tolist())
            selected = st.selectbox("Choose a pollutant trend", options, key="air_intelligence_trend")
            selected_rows = chart.loc[chart["pollutant"].astype(str).eq(selected)]
            if not selected_rows.empty:
                st.line_chart(selected_rows.set_index("observed_at")["value"].sort_index(), y_label=str(selected_rows.iloc[-1].get("unit") or "Source unit"))
    st.markdown("### Industrial pollution sources")
    st.caption("Facility cards are research leads, not proof that a facility caused a monitoring-station reading.")
    choice = st.selectbox("Investigate a pollutant", ["PM2.5", "PM10", "NO₂", "SO₂", "CO", "O₃", "CO₂"], key="air_intelligence_source_pollutant")
    try:
        facilities = pd.read_csv(industrial_csv)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError):
        facilities = pd.DataFrame()
    if facilities.empty:
        st.info("The reviewed industrial-facility inventory is unavailable.")
    else:
        st.info(f"No facility-specific measured stack-emission results are verified for {choice}. The facilities below are Edayar candidates for further investigation, not confirmed sources.")
        for _, facility in facilities.iterrows():
            name = _safe_text(facility.get("official_name")) or _safe_text(facility.get("facility_name_as_published")) or "Unnamed candidate"
            industry = _safe_text(facility.get("industry_type_as_individually_documented")) or "Industry process not individually documented"
            address = _safe_text(facility.get("address_as_published")) or "Facility address not recorded"
            evidence = _safe_text(facility.get("measured_emissions_status")) or "unavailable"
            url = _safe_text(facility.get("source_url"))
            with st.expander(name):
                st.write(industry)
                st.caption(address)
                st.caption(f"Measured stack-emission evidence: {evidence}")
                st.warning("Candidate facility only — no causal link to the selected ambient pollutant is established.")
                if url.startswith("https://"):
                    st.markdown(f"[Open facility inventory source]({url})")
    with st.expander("Data sources and limitations"):
        st.markdown("- **KSPCB Eloor monthly reports:** historical day-level observations; exact averaging intervals and row-level QA are not established for every record.\n- **KSPCB daily AQI extracts:** dated historical reports, not a live feed.\n- **Industrial inventory:** facility identity/process leads and consent context; measured stack emissions and source attribution are not established.\n- **CO₂:** no verified local ambient CO₂ series is connected.")
        st.caption("Original source files and timestamps are retained. Missing data are not filled, historical values are not labelled live, and no factory is blamed without evidence.")

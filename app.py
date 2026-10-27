"""AI RESILIENCE prototype entry point and shared navigation."""

from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent

@st.cache_data(ttl=3600)
def load_quality_summary() -> tuple[str, str]:
    """Read the two known hydrology issues for concise app-wide warnings."""
    conflict_path = ROOT / "data" / "processed" / "cwc_rainfall_conflicts.csv"
    if conflict_path.is_file():
        conflicts = pd.read_csv(conflict_path, usecols=["Station", "Data Acquisition Time"])
        conflict_groups = conflicts.drop_duplicates().shape[0]
        rainfall_warning = (
            f"Rainfall QA: the reviewed conflict export contains {conflict_groups:,} "
            "station-time groups with conflicting readings. Raw values are preserved."
        )
    else:
        rainfall_warning = (
            "Rainfall QA: the project audit previously found conflicting duplicate "
            "station-time readings. Review them before using rainfall for thresholds."
        )

    telemetry_path = ROOT / "data" / "raw" / "rwl_tel_hr_kerala_sw_031_2021_2025.csv"
    try:
        telemetry = pd.read_csv(
            telemetry_path,
            usecols=["Station", "Data Acquisition Time", "River Water Level Telemetry Hourly (meter)"],
        )
        station = telemetry["Station"].astype("string").str.strip().str.casefold()
        station_rows = telemetry.loc[station.eq("f.c.s. mananthavadi")].copy()
        station_rows["_time"] = pd.to_datetime(
            station_rows["Data Acquisition Time"], dayfirst=True, errors="coerce"
        )
        station_rows["_value"] = pd.to_numeric(
            station_rows["River Water Level Telemetry Hourly (meter)"], errors="coerce"
        )
        station_rows = station_rows.dropna(subset=["_time", "_value"]).sort_values("_time")
        delta = station_rows["_value"].diff().abs()
        index = delta.idxmax()
        position = station_rows.index.get_loc(index)
        before = station_rows.iloc[position - 1]
        after = station_rows.iloc[position]
        jump = float(delta.loc[index])
        gap = after["_time"] - before["_time"]
        river_warning = (
            "River-level QA: F.C.S. Mananthavadi telemetry has a large change "
            f"({jump:.3f} m) across a {gap.days}-day data gap. The reporting reference "
            "is unconfirmed; do not apply an automatic correction."
        )
    except (OSError, ValueError, KeyError, IndexError, pd.errors.ParserError):
        river_warning = (
            "River-level QA: F.C.S. Mananthavadi telemetry has a previously reviewed "
            "large change across a data gap. The reporting reference is unconfirmed."
        )
    return rainfall_warning, river_warning


st.set_page_config(
    page_title="AI RESILIENCE | Disaster-risk prototype",
    page_icon=":material/shield:",
    layout="wide",
)


pages = {
    "Explore": [
        st.Page("app_pages/decision_workflow.py", title="Decision workflow", icon=":material/assignment_turned_in:"),
        st.Page("app_pages/kochi_map.py", title="Kochi map", icon=":material/map:"),
        st.Page("app_pages/air_pollution.py", title="Air pollution", icon=":material/factory:"),
        st.Page("app_pages/hospital_vulnerability.py", title="Hospital vulnerability", icon=":material/local_hospital:"),
        st.Page("app_pages/compound_scenario.py", title="Cyclone + flood", icon=":material/thunderstorm:"),
        st.Page("app_pages/disaster_probability.py", title="Disaster probability", icon=":material/monitor_heart:"),
    ],
    
    "Plan": [
        st.Page(
            "app_pages/mitigation_planner.py",
            title="Mitigation budget",
            icon=":material/account_balance_wallet:",
        ),
}

page = st.navigation(pages, position="top")

st.title("AI RESILIENCE")
st.caption("Disaster-risk assessment prototype | Exploratory use only")

rainfall_warning, river_warning = load_quality_summary()
st.warning(rainfall_warning, icon=":material/water_drop:")
st.warning(river_warning, icon=":material/water:")
st.info(
    "Prototype data and methods are not independently validated. This app does not "
    "issue warnings or replace official emergency guidance.",
    icon=":material/info:",
)

page.run()

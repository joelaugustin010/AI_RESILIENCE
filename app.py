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
        st.Page(
            "app_pages/decision_workflow.py",
            title="Decision Workflow",
            icon=":material/assignment_turned_in:",
        ),
        st.Page(
            "app_pages/disaster_assistant.py",
            title="Disaster Intelligence Assistant",
            icon=":material/psychology_alt:",
        ),
        st.Page(
            "app_pages/kochi_map.py",
            title="Kochi Map",
            icon=":material/map:",
        ),
        st.Page(
            "app_pages/air_pollution.py",
            title="Air Pollution",
            icon=":material/factory:",
        ),
        st.Page(
            "app_pages/data_readiness.py",
            title="Data Readiness",
            icon=":material/fact_check:",
        ),
        st.Page(
            "app_pages/hazard_model_lab.py",
            title="Hazard Model Lab",
            icon=":material/model_training:",
        ),
        st.Page(
            "app_pages/hospital_vulnerability.py",
            title="Hospital Vulnerability",
            icon=":material/local_hospital:",
        ),
        st.Page(
            "app_pages/compound_scenario.py",
            title="Cyclone + Flood",
            icon=":material/thunderstorm:",
        ),
        st.Page(
            "app_pages/disaster_probability.py",
            title="Disaster Probability",
            icon=":material/analytics:",
        ),
    ],
    "Plan": [
        st.Page(
            "app_pages/mitigation_planner.py",
            title="Mitigation Budget",
            icon=":material/account_balance_wallet:",
        ),
        st.Page(
            "app_pages/smart_mitigation_design.py",
            title="Smart Mitigation Design Studio",
            icon=":material/engineering:",
        ),
    ],
}

page = st.navigation(pages, position="top")

# A lightweight visual system shared by every page. Keep this CSS local to the
# Streamlit app so the deployment needs no external assets or build step.
st.markdown(
    """
    <style>
    :root {
      --ar-ink: #102a43;
      --ar-muted: #526579;
      --ar-teal: #087e8b;
      --ar-cyan: #22b8cf;
      --ar-border: #dce7ee;
      --ar-surface: #f4f8fb;
    }
    .stApp {
      background:
        radial-gradient(ellipse at 82% 0%, rgba(34,184,207,.10), transparent 34rem),
        linear-gradient(180deg, #f7fafc 0%, #ffffff 34rem);
    }
    .block-container { padding-top: 1.35rem; padding-bottom: 3rem; max-width: 1440px; }
    [data-testid="stHeader"] { background: rgba(247,250,252,.82); }
    [data-testid="stSidebar"] { border-right: 1px solid var(--ar-border); }
    h1, h2, h3 { color: var(--ar-ink); letter-spacing: -.025em; }
    h1 { font-weight: 800; }
    [data-testid="stMetric"] {
      background: #fff; border: 1px solid var(--ar-border);
      padding: 1rem 1.05rem; border-radius: 16px;
      box-shadow: 0 5px 18px rgba(16,42,67,.045);
    }
    [data-testid="stMetricLabel"] { color: var(--ar-muted); }
    [data-testid="stMetricValue"] { color: var(--ar-ink); font-weight: 750; }
    div[data-testid="stAlert"] { border-radius: 12px; }
    div.stButton > button, div.stDownloadButton > button {
      border-radius: 10px; font-weight: 650; min-height: 2.7rem;
    }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
      border: 1px solid var(--ar-border); border-radius: 12px; overflow: hidden;
    }
    .ar-hero {
      position: relative; overflow: hidden; border-radius: 24px;
      padding: clamp(1.5rem, 3vw, 2.6rem); margin: .25rem 0 1.25rem;
      color: #fff;
      background: linear-gradient(118deg, #102a43 0%, #075985 56%, #087e8b 100%);
      box-shadow: 0 18px 40px rgba(7,89,133,.18);
    }
    .ar-hero:after {
      content: ""; position: absolute; width: 310px; height: 310px;
      right: -95px; top: -155px; border-radius: 50%;
      border: 1px solid rgba(255,255,255,.20);
      box-shadow: 0 0 0 34px rgba(255,255,255,.045), 0 0 0 70px rgba(255,255,255,.035);
    }
    .ar-eyebrow {
      color: #9eeaf2; text-transform: uppercase; letter-spacing: .15em;
      font-size: .76rem; font-weight: 800; margin-bottom: .8rem;
    }
    .ar-hero h1 { color: white; font-size: clamp(2.1rem, 4vw, 3.35rem); line-height: 1.05; margin: 0 0 .8rem; }
    .ar-hero p { color: #e0f2fe; font-size: 1.04rem; max-width: 760px; line-height: 1.65; margin: 0; }
    .ar-chip {
      display: inline-block; margin-top: 1.25rem; margin-right: .4rem;
      border: 1px solid rgba(255,255,255,.28); background: rgba(255,255,255,.10);
      color: #fff; padding: .35rem .7rem; border-radius: 999px; font-size: .78rem;
    }
    .ar-section-label {
      color: var(--ar-teal); font-size: .76rem; text-transform: uppercase;
      letter-spacing: .12em; font-weight: 800; margin-bottom: .25rem;
    }
    @media (max-width: 640px) {
      .block-container { padding-left: 1rem; padding-right: 1rem; }
      .ar-hero { border-radius: 17px; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="ar-hero">
      <div class="ar-eyebrow">Kochi · Multi-hazard intelligence</div>
      <h1>AI RESILIENCE</h1>
      <p>Turn disaster evidence into clearer decisions. Explore hazard context, review data quality,
      compare preparedness scenarios and plan practical mitigation—without confusing assumptions
      with verified facts.</p>
      <span class="ar-chip">Evidence-first workflow</span>
      <span class="ar-chip">City resilience planning</span>
      <span class="ar-chip">SDG-aligned project</span>
    </section>
    """,
    unsafe_allow_html=True,
)

metric_a, metric_b, metric_c = st.columns(3)
with metric_a:
    st.metric("Project workspaces", "11", help="Explore and Plan sections in the application.")
with metric_b:
    st.metric("Official alerts issued", "0", help="This educational prototype does not issue official alerts.")
with metric_c:
    st.metric("Validated live predictions", "Not enabled", help="Numerical disaster predictions remain gated until data and models pass validation.")

st.markdown('<div class="ar-section-label">Current operating boundaries</div>', unsafe_allow_html=True)
st.caption("Designed for evidence review and preparedness planning—not emergency dispatch or official forecasting.")

with st.expander("Review data-quality notices", expanded=False):
    rainfall_warning, river_warning = load_quality_summary()
    st.warning(rainfall_warning, icon=":material/water_drop:")
    st.warning(river_warning, icon=":material/water:")
    st.info(
        "Prototype data and methods are not independently validated. This app does not "
        "issue warnings or replace official emergency guidance.",
        icon=":material/info:",
    )

page.run()

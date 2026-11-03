"""AI RESILIENCE prototype entry point and shared navigation."""

import streamlit as st


st.set_page_config(
    page_title="AI RESILIENCE | Disaster-risk prototype",
    page_icon=":material/shield:",
    layout="wide",
)

pages = {
    "Home": [
        st.Page(
            "app_pages/home.py",
            title="Command Centre",
            icon=":material/dashboard:",
        ),
    ],
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
    <div style="display:flex;align-items:center;gap:.55rem;margin:.1rem 0 1rem;color:#526579;font-size:.82rem">
      <span style="display:inline-block;width:.55rem;height:.55rem;border-radius:50%;background:#087e8b"></span>
      <span><strong style="color:#102a43">AI RESILIENCE</strong> · Kochi multi-hazard planning workspace</span>
    </div>
    """,
    unsafe_allow_html=True,
)

page.run()

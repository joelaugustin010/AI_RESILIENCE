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
      color-scheme: dark;
      --ar-bg: #061522;
      --ar-bg-2: #0a2030;
      --ar-panel: rgba(12, 35, 51, .88);
      --ar-panel-strong: #102b3c;
      --ar-ink: #e7f5f5;
      --ar-muted: #a7c1c8;
      --ar-teal: #42e0c1;
      --ar-cyan: #56c8e8;
      --ar-lime: #b4e66b;
      --ar-border: rgba(130, 190, 199, .22);
      --ar-shadow: 0 18px 48px rgba(0, 0, 0, .22);
    }
    html, body, [data-testid="stAppViewContainer"] { background: #061522 !important; }
    .stApp {
      color: var(--ar-ink) !important;
      background:
        radial-gradient(ellipse at 8% 4%, rgba(28, 190, 169, .19), transparent 31rem),
        radial-gradient(ellipse at 92% 12%, rgba(47, 137, 190, .17), transparent 34rem),
        radial-gradient(ellipse at 52% 100%, rgba(34, 116, 115, .11), transparent 38rem),
        repeating-radial-gradient(ellipse at 85% 18%, transparent 0 34px, rgba(126, 208, 202, .035) 35px 36px, transparent 37px 72px),
        linear-gradient(145deg, #061522 0%, #0a2030 48%, #071925 100%) !important;
      background-attachment: fixed !important;
    }
    .block-container { padding-top: 1.45rem; padding-bottom: 3.5rem; max-width: 1500px; }
    [data-testid="stHeader"], [data-testid="stToolbar"] { background: rgba(6, 21, 34, .76) !important; }
    [data-testid="stSidebar"] { background: rgba(7, 25, 39, .96) !important; border-right: 1px solid var(--ar-border); }
    [data-testid="stSidebar"] * { color: var(--ar-ink); }
    [data-testid="stAppViewContainer"] > .main { background: transparent !important; }
    [data-testid="stMain"] { background: transparent !important; }
    h1, h2, h3, h4, h5, h6 { color: #effafa; letter-spacing: -.025em; }
    p, li, label, .stMarkdown, .stCaption, [data-testid="stWidgetLabel"] { color: #c5dadd; }
    [data-testid="stMetric"] {
      background: linear-gradient(145deg, rgba(17, 48, 66, .96), rgba(10, 34, 49, .96)) !important;
      border: 1px solid var(--ar-border) !important;
      padding: 1rem 1.05rem; border-radius: 17px;
      box-shadow: var(--ar-shadow);
    }
    [data-testid="stMetricLabel"] { color: #9fc0c8 !important; }
    [data-testid="stMetricValue"] { color: #f0ffff !important; font-weight: 780; }
    [data-testid="stMetricDelta"] { color: var(--ar-teal) !important; }
    div[data-testid="stAlert"] { border-radius: 14px; border: 1px solid var(--ar-border); }
    [data-testid="stExpander"], [data-testid="stVerticalBlockBorderWrapper"] > div {
      border-color: var(--ar-border) !important;
    }
    [data-testid="stExpander"] { background: rgba(12, 35, 51, .72) !important; border-radius: 15px; }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary p { color: #e5f4f4 !important; }
    [data-baseweb="select"] > div, [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div, [data-testid="stDateInput"] input,
    [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
      background: #102b3c !important; color: #eaf7f7 !important;
      border-color: rgba(130, 190, 199, .34) !important; border-radius: 11px !important;
    }
    [data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"] {
      background: #102b3c !important; color: #eaf7f7 !important;
    }
    [data-baseweb="menu"] *, [role="option"] { color: #eaf7f7 !important; }
    [data-testid="stRadio"] label, [data-testid="stCheckbox"] label { color: #d5e7e8 !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
      border: 1px solid var(--ar-border); border-radius: 13px; overflow: hidden;
      background: rgba(12, 35, 51, .8);
    }
    [data-testid="stTabs"] button { color: #a9c9ce !important; }
    [data-testid="stTabs"] button[aria-selected="true"] { color: #58e1c5 !important; border-bottom-color: #42e0c1 !important; }
    div.stButton > button, div.stDownloadButton > button {
      border-radius: 11px; font-weight: 700; min-height: 2.7rem;
      border: 1px solid rgba(91, 223, 200, .42);
      background: linear-gradient(110deg, #126a70, #147c83);
      color: #f4ffff !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
      border-color: #7bf0d7; background: linear-gradient(110deg, #16817e, #168b91);
      color: #fff !important;
    }
    hr { border-color: rgba(130, 190, 199, .22) !important; }
    a { color: #62dfd0 !important; }
    .ar-hero {
      position: relative; overflow: hidden; border-radius: 25px;
      padding: clamp(1.5rem, 3vw, 2.6rem); margin: .25rem 0 1.25rem;
      color: #fff; background: linear-gradient(118deg, #092032 0%, #07516a 55%, #087e78 100%);
      border: 1px solid rgba(120, 220, 208, .25); box-shadow: 0 22px 54px rgba(0,0,0,.26);
    }
    .ar-hero:after {
      content: ""; position: absolute; width: 310px; height: 310px; right: -95px; top: -155px;
      border-radius: 50%; border: 1px solid rgba(255,255,255,.22);
      box-shadow: 0 0 0 34px rgba(255,255,255,.045), 0 0 0 70px rgba(255,255,255,.035);
    }
    .ar-eyebrow { color: #8cf3df; text-transform: uppercase; letter-spacing: .15em; font-size: .76rem; font-weight: 800; margin-bottom: .8rem; }
    .ar-hero h1 { color: white; font-size: clamp(2.1rem, 4vw, 3.35rem); line-height: 1.05; margin: 0 0 .8rem; }
    .ar-hero p { color: #d9f3f1; font-size: 1.04rem; max-width: 760px; line-height: 1.65; margin: 0; }
    .ar-chip { display: inline-block; margin-top: 1.25rem; margin-right: .4rem; border: 1px solid rgba(255,255,255,.28); background: rgba(255,255,255,.10); color: #fff; padding: .35rem .7rem; border-radius: 999px; font-size: .78rem; }
    .ar-section-label { color: #55e1ca; font-size: .76rem; text-transform: uppercase; letter-spacing: .12em; font-weight: 800; margin-bottom: .25rem; }
    @media (max-width: 640px) { .block-container { padding-left: 1rem; padding-right: 1rem; } .ar-hero { border-radius: 18px; } }
    @media (prefers-reduced-motion: reduce) { *, *:before, *:after { scroll-behavior: auto !important; transition-duration: .01ms !important; } }

    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="display:flex;align-items:center;gap:.55rem;margin:.1rem 0 1rem;color:#a7c1c8;font-size:.82rem">
      <span style="display:inline-block;width:.55rem;height:.55rem;border-radius:50%;background:#42e0c1;box-shadow:0 0 12px #42e0c1"></span>
      <span><strong style="color:#e7f5f5">AI RESILIENCE</strong> · Kochi multi-hazard planning workspace</span>
    </div>
    """,
    unsafe_allow_html=True,
)

page.run()

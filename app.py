"""AI RESILIENCE prototype entry point and shared navigation."""

from __future__ import annotations

import html

import streamlit as st


st.set_page_config(
    page_title="AI RESILIENCE | Kochi environmental & disaster intelligence",
    page_icon=":material/shield:",
    layout="wide",
)

# Open directly on the Kochi-focused project dashboard.
pages = {
    "Home": [
        st.Page(
            "app_pages/home.py",
            title="Home",
            icon=":material/home:",
            default=True,
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
            title="Kochi Multi-Hazard Review",
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

# A lightweight, application-wide design system. Keeping it local means the
# deployment needs no external asset or build step, and every analytical page
# inherits the same typography, surfaces, colour semantics and motion.
st.markdown(
    """
    <style>
    :root {
      --ar-bg: #06131f;
      --ar-bg-deep: #040e17;
      --ar-panel: #0b2434;
      --ar-panel-2: #0e2b3c;
      --ar-panel-3: #123447;
      --ar-ink: #eef8f8;
      --ar-ink-soft: #d3e6e8;
      --ar-muted: #a5c0c7;
      --ar-faint: #7f9ba3;
      --ar-teal: #42e0c1;
      --ar-teal-soft: #8cf3df;
      --ar-cyan: #5cc8e8;
      --ar-emerald: #4ade80;
      --ar-amber: #f0c56a;
      --ar-orange: #fb923c;
      --ar-red: #f87171;
      --ar-violet: #b39bff;
      --ar-border: rgba(130, 190, 199, .22);
      --ar-border-strong: rgba(130, 190, 199, .42);
      --ar-shadow: 0 22px 55px rgba(0, 0, 0, .30);
      --ar-shadow-soft: 0 12px 32px rgba(0, 0, 0, .18);
      --ar-ease: cubic-bezier(.2, .7, .2, 1);
      --ar-accent: var(--ar-teal);
      --ar-radius: 18px;
    }

    html { scroll-behavior: smooth; }
    html, body, [data-testid="stAppViewContainer"] { background: var(--ar-bg) !important; }
    html, body, [class*="css"] {
      font-family: "SF Pro Text", "SF Pro Display", -apple-system, BlinkMacSystemFont,
                   "Segoe UI", Inter, Roboto, "Helvetica Neue", sans-serif;
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
    }
    .stApp {
      color: var(--ar-ink) !important;
      background:
        radial-gradient(ellipse at 7% 2%, rgba(28, 190, 169, .16), transparent 30rem),
        radial-gradient(ellipse at 94% 8%, rgba(47, 137, 190, .14), transparent 34rem),
        radial-gradient(ellipse at 52% 100%, rgba(34, 116, 115, .10), transparent 40rem),
        repeating-radial-gradient(ellipse at 85% 18%, transparent 0 34px, rgba(126, 208, 202, .028) 35px 36px, transparent 37px 72px),
        linear-gradient(145deg, #06131f 0%, #0a2030 48%, #071925 100%) !important;
      background-attachment: fixed !important;
    }
    .block-container {
      padding-top: 1.3rem;
      padding-bottom: 3.2rem;
      max-width: 1500px;
    }
    [data-testid="stDecoration"] {
      background: linear-gradient(90deg, transparent, rgba(66, 224, 193, .7), transparent) !important;
      height: 2px;
    }

    /* ---------- Motion language ---------- */
    @keyframes arPageIn {
      from { opacity: 0; transform: translateY(7px); }
      to   { opacity: 1; transform: none; }
    }
    @keyframes arRiseIn {
      from { opacity: 0; transform: translateY(12px); }
      to   { opacity: 1; transform: none; }
    }
    @keyframes arMenuIn {
      from { opacity: 0; transform: translateY(-4px) scale(.995); }
      to   { opacity: 1; transform: none; }
    }
    @keyframes arSoftPulse {
      0%, 100% { opacity: .58; }
      50% { opacity: 1; }
    }
    [data-testid="stMainBlockContainer"], .block-container {
      animation: arPageIn .42s var(--ar-ease) both;
    }
    [data-testid="stMetric"], [data-testid="stVerticalBlockBorderWrapper"] {
      animation: arRiseIn .34s var(--ar-ease) both;
    }

    /* ---------- Navigation ---------- */
    [data-testid="stHeader"], [data-testid="stToolbar"] {
      background: rgba(6, 19, 31, .76) !important;
      backdrop-filter: blur(16px);
    }
    [data-testid="stTopNav"] {
      background: transparent !important;
      border-bottom: 1px solid rgba(130, 190, 199, .10);
    }
    [data-testid="stTopNavSection"],
    [data-testid="stTopNavLink"] {
      border-radius: 999px !important;
      padding: .34rem .78rem !important;
      color: #f0ffff !important;
      font-weight: 780 !important;
      text-shadow: 0 1px 12px rgba(0, 0, 0, .38);
      background: transparent !important;
      transition: background .2s var(--ar-ease), color .2s var(--ar-ease),
                  transform .2s var(--ar-ease), box-shadow .2s var(--ar-ease);
    }
    [data-testid="stTopNavSection"] p,
    [data-testid="stTopNavLink"] p,
    [data-testid="stTopNavSection"] span,
    [data-testid="stTopNavLink"] span { color: inherit !important; }
    [data-testid="stTopNavSection"]:hover,
    [data-testid="stTopNavLink"]:hover {
      background: rgba(66, 224, 193, .10) !important;
      color: #efffff !important;
      transform: translateY(-1px);
    }
    [data-testid="stTopNavSection"][aria-expanded="true"],
    [data-testid="stTopNavLink"][aria-current="page"],
    [data-testid="stTopNavLink"][data-active="true"] {
      background: rgba(66, 224, 193, .15) !important;
      color: #b8fff1 !important;
      box-shadow: inset 0 0 0 1px rgba(66, 224, 193, .22);
    }
    [data-testid="stTopNavPopover"], [data-testid="stTopNavPopoverBody"] {
      background: #0b2233 !important;
      border: 1px solid var(--ar-border) !important;
      border-radius: 16px !important;
      box-shadow: var(--ar-shadow);
      animation: arMenuIn .18s var(--ar-ease) both;
    }
    [data-testid="stTopNavDropdownLink"] {
      border-radius: 10px;
      color: #efffff !important;
      font-weight: 650 !important;
      transition: background .16s var(--ar-ease), color .16s var(--ar-ease), padding-left .16s var(--ar-ease);
    }
    [data-testid="stTopNavDropdownLink"] p,
    [data-testid="stTopNavDropdownLink"] span { color: inherit !important; }
    [data-testid="stTopNavDropdownLink"] [data-testid="stIconMaterial"] {
      color: #b9e6e7 !important;
      transition: color .16s var(--ar-ease);
    }
    [data-testid="stTopNavDropdownLink"]:hover {
      background: rgba(66, 224, 193, .11) !important;
      color: #b8fff1 !important;
      padding-left: .35rem !important;
    }
    [data-testid="stTopNavDropdownLink"]:hover [data-testid="stIconMaterial"] {
      color: #9cf8e6 !important;
    }

    [data-testid="stSidebar"] {
      background: rgba(7, 23, 36, .98) !important;
      border-right: 1px solid var(--ar-border);
    }
    [data-testid="stSidebar"] * { color: var(--ar-ink); }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: var(--ar-muted) !important; }
    [data-testid="stSidebarNavLink"] {
      border-radius: 10px;
      transition: background .16s var(--ar-ease), color .16s var(--ar-ease);
    }
    [data-testid="stSidebarNavLink"]:hover { background: rgba(66, 224, 193, .08); }
    [data-testid="stAppViewContainer"] > .main, [data-testid="stMain"] { background: transparent !important; }

    /* ---------- Typography ---------- */
    h1, h2, h3, h4, h5, h6 {
      color: #f1fbfb !important;
      letter-spacing: -.028em;
      text-wrap: balance;
    }
    h2 { line-height: 1.22; }
    h3 { line-height: 1.3; }
    p, li, label, .stMarkdown, .stCaption, [data-testid="stWidgetLabel"] { color: #c5dadd; }
    [data-testid="stCaptionContainer"], .stCaption { color: #94b0b8 !important; }
    a { color: #62dfd0 !important; text-underline-offset: 2px; }
    a:hover { color: #9cf8e6 !important; }
    hr { border-color: rgba(130, 190, 199, .18) !important; margin: 1.5rem 0; }
    strong { color: #f0fbfb; }
    code {
      color: #b7f7ea !important;
      background: rgba(66, 224, 193, .08) !important;
      border: 1px solid rgba(66, 224, 193, .14);
      border-radius: 6px;
      padding: .08rem .3rem;
    }

    /* ---------- Standard module header ---------- */
    [class*="st-key-ar-head-"] {
      position: relative;
      overflow: hidden;
      margin: .1rem 0 1.15rem;
      padding: clamp(1.3rem, 2.8vw, 2.15rem) clamp(1.35rem, 3vw, 2.5rem);
      border: 1px solid var(--ar-border);
      border-radius: 26px;
      background:
        linear-gradient(90deg, rgba(4, 18, 28, .95) 0%, rgba(7, 35, 47, .76) 58%, rgba(7, 34, 43, .86) 100%),
        radial-gradient(ellipse at 90% -10%, color-mix(in srgb, var(--ar-accent) 22%, transparent), transparent 24rem),
        radial-gradient(ellipse at 8% 120%, rgba(20, 90, 110, .28), transparent 26rem),
        var(--ar-hero-image) center / cover no-repeat,
        linear-gradient(120deg, #071c2b 0%, #0a2c3e 56%, #0b3a45 100%);
      box-shadow: var(--ar-shadow);
      isolation: isolate;
    }
    [class*="st-key-ar-head-"]:before {
      content: "";
      position: absolute;
      z-index: -1;
      width: 290px;
      height: 290px;
      right: -110px;
      top: -165px;
      border-radius: 50%;
      border: 1px solid color-mix(in srgb, var(--ar-accent) 34%, transparent);
      box-shadow: 0 0 0 28px color-mix(in srgb, var(--ar-accent) 5%, transparent),
                  0 0 0 58px color-mix(in srgb, var(--ar-accent) 3%, transparent);
      pointer-events: none;
    }
    [class*="st-key-ar-head-"]:after {
      content: "";
      position: absolute;
      inset: 0 auto auto 0;
      width: 100%;
      height: 3px;
      background: linear-gradient(90deg, var(--ar-accent), transparent 60%);
      opacity: .85;
    }
    [class*="st-key-ar-head-"] [data-testid="stVerticalBlock"] { gap: .38rem; }
    [class*="st-key-ar-head-"] [data-testid="stHeading"] { margin: 0 !important; }
    [class*="st-key-ar-head-"] h1 {
      margin: .1rem 0 .45rem !important;
      padding: 0 !important;
      color: #f6ffff !important;
      font-size: clamp(2.05rem, 4vw, 3.25rem) !important;
      font-weight: 820 !important;
      line-height: 1.02 !important;
      letter-spacing: -.045em !important;
    }
    .ar-page-kicker {
      display: inline-flex;
      align-items: center;
      gap: .55rem;
      color: color-mix(in srgb, var(--ar-accent) 76%, white);
      font-size: .71rem;
      font-weight: 800;
      letter-spacing: .16em;
      text-transform: uppercase;
    }
    .ar-page-dot {
      width: .5rem;
      height: .5rem;
      border-radius: 50%;
      background: var(--ar-accent);
      box-shadow: 0 0 0 4px color-mix(in srgb, var(--ar-accent) 16%, transparent);
      animation: arSoftPulse 2.8s ease-in-out infinite;
    }
    .ar-page-title {
      color: #f6ffff;
      font-size: clamp(2.05rem, 4vw, 3.25rem);
      font-weight: 820;
      line-height: 1.02;
      letter-spacing: -.045em;
      margin: .1rem 0 .45rem;
    }
    .ar-page-copy {
      max-width: 940px;
      margin: 0 !important;
      color: #c8dfe2 !important;
      font-size: clamp(.95rem, 1.15vw, 1.04rem) !important;
      line-height: 1.68 !important;
    }
    .ar-page-meta {
      display: flex;
      flex-wrap: wrap;
      gap: .42rem;
      margin-top: .65rem;
    }
    .ar-page-meta span {
      display: inline-flex;
      align-items: center;
      min-height: 1.7rem;
      padding: .22rem .62rem;
      border: 1px solid rgba(130, 190, 199, .24);
      border-radius: 999px;
      background: rgba(6, 23, 35, .38);
      color: #c8e4e5;
      font-size: .7rem;
      font-weight: 650;
      letter-spacing: .035em;
      text-transform: uppercase;
      backdrop-filter: blur(6px);
    }

    /* Keep module photography available even when Streamlit hot-reloads an
       older copy of src.ui_theme before the next full deployment restart. */
    .st-key-ar-head-air-quality,
    .st-key-ar-head-disaster-probability,
    .st-key-ar-head-data-readiness,
    .st-key-ar-head-hazard-model-lab,
    .st-key-ar-head-hospital-vulnerability,
    .st-key-ar-head-kochi-map,
    .st-key-ar-head-mitigation-budget,
    .st-key-ar-head-smart-mitigation,
    .st-key-ar-head-compound-scenario,
    .st-key-ar-head-disaster-assistant { --ar-hero-image: none; }
    .st-key-ar-head-air-quality { --ar-hero-image: url('app/static/images/threats-monsoon.webp'); }
    .st-key-ar-head-disaster-probability { --ar-hero-image: url('app/static/images/hero-kerala-fallback.jpg'); }
    .st-key-ar-head-data-readiness,
    .st-key-ar-head-hazard-model-lab,
    .st-key-ar-head-hospital-vulnerability,
    .st-key-ar-head-kochi-map { --ar-hero-image: url('app/static/images/beauty-city.webp'); }
    .st-key-ar-head-mitigation-budget,
    .st-key-ar-head-smart-mitigation { --ar-hero-image: url('app/static/images/hero-kerala-flood-road.jpg'); }
    .st-key-ar-head-compound-scenario { --ar-hero-image: url('app/static/images/hero-kerala-coast.jpg'); }
    .st-key-ar-head-disaster-assistant { --ar-hero-image: url('app/static/images/hero-kerala-ghats.jpg'); }

    /* ---------- Section rhythm ---------- */
    .ar-sec-intro { margin: 1.5rem 0 .6rem; }
    .ar-sec-overline {
      display: inline-block;
      color: var(--ar-teal-soft);
      font-size: .68rem;
      font-weight: 800;
      letter-spacing: .16em;
      text-transform: uppercase;
    }
    .ar-sec-intro h2 {
      margin: .25rem 0 .35rem;
      font-size: clamp(1.35rem, 2.2vw, 1.85rem);
      line-height: 1.18;
    }
    .ar-sec-intro p { max-width: 860px; color: var(--ar-muted); line-height: 1.6; margin: 0; }

    /* ---------- Cards, metrics and layered panels ---------- */
    [data-testid="stVerticalBlockBorderWrapper"] {
      position: relative;
      border: 1px solid var(--ar-border) !important;
      border-radius: var(--ar-radius) !important;
      background:
        radial-gradient(ellipse at 100% 0%, rgba(66, 224, 193, .055), transparent 18rem),
        linear-gradient(150deg, rgba(17, 48, 66, .95), rgba(9, 31, 46, .95)) !important;
      box-shadow: var(--ar-shadow-soft);
      padding: .15rem;
      transition: border-color .22s var(--ar-ease), box-shadow .22s var(--ar-ease),
                  background .22s var(--ar-ease);
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
      border-color: rgba(91, 223, 200, .34) !important;
      box-shadow: 0 20px 44px rgba(0, 0, 0, .26);
    }
    [data-testid="stMetric"] {
      position: relative;
      overflow: hidden;
      background:
        radial-gradient(ellipse at 100% 0%, rgba(66, 224, 193, .07), transparent 12rem),
        linear-gradient(145deg, rgba(17, 48, 66, .97), rgba(10, 34, 49, .97)) !important;
      border: 1px solid var(--ar-border) !important;
      padding: 1rem 1.08rem !important;
      border-radius: 17px !important;
      box-shadow: 0 16px 42px rgba(0, 0, 0, .22);
      transition: transform .22s var(--ar-ease), box-shadow .22s var(--ar-ease),
                  border-color .22s var(--ar-ease);
    }
    [data-testid="stMetric"]:before {
      content: "";
      position: absolute;
      inset: 0 auto auto 0;
      width: 100%;
      height: 2px;
      background: linear-gradient(90deg, var(--ar-teal), transparent 72%);
      opacity: .55;
    }
    [data-testid="stMetric"]:hover {
      transform: translateY(-2px);
      border-color: rgba(91, 223, 200, .42) !important;
      box-shadow: 0 24px 56px rgba(0, 0, 0, .32);
    }
    [data-testid="stMetricLabel"] { color: #a4c4ca !important; font-weight: 600; }
    [data-testid="stMetricLabel"] p { color: inherit !important; }
    [data-testid="stMetricValue"] {
      color: #f4ffff !important;
      font-weight: 780;
      font-variant-numeric: tabular-nums;
      letter-spacing: -.025em;
      transition: color .2s var(--ar-ease);
    }
    [data-testid="stMetricDelta"] { color: var(--ar-teal) !important; font-weight: 650; }

    /* ---------- Expanders ---------- */
    [data-testid="stExpander"] {
      background: linear-gradient(150deg, rgba(12, 35, 51, .85), rgba(9, 28, 42, .85)) !important;
      border: 1px solid var(--ar-border) !important;
      border-radius: 15px !important;
      transition: border-color .2s var(--ar-ease), background .2s var(--ar-ease),
                  box-shadow .2s var(--ar-ease);
    }
    [data-testid="stExpander"]:hover {
      border-color: var(--ar-border-strong) !important;
      box-shadow: var(--ar-shadow-soft);
    }
    [data-testid="stExpander"] summary, [data-testid="stExpander"] summary p { color: #e5f4f4 !important; }
    [data-testid="stExpander"] summary {
      padding: .55rem .2rem;
      transition: color .16s var(--ar-ease);
    }
    [data-testid="stExpander"] summary:hover { color: var(--ar-teal) !important; }
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] { animation: arRiseIn .25s var(--ar-ease) both; }

    /* ---------- Inputs, selectors and menus ---------- */
    [data-baseweb="select"] > div,
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-testid="stDateInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {
      background: #0f2b3c !important;
      color: #eaf7f7 !important;
      border-color: rgba(130, 190, 199, .30) !important;
      border-radius: 11px !important;
      transition: border-color .2s var(--ar-ease), box-shadow .2s var(--ar-ease), background .2s var(--ar-ease);
    }
    [data-baseweb="select"] > div:hover,
    [data-baseweb="input"] > div:hover,
    [data-baseweb="textarea"] > div:hover {
      border-color: rgba(130, 190, 199, .52) !important;
      background: #113144 !important;
    }
    [data-baseweb="select"] > div:focus-within,
    [data-baseweb="input"] > div:focus-within,
    [data-baseweb="textarea"] > div:focus-within {
      border-color: rgba(66, 224, 193, .78) !important;
      box-shadow: 0 0 0 3px rgba(66, 224, 193, .14);
    }
    [data-baseweb="select"] span, [data-baseweb="select"] div { color: #eaf7f7; }
    [data-baseweb="select"] [data-testid="stSelectboxVirtualDropdown"] { color: #a9c6cc; }
    [data-baseweb="popover"] {
      background: #0d293a !important;
      border: 1px solid var(--ar-border) !important;
      border-radius: 13px !important;
      box-shadow: var(--ar-shadow);
      animation: arMenuIn .17s var(--ar-ease) both;
      overflow: hidden;
    }
    [data-baseweb="menu"], [role="listbox"] {
      background: #0d293a !important;
      color: #eaf7f7 !important;
    }
    [data-baseweb="menu"] *, [role="option"] { color: #eaf7f7 !important; }
    [role="option"] {
      border-radius: 8px;
      margin: 2px 5px;
      transition: background .14s var(--ar-ease), padding-left .14s var(--ar-ease);
    }
    [role="option"]:hover { background: rgba(66, 224, 193, .10) !important; padding-left: .35rem !important; }
    [role="option"][aria-selected="true"] {
      background: rgba(66, 224, 193, .17) !important;
      color: #a8f9e8 !important;
      box-shadow: inset 2px 0 0 var(--ar-teal);
    }
    [data-testid="stMultiSelect"] [data-baseweb="tag"] {
      background: rgba(66, 224, 193, .16) !important;
      border: 1px solid rgba(66, 224, 193, .28);
      color: #d8fff7 !important;
      border-radius: 7px;
    }
    [data-testid="stRadio"] [role="radiogroup"] {
      gap: .45rem;
      flex-wrap: wrap;
      align-items: center;
    }
    [data-testid="stRadio"] label {
      border: 1px solid rgba(130, 190, 199, .22);
      border-radius: 999px;
      padding: .38rem .82rem;
      background: rgba(12, 38, 54, .55);
      color: #d5e7e8 !important;
      transition: border-color .18s var(--ar-ease), background .18s var(--ar-ease),
                  color .18s var(--ar-ease), box-shadow .18s var(--ar-ease);
    }
    [data-testid="stRadio"] label:hover {
      border-color: rgba(66, 224, 193, .42);
      background: rgba(66, 224, 193, .07);
    }
    [data-testid="stRadio"] label:has(input:checked) {
      border-color: rgba(66, 224, 193, .66);
      background: rgba(66, 224, 193, .14);
      color: #ecfffb !important;
      box-shadow: 0 0 0 3px rgba(66, 224, 193, .10);
    }
    [data-testid="stCheckbox"] label { color: #d5e7e8 !important; }
    [data-testid="stSlider"] [role="slider"] {
      transition: box-shadow .18s var(--ar-ease), transform .18s var(--ar-ease);
    }
    [data-testid="stSlider"] [role="slider"]:hover {
      box-shadow: 0 0 0 5px rgba(66, 224, 193, .16);
      transform: scale(1.05);
    }

    /* ---------- Data and charts ---------- */
    [data-testid="stDataFrame"], [data-testid="stTable"] {
      border: 1px solid var(--ar-border);
      border-radius: 14px;
      overflow: hidden;
      background: rgba(12, 35, 51, .8);
      box-shadow: var(--ar-shadow-soft);
    }
    [data-testid="stDataFrame"] [role="columnheader"] { color: #cfe8e9 !important; }
    [data-testid="stPlotlyChart"], [data-testid="stAltairChart"], [data-testid="stVegaLiteChart"] {
      border: 1px solid var(--ar-border);
      border-radius: 16px;
      padding: .45rem .5rem;
      background: linear-gradient(150deg, rgba(13, 39, 56, .72), rgba(8, 27, 41, .55));
      box-shadow: var(--ar-shadow-soft);
    }
    [data-testid="stPlotlyChart"] .modebar { opacity: .35; transition: opacity .2s var(--ar-ease); }
    [data-testid="stPlotlyChart"]:hover .modebar { opacity: 1; }
    [data-testid="stDeckGlJsonChart"] {
      border: 1px solid var(--ar-border);
      border-radius: 16px;
      overflow: hidden;
      box-shadow: var(--ar-shadow-soft);
    }

    /* ---------- Tabs ---------- */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
      gap: .3rem;
      padding: .32rem;
      border: 1px solid var(--ar-border);
      border-radius: 13px;
      background: rgba(8, 27, 41, .62);
      width: fit-content;
      max-width: 100%;
      overflow-x: auto;
    }
    [data-testid="stTabs"] button {
      border-radius: 9px !important;
      padding: .42rem .9rem !important;
      color: #a9c9ce !important;
      background: transparent !important;
      transition: color .18s var(--ar-ease), background .18s var(--ar-ease),
                  box-shadow .18s var(--ar-ease);
    }
    [data-testid="stTabs"] button:hover { color: #dffbf7 !important; background: rgba(66, 224, 193, .07) !important; }
    [data-testid="stTabs"] button[aria-selected="true"] {
      color: #062421 !important;
      background: linear-gradient(110deg, #9af4e2, #42e0c1) !important;
      box-shadow: 0 6px 18px rgba(66, 224, 193, .18);
    }
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] { display: none; }
    [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }
    [data-testid="stTabs"] [role="tabpanel"] { animation: arRiseIn .28s var(--ar-ease) both; padding-top: .75rem; }

    /* ---------- Buttons and links ---------- */
    div.stButton > button, div.stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
      border-radius: 11px;
      font-weight: 700;
      min-height: 2.65rem;
      border: 1px solid rgba(91, 223, 200, .38);
      background: linear-gradient(110deg, #11616a, #14747d);
      color: #f4ffff !important;
      transition: transform .18s var(--ar-ease), box-shadow .18s var(--ar-ease),
                  border-color .18s var(--ar-ease), background .18s var(--ar-ease);
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
      border-color: #7bf0d7;
      background: linear-gradient(110deg, #147a78, #168b91);
      color: #fff !important;
      transform: translateY(-1px);
      box-shadow: 0 12px 28px rgba(0, 0, 0, .26);
    }
    div.stButton > button:active, div.stDownloadButton > button:active,
    [data-testid="stFormSubmitButton"] > button:active {
      transform: translateY(0) scale(.995);
    }
    div.stButton > button[kind="primary"],
    button[data-testid="stBaseButton-primary"],
    [data-testid="stFormSubmitButton"] > button[kind="primary"] {
      background: linear-gradient(110deg, #16a596, #42e0c1) !important;
      color: #041a1c !important;
      border-color: transparent !important;
      box-shadow: 0 10px 26px rgba(66, 224, 193, .16);
    }
    div.stButton > button[kind="primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover,
    [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
      background: linear-gradient(110deg, #1ab8a7, #65efd4) !important;
      color: #041a1c !important;
      box-shadow: 0 16px 34px rgba(66, 224, 193, .22);
    }
    div.stButton > button[kind="secondary"],
    button[data-testid="stBaseButton-secondary"] {
      background: rgba(13, 39, 56, .82) !important;
      color: #e8fbf8 !important;
      border-color: rgba(130, 190, 199, .34) !important;
    }
    [data-testid="stPageLink"] a {
      border-radius: 10px;
      padding: .45rem .6rem;
      transition: background .18s var(--ar-ease), color .18s var(--ar-ease),
                  transform .18s var(--ar-ease), padding-left .18s var(--ar-ease);
    }
    [data-testid="stPageLink"] a:hover {
      background: rgba(66, 224, 193, .08);
      color: #9cf8e6 !important;
      transform: translateX(2px);
      padding-left: .72rem;
    }

    /* ---------- Focus and alerts ---------- */
    [data-testid="stTopNavSection"]:focus-visible,
    [data-testid="stTopNavLink"]:focus-visible,
    [data-testid="stTopNavDropdownLink"]:focus-visible,
    [data-testid="stPageLink"] a:focus-visible,
    div.stButton > button:focus-visible,
    div.stDownloadButton > button:focus-visible,
    input:focus-visible, textarea:focus-visible, select:focus-visible {
      outline: 2px solid #42e0c1 !important;
      outline-offset: 2px;
    }
    div[data-testid="stAlert"] {
      border-radius: 13px;
      border: 1px solid var(--ar-border);
      background: rgba(13, 42, 61, .86);
      box-shadow: var(--ar-shadow-soft);
    }
    div[data-testid="stAlert"] p { color: #dceff0 !important; }
    div[data-testid="stAlert"]:has([data-testid="stAlertContentWarning"]) {
      border-left: 3px solid var(--ar-amber);
    }
    div[data-testid="stAlert"]:has([data-testid="stAlertContentError"]) {
      border-left: 3px solid var(--ar-red);
    }
    div[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) {
      border-left: 3px solid var(--ar-emerald);
    }
    div[data-testid="stAlert"]:has([data-testid="stAlertContentInfo"]) {
      border-left: 3px solid var(--ar-cyan);
    }

    /* ---------- Loading ---------- */
    [data-testid="stSpinner"] { color: var(--ar-teal) !important; }
    [data-testid="stSpinner"] svg { animation-duration: 1.1s; }
    [data-testid="stStatusWidget"] { animation: arSoftPulse 1.8s ease-in-out infinite; }
    [data-testid="stProgress"] { background: rgba(130, 190, 199, .12); border-radius: 999px; }
    [data-testid="stProgress"] > div > div {
      background: linear-gradient(90deg, var(--ar-teal), var(--ar-cyan));
      border-radius: 999px;
      transition: width .5s var(--ar-ease);
    }

    /* ---------- Risk colour language ---------- */
    .ar-risk {
      display: inline-flex;
      align-items: center;
      gap: .35rem;
      padding: .22rem .6rem;
      border-radius: 999px;
      font-size: .72rem;
      font-weight: 700;
      letter-spacing: .02em;
      border: 1px solid transparent;
    }
    .ar-risk-safe { color: #baf7d0; background: rgba(74, 222, 128, .12); border-color: rgba(74, 222, 128, .30); }
    .ar-risk-moderate { color: #ffe3a3; background: rgba(240, 197, 106, .12); border-color: rgba(240, 197, 106, .30); }
    .ar-risk-high { color: #ffc6a3; background: rgba(251, 146, 60, .12); border-color: rgba(251, 146, 60, .32); }
    .ar-risk-critical { color: #ffb4b4; background: rgba(248, 113, 113, .12); border-color: rgba(248, 113, 113, .34); }

    /* ---------- Legacy shared classes ---------- */
    .ar-hero {
      position: relative;
      overflow: hidden;
      border-radius: 25px;
      padding: clamp(1.5rem, 3vw, 2.6rem);
      margin: .25rem 0 1.25rem;
      color: #fff;
      background: linear-gradient(118deg, #092032 0%, #07516a 55%, #087e78 100%);
      border: 1px solid rgba(120, 220, 208, .25);
      box-shadow: var(--ar-shadow);
    }
    .ar-eyebrow {
      color: #8cf3df;
      text-transform: uppercase;
      letter-spacing: .15em;
      font-size: .76rem;
      font-weight: 800;
      margin-bottom: .8rem;
    }
    .ar-hero h1 { color: white; font-size: clamp(2.1rem, 4vw, 3.35rem); line-height: 1.05; margin: 0 0 .8rem; }
    .ar-hero p { color: #d9f3f1; font-size: 1.04rem; max-width: 760px; line-height: 1.65; margin: 0; }
    .ar-chip {
      display: inline-block;
      margin-top: 1.25rem;
      margin-right: .4rem;
      border: 1px solid rgba(255, 255, 255, .28);
      background: rgba(255, 255, 255, .10);
      color: #fff;
      padding: .35rem .7rem;
      border-radius: 999px;
      font-size: .78rem;
    }
    .ar-section-label {
      color: #55e1ca;
      font-size: .76rem;
      text-transform: uppercase;
      letter-spacing: .12em;
      font-weight: 800;
      margin-bottom: .25rem;
    }

    /* ---------- Application footer ---------- */
    .ar-global-foot {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: .8rem 1.4rem;
      margin: 2.6rem 0 0;
      padding: 1rem 0 0;
      border-top: 1px solid rgba(130, 190, 199, .14);
      color: #8fabb3;
      font-size: .76rem;
      letter-spacing: .02em;
    }
    .ar-global-foot strong { color: #d9f2f1; letter-spacing: .08em; }
    .ar-global-foot .ar-foot-module {
      padding: .22rem .55rem;
      border: 1px solid rgba(130, 190, 199, .18);
      border-radius: 999px;
      color: #b6d2d5;
      font-size: .68rem;
      letter-spacing: .06em;
      text-transform: uppercase;
    }

    /* ---------- Scrollbars ---------- */
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #071925; }
    ::-webkit-scrollbar-thumb {
      background: rgba(130, 190, 199, .24);
      border-radius: 999px;
      border: 2px solid #071925;
    }
    ::-webkit-scrollbar-thumb:hover { background: rgba(130, 190, 199, .42); }

    @media (max-width: 900px) {
      .block-container { padding-top: 1rem; }
      [data-testid="stTopNavLink"] { padding: .3rem .55rem; }
      [class*="st-key-ar-head-"] { border-radius: 20px; }
    }
    @media (max-width: 640px) {
      .block-container { padding-left: 1rem; padding-right: 1rem; }
      .ar-hero { border-radius: 18px; }
      [class*="st-key-ar-head-"] { padding: 1.2rem 1.1rem; border-radius: 18px; }
      [class*="st-key-ar-head-"] h1, .ar-page-title { font-size: 1.9rem !important; }
      [data-testid="stMetric"] { padding: .85rem .9rem !important; }
      .stApp { background-attachment: scroll !important; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        scroll-behavior: auto !important;
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .01ms !important;
      }
      [data-testid="stMetric"]:hover,
      div.stButton > button:hover,
      [data-testid="stPageLink"] a:hover { transform: none; }
      .ar-page-dot { animation: none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# AI RESILIENCE — light glass interface layer.
# This override intentionally follows the existing shared component structure.
st.markdown(
    """
    <style>
    :root {
      color-scheme: light;
      --ar-bg: #F4F8F5;
      --ar-bg-deep: #EAF3EE;
      --ar-panel: rgba(255,255,255,.82);
      --ar-panel-2: #ffffff;
      --ar-panel-3: #EAF3EE;
      --ar-ink: #1D3030;
      --ar-ink-soft: #294640;
      --ar-muted: #71827F;
      --ar-faint: #8A9994;
      --ar-teal: #247A65;
      --ar-teal-soft: #2F8A70;
      --ar-cyan: #83B9A5;
      --ar-emerald: #31866B;
      --ar-amber: #a96b12;
      --ar-orange: #bd5b25;
      --ar-red: #c04444;
      --ar-violet: #7256b5;
      --ar-border: rgba(44, 105, 82, .16);
      --ar-border-strong: rgba(36, 122, 101, .32);
      --ar-shadow: 0 18px 48px rgba(26, 65, 49, .10);
      --ar-shadow-soft: 0 8px 26px rgba(26, 65, 49, .07);
    }
    html, body, [data-testid="stAppViewContainer"] {
      background: #F4F8F5 !important;
      color: #1D3030 !important;
    }
    .stApp {
      color: #1D3030 !important;
      background:
        radial-gradient(ellipse at 5% 0%, rgba(131, 185, 165, .15), transparent 32rem),
        radial-gradient(ellipse at 95% 5%, rgba(36, 122, 101, .10), transparent 34rem),
        linear-gradient(145deg, #F4F8F5 0%, #EAF3EE 52%, #F8FBF9 100%) !important;
      background-attachment: fixed !important;
    }
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stMain"], [data-testid="stMainBlockContainer"] {
      background: transparent !important;
      color: #1D3030 !important;
    }
    [data-testid="stHeader"], [data-testid="stToolbar"] {
      background: rgba(244,248,245,.88) !important;
      backdrop-filter: blur(18px);
    }
    [data-testid="stTopNav"] {
      background: rgba(244,248,245,.78) !important;
      border-bottom: 1px solid rgba(44,105,82,.16) !important;
    }
    [data-testid="stTopNavSection"], [data-testid="stTopNavLink"] {
      color: #294640 !important;
      text-shadow: none !important;
      font-weight: 700 !important;
    }
    [data-testid="stTopNavSection"] p, [data-testid="stTopNavLink"] p,
    [data-testid="stTopNavSection"] span, [data-testid="stTopNavLink"] span {
      color: inherit !important;
    }
    [data-testid="stTopNavSection"]:hover, [data-testid="stTopNavLink"]:hover {
      background: rgba(36,122,101,.09) !important;
      color: #247A65 !important;
    }
    [data-testid="stTopNavSection"][aria-expanded="true"],
    [data-testid="stTopNavLink"][aria-current="page"],
    [data-testid="stTopNavLink"][data-active="true"] {
      background: rgba(36,122,101,.12) !important;
      color: #247A65 !important;
      box-shadow: inset 0 0 0 1px rgba(36,122,101,.18);
    }
    [data-testid="stTopNavPopover"], [data-testid="stTopNavPopoverBody"] {
      background: rgba(255,255,255,.97) !important;
      border: 1px solid var(--ar-border) !important;
      box-shadow: var(--ar-shadow) !important;
    }
    [data-testid="stTopNavDropdownLink"] {
      color: #294640 !important;
    }
    [data-testid="stTopNavDropdownLink"] p,
    [data-testid="stTopNavDropdownLink"] span { color: inherit !important; }
    [data-testid="stTopNavDropdownLink"]:hover {
      color: #247A65 !important;
      background: #EAF3EE !important;
    }
    [data-testid="stSidebar"] {
      background: #163D36 !important;
      border-right: 1px solid rgba(220,232,227,.18) !important;
    }
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label { color: #F3F8F5 !important; }
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: #C4D8CF !important; }
    [data-testid="stSidebarNavLink"]:hover { background: rgba(131,185,165,.14) !important; }
    h1, h2, h3, h4, h5, h6,
    [data-testid="stHeading"] * {
      color: #1D3030 !important;
    }
    p, li, label, .stMarkdown, .stCaption,
    [data-testid="stWidgetLabel"] { color: #405D54; }
    [data-testid="stCaptionContainer"], .stCaption {
      color: #82918B !important;
    }
    strong { color: #1D3030 !important; }
    a { color: #247A65 !important; }
    a:hover { color: #1B604F !important; }
    hr { border-color: rgba(44,105,82,.20) !important; }
    code {
      color: #176d68 !important;
      background: #eaf6f4 !important;
      border-color: rgba(36,122,101,.16) !important;
    }
    [class*="st-key-ar-head-"] {
      border: 1px solid rgba(44,105,82,.20) !important;
      border-radius: 24px !important;
      background:
        radial-gradient(ellipse at 94% 0%, rgba(75,174,163,.12), transparent 23rem),
        linear-gradient(120deg, rgba(255,255,255,.97), rgba(239,248,249,.94)) !important;
      box-shadow: 0 14px 38px rgba(32,73,97,.09) !important;
    }
    [class*="st-key-ar-head-"] h1,
    [class*="st-key-ar-head-"] .ar-page-title {
      color: #1D3030 !important;
    }
    .ar-page-kicker, .ar-sec-overline { color: #247A65 !important; }
    .ar-page-dot {
      background: #247A65 !important;
      box-shadow: 0 0 0 4px rgba(36,122,101,.13) !important;
    }
    .ar-page-copy, .ar-sec-intro p { color: #71827F !important; }
    .ar-page-meta span {
      color: #48685B !important;
      background: rgba(255,255,255,.72) !important;
      border-color: rgba(44,105,82,.20) !important;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
      border: 1px solid rgba(44,105,82,.18) !important;
      border-radius: 17px !important;
      background: rgba(255,255,255,.82) !important;
      box-shadow: 0 8px 24px rgba(32,73,97,.07) !important;
      backdrop-filter: blur(12px);
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
      border-color: rgba(36,122,101,.34) !important;
      box-shadow: 0 14px 32px rgba(32,73,97,.10) !important;
    }
    [data-testid="stMetric"] {
      background: linear-gradient(145deg, rgba(255,255,255,.98), rgba(244,250,251,.94)) !important;
      border: 1px solid rgba(44,105,82,.18) !important;
      box-shadow: 0 8px 24px rgba(32,73,97,.07) !important;
    }
    [data-testid="stMetric"]:before {
      background: linear-gradient(90deg, #247A65, #7cc9c0, transparent) !important;
    }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
      color: #71827F !important;
    }
    [data-testid="stMetricValue"] { color: #1D3030 !important; }
    [data-testid="stMetricDelta"] { color: #16866f !important; }
    [data-testid="stExpander"] {
      background: rgba(255,255,255,.78) !important;
      border: 1px solid rgba(44,105,82,.18) !important;
      border-radius: 14px !important;
    }
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] summary p { color: #294640 !important; }
    [data-testid="stTabs"] button {
      color: #71827F !important;
      border-radius: 10px !important;
    }
    [data-testid="stTabs"] button:hover {
      color: #247A65 !important;
      background: rgba(36,122,101,.07) !important;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
      color: #1B604F !important;
      background: linear-gradient(110deg, #DDEFE6, #EAF3EE) !important;
      box-shadow: inset 0 0 0 1px rgba(36,122,101,.18) !important;
    }
    div.stButton > button, div.stDownloadButton > button,
    [data-testid="stFormSubmitButton"] > button {
      color: #ffffff !important;
      border: 1px solid rgba(8,127,120,.20) !important;
      background: linear-gradient(110deg, #247A65, #247A65) !important;
      box-shadow: 0 6px 16px rgba(36,122,101,.14);
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
      background: linear-gradient(110deg, #076d68, #11877f) !important;
      box-shadow: 0 10px 22px rgba(36,122,101,.20) !important;
    }
    div.stButton > button[kind="secondary"],
    button[data-testid="stBaseButton-secondary"] {
      color: #315B4C !important;
      background: #F4F8F5 !important;
      border-color: rgba(44,105,82,.24) !important;
    }
    input, textarea, [data-baseweb="select"] > div {
      color: #294640 !important;
      background-color: #ffffff !important;
      border-color: rgba(44,105,82,.30) !important;
    }
    [data-testid="stDataFrame"], [data-testid="stTable"] {
      border: 1px solid rgba(44,105,82,.16);
      border-radius: 12px;
      overflow: hidden;
    }
    div[data-testid="stAlert"] {
      background: rgba(255,255,255,.92) !important;
      border-color: rgba(44,105,82,.20) !important;
      box-shadow: 0 6px 18px rgba(32,73,97,.06) !important;
    }
    div[data-testid="stAlert"] p { color: #405D54 !important; }
    [data-testid="stSpinner"] { color: #247A65 !important; }
    [data-testid="stProgress"] { background: #EAF3EE !important; }
    [data-testid="stProgress"] > div > div {
      background: linear-gradient(90deg, #247A65, #55b7c8) !important;
    }
    .ar-risk-safe { color:#16764f !important; background:#e9f7ef !important; border-color:#b9e4cb !important; }
    .ar-risk-moderate { color:#94620e !important; background:#fff6df !important; border-color:#f0d99c !important; }
    .ar-risk-high { color:#a54e1c !important; background:#fff0e5 !important; border-color:#efc3a5 !important; }
    .ar-risk-critical { color:#a83333 !important; background:#fff0f0 !important; border-color:#edb8b8 !important; }
    .ar-global-foot {
      border-top-color: rgba(44,105,82,.18) !important;
      color: #82918B !important;
    }
    .ar-global-foot strong { color: #315B4C !important; }
    .ar-global-foot .ar-foot-module {
      color: #48685B !important;
      border-color: rgba(44,105,82,.20) !important;
      background: rgba(255,255,255,.65);
    }
    ::-webkit-scrollbar-track { background: #edf4f7 !important; }
    ::-webkit-scrollbar-thumb {
      background: rgba(44,105,82,.30) !important;
      border-color: #edf4f7 !important;
    }
    [data-testid="stTopNavSection"]:focus-visible,
    [data-testid="stTopNavLink"]:focus-visible,
    [data-testid="stTopNavDropdownLink"]:focus-visible,
    [data-testid="stPageLink"] a:focus-visible,
    div.stButton > button:focus-visible,
    div.stDownloadButton > button:focus-visible,
    input:focus-visible, textarea:focus-visible, select:focus-visible {
      outline: 2px solid #247A65 !important;
      outline-offset: 2px;
    }
    @media (max-width: 640px) {
      .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
      [class*="st-key-ar-head-"] { border-radius: 18px !important; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .01ms !important;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Match the shared chart surfaces to the application chrome. Both libraries are
# optional in minimal deployments, so failures are intentionally non-fatal.
try:  # pragma: no cover - presentation only
    import plotly.graph_objects as go
    import plotly.io as pio

    pio.templates["ai_resilience"] = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family='-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif',
                color="#405D54",
                size=13,
            ),
            title=dict(font=dict(color="#1D3030", size=17), x=0.01, xanchor="left"),
            colorway=["#247A65", "#83B9A5", "#328BCB", "#8064B5", "#D58A36", "#C5A13A", "#C85C5C"],
            xaxis=dict(
                gridcolor="rgba(44,105,82,.12)",
                zerolinecolor="rgba(44,105,82,.18)",
                linecolor="rgba(44,105,82,.24)",
                tickfont=dict(color="#71827F"),
                title=dict(font=dict(color="#71827F")),
            ),
            yaxis=dict(
                gridcolor="rgba(44,105,82,.12)",
                zerolinecolor="rgba(44,105,82,.18)",
                linecolor="rgba(44,105,82,.24)",
                tickfont=dict(color="#71827F"),
                title=dict(font=dict(color="#71827F")),
            ),
            legend=dict(
                bgcolor="rgba(255,255,255,.88)",
                bordercolor="rgba(44,105,82,.18)",
                borderwidth=1,
                font=dict(color="#405D54"),
            ),
            hoverlabel=dict(
                bgcolor="#ffffff",
                bordercolor="rgba(130,190,199,.35)",
                font=dict(color="#1D3030"),
            ),
            margin=dict(l=55, r=28, t=64, b=48),
        )
    )
    pio.templates.default = "ai_resilience"
except Exception:  # pragma: no cover - optional dependency
    pass

try:  # pragma: no cover - presentation only
    import altair as alt

    def _ar_altair_theme() -> dict:
        return {
            "config": {
                "background": "transparent",
                "font": '-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif',
                "view": {"stroke": "transparent", "continuousWidth": 640, "continuousHeight": 320},
                "axis": {
                    "domainColor": "rgba(130,190,199,.30)",
                    "gridColor": "rgba(44,105,82,.12)",
                    "tickColor": "rgba(130,190,199,.30)",
                    "labelColor": "#71827F",
                    "titleColor": "#71827F",
                    "labelFontSize": 11,
                    "titleFontSize": 12,
                    "titleFontWeight": 600,
                },
                "legend": {
                    "labelColor": "#405D54",
                    "titleColor": "#b9d4d9",
                    "labelFontSize": 11,
                    "titleFontSize": 11,
                },
                "title": {"color": "#1D3030", "fontSize": 15, "anchor": "start"},
                "range": {
                    "category": ["#247A65", "#83B9A5", "#328BCB", "#8064B5", "#D58A36", "#C5A13A", "#C85C5C"],
                },
            }
        }

    alt.themes.register("ai_resilience", _ar_altair_theme)
    alt.themes.enable("ai_resilience")
except Exception:  # pragma: no cover - optional dependency
    pass


# The homepage carries its own cinematic masthead; the shared breadcrumb strip
# is kept for the analytical workspaces where it provides useful orientation.
if page.title != "Home":
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:.55rem;margin:.1rem 0 1rem;color:#71827F;font-size:.82rem">
          <span style="display:inline-block;width:.55rem;height:.55rem;border-radius:50%;background:#247A65"></span>
          <span><strong style="color:#315B4C">AI RESILIENCE</strong> · KOCHI CLIMATE INTELLIGENCE · INTELLIGENT CITIES, RESILIENT FUTURES</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

page.run()

# Final application-wide polish is injected after the selected page renders so
# page-local styles cannot accidentally break shared controls or readability.
st.markdown(
    """
    <style>
    /* Consistent controls */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div {
      color: #294640 !important;
      background: rgba(255,255,255,.96) !important;
      border-color: rgba(44,105,82,.25) !important;
      border-radius: 11px !important;
      box-shadow: none !important;
    }
    [data-testid="stTextInput"] input:focus,
    [data-testid="stNumberInput"] input:focus,
    [data-testid="stDateInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {
      border-color: #247A65 !important;
      box-shadow: 0 0 0 2px rgba(36,122,101,.13) !important;
    }
    [data-testid="stCheckbox"] label,
    [data-testid="stRadio"] label,
    [data-testid="stToggle"] label,
    [data-testid="stSlider"] label,
    [data-testid="stWidgetLabel"] {
      color: #405D54 !important;
    }
    [data-testid="stCheckbox"] input,
    [data-testid="stRadio"] input { accent-color: #247A65 !important; }
    [data-testid="stSelectbox"] svg,
    [data-testid="stMultiSelect"] svg { color: #48685B !important; }
    [data-baseweb="popover"], [data-baseweb="menu"] {
      background: #ffffff !important;
      border: 1px solid rgba(44,105,82,.18) !important;
      box-shadow: 0 14px 32px rgba(26,65,49,.13) !important;
    }
    [role="option"] { color: #294640 !important; }
    [role="option"]:hover, [aria-selected="true"][role="option"] {
      background: #EAF3EE !important;
    }

    /* Data and chart surfaces */
    [data-testid="stDataFrame"], [data-testid="stTable"],
    [data-testid="stPlotlyChart"], [data-testid="stVegaLiteChart"],
    [data-testid="stPydeckChart"] {
      border: 1px solid rgba(44,105,82,.15) !important;
      border-radius: 14px !important;
      background: rgba(255,255,255,.72) !important;
      overflow: hidden;
    }
    [data-testid="stDataFrame"] [role="grid"],
    [data-testid="stTable"] table {
      color: #294640 !important;
    }
    [data-testid="stPlotlyChart"] .js-plotly-plot,
    [data-testid="stVegaLiteChart"] canvas {
      border-radius: 12px;
    }

    /* Alerts, forms and expandable content */
    [data-testid="stAlert"] {
      border-radius: 13px !important;
      border: 1px solid rgba(44,105,82,.18) !important;
    }
    [data-testid="stForm"] {
      border: 1px solid rgba(44,105,82,.16) !important;
      border-radius: 16px !important;
      padding: 1rem !important;
      background: rgba(255,255,255,.66) !important;
    }
    [data-testid="stExpander"] {
      border-radius: 13px !important;
      border-color: rgba(44,105,82,.18) !important;
    }

    /* Responsive page rhythm and keyboard accessibility */
    @media (max-width: 900px) {
      .block-container { padding-top: 1rem !important; }
      [class*="st-key-ar-head-"] { padding: 1.25rem !important; }
      [data-testid="stMetric"] { padding: .8rem !important; }
    }
    @media (max-width: 640px) {
      .block-container { padding-left: .85rem !important; padding-right: .85rem !important; }
      [data-testid="stHorizontalBlock"] { gap: .65rem !important; }
      [class*="st-key-ar-head-"] h1,
      [class*="st-key-ar-head-"] .ar-page-title {
        font-size: clamp(1.65rem, 8vw, 2.25rem) !important;
        line-height: 1.08 !important;
      }
      [data-testid="stMetricValue"] { font-size: 1.35rem !important; }
      [data-testid="stDataFrame"], [data-testid="stTable"] { max-width: 100%; }
    }
    :focus-visible {
      outline: 2px solid #247A65 !important;
      outline-offset: 2px !important;
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: .01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .01ms !important;
        scroll-behavior: auto !important;
      }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if page.title != "Home":
    st.markdown(
        f"""
        <footer class="ar-global-foot">
          <span><strong>AI RESILIENCE</strong> · Evidence-first environmental &amp; disaster intelligence</span>
          <span class="ar-foot-module">{html.escape(page.title)}</span>
        </footer>
        """,
        unsafe_allow_html=True,
    )

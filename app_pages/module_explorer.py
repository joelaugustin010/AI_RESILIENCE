"""Integrated visual module explorer for the AI_RESILIENCE application."""

from __future__ import annotations

import streamlit as st

from src.ui_theme import render_page_intro


st.markdown(
    """
    <style>
    /* Explorer uses a light coastal surface so text remains readable under
       both the global app theme and Streamlit's light/dark browser settings. */
    [data-testid="stMain"] .ar-explorer-lede {
      max-width: 900px !important;
      color: #36545a !important;
      -webkit-text-fill-color: #36545a !important;
      font-size: 1rem !important;
      line-height: 1.75 !important;
      font-weight: 450 !important;
      margin: 0 0 1.35rem !important;
    }
    [data-testid="stMain"] .ar-explorer-group {
      margin: 1.8rem 0 .85rem !important;
      color: #176b63 !important;
      -webkit-text-fill-color: #176b63 !important;
      font-size: .82rem !important;
      line-height: 1.4 !important;
      font-weight: 800 !important;
      letter-spacing: .11em !important;
      text-transform: uppercase !important;
    }
    [data-testid="stMain"] .ar-explorer-card {
      min-height: 190px !important;
      display: flex !important;
      flex-direction: column !important;
      justify-content: flex-end !important;
      padding: 1.25rem !important;
      border: 1px solid #cfe2dc !important;
      border-radius: 18px !important;
      overflow: hidden !important;
      color: #183e43 !important;
      background: linear-gradient(145deg, #ffffff 0%, #edf6f2 100%) !important;
      box-shadow: 0 8px 24px rgba(23, 78, 85, .08) !important;
      transition: transform .18s ease, box-shadow .18s ease !important;
    }
    [data-testid="stMain"] .ar-explorer-card:hover {
      transform: translateY(-3px) !important;
      box-shadow: 0 14px 30px rgba(23, 78, 85, .13) !important;
      border-color: #91c8bb !important;
    }
    [data-testid="stMain"] .ar-explorer-icon {
      display: inline-flex !important;
      align-items: center !important;
      justify-content: center !important;
      width: 2.7rem !important;
      height: 2.7rem !important;
      margin: 0 0 auto !important;
      border-radius: 13px !important;
      background: #dcefe9 !important;
      color: #176b63 !important;
      font-size: 1.45rem !important;
    }
    [data-testid="stMain"] .ar-explorer-card h3 {
      color: #173f43 !important;
      -webkit-text-fill-color: #173f43 !important;
      font-size: 1.12rem !important;
      font-weight: 780 !important;
      line-height: 1.35 !important;
      letter-spacing: -.015em !important;
      margin: 1.15rem 0 .45rem !important;
    }
    [data-testid="stMain"] .ar-explorer-card p {
      color: #456267 !important;
      -webkit-text-fill-color: #456267 !important;
      font-size: .91rem !important;
      font-weight: 450 !important;
      line-height: 1.6 !important;
      margin: 0 !important;
    }
    [data-testid="stMain"] .ar-explorer-meta {
      margin-top: .8rem !important;
      color: #176b63 !important;
      -webkit-text-fill-color: #176b63 !important;
      font-size: .72rem !important;
      line-height: 1.35 !important;
      font-weight: 800 !important;
      letter-spacing: .055em !important;
      text-transform: uppercase !important;
    }
    [data-testid="stMain"] [data-testid="stWidgetLabel"] p {
      color: #294f53 !important;
      -webkit-text-fill-color: #294f53 !important;
      font-size: .9rem !important;
      font-weight: 700 !important;
    }
    [data-testid="stMain"] [data-testid="stTextInput"] input {
      color: #173f43 !important;
      -webkit-text-fill-color: #173f43 !important;
      background: #ffffff !important;
      border: 1px solid #bfd8d0 !important;
      border-radius: 11px !important;
      min-height: 2.8rem !important;
    }
    [data-testid="stMain"] [data-testid="stTextInput"] input::placeholder {
      color: #718985 !important;
      -webkit-text-fill-color: #718985 !important;
      opacity: 1 !important;
    }
    [data-testid="stMain"] [data-testid="stSelectbox"] div,
    [data-testid="stMain"] [data-testid="stSelectbox"] span {
      color: #173f43 !important;
      -webkit-text-fill-color: #173f43 !important;
    }
    [data-testid="stMain"] [data-testid="stMetricLabel"],
    [data-testid="stMain"] [data-testid="stMetricLabel"] p {
      color: #456267 !important;
      -webkit-text-fill-color: #456267 !important;
      font-weight: 700 !important;
    }
    [data-testid="stMain"] [data-testid="stMetricValue"] {
      color: #176b63 !important;
      -webkit-text-fill-color: #176b63 !important;
      font-weight: 800 !important;
    }
    [data-testid="stMain"] [data-testid="stAlert"] p {
      color: #294f53 !important;
      -webkit-text-fill-color: #294f53 !important;
    }
    @media (max-width: 760px) {
      [data-testid="stMain"] .ar-explorer-card { min-height: 170px !important; }
      [data-testid="stMain"] .ar-explorer-card h3 { font-size: 1.04rem !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

render_page_intro(
    "module-explorer",
    "Explore AI_RESILIENCE",
    "Find the right workspace for the question you want to investigate — from Kochi's environmental evidence to multi-hazard review and practical mitigation planning.",
    eyebrow="AI_RESILIENCE · MODULE EXPLORER",
    tags=("12 workspaces", "Evidence first", "Kochi pilot"),
)
st.markdown(
    '<p class="ar-explorer-lede">Choose a workspace below. Each card opens an existing application page; evidence quality, assumptions and known limitations remain visible within the relevant workflow.</p>',
    unsafe_allow_html=True,
)

MODULE_GROUPS = (
    (
        "Environmental intelligence",
        (
            ("", "Kochi Map", "Explore spatial layers, infrastructure context and source validation notes.", "kochi/waterfront.jpg", "app_pages/kochi_map.py", "Spatial context"),
            ("", "Air Pollution", "Review air-quality evidence, pollutant context and monitoring readiness.", "kochi/coast.jpg", "app_pages/air_pollution.py", "Atmospheric evidence"),
            ("", "Hospital Vulnerability", "Inspect critical-facility context and documented accessibility limitations.", "kochi/water-metro.jpg", "app_pages/hospital_vulnerability.py", "Public health"),
            ("", "Data & Model Transparency", "Review coverage, provenance, validation status and known data limitations.", "kochi/mangalavanam.jpg", "app_pages/data_readiness.py", "Transparency"),
        ),
    ),
    (
        "Disaster resilience",
        (
            ("", "Decision Workflow", "Move from a scenario question through evidence gates and decision context.", "kochi/backwaters.jpg", "app_pages/decision_workflow.py", "Scenario review"),
            ("", "Disaster Intelligence Assistant", "Ask natural-language questions grounded in reviewed project evidence.", "kochi/fishing-nets.jpg", "app_pages/disaster_assistant.py", "Grounded assistant"),
            ("", "Cyclone + Flood", "Explore compound hazard scenario inputs, outputs and uncertainty.", "kochi/maradu.jpg", "app_pages/compound_scenario.py", "Compound hazards"),
            ("", "Multi-Hazard Evidence Review", "Inspect available hazard evidence without presenting unsupported certainty.", "kochi/industrial-coast.jpg", "app_pages/disaster_probability.py", "Evidence review"),
            ("", "Hazard Model Lab", "Review model inputs, readiness and limitations across hazard workflows.", "kochi/backwaters.jpg", "app_pages/hazard_model_lab.py", "Model readiness"),
            ("", "ML Evidence & Demonstration", "Replay documented research cases and inspect model limitations without live-warning claims.", "beauty-forest.webp", "app_pages/submission_ml_demo.py", "Research evidence"),
        ),
    ),
    (
        "Mitigation & planning",
        (
            ("", "Mitigation Budget", "Build a transparent planning worksheet using user-supplied assumptions.", "kochi/industrial-coast.jpg", "app_pages/mitigation_planner.py", "Budget planning"),
            ("", "Smart Mitigation Design Studio", "Develop connected mitigation concepts while keeping assumptions visible.", "kochi/mangalavanam.jpg", "app_pages/smart_mitigation_design.py", "Design studio"),
        ),
    ),
)

all_modules = [
    (group_title, module)
    for group_title, modules in MODULE_GROUPS
    for module in modules
]

search_col, group_col = st.columns([2, 1], gap="medium")
with search_col:
    search_term = st.text_input(
        "Search workspaces",
        placeholder="Try air quality, flood, budget, hospital…",
        key="explorer_search",
    ).strip().casefold()
with group_col:
    selected_group = st.selectbox(
        "Workspace category",
        ["All categories", *(group_title for group_title, _ in MODULE_GROUPS)],
        key="explorer_category",
    )

filtered_groups = []
for group_title, modules in MODULE_GROUPS:
    if selected_group != "All categories" and group_title != selected_group:
        continue
    matches = [
        module for module in modules
        if not search_term
        or search_term in " ".join((module[1], module[2], module[5], group_title)).casefold()
    ]
    if matches:
        filtered_groups.append((group_title, matches))

visible_count = sum(len(modules) for _, modules in filtered_groups)
metric_cols = st.columns(3)
metric_cols[0].metric("Available workspaces", len(all_modules))
metric_cols[1].metric("Categories", len(MODULE_GROUPS))
metric_cols[2].metric("Matching results", visible_count)

if not visible_count:
    st.info("No workspace matches that search. Try a broader keyword or choose All categories.")
else:
    for group_title, modules in filtered_groups:
        st.markdown(f'<div class="ar-explorer-group">{group_title}</div>', unsafe_allow_html=True)
        for start in range(0, len(modules), 3):
            columns = st.columns(3, gap="medium")
            for column, (icon, title, description, image, route, meta) in zip(columns, modules[start:start + 3]):
                with column:
                    st.markdown(
                        f'<article class="ar-explorer-card" style="--explorer-image:url(\'app/static/images/{image}\')"><div class="ar-explorer-icon">{icon}</div><h3>{title}</h3><p>{description}</p><div class="ar-explorer-meta">{meta} · Open workspace →</div></article>',
                        unsafe_allow_html=True,
                    )
                    st.page_link(
                        route,
                        label=f"Open {title}",
                                                use_container_width=True,
                    )

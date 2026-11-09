"""Integrated visual module explorer for the AI_RESILIENCE application."""

from __future__ import annotations

import streamlit as st

from src.ui_theme import render_page_intro


st.markdown(
    """
    <style>
    .ar-explorer-lede { max-width:850px; color:#5d756c; line-height:1.7; margin:-.4rem 0 1.4rem; }
    .ar-explorer-group { margin:1.7rem 0 .7rem; color:#247a65; font-size:.72rem; font-weight:850; letter-spacing:.14em; text-transform:uppercase; }
    .ar-explorer-card { min-height:185px; display:flex; flex-direction:column; justify-content:flex-end; padding:1.15rem; border-radius:20px; overflow:hidden; color:#fff; background:linear-gradient(180deg,rgba(7,24,22,.03),rgba(7,25,23,.9)),var(--explorer-image) center/cover; box-shadow:0 12px 30px rgba(24,73,55,.13); transition:transform .2s ease,box-shadow .2s ease; }
    .ar-explorer-card:hover { transform:translateY(-4px); box-shadow:0 20px 42px rgba(24,73,55,.21); }
    .ar-explorer-icon { margin-bottom:auto; font-size:1.5rem; }
    .ar-explorer-card h3 { color:#fff!important; font-size:1.05rem; margin:0 0 .25rem; }
    .ar-explorer-card p { color:#e4f4ea!important; font-size:.8rem; line-height:1.45; margin:0; }
    .ar-explorer-meta { margin-top:.55rem; color:#c8f2dc; font-size:.68rem; font-weight:750; letter-spacing:.05em; text-transform:uppercase; }
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
            ("🌊", "Kochi Map", "Explore spatial layers, infrastructure context and source validation notes.", "kochi/waterfront.jpg", "app_pages/kochi_map.py", "Spatial context"),
            ("🌬️", "Air Pollution", "Review air-quality evidence, pollutant context and monitoring readiness.", "kochi/coast.jpg", "app_pages/air_pollution.py", "Atmospheric evidence"),
            ("🏥", "Hospital Vulnerability", "Inspect critical-facility context and documented accessibility limitations.", "kochi/water-metro.jpg", "app_pages/hospital_vulnerability.py", "Public health"),
            ("🌿", "Data & Model Transparency", "Review coverage, provenance, validation status and known data limitations.", "kochi/mangalavanam.jpg", "app_pages/data_readiness.py", "Transparency"),
        ),
    ),
    (
        "Disaster resilience",
        (
            ("🧭", "Decision Workflow", "Move from a scenario question through evidence gates and decision context.", "kochi/backwaters.jpg", "app_pages/decision_workflow.py", "Scenario review"),
            ("🧠", "Disaster Intelligence Assistant", "Ask natural-language questions grounded in reviewed project evidence.", "kochi/fishing-nets.jpg", "app_pages/disaster_assistant.py", "Grounded assistant"),
            ("⛈️", "Cyclone + Flood", "Explore compound hazard scenario inputs, outputs and uncertainty.", "kochi/maradu.jpg", "app_pages/compound_scenario.py", "Compound hazards"),
            ("📊", "Multi-Hazard Evidence Review", "Inspect available hazard evidence without presenting unsupported certainty.", "kochi/industrial-coast.jpg", "app_pages/disaster_probability.py", "Evidence review"),
            ("🧪", "Hazard Model Lab", "Review model inputs, readiness and limitations across hazard workflows.", "kochi/backwaters.jpg", "app_pages/hazard_model_lab.py", "Model readiness"),
            ("📈", "ML Evidence & Demonstration", "Replay documented research cases and inspect model limitations without live-warning claims.", "beauty-forest.webp", "app_pages/submission_ml_demo.py", "Research evidence"),
        ),
    ),
    (
        "Mitigation & planning",
        (
            ("💼", "Mitigation Budget", "Build a transparent planning worksheet using user-supplied assumptions.", "kochi/industrial-coast.jpg", "app_pages/mitigation_planner.py", "Budget planning"),
            ("🛠️", "Smart Mitigation Design Studio", "Develop connected mitigation concepts while keeping assumptions visible.", "kochi/mangalavanam.jpg", "app_pages/smart_mitigation_design.py", "Design studio"),
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
                        icon=":material/arrow_forward:",
                        use_container_width=True,
                    )

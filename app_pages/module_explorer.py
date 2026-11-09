"""Integrated visual module explorer for the AI_RESILIENCE application."""

from __future__ import annotations

import streamlit as st

from src.ui_theme import page_header


st.markdown(
    """
    <style>
    .ar-explorer-lede { max-width:850px; color:#b7d0d2; line-height:1.72; margin:-.35rem 0 1.5rem; }
    .ar-explorer-group {
      display:flex; align-items:center; gap:.7rem; margin:2rem 0 .9rem;
      color:#8cf3df; font-size:.72rem; font-weight:850; letter-spacing:.16em;
      text-transform:uppercase;
    }
    .ar-explorer-group:after { content:""; height:1px; flex:1; background:linear-gradient(90deg,rgba(66,224,193,.32),transparent); }
    .ar-explorer-card {
      position:relative; isolation:isolate; min-height:230px; height:100%;
      display:flex; flex-direction:column; justify-content:flex-end;
      padding:1.25rem; border:1px solid rgba(168,224,220,.28);
      border-radius:22px; overflow:hidden; color:#fff;
      background:linear-gradient(145deg,#0b2635,#102f3d);
      box-shadow:0 16px 38px rgba(0,0,0,.25);
      transition:transform .28s cubic-bezier(.2,.7,.2,1),border-color .28s ease,box-shadow .28s ease;
    }
    .ar-explorer-card:before {
      content:""; position:absolute; z-index:-2; inset:0;
      background:var(--explorer-image) center/cover no-repeat;
      transform:scale(1.015); transition:transform .7s cubic-bezier(.2,.7,.2,1);
    }
    .ar-explorer-card:after {
      content:""; position:absolute; z-index:-1; inset:0;
      background:linear-gradient(180deg,rgba(3,16,24,.08) 0%,rgba(3,16,24,.26) 35%,rgba(3,16,24,.94) 100%),
                 linear-gradient(90deg,rgba(3,16,24,.18),transparent 85%);
    }
    .ar-explorer-card:hover {
      transform:translateY(-4px); border-color:rgba(105,239,214,.58);
      box-shadow:0 24px 48px rgba(0,0,0,.34);
    }
    .ar-explorer-card:hover:before { transform:scale(1.075); }
    .ar-explorer-icon {
      display:flex; align-items:center; justify-content:center; width:42px; height:42px;
      margin-bottom:auto; border:1px solid rgba(231,255,249,.32); border-radius:13px;
      background:rgba(4,24,33,.48); color:#fff; font-size:1.35rem;
      backdrop-filter:blur(9px);
    }
    .ar-explorer-card h3 { color:#fff!important; font-size:1.08rem; margin:.95rem 0 .3rem; letter-spacing:-.02em; }
    .ar-explorer-card p { color:#e1f0f1!important; font-size:.82rem; line-height:1.52; margin:0; max-width:34rem; }
    .ar-explorer-meta {
      display:inline-flex; align-items:center; width:max-content; max-width:100%;
      margin-top:.7rem; padding:.3rem .58rem; border:1px solid rgba(210,255,245,.23);
      border-radius:999px; background:rgba(4,24,33,.48); color:#baf5e9;
      font-size:.66rem; font-weight:800; letter-spacing:.07em; text-transform:uppercase;
      backdrop-filter:blur(8px);
    }
    [data-testid="stPageLink"] a {
      border:1px solid rgba(130,190,199,.22); border-radius:12px;
      background:rgba(11,36,52,.78); color:#e5f8f6!important;
      font-weight:750; transition:transform .2s ease,border-color .2s ease,background .2s ease;
    }
    [data-testid="stPageLink"] a:hover {
      transform:translateY(-1px); border-color:rgba(66,224,193,.45);
      background:rgba(17,64,73,.88);
    }
    @media(max-width:700px) {
      .ar-explorer-card { min-height:205px; }
      .ar-explorer-group { margin-top:1.5rem; }
    }
    @media(prefers-reduced-motion:reduce) {
      .ar-explorer-card,.ar-explorer-card:before,[data-testid="stPageLink"] a { transition:none; }
      .ar-explorer-card:hover,[data-testid="stPageLink"] a:hover { transform:none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

page_header(
    "AI_RESILIENCE · MODULE EXPLORER",
    "Explore AI_RESILIENCE",
    "Choose an existing workspace by the question you want to answer — from environmental signals and spatial context to disaster resilience and practical mitigation planning.",
    key="module-explorer",
    meta=("Existing modules", "Evidence first", "Kochi and Kerala"),
)
st.markdown(
    '<p class="ar-explorer-lede">Every card below opens a registered application module. Outputs retain their existing provenance, uncertainty notes, calculations and data-quality safeguards.</p>',
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

for group_title, modules in MODULE_GROUPS:
    st.markdown(f'<div class="ar-explorer-group">{group_title}</div>', unsafe_allow_html=True)
    for start in range(0, len(modules), 3):
        columns = st.columns(3, gap="medium")
        for column, (icon, title, description, image, route, meta) in zip(columns, modules[start:start + 3]):
            with column:
                st.markdown(
                    f'<article class="ar-explorer-card" style="--explorer-image:url(\'app/static/images/{image}\')"><div class="ar-explorer-icon">{icon}</div><h3>{title}</h3><p>{description}</p><div class="ar-explorer-meta">{meta} · Open workspace →</div></article>',
                    unsafe_allow_html=True,
                )
                st.page_link(route, label=f"Open {title}", icon=":material/arrow_forward:", use_container_width=True)

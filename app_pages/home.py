"""Command-centre landing page for AI RESILIENCE."""

import streamlit as st

# Command-centre layout; shared workspace styling is defined in app.py.
st.markdown(
    """
    <style>
    .stApp { background: transparent !important; }
    .ar-home-hero {
      position: relative; isolation: isolate; overflow: hidden;
      display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(180px, .75fr);
      gap: 1.5rem; align-items: center;
      padding: clamp(1.6rem, 4vw, 3.1rem);
      margin: .25rem 0 1.4rem; border-radius: 26px;
      color: #f8fafc; background: linear-gradient(125deg, #071a2b 0%, #103d59 54%, #087e8b 100%);
      box-shadow: 0 22px 55px rgba(7, 40, 61, .19);
    }
    .ar-home-hero:before {
      content: ""; position: absolute; inset: 0; z-index: -1; opacity: .17;
      background-image: linear-gradient(rgba(255,255,255,.12) 1px, transparent 1px),
                        linear-gradient(90deg, rgba(255,255,255,.12) 1px, transparent 1px);
      background-size: 36px 36px;
      mask-image: linear-gradient(110deg, black, transparent 80%);
    }
    .ar-home-hero:after {
      content: ""; position: absolute; z-index: -1; width: 330px; height: 330px;
      right: -95px; top: -115px; border: 1px solid rgba(153,246,228,.3);
      border-radius: 50%; box-shadow: 0 0 0 28px rgba(153,246,228,.055),
        0 0 0 62px rgba(153,246,228,.045), 0 0 0 100px rgba(153,246,228,.035);
    }
    .ar-home-kicker {
      color: #a5f3fc; text-transform: uppercase; letter-spacing: .16em;
      font-size: .74rem; font-weight: 800; margin-bottom: .9rem;
    }
    .ar-home-title {
      color: #fff !important; font-size: clamp(2.2rem, 4.6vw, 3.8rem) !important;
      line-height: 1.02 !important; letter-spacing: -.045em !important;
      margin: 0 0 1rem !important; font-weight: 850 !important;
    }
    .ar-home-copy {
      color: #dbeafe; max-width: 700px; font-size: 1.02rem; line-height: 1.72;
      margin: 0 0 1.15rem;
    }
    .ar-home-pill {
      display: inline-block; margin: .15rem .35rem .15rem 0; padding: .4rem .72rem;
      border-radius: 999px; border: 1px solid rgba(255,255,255,.23);
      background: rgba(255,255,255,.085); color: #f0fdfa; font-size: .77rem;
    }
    .ar-radar {
      min-height: 205px; display: flex; align-items: center; justify-content: center;
      position: relative;
    }
    .ar-radar-ring {
      width: 190px; height: 190px; border-radius: 50%; position: relative;
      border: 1px solid rgba(165,243,252,.45);
      background: radial-gradient(circle, rgba(34,211,238,.14) 0 2px, transparent 3px),
                  repeating-radial-gradient(circle, transparent 0 26px, rgba(165,243,252,.18) 27px 28px),
                  linear-gradient(135deg, rgba(255,255,255,.07), rgba(255,255,255,0));
      box-shadow: inset 0 0 40px rgba(34,211,238,.07), 0 0 42px rgba(34,211,238,.08);
    }
    .ar-radar-ring:before {
      content: ""; position: absolute; width: 1px; height: 100%; left: 50%; top: 0;
      background: rgba(165,243,252,.2);
    }
    .ar-radar-ring:after {
      content: ""; position: absolute; height: 1px; width: 100%; left: 0; top: 50%;
      background: rgba(165,243,252,.2);
    }
    .ar-radar-dot {
      position: absolute; left: 61%; top: 29%; width: 10px; height: 10px;
      border-radius: 50%; background: #99f6e4; box-shadow: 0 0 0 7px rgba(153,246,228,.13), 0 0 18px #5eead4;
    }
    .ar-mini-label {
      position: absolute; bottom: 3px; text-align: center; width: 100%;
      color: #bae6fd; font-size: .68rem; letter-spacing: .13em; text-transform: uppercase;
    }
    .ar-section-kicker {
      color: #68e8d1; font-size: .72rem; text-transform: uppercase;
      letter-spacing: .15em; font-weight: 850; margin-bottom: .25rem;
    }
    .ar-work-card {
      min-height: 190px; border: 1px solid rgba(130,190,199,.24); border-radius: 18px;
      padding: 1.05rem 1.1rem; background: linear-gradient(150deg,rgba(17,49,66,.96),rgba(9,31,46,.96));
      box-shadow: 0 7px 22px rgba(16,42,67,.045);
      transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    .ar-work-card:hover {
      transform: translateY(-3px); border-color: #8bd3dc;
      box-shadow: 0 14px 30px rgba(16,42,67,.085);
    }
    .ar-work-icon { font-size: 1.45rem; margin-bottom: .55rem; }
    .ar-work-title { color: #effafa; font-size: 1.02rem; font-weight: 800; margin-bottom: .35rem; }
    .ar-work-copy { color: #b6d0d4; font-size: .88rem; line-height: 1.55; }
    @media (max-width: 760px) {
      .ar-home-hero { grid-template-columns: 1fr; border-radius: 19px; }
      .ar-radar { display: none; }
    }
    @media (prefers-reduced-motion: reduce) {
      .ar-work-card { transition: none; }
      .ar-work-card:hover { transform: none; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <section class="ar-home-hero">
      <div>
        <div class="ar-home-kicker">Kochi · Urban resilience intelligence</div>
        <h1 class="ar-home-title">AI RESILIENCE</h1>
        <p class="ar-home-copy">
          Explore disaster evidence, understand uncertainty, and turn risk information
          into clearer preparedness decisions. One workspace for mapping, scenario
          review, environmental context, and mitigation planning.
        </p>
        <span class="ar-home-pill">Evidence-first</span>
        <span class="ar-home-pill">Multi-hazard planning</span>
        <span class="ar-home-pill">SDG 11 · SDG 13 · SDG 6 · SDG 9 aligned</span>
      </div>
      <div class="ar-radar" aria-hidden="true">
        <div class="ar-radar-ring"><span class="ar-radar-dot"></span></div>
        <div class="ar-mini-label">Observe · Assess · Prepare</div>
      </div>
    </section>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="ar-section-kicker">Command centre</div>', unsafe_allow_html=True)
st.subheader("Where would you like to start?")
st.caption("Choose a workspace. Results and map layers should always be interpreted alongside their source, coverage, and validation status.")

primary = [
    ("🧭", "Decision Workflow", "Build a scenario, inspect the supporting inputs, and review the generated decision summary.", "app_pages/decision_workflow.py", ":material/assignment_turned_in:"),
    ("🗺️", "Kochi Map", "Explore available geographic layers, ward labels, and spatial-data quality notices.", "app_pages/kochi_map.py", ":material/map:"),
    ("🌫️", "Air Pollution", "Review historical monitoring records and the limits of industrial-source attribution.", "app_pages/air_pollution.py", ":material/factory:"),
]
cols = st.columns(3, gap="medium")
for col, (icon, title, description, path, page_icon) in zip(cols, primary):
    with col:
        st.markdown(
            f'<div class="ar-work-card"><div class="ar-work-icon">{icon}</div>'
            f'<div class="ar-work-title">{title}</div><div class="ar-work-copy">{description}</div></div>',
            unsafe_allow_html=True,
        )
        st.page_link(path, label=f"Open {title}", icon=page_icon, use_container_width=True)

st.markdown('<div class="ar-section-kicker" style="margin-top:1.4rem">Research and planning tools</div>', unsafe_allow_html=True)
st.subheader("Explore the workspaces")
tools = [
    ("Disaster Intelligence Assistant", "Organise disaster-preparedness questions and evidence.", "app_pages/disaster_assistant.py", ":material/psychology_alt:"),
    ("Data Readiness", "Inspect provenance, completeness, and validation blockers.", "app_pages/data_readiness.py", ":material/fact_check:"),
    ("Hazard Model Lab", "Review model readiness before interpreting outputs.", "app_pages/hazard_model_lab.py", ":material/model_training:"),
    ("Hospital Vulnerability", "Review evidence needed for critical-facility exposure.", "app_pages/hospital_vulnerability.py", ":material/local_hospital:"),
    ("Cyclone + Flood", "Open the unified workflow and select the cyclone + flood scenario.", "app_pages/decision_workflow.py", ":material/thunderstorm:"),
    ("Disaster Probability", "Inspect probability-model readiness and limitations.", "app_pages/disaster_probability.py", ":material/analytics:"),
    ("Mitigation Budget", "Compare supplied costs and check budget arithmetic.", "app_pages/mitigation_planner.py", ":material/account_balance_wallet:"),
    ("Smart Mitigation Design", "Structure a mitigation concept for a selected scenario.", "app_pages/smart_mitigation_design.py", ":material/engineering:"),
]
for i in range(0, len(tools), 4):
    cols = st.columns(4, gap="medium")
    for col, (title, description, path, icon) in zip(cols, tools[i:i + 4]):
        with col:
            with st.container(border=True):
                st.markdown(f"#### {title}")
                st.caption(description)
                st.page_link(path, label="Open workspace", icon=icon, use_container_width=True)

st.divider()
st.markdown('<div class="ar-section-kicker">Trust and readiness</div>', unsafe_allow_html=True)
s1, s2, s3 = st.columns(3)
with s1:
    st.metric("Research workspaces", "11", help="One command centre, eight Explore tools, and two Plan tools.")
with s2:
    st.metric("Official emergency alerts", "Not enabled", help="This student prototype does not issue official warnings.")
with s3:
    st.metric("Validated live predictions", "Not enabled", help="Predictions require suitable local data and independent evaluation.")

st.info(
    "Scientific transparency matters: scenario outputs are not automatically validated probabilities, "
    "and historical observations do not prove current conditions or identify a pollution source. "
    "For an actual emergency, follow official Kerala State Disaster Management Authority, IMD, "
    "and district-administration guidance."
)

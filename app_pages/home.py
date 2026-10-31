"""Command centre landing page for the AI RESILIENCE project."""

import streamlit as st

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

st.markdown('<div class="ar-section-label">Command centre</div>', unsafe_allow_html=True)
st.subheader("Start with a question")
st.caption("Choose a workspace below. Each tool is designed to show what the evidence supports—and what still needs verification.")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("### 🧭 Assess a scenario")
    st.write("Describe a hazard, review the available evidence, compare scenarios and export a report.")
    st.page_link("app_pages/decision_workflow.py", label="Open Decision Workflow", icon=":material/assignment_turned_in:", use_container_width=True)
with c2:
    st.markdown("### 🗺️ Explore Kochi")
    st.write("Inspect available geographic layers and check the status of spatial evidence.")
    st.page_link("app_pages/kochi_map.py", label="Open Kochi Map", icon=":material/map:", use_container_width=True)
with c3:
    st.markdown("### 🌫️ Investigate air quality")
    st.write("Review historical monitoring evidence and the limits of source attribution.")
    st.page_link("app_pages/air_pollution.py", label="Open Air Quality", icon=":material/factory:", use_container_width=True)

st.divider()
st.markdown('<div class="ar-section-label">Explore the intelligence tools</div>', unsafe_allow_html=True)
tools = [
    ("Disaster Intelligence Assistant", "Organise questions and evidence for disaster preparedness.", "app_pages/disaster_assistant.py", ":material/psychology_alt:"),
    ("Data Readiness", "See which datasets are connected, incomplete or awaiting validation.", "app_pages/data_readiness.py", ":material/fact_check:"),
    ("Hazard Model Lab", "Inspect model readiness and limitations before interpreting results.", "app_pages/hazard_model_lab.py", ":material/model_training:"),
    ("Hospital Vulnerability", "Review the evidence required to assess critical-facility exposure.", "app_pages/hospital_vulnerability.py", ":material/local_hospital:"),
    ("Cyclone + Flood", "Explore compound-hazard assumptions and their evidence needs.", "app_pages/compound_scenario.py", ":material/thunderstorm:"),
    ("Disaster Probability", "Inspect probability-model readiness and limitations.", "app_pages/disaster_probability.py", ":material/analytics:"),
    ("Mitigation Budget", "Compare user-supplied costs and check arithmetic budget fit.", "app_pages/mitigation_planner.py", ":material/account_balance_wallet:"),
    ("Smart Mitigation Design", "Build a structured mitigation concept for a selected scenario.", "app_pages/smart_mitigation_design.py", ":material/engineering:"),
]
for i in range(0, len(tools), 4):
    cols = st.columns(4)
    for col, (title, description, path, icon) in zip(cols, tools[i:i + 4]):
        with col:
            with st.container(border=True):
                st.markdown(f"#### {title}")
                st.caption(description)
                st.page_link(path, label="Open workspace", icon=icon, use_container_width=True)

st.divider()
status1, status2, status3 = st.columns(3)
with status1:
    st.metric("Workspaces", "11", help="One command centre, nine Explore tools, and two Plan tools.")
with status2:
    st.metric("Official alerts", "Not enabled", help="The app does not issue official warnings.")
with status3:
    st.metric("Validated live predictions", "Not enabled", help="Numerical prediction remains disabled until appropriate local evidence and independent validation are available.")

st.info(
    "For a real emergency, follow official Kerala State Disaster Management Authority and district-administration guidance. "
    "This student project is for evidence exploration and preparedness planning, not emergency response."
)

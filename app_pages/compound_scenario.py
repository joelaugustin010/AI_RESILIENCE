"""Qualitative user-driven multi-hazard scenario worksheet."""

import streamlit as st

from src.prototype_data import load_dataset


st.header("What happens if hazards occur together?")
st.write("Select hazards and exposed services to organize a planning discussion. This is a qualitative scenario worksheet, not a local impact model or forecast.")

hazard_notes = {
    "Flood": "Review flood exposure, drainage condition, safe access, water and sanitation continuity.",
    "Cyclone": "Review wind-related damage pathways, power and communications continuity, shelter access, and timing with rainfall or coastal water.",
    "Earthquake": "Review building structural assessment, non-structural hazards, utility isolation, and access for emergency response.",
    "Landslide": "Review slope and ground-condition evidence, rainfall context, access routes, and safe-area planning.",
    "Heatwave": "Review heat-health plans, cooling access, water supply, outdoor worker exposure, and backup power.",
    "Drought": "Review water-source reliability, demand management, health and livelihood dependencies.",
    "Industrial incident": "Review facility-specific hazard information, isolation procedures, downwind/downstream exposure data, and official response protocols.",
    "Infrastructure failure": "Review dependencies and cascading failures across power, water, transport, drainage, and communications.",
}

with st.form("compound_scenario_form"):
    area = st.text_input("Area or location to consider", value="")
    hazards = st.multiselect("Hazards or failures in the scenario", list(hazard_notes), default=["Cyclone", "Flood"])
    conditions = st.text_area("Scenario conditions and timing (user supplied)", help="For example, sequence, duration, extent, and which observations are confirmed. Keep units and source with each value.")
    assets = st.multiselect("Services or assets to review", ["Hospitals", "Roads and bridges", "Electricity", "Drinking water", "Communications", "Shelters", "Schools", "Drainage", "Industrial facilities"], default=["Hospitals", "Roads and bridges", "Electricity"])
    submitted = st.form_submit_button("Build scenario checklist", type="primary")

if submitted:
    st.subheader("Scenario checklist")
    st.write(f"**Location:** {area.strip() or 'Not specified'}")
    st.write(f"**Selected hazards:** {', '.join(hazards) if hazards else 'None'}")
    if not hazards:
        st.warning("Select at least one hazard.")
    else:
        st.write("**Review these pathways:**")
        for hazard in hazards:
            st.write(f"- **{hazard}:** {hazard_notes[hazard]}")
        if len(hazards) > 1:
            st.info("Check sequencing and shared dependencies: one hazard can reduce access or service capacity needed to respond to another. This app has no locally calibrated interaction model and does not quantify combined effects.")
        if assets:
            st.write("**Assets selected for review:** " + ", ".join(assets))
            st.caption("For each asset, verify location, hazard exposure, service dependencies, backup duration, access route, and responsible operator.")
        st.write("**Conditions entered:**", conditions.strip() or "None")
        st.warning("No probability, damage, casualty, service-outage, or monetary impact estimate is available from this worksheet. Confirm conditions and response actions with local authorities and official guidance.")

try:
    examples = load_dataset("compound_disaster_data.csv", ["event_id", "district", "event_date", "compound_impact_severity_class"])
except (FileNotFoundError, ValueError):
    examples = None
if examples is not None:
    with st.expander("View the project's five unverified example rows"):
        st.caption("No source documentation is present in this project; these rows do not calculate the scenario.")
        st.dataframe(examples, hide_index=True, width="stretch")


import streamlit as st

st.set_page_config(
    page_title="Disaster Scenarios | AI RESILIENCE",
    page_icon="🌪️",
    layout="wide",
)

st.title("🌪️ Combined Disaster Scenario Analysis")
st.caption("AI RESILIENCE | Scenario-planning prototype")

st.warning(
    "This is a demonstration tool, not a validated disaster "
    "prediction system. Use official alerts for safety decisions."
)

# 1. Select the study area
st.header("1. Select a scenario")

area = st.selectbox(
    "Study area",
    [
        "Kochi",
        "Ernakulam",
        "Fort Kochi",
        "Edappally",
        "Kalamassery",
    ],
)

# 2. Select hypothetical hazards
st.subheader("Select the hazards to explore")

cyclone = st.checkbox("Cyclone")
flood = st.checkbox("Flood")
heavy_rain = st.checkbox("Heavy rainfall")
storm_surge = st.checkbox("Coastal storm surge")

# 3. Select services
st.subheader("Services to assess")

service_options = [
    "Hospitals and clinics",
    "Roads and bridges",
    "Schools",
    "Electricity supply",
    "Drinking-water supply",
    "Communication networks",
    "Emergency shelters",
]

services = st.multiselect(
    "Which services should planners review?",
    options=service_options,
    default=["Hospitals and clinics", "Roads and bridges"],
    placeholder="Choose one or more service types",
)

# 4. Analyse the scenario
if st.button("Analyse Scenario", type="primary"):
    selected_hazards = []

    if cyclone:
        selected_hazards.append("Cyclone")

    if flood:
        selected_hazards.append("Flood")

    if heavy_rain:
        selected_hazards.append("Heavy rainfall")

    if storm_surge:
        selected_hazards.append("Coastal storm surge")

    st.header("2. Scenario assessment result")
    st.write("**Study area:**", area)

    if not selected_hazards:
        st.info(
            "Please select at least one hazard, then click "
            "'Analyse Scenario'."
        )

    else:
        st.write("**Selected hazards:**", ", ".join(selected_hazards))

        hazard_count = len(selected_hazards)

        # Demonstration category based on hazard count only
        if hazard_count == 1:
            scenario_level = "Single-hazard scenario"
            explanation = (
                "One hazard is selected. Review local exposure, "
                "preparedness, and official warnings."
            )

        elif hazard_count == 2:
            scenario_level = "Combined-hazard scenario"
            explanation = (
                "Two hazards are selected. Their effects may overlap "
                "and create additional challenges."
            )

        else:
            scenario_level = "Multiple-hazard scenario"
            explanation = (
                "Three or more hazards are selected. A detailed "
                "assessment using verified local data is needed."
            )

        st.metric("Scenario category", scenario_level)
        st.write("**Interpretation:**", explanation)

        # 5. Services selected for review
        st.header("3. Services to review")

        if services:
            for service in services:
                st.write(f"- {service}")
        else:
            st.info("No service types were selected.")

        # 6. Planning recommendations
        st.header("4. Suggested planning checks")

        checks = [
            "Consult official weather and disaster-management alerts.",
            "Check current rainfall reports and relevant river levels.",
            "Identify verified evacuation routes and accessible shelters.",
            "Check emergency-service availability and backup communication.",
            "Review electricity and drinking-water backup arrangements.",
            "Use verified local maps to identify exposed infrastructure.",
        ]

        for check in checks:
            st.write(f"- {check}")

        # 7. Explain limitations
        st.info(
            "How this result is produced: the category is based only "
            "on the number of selected hazards. It does not calculate "
            "disaster probability, actual risk, or hospital vulnerability. "
            "This prototype does not yet use a trained AI model or live "
            "disaster data."
        )

st.caption(
    "AI RESILIENCE | Educational prototype | "
    "Not for emergency decision-making"
)

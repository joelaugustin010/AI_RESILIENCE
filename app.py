import streamlit as st

from assessment import assess_conditions

st.set_page_config(
    page_title="AI RESILIENCE",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 AI RESILIENCE")
st.subheader("AI-Powered Disaster Risk Assessment")

st.info(
    "Prototype interface for assessing environmental "
    "conditions and exploring city improvements."
)

st.sidebar.header("Team Workspace")

member = st.sidebar.selectbox(
    "Choose your role",
    ["Team Leader", "Data Analyst", "Developer"]
)

st.write("Welcome to the workspace,", member)

st.header("Environmental Data")

col1, col2 = st.columns(2)

with col1:
    rainfall = st.number_input(
        "Rainfall (mm)",
        min_value=0.0,
        max_value=1000.0,
        value=50.0
    )

    temperature = st.number_input(
        "Temperature (°C)",
        min_value=-20.0,
        max_value=60.0,
        value=30.0
    )

with col2:
    river_level = st.number_input(
        "River level (metres)",
        min_value=0.0,
        max_value=30.0,
        value=2.0
    )

    ground = st.selectbox(
        "Ground condition",
        ["Normal", "Waterlogged", "Dry", "Unstable"]
    )

if st.button("Assess Conditions"):
    score = assess_conditions(rainfall, river_level, ground)

    st.header("Assessment Results")
    st.metric("Sample indicator score", f"{score}/3")

    if score == 0:
        st.success("Few warning indicators in this sample.")
    elif score == 1:
        st.warning("Some warning indicators are present.")
    else:
        st.error("Multiple warning indicators are present.")

    st.caption(
        "Demonstration rules only. This is not a trained "
        "AI model or a real disaster forecast."
    )

st.divider()

st.header("City Improvement Suggestions")

st.write(
    "- Improve rainwater drainage and maintenance.\n"
    "- Monitor river levels during heavy rainfall.\n"
    "- Protect vulnerable areas and maintain emergency plans."
)
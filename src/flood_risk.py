
import streamlit as st

st.set_page_config(
    page_title="Kochi Flood Risk | AI RESILIENCE",
    page_icon="🌧️",
    layout="wide",
)

st.title("🌧️ Kochi Flood-Risk Assessment")
st.caption("AI RESILIENCE | Initial prototype")

st.warning(
    "This is an experimental demonstration. "
    "It does not predict real floods or replace official warnings."
)

area = st.selectbox(
    "Study area",
    [
        "Kochi — area not yet specified",
        "Ernakulam",
        "Fort Kochi",
        "Edappally",
        "Kalamassery",
        "Other area — verify location",
    ],
)

st.subheader("Enter observed conditions")

col1, col2 = st.columns(2)

with col1:
    rainfall = st.number_input(
        "Rainfall (mm)",
        min_value=0.0,
        max_value=1000.0,
        value=50.0,
        help="Enter an observed value and record its time period.",
    )

    river_level = st.number_input(
        "River level (metres)",
        min_value=0.0,
        max_value=30.0,
        value=2.0,
    )

with col2:
    ground = st.selectbox(
        "Ground condition",
        ["Unknown", "Normal", "Waterlogged", "Unstable"],
    )

    rainfall_period = st.selectbox(
        "Rainfall measurement period",
        ["Not specified", "Last 1 hour", "Last 24 hours"],
    )

if st.button("Review entered conditions", type="primary"):
    st.subheader("Observation summary")

    st.write("**Study area:**", area)
    st.write("**Rainfall:**", f"{rainfall} mm")
    st.write("**Rainfall period:**", rainfall_period)
    st.write("**River level:**", f"{river_level} metres")
    st.write("**Ground condition:**", ground)

    st.info(
        "No validated flood-risk estimate is available yet. "
        "These observations must be matched with suitable local "
        "data before a scientifically meaningful assessment can be made."
    )

st.divider()

st.subheader("Next development tasks")

st.markdown(
    """
    - Obtain reliable historical flood records for the study area.
    - Identify the source and measurement period of rainfall data.
    - Obtain relevant geographic and elevation information.
    - Validate the assessment method before reporting risk estimates.
    """
)

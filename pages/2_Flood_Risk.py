
import streamlit as st

st.title("🌧️ Kochi Flood-Risk Assessment")
st.caption("AI RESILIENCE | Experimental prototype")

st.warning(
    "This prototype does not provide real flood forecasts. "
    "Use official alerts for emergency decisions."
)

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

rainfall = st.number_input(
    "Rainfall (mm)",
    min_value=0.0,
    max_value=1000.0,
    value=50.0,
)

river_level = st.number_input(
    "River level (metres)",
    min_value=0.0,
    max_value=30.0,
    value=2.0,
)

ground = st.selectbox(
    "Ground condition",
    ["Unknown", "Normal", "Waterlogged", "Unstable"],
)

if st.button("Review observations"):
    st.subheader("Observation summary")
    st.write("Study area:", area)
    st.write("Rainfall:", rainfall, "mm")
    st.write("River level:", river_level, "metres")
    st.write("Ground condition:", ground)

    st.info(
        "A validated flood-risk model and reliable local data "
        "are required before estimating flood risk."
    )

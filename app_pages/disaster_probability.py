import streamlit as st

from src.flood_model import audit_flood_dataset, load_flood_data


st.header("What is the probability of a particular disaster?")

try:
    data, metadata = load_flood_data()
    readiness = audit_flood_dataset(data, metadata)
except (FileNotFoundError, ValueError, OSError) as error:
    st.error(str(error))
    st.stop()

st.write(
    f"The project contains {len(data)} unverified example row(s) labelled for a flood "
    "event within the next 24 hours. The model-readiness audit below checks the data "
    "and refuses to train or estimate a probability when evidence is inadequate."
)

positive = int(data["target_flood_event_next_24h"].eq(1).sum())
negative = int(data["target_flood_event_next_24h"].eq(0).sum())
if readiness["ready"]:
    st.success("The dataset passed the current prototype screening gates. Research evaluation is still not proof of operational forecast skill.")
else:
    st.error(
        "AI evaluation blocked: no model was fitted and no probability was calculated. "
        "The current file does not meet the data-readiness requirements."
    )

col1, col2, col3 = st.columns(3)
col1.metric("Labeled examples", len(data))
col2.metric("Rows labeled flood", positive)
col3.metric("Rows labeled no flood", negative)
st.caption(
    f"Date coverage: {readiness['date_min'] or 'unknown'} to {readiness['date_max'] or 'unknown'} "
    f"({readiness['distinct_dates']} distinct date(s)); exact duplicate rows: {readiness['exact_duplicates']}."
)
st.caption(
    "The class counts describe these example rows only. They are not a probability "
    "for a new place or time."
)

with st.expander("Why the model is or is not ready", expanded=not readiness["ready"]):
    st.write(
        f"Dataset kind: **{metadata.get('data_kind', 'not documented')}**. "
        f"Label source: **{metadata.get('label_source') or 'not documented'}**."
    )
    if readiness["blockers"]:
        st.markdown("**Blocking issues**")
        for reason in readiness["blockers"]:
            st.markdown(f"- {reason}")
    if readiness["warnings"]:
        st.markdown("**Review warnings**")
        for warning in readiness["warnings"]:
            st.markdown(f"- {warning}")
    st.caption(
        "The row, class, and event-group counts below are screening floors for this "
        "prototype. Passing them would not establish that a model is scientifically "
        "valid or suitable for warnings."
    )
    st.json(readiness["screening_floors"])

with st.form("disaster_probability_form"):
    target = st.selectbox(
        "Disaster to assess",
        ["Flood within the next 24 hours", "Cyclone", "Landslide", "Other"],
    )
    district = st.text_input("District or area", value="")
    st.subheader("Enter available conditions (optional)")
    col1, col2 = st.columns(2)
    with col1:
        rainfall_3day = st.number_input("Rainfall over previous 3 days (mm)", min_value=0.0, value=0.0)
        rainfall_24h = st.number_input("Forecast rainfall over 24 hours (mm)", min_value=0.0, value=0.0)
        moisture = st.number_input("Soil moisture (%)", min_value=0.0, max_value=100.0, value=0.0)
        slope = st.number_input("Slope angle (degrees)", min_value=0.0, max_value=90.0, value=0.0)
    with col2:
        river = st.number_input("River-level reading (m), if reference is known", min_value=0.0, value=0.0)
        river_reference_verified = st.checkbox("I have verified the river gauge reference")
        ipwv = st.number_input("Atmospheric moisture input (mm), if available", min_value=0.0, value=0.0)
        warning_status = st.text_input("Warning status from an official source (optional)", value="")
    submitted = st.form_submit_button("Review entered conditions", type="primary")

if submitted:
    st.subheader("Assessment status")
    if target != "Flood within the next 24 hours":
        st.info(f"No outcome-labeled dataset or validated model is available for {target.lower()}.")
    else:
        st.info(
            "No flood probability was calculated. These inputs are recorded here for "
            "discussion only; the five-row example dataset is not used to make a prediction."
        )
    st.write(f"**Area:** {district.strip() or 'Not specified'}")
    st.write(
        f"**Entered values:** 3-day rain {rainfall_3day:g} mm; 24-hour forecast "
        f"{rainfall_24h:g} mm; soil moisture {moisture:g}%; slope {slope:g}°; "
        f"river reading {river:g} m; atmospheric moisture {ipwv:g} mm."
    )
    if river > 0 and not river_reference_verified:
        st.warning("River reference is not confirmed; do not compare this reading with a threshold.")
    if warning_status.strip():
        st.write("**User-entered official warning status:**", warning_status.strip())
        st.caption("The app does not verify external warning status.")

st.caption(
    "A chronological, event-separated scikit-learn evaluation pipeline is prepared "
    "for future verified data, with a prior baseline and precision, recall, F1 and "
    "confusion-matrix reporting. It has not been run on real data because labels, "
    "event identifiers, temporal feature availability and sufficient observations "
    "are not available."
)

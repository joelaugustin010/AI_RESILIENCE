import streamlit as st
import pandas as pd

from src.evidence_fusion import SOURCE_REGISTRY, audit_multisource_evidence

from src.flood_model import (
    FEATURE_COLUMNS,
    audit_flood_dataset,
    load_flood_data,
)


st.header("Flood model readiness")
st.caption("Evidence first: this page deliberately withholds flood probabilities until the data and evaluation are scientifically defensible.")

try:
    data, metadata = load_flood_data()
    readiness = audit_flood_dataset(data, metadata)
except (FileNotFoundError, ValueError, OSError) as error:
    st.error(str(error))
    st.stop()

st.write(
    f"The repository currently contains {len(data)} unverified demonstration row(s). "
    "They are not verified historical outcomes and must not be treated as training evidence. "
    "The readiness audit below checks data integrity and blocks unsupported estimates."
)
st.error("CURRENT OUTPUT: No flood probability or operational warning is available from this model.")
st.caption("For real-time safety decisions, use official KSDMA/IMD/CWC guidance. This school project is not an emergency-warning service.")

fusion_readiness = audit_multisource_evidence([])
st.subheader("Multi-source evidence fusion")
st.write(
    "The system now inventories independent evidence families instead of relying on one dataset: "
    "rain-gauge observations, river-gauge observations, official hazard mapping, gridded rainfall/flood-frequency "
    "estimates, meteorological forecasts, and terrain/drainage evidence. Each source has its own quality, time, "
    "location, unit, and reuse checks."
)
st.error(
    "Fusion status: INSUFFICIENT_EVIDENCE. No numerical flood prediction is permitted because the current "
    "source records are not yet approved for automated fusion. This is an intentional fail-closed result, not a zero-risk result."
)
st.caption(
    f"Approved independent source families currently available for automated fusion: "
    f"{len(fusion_readiness['independent_source_families'])}. "
    "Required minimum: 3, with time-aligned rainfall/forecast evidence and an independent river/hazard context."
)
source_rows = [
    {
        "Evidence family": source.get("family", "unknown"),
        "Source": source.get("title", source_id),
        "Status": source.get("status", "not documented"),
        "Units": source.get("unit") or "Not applicable / not established",
        "Permitted use and limitation": source.get("use", ""),
        "Source URL": source.get("url", ""),
    }
    for source_id, source in SOURCE_REGISTRY.items()
]
with st.expander("Reviewed multi-source inventory", expanded=True):
    st.dataframe(
        pd.DataFrame(source_rows),
        hide_index=True,
        width="stretch",
        column_config={"Source URL": st.column_config.LinkColumn("Source URL")},
    )
    st.markdown("**Fusion gate blockers**")
    for blocker in fusion_readiness["blockers"]:
        st.markdown(f"- {blocker}")
    st.caption(fusion_readiness["interpretation"])

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
col1.metric("Unverified demo rows", len(data))
col2.metric("Demo rows marked flood", positive)
col3.metric("Demo rows marked no flood", negative)
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
    
    st.markdown("**Integrity and provenance**")
    integrity = readiness.get("integrity", {})

    if integrity.get("hash_verified"):
        st.success("Dataset SHA-256 matches its metadata.")
    elif integrity.get("raw_hash_matches") is False:
        st.error("Dataset SHA-256 does not match its metadata.")
    else:
        st.warning("Dataset SHA-256 has not been verified.")

    st.write(
        "Verified real observations are required before "
        "user-facing model evaluation is allowed."
    )

    st.markdown("**Feature coverage**")
    st.write(
        f"Usable required features: "
        f"{readiness['feature_count']} of "
        f"{len(FEATURE_COLUMNS)}."
    )

    st.write(
        f"Calendar dates covered: {readiness['distinct_dates']}"
    )

    st.write(
        f"Invalid timestamps: "
        f"{readiness['invalid_timestamps'] or 0}"
    )

    if readiness["missing_values"]:
        st.markdown("**Missing values by column**")
        st.json(readiness["missing_values"])

    st.markdown("**Integrity audit details**")
    st.json(readiness.get("metadata_status", {}))


st.subheader("Hypothetical scenario notes")
st.caption("Use this form only to document assumptions for discussion. It does not score risk, estimate probability, or verify an official warning.")
with st.form("disaster_probability_form"):
    target = st.selectbox(
        "Scenario type (discussion only)",
        ["River flooding", "Urban waterlogging", "Cyclone + flood", "Landslide", "Other"],
    )
    district = st.text_input("Area under discussion", value="") 
    st.subheader("Optional scenario inputs — not model features")
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
    submitted = st.form_submit_button("Review scenario assumptions", type="primary")

if submitted:
    st.subheader("Assessment status")
    st.info(
        f"Scenario type: {target}. No probability, risk score, or forecast was calculated. "
        "These entered values are discussion notes only and are not used to make a prediction."
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
    "Release gate: before a predictive model can be enabled, the project needs verified flood-event outcomes, defensible non-event periods, a validated station/catchment crosswalk, features available at the stated issue time, and event-separated chronological evaluation against simple baselines. "
    "A planned evaluation pipeline or passing software tests does not prove predictive skill."
)

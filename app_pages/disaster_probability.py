"""Four-hazard, input-based screening workspace for Ernakulam."""
from __future__ import annotations

import streamlit as st

from src.hazard_screening import HAZARD_CONFIG, LEVELS, assess_all_hazards

st.title("Disaster Risk Assessment")
st.caption("AI RESILIENCE · Ernakulam district, Kerala")

st.info(
    "Research prototype only. This page summarizes the conditions you enter; "
    "it does not issue official warnings or calculate validated hazard probabilities. "
    "Always follow current KSDMA, IMD and other competent-authority guidance."
)

mode = st.radio(
    "Choose assessment mode",
    ["Simple Mode", "Advanced Mode"],
    horizontal=True,
    help="Both modes use the same screening engine. Advanced Mode records scientific measurements as context; it does not silently convert unverified measurements into risk probabilities.",
)

st.subheader("Assessment location")
area = st.selectbox(
    "Select area",
    [
        "Ernakulam district (district-wide)",
        "Kochi",
        "Aluva",
        "Kalamassery",
        "Kakkanad",
        "Fort Kochi",
        "North Paravur",
        "Perumbavoor",
        "Muvattupuzha",
        "Kothamangalam",
        "Angamaly",
        "Tripunithura",
        "Other / not specified",
    ],
)
st.caption(
    "The location is recorded for context only. The assessment does not have verified "
    "neighbourhood-level coverage or automatically fetch local observations."
)

st.subheader("Enter current conditions")
st.write(
    "Complete the indicators you can assess. Leave anything unknown as "
    "'Not known / not checked'; missing information is never treated as zero."
)

all_inputs: dict[str, dict[str, str]] = {}
advanced_context: dict[str, dict[str, str]] = {}

with st.form("hazard_screening_form"):
    for hazard, config in HAZARD_CONFIG.items():
        with st.expander(f"{config['icon']} {hazard}", expanded=True):
            st.write(config["description"])
            all_inputs[hazard] = {}
            advanced_context[hazard] = {}
            for key, label, question in config["indicators"]:
                st.markdown(f"**{label}**")
                st.caption(question)
                selected = st.selectbox(
                    label,
                    list(LEVELS.keys()),
                    key=f"{hazard}_{key}_level",
                    label_visibility="collapsed",
                )
                all_inputs[hazard][key] = selected
                if mode == "Advanced Mode":
                    c1, c2 = st.columns(2)
                    with c1:
                        advanced_context[hazard][f"{key}_value"] = st.text_input(
                            f"{label}: measured value (optional)",
                            key=f"{hazard}_{key}_value",
                            placeholder="Enter source-reported value",
                        )
                    with c2:
                        advanced_context[hazard][f"{key}_unit"] = st.text_input(
                            f"{label}: unit / source (optional)",
                            key=f"{hazard}_{key}_unit",
                            placeholder="Unit · source · observation time",
                        )
    submitted = st.form_submit_button("Assess all four hazards", type="primary", use_container_width=True)

if submitted:
    try:
        results = assess_all_hazards(all_inputs)
    except ValueError as exc:
        st.error(f"Assessment could not be completed: {exc}")
    else:
        st.divider()
        st.header("Assessment results")
        st.caption(f"Selected area: {area} · Mode: {mode}")
        st.warning(
            "These are user-input screening summaries, not official alerts, "
            "validated risk scores or probabilities. No live data was fetched."
        )
        cols = st.columns(2)
        for index, (hazard, result) in enumerate(results.items()):
            with cols[index % 2]:
                with st.container(border=True):
                    st.markdown(f"### {HAZARD_CONFIG[hazard]['icon']} {hazard}")
                    st.subheader(result["category"])
                    st.write(result["explanation"])
                    m1, m2 = st.columns(2)
                    m1.metric("Indicators assessed", f"{result['assessed_count']}/{result['indicator_count']}")
                    m2.metric("Not checked", result["unknown_count"])
                    st.caption(f"Method: {result['method']}")
                    st.caption(f"Assessment period: {HAZARD_CONFIG[hazard]['period']}")
                    st.markdown("**Conditions entered**")
                    for key, label, _ in HAZARD_CONFIG[hazard]["indicators"]:
                        st.write(f"- {label}: {all_inputs[hazard][key]}")
                    if mode == "Advanced Mode":
                        supplied = [
                            (key, value) for key, value in advanced_context[hazard].items()
                            if value.strip()
                        ]
                        if supplied:
                            with st.expander("Advanced measurements entered"):
                                for key, value in supplied:
                                    st.write(f"- {key.replace('_', ' ').title()}: {value}")
        st.divider()
        st.subheader("What to do next")
        st.markdown(
            """
            - **Flood / waterlogging:** Check official rainfall and river bulletins; avoid flooded roads and follow local instructions.
            - **Cyclone / coastal storm:** Follow IMD and KSDMA bulletins; secure loose outdoor items and follow evacuation instructions if issued.
            - **Landslide:** If new ground movement or slope changes are noticed, move away from the slope and contact local authorities.
            - **Drought / water scarcity:** Follow local water-supply advisories and use water carefully; verify shortages with the responsible utility.
            """
        )
        st.caption(
            "A low-concern or incomplete result must never be used to delay emergency action. "
            "For emergencies, contact the appropriate local emergency services."
        )

st.divider()
with st.expander("Data sources and scientific limitations"):
    st.markdown(
        """
        **Live data status:** No IMD, CWC, NWIC or KSDMA live feed is connected by this page.

        **Model status:** No trained model is used here. The existing flood-model evaluation gate
        remains separate and unchanged; the current small, unverified example dataset is not
        promoted into a predictive model.

        **How to interpret results:** The screening labels summarize only the condition levels
        selected by the user. They are not calibrated risk classes, probabilities, return periods,
        or official warnings. Advanced measurements are displayed as user-entered context and
        are not automatically interpreted without verified units, timestamps, location matching
        and defensible hazard-specific thresholds.

        **Geographic scope:** Ernakulam district is the intended project scope. Selecting a
        sub-area does not imply validated local coverage.
        """
    )

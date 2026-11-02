"""Integrated Kochi cyclone, flood and compound-impact planning workspace."""
from __future__ import annotations

import json
from datetime import date

import streamlit as st

from src.compound_hazard_assessment import assess_compound_scenario


st.set_page_config(page_title="Cyclone + Flood | AI RESILIENCE", page_icon="🌧️", layout="wide")
st.title("Kochi Cyclone + Flood Resilience Workspace")
st.caption("One integrated workspace for rainfall, river flooding, cyclone exposure, compound pathways and service continuity.")

st.warning(
    "Research and planning prototype only. It does not issue warnings or calculate validated "
    "hazard probabilities, inundation depths, damage or casualties. Follow official IMD, CWC, "
    "KSDMA and local-authority instructions for real safety decisions."
)

st.markdown(
    """
    **How this workspace works:** record whether the case is hypothetical, historical or based on
    current observations; add source and timing; review flood and cyclone pathways together;
    then inspect consequences and preparedness actions for critical services. Blank or unknown
    inputs remain explicit data gaps.
    """
)

with st.form("compound_scenario_form"):
    st.subheader("1. Define the event")
    area = st.text_input("Study area", value="Kochi / Ernakulam")
    hazards = st.multiselect("Hazards in this scenario", ["Flood", "Cyclone"], default=["Flood", "Cyclone"])
    evidence_type = st.selectbox(
        "Evidence type",
        ["Hypothetical scenario", "Historical event", "Current sourced observations", "Official forecast product"],
    )
    col1, col2 = st.columns(2)
    with col1:
        period_start = st.date_input("Scenario period — start", value=date.today())
    with col2:
        period_end = st.date_input("Scenario period — end", value=date.today())
    observation_time = st.text_input(
        "Observation / bulletin issue time and timezone",
        placeholder="Example: 2026-11-02 10:00 IST",
    )
    evidence_source = st.text_input(
        "Source URL or document reference",
        placeholder="Official IMD / CWC / KSDMA source or project dataset record",
    )

    st.divider()
    st.subheader("2. Flood and rainfall evidence")
    st.caption("Leave unknown values blank. Do not enter an estimated value as an observation.")
    c1, c2 = st.columns(2)
    with c1:
        rainfall_mm = st.text_input("Rainfall (mm)", placeholder="Observed accumulation")
        rainfall_reference_mm = st.text_input("Documented rainfall reference (mm)", placeholder="Optional; same period and station")
    with c2:
        river_level_m = st.text_input("River level (m)", placeholder="Gauge observation")
        river_reference_level_m = st.text_input("Official gauge reference / danger level (m)", placeholder="Optional; same gauge and datum")

    st.divider()
    st.subheader("3. Cyclone and coastal evidence")
    c1, c2 = st.columns(2)
    with c1:
        cyclone_distance_km = st.text_input("Cyclone track distance from study area (km)", placeholder="Source-derived; specify track time")
        cyclone_wind_knots = st.text_input("Recorded / forecast wind speed (knots)", placeholder="Preserve source definition and time")
    with c2:
        coastal_water_notes = st.text_area(
            "Coastal water, tide, surge or outfall evidence",
            placeholder="Record source, timestamp, location and whether observed or forecast.",
        )

    st.divider()
    st.subheader("4. Services and infrastructure to review")
    services = st.multiselect(
        "Select exposed services",
        ["Hospitals", "Roads and bridges", "Electricity", "Drinking water", "Communications",
         "Shelters", "Schools", "Drainage", "Industrial facilities"],
        default=["Hospitals", "Roads and bridges", "Electricity", "Drainage"],
    )
    submitted = st.form_submit_button("Generate integrated scenario review", type="primary")

if submitted:
    try:
        result = assess_compound_scenario({
            "area": area,
            "hazards": hazards,
            "evidence_type": evidence_type,
            "period_start": period_start,
            "period_end": period_end,
            "observation_time": observation_time,
            "evidence_source": evidence_source,
            "rainfall_mm": rainfall_mm,
            "rainfall_reference_mm": rainfall_reference_mm,
            "river_level_m": river_level_m,
            "river_reference_level_m": river_reference_level_m,
            "cyclone_distance_km": cyclone_distance_km,
            "cyclone_wind_knots": cyclone_wind_knots,
            "coastal_water_notes": coastal_water_notes,
            "services": services,
        })
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.divider()
        st.subheader("Integrated assessment")
        st.info("Status: scenario review only — not a validated forecast.")
        if result["compound"]:
            st.success("Both hazards are selected. Compound interaction pathways are included in this review.")
        else:
            st.info("Only one hazard is selected; compound interaction analysis is not applicable.")

        st.markdown("#### Hazard pathways")
        for item in result["pathways"]:
            with st.expander(item["hazard"], expanded=True):
                st.write(item["pathway"])

        st.markdown("#### Supplied evidence and reference comparisons")
        st.json(result["reported_inputs"])
        if result["reference_comparisons"]:
            for item in result["reference_comparisons"]:
                st.write(
                    f"**{item['measure']}:** {item['result']} "
                    f"({item['observed']} compared with supplied reference {item['reference']})."
                )
                st.caption(item["warning"])
        else:
            st.caption("No threshold comparison was made. A reference level is never assumed or invented.")

        st.markdown("#### Possible consequences to investigate")
        for item in result["service_reviews"]:
            with st.expander(item["service"], expanded=True):
                for point in item["review_points"]:
                    st.write(f"- {point}")

        st.markdown("#### Action framework")
        before, during, after = st.columns(3)
        with before:
            st.markdown("**Before**")
            for action in result["actions"]["before"]:
                st.write(f"- {action}")
        with during:
            st.markdown("**During**")
            for action in result["actions"]["during"]:
                st.write(f"- {action}")
        with after:
            st.markdown("**After**")
            for action in result["actions"]["after"]:
                st.write(f"- {action}")

        st.markdown("#### Evidence still required")
        for gap in result["data_gaps"]:
            st.write(f"- {gap}")
        st.warning(result["interpretation"])
        st.download_button(
            "Download scenario review (JSON)",
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name="ai_resilience_compound_cyclone_flood_review.json",
            mime="application/json",
        )

st.divider()
st.caption(
    "Scientific boundary: historical cyclone tracks, event-only flood records, rainfall observations "
    "and river gauges are not interchangeable. Prediction requires aligned issue times, valid times, "
    "verified locations, independent outcomes and held-out event evaluation. The workspace keeps "
    "these requirements visible rather than manufacturing a risk score."
)

"""Kochi multi-hazard intelligence and evidence-readiness dashboard.

This page separates evidence-backed model outputs from planning status. It does
not invent probabilities, convert warning colours into probabilities, or issue
operational alerts. Each hazard requires its own validated data and evaluation.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.evidence_fusion import SOURCE_REGISTRY, audit_multisource_evidence
from src.flood_model import FEATURE_COLUMNS, audit_flood_dataset, load_flood_data



HAZARDS = {
    "Flood & urban waterlogging": {
        "icon": "🌊",
        "status": "Evidence review in progress",
        "stage": "DATA READINESS",
        "description": "River flooding, intense rainfall, drainage capacity, tidal influence and local waterlogging.",
        "inputs": [
            "Quality-controlled rainfall observations and forecasts",
            "Verified river and tide levels with known gauge datums",
            "Terrain, drainage and catchment connectivity",
            "Geocoded, independently verified flood-event and non-event records",
        ],
        "output": "No numerical flood probability is currently available.",
    },
    "Cyclone & severe storm": {
        "icon": "🌀",
        "status": "Not yet modelled",
        "stage": "SOURCE DISCOVERY",
        "description": "Cyclone track, forecast uncertainty, wind field, storm surge and extreme rainfall affecting the Kochi coast.",
        "inputs": [
            "Official IMD cyclone track and forecast issue/valid times",
            "IMD wind and rainfall forecast fields with spatial coverage",
            "INCOIS storm-surge and coastal water-level information",
            "Verified local impact records and exposure data",
        ],
        "output": "No cyclone probability or local impact estimate is available.",
    },
    "Landslide": {
        "icon": "⛰️",
        "status": "Not yet modelled",
        "stage": "SOURCE DISCOVERY",
        "description": "Slope-instability context for mapped locations; this hazard is not assumed to apply uniformly across low-lying Kochi.",
        "inputs": [
            "Authoritative landslide susceptibility and inventory maps",
            "Terrain slope, geology and land-cover layers",
            "Quality-controlled antecedent and forecast rainfall",
            "Verified landslide event locations and non-event periods",
        ],
        "output": "No landslide probability or susceptibility classification is available.",
    },
    "Drought & water scarcity": {
        "icon": "☀️",
        "status": "Not yet modelled",
        "stage": "SOURCE DISCOVERY",
        "description": "Seasonal rainfall deficit, groundwater and reservoir conditions, and drinking-water supply stress.",
        "inputs": [
            "Long-term rainfall climatology and quality-controlled observations",
            "Groundwater and reservoir monitoring with dated source records",
            "Water-supply demand and service-area information",
            "Documented drought definitions and historical impact records",
        ],
        "output": "No drought probability or water-scarcity forecast is available.",
    },
}

st.title("Kochi Multi-Hazard Intelligence")
st.caption("AI RESILIENCE · Kochi and Ernakulam, Kerala, India · Evidence-led assessment")

st.warning(
    "Research prototype only. This dashboard does not issue emergency warnings, "
    "replace official forecasts, or provide safety instructions. Follow KSDMA, "
    "IMD, CWC and other competent authorities for current conditions."
)

overview = st.columns(4)
for column, (name, details) in zip(overview, HAZARDS.items()):
    with column:
        st.metric(name, details["stage"])
        st.caption(details["status"])

st.divider()
st.subheader("Assessment workspace")
selected_area = st.selectbox(
    "Area under review",
    [
        "Kochi – city overview",
        "Fort Kochi",
        "Ernakulam",
        "Vyttila",
        "Edappally",
        "Kakkanad",
        "Kalamassery",
        "Eloor–Edayar",
        "Aluva",
        "Tripunithura",
    ],
)
st.caption(
    f"Selected area: {selected_area}. Area selection is a reporting filter only; "
    "it does not imply that location-specific hazard data or a model is available."
)

tabs = st.tabs(
    [
        "🌊 Flood",
        "🌀 Cyclone",
        "⛰️ Landslide",
        "☀️ Drought",
        "Evidence register",
    ]
)

# Flood tab: preserve and display the existing fail-closed dataset audit.
with tabs[0]:
    details = HAZARDS["Flood & urban waterlogging"]
    st.subheader("Flood and urban waterlogging")
    st.write(details["description"])
    try:
        flood_data, flood_metadata = load_flood_data()
        flood_readiness = audit_flood_dataset(flood_data, flood_metadata)
        fusion_readiness = audit_multisource_evidence([])
    except (FileNotFoundError, ValueError, OSError, KeyError) as error:
        st.error(f"Flood readiness audit could not be completed: {error}")
        flood_data = pd.DataFrame()
        flood_metadata = {}
        flood_readiness = None
        fusion_readiness = None

    if flood_readiness is not None:
        if flood_readiness["ready"]:
            st.success("Dataset passed the current prototype screening gates. This is not proof of forecast skill.")
        else:
            st.error("MODEL STATUS: BLOCKED — no flood probability has been calculated.")
        metrics = st.columns(4)
        metrics[0].metric("Candidate rows", flood_readiness["rows"])
        metrics[1].metric("Required features present", f'{flood_readiness["feature_count"]}/{len(FEATURE_COLUMNS)}')
        metrics[2].metric("Distinct dates", flood_readiness["distinct_dates"])
        metrics[3].metric("Exact duplicates", flood_readiness["exact_duplicates"])

        st.info(
            f'Dataset type: {flood_metadata.get("data_kind", "not documented")}. '
            "The repository's current five example rows are unverified demonstration data, "
            "not training evidence."
        )
        if flood_readiness["blockers"]:
            with st.expander("Flood model blockers", expanded=True):
                for blocker in flood_readiness["blockers"]:
                    st.markdown(f"- {blocker}")
        if flood_readiness["warnings"]:
            with st.expander("Flood data review warnings"):
                for warning in flood_readiness["warnings"]:
                    st.markdown(f"- {warning}")

        if fusion_readiness is not None:
            st.subheader("Multi-source evidence gate")
            st.error(
                f'Fusion status: {fusion_readiness["status"]}. '
                "No numerical prediction is permitted from the current source registry."
            )
            st.caption(fusion_readiness["interpretation"])
            for blocker in fusion_readiness["blockers"]:
                st.markdown(f"- {blocker}")

        with st.expander("Flood dataset screening details"):
            st.write(
                f'Date coverage: {flood_readiness["date_min"] or "unknown"} to '
                f'{flood_readiness["date_max"] or "unknown"}.'
            )
            st.write(f'Invalid timestamps: {flood_readiness["invalid_timestamps"] or 0}')
            st.json(flood_readiness["screening_floors"])
            if flood_readiness["missing_values"]:
                st.write("Missing values by column")
                st.json(flood_readiness["missing_values"])
            st.write("Dataset provenance sidecar")
            st.json(flood_metadata)

    st.markdown("**Required evidence before flood probability can be enabled**")
    for item in details["inputs"]:
        st.markdown(f"- {item}")

# Other hazard tabs are explicit readiness panels, not placeholder probability scores.
for tab, hazard_name in zip(tabs[1:4], list(HAZARDS.keys())[1:]):
    details = HAZARDS[hazard_name]
    with tab:
        st.subheader(f'{details["icon"]} {hazard_name}')
        st.write(details["description"])
        st.warning(f'{details["stage"]} · {details["status"]}')
        st.error(details["output"])
        st.markdown("**Required evidence and validation work**")
        for item in details["inputs"]:
            st.markdown(f"- {item}")
        st.caption(
            "This hazard has no trained or validated probability model in the repository. "
            "No risk score is generated from manually entered values."
        )

with tabs[4]:
    st.subheader("Reviewed flood evidence source register")
    st.caption(
        "This register records candidate sources and known limitations. A source appearing "
        "here does not mean it is connected, current, independently verified or approved for modelling."
    )
    source_rows = []
    for source_id, source in SOURCE_REGISTRY.items():
        source_rows.append(
            {
                "Source family": source.get("family", "not documented"),
                "Source": source.get("title", source_id),
                "Review status": source.get("status", "not documented"),
                "Unit": source.get("unit") or "Not established",
                "Permitted use / limitation": source.get("use", ""),
                "Reference": source.get("url", ""),
            }
        )
    st.dataframe(
        pd.DataFrame(source_rows),
        hide_index=True,
        width="stretch",
        column_config={"Reference": st.column_config.LinkColumn("Reference")},
    )

    st.subheader("Cross-hazard data plan")
    plan_rows = []
    for hazard_name, details in HAZARDS.items():
        plan_rows.append(
            {
                "Hazard": hazard_name,
                "Development stage": details["stage"],
                "Current status": details["status"],
                "Model output": details["output"],
            }
        )
    st.dataframe(pd.DataFrame(plan_rows), hide_index=True, width="stretch")

st.divider()
st.subheader("Scientific release rules")
st.markdown(
    """
    1. Each hazard must have its own documented event definition, predictors and forecast horizon.
    2. Every observation must retain its source, location, unit, timestamp, issue time and quality status.
    3. Related observations from the same event must not leak across training and evaluation.
    4. Models must be tested on later, independent events and compared with simple baselines.
    5. Probability calibration and uncertainty must be assessed before any probability is displayed.
    6. Missing, stale or unverified evidence must produce an unavailable result, never a zero-risk result.
    """
)
st.caption(
    "AI RESILIENCE is an educational research prototype. All hazard outputs remain "
    "unavailable until their respective evidence and validation gates are passed."
)

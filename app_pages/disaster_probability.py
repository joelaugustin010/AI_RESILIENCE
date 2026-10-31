
"""Kochi Multi-Hazard Intelligence Dashboard."""

import pandas as pd
import streamlit as st

from src.dataframe_display import display_dataframe

from src.evidence_fusion import (
    SOURCE_REGISTRY,
    audit_multisource_evidence,
)

from src.flood_model import (
    FEATURE_COLUMNS,
    audit_flood_dataset,
    load_flood_data,
)


# --------------------------------------------------
# PAGE HEADER
# --------------------------------------------------

st.title("🌍 KOCHI MULTI-HAZARD INTELLIGENCE")

st.caption(
    "AI RESILIENCE | Kochi, Kerala, India | "
    "Multi-Hazard Risk Assessment"
)

st.info(
    "Research prototype only. This application does not issue "
    "emergency warnings or replace official KSDMA, IMD or CWC guidance."
)


# --------------------------------------------------
# HAZARD CONFIGURATION
# --------------------------------------------------

HAZARDS = {
    "Flood & Urban Waterlogging": {
        "icon": "🌊",
        "status": "Evidence review in progress",
        "description": (
            "River flooding, intense rainfall, drainage capacity, "
            "tidal influence and urban waterlogging."
        ),
        "inputs": [
            "Rainfall observations and forecasts",
            "Verified river and tide levels",
            "Terrain and drainage information",
            "Historical flood-event records",
        ],
    },

    "Cyclone & Severe Storm": {
        "icon": "🌀",
        "status": "Data integration pending",
        "description": (
            "Cyclone tracks, wind conditions, storm surge "
            "and extreme rainfall affecting coastal Kochi."
        ),
        "inputs": [
            "Official IMD cyclone forecasts",
            "Wind speed and direction",
            "Storm-surge information",
            "Historical cyclone impact records",
        ],
    },

    "Landslide": {
        "icon": "⛰️",
        "status": "Data integration pending",
        "description": (
            "Slope instability and rainfall-related landslide "
            "susceptibility in relevant mapped areas."
        ),
        "inputs": [
            "Slope and elevation data",
            "Geological information",
            "Rainfall history",
            "Verified landslide inventories",
        ],
    },

    "Drought & Water Scarcity": {
        "icon": "☀️",
        "status": "Data integration pending",
        "description": (
            "Seasonal rainfall deficit, groundwater conditions "
            "and drinking-water supply stress."
        ),
        "inputs": [
            "Historical rainfall records",
            "Groundwater monitoring",
            "Reservoir levels",
            "Water demand and supply records",
        ],
    },
}


# --------------------------------------------------
# KOCHI LOCATION SELECTOR
# --------------------------------------------------

st.subheader("📍 Geographic Assessment")

area = st.selectbox(
    "Select assessment area",
    [
        "Kochi City",
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
    f"Selected area: {area}. This selection does not imply "
    "that validated local hazard data is available."
)


# --------------------------------------------------
# HAZARD OVERVIEW
# --------------------------------------------------

st.divider()
st.subheader("⚠️ Hazard Monitoring Overview")

columns = st.columns(4)

for column, (name, details) in zip(
    columns,
    HAZARDS.items(),
):
    with column:
        st.markdown(f"### {details['icon']}")
        st.markdown(f"**{name}**")
        st.caption(details["status"])


# --------------------------------------------------
# HAZARD TABS
# --------------------------------------------------

tabs = st.tabs(
    [
        "🌊 Flood",
        "🌀 Cyclone",
        "⛰️ Landslide",
        "☀️ Drought",
        "📚 Evidence Register",
    ]
)


# ==================================================
# 1. FLOOD ASSESSMENT
# ==================================================

with tabs[0]:

    st.header("🌊 Flood & Urban Waterlogging")

    st.write(
        HAZARDS["Flood & Urban Waterlogging"]["description"]
    )

    try:

        data, metadata = load_flood_data()

        readiness = audit_flood_dataset(
            data,
            metadata,
        )

        fusion = audit_multisource_evidence([])

        st.subheader("Flood Dataset Readiness")

        if readiness["ready"]:

            st.success(
                "Dataset passed the current prototype "
                "screening gates. This does not prove "
                "predictive accuracy."
            )

        else:

            st.error(
                "MODEL STATUS: BLOCKED. "
                "No flood probability has been calculated."
            )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Candidate records",
            readiness["rows"],
        )

        col2.metric(
            "Available features",
            f"{readiness['feature_count']}/{len(FEATURE_COLUMNS)}",
        )

        col3.metric(
            "Distinct dates",
            readiness["distinct_dates"],
        )

        col4.metric(
            "Duplicate records",
            readiness["exact_duplicates"],
        )

        st.info(
            "Dataset classification: "
            + str(metadata.get("data_kind", "Unknown"))
        )

        if readiness["blockers"]:

            with st.expander(
                "View dataset blockers",
                expanded=True,
            ):

                for item in readiness["blockers"]:
                    st.markdown(f"- {item}")

        if readiness["warnings"]:

            with st.expander("View warnings"):

                for item in readiness["warnings"]:
                    st.markdown(f"- {item}")

        st.subheader("Multi-Source Evidence Fusion")

        st.error(
            f"Fusion status: {fusion['status']}. "
            "Numerical flood predictions remain disabled."
        )

        st.caption(fusion["interpretation"])

        for item in fusion["blockers"]:
            st.markdown(f"- {item}")

        with st.expander("Dataset technical details"):

            st.write(
                "Date range:",
                readiness["date_min"],
                "to",
                readiness["date_max"],
            )

            st.write(
                "Invalid timestamps:",
                readiness["invalid_timestamps"],
            )

            st.json(readiness["screening_floors"])

            st.write("Dataset metadata")

            st.json(metadata)

    except (FileNotFoundError, ValueError, OSError, KeyError) as error:

        st.error(
            f"Flood readiness assessment unavailable: {error}"
        )


# ==================================================
# 2. CYCLONE ASSESSMENT
# ==================================================

with tabs[1]:

    st.header("🌀 Cyclone & Severe Storm Assessment")

    details = HAZARDS["Cyclone & Severe Storm"]

    st.write(details["description"])

    st.warning(
        "MODEL STATUS: NOT YET AVAILABLE"
    )

    st.write("Required datasets:")

    for item in details["inputs"]:
        st.markdown(f"- {item}")

    st.info(
        "Cyclone probability and local impact estimates "
        "will remain unavailable until official forecast "
        "products and independently verified historical "
        "impact records are integrated."
    )


# ==================================================
# 3. LANDSLIDE ASSESSMENT
# ==================================================

with tabs[2]:

    st.header("⛰️ Landslide Assessment")

    details = HAZARDS["Landslide"]

    st.write(details["description"])

    st.warning(
        "MODEL STATUS: NOT YET AVAILABLE"
    )

    st.write("Required datasets:")

    for item in details["inputs"]:
        st.markdown(f"- {item}")

    st.info(
        "A landslide model requires appropriate terrain, "
        "geology, rainfall and verified event data. "
        "It must not assume that every part of Kochi "
        "has the same landslide exposure."
    )


# ==================================================
# 4. DROUGHT ASSESSMENT
# ==================================================

with tabs[3]:

    st.header("☀️ Drought & Water Scarcity Assessment")

    details = HAZARDS["Drought & Water Scarcity"]

    st.write(details["description"])

    st.warning(
        "MODEL STATUS: NOT YET AVAILABLE"
    )

    st.write("Required datasets:")

    for item in details["inputs"]:
        st.markdown(f"- {item}")

    st.info(
        "Drought assessment requires long-term historical "
        "observations and a clearly defined drought "
        "measurement methodology."
    )


# ==================================================
# 5. EVIDENCE REGISTER
# ==================================================

with tabs[4]:

    st.header("📚 Evidence Source Register")

    st.write(
        "Reviewed candidate sources for the existing "
        "flood evidence assessment."
    )

    rows = []

    for source_id, source in SOURCE_REGISTRY.items():

        rows.append(
            {
                "Evidence family": source.get(
                    "family",
                    "Unknown",
                ),

                "Source": source.get(
                    "title",
                    source_id,
                ),

                "Status": source.get(
                    "status",
                    "Not documented",
                ),

                "Unit": source.get(
                    "unit",
                    "Not established",
                ),

                "Limitations": source.get(
                    "use",
                    "",
                ),

                "Reference": source.get(
                    "url",
                    "",
                ),
            }
        )

    display_dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Reference": st.column_config.LinkColumn(
                "Reference"
            )
        },
    )


# --------------------------------------------------
# SCIENTIFIC VALIDATION RULES
# --------------------------------------------------

st.divider()

st.header("🔬 Scientific Model Validation")

st.markdown(
    """
    Every hazard model must satisfy the following requirements:

    1. Verified and traceable source datasets.
    2. Correct geographic coverage for Kochi.
    3. Documented observation timestamps and units.
    4. Clearly defined hazard-event labels.
    5. Independent training and evaluation events.
    6. Comparison against simple baseline models.
    7. Probability calibration and uncertainty assessment.
    8. No leakage from information unavailable at prediction time.
    """
)

st.success(
    "Evidence-first architecture enabled. "
    "Unsupported probability estimates are blocked."
)

st.caption(
    "AI RESILIENCE | Kochi, Kerala, India | "
    "Educational research prototype"
)

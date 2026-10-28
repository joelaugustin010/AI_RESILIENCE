"""Source provenance, validation status and analysis readiness."""
from pathlib import Path

import pandas as pd
import streamlit as st

from src.ingestion_audit import DATA_STATUS_DEFINITIONS, build_ingestion_report


ROOT = Path(__file__).resolve().parents[1]


@st.cache_data(ttl=60)
def load_report() -> dict:
    return build_ingestion_report(ROOT)


report = load_report()
st.title("Data readiness")
st.caption(
    "This page checks local source integrity and reads the project catalogs. "
    "It does not download data or rewrite raw files."
)
st.caption(f"Last local validation: {report['validated_at_utc']}")

with st.expander("How validation statuses are used"):
    for status, meaning in DATA_STATUS_DEFINITIONS.items():
        st.markdown(f"**{status.capitalize()}** — {meaning}")

if report["catalog_errors"]:
    for error in report["catalog_errors"]:
        st.warning(error)

st.subheader("Recovered local research")
source_rows = [
    {
        "Dataset": item["name"],
        "Status": item["status"],
        "Publisher": item.get("publisher") or "Not recorded",
        "Period": item.get("reporting_period") or "Not established",
        "Coverage": item.get("geographic_coverage") or "Not established",
        "Units": item.get("units") or "Not stated",
        "CRS": item.get("crs") or "Not stated / not applicable",
        "File": item["storage_location"],
        "Integrity": "; ".join(f"{key}: {value}" for key, value in item["validation_checks"].items()),
    }
    for item in report["recovered_sources"]
]
if source_rows:
    st.dataframe(
        pd.DataFrame(source_rows).astype("string"),
        hide_index=True,
        width="stretch",
        alt="Local source files and the results of provenance and integrity checks",
    )
    for item in report["recovered_sources"]:
        if item["validation_errors"] or item["validation_warnings"]:
            with st.expander(f"{item['name']}: validation notes"):
                for error in item["validation_errors"]:
                    st.error(error)
                for warning in item["validation_warnings"]:
                    st.warning(warning)
                for limitation in item["known_limitations"]:
                    st.write(f"- {limitation}")
                if item["html_summary"]:
                    st.caption(
                        "HTML structure only: "
                        f"{item['html_summary'].get('table_count', 0)} table(s), "
                        f"{item['html_summary'].get('row_count', 0)} rows, "
                        f"{item['html_summary'].get('form_count', 0)} forms and "
                        f"{item['html_summary'].get('input_control_count', 0)} input controls. "
                        "The source HTML itself is not rendered."
                    )
else:
    st.info("No recovered raw source files are present in this checkout.")

st.subheader("Spatial catalog")
spatial_rows = [
    {
        "Dataset": item["name"],
        "Status": item["status"],
        "Geographic coverage": item.get("geographic_coverage") or "Not established",
        "CRS": item.get("crs") or "Not stated",
        "Local file": item.get("local_file") or "Not acquired",
        "Blocker": item.get("blocker") or "",
    }
    for item in report["spatial_catalog"]
]
if spatial_rows:
    st.dataframe(
        pd.DataFrame(spatial_rows).astype("string"),
        hide_index=True,
        width="stretch",
        alt="Spatial datasets, their evidence status, coverage, CRS and analysis blockers",
    )

st.subheader("Flood analysis")
flood = report["flood_analysis"]
st.warning(flood["conclusion"], title="Operational exposure analysis is unavailable")
st.caption(flood["available_hazard_context"])
for blocker in flood["blockers"]:
    st.write(f"- {blocker}")
st.markdown("**Evidence needed to reopen the analysis**")
for requirement in flood["next_evidence"]:
    st.write(f"- {requirement}")

st.subheader("Air quality and industrial attribution")
air = report["air_attribution"]
st.info(air["conclusion"], title="Historical summaries do not identify a factory source")
for blocker in air["blockers"]:
    st.write(f"- {blocker}")
st.caption(
    "The Air Pollution page remains the descriptive station-summary view. "
    "This readiness page does not create a second scoring or decision workflow."
)

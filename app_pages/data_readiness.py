"""Source provenance, validation status and analysis readiness."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dataframe_display import display_dataframe

from src.ingestion_audit import DATA_STATUS_DEFINITIONS, build_ingestion_report
from src.evidence_alternatives import ALTERNATIVE_EVIDENCE
from src.ui_theme import page_header


ROOT = Path(__file__).resolve().parents[1]
FLOOD_REFERENCE_PATH = ROOT / "data" / "reference" / "ksdma_ernakulam_flood_return_period_statistics_2022.json"
CLIMATE_BENCHMARK_REPORT = ROOT / "reports" / "kochi_climate_benchmarks.json"


@st.cache_data(ttl=60)
def load_report() -> dict:
    return build_ingestion_report(ROOT)


report = load_report()
page_header(
    "AI RESILIENCE · EVIDENCE & PROVENANCE",
    "Data readiness",
    "Check local source integrity, provenance and analysis readiness before relying on "
    "a model output. Nothing is downloaded and no raw file is rewritten.",
    meta=("Local source audit", "Provenance", "No downloads"),
    accent="cyan",
    key="data-readiness",
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
    display_dataframe(
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
    display_dataframe(
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

st.subheader("Official flood-risk context: Ernakulam district")
st.caption(
    "KSDMA's published district-level statistics are available as a source-traceable reference. "
    "They do not identify affected Kochi wards or validate the separate GeoTIFF pixel values."
)
try:
    flood_reference = json.loads(FLOOD_REFERENCE_PATH.read_text(encoding="utf-8"))
    scenario_label = st.radio(
        "Scenario",
        ["Historical", "RCP 8.5 climate scenario"],
        horizontal=True,
        key="ksdma_flood_reference_scenario",
    )
    scenario_key = "historical_scenario" if scenario_label == "Historical" else "rcp_8_5_scenario"
    flood_rows = flood_reference[scenario_key]
    flood_frame = pd.DataFrame([
        {
            "Return period (years)": row["return_period_years"],
            "Annual exceedance probability (%)": row["annual_exceedance_probability_percent"],
            "Area affected (km²)": row["area_affected_sq_km"],
            "Hospitals exposed (source count)": row["hospitals_exposed"],
            "Schools exposed (source count)": row["schools_exposed"],
        }
        for row in flood_rows
    ])
    display_dataframe(flood_frame, hide_index=True, width="stretch")
    st.caption(
        f"Publisher: {flood_reference['publisher']} · Published: {flood_reference['publication_date']} · "
        f"Coverage: {flood_reference['geographic_coverage']}."
    )
    st.markdown(f"**Method context:** {flood_reference['method_context']}")
    st.markdown(f"**Source:** {flood_reference['source_url']}")
    with st.expander("Interpretation and limitations"):
        st.write(flood_reference["return_period_definition"])
        for limitation in flood_reference["limitations"]:
            st.write(f"- {limitation}")
except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
    st.error(f"Could not load the official flood reference table: {exc}")

st.subheader("Air quality and industrial attribution")
air = report["air_attribution"]
st.info(air["conclusion"], title="Historical summaries do not identify a factory source")
for blocker in air["blockers"]:
    st.write(f"- {blocker}")
st.caption(
    "The Air Pollution page remains the descriptive station-summary view. "
    "This readiness page does not create a second scoring or decision workflow."
)

st.subheader("Alternative evidence routes")
st.caption(
    "These public catalogues and operational summaries offer additional evidence "
    "routes when complete local event panels are unavailable. A catalogue listing "
    "does not mean its underlying data have been downloaded, licensed, or validated."
)
for track_id, item in ALTERNATIVE_EVIDENCE.items():
    with st.expander(item["title"]):
        st.write(item["method"])
        st.markdown("**Can support**")
        for capability in item["supports"]:
            st.write(f"- {capability.replace('_', ' ')}")
        st.markdown("**Cannot establish by itself**")
        for limitation in item["does_not_support"]:
            st.write(f"- {limitation.replace('_', ' ')}")
        st.caption(f"Readiness: {item['status']}")
        for source in item["sources"]:
            st.markdown(
                f"- [{source['publisher']} — {source['title']}]({source['url']}) "
                f"· {source['access']}"
            )

st.subheader("Descriptive climate benchmarks: Kochi")
st.caption(
    "A separate, reproducible climatology for checking model context. It is not a "
    "forecast, official warning, IMD declaration, or attribution statement."
)
try:
    climate = json.loads(CLIMATE_BENCHMARK_REPORT.read_text(encoding="utf-8"))
    record = climate["record"]
    heat = climate["heat"]["thresholds"]
    rainfall = climate["rainfall"]
    spi = climate["spi_readiness"]
    metric_cols = st.columns(4)
    metric_cols[0].metric(
        "Record",
        f"{record['first_date']} to {record['last_date']}",
        help="Daily consecutive record; no gaps.",
    )
    metric_cols[1].metric("Complete years", record["complete_year_count"])
    metric_cols[2].metric(
        "Baseline 95th-percentile Tmax", f"{heat['baseline_p95_c']:.1f} °C"
    )
    metric_cols[3].metric(
        "Mean annual rainfall", f"{rainfall['annual_total_mm']['mean']:,.0f} mm"
    )
    st.caption(
        f"Full-record maximum Tmax {heat['full_record_max_c']:.1f} °C · "
        f"wettest day {rainfall['wettest_day']['precipitation_mm']:.1f} mm on "
        f"{rainfall['wettest_day']['date']} · "
        f"SPI-1 reference rule "
        f"{'met' if spi['meets_30_year_spi_reference_rule'] else 'not met'} "
        f"({spi['reference_years']} years). Baseline: "
        f"{climate['baseline_period']['start']} to {climate['baseline_period']['end']}."
    )
    st.info(
        "The input is Open-Meteo archived reanalysis at a model grid point, not a "
        "rain-gauge or thermometer observation. Heat and heavy-rain thresholds are "
        "transparent screening values, not official IMD criteria or local warnings.",
        title="Descriptive climatology, not a hazard prediction",
    )
    with st.expander("Climate benchmark source, portability and limitations"):
        st.markdown(
            f"**Provider:** {climate['source']['provider']}  \n"
            f"**Source:** {climate['source']['source_url']}  \n"
            f"**File:** `{climate['source']['file']}`  \n"
            f"**SHA-256:** `{climate['source']['sha256']}`  \n"
            f"**Licence:** {climate['source']['licence']}"
        )
        for limitation in climate["limitations"]:
            st.write(f"- {limitation}")
        st.caption(
            "Reproduce with `python scripts/build_climate_benchmarks.py` after "
            "placing the documented local reanalysis snapshot in "
            "`data/external/hazards/raw/weather/`."
        )
except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
    st.info(
        "Insufficient evidence: the descriptive climate-benchmark report could not "
        f"be loaded ({exc}). No climate value is shown."
    )

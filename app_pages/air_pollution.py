"""Pollution-source evidence status for Kochi and Ernakulam."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data" / "reference" / "air_quality_acquisition.json"


def load_source_register() -> dict:
    """Load the reviewed source-status record; no sample measurement is used."""
    with REGISTER.open(encoding="utf-8") as source_file:
        return json.load(source_file)


st.header("Which factory is responsible for today's air pollution?")
st.warning(
    "A source cannot currently be identified from this project. There is no acquired, "
    "verified pollutant-specific observation series joined to monitor locations, "
    "weather, and verified facility emissions."
)
st.caption(
    "AQI is an index, not a chemical fingerprint. A high value, nearby factory, or "
    "wind direction alone does not establish which source caused a reading."
)

try:
    register = load_source_register()
except (OSError, json.JSONDecodeError) as error:
    st.error(f"Pollution data-source status could not be loaded: {error}")
    st.stop()

st.subheader("Verified monitoring-network context")
stations = pd.DataFrame(register["kspcb_namp_ernakulam_stations"])
st.write(
    "KSPCB lists the following Ernakulam stations in its manual NAMP network. "
    "This is station-list context, not a set of measurements or mapped coordinates."
)
st.dataframe(stations, hide_index=True, width="stretch")
st.caption(
    "KSPCB describes manual NAMP/SAMP observations on 8–11 days per month, with "
    "different sampling durations by pollutant. Its IPAM page describes CAAQMS as "
    "24×7 and lists PM10, PM2.5, SO₂, CO, NO, NO₂, NOx, NH₃ and O₃; the page reviewed "
    "did not expose a downloadable, dated Kochi observation table."
)

with st.expander("Acquisition status and evidence"):
    for item in register["sources"]:
        st.markdown(f"**[{item['publisher']}]({item['url']})** — {item['status']}")
        st.write(item["evidence"])
        st.caption(f"Reuse: {item['reuse_status']} | Reviewed: {item['reviewed_on']}")

st.subheader("What is missing for a defensible source investigation")
st.markdown(
    "- Time-stamped, pollutant-specific measurements (with units, averaging period, and quality flags).\n"
    "- Verified monitoring-station locations and stable coverage metadata.\n"
    "- Time-aligned wind speed/direction and other relevant meteorology.\n"
    "- Verified factory locations and facility-specific emissions/consent records.\n"
    "- Alternative-source and transport analysis before assessing possible associations."
)

st.info(
    "The legacy `data/raw/air_pollution_data.csv` is a small illustrative sample, not an "
    "observational dataset. It contains an out-of-state facility and undocumented values; "
    "this page intentionally does not rank or analyze those rows."
)
st.markdown(
    "**Next safe step:** request a dated station-level export (including pollutant "
    "concentrations, units, completeness/quality flags, station coordinates, and reuse "
    "terms) from KSPCB/CPCB, then obtain aligned meteorology and verified facility records."
)

"""Evidence availability for unresolved disaster-model data requirements.

This registry distinguishes public aggregate/event inventories, licensed data,
simulation outputs and missing asset-level observations. It never marks a
source as training-ready merely because a catalogue or report exists.
"""
from __future__ import annotations

from typing import Any


EVIDENCE_TRACKS: dict[str, dict[str, Any]] = {
    "flood_impacts": {
        "title": "Flood inundation and impacts",
        "status": "PARTIAL_PUBLIC_EVENT_AND_DISTRICT_IMPACT_DATA",
        "available": (
            "India Flood Inventory v4 (1967–2023) provides event/district records, "
            "district flooded-area and impact tables. USGS GFID provides global "
            "geocoded event-impact records."
        ),
        "gap": (
            "Neither source is a local, time-aligned Kochi inundation-depth/duration "
            "dataset. GFID coordinates are representative event locations, not flood "
            "footprints; impact definitions vary by source."
        ),
        "next": (
            "Acquire and quality-check event-level local inundation polygons/depths, "
            "rainfall, canal/river levels with datum, tide/outfall and drainage state; "
            "hold out entire events and geographies."
        ),
        "sources": [
            "https://zenodo.org/records/16994648",
            "https://catalog.data.gov/dataset/the-global-flood-impacts-database-gfid",
        ],
    },
    "landslide": {
        "title": "Landslide event inventory and background",
        "status": "EVENT_INVENTORIES_IDENTIFIED_BACKGROUND_NOT_VALIDATED",
        "available": (
            "A Kerala 2018 monsoon inventory reports 4,728 mapped landslides. NRSC/ISRO "
            "describes an approximately 80,000-landslide inventory across India "
            "(1998–2022), including seasonal, event-based and route-wise records."
        ),
        "gap": (
            "Event inventories are presence records, not verified non-event samples. "
            "NRSC data access/reuse conditions, geometry, completeness and spatial "
            "resolution require review; event reporting is spatially biased."
        ),
        "next": (
            "Obtain authorized inventory geometries and metadata; align DEM, slope, "
            "geology, soil, land cover, drainage and antecedent rainfall; define "
            "surveyed non-event periods/areas and spatially blocked evaluation."
        ),
        "sources": [
            "https://research.utwente.nl/en/datasets/landslide-inventory-of-the-2018-monsoon-rainfall-in-kerala-india/",
            "https://www.nrsc.gov.in/nrscnew/resources_atlas_landslide.php",
        ],
    },
    "industrial": {
        "title": "Industrial incident and non-incident records",
        "status": "NO_OPEN_FACILITY_LEVEL_TRAINING_PANEL_VERIFIED",
        "available": (
            "DGFASLI describes statutory major-accident reporting and annual safety "
            "reporting duties; Labour Bureau publishes annual aggregate factory "
            "statistics. These are governance/aggregate sources, not a facility-time "
            "incident panel."
        ),
        "gap": (
            "No open, provenance-verified facility-level dataset was identified with "
            "incident and non-incident operating periods, process/release variables, "
            "inspection history and monitoring outcomes."
        ),
        "next": (
            "Use only lawfully shared, de-identified records approved by the data "
            "owner; retain process/facility context, near misses, exposure time and "
            "verified non-event periods. Keep process-safety engineering primary."
        ),
        "sources": [
            "https://dgfasli.gov.in/en/faq",
            "https://labourbureau.gov.in/annual-report-on-statistics-of-factories",
        ],
    },
    "infrastructure": {
        "title": "Infrastructure condition, outages and restoration",
        "status": "AGGREGATE_RELIABILITY_METRICS_ONLY",
        "available": (
            "KSEB's public KPI page has reported SAIFI/SAIDI and related reliability "
            "indicators. These aggregate service metrics do not identify individual "
            "asset failures or restoration episodes."
        ),
        "gap": (
            "No open Kochi asset-level panel was verified with asset IDs, condition, "
            "inspection/maintenance, failure onset, outage footprint and restoration "
            "timestamps. US EAGLE-I county outage data are not a substitute for Kerala."
        ),
        "next": (
            "Seek de-identified feeder/asset event histories, network topology, "
            "maintenance and restoration logs from the responsible utility; preserve "
            "planned/force-majeure exclusions and outage definitions."
        ),
        "sources": [
            "https://hris.kseb.in/kpi/index.html",
            "https://impact.ornl.gov/en/datasets/eagle-i-power-outage-data-2014-2022/",
        ],
    },
    "intervention": {
        "title": "Real-world intervention effectiveness",
        "status": "NO_VERIFIED_PHYSICAL_INTERVENTION_EPISODES",
        "available": (
            "A Bangladesh randomized flood anticipatory-cash evaluation is a licensed "
            "candidate for a narrowly defined assistance-timing effect. The Geul archive "
            "contains simulated counterfactuals for specified measures and remains a "
            "separate simulation-only track."
        ),
        "gap": (
            "No authorized, compatible episode table is present. Cash-transfer timing "
            "is not a physical drainage/embankment intervention; Geul simulation outputs "
            "are not observed outcomes and are not Kochi-calibrated."
        ),
        "next": (
            "Keep the empirical model withheld until assignment, treatment, pre-treatment "
            "covariates and measured outcomes are lawfully available and linked. Train "
            "simulation surrogates separately with event/spatial holdouts."
        ),
        "sources": [
            "https://microdata.worldbank.org/catalog/8009",
            "https://zenodo.org/records/15488420",
        ],
    },
    "kochi_causal": {
        "title": "Kochi Operation Breakthrough causal evaluation",
        "status": "DOCUMENTED_PROJECT_NO_LINKED_SITE_EVENT_PANEL",
        "available": (
            "KSDMA documents the 21 October 2019 flood and Operation Breakthrough. "
            "The Irrigation Department report documents Phase I/II works and reports "
            "relief narratively; the 2024 government order records Phase III technical "
            "sanction near High Court Junction."
        ),
        "gap": (
            "No linked site-by-event panel with verified intervention commissioning, "
            "repeated inundation/damage outcomes, comparison locations and rainfall/tide/"
            "river covariates is available in the repository."
        ),
        "next": (
            "Obtain work orders, as-built footprints, commissioning and maintenance "
            "records; combine with event-level rainfall/tide/gauge and measured "
            "inundation/damage at treated and comparable not-yet-treated sites. "
            "Audit pre-trends, concurrent works and spillovers before estimation."
        ),
        "sources": [
            "https://sdma.kerala.gov.in/kochi-2019/",
            "https://www.irrigation.kerala.gov.in/sites/default/files/2021-08/kochiflood.pdf",
            "https://document.kerala.gov.in/documents/governmentorders/govtorder1707202414%3A45%3A51.pdf",
        ],
    },
}


HAZARD_TRACKS: dict[str, tuple[str, ...]] = {
    "Flood": ("flood_impacts", "kochi_causal", "intervention"),
    "Landslide": ("landslide",),
    "Industrial incident": ("industrial",),
    "Infrastructure failure": ("infrastructure", "intervention"),
    "Compound: cyclone + flood": ("flood_impacts", "kochi_causal", "intervention"),
    "Compound: heavy rainfall + drainage failure": (
        "flood_impacts", "infrastructure", "kochi_causal", "intervention"
    ),
}


def evidence_readiness_for_hazards(hazards: list[str] | tuple[str, ...]) -> list[dict[str, Any]]:
    """Return deduplicated, deterministic source-readiness tracks for selected hazards."""
    selected: list[str] = []
    for hazard in hazards:
        for track_id in HAZARD_TRACKS.get(str(hazard), ()):
            if track_id not in selected:
                selected.append(track_id)
    return [
        {"track_id": track_id, **EVIDENCE_TRACKS[track_id]}
        for track_id in selected
    ]


__all__ = ["EVIDENCE_TRACKS", "HAZARD_TRACKS", "evidence_readiness_for_hazards"]

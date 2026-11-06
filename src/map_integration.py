"""Transfer evidence-gated workflow context to the interactive Kochi map."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.hazard_registry import WORKFLOW_HAZARDS, components_for, is_workflow_hazard


MAP_CONTEXT_KEY = "kochimap_assessment_context"

# Layer availability is deliberately explicit.  None of the ten workflow
# hazards currently has a validated, licence-cleared local hazard footprint in
# this repository, so the map must say so rather than implying that a base map
# or a land-cover image is a hazard layer.
_HAZARD_FOOTPRINT_STATUS: dict[str, tuple[str, str]] = {
    "Flood": (
        "Modelled scenario context available",
        "The JRC GloFAS RP100 preview is displayed as a modelled 100-year river-flood depth scenario under ODbL 1.0 / CC BY 4.0 attribution. It is not observed flooding, a forecast, or an official warning.",
    ),
    "Cyclone": (
        "Not available",
        "No validated cyclone track, wind-field, or storm-surge footprint has been acquired and QA-approved.",
    ),
    "Earthquake": (
        "Not available",
        "No validated local ground-shaking or fault footprint has been acquired and QA-approved.",
    ),
    "Landslide": (
        "Not available",
        "No validated local landslide inventory or susceptibility footprint has been acquired and QA-approved.",
    ),
    "Heatwave": (
        "Not available",
        "No validated local heat-exposure or temperature footprint has been acquired and QA-approved.",
    ),
    "Drought": (
        "Not available",
        "No validated local drought-index or water-availability footprint has been acquired and QA-approved.",
    ),
    "Industrial incident": (
        "Not available",
        "No validated facility release, plume, or downwind-exposure footprint has been acquired and QA-approved.",
    ),
    "Infrastructure failure": (
        "Not available",
        "No validated network outage or service-area footprint has been acquired and QA-approved.",
    ),
    "Compound: cyclone + flood": (
        "Modelled flood component only",
        "Only the JRC RP100 modelled flood scenario is displayable. No validated cyclone track, wind-field, or storm-surge footprint is approved, so this is not a compound hazard footprint.",
    ),
    "Compound: heavy rainfall + drainage failure": (
        "Modelled flood component only",
        "Only the JRC RP100 modelled flood scenario is displayable. No validated drainage-network layer or drainage-capacity footprint is approved, so this is not a compound hazard footprint.",
    ),
}

_LANDCOVER_CONTEXT_HAZARDS = {
    "Flood",
    "Cyclone",
    "Landslide",
    "Heatwave",
    "Drought",
    "Compound: cyclone + flood",
    "Compound: heavy rainfall + drainage failure",
}


def hazard_has_flood_component(active_hazard: str | None) -> bool:
    """Whether the selected registered scenario contains a flood component."""
    return bool(active_hazard and "Flood" in components_for(active_hazard))


_KSDMA_HAZARD_REFERENCES: dict[str, list[dict[str, str]]] = {
    "Flood": [
        {
            "title": "KSDMA Ernakulam historical flood probability map (PDF)",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf",
            "scope": "District-level historical model map; not a live forecast or ward-validated footprint.",
        },
        {
            "title": "KSDMA historical flood return-probability rasters (10/25/50-year ZIP)",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/1.-Flood-Return-Probability-Historical-10-25-50-years.zip",
            "scope": "Raster semantics and dataset-specific reuse terms remain unresolved; not rendered or used for exposure.",
        },
    ],
    "Landslide": [
        {
            "title": "KSDMA / GSI 2022 Ernakulam landslide-susceptibility shapefile (ZIP)",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip",
            "scope": "Official district shapefile link; archive schema, CRS, licence and geometry still require local QA before map ingestion.",
        },
        {
            "title": "KSDMA Ernakulam landslide-susceptibility district map (PDF)",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2025/06/Landslide_Susceptibility_Zones_Districts_FINAL.pdf",
            "scope": "Reference map only; not a validated ward-level Kochi overlay.",
        },
    ],
    "Drought": [
        {
            "title": "KSDMA drought-prone area map (Kerala; data period 2012–2013)",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2018/10/KL-Drought-1.jpg",
            "scope": "Old state-level seasonal susceptibility reference; not current local water-availability evidence.",
        },
    ],
    "Earthquake": [
        {
            "title": "KSDMA earthquake / tremor events and seismographs map",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2018/10/Map-Earthquake-incidents.jpg",
            "scope": "Historical event/seismograph reference (map states 2000–2016); not a ground-shaking forecast or local susceptibility model.",
        },
    ],
    "Industrial incident": [
        {
            "title": "KSDMA major industrial accident hazard susceptibility map",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2018/10/Map-Major-Industrial-Accident-Hazard-Zones.jpg",
            "scope": "State-level reference only; does not establish current facility-specific release or downwind exposure zones.",
        },
    ],
    "Cyclone": [
        {
            "title": "KSDMA coastal hazard susceptibility map",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2018/10/Map-Coastal-Hazard-Susceptibility.jpg",
            "scope": "Coastal erosion / storm-surge / tsunami reference; not a cyclone track, wind-field or event-specific surge footprint.",
        },
    ],
    "Compound: cyclone + flood": [
        {
            "title": "KSDMA Ernakulam historical flood probability map (PDF)",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf",
            "scope": "Flood component only; no validated cyclone track, wind-field or storm-surge overlay is available.",
        },
    ],
    "Compound: heavy rainfall + drainage failure": [
        {
            "title": "KSDMA Ernakulam historical flood probability map (PDF)",
            "url": "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf",
            "scope": "Flood-context reference only; no validated municipal drainage inventory or drainage-capacity footprint is available.",
        },
    ],
}


def hazard_map_references(active_hazard: str | None) -> list[dict[str, str]]:
    """Return official reference products without promoting PDFs/portals to GIS layers."""
    if not active_hazard or not is_workflow_hazard(active_hazard):
        return []

    references = [dict(item) for item in _KSDMA_HAZARD_REFERENCES.get(active_hazard, [])]
    references.append(
        {
            "title": "Kerala Fire and Rescue Services — Ernakulam multi-hazard map (PDF)",
            "url": "https://fire.kerala.gov.in/wp-content/uploads/2021/11/7_Multi_hazard_Map_of_Ernakulam.pdf",
            "scope": (
                "Official district-level multi-hazard reference. PDF only: not a georeferenced "
                "Kochi GIS overlay, current event forecast, or ward-level exposure layer."
            ),
        }
    )
    if active_hazard == "Heatwave":
        references.append(
            {
                "title": "KSDMA / C-DIT disaster portal — hazard map index (includes Heat)",
                "url": "https://sdma.cditproject.org/",
                "scope": (
                    "State-level portal reference only. The heat map is not independently "
                    "validated here and is not a local temperature/exposure GIS layer."
                ),
            }
        )
    return references


def hazard_layer_availability(active_hazard: str | None = None) -> list[dict[str, Any]]:
    """Return an explicit availability row for every workflow hazard.

    The function is pure so the map page and regression tests share exactly the
    same statements.  It never promotes a context layer to a hazard footprint.
    """
    rows: list[dict[str, Any]] = []
    for hazard in WORKFLOW_HAZARDS:
        if hazard in _HAZARD_FOOTPRINT_STATUS:
            status, reason = _HAZARD_FOOTPRINT_STATUS[hazard]
        else:
            status, reason = (
                "Not available",
                "No validated hazard footprint is registered for this hazard.",
            )
        rows.append(
            {
                "Hazard": hazard,
                "Selected": hazard == active_hazard,
                "Hazard footprint / modelled context": status,
                "Context layer": (
                    "ESA WorldCover 2021 land-cover context"
                    if hazard in _LANDCOVER_CONTEXT_HAZARDS
                    else "None"
                ),
                "Footprint scope / limitation": reason,
                "Components": ", ".join(components_for(hazard)),
            }
        )
    return rows


_MAP_INPUT_FIELDS = (
    "source_and_time",
    "rainfall_mm",
    "rainfall_period",
    "river_level_m",
    "river_station",
    "wind_speed_kmh",
    "temperature_c",
    "relative_humidity_percent",
    "earthquake_mmi",
    "antecedent_rainfall_mm",
    "catchment_area_ha",
    "runoff_coefficient",
    "drainage_capacity_m3_s",
    "drainage_status",
    "infrastructure_status",
    "pollutant_name",
    "pollutant_concentration",
    "pollutant_unit",
    "pollutant_averaging_period",
    "failed_service",
    "affected_population",
    "assets",
    "condition_notes",
)


def build_map_context(
    inputs: Mapping[str, Any],
    assessment: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build a compact, explicitly user-supplied scenario context for map navigation."""
    if not isinstance(inputs, Mapping):
        raise ValueError("Map context inputs must be a mapping.")

    context: dict[str, Any] = {
        "hazard": inputs.get("hazard", "Not supplied"),
        "location": inputs.get("location", "Not supplied"),
        "input_classification": inputs.get("input_classification", "Unknown / unverified"),
        "conditions": {
            field: inputs[field]
            for field in _MAP_INPUT_FIELDS
            if field in inputs and inputs[field] not in (None, "", [], "Not supplied")
        },
    }
    if assessment is not None:
        context["assessment"] = {
            key: assessment[key]
            for key in (
                "assessment_type",
                "result_status",
                "model_id",
                "methodology",
                "hazard_assessment",
                "potential_consequences",
                "recommendations",
                "validation",
            )
            if key in assessment
        }
    return context


def selected_feature_properties(selection: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Extract picked GeoJSON properties while ignoring geometry and unknown shapes."""
    if not isinstance(selection, Mapping):
        return []
    selection_data = selection.get("selection", selection)
    if not isinstance(selection_data, Mapping):
        return []
    objects = selection_data.get("objects", {})
    if not isinstance(objects, Mapping):
        return []

    properties: list[dict[str, Any]] = []
    for selected_objects in objects.values():
        if not isinstance(selected_objects, list):
            continue
        for selected in selected_objects:
            if not isinstance(selected, Mapping):
                continue
            feature_properties = selected.get("properties", selected)
            if isinstance(feature_properties, Mapping):
                properties.append(
                    {
                        str(key): value
                        for key, value in feature_properties.items()
                        if key != "geometry"
                        and isinstance(value, (str, int, float, bool, type(None)))
                    }
                )
    return properties

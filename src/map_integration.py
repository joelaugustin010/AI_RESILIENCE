"""Transfer evidence-gated workflow context to the interactive Kochi map."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.hazard_registry import WORKFLOW_HAZARDS, components_for


MAP_CONTEXT_KEY = "kochimap_assessment_context"

# Layer availability is deliberately explicit.  None of the ten workflow
# hazards currently has a validated, licence-cleared local hazard footprint in
# this repository, so the map must say so rather than implying that a base map
# or a land-cover image is a hazard layer.
_HAZARD_FOOTPRINT_STATUS: dict[str, tuple[str, str]] = {
    "Flood": (
        "Not displayed",
        "The JRC RP100 preview is withheld pending licence clarification, and the KSDMA raster's valid-pixel meaning and units are undocumented.",
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
        "Not displayed",
        "A compound view needs both a validated cyclone footprint and a validated flood footprint; neither is approved.",
    ),
    "Compound: heavy rainfall + drainage failure": (
        "Not displayed",
        "A compound view needs a validated flood footprint and a validated drainage-network layer; neither is approved.",
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
                "Validated hazard footprint": status,
                "Context layer": (
                    "ESA WorldCover 2021 land-cover context"
                    if hazard in _LANDCOVER_CONTEXT_HAZARDS
                    else "None"
                ),
                "Why no footprint is shown": reason,
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

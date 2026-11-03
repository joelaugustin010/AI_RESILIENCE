"""Transfer evidence-gated workflow context to the interactive Kochi map."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


MAP_CONTEXT_KEY = "kochimap_assessment_context"

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

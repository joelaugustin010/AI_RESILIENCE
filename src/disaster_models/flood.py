"""Flood assessment using measured/scenario rainfall and rational-method runoff."""

from __future__ import annotations

from typing import Any

from src.disaster_models.common import (
    build_assessment,
    numeric_input,
    rainfall_intensity,
    recommendation,
    validate_top_level,
)

SOURCES = [
    {
        "title": "FHWA, Urban Drainage Design Manual (HEC-22)",
        "url": "https://www.fhwa.dot.gov/engineering/hydraulics/pubs/10009/10009.pdf",
        "role": "Established urban runoff and drainage design methods; rational method limitations apply.",
    },
    {
        "title": "UNDRR, Disaster risk terminology",
        "url": "https://www.undrr.org/terminology/disaster-risk",
        "role": "Hazard, exposure, vulnerability, and capacity remain distinct dimensions.",
    },
]


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    rain = rainfall_intensity(inputs)
    area = numeric_input(inputs, "catchment_area_ha", minimum=0.0001, maximum=1_000_000)
    runoff = numeric_input(inputs, "runoff_coefficient", minimum=0, maximum=1)
    estimate = None
    if rain["value"] is not None and area is not None and runoff is not None:
        estimate = 0.002777777777777778 * runoff * rain["value"] * area
    river_level = numeric_input(inputs, "river_level_m")
    indicators = {
        "rainfall_depth_and_period": rain,
        "source_reported_river_level_m": {
            "value": river_level,
            "status": "recorded_without_datum_or_threshold" if river_level is not None else "unavailable",
        },
        "rational_method_peak_runoff_m3_s": {
            "value": estimate,
            "status": "scenario_estimate" if estimate is not None else "unavailable",
            "equation": "Q = 0.00278 C i A, with i in mm/h and A in hectares.",
            "limitations": "Small catchment, uniform design rainfall and a suitable time-of-concentration intensity are required; this app does not verify them.",
        },
    }
    return build_assessment(
        hazard="Flood",
        model_id="flood_rational_method_screening",
        method="Rainfall descriptor plus optional Rational Method peak runoff screening",
        scientific_basis="Q = C i A with unit conversion (0.00278 for mm/h and hectares); it estimates peak runoff under restrictive catchment/design assumptions, not inundation depth or flood probability.",
        inputs=inputs,
        result_status="physical_indicator_only_not_local_flood_severity",
        hazard_assessment={
            "severity": "Not classified; no local flood threshold, compatible terrain/drainage model, or verified flood extent is available.",
            "indicators": indicators,
        },
        calculation={
            "rainfall_intensity": "Total user-supplied depth divided by explicitly selected duration; mean intensity only.",
            "runoff": "Calculated only when rainfall duration, catchment area, and runoff coefficient are all supplied.",
        },
        consequence_pathways=[
            "Runoff may exceed drainage conveyance only when catchment and verified design-capacity evidence are available.",
            "Flood depth, duration, road access, facility impacts, and population exposure are unknown.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Assess catchment-scale storage and drainage improvements only after a surveyed hydraulic study identifies a specific capacity or conveyance deficit.",
                    "Long-term flood risk-reduction planning is requested.",
                    "FHWA HEC-22 methods, verified catchments, surveyed drainage, design rainfall and observed flood records.",
                    category="prevention",
                    limitations="This screening does not establish a local drainage deficiency or justify a specific construction project.",
                ),
                recommendation("before", "Check rainfall inputs, drainage assets, outfalls and receiving-water constraints.", "A flood scenario is being reviewed.", "Local authority drainage inventory, surveyed elevations, maintenance records and design capacity."),
            ],
            "during": [recommendation("during", "Use official warnings and incident-command instructions; report observed inundation and blocked access to authorities.", "Flooding or official warning is reported.", "Current KSDMA/IMD/local-authority instructions; do not infer safe routes from this model.")],
            "after": [recommendation("after", "Record high-water marks, duration, service outages and damage with time/location references before cleanup changes evidence.", "Floodwater has receded and assessment is authorized.", "Independent field observations and asset-owner inspection.")],
        },
        uncertainty=[
            "Rainfall input provenance and averaging interval are not independently checked.",
            "River gauge datum and warning thresholds are unresolved; the reading is not threshold-classified.",
            "Rational-method inputs may not represent a local design storm or catchment.",
            "Spatial exposure and consequences are not calculated.",
        ],
        data_gaps=[
            "Verified flood footprint/depth and local hydraulic model.",
            "Catchment boundary, time of concentration, drainage design capacity, tide/backwater conditions and asset locations.",
            "Independently reviewed flood-impact observations for validation.",
        ],
        sources=SOURCES,
    )

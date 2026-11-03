"""Earthquake assessment accepts reported MMI but does not estimate shaking."""

from __future__ import annotations

from typing import Any

from src.disaster_models.common import build_assessment, numeric_input, recommendation, validate_top_level

SOURCES = [
    {
        "title": "USGS, Modified Mercalli Intensity Scale",
        "url": "https://www.usgs.gov/programs/earthquake-hazards/modified-mercalli-intensity-scale",
        "role": "Qualitative descriptions of observed shaking and effects; intensity is not a site-specific prediction.",
    },
]


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    mmi_value = numeric_input(inputs, "earthquake_mmi", minimum=1, maximum=12)
    if mmi_value is not None and not mmi_value.is_integer():
        raise ValueError("earthquake_mmi must be an integer from 1 to 12.")
    mmi = int(mmi_value) if mmi_value is not None else None
    return build_assessment(
        hazard="Earthquake",
        model_id="earthquake_reported_intensity_review",
        method="USGS Modified Mercalli Intensity (MMI) descriptive scale review",
        scientific_basis="MMI describes observed effects on people, objects, and structures; it is an ordinal intensity scale, not a magnitude-to-damage conversion.",
        inputs=inputs,
        result_status="reported_intensity_context_only" if mmi is not None else "insufficient_evidence_for_shaking_assessment",
        hazard_assessment={
            "severity": "Reported MMI is displayed without verification; no site-specific shaking or damage class is predicted.",
            "indicators": {
                "reported_mmi": mmi,
                "mmi_description": _mmi_description(mmi) if mmi is not None else None,
                "catalogue_note": "The acquired USGS regional query returned zero records; it is not a complete local hazard assessment.",
            },
        },
        calculation={"method": "No numerical shaking calculation is performed; an optional user-entered MMI is retained as a reported ordinal observation."},
        consequence_pathways=[
            "Building damage depends on ground motion, site soil, structural system, construction quality and occupancy.",
            "Aftershocks and utility/road disruption require current official information and local inspection.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Prioritize structural assessment and any seismic retrofit of critical facilities using verified site conditions and applicable seismic standards.",
                    "Long-term earthquake risk-reduction planning is requested.",
                    "Current BIS seismic design standards, authoritative GSI/NCS hazard information, and qualified structural audits.",
                    category="prevention",
                    limitations="No site shaking, building vulnerability, retrofit priority, or benefit is calculated from the reported MMI field.",
                ),
                recommendation("before", "Secure heavy items, identify accessible reunification arrangements and maintain emergency supplies.", "Preparedness review for earthquake is requested.", "Local emergency-management guidance and qualified building-safety review."),
            ],
            "during": [recommendation("during", "Follow recognized protective actions and official emergency instructions; do not use this app to identify structural safety.", "Shaking is occurring or an official alert is issued.", "Competent emergency authorities and trained responders.")],
            "after": [recommendation("after", "Avoid visibly damaged structures and report hazards; arrange qualified structural, gas, electrical and water inspections.", "Shaking has stopped and local authorities permit response.", "Qualified engineers and utility operators.")],
        },
        uncertainty=[
            "Optional MMI is user-entered and may not be an independently surveyed intensity.",
            "No accelerogram, PGA/PGV, site class, fault-distance or ground-motion model is provided.",
            "Building exposure, fragility and population are unknown.",
        ],
        data_gaps=[
            "Authoritative NCS/GSI/USGS event and hazard information with completeness metadata.",
            "Local site conditions and event-specific ground motion.",
            "Geocoded building inventory, structural vulnerability and independent impact outcomes.",
        ],
        sources=SOURCES,
    )


def _mmi_description(mmi: int) -> str:
    if mmi <= 2:
        return "Not felt to weak effects."
    if mmi <= 4:
        return "Light shaking; effects depend on setting and construction."
    if mmi == 5:
        return "Moderate shaking; some effects may be observed."
    if mmi == 6:
        return "Strong shaking; damage can occur in vulnerable construction."
    if mmi <= 8:
        return "Very strong to severe shaking; local damage depends on site and building vulnerability."
    return "Violent to extreme reported intensity; effects require qualified field assessment."

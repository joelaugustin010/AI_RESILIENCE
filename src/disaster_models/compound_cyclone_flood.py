"""Compound cyclone/flood scenario with separate components and unresolved coupling."""

from __future__ import annotations

from typing import Any

from src.disaster_models.common import build_assessment, recommendation, validate_top_level
from src.disaster_models.cyclone import assess as assess_cyclone
from src.disaster_models.flood import assess as assess_flood

SOURCES = [
    {
        "title": "Zscheischler et al. (2020), A typology of compound weather and climate events",
        "url": "https://doi.org/10.1038/s43017-020-0060-z",
        "role": "Compound-event categories and the need to identify event dependencies.",
    },
    {
        "title": "WMO Tropical Cyclone Programme",
        "url": "https://wmo.int/activities/tropical-cyclone-programme",
        "role": "Authoritative tropical-cyclone monitoring and warning context.",
    },
]


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    cyclone = assess_cyclone(inputs)
    flood = assess_flood(inputs)
    return build_assessment(
        hazard="Compound: cyclone + flood",
        model_id="compound_cyclone_flood_dependency_assessment",
        method="Component hazard review with evidence-gated compound-event dependency analysis",
        scientific_basis="Cyclone-related wind/rainfall and flood processes can interact, but a compound event requires compatible timing, spatial overlap, hydrology/coastal boundary conditions and outcome evidence. Component values are not added.",
        inputs=inputs,
        result_status="components_reviewed_interaction_unresolved_no_combined_score",
        hazard_assessment={
            "severity": "Cyclone and flood components are evaluated separately; combined severity and probability are unavailable.",
            "components": {
                "cyclone": {
                    "status": cyclone["result_status"],
                    "indicators": cyclone["hazard_assessment"]["indicators"],
                },
                "flood": {
                    "status": flood["result_status"],
                    "indicators": flood["hazard_assessment"]["indicators"],
                },
            },
            "interaction_status": "unresolved_dependency",
            "interaction_requirements": [
                "Time-aligned official cyclone track/advisory, local rainfall and river/coastal water observations.",
                "Compatible flood extent/depth, drainage condition, and independently reviewed impacts.",
            ],
        },
        calculation={
            "method": "No joint probability, interaction multiplier, or summed score. The cyclone dynamic-pressure indicator and flood rainfall/runoff indicators remain separate.",
        },
        consequence_pathways=[
            "Concurrent or sequential rainfall, river/coastal water, and drainage constraints may alter inundation; local causal dependency is unresolved.",
            "Potential road, hospital, power, water and population consequences are unquantified without verified spatial/time-linked evidence.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Develop coordinated cyclone, rainfall, river, coastal-water and drainage risk-reduction plans only after event timing and hydraulic dependencies are assessed.",
                    "Long-term compound cyclone/flood risk-reduction planning is requested.",
                    "Time-aligned official meteorology, verified gauges, coastal/drainage data, and independently reviewed flood outcomes.",
                    category="prevention",
                    limitations="The compound interaction remains unresolved; component indicators must not be added or used to select a local project.",
                ),
                recommendation("before", "Reconcile IMD/KSDMA cyclone advisories with local flood, river and coastal monitoring; review drainage and service continuity plans.", "A cyclone-plus-flood scenario or official watch is considered.", "Time-stamped official hazard sources, municipal flood plan, verified gauges and operator contacts."),
            ],
            "during": [recommendation("during", "Follow competent-authority warnings and incident command; do not infer safe routes or combine independent warning levels.", "A cyclone warning or flooding is reported.", "Current IMD, KSDMA and district administration guidance.")],
            "after": [recommendation("after", "Record cyclone conditions, rainfall, water levels, inundation duration and service impacts on a common time basis for independent review.", "Authorities authorize post-event assessment.", "Independent event records, gauge metadata, georeferenced impact observations and source hashes.")],
        },
        uncertainty=[
            "Cyclone wind/rainfall inputs may not be contemporaneous or independently verified.",
            "Spatial overlap and causal interaction are not established by simultaneous user entries.",
            "River datum, coastal surge, drainage behavior, exposure and vulnerability are unknown.",
            "Compound effects are not additive and are not quantitatively estimated.",
        ],
        data_gaps=[
            "Official time-stamped cyclone track/advisory and local station observations.",
            "River/coastal levels, drainage state, compatible flood extent and impacts.",
            "Verified infrastructure/population exposure and independent event outcomes.",
        ],
        sources=SOURCES,
        assumptions=["The selected label means a scenario combining cyclone conditions and flood processes, not proof of an observed compound event."],
    ) | {
        "component_assessments": {
            "Cyclone": cyclone,
            "Flood": flood,
        }
    }

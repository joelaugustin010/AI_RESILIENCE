"""Rainfall/drainage scenario using Rational Method runoff and a design-capacity check."""

from __future__ import annotations

from typing import Any

from src.disaster_models.common import (
    build_assessment,
    numeric_input,
    rainfall_intensity,
    record_scenario_consequence,
    recommendation,
    validate_top_level,
)

SOURCES = [
    {
        "title": "FHWA, Urban Drainage Design Manual (HEC-22)",
        "url": "https://www.fhwa.dot.gov/engineering/hydraulics/pubs/10009/10009.pdf",
        "role": "Rational Method and drainage-design assumptions for small catchments.",
    },
    {
        "title": "Zscheischler et al. (2020), A typology of compound weather and climate events",
        "url": "https://doi.org/10.1038/s43017-020-0060-z",
        "role": "Compound-event framework; this model does not infer a joint probability.",
    },
]


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    rain = rainfall_intensity(inputs)
    area = numeric_input(inputs, "catchment_area_ha", minimum=0.0001, maximum=1_000_000)
    runoff = numeric_input(inputs, "runoff_coefficient", minimum=0, maximum=1)
    capacity = numeric_input(inputs, "drainage_capacity_m3_s", minimum=0.000001, maximum=1_000_000)
    flow = None
    ratio = None
    relation = "unavailable"
    if rain["value"] is not None and area is not None and runoff is not None:
        flow = 0.002777777777777778 * runoff * rain["value"] * area
        if capacity is not None:
            ratio = flow / capacity
            relation = (
                "scenario_runoff_exceeds_user_supplied_capacity"
                if flow > capacity
                else "scenario_runoff_does_not_exceed_user_supplied_capacity"
            )
    result = build_assessment(
        hazard="Compound: heavy rainfall + drainage failure",
        model_id="compound_rainfall_drainage_rational_method_screening",
        method="Rational Method peak runoff estimate with conditional user-supplied drainage-capacity comparison",
        scientific_basis="Q = 0.00278 C i A for i in mm/h and catchment area A in hectares. The comparison is meaningful only if design intensity, catchment, runoff coefficient and capacity are compatible and verified.",
        inputs=inputs,
        result_status=(
            "scenario_flow_capacity_comparison_only"
            if ratio is not None
            else "partial_scenario_inputs_or_insufficient_hydraulic_evidence"
        ),
        hazard_assessment={
            "severity": "No flood severity is assigned. A flow/capacity comparison is not proof of inundation or drainage failure.",
            "indicators": {
                "rainfall_mean_intensity": rain,
                "catchment_area_ha": area,
                "runoff_coefficient": runoff,
                "estimated_peak_runoff_m3_s": flow,
                "user_supplied_drainage_capacity_m3_s": capacity,
                "runoff_to_capacity_ratio": ratio,
                "hydraulic_relation": relation,
            },
        },
        calculation={
            "equation": "Q = 0.00278 C i A",
            "interpretation": "Ratio compares a simplified scenario peak flow to user-entered capacity only; it is not a risk score, overflow probability, or observed service failure.",
        },
        consequence_pathways=[
            "If scenario inflow exceeds a valid design capacity, surcharge/ponding may be possible; actual outcome depends on network hydraulics, storage, tide/backwater, blockage and maintenance.",
            "Population and infrastructure impacts remain unquantified without verified flood extent and asset exposure.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Plan drainage maintenance, storage or capacity changes only after verified catchment, design-rainfall and hydraulic evidence identifies a need.",
                    "Long-term heavy-rainfall/drainage risk-reduction planning is requested.",
                    "Surveyed drainage network, design drawings, local rainfall IDF basis, and operator maintenance records.",
                    category="prevention",
                    limitations="This simplified flow/capacity comparison does not identify an overflow location or demonstrate that upgrades will reduce impacts.",
                ),
                recommendation("before", "Verify catchment delineation, design storm duration, runoff assumptions and drainage capacity with the responsible engineer; inspect blockage and outfall constraints.", "A rainfall/drainage scenario is being reviewed.", "Surveyed network, design drawings, rainfall IDF basis and operator maintenance records."),
            ],
            "during": [recommendation("during", "Follow local flood advisories and report observed ponding/blockage to the responsible authority; do not infer overflow location from the calculation.", "Heavy rain, drainage failure or flooding is reported.", "Incident command and municipal drainage operator; verified field observations.")],
            "after": [recommendation("after", "Document water levels, duration, blocked assets, outfall conditions and service disruptions; inspect before repair or capacity redesign.", "Water recedes and inspection is authorized.", "Georeferenced observations, as-built drainage records and qualified hydraulic review.")],
        },
        uncertainty=[
            "Rainfall mean intensity is not a design hyetograph or peak intensity over time of concentration.",
            "Runoff coefficient, catchment boundary and drainage capacity are scenario inputs and not verified.",
            "Rational Method assumptions may not hold for the actual catchment/network.",
            "No spatially explicit consequence or population exposure is estimated.",
        ],
        data_gaps=[
            "Verified subcatchment, imperviousness, time of concentration and local design rainfall.",
            "Drainage network geometry, capacity, storage, condition, outfall/tide constraints and maintenance status.",
            "Observed flood extent/depth/duration and independently reviewed impacts.",
        ],
        sources=SOURCES,
    )
    if flow is not None and capacity is not None and ratio is not None:
        excess = max(flow - capacity, 0.0)
        record_scenario_consequence(
            result,
            category="infrastructure",
            value={
                "indicator": "peak runoff to user-entered drainage-capacity comparison",
                "estimated_peak_runoff_m3_s": flow,
                "user_supplied_capacity_m3_s": capacity,
                "runoff_to_capacity_ratio": ratio,
                "scenario_excess_flow_m3_s": excess,
                "hydraulic_relation": relation,
            },
            interpretation=(
                "Under the entered scenario assumptions, calculated peak runoff "
                f"is {flow:.6g} m³/s against a user-entered capacity of "
                f"{capacity:.6g} m³/s. "
                + (
                    "This indicates scenario demand exceeds the nominated capacity; "
                    "surcharge or inundation is not calculated or confirmed."
                    if flow > capacity
                    else "This comparison does not indicate exceedance of the nominated capacity; it does not establish safety or exclude flooding."
                )
            ),
        )
        result["potential_consequences"]["cascading_or_compound_pathways"].append(
            (
                "SIMULATED SCENARIO ONLY: runoff-to-capacity comparison is "
                f"{relation}; no observed drainage failure, inundation, exposed "
                "asset, or service impact is established."
            )
        )
        during_action = result["recommendations"]["during"][0]
        during_action["relevance"] = (
            "The entered heavy-rainfall/drainage scenario produced a runoff-to-capacity "
            f"comparison of {ratio:.3g}; the calculation cannot confirm actual overflow."
        )
        during_action["trigger"] = during_action["relevance"]
    return result

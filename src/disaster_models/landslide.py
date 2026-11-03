"""Landslide rainfall screening; no uncalibrated local threshold is applied."""

from __future__ import annotations

from typing import Any

from src.disaster_models.common import build_assessment, numeric_input, rainfall_intensity, recommendation, validate_top_level

SOURCES = [
    {
        "title": "Guzzetti et al. (2008), The rainfall intensity-duration control of shallow landslides and debris flows",
        "url": "https://doi.org/10.1016/j.earscirev.2007.06.003",
        "role": "Reviews empirical rainfall intensity-duration thresholds and their regional dependence.",
    },
    {
        "title": "USGS Landslide Hazards Program",
        "url": "https://www.usgs.gov/programs/landslide-hazards",
        "role": "Landslide process and hazard information; no Kerala-specific threshold is assumed here.",
    },
]


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    rain = rainfall_intensity(inputs)
    antecedent = numeric_input(inputs, "antecedent_rainfall_mm", minimum=0, maximum=20_000)
    return build_assessment(
        hazard="Landslide",
        model_id="landslide_rainfall_context",
        method="Rainfall intensity-duration context with explicit threshold refusal",
        scientific_basis="Published rainfall-trigger approaches use intensity-duration and antecedent wetness, with thresholds calibrated to local geology, terrain, and event inventory. No transferable local threshold is available.",
        inputs=inputs,
        result_status="rainfall_context_only_no_susceptibility_or_trigger_class",
        hazard_assessment={
            "severity": "Not classified; rainfall alone cannot establish slope failure or susceptibility.",
            "indicators": {
                "mean_rainfall_intensity": rain,
                "user_reported_antecedent_rainfall_mm": antecedent,
                "threshold_comparison": "Unavailable: no locally calibrated, independently validated intensity-duration threshold.",
            },
        },
        calculation={"method": "Mean rainfall depth divided by stated duration where supported; no empirical trigger threshold is applied."},
        consequence_pathways=[
            "Slope failure requires susceptible terrain/material and hydrologic conditions; no slope, geology, soil, or saturation data are joined.",
            "Road, settlement and utility exposure remains unknown without a verified landslide footprint.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Use site-specific geotechnical assessment to determine whether slope stabilization, land-use controls, or drainage works are warranted.",
                    "Long-term slope risk-reduction planning is requested.",
                    "Verified terrain/geology, a locally reviewed failure inventory, and qualified geotechnical engineering.",
                    category="prevention",
                    limitations="Rainfall context alone does not identify a susceptible slope or justify a particular stabilization measure.",
                ),
                recommendation("before", "Check official slope/landslide advisories and inspect known drainage or slope problems through qualified local personnel.", "Heavy rain or a landslide scenario is being reviewed.", "Local geotechnical maps, official advisories and trained inspection."),
            ],
            "during": [recommendation("during", "Keep clear of active slope failures and follow official evacuation/closure directions; do not infer a safe route from rainfall alone.", "Ground movement, debris flow or official warning is reported.", "Emergency services and competent local authorities.")],
            "after": [recommendation("after", "Maintain closures until qualified assessment; document cracks, scarps, blocked channels and road damage without entering unstable ground.", "A reported slope event has ceased and access is authorized.", "Geotechnical inspection and independently located event records.")],
        },
        uncertainty=[
            "Rainfall station/grid, interval and input quality are unverified.",
            "Averaged intensity is not peak short-duration intensity.",
            "Terrain, geology, soil saturation, land cover and local threshold uncertainty dominate triggering assessment.",
        ],
        data_gaps=[
            "High-resolution slope, geology, soil, drainage and land-cover data.",
            "Local event inventory with rainfall time series and failure locations.",
            "Independent validation of a regionally appropriate trigger model.",
        ],
        sources=SOURCES,
    )

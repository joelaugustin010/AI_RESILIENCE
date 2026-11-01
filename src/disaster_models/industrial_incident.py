"""Industrial air-incident measurement review; no source attribution or dispersion."""

from __future__ import annotations

from typing import Any

from src.disaster_models.common import build_assessment, numeric_input, recommendation, validate_top_level

SOURCES = [
    {
        "title": "WHO Global Air Quality Guidelines (2021)",
        "url": "https://www.who.int/publications/i/item/9789240034228",
        "role": "Health-based air-quality guideline framework; not a substitute for applicable Indian legal standards or source attribution.",
    },
    {
        "title": "U.S. EPA, AERMOD Modeling System",
        "url": "https://www.epa.gov/scram/air-quality-dispersion-modeling-preferred-and-recommended-models",
        "role": "Illustrates input requirements for source-specific dispersion modelling; no such model is run here.",
    },
]


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    concentration = numeric_input(inputs, "pollutant_concentration", minimum=0, maximum=1e12)
    reference = numeric_input(inputs, "pollutant_reference_value", minimum=0.000001, maximum=1e12)
    unit = str(inputs.get("pollutant_unit", "")).strip()
    reference_unit = str(inputs.get("pollutant_reference_unit", "")).strip()
    averaging = str(inputs.get("pollutant_averaging_period", "")).strip()
    reference_averaging = str(inputs.get("pollutant_reference_averaging_period", "")).strip()
    ratio = None
    if concentration is not None and reference is not None:
        if not unit or unit != reference_unit:
            raise ValueError("Measured concentration and reference must use the same explicitly stated unit.")
        if not averaging or averaging != reference_averaging:
            raise ValueError("Measured concentration and reference must use the same averaging period.")
        ratio = concentration / reference

    return build_assessment(
        hazard="Industrial incident",
        model_id="pollutant_measurement_comparison",
        method="Pollutant-specific concentration comparison to a user-supplied, time-matched reference",
        scientific_basis="A like-for-like concentration/reference ratio is descriptive only. Source attribution or plume prediction requires emissions, stack, meteorology, terrain, and monitoring/dispersion evidence.",
        inputs=inputs,
        result_status=(
            "matched_measurement_comparison_only"
            if ratio is not None
            else "insufficient_pollutant_specific_evidence"
        ),
        hazard_assessment={
            "severity": "No industrial incident or source is confirmed; no legal compliance finding or health risk class is made.",
            "indicators": {
                "pollutant": inputs.get("pollutant_name"),
                "concentration": concentration,
                "reference_value": reference,
                "unit": unit or None,
                "averaging_period": averaging or None,
                "concentration_to_reference_ratio": ratio,
                "interpretation": "Ratio only; user-supplied reference applicability, measurement QA and legal status are unverified.",
            },
        },
        calculation={"equation": "observed concentration / reference concentration", "guard": "Only computed when units and averaging periods exactly match."},
        consequence_pathways=[
            "Potential exposure depends on measured pollutant, concentration, duration, location, meteorology and population activity.",
            "Nearby facilities or AQI cannot establish that an industry caused a measured concentration.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Review process-safety and emissions-control measures using current facility-specific hazard and permit records.",
                    "Long-term industrial incident prevention is requested.",
                    "Current KSPCB consent/emissions records, facility process-safety assessment, and qualified regulator/engineer review.",
                    category="prevention",
                    limitations="A concentration comparison does not confirm a release, source, control failure, or required corrective action.",
                ),
                recommendation("before", "Maintain facility-specific emergency contacts, pollutant inventory, monitoring calibration and notification procedures.", "Industrial incident preparedness is requested.", "Facility safety plan, current consent/emissions data and regulator-approved response procedures."),
            ],
            "during": [recommendation("during", "Follow regulator/emergency-authority instructions; preserve time-stamped pollutant-specific observations and do not approach a suspected release.", "A release or unusual measurement is reported.", "KSPCB/district emergency authority; no plume direction or evacuation zone is generated here.")],
            "after": [recommendation("after", "Arrange independent environmental sampling, exposure documentation and facility/regulatory review before attributing cause or declaring recovery.", "Authorities authorize post-incident investigation.", "Accredited laboratory, source records, meteorology and independent source-apportionment review.")],
        },
        uncertainty=[
            "Measurement source, calibration, coordinates and averaging metadata are unverified.",
            "The comparison reference may not be legally applicable or health-equivalent despite matching text fields.",
            "No emissions inventory, meteorological dispersion, source apportionment, or exposure assessment is performed.",
        ],
        data_gaps=[
            "Quality-assured pollutant-specific time series with co-located meteorology.",
            "Current facility emissions, stack parameters, operating status and applicable permits/standards.",
            "Independent source attribution, exposure and health/outcome records.",
        ],
        sources=SOURCES,
    )

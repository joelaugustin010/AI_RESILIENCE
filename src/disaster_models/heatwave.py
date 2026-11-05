"""Heat-index screening using the NOAA/NWS Rothfusz regression."""

from __future__ import annotations

from typing import Any

from src.disaster_models.common import build_assessment, numeric_input, recommendation, validate_top_level

SOURCES = [
    {
        "title": "National Weather Service, Heat Index",
        "url": "https://www.weather.gov/ama/heatindex",
        "role": "Heat-index definition, worked examples, and U.S. screening bands; not a Kerala warning threshold.",
    },
    {
        "title": "NOAA/NWS Weather Prediction Center, The Heat Index Equation",
        "url": "https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml",
        "role": "Steadman screening formula, Rothfusz regression, and low/high-humidity adjustments.",
    },
]


def heat_index_fahrenheit(temperature_f: float, relative_humidity_percent: float) -> float | None:
    """Return the NWS/Steadman heat index when its stated domain applies.

    The NWS algorithm (WPC heat-index equation) first evaluates Steadman's
    simple formula averaged with the air temperature.  Only when that screening
    value reaches 80 F is the Rothfusz regression applied, together with the
    published low-humidity (RH < 13%) and high-humidity (RH > 85%) adjustments.
    Applying the regression directly at low humidity was both outside its
    calibration range and made the low-humidity adjustment unreachable.
    """
    if temperature_f < 80:
        return None
    t = temperature_f
    rh = relative_humidity_percent
    simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
    screening = (simple + t) / 2
    if screening < 80:
        return screening
    index = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * rh
        - 0.22475541 * t * rh
        - 0.00683783 * t**2
        - 0.05481717 * rh**2
        + 0.00122874 * t**2 * rh
        + 0.00085282 * t * rh**2
        - 0.00000199 * t**2 * rh**2
    )
    if rh < 13 and 80 <= t <= 112:
        index -= ((13 - rh) / 4) * ((17 - abs(t - 95)) / 17) ** 0.5
    elif rh > 85 and 80 <= t <= 87:
        index += ((rh - 85) / 10) * ((87 - t) / 5)
    return index


def _heat_index_band(value_f: float) -> str:
    if value_f < 80:
        return "Below NWS heat-index screening bands"
    if value_f < 90:
        return "NWS caution band"
    if value_f < 103:
        return "NWS extreme-caution band"
    if value_f < 125:
        return "NWS danger band"
    return "NWS extreme-danger band"


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    temperature_c = numeric_input(inputs, "temperature_c", minimum=-100, maximum=70)
    humidity = numeric_input(inputs, "relative_humidity_percent", minimum=0, maximum=100)
    temperature_f = temperature_c * 9 / 5 + 32 if temperature_c is not None else None
    index_f = (
        heat_index_fahrenheit(temperature_f, humidity)
        if temperature_f is not None and humidity is not None
        else None
    )
    return build_assessment(
        hazard="Heatwave",
        model_id="heat_index_screening",
        method="NOAA/NWS Rothfusz heat-index regression",
        scientific_basis="Steadman screening formula followed, when the screening value reaches 80 F, by the Rothfusz regression with the published low- and high-humidity adjustments. Solar radiation, wind, acclimatization, exertion, health status and local warning criteria are not represented.",
        inputs=inputs,
        result_status=(
            "screening_indicator_calculated_not_local_warning"
            if index_f is not None
            else "insufficient_inputs_or_outside_screening_domain"
        ),
        hazard_assessment={
            "severity": (
                f"Calculated heat-index screening band: {_heat_index_band(index_f)}. "
                "U.S. NWS bands are not a locally approved Kerala warning or medical diagnosis."
                if index_f is not None
                else "Heat index unavailable: both temperature and humidity are needed, and the NWS screening applies only at temperature >=80 F (26.7 C)."
            ),
            "indicators": {
                "temperature_c": temperature_c,
                "relative_humidity_percent": humidity,
                "heat_index_f": index_f,
                "heat_index_c": (index_f - 32) * 5 / 9 if index_f is not None else None,
                "screening_band": _heat_index_band(index_f) if index_f is not None else None,
            },
        },
        calculation={
            "equation": "NWS/Steadman simple screening formula; Rothfusz multiple-regression equation with published low/high-humidity adjustments when the screening value reaches 80 F.",
            "calculation_status": "No output is produced below the NWS 80 F screening domain.",
        },
        consequence_pathways=[
            "Heat illness depends on exposure duration, activity, shade, hydration, acclimatization, age and health.",
            "Healthcare demand and population exposure are not estimated without local observations and demographic evidence.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Plan shade, cooling access and heat-health protections through a locally approved program informed by observed heat exposure and health needs.",
                    "Long-term heat-health risk-reduction planning is requested.",
                    "Quality-controlled local meteorology, public-health authority guidance, and verified facility/community needs.",
                    category="prevention",
                    limitations="The supplied heat-index calculation does not identify local hotspots, vulnerable groups, or intervention benefits.",
                ),
                recommendation("before", "Review local heat-health plans, shaded/cool spaces, drinking-water access and outreach to people at elevated health risk.", "High heat is forecast or preparedness is requested.", "IMD/local public-health guidance and verified facility/community plans."),
            ],
            "during": [recommendation("during", "Follow official health guidance; reduce heat exposure and seek medical help for suspected heat illness.", "High heat or symptoms are observed.", "Local health authority and emergency medical services; this heat-index screening is not triage.")],
            "after": [recommendation("after", "Document heat-related service demand, outages and affected groups using privacy-protective records; review cooling and water continuity.", "The heat episode has ended.", "Health-service and utility records with defined time/place and independent review.")],
        },
        uncertainty=[
            "Temperature/humidity are user-entered and may not be contemporaneous or co-located.",
            "The equation is a screening regression with published approximation error; radiant heat, wind and personal factors are absent.",
            "U.S. NWS categories do not establish local Kerala public-health action thresholds.",
        ],
        data_gaps=[
            "Quality-controlled, time-matched local temperature/humidity and radiation/wind observations.",
            "Locally approved heat-health triggers and population vulnerability data.",
            "Independent health outcome data for local validation.",
        ],
        sources=SOURCES,
    )

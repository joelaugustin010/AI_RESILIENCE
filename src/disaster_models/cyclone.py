"""Cyclone wind-intensity context without track, surge, or damage prediction."""

from __future__ import annotations

from typing import Any

from src.disaster_models.common import build_assessment, numeric_input, recommendation, validate_top_level

SOURCES = [
    {
        "title": "NOAA National Hurricane Center, Saffir-Simpson Hurricane Wind Scale",
        "url": "https://www.nhc.noaa.gov/aboutsshws.php",
        "role": "Wind-only classification context; not directly applied to an unverified wind-speed input or Kerala warning.",
    },
    {
        "title": "UNDRR, Disaster risk terminology",
        "url": "https://www.undrr.org/terminology/disaster-risk",
        "role": "Separates hazard from exposure and vulnerability.",
    },
]


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    speed_kmh = numeric_input(inputs, "wind_speed_kmh", minimum=0, maximum=500)
    speed_ms = speed_kmh / 3.6 if speed_kmh is not None else None
    dynamic_pressure = 0.5 * 1.225 * speed_ms**2 if speed_ms is not None else None
    return build_assessment(
        hazard="Cyclone",
        model_id="cyclone_wind_physics_screening",
        method="Wind-speed conversion and idealized dynamic-pressure indicator",
        scientific_basis="q = 1/2 rho v^2, using an assumed near-surface air density rho=1.225 kg/m^3. This physical pressure proxy is not a structural wind-load or damage model.",
        inputs=inputs,
        result_status="wind_indicator_only_track_and_impacts_unavailable",
        hazard_assessment={
            "severity": "No cyclone category or warning is assigned; sustained/gust averaging, track, radius, and official advisory are not verified.",
            "indicators": {
                "user_reported_wind_speed_kmh": speed_kmh,
                "wind_speed_m_s": speed_ms,
                "idealized_dynamic_pressure_pa": dynamic_pressure,
                "pressure_assumption": "Constant air density 1.225 kg/m3; excludes gust factors, exposure, terrain, and building coefficients.",
            },
        },
        calculation={"equation": "q=0.5*rho*v^2", "wind_speed_conversion": "m/s = km/h / 3.6"},
        consequence_pathways=[
            "Wind damage depends on gust, duration, direction, terrain, construction, and debris; no local fragility data are available.",
            "Cyclone rainfall, coastal water/surge, river levels and drainage may interact, but event-specific joint observations are absent.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Prioritize wind-resilience retrofits for critical facilities only after qualified structural surveys and local wind-hazard review.",
                    "Long-term cyclone risk-reduction planning is requested.",
                    "Applicable Indian structural design standards, qualified engineering inspection, and verified facility inventory.",
                    category="prevention",
                    limitations="No local wind load, facility vulnerability, or retrofit benefit is estimated by this indicator.",
                ),
                recommendation("before", "Monitor IMD and district-authority advisories; review shelter, communications, backup power and facility continuity plans.", "A cyclone scenario or official watch is being reviewed.", "Official forecast/advisory, local authority plans and verified facility backup capacity."),
            ],
            "during": [recommendation("during", "Follow official shelter/evacuation instructions and avoid exposed areas; this model does not identify safe locations.", "Official warning or dangerous conditions are reported.", "Current IMD, KSDMA and district administration instructions.")],
            "after": [recommendation("after", "Wait for competent-authority clearance; assess structural, electrical, water and access hazards before re-entry.", "The official response authority permits damage assessment.", "Qualified structural/utility inspection and incident records.")],
        },
        uncertainty=[
            "Wind measurement averaging period, gust status, height, exposure and source are unverified.",
            "Dynamic pressure assumes constant air density and does not represent actual building load.",
            "Track, landfall, storm surge, rainfall and local cyclone warning data are not included.",
        ],
        data_gaps=[
            "IMD cyclone track/advisory and time-matched station wind observations.",
            "Coastal elevation, tide/surge, rainfall, river levels and local drainage observations.",
            "Building inventory, structural class and validated wind-damage functions.",
        ],
        sources=SOURCES,
    )

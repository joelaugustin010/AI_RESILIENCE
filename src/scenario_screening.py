"""Transparent conditional scenario screening from user-entered assumptions.

This module provides useful scenario-specific reasoning without pretending that
hypothetical inputs are observations or producing calibrated probabilities,
numerical risk scores, or official warnings.
"""
from __future__ import annotations

from typing import Any

import pandas as pd


def _imd_24h_rainfall_category(rainfall_mm: float) -> str:
    """Return the IMD station rainfall category for a 24-hour accumulation.

    Thresholds are the IMD published 24-hour station categories. This is a
    meteorological rainfall category only, not a flood-risk classification.
    Source: https://mausam.imd.gov.in/imd_latest/contents/pdf/pubbrochures/Heavy%20Rainfall%20Warning%20Services.pdf
    """
    amount = float(rainfall_mm)
    if amount < 2.5:
        return "Very light / trace"
    if amount < 15.6:
        return "Light"
    if amount < 64.5:
        return "Moderate"
    if amount < 115.6:
        return "Heavy"
    if amount < 204.5:
        return "Very heavy"
    return "Extremely heavy"


def build_scenario_screening(inputs: dict[str, Any]) -> pd.DataFrame:
    """Return conditional findings and concrete checks for the selected hazard."""
    hazard = str(inputs.get("hazard", ""))
    classification = str(inputs.get("input_classification", "Unknown / unverified"))
    hypothetical = "hypothetical" in classification.casefold()
    evidence_class = "Hypothetical assumption" if hypothetical else classification
    rows: list[dict[str, str]] = []

    def add(signal: str, interpretation: str, next_step: str) -> None:
        rows.append({
            "Scenario signal": signal,
            "Conditional assessment": interpretation,
            "Next check / action": next_step,
            "Evidence class": evidence_class,
        })

    rainfall = inputs.get("rainfall_mm")
    period = str(inputs.get("rainfall_period", "Not supplied"))
    drainage = str(inputs.get("drainage_status", "Not supplied"))
    river = inputs.get("river_level_m")
    wind = inputs.get("wind_speed_kmh")
    temperature = inputs.get("temperature_c")
    normal_temp = inputs.get("normal_max_temperature_c")
    population = inputs.get("affected_population")
    assets = inputs.get("assets") or []

    flood_related = hazard in {
        "Flood", "Compound: cyclone + flood",
        "Compound: heavy rainfall + drainage failure",
    }
    if flood_related:
        if rainfall is not None:
            add(
                f"Rainfall assumption: {rainfall:g} mm ({period})",
                "This amount and accumulation period are part of the scenario forcing. The app has no approved local rainfall-to-flood threshold, so it does not convert this value into a flood-risk category or probability.",
                "Check the exact accumulation window, local forecast/observation source, catchment response, and official warnings.",
            )
            if period == "Last 24 hours":
                rainfall_category = _imd_24h_rainfall_category(float(rainfall))
                add(
                    f"IMD 24-hour station rainfall category: {rainfall_category}",
                    f"For the entered 24-hour amount, the India Meteorological Department's station rainfall categories classify {rainfall:g} mm as {rainfall_category.lower()} rainfall. This describes rainfall amount only; it is not a Kochi flood prediction, alert, or estimate of inundation depth.",
                    "Confirm the measurement is a station total for the relevant 24-hour window (IMD daily totals commonly end at 0830 IST), and check current IMD/KSDMA bulletins and local water levels. Reference: https://mausam.imd.gov.in/imd_latest/contents/pdf/pubbrochures/Heavy%20Rainfall%20Warning%20Services.pdf",
                )
        if river is not None:
            station = str(inputs.get("river_station") or "").strip() or "station not supplied"
            datum = str(inputs.get("river_reference") or "").strip() or "gauge reference not supplied"
            add(
                f"River-level assumption: {river:g} m",
                f"Reading recorded for context only ({station}; {datum}). Without a verified station datum and local threshold, the number alone cannot establish whether the river is dangerous.",
                "Confirm gauge identity, datum, timestamp, trend, and official local warning level.",
            )
        if drainage in {"Reported failed", "Hypothetical partial failure", "Reported partially impaired"}:
            add(
                f"Drainage condition: {drainage}",
                "If this condition holds during heavy rainfall, reduced drainage capacity can increase the potential for surface-water accumulation and local access disruption. Extent and depth are not calculated.",
                "Inspect drains and outfalls, identify low points, check safe routes, and verify nearby critical services.",
            )
        elif drainage == "Reported functioning":
            add(
                "Drainage condition: reported functioning",
                "Functioning drainage may reduce one pathway, but does not rule out river overflow, coastal flooding, blocked downstream outlets, or rainfall beyond capacity.",
                "Verify capacity, downstream conditions, maintenance status, and observed water levels.",
            )
        if hazard == "Compound: cyclone + flood":
            add(
                "Compound cyclone + flood",
                "Wind, heavy rainfall, coastal/river water and service disruption may overlap. The combined timing and impact are unknown; component values must not be treated as a calibrated joint model.",
                "Check the same-issue-time official cyclone bulletin, rainfall forecast, coastal/river levels, drainage, power and evacuation arrangements.",
            )
        if hazard == "Compound: heavy rainfall + drainage failure":
            add(
                "Compound heavy rainfall + drainage failure",
                "The assumed coincidence of rainfall and drainage impairment is a plausible waterlogging pathway. This is a conditional mechanism, not a prediction that flooding will occur.",
                "Confirm failure location and duration, rainfall timing, observed water depth, affected routes and available pumping/maintenance response.",
            )
    if hazard in {"Cyclone", "Compound: cyclone + flood"} and wind is not None:
        add(
            f"Wind-speed assumption: {wind:g} km/h",
            "Higher wind can increase risk of tree/debris damage, roof damage and power/communication disruption, but this app does not classify cyclone intensity from a user-entered speed.",
            "Verify sustained versus gust speed, averaging period, forecast source, track, and official IMD warning category.",
        )
    if hazard == "Heatwave" and temperature is not None:
        if normal_temp is not None:
            departure = float(temperature) - float(normal_temp)
            add(
                f"Maximum temperature: {temperature:g} °C; supplied normal: {normal_temp:g} °C",
                f"The entered departure is {departure:.1f} °C. The separate station-criterion screen below checks relevant numeric conditions; this scenario output is not a forecast or official declaration.",
                "Verify station, date, local normal, consecutive-day duration, humidity/night temperatures, and official bulletin.",
            )
        else:
            add(
                f"Maximum-temperature assumption: {temperature:g} °C",
                "Temperature alone cannot establish heatwave status or quantify health impacts without local normal, duration and exposure context.",
                "Supply a verified station normal and date series; review water, cooling, health-service and outdoor-worker preparedness.",
            )
    if hazard == "Landslide":
        slope = str(inputs.get("slope_condition", "Not supplied"))
        soil = str(inputs.get("soil_condition", "Not supplied"))
        if rainfall is not None or slope not in {"Not supplied", ""} or soil not in {"Not supplied", ""}:
            add(
                "Rainfall / slope / ground assumptions",
                f"Entered context: rainfall {rainfall if rainfall is not None else 'not supplied'} mm ({period}); slope {slope}; soil/ground {soil}. Saturated ground and unstable slopes can be relevant pathways, but no local failure probability is computed.",
                "Check official landslide alerts, local slope/geology evidence, fresh cracks or movement, drainage, and safe access; follow authority instructions.",
            )
    if hazard == "Drought":
        indicator = str(inputs.get("drought_indicator", "Not supplied"))
        water = str(inputs.get("water_supply_status", "Not supplied"))
        add(
            "Drought and water-supply assumptions",
            f"Drought indicator: {indicator}; water-supply status: {water}. These qualitative inputs do not establish drought severity without a defined index, time window and source.",
            "Check rainfall anomaly, soil moisture/evaporative demand, reservoir/storage, demand, and local water-supply advisories.",
        )
    if hazard == "Earthquake":
        magnitude = inputs.get("earthquake_magnitude")
        depth = inputs.get("earthquake_depth_km")
        add(
            "Earthquake scenario",
            f"Supplied magnitude: {magnitude if magnitude is not None else 'not supplied'}; depth: {depth if depth is not None else 'not supplied'}. Magnitude alone cannot determine local shaking or building damage.",
            "Use an authoritative event bulletin; review local ground-motion/site conditions, building vulnerability, utility isolation and safe access.",
        )
    if hazard == "Industrial incident":
        substance = str(inputs.get("industrial_substance") or "").strip() or "not supplied"
        release = str(inputs.get("industrial_release_status", "Not supplied"))
        direction = str(inputs.get("industrial_wind_direction") or "").strip() or "not supplied"
        add(
            "Industrial release assumptions",
            f"Substance: {substance}; release status: {release}; wind direction: {direction}. Without verified substance, quantity, release conditions and monitoring, the impact footprint cannot be inferred.",
            "Follow facility and emergency-service procedures; verify substance-specific monitoring, wind/meteorology, isolation distance and official instructions.",
        )
    if hazard == "Infrastructure failure":
        asset = str(inputs.get("failed_asset_type", "Not supplied"))
        failure = str(inputs.get("failure_status", "Not supplied"))
        status = str(inputs.get("infrastructure_status", "Not supplied"))
        add(
            "Infrastructure-failure assumptions",
            f"Asset type: {asset}; failure status: {failure}; wider infrastructure condition: {status}. Service impacts depend on network dependencies and redundancy not modeled here.",
            "Identify the responsible operator, affected service area, backup duration, alternate routes/communications, and repair/restore estimate.",
        )

    if population is not None:
        add(
            f"Affected-population context: {population:g} people",
            "This is a user-entered planning assumption, not an estimate generated by the app and not a verified exposed or affected population.",
            "Confirm the geographic area, time window, population source and whether the number means exposed, displaced, or directly affected people.",
        )
    if assets:
        add(
            "Assets nominated for review: " + ", ".join(map(str, assets)),
            "These assets are priorities selected by the user. The app has not confirmed that they lie inside a hazard footprint.",
            "Verify asset identities and coordinates, then overlay them only with an appropriately validated hazard layer.",
        )
    if not rows:
        add(
            "General scenario",
            "No dedicated structured trigger was supplied for this hazard. Use the scenario assumptions and checklist below for a conditional review; no prediction is generated.",
            "Document event timing, source, location, hazard mechanism, exposed people/assets, and service dependencies.",
        )

    return pd.DataFrame(rows, columns=[
        "Scenario signal", "Conditional assessment", "Next check / action", "Evidence class"
    ])

"""Transparent rule-based scenario output for the ten decision-workflow options.

This is not a trained ML model and does not estimate calibrated probabilities. It turns
user-entered scenario context into a reproducible conditional outcome and explicitly
returns "insufficient evidence" when key inputs are absent.
"""
from __future__ import annotations

from typing import Any

from src.hazard_registry import WORKFLOW_HAZARDS

HAZARDS = WORKFLOW_HAZARDS

IMD_24H_HEAVY_RAIN_MM = 64.5
IMD_24H_VERY_HEAVY_RAIN_MM = 115.6
IMD_24H_EXTREME_RAIN_MM = 204.5


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() not in {"", "Not supplied", "Unknown"}


_NUMERIC_INPUT_RULES: dict[str, tuple[float, float, bool]] = {
    # Broad plausibility guards, not hazard thresholds or warning criteria.
    "rainfall_mm": (0.0, 2000.0, False),
    "wind_speed_kmh": (0.0, 500.0, False),
    "temperature_c": (-90.0, 65.0, False),
    "normal_max_temperature_c": (-90.0, 65.0, False),
    "river_level_m": (-20.0, 100.0, False),
    "earthquake_magnitude": (0.0, 10.0, False),
    "earthquake_depth_km": (0.0, 750.0, False),
    "heatwave_consecutive_days": (0.0, 366.0, True),
    "heatwave_station_count": (0.0, 100000.0, True),
}


def validate_scenario_inputs(inputs: dict[str, Any]) -> list[dict[str, str]]:
    """Reject malformed measurements before rule evaluation; bounds are not hazard thresholds."""
    import math
    problems: list[dict[str, str]] = []
    for field, (minimum, maximum, integer_only) in _NUMERIC_INPUT_RULES.items():
        raw = inputs.get(field)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        if isinstance(raw, bool):
            problems.append({"field": field, "message": "Enter a numeric measurement, not a true/false value."})
            continue
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError):
            problems.append({"field": field, "message": "Value must be numeric."})
            continue
        if not math.isfinite(value):
            problems.append({"field": field, "message": "Value must be finite; NaN and infinity are not accepted."})
        elif value < minimum or value > maximum:
            problems.append({"field": field, "message": f"Value is outside the broad input-quality range [{minimum:g}, {maximum:g}]."})
        elif integer_only and not value.is_integer():
            problems.append({"field": field, "message": "Value must be a whole number."})
    return problems

def predict_scenario_outcome(inputs: dict[str, Any]) -> dict[str, Any]:
    """Produce a transparent, conditional outcome for any supported hazard choice."""
    hazard = str(inputs.get("hazard", ""))
    if hazard not in HAZARDS:
        raise ValueError(f"Unsupported hazard: {hazard!r}")

    input_problems = validate_scenario_inputs(inputs)
    if input_problems:
        return {
            "hazard": hazard,
            "concern_level": "Input validation required",
            "conditional_outcome": "Scenario not assessed because supplied measurements failed input validation.",
            "basis": "Invalid or implausible values must be corrected before hazard-specific interpretation.",
            "evidence_used": [],
            "recommended_checks": ["Correct the listed fields and verify units, source, timestamp and measurement period."],
            "model_type": "Input validation only — no scenario assessment performed",
            "numerical_probability": None,
            "is_trained_ml": False,
            "is_official_warning": False,
            "input_validation": {"valid": False, "problems": input_problems},
            "limitations": ["No hazard conclusion was generated from invalid inputs.", "Input-range checks are broad data-quality guards, not hazard thresholds.", "Insufficient or invalid evidence never means safe or zero risk."],
        }

    evidence: list[str] = []
    assumptions: list[str] = []
    actions: list[str] = []
    outcome = "Insufficient evidence to classify this scenario"
    concern = "Insufficient evidence"
    basis = "No hazard-specific trigger was supplied."
    rainfall = inputs.get("rainfall_mm")
    period = str(inputs.get("rainfall_period", "Not supplied"))
    drainage = str(inputs.get("drainage_status", "Not supplied"))
    wind = inputs.get("wind_speed_kmh")
    temperature = inputs.get("temperature_c")
    normal = inputs.get("normal_max_temperature_c")
    slope = str(inputs.get("slope_condition", "Not supplied"))
    soil = str(inputs.get("soil_condition", "Not supplied"))
    water = str(inputs.get("water_supply_status", "Not supplied"))
    release = str(inputs.get("industrial_release_status", "Not supplied"))
    failure = str(inputs.get("failure_status", "Not supplied"))
    infrastructure = str(inputs.get("infrastructure_status", "Not supplied"))

    if hazard == "Flood":
        if rainfall is not None:
            evidence.append(f"User-entered rainfall: {float(rainfall):g} mm ({period}).")
            if period == "Last 24 hours":
                amount = float(rainfall)
                category = (
                    "extremely heavy" if amount >= IMD_24H_EXTREME_RAIN_MM else
                    "very heavy" if amount >= IMD_24H_VERY_HEAVY_RAIN_MM else
                    "heavy" if amount >= IMD_24H_HEAVY_RAIN_MM else
                    "below the IMD heavy-rainfall category"
                )
                evidence.append(f"IMD 24-hour station rainfall category: {category}.")
        if drainage in {"Reported partially impaired", "Reported failed", "Hypothetical partial failure"}:
            evidence.append(f"Drainage impairment entered: {drainage}.")
            concern = "Elevated conditional waterlogging concern"
            outcome = "Surface-water accumulation and local access disruption are plausible if rainfall and drainage impairment overlap."
            basis = "Rainfall/drainage pathway identified; no flood probability, depth, extent, or ward exposure is calculated."
            actions.extend(["Verify the rainfall source and accumulation window.", "Inspect drains/outfalls and check observed water levels and official advisories."])
        elif rainfall is not None:
            concern = "Rainfall signal present; flood outcome unconfirmed"
            outcome = "Heavy rainfall may increase runoff, but flooding cannot be inferred from rainfall alone."
            basis = "Rainfall is a forcing indicator, not a calibrated local flood model."
            actions.extend(["Check local river/tide levels, drainage capacity, terrain and official warnings.", "Confirm whether the rainfall value is observed or forecast."])
        if inputs.get("river_level_m") is not None:
            evidence.append("A river-level value was supplied, but no verified station datum or local threshold is available.")
            actions.append("Verify gauge identity, datum, timestamp, trend and official warning level.")
    elif hazard == "Cyclone":
        if wind is not None:
            evidence.append(f"User-entered wind speed: {float(wind):g} km/h; averaging period and source are not independently verified.")
            concern = "Wind-impact pathway identified"
            outcome = "Wind-related damage or power/communication disruption is possible; local cyclone intensity and impact are not determined."
            basis = "No verified forecast track, gust/mean-wind distinction, surge estimate or local exposure model."
        actions.extend(["Check the latest official IMD cyclone bulletin and its issue time.", "Review official shelter, coastal-water and communications guidance."])
    elif hazard == "Earthquake":
        magnitude = inputs.get("earthquake_magnitude")
        depth = inputs.get("earthquake_depth_km")
        if magnitude is not None or depth is not None:
            evidence.append(f"Supplied event parameters: magnitude={magnitude if magnitude is not None else 'not supplied'}, depth_km={depth if depth is not None else 'not supplied'}.")
            concern = "Event parameters supplied; local impact unknown"
            outcome = "Local shaking and damage cannot be predicted from magnitude/depth alone; site conditions and building vulnerability are required."
            basis = "No site-specific ground-motion or building-impact model is validated here."
        actions.extend(["Verify the event with an authoritative seismic bulletin.", "Follow official safety guidance and have building safety assessed by qualified professionals."])
    elif hazard == "Landslide":
        if slope == "Recent slope failure reported":
            evidence.append("A recent slope failure was selected as reported context.")
            concern = "Urgent local hazard concern — verify immediately"
            outcome = "Further movement or nearby access disruption may be possible; the app cannot forecast failure timing or runout."
            basis = "Reported failure is a serious field signal, not a model-derived probability."
        elif slope == "Cracks or movement reported" and (soil == "Saturated / waterlogged" or rainfall is not None):
            evidence.append(f"Slope movement reported; ground={soil}; rainfall={rainfall if rainfall is not None else 'not supplied'} mm.")
            concern = "Elevated conditional slope concern"
            outcome = "Slope instability may be a concern under the entered conditions; no local failure probability is calculated."
            basis = "Conditional mechanism only; site geology and official alerts are not integrated."
        elif _present(slope) or _present(soil) or rainfall is not None:
            evidence.append(f"Slope={slope}; ground={soil}; rainfall={rainfall if rainfall is not None else 'not supplied'} mm.")
            concern = "Site evidence needs review"
            outcome = "The supplied context alone is not enough to classify landslide likelihood."
            basis = "No validated local slope, geology, or event-inventory model."
        actions.extend(["Check official landslide advisories and local geotechnical evidence.", "If fresh movement or a slope failure is observed, keep away and follow local emergency-authority instructions."])
    elif hazard == "Heatwave":
        if temperature is not None:
            evidence.append(f"User-entered maximum temperature: {float(temperature):g} °C.")
        if temperature is not None and normal is not None:
            departure = float(temperature) - float(normal)
            evidence.append(f"Difference from user-supplied station normal: {departure:+.1f} °C.")
            concern = "Temperature anomaly available; heatwave status unconfirmed"
            outcome = "A temperature departure is present in the supplied inputs, but an official heatwave classification or health-impact forecast is not produced."
            basis = "Station, duration, humidity and official local criteria need verification."
        elif temperature is not None:
            concern = "Temperature supplied; insufficient for heatwave classification"
            outcome = "Temperature alone cannot establish a heatwave or quantify health impacts."
            basis = "No verified local normal, duration or humidity inputs."
        actions.extend(["Check official IMD heatwave bulletins and the relevant station/time period.", "Review water, cooling, health-service and outdoor-worker preparedness."])
    elif hazard == "Drought":
        evidence.append(f"Drought indicator={inputs.get('drought_indicator', 'Not supplied')}; water supply={water}.")
        if water in {"Restricted", "Severely disrupted"}:
            concern = "Water-service stress indicated by supplied context"
            outcome = "Water-supply disruption is a planning concern; drought cause, geographic extent and duration are not established."
            basis = "User-entered service status, not a drought probability."
        elif _present(inputs.get("drought_indicator")):
            concern = "Drought indicator nominated; severity unverified"
            outcome = "A drought assessment requires a defined index/time window plus rainfall, storage and demand evidence."
            basis = "No validated local drought classifier."
        actions.extend(["Check official drought indices, rainfall anomaly, storage/reservoir and supply records.", "Review essential-service water continuity and conservation plans."])
    elif hazard == "Industrial incident":
        substance = str(inputs.get("industrial_substance") or "").strip() or "not supplied"
        evidence.append(f"Substance={substance}; release status={release}.")
        if release == "Confirmed by cited authority":
            concern = "Confirmed incident status entered — follow official instructions"
            outcome = "A hazardous-release pathway may require protective action, but the affected footprint and safe distance are not calculated."
            basis = "No substance-specific release quantity, monitoring or dispersion model is available."
        elif release in {"Suspected", "Reported by user"}:
            concern = "Unverified incident concern"
            outcome = "The report needs confirmation; the app cannot infer the substance, plume direction or safe area."
            basis = "User report is not an independently verified incident record."
        elif release == "No release reported":
            concern = "No release reported in supplied input; incident status not independently verified"
            outcome = "No release is reported in this input, but the app cannot certify that the area is safe."
            basis = "Absence of a report is not proof of absence."
        actions.extend(["Contact the relevant emergency service/site operator and follow official instructions.", "Use substance-specific monitoring and authoritative guidance; do not infer source from AQI alone."])
    elif hazard == "Infrastructure failure":
        asset = str(inputs.get("failed_asset_type", "Not supplied"))
        evidence.append(f"Asset={asset}; failure status={failure}; wider disruption={infrastructure}.")
        if failure == "Confirmed by cited authority" or infrastructure == "Disruption reported by user":
            concern = "Service-disruption pathway identified"
            outcome = f"The reported {asset.lower()} failure may interrupt dependent services; affected area and restoration time are unknown."
            basis = "No verified dependency graph, outage footprint or repair-time model."
        elif failure in {"Suspected", "Reported by user", "Hypothetical"}:
            concern = "Failure needs verification"
            outcome = f"A possible {asset.lower()} disruption is a scenario to check; downstream consequences are not quantified."
            basis = "No independently verified asset/failure record."
        actions.extend(["Confirm the asset status with its responsible operator.", "Check dependent services, backup capacity, alternate access and official updates."])
    elif hazard == "Compound: cyclone + flood":
        rain_signal = rainfall is not None
        wind_signal = wind is not None
        drainage_signal = drainage in {"Reported partially impaired", "Reported failed", "Hypothetical partial failure"}
        evidence.extend([
            f"Rainfall supplied: {'yes' if rain_signal else 'no'}",
            f"Wind supplied: {'yes' if wind_signal else 'no'}",
            f"Drainage impairment supplied: {'yes' if drainage_signal else 'no'}",
        ])
        if (rain_signal and wind_signal) or (rain_signal and drainage_signal):
            concern = "Compound impact pathways identified"
            outcome = "Concurrent wind/rainfall or rainfall/drainage stress could disrupt access and essential services; joint timing and extent remain unknown."
            basis = "Scenario co-occurrence is not a calibrated joint probability or flood prediction."
        else:
            concern = "Compound scenario incompletely specified"
            outcome = "The compound outcome cannot be meaningfully classified until relevant rainfall, wind, water-level and drainage evidence is supplied."
            basis = "One or more component conditions are missing."
        actions.extend(["Use official, same-issue-time cyclone/rainfall bulletins.", "Verify coastal/river levels, drainage, power, shelters and local authority instructions."])
    elif hazard == "Compound: heavy rainfall + drainage failure":
        rain_signal = rainfall is not None
        drainage_signal = drainage in {"Reported partially impaired", "Reported failed", "Hypothetical partial failure"}
        evidence.extend([f"Rainfall supplied: {'yes' if rain_signal else 'no'}", f"Drainage impairment supplied: {'yes' if drainage_signal else 'no'}"])
        if rain_signal and drainage_signal:
            concern = "Elevated conditional waterlogging concern"
            outcome = "Rainfall coinciding with drainage impairment could cause surface-water accumulation and access disruption in connected low-lying areas."
            basis = "Conditional mechanism only; no local depth, extent, probability or exposed-population estimate."
        else:
            concern = "Compound scenario incompletely specified"
            outcome = "A combined outcome cannot be classified until rainfall timing and the location/status of drainage impairment are described."
            basis = "Required co-occurring inputs are incomplete."
        actions.extend(["Verify rainfall timing and the drainage failure location/status.", "Check observed water levels, safe access and official advisories."])

    if not evidence:
        evidence.append("No hazard-specific measurable or reported condition was supplied.")
    if not actions:
        actions.append("Supply a time-stamped source, relevant measurements and verified local context before interpreting this scenario.")
    return {
        "hazard": hazard,
        "concern_level": concern,
        "conditional_outcome": outcome,
        "basis": basis,
        "evidence_used": evidence,
        "recommended_checks": list(dict.fromkeys(actions)),
        "model_type": "Transparent rule-based scenario screening",
        "numerical_probability": None,
        "is_trained_ml": False,
        "is_official_warning": False,
        "limitations": [
            "Inputs are user supplied and are not independently verified.",
            "This output is conditional scenario screening, not a calibrated prediction, forecast, or official warning.",
            "Insufficient evidence never means safe or zero risk.",
        ],
    }

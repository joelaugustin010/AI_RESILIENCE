"""Input validation and strict model gates for Ernakulam hazard predictions."""

from __future__ import annotations

import math
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from src.ernakulam_disaster_dashboard import load_location_registry, location_options


ROOT = Path(__file__).resolve().parents[1]
MODEL_DIRECTORY = ROOT / "models" / "hazards" / "ernakulam_input_models"
EVIDENCE_PATH = ROOT / "data" / "reference" / "ernakulam_disaster_evidence.json"
FLOOD_STATISTICS_PATH = (
    ROOT
    / "data"
    / "reference"
    / "ksdma_ernakulam_flood_return_period_statistics_2022.json"
)

INPUTS = {
    "rainfall_intensity_mm_h": {
        "label": "Rainfall intensity",
        "unit": "mm/hour",
        "minimum": 0.0,
        "maximum": 500.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Observed rainfall rate at the selected area; enter a measured value.",
    },
    "water_level_m": {
        "label": "Water level",
        "unit": "metres",
        "minimum": -50.0,
        "maximum": 50.0,
        "step": 0.01,
        "format": "%.2f",
        "help": (
            "Relative to the named gauge/datum below. Levels from different "
            "references are not interchangeable."
        ),
    },
    "wind_speed_kmh": {
        "label": "Wind speed",
        "unit": "km/h",
        "minimum": 0.0,
        "maximum": 400.0,
        "step": 0.1,
        "format": "%.1f",
        "help": (
            "Observed sustained wind speed, not a gust, unless the model "
            "specification states otherwise."
        ),
    },
    "pressure_hpa": {
        "label": "Atmospheric pressure",
        "unit": "hPa",
        "minimum": 800.0,
        "maximum": 1100.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Observed station pressure with the instrument's reference convention recorded.",
    },
    "soil_moisture_percent": {
        "label": "Soil moisture",
        "unit": "%",
        "minimum": 0.0,
        "maximum": 100.0,
        "step": 0.1,
        "format": "%.1f",
        "help": (
            "Sensor-reported volumetric percentage; sensor depth and method "
            "affect comparability."
        ),
    },
    "temperature_c": {
        "label": "Temperature",
        "unit": "°C",
        "minimum": -10.0,
        "maximum": 60.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Observed air temperature in degrees Celsius.",
    },
    "accumulated_rainfall_24h_mm": {
        "label": "Accumulated rainfall, past 24 hours",
        "unit": "mm",
        "minimum": 0.0,
        "maximum": 2000.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Measured total over the 24 hours immediately before the observation time.",
    },
    "accumulated_rainfall_72h_mm": {
        "label": "Accumulated rainfall, past 72 hours",
        "unit": "mm",
        "minimum": 0.0,
        "maximum": 5000.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Measured total over the 72 hours immediately before the observation time.",
    },
    "rainfall_duration_h": {
        "label": "Rainfall duration",
        "unit": "hours",
        "minimum": 0.0,
        "maximum": 168.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Duration of the current measured rainfall episode.",
    },
    "water_level_rise_m_h": {
        "label": "Water-level change",
        "unit": "metres/hour",
        "minimum": -10.0,
        "maximum": 10.0,
        "step": 0.01,
        "format": "%.2f",
        "help": "Measured rate of change at the same gauge and datum as the water level.",
    },
    "wind_gust_kmh": {
        "label": "Wind gust",
        "unit": "km/h",
        "minimum": 0.0,
        "maximum": 500.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Maximum measured gust; do not substitute sustained wind.",
    },
    "relative_humidity_percent": {
        "label": "Relative humidity",
        "unit": "%",
        "minimum": 0.0,
        "maximum": 100.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Measured relative humidity at the same time as the other weather readings.",
    },
    "rainfall_deficit_30d_percent": {
        "label": "Rainfall deficit, past 30 days",
        "unit": "%",
        "minimum": 0.0,
        "maximum": 100.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Percent difference from a named, quality-controlled local normal period.",
    },
    "rainfall_deficit_90d_percent": {
        "label": "Rainfall deficit, past 90 days",
        "unit": "%",
        "minimum": 0.0,
        "maximum": 100.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Percent difference from a named, quality-controlled local normal period.",
    },
    "rainfall_forecast_24h_mm": {
        "label": "Forecast rainfall, next 24 hours",
        "unit": "mm",
        "minimum": 0.0,
        "maximum": 2000.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Forecast value from a named, time-stamped meteorological source.",
    },
    "storm_distance_km": {
        "label": "Distance to storm centre",
        "unit": "km",
        "minimum": 0.0,
        "maximum": 2000.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Distance from a verified storm centre/track at its stated valid time.",
    },
    "coastal_surge_m": {
        "label": "Coastal water-level anomaly",
        "unit": "metres",
        "minimum": -20.0,
        "maximum": 20.0,
        "step": 0.01,
        "format": "%.2f",
        "help": "Measured or forecast anomaly with its station and vertical datum identified.",
    },
    "slope_degrees": {
        "label": "Ground slope",
        "unit": "degrees",
        "minimum": 0.0,
        "maximum": 90.0,
        "step": 0.1,
        "format": "%.1f",
        "help": "Measured or GIS-derived local slope; source and resolution affect comparability.",
    },
}

SIMPLE_INPUTS = {
    "rain": {
        "label": "How is the rain in your area?",
        "options": ("No rain", "Light", "Steady", "Heavy", "Very heavy", "I don't know"),
        "help": "Think about what you can see or feel nearby, not a forecast.",
    },
    "water_rising": {
        "label": "Is water rising near your area?",
        "options": (
            "No",
            "A little",
            "Rising quickly",
            "Already overflowing",
            "I don't know",
        ),
        "help": "Consider nearby streams, canals, drains, or standing water.",
    },
    "water_collecting": {
        "label": "Is water collecting near roads or homes?",
        "options": ("No", "In a few places", "Across roads or near homes", "I don't know"),
        "help": "Choose what you can see nearby; do not enter a flooded area to check.",
    },
    "wind": {
        "label": "How strong is the wind?",
        "options": ("Calm", "Breezy", "Strong", "Very strong", "I don't know"),
        "help": "For example, are trees or loose objects moving noticeably?",
    },
    "weather": {
        "label": "What is the weather like?",
        "options": ("Usual", "Hot", "Humid", "Stormy", "I don't know"),
        "help": "Choose the closest description of current conditions.",
    },
    "ground": {
        "label": "How wet is the ground?",
        "options": ("Dry", "Damp", "Wet", "Saturated", "I don't know"),
        "help": "Saturated means the ground is very wet or water is pooling.",
    },
    "unusual_changes": {
        "label": "Have you noticed unusual local changes?",
        "options": ("No", "Yes", "I don't know"),
        "help": "For example, sudden water rise, new cracks, or unusual drying.",
    },
    "storm_warning": {
        "label": "Have you heard an official cyclone or storm warning?",
        "options": ("No warning that I know of", "I heard an official warning", "I don't know"),
        "help": "This is your report only; the app does not fetch or verify live warnings.",
    },
    "slope_signs": {
        "label": "Have you noticed new cracks or ground movement on a slope?",
        "options": ("No", "Yes", "I don't know"),
        "help": "Do not approach an unstable slope to check.",
    },
    "recent_rainfall": {
        "label": "Has there been less rain than usual recently?",
        "options": ("About usual", "Less than usual", "Much less than usual", "I don't know"),
        "help": "Compare with what is usual for this area over recent weeks, not just today.",
    },
    "water_shortage": {
        "label": "Are you noticing a local water shortage?",
        "options": ("No", "Some shortage", "Serious shortage", "I don't know"),
        "help": "Consider local supply restrictions or unusually low water availability.",
    },
    "duration": {
        "label": "How long have these conditions lasted?",
        "options": (
            "Less than 1 hour",
            "1–3 hours",
            "3–6 hours",
            "More than 6 hours",
            "Several days",
            "I don't know",
        ),
        "help": "Choose how long the main rain, wind, or wet conditions have continued.",
    },
}

HAZARD_MODELS = {
    "flood": {
        "label": "Flood and Urban Waterlogging",
        "icon": "🌊",
        "features": (
            "rainfall_intensity_mm_h",
            "accumulated_rainfall_24h_mm",
            "accumulated_rainfall_72h_mm",
            "rainfall_duration_h",
            "water_level_m",
            "water_level_rise_m_h",
        ),
        "advanced_fields": (
            "rainfall_intensity_mm_h",
            "accumulated_rainfall_24h_mm",
            "accumulated_rainfall_72h_mm",
            "rainfall_duration_h",
            "rainfall_forecast_24h_mm",
            "water_level_m",
            "water_level_rise_m_h",
        ),
        "additional_requirements": (
            "Antecedent catchment rainfall, a verified local river-level trend and datum, "
            "drainage/tide context, and matched local flood and non-flood outcomes."
        ),
        "dataset_gap": (
            "No Ernakulam flood-occurrence dataset pairs issue-time measurements with "
            "verified flood and non-flood outcomes."
        ),
    },
    "cyclone": {
        "label": "Cyclone and Coastal Storm Impacts",
        "icon": "🌀",
        "features": (
            "wind_speed_kmh",
            "wind_gust_kmh",
            "pressure_hpa",
            "relative_humidity_percent",
            "storm_distance_km",
            "coastal_surge_m",
        ),
        "advanced_fields": (
            "wind_speed_kmh",
            "wind_gust_kmh",
            "pressure_hpa",
            "relative_humidity_percent",
            "temperature_c",
            "storm_distance_km",
            "coastal_surge_m",
        ),
        "additional_requirements": (
            "A time-stamped storm forecast track/intensity, distance and bearing to the "
            "coast, tide/surge or wave conditions, and verified local impact labels."
        ),
        "dataset_gap": (
            "Regional best tracks are not local impact labels or forecast-time track "
            "predictions for Ernakulam."
        ),
    },
    "landslide": {
        "label": "Landslide",
        "icon": "⛰️",
        "features": (
            "rainfall_intensity_mm_h",
            "accumulated_rainfall_24h_mm",
            "accumulated_rainfall_72h_mm",
            "rainfall_duration_h",
            "soil_moisture_percent",
            "slope_degrees",
        ),
        "advanced_fields": (
            "rainfall_intensity_mm_h",
            "accumulated_rainfall_24h_mm",
            "accumulated_rainfall_72h_mm",
            "rainfall_duration_h",
            "soil_moisture_percent",
            "slope_degrees",
        ),
        "additional_requirements": (
            "Antecedent 24/72-hour rainfall, slope, geology, land cover and a complete "
            "landslide inventory with defensible background locations."
        ),
        "dataset_gap": (
            "The available event catalogue is incomplete and does not provide verified "
            "non-event samples or reliable local susceptibility geometry."
        ),
    },
    "drought": {
        "label": "Drought and Water Scarcity",
        "icon": "☀️",
        "features": (
            "accumulated_rainfall_24h_mm",
            "rainfall_deficit_30d_percent",
            "rainfall_deficit_90d_percent",
            "soil_moisture_percent",
            "temperature_c",
            "relative_humidity_percent",
        ),
        "advanced_fields": (
            "accumulated_rainfall_24h_mm",
            "rainfall_deficit_30d_percent",
            "rainfall_deficit_90d_percent",
            "soil_moisture_percent",
            "temperature_c",
            "relative_humidity_percent",
        ),
        "additional_requirements": (
            "Multi-week/month rainfall deficits or SPI/SPEI, groundwater or reservoir "
            "availability, and a defined future drought target."
        ),
        "dataset_gap": (
            "No verified Ernakulam drought-index and water-availability time series "
            "paired with future drought outcomes is available."
        ),
    },
}

HAZARD_GUIDANCE = {
    "flood": {
        "missing": (
            "Verified local flood and non-flood outcomes paired with measurements "
            "taken before each event; gauge datum and drainage/tide context."
        ),
        "source_candidates": (
            {
                "name": "CWC/NWIC hourly rainfall observations",
                "url": "https://nwdp.nwic.gov.in/dataset/rainfall-cwc-telemetry-hourly",
                "status": "Candidate source; the local station file needs provenance and quality verification.",
            },
            {
                "name": "KSDMA flood hazard material",
                "url": "https://sdma.kerala.gov.in/hazard-maps/",
                "status": "Scenario/hazard context, not paired occurrence training labels.",
            },
        ),
        "next_step": (
            "Verify local gauge identities and datums, obtain dated flood impacts "
            "and non-event periods, then time-align only pre-event observations."
        ),
        "precaution": (
            "Keep away from fast-rising water; move to higher ground if local "
            "authorities advise evacuation."
        ),
    },
    "cyclone": {
        "missing": (
            "Time-stamped official storm forecast tracks/intensity paired with "
            "verified Ernakulam wind, surge, and damage/impact outcomes."
        ),
        "source_candidates": (
            {
                "name": "IMD cyclone bulletins and advisories",
                "url": "https://mausam.imd.gov.in/",
                "status": "Official current forecast source; not connected to automatic retrieval.",
            },
            {
                "name": "NOAA/NCEI IBTrACS best tracks",
                "url": "https://www.ncei.noaa.gov/products/international-best-track-archive",
                "status": "Regional historical tracks exist; they are not local impact labels or live forecasts.",
            },
        ),
        "next_step": (
            "Archive issue-time IMD bulletins and reconcile historical tracks with "
            "official district impact reports before defining a forecast target."
        ),
        "precaution": (
            "Follow IMD/KSDMA bulletins, secure loose outdoor items, and follow "
            "official coastal evacuation instructions."
        ),
    },
    "landslide": {
        "missing": (
            "A quality-controlled local landslide inventory, defensible background "
            "locations, valid terrain/susceptibility geometry, and antecedent rainfall."
        ),
        "source_candidates": (
            {
                "name": "KSDMA/GSI susceptibility map portal",
                "url": "https://sdma.kerala.gov.in/hazard-maps/",
                "status": "The project polygons fail geometry validation and cannot classify local areas.",
            },
            {
                "name": "NASA Global Landslide Catalog",
                "url": "https://data.nasa.gov/",
                "status": "Sparse, reporting-biased reports; not a complete local inventory.",
            },
        ),
        "next_step": (
            "Request a valid GSI/KSDMA inventory and terrain layers, then reconcile "
            "event locations and dates with rainfall records."
        ),
        "precaution": (
            "Stay clear of fresh cracks, leaning trees, or new slope movement; "
            "move away from slopes if conditions appear unsafe."
        ),
    },
    "drought": {
        "missing": (
            "A defined future drought target plus long-term rainfall-deficit, "
            "groundwater/reservoir, and water-supply impact observations."
        ),
        "source_candidates": (
            {
                "name": "India Drought Monitor",
                "url": "https://indiadroughtmonitor.in/",
                "status": "Candidate source identified; verified Ernakulam time-series coverage has not been established.",
            },
            {
                "name": "IMD rainfall observations",
                "url": "https://dsp.imdpune.gov.in/",
                "status": "Historical data service; district series, access, and reuse conditions need verification.",
            },
        ),
        "next_step": (
            "Define meteorological and water-scarcity outcomes, then assemble "
            "multi-year district rainfall and water-availability series."
        ),
        "precaution": (
            "Use water carefully and follow local water-supply or public-health "
            "advice; this page does not determine water safety."
        ),
    },
}

INPUT_MODEL_RECORDS_USED = {hazard_id: 0 for hazard_id in HAZARD_MODELS}

IMD_DAILY_RAINFALL_REFERENCE = {
    "name": "India Meteorological Department rainfall categories",
    "url": "https://mausam.imd.gov.in/responsive/monsooninformation.php",
    "thresholds_mm": {
        "heavy": 64.5,
        "very_heavy": 115.6,
        "extremely_heavy": 204.5,
    },
}


class InputValidationError(ValueError):
    """Raised when a submitted environmental reading is missing or invalid."""

    def __init__(self, errors: Mapping[str, str]):
        self.errors = dict(errors)
        super().__init__("; ".join(self.errors.values()))


def load_hazard_evidence_context(hazard_id: str) -> dict[str, Any]:
    """Load verified Ernakulam context without treating it as a live observation."""
    if hazard_id not in HAZARD_MODELS:
        raise ValueError(f"Unsupported hazard: {hazard_id!r}")

    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if evidence.get("district") != "Ernakulam" or evidence.get("state") != "Kerala":
        raise ValueError("Hazard evidence must be scoped to Ernakulam, Kerala.")
    records = {
        record.get("id"): record
        for record in evidence.get("hazards", [])
        if isinstance(record, dict)
    }
    if set(records) != set(HAZARD_MODELS):
        raise ValueError("Evidence inventory must match the four supported hazards.")

    record = records[hazard_id]
    context = {
        "status": record["status"],
        "observation_period": record["observation_period"],
        "spatial_coverage": record["spatial_coverage"],
        "record_coverage": record["record_coverage"],
        "key_findings": list(record["key_findings"]),
        "uncertainty": record["uncertainty"],
        "seasonal_pattern": record["seasonal_pattern"],
        "seasonal_pattern_gap": record["seasonal_pattern_gap"],
        "sources": list(record["sources"]),
    }
    if hazard_id == "flood":
        flood_statistics = json.loads(
            FLOOD_STATISTICS_PATH.read_text(encoding="utf-8")
        )
        if flood_statistics.get("geographic_coverage") != (
            "Ernakulam district aggregate, not Kochi Corporation or individual wards"
        ):
            raise ValueError("Flood scenario statistics are not verified district aggregates.")
        context["historical_scenario"] = list(
            flood_statistics["historical_scenario"]
        )
        context["source_retrieved_on"] = flood_statistics["retrieved_on"]
    return context


def validate_location(location: str) -> None:
    """Reject any location not in the verified Ernakulam-only selector."""
    if location not in location_options(load_location_registry()):
        raise ValueError("Select a verified location within Ernakulam district.")


def validate_environmental_inputs(
    values: Mapping[str, Any],
    water_level_reference: str = "",
    required_fields: tuple[str, ...] = (),
) -> dict[str, float]:
    """Validate supplied readings; missing optional measurements remain absent."""
    errors: dict[str, str] = {}
    cleaned: dict[str, float] = {}
    unknown_fields = set(values) - set(INPUTS)
    if unknown_fields:
        raise InputValidationError(
            {name: f"Unsupported environmental input: {name}." for name in unknown_fields}
        )
    for field, specification in INPUTS.items():
        if field not in values:
            continue
        raw_value = values[field]
        if raw_value is None or (isinstance(raw_value, str) and not raw_value.strip()):
            continue
        if isinstance(raw_value, bool):
            errors[field] = f"{specification['label']} must be a number."
            continue
        try:
            numeric_value = float(raw_value)
        except (TypeError, ValueError):
            errors[field] = f"{specification['label']} must be a number."
            continue
        if not math.isfinite(numeric_value):
            errors[field] = f"{specification['label']} must be finite."
        elif not specification["minimum"] <= numeric_value <= specification["maximum"]:
            errors[field] = (
                f"{specification['label']} must be between "
                f"{specification['minimum']:g} and {specification['maximum']:g} "
                f"{specification['unit']}."
            )
        else:
            cleaned[field] = numeric_value

    for field in required_fields:
        if field not in cleaned:
            specification = INPUTS.get(field)
            label = specification["label"] if specification else field
            errors[field] = f"Enter the required model input: {label}."
    datum_fields = {"water_level_m", "water_level_rise_m_h", "coastal_surge_m"}
    if datum_fields.intersection(cleaned) and (
        not isinstance(water_level_reference, str) or not water_level_reference.strip()
    ):
        errors["water_level_reference"] = (
            "Name the monitoring station and measurement datum/reference for water levels."
        )
    if errors:
        raise InputValidationError(errors)
    return cleaned


def validate_simple_observations(
    observations: Mapping[str, Any],
    required_fields: set[str] | None = None,
) -> dict[str, str]:
    """Validate qualitative choices without mapping them to numeric measurements."""
    errors = {}
    validated = {}
    fields_to_validate = required_fields or set(SIMPLE_INPUTS)
    for key in fields_to_validate:
        specification = SIMPLE_INPUTS[key]
        value = observations.get(key)
        if value is None:
            errors[key] = f"Choose an answer for: {specification['label']}"
        elif value not in specification["options"]:
            errors[key] = f"Choose a listed answer for: {specification['label']}"
        else:
            validated[key] = value
    unknown_fields = set(observations) - set(SIMPLE_INPUTS)
    for key in unknown_fields:
        errors[key] = f"Unsupported simple observation: {key}."
    if errors:
        raise InputValidationError(errors)
    return validated


def validate_assessment_observations(
    observations: Mapping[str, Any],
) -> dict[str, str]:
    """Validate optional qualitative context without creating numeric features."""
    errors: dict[str, str] = {}
    validated: dict[str, str] = {}
    for key, value in observations.items():
        specification = SIMPLE_INPUTS.get(key)
        if specification is None:
            errors[key] = f"Unsupported assessment observation: {key}."
        elif value is None or (isinstance(value, str) and not value.strip()):
            continue
        elif value not in specification["options"]:
            errors[key] = f"Choose a listed answer for: {specification['label']}"
        else:
            validated[key] = value
    if errors:
        raise InputValidationError(errors)
    return validated


def validate_observation_time(value: datetime) -> datetime:
    if not isinstance(value, datetime):
        raise InputValidationError(
            {"observation_time": "Enter the date and time these conditions were observed."}
        )
    if value.tzinfo is not None:
        raise InputValidationError(
            {"observation_time": "Enter the observed local date and time in India Standard Time."}
        )
    return value


def _simple_features_from_validated_mapping(
    hazard_id: str,
    feature_names: list[str],
    observations: Mapping[str, str],
    metadata: Mapping[str, Any],
) -> tuple[dict[str, float] | None, str | None]:
    mapping = metadata.get("simple_mode_mapping")
    if (
        not isinstance(mapping, Mapping)
        or mapping.get("validated") is not True
        or not isinstance(mapping.get("mapping_id"), str)
        or not mapping["mapping_id"].strip()
        or not isinstance(mapping.get("evidence_reference"), str)
        or not mapping["evidence_reference"].strip()
    ):
        return None, (
            "No scientifically validated Simple Mode mapping exists for this model; "
            "qualitative answers were not converted to measurements."
        )
    feature_mappings = mapping.get("feature_mappings")
    if not isinstance(feature_mappings, Mapping):
        return None, "The model's Simple Mode mapping is incomplete."

    translated: dict[str, float] = {}
    for feature in feature_names:
        feature_mapping = feature_mappings.get(feature)
        if not isinstance(feature_mapping, Mapping):
            return None, f"The Simple Mode mapping does not cover required feature {feature}."
        answer_field = feature_mapping.get("answer_field")
        value_map = feature_mapping.get("value_map")
        if answer_field not in SIMPLE_INPUTS or not isinstance(value_map, Mapping):
            return None, f"The Simple Mode mapping for {feature} is invalid."
        answer = observations.get(answer_field)
        if answer is None or answer == "I don't know":
            continue
        if answer not in value_map:
            return None, (
                f"The selected Simple Mode answer has no validated mapping for {feature}."
            )
        mapped_value = value_map[answer]
        if (
            isinstance(mapped_value, bool)
            or not isinstance(mapped_value, (int, float))
            or not math.isfinite(mapped_value)
        ):
            return None, f"The Simple Mode mapping for {feature} is not numeric."
        limits = INPUTS.get(feature)
        if limits and not limits["minimum"] <= mapped_value <= limits["maximum"]:
            return None, f"The Simple Mode mapping for {feature} is outside its valid range."
        translated[feature] = float(mapped_value)
    return translated, None


def model_artifact_path(hazard_id: str) -> Path:
    if hazard_id not in HAZARD_MODELS:
        raise ValueError(f"Unsupported hazard model: {hazard_id!r}")
    return MODEL_DIRECTORY / f"{hazard_id}.joblib"


def load_hazard_model(hazard_id: str) -> Mapping[str, Any] | None:
    """Load a hazard-specific model bundle; absent artifacts are not predictions."""
    path = model_artifact_path(hazard_id)
    if not path.is_file():
        return None
    from joblib import load

    bundle = load(path)
    if not isinstance(bundle, Mapping):
        raise ValueError(f"Model artifact {path} is not a model bundle.")
    if bundle.get("hazard_id") != hazard_id:
        raise ValueError(f"Model artifact {path} is registered for another hazard.")
    if not callable(getattr(bundle.get("model"), "predict_proba", None)):
        raise ValueError(f"Model artifact {path} has no probability estimator.")
    return bundle


def _validated_model_metadata(
    hazard_id: str,
    location: str,
    bundle: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, str | None]:
    metadata = bundle.get("metadata")
    if not isinstance(metadata, Mapping):
        return None, "The model artifact has no validation metadata."
    if (
        metadata.get("district") != "Ernakulam"
        or metadata.get("hazard_id") != hazard_id
        or metadata.get("model_status") != "validated"
        or metadata.get("evidence_status") != "verified"
    ):
        return None, "The model is not validated for this hazard and district."

    scope = metadata.get("geographic_scope")
    supported_locations = metadata.get("supported_locations")
    if not isinstance(supported_locations, list) or location not in supported_locations:
        return None, "No validated model coverage exists for the selected location."
    if scope == "district" and location != "Ernakulam district (all areas)":
        return None, "This model only supports a district-level result, not this locality."
    if scope not in {"district", "locality"}:
        return None, "The model's geographic scope is not established."

    validation = metadata.get("evaluation")
    if not isinstance(validation, Mapping) or any(
        validation.get(gate) is not True
        for gate in (
            "chronological_validation",
            "calibration_checked",
            "probabilities_calibrated",
            "beats_baselines",
        )
    ):
        return None, "Chronological validation, calibration, or baseline checks failed."
    training = metadata.get("training")
    if (
        not isinstance(training, Mapping)
        or not isinstance(training.get("dataset_id"), str)
        or not training["dataset_id"].strip()
        or training.get("source_manifest_verified") is not True
    ):
        return None, "The model has no training-data record."
    record_counts = {}
    for count_name in ("genuine_records", "positive_records", "negative_records"):
        count = training.get(count_name)
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            return None, "The model lacks genuine positive and negative training records."
        record_counts[count_name] = count
    if (
        record_counts["positive_records"] + record_counts["negative_records"]
        > record_counts["genuine_records"]
    ):
        return None, "The training record counts are inconsistent."

    metrics = metadata.get("metrics")
    metric_names = ("precision", "recall", "f1", "roc_auc", "pr_auc", "brier_score")
    if not isinstance(metrics, Mapping) or any(
        isinstance(metrics.get(name), bool)
        or not isinstance(metrics.get(name), (int, float))
        or not math.isfinite(metrics[name])
        or not 0 <= metrics[name] <= 1
        for name in metric_names
    ):
        return None, "Required held-out classification and calibration metrics are missing."
    baseline_metrics = metadata.get("baseline_metrics")
    if not isinstance(baseline_metrics, Mapping) or any(
        isinstance(baseline_metrics.get(name), bool)
        or not isinstance(baseline_metrics.get(name), (int, float))
        or not math.isfinite(baseline_metrics[name])
        or not 0 <= baseline_metrics[name] <= 1
        for name in ("f1", "pr_auc", "brier_score")
    ):
        return None, "A simple held-out baseline comparison is missing."

    feature_names = metadata.get("feature_names")
    if (
        not isinstance(feature_names, list)
        or not feature_names
        or tuple(feature_names) != HAZARD_MODELS[hazard_id]["features"]
    ):
        return None, "The model feature schema does not match this hazard's reviewed inputs."
    if not isinstance(metadata.get("target_definition"), str) or not metadata[
        "target_definition"
    ].strip():
        return None, "The model's event target is not defined."
    if not isinstance(metadata.get("forecast_horizon"), str) or not metadata[
        "forecast_horizon"
    ].strip():
        return None, "The model's forecast horizon is not defined."
    if not isinstance(metadata.get("plain_language_explanation"), str) or not metadata[
        "plain_language_explanation"
    ].strip():
        return None, "A reviewed plain-language explanation is missing."
    if not isinstance(metadata.get("confidence"), str) or not metadata[
        "confidence"
    ].strip():
        return None, "The model's confidence assessment is missing."
    thresholds = metadata.get("risk_thresholds")
    if not isinstance(thresholds, Mapping):
        return None, "Evaluation-based risk thresholds are missing."
    values = [thresholds.get(key) for key in ("moderate", "high", "very_high")]
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values):
        return None, "Evaluation-based risk thresholds are invalid."
    if not 0 <= values[0] < values[1] < values[2] <= 1:
        return None, "Evaluation-based risk thresholds are invalid."
    if not isinstance(metadata.get("risk_threshold_basis"), str) or not metadata[
        "risk_threshold_basis"
    ].strip():
        return None, "The model's risk-threshold basis is missing."
    return metadata, None


def _risk_label(probability: float, thresholds: Mapping[str, float]) -> str:
    if probability >= thresholds["very_high"]:
        return "Very High"
    if probability >= thresholds["high"]:
        return "High"
    if probability >= thresholds["moderate"]:
        return "Moderate"
    return "Low"


def validated_probability(result: Mapping[str, Any]) -> float | None:
    """Return only a finite probability from a validated prediction result."""
    if not isinstance(result, Mapping) or result.get("status") != "validated_prediction":
        return None
    probability = result.get("probability")
    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
        return None
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        return None
    return float(probability)


def _rainfall_context(amount_mm: float) -> str:
    thresholds = IMD_DAILY_RAINFALL_REFERENCE["thresholds_mm"]
    if amount_mm >= thresholds["extremely_heavy"]:
        return "extremely heavy"
    if amount_mm >= thresholds["very_heavy"]:
        return "very heavy"
    if amount_mm >= thresholds["heavy"]:
        return "heavy"
    return "below the IMD heavy-rainfall threshold"


def _preliminary_assessment(
    hazard_id: str,
    location: str,
    inputs: Mapping[str, float],
    observations: Mapping[str, str] | None,
    *,
    input_mode: str,
    observation_time: datetime | None,
    model_note: str | None = None,
) -> dict[str, Any]:
    """Create a rule-based concern tier without presenting it as likelihood."""
    observations = observations or {}
    hazard = HAZARD_MODELS[hazard_id]
    guidance = HAZARD_GUIDANCE[hazard_id]
    factors: list[str] = []
    missing: list[str] = []
    risk_label = "Not enough evidence"
    basis = "No validated local scoring scale or calibrated probability is available."

    rain = observations.get("rain")
    duration = observations.get("duration")
    heavy_rain = rain in {"Heavy", "Very heavy"}
    long_rain = duration in {"More than 6 hours", "Several days"}
    rainfall_24h = inputs.get("accumulated_rainfall_24h_mm")

    if hazard_id == "flood":
        rising = observations.get("water_rising")
        collecting = observations.get("water_collecting")
        if rising == "Already overflowing" or collecting == "Across roads or near homes":
            risk_label = "Very High"
            factors.append("You reported overflowing water or water across roads/near homes.")
        elif rising == "Rising quickly":
            risk_label = "High"
            factors.append("You reported nearby water rising quickly.")
        elif rising == "A little" or collecting == "In a few places":
            risk_label = "Moderate"
            factors.append("You reported some nearby water rise or pooling.")
        elif (
            inputs.get("water_level_rise_m_h") is not None
            and inputs["water_level_rise_m_h"] > 0
        ):
            risk_label = "Moderate"
            factors.append("The entered gauge reading shows water rising.")
        elif heavy_rain:
            risk_label = "Moderate"
            factors.append(
                f"You reported {rain.lower()} rain; this is a flood-contributing condition, "
                "not evidence that flooding has occurred."
            )
        elif (
            rising == "No"
            and collecting == "No"
            and rain in {"No rain", "Light"}
        ):
            risk_label = "Low"
            factors.append("You reported no nearby water rise or pooling and little/no rain.")
        else:
            missing.append(
                "Current nearby water behaviour (rising, pooling, or overflowing)."
            )
        if rainfall_24h is not None:
            factors.append(
                f"Entered 24-hour rainfall is {rainfall_24h:g} mm "
                f"({_rainfall_context(rainfall_24h)} by IMD daily categories)."
            )
        if inputs.get("rainfall_forecast_24h_mm") is not None:
            factors.append(
                "Entered next-24-hour rainfall forecast: "
                f"{inputs['rainfall_forecast_24h_mm']:g} mm; its source and valid time "
                "are not independently verified."
            )
        if rising in {"I don't know", None} or collecting in {"I don't know", None}:
            missing.append("A verified local gauge level/trend and drainage/tide context.")
        basis = (
            "The tier prioritizes directly reported local water impacts; rainfall is "
            "context only. It is not a forecast of flood occurrence."
        )

    elif hazard_id == "cyclone":
        warning = observations.get("storm_warning")
        wind = observations.get("wind")
        if warning == "I heard an official warning" and wind == "Very strong":
            risk_label = "Very High"
            factors.extend(
                (
                    "You reported an official storm warning (not verified by this app).",
                    "You reported very strong local wind.",
                )
            )
        elif warning == "I heard an official warning":
            risk_label = "High"
            factors.append("You reported an official storm warning; this app cannot verify it.")
        elif wind == "Very strong":
            risk_label = "High"
            factors.append("You reported very strong local wind; this does not establish a cyclone.")
        elif wind == "Strong" or (wind == "Breezy" and observations.get("weather") == "Stormy"):
            risk_label = "Moderate"
            factors.append("You reported storm-like local wind/weather conditions.")
        elif warning == "No warning that I know of" and wind == "Calm":
            risk_label = "Low"
            factors.append("You reported calm local wind and no warning known to you.")
        elif warning == "I don't know" or wind in {None, "I don't know"}:
            missing.append("A time-stamped IMD storm track/warning and coastal exposure information.")
        else:
            missing.append("Verified storm-track, wind, and coastal water-level information.")
        if inputs.get("wind_speed_kmh") is not None:
            factors.append(f"Entered sustained wind: {inputs['wind_speed_kmh']:g} km/h.")
        if inputs.get("wind_gust_kmh") is not None:
            factors.append(f"Entered maximum gust: {inputs['wind_gust_kmh']:g} km/h.")
        if inputs.get("storm_distance_km") is not None:
            factors.append(
                f"Entered storm-centre distance: {inputs['storm_distance_km']:g} km; "
                "track source and valid time are not verified here."
            )
        basis = (
            "This is a local storm-condition precaution tier, not cyclone detection. "
            "A reported warning is user-entered and is not fetched or verified."
        )

    elif hazard_id == "landslide":
        slope_signs = observations.get("slope_signs")
        ground = observations.get("ground")
        if slope_signs == "Yes":
            risk_label = "Very High"
            factors.append("You reported new cracks or ground movement on a slope.")
        elif heavy_rain and ground == "Saturated":
            risk_label = "High"
            factors.append(
                f"You reported {rain.lower()} rain and saturated ground, which can "
                "increase slope concern."
            )
        elif (heavy_rain and ground in {"Wet", "Saturated"}) or (
            rain == "Steady" and ground == "Saturated"
        ):
            risk_label = "Moderate"
            factors.append("You reported wet ground with ongoing/heavy rain.")
        elif (
            slope_signs == "No"
            and ground == "Dry"
            and rain in {"No rain", "Light"}
        ):
            risk_label = "Low"
            factors.append("You reported dry ground, little/no rain, and no new slope signs.")
        else:
            missing.append("Recent slope-specific rainfall and signs of slope movement.")
        if rainfall_24h is not None:
            factors.append(
                f"Entered 24-hour rainfall: {rainfall_24h:g} mm "
                f"({_rainfall_context(rainfall_24h)} by IMD daily categories)."
            )
        if inputs.get("accumulated_rainfall_72h_mm") is not None:
            factors.append(
                f"Entered 72-hour rainfall: "
                f"{inputs['accumulated_rainfall_72h_mm']:g} mm."
            )
        if inputs.get("slope_degrees") is not None:
            factors.append(
                f"Entered slope: {inputs['slope_degrees']:g} degrees; geology and "
                "verified susceptibility are not available."
            )
        if slope_signs in {None, "I don't know"}:
            missing.append("A verified local landslide inventory, geology, and susceptibility map.")
        basis = (
            "The tier reflects reported slope warning signs and wet-ground/rain "
            "combinations. It is not a landslide forecast or susceptibility map."
        )

    elif hazard_id == "drought":
        rainfall_departure = observations.get("recent_rainfall")
        shortage = observations.get("water_shortage")
        hot_weather = observations.get("weather") == "Hot"
        if shortage == "Serious shortage" and rainfall_departure in {
            "Less than usual",
            "Much less than usual",
        }:
            risk_label = "Very High"
            factors.extend(
                (
                    "You reported serious local water shortage.",
                    f"You reported {rainfall_departure.lower()} rainfall recently.",
                )
            )
        elif shortage == "Some shortage" and rainfall_departure == "Much less than usual":
            risk_label = "High"
            factors.append("You reported both water shortage and much less-than-usual rain.")
        elif shortage == "Some shortage" or (
            rainfall_departure in {"Less than usual", "Much less than usual"} and hot_weather
        ):
            risk_label = "Moderate"
            factors.append("You reported a water-supply or sustained-dryness concern.")
        elif (
            shortage == "No"
            and rainfall_departure == "About usual"
            and not hot_weather
        ):
            risk_label = "Low"
            factors.append("You reported usual rainfall and no local water shortage.")
        else:
            missing.append("Recent rainfall compared with local normals and local water availability.")
        for field in ("rainfall_deficit_30d_percent", "rainfall_deficit_90d_percent"):
            if field in inputs:
                factors.append(
                    f"Entered {INPUTS[field]['label'].lower()}: {inputs[field]:g}%."
                )
        if inputs.get("soil_moisture_percent") is not None:
            factors.append(
                f"Entered sensor soil moisture: {inputs['soil_moisture_percent']:g}%."
            )
        if shortage in {None, "I don't know"}:
            missing.append("Reservoir/groundwater status and verified supply-impact data.")
        basis = (
            "This tier uses reported rainfall departure and water-supply impacts. "
            "A drought index and water-resource observations are not retrieved."
        )

    else:
        raise ValueError(f"Unsupported hazard: {hazard_id!r}")

    if long_rain and rain in {"Heavy", "Very heavy"} and hazard_id in {"flood", "landslide"}:
        factors.append(f"You reported these rain conditions lasting {duration.lower()}.")
    if not factors:
        factors.append("No hazard-specific concerning condition was supplied for this assessment.")
    if not missing:
        missing.extend(
            (
                "Time-stamped local observations from an authoritative source.",
                "Validated hazard-specific local thresholds and exposure data.",
            )
        )

    explanation = (
        " ".join(factors)
        if risk_label != "Not enough evidence"
        else (
            "The available entries do not establish this hazard's local indicators. "
            + " ".join(factors)
        )
    )
    limitations = [
        "This is a preliminary rule-based assessment of entered/reported conditions, "
        "not a validated forecast or probability.",
        "No live IMD, KSDMA, CWC, gauge, or sensor observations were retrieved.",
        "The selected administrative location is not independently covered by a local model.",
    ]
    if model_note:
        limitations.append(f"Machine-learning model not used: {model_note}")

    return {
        "hazard_id": hazard_id,
        "hazard_name": hazard["label"],
        "icon": hazard["icon"],
        "location": location,
        "probability": None,
        "risk_score": None,
        "risk_label": risk_label,
        "status": "preliminary_assessment",
        "assessment_method": "Preliminary rule-based assessment",
        "forecast_horizon": "Current entered conditions; not a future forecast",
        "confidence": "Limited — user-entered information only",
        "explanation": explanation,
        "contributing_conditions": factors,
        "missing_information": missing,
        "precautions": guidance["precaution"],
        "limitations": limitations,
        "assessment_basis": basis,
        "status_reason": (
            f"Machine-learning model not used: {model_note}"
            if model_note
            else "No eligible calibrated Ernakulam model was available."
        ),
        "sources": (
            [IMD_DAILY_RAINFALL_REFERENCE]
            if hazard_id in {"flood", "landslide"}
            else []
        ),
        "reference_evidence": load_hazard_evidence_context(hazard_id),
        "additional_requirements": hazard["additional_requirements"],
        "data_quality": "User-entered; not independently verified or calibrated.",
        "input_mode": input_mode,
        "observation_time": observation_time.isoformat() if observation_time else None,
    }


def predict_hazard(
    hazard_id: str,
    location: str,
    inputs: Mapping[str, float],
    model_bundle: Mapping[str, Any] | None = None,
    *,
    input_mode: str = "advanced",
    simple_observations: Mapping[str, str] | None = None,
    water_level_reference: str = "",
    observation_time: datetime | None = None,
    assessment_observations: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Use a validated model when eligible; otherwise return a guarded assessment."""
    if hazard_id not in HAZARD_MODELS:
        raise ValueError(f"Unsupported hazard: {hazard_id!r}")
    if input_mode not in {"simple", "advanced"}:
        raise ValueError(f"Unsupported input mode: {input_mode!r}")
    validate_location(location)
    if observation_time is not None:
        validate_observation_time(observation_time)
    if input_mode == "advanced":
        inputs = validate_environmental_inputs(inputs, water_level_reference)
        clean_observations = validate_assessment_observations(assessment_observations or {})
    elif simple_observations is not None:
        hazard_simple_fields = {
            "flood": {"rain", "water_rising", "water_collecting", "duration"},
            "cyclone": {"wind", "weather", "storm_warning"},
            "landslide": {"ground", "slope_signs", "unusual_changes"},
            "drought": {"recent_rainfall", "water_shortage"},
        }
        simple_observations = validate_simple_observations(
            simple_observations,
            required_fields=hazard_simple_fields[hazard_id],
        )
        clean_observations = simple_observations
    else:
        clean_observations = {}
    specification = HAZARD_MODELS[hazard_id]
    bundle = model_bundle if model_bundle is not None else load_hazard_model(hazard_id)
    if bundle is None:
        return _preliminary_assessment(
            hazard_id,
            location,
            inputs,
            clean_observations,
            input_mode=input_mode,
            observation_time=observation_time,
            model_note="no eligible Ernakulam model artifact is registered.",
        )

    metadata, rejection_reason = _validated_model_metadata(hazard_id, location, bundle)
    if rejection_reason:
        return _preliminary_assessment(
            hazard_id,
            location,
            inputs,
            clean_observations,
            input_mode=input_mode,
            observation_time=observation_time,
            model_note=rejection_reason,
        )

    estimator = bundle["model"]
    feature_names = metadata["feature_names"]
    model_inputs: Mapping[str, float] = inputs
    if input_mode == "simple":
        if simple_observations is None:
            return _preliminary_assessment(
                hazard_id, location, inputs, clean_observations, input_mode=input_mode,
                observation_time=observation_time,
                model_note="Simple Mode answers are required by the model.",
            )
        model_inputs, mapping_error = _simple_features_from_validated_mapping(
            hazard_id,
            feature_names,
            simple_observations,
            metadata,
        )
        if mapping_error:
            return _preliminary_assessment(
                hazard_id,
                location,
                inputs,
                clean_observations,
                input_mode=input_mode,
                observation_time=observation_time,
                model_note=mapping_error,
            )
    missing_features = [name for name in feature_names if name not in model_inputs]
    if missing_features:
        return _preliminary_assessment(
            hazard_id,
            location,
            inputs,
            clean_observations,
            input_mode=input_mode,
            observation_time=observation_time,
            model_note=(
                "required inputs are missing or marked unknown: "
                + ", ".join(missing_features)
            ),
        )

    frame = pd.DataFrame([{name: model_inputs[name] for name in feature_names}])
    probabilities = estimator.predict_proba(frame)
    classes = list(getattr(estimator, "classes_", []))
    if 1 not in classes:
        raise ValueError(f"The {hazard_id} model has no positive event class.")
    positive_probability = float(probabilities[0][classes.index(1)])
    if not math.isfinite(positive_probability) or not 0 <= positive_probability <= 1:
        raise ValueError(f"The {hazard_id} model returned an invalid probability.")

    thresholds = metadata["risk_thresholds"]
    return {
        "hazard_id": hazard_id,
        "hazard_name": specification["label"],
        "icon": specification["icon"],
        "location": location,
        "probability": positive_probability,
        "risk_score": None,
        "risk_label": _risk_label(positive_probability, thresholds),
        "status": "validated_prediction",
        "assessment_method": "Validated ML",
        "forecast_horizon": metadata["forecast_horizon"],
        "confidence": metadata["confidence"],
        "explanation": metadata["plain_language_explanation"],
        "contributing_conditions": [],
        "missing_information": [],
        "precautions": HAZARD_GUIDANCE[hazard_id]["precaution"],
        "limitations": [metadata["target_definition"]],
        "assessment_basis": metadata["risk_threshold_basis"],
        "additional_requirements": specification["additional_requirements"],
        "reference_evidence": load_hazard_evidence_context(hazard_id),
        "data_quality": metadata["confidence"],
        "input_mode": input_mode,
        "observation_time": observation_time.isoformat() if observation_time else None,
        "metrics": metadata["metrics"],
    }


def predict_all_hazards(
    location: str,
    values: Mapping[str, Any],
    water_level_reference: str = "",
    *,
    input_mode: str = "advanced",
    simple_observations: Mapping[str, Any] | None = None,
    observation_time: datetime | None = None,
    assessment_observations: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Validate either mode and run the same four hazard-specific pipelines."""
    validate_location(location)
    if observation_time is not None:
        validate_observation_time(observation_time)
    if input_mode == "advanced":
        clean_inputs = validate_environmental_inputs(values, water_level_reference)
        clean_observations = None
        clean_assessment_observations = validate_assessment_observations(
            assessment_observations or {}
        )
    elif input_mode == "simple":
        clean_inputs = {}
        clean_observations = validate_simple_observations(simple_observations or {})
        clean_assessment_observations = clean_observations
    else:
        raise ValueError(f"Unsupported input mode: {input_mode!r}")
    return [
        predict_hazard(
            hazard_id,
            location,
            clean_inputs,
            input_mode=input_mode,
            simple_observations=clean_observations,
            water_level_reference=water_level_reference,
            observation_time=observation_time,
            assessment_observations=clean_assessment_observations,
        )
        for hazard_id in HAZARD_MODELS
    ]


def data_readiness_summary() -> dict[str, Any]:
    """Describe the active model registry without implying historical evidence is a model."""
    registry_path = ROOT / "reports" / "hazard_dataset_readiness.json"
    if not registry_path.is_file():
        raise FileNotFoundError(f"Expected hazard data-readiness report: {registry_path}")
    readiness = json.loads(registry_path.read_text(encoding="utf-8"))
    return {
        "input_model_records_used": dict(INPUT_MODEL_RECORDS_USED),
        "registered_artifacts": {
            hazard_id: model_artifact_path(hazard_id).is_file()
            for hazard_id in HAZARD_MODELS
        },
        "dataset_readiness_status": readiness.get("status", "not reported"),
    }


def prediction_ready_hazards(location: str) -> dict[str, dict[str, Any]]:
    """Return only hazards with a genuinely validated model for ``location``.

    Presence of a CSV, raw catalogue, or research baseline is deliberately not
    sufficient.  The same artifact and metadata gates used at prediction time
    are evaluated here so the UI cannot offer a hazard that will later fall
    back to a qualitative assessment.
    """
    validate_location(location)
    ready: dict[str, dict[str, Any]] = {}
    for hazard_id, specification in HAZARD_MODELS.items():
        try:
            bundle = load_hazard_model(hazard_id)
        except (OSError, ValueError, TypeError, ImportError) as error:
            continue
        if bundle is None:
            continue
        metadata, rejection_reason = _validated_model_metadata(hazard_id, location, bundle)
        if rejection_reason or metadata is None:
            continue
        ready[hazard_id] = {
            "label": specification["label"],
            "icon": specification["icon"],
            "forecast_horizon": metadata["forecast_horizon"],
            "confidence": metadata["confidence"],
        }
    return ready


def prediction_unavailable_reasons(location: str) -> dict[str, str]:
    """Explain why hazards are absent without treating them as predictions."""
    validate_location(location)
    reasons: dict[str, str] = {}
    for hazard_id, specification in HAZARD_MODELS.items():
        try:
            bundle = load_hazard_model(hazard_id)
        except (OSError, ValueError, TypeError, ImportError) as error:
            reasons[specification["label"]] = f"Model artifact could not be validated: {error}"
            continue
        if bundle is None:
            reasons[specification["label"]] = (
                f"No validated {hazard_id} artifact; {specification['dataset_gap']}"
            )
            continue
        _, rejection_reason = _validated_model_metadata(hazard_id, location, bundle)
        if rejection_reason:
            reasons[specification["label"]] = rejection_reason
    return reasons

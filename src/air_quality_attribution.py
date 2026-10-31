"""Evidence gate for future industrial source-attribution work.

This module deliberately does not score or rank facilities. It exposes the
minimum evidence domains that must be reviewed before a ranking can be made.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from datetime import date
from urllib.parse import urlsplit

import pandas as pd

from src.air_quality import AirQualityDataError, SUPPORTED_POLLUTANTS, validate_observations


SOURCE_EVIDENCE_REQUIREMENTS = {
    "observation_window": "A validated pollutant observation with a stated averaging window and time precision suitable for transport analysis.",
    "facility_locations": "Verified facility-specific coordinates with a stated coordinate reference system.",
    "pollutant_emissions": "Pollutant-specific emissions or stack measurements with dates and units.",
    "source_signatures": "Evidence linking candidate process emissions to the observed pollutant or pollutant mixture.",
    "time_aligned_meteorology": "Meteorology aligned to the observation averaging window, including wind speed and direction.",
    "alternatives_and_background": "A competing-source inventory and background/traffic context for the same period.",
    "transport_method": "A documented transport or dispersion method with limitations stated.",
}

INSUFFICIENT_ATTRIBUTION_MESSAGE = (
    "Insufficient evidence to reliably identify the pollution source."
)
AMBIENT_EVIDENCE_TYPES = {"measured", "estimated", "illustrative", "unverified", "missing"}

SOURCE_EVIDENCE_ACTIONS = {
    "observation_window": "Obtain station-specific timestamps, averaging periods, valid-hour counts and row-level QA flags from the monitoring authority.",
    "facility_locations": "Obtain facility-specific coordinates from an authoritative record, including the coordinate reference system and retrieval date.",
    "pollutant_emissions": "Obtain dated, pollutant-specific measured stack-test results with units, reporting authority and source document. Permit limits are not measurements.",
    "source_signatures": "Obtain independently reviewed process or emissions evidence that documents a plausible pollutant signature for the specific facility.",
    "time_aligned_meteorology": "Obtain quality-reviewed wind speed and direction with timestamps, averaging periods, verified monitoring-site location and source provenance matching the ambient observation window.",
    "alternatives_and_background": "Document background concentrations and competing sources such as traffic and other industrial activity for the same place and period.",
    "transport_method": "Specify a scientifically reviewed transport or dispersion method, its input data, assumptions, validation and limitations.",
}


def evidence_action_plan(evidence: Mapping[str, bool]) -> list[dict[str, str]]:
    """Explain every evidence gate and give a concrete next data request."""
    unknown = set(evidence) - set(SOURCE_EVIDENCE_REQUIREMENTS)
    if unknown:
        raise ValueError("Unknown source-evidence field(s): " + ", ".join(sorted(unknown)))
    return [
        {
            "evidence_domain": field,
            "requirement": description,
            "status": "Available for review" if evidence.get(field) is True else "Missing",
            "next_action": SOURCE_EVIDENCE_ACTIONS[field],
        }
        for field, description in SOURCE_EVIDENCE_REQUIREMENTS.items()
    ]


def _valid_https_url(value: object) -> bool:
    """Accept only absolute HTTPS URLs with a host and no embedded credentials."""
    text = str(value).strip() if value is not None else ""
    if not text or any(character.isspace() for character in text):
        return False
    try:
        parsed = urlsplit(text)
        # Accessing .port also rejects malformed or out-of-range port values.
        parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and bool(parsed.hostname)
        and parsed.username is None
        and parsed.password is None
    )


def source_attribution_readiness(evidence: Mapping[str, bool]) -> dict[str, object]:
    """Return whether the source evidence gate is met, without assigning ranks.

    Missing evidence always produces an empty ranking. Passing the gate means
    the input is ready for a reviewed attribution method; this function itself
    does not claim causation or calculate a confidence score.
    """
    unknown = set(evidence) - set(SOURCE_EVIDENCE_REQUIREMENTS)
    if unknown:
        raise ValueError("Unknown source-evidence field(s): " + ", ".join(sorted(unknown)))
    missing = [
        description
        for field, description in SOURCE_EVIDENCE_REQUIREMENTS.items()
        if evidence.get(field) is not True
    ]
    return {
        "status": "insufficient_evidence" if missing else "ready_for_method_review",
        "eligible_for_ranking": not missing,
        "missing_evidence": missing,
        "ranking": [],
        "confidence": None,
    }


def validate_attribution_observations(
    observations: pd.DataFrame,
    station_inventory: list[str] | tuple[str, ...],
    *,
    provenance_verified: bool,
    as_of: date | str,
) -> pd.DataFrame:
    """Validate ambient concentration rows while retaining source-form values.

    This adds attribution-oriented provenance fields around the existing air
    quality validator. The source station label is not promoted to an official
    station identifier when the source did not publish one.
    """
    if provenance_verified is not True:
        raise AirQualityDataError("Unverified observations are not eligible for assessment.")
    if not isinstance(observations, pd.DataFrame):
        raise AirQualityDataError("Observations must be provided as a pandas DataFrame.")
    if "source_url" not in observations.columns:
        raise AirQualityDataError("A source_url is required for every ambient observation.")
    if not observations["source_url"].map(_valid_https_url).all():
        raise AirQualityDataError("Every ambient observation must have an HTTPS source_url.")

    frame = observations.copy()
    source_fields = {
        "source_observed_at": "observed_at",
        "source_station_label": "station",
        "source_pollutant": "pollutant",
        "source_value": "value",
        "source_unit": "unit",
    }
    for target, source in source_fields.items():
        if source not in frame.columns:
            raise AirQualityDataError(f"Missing required source field: {source}.")
        frame[target] = frame[source]
    identifier_column = next(
        (name for name in ("source_station_identifier", "station_identifier", "station_id") if name in frame),
        None,
    )
    if identifier_column is None:
        frame["source_station_identifier"] = pd.NA
    elif identifier_column != "source_station_identifier":
        frame["source_station_identifier"] = frame[identifier_column]

    validated = validate_observations(frame, station_inventory, verified=True)
    reference_date = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
    temporal_status: list[str] = []
    for value in validated["observed_at"]:
        observed_date = pd.Timestamp(value).date()
        if observed_date > reference_date:
            raise AirQualityDataError("Ambient observations cannot be dated after the assessment date.")
        temporal_status.append("current" if observed_date == reference_date else "historical")
    validated["evidence_type"] = "measured"
    validated["temporal_status"] = temporal_status
    validated["source_provenance_verified"] = True
    return validated


def _finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _retrieval_date_present(value: object) -> bool:
    try:
        date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _verified_documented_evidence(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and value.get("evidence_status") == "verified"
        and bool(str(value.get("description") or "").strip())
        and _valid_https_url(value.get("source_url"))
        and _retrieval_date_present(value.get("retrieved_on"))
    )


def _dated_at_or_before(value: object, reference: date) -> bool:
    sample_date = _record_date(value)
    return sample_date is not None and sample_date <= reference


def _record_date(value: object) -> date | None:
    text = str(value or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    else:
        try:
            timestamp = pd.Timestamp(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if pd.isna(timestamp) or timestamp.tzinfo is None:
            return None
        return timestamp.tz_convert("UTC").date()


def _pollutant_key(value: object) -> str | None:
    key = re.sub(r"\s+", "", str(value or "")).casefold()
    aliases = {"pm25": "PM2.5"}
    canonical = aliases.get(key)
    if canonical is None:
        canonical = next(
            (pollutant for pollutant in SUPPORTED_POLLUTANTS if pollutant.casefold() == key),
            None,
        )
    return canonical


def _verified_coordinates(facility: Mapping[str, object]) -> bool:
    if facility.get("coordinates_status") != "verified":
        return False
    latitude = _finite_number(facility.get("facility_latitude"))
    longitude = _finite_number(facility.get("facility_longitude"))
    crs = str(
        facility.get("coordinate_reference_system")
        or facility.get("coordinates_crs")
        or ""
    ).strip()
    source = str(facility.get("coordinates_source_url") or "").strip()
    retrieved_on = facility.get("coordinates_retrieved_on")
    return (
        latitude is not None
        and longitude is not None
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
        and bool(crs)
        and _valid_https_url(source)
        and _retrieval_date_present(retrieved_on)
    )


def _verified_stack_measurements(
    facility: Mapping[str, object], as_of: date, ambient: pd.DataFrame
) -> bool:
    """Require measured stack records; permit limits and prose do not qualify."""
    records = facility.get("stack_emissions")
    if not isinstance(records, (list, tuple)) or ambient.empty:
        return False
    ambient_matches = {
        (_pollutant_key(row.pollutant), _record_date(row.observed_at))
        for row in ambient.itertuples(index=False)
    }
    for record in records:
        if not isinstance(record, Mapping) or record.get("evidence_type") != "measured":
            continue
        if record.get("record_type") != "measured_stack_emission":
            continue
        if record.get("evidence_status") != "verified":
            continue
        value = _finite_number(record.get("value"))
        pollutant = _pollutant_key(record.get("pollutant"))
        sampled_at = _record_date(record.get("sampled_at"))
        if (
            value is not None
            and value >= 0
            and pollutant is not None
            and (pollutant, sampled_at) in ambient_matches
            and str(record.get("unit") or "").strip()
            and sampled_at is not None
            and sampled_at <= as_of
            and str(record.get("reporting_authority") or "").strip()
            and _valid_https_url(record.get("source_url"))
            and _retrieval_date_present(record.get("retrieved_on"))
        ):
            return True
    return False


def _explicit_averaging_window(value: object) -> bool:
    text = str(value or "").strip().casefold()
    vague = ("not stated", "unknown", "unspecified", "daily report value")
    return bool(text) and not any(term in text for term in vague)


def _time_key(value: object) -> tuple[str, str] | None:
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return ("day", date.fromisoformat(text).isoformat())
        except ValueError:
            return None
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if pd.isna(timestamp) or timestamp.tzinfo is None:
        return None
    return ("instant", timestamp.tz_convert("UTC").isoformat())


def _suitable_observation_precision(row: object) -> bool:
    precision = str(getattr(row, "timestamp_precision", "")).casefold()
    if precision == "instant":
        return True
    period = re.sub(r"\s+", "", str(getattr(row, "averaging_period", "")).casefold())
    return precision == "day" and bool(
        re.fullmatch(r"(?:24[- ]?hours?|24h|daily|1[- ]?day)", period)
    )


def _time_aligned_meteorology(
    ambient: pd.DataFrame,
    meteorology: pd.DataFrame | None,
    *,
    verified_site: bool,
) -> bool:
    if not verified_site or ambient.empty or not isinstance(meteorology, pd.DataFrame) or meteorology.empty:
        return False
    required = {
        "observed_at", "station", "wind_speed", "wind_speed_unit", "wind_direction",
        "wind_direction_unit", "averaging_period", "source_url",
    }
    if not required.issubset(meteorology.columns):
        return False
    valid_ambient = ambient.loc[ambient["quality_flag"].eq("valid")].copy()
    if valid_ambient.empty or not all(
        _explicit_averaging_window(row.averaging_period) and _suitable_observation_precision(row)
        for row in valid_ambient.itertuples(index=False)
    ):
        return False
    if not meteorology["source_url"].map(_valid_https_url).all():
        return False
    if not meteorology["wind_speed_unit"].astype("string").str.casefold().eq("m/s").all():
        return False
    direction_units = meteorology["wind_direction_unit"].astype("string").str.casefold()
    if not direction_units.isin({"degree", "degrees", "deg"}).all():
        return False
    speeds = pd.to_numeric(meteorology["wind_speed"], errors="coerce")
    directions = pd.to_numeric(meteorology["wind_direction"], errors="coerce")
    if speeds.isna().any() or directions.isna().any() or (speeds < 0).any() or ((directions < 0) | (directions > 360)).any():
        return False
    if not meteorology["averaging_period"].map(_explicit_averaging_window).all():
        return False
    meteorology_times = meteorology["observed_at"].map(_time_key)
    # Exact source timestamps and matching station/window are required. Day-only
    # values can match only where both records state an explicit common window.
    for row in valid_ambient.itertuples(index=False):
        observation_time = _time_key(row.observed_at)
        if observation_time is None or not _suitable_observation_precision(row):
            return False
        matching = meteorology.loc[
            meteorology["station"].astype("string").str.casefold().eq(str(row.station).casefold())
            & meteorology_times.map(lambda value: value == observation_time)
            & meteorology["averaging_period"].astype("string").eq(str(row.averaging_period))
        ]
        if matching.empty:
            return False
    return True


def assess_industrial_sources(
    facilities: list[Mapping[str, object]],
    ambient_observations: pd.DataFrame | None,
    station_inventory: list[str] | tuple[str, ...],
    meteorology: pd.DataFrame | None,
    *,
    as_of: date | str,
    ambient_evidence_type: str = "measured",
    ambient_provenance_verified: bool = False,
    meteorology_provenance_verified: bool = False,
    meteorology_site_verified: bool = False,
    context_evidence: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """Assess whether facility-level source attribution is supportable.

    This is a deterministic evidence gate, not a predictive or causal model.
    It never ranks candidates. AQI, permits, fuel records, proximity, industry
    labels, and wind direction by themselves do not satisfy emissions evidence.
    """
    if ambient_evidence_type not in AMBIENT_EVIDENCE_TYPES:
        raise ValueError("ambient_evidence_type must be one of " + ", ".join(sorted(AMBIENT_EVIDENCE_TYPES)))
    reference_date = date.fromisoformat(as_of) if isinstance(as_of, str) else as_of
    context = context_evidence or {}
    unknown_context = set(context) - {"alternatives_and_background", "transport_method"}
    if unknown_context:
        raise ValueError("Unknown context-evidence field(s): " + ", ".join(sorted(unknown_context)))
    identities = [str(facility.get("facility_id", "")).strip() for facility in facilities]
    if any(not identity for identity in identities) or len(set(identities)) != len(identities):
        raise ValueError("Facilities must have unique, non-empty facility_id values.")

    validated_ambient = pd.DataFrame()
    validation_error = None
    excluded_reason = None
    resolved_ambient_type = (
        "missing"
        if ambient_observations is None or ambient_observations.empty or ambient_evidence_type == "missing"
        else ambient_evidence_type
    )
    if resolved_ambient_type == "missing":
        excluded_reason = "No ambient concentration observations were supplied."
    elif resolved_ambient_type in {"illustrative", "estimated"}:
        excluded_reason = f"{resolved_ambient_type.capitalize()} records are not observations and are excluded."
    elif resolved_ambient_type == "unverified" or ambient_provenance_verified is not True:
        excluded_reason = "Ambient records lack verified source provenance and are excluded."
    else:
        try:
            validated_ambient = validate_attribution_observations(
                ambient_observations,
                station_inventory,
                provenance_verified=True,
                as_of=as_of,
            )
        except (AirQualityDataError, TypeError, ValueError) as error:
            validation_error = str(error)
            excluded_reason = "Ambient observations failed validation."

    usable_ambient = validated_ambient.loc[
        validated_ambient.get("quality_flag", pd.Series(dtype="string")).eq("valid")
    ].copy() if not validated_ambient.empty else pd.DataFrame()
    observation_window = bool(
        not usable_ambient.empty
        and all(
            _explicit_averaging_window(row.averaging_period) and _suitable_observation_precision(row)
            for row in usable_ambient.itertuples(index=False)
        )
    )
    meteorology_ready = bool(
        meteorology_provenance_verified
        and _time_aligned_meteorology(
            usable_ambient,
            meteorology,
            verified_site=meteorology_site_verified,
        )
    )

    candidate_results = []
    for facility in facilities:
        facility_id = str(facility["facility_id"]).strip()
        facility_evidence = {
            "observation_window": observation_window,
            "facility_locations": _verified_coordinates(facility),
            "pollutant_emissions": _verified_stack_measurements(
                facility, reference_date, usable_ambient
            ),
            "source_signatures": _verified_documented_evidence(facility.get("source_signature_evidence")),
            "time_aligned_meteorology": meteorology_ready,
            "alternatives_and_background": _verified_documented_evidence(context.get("alternatives_and_background")),
            "transport_method": _verified_documented_evidence(context.get("transport_method")),
        }
        gate = source_attribution_readiness(facility_evidence)
        candidate_results.append(
            {
                "facility_id": facility_id,
                "facility_name": str(facility.get("official_name") or facility.get("facility_name_as_published") or facility_id),
                "status": gate["status"],
                "evidence": {
                    **facility_evidence,
                    "ambient_valid_observation_count": len(usable_ambient),
                    "ambient_evidence_type": resolved_ambient_type,
                    "ambient_temporal_statuses": sorted(set(validated_ambient.get("temporal_status", []))),
                    "inventory_coordinates_status": facility.get("coordinates_status", "unavailable"),
                    "inventory_measured_emissions_status": facility.get("measured_emissions_status", "unavailable"),
                    "inventory_emissions_limits_status": facility.get("emissions_limits_status", "unavailable"),
                    "historical_consent_record_status": facility.get(
                        "historical_consent_or_effluent_record_status", "unavailable"
                    ),
                    "current_consent_status_as_published": facility.get("current_consent_status", "unavailable"),
                    "current_consent_evidence_status": facility.get("current_consent_evidence_status", "unavailable"),
                    "consent_is_stack_emissions_evidence": False,
                },
                "missing_evidence": gate["missing_evidence"],
                "explanation": INSUFFICIENT_ATTRIBUTION_MESSAGE if gate["status"] == "insufficient_evidence" else "Evidence passed the minimum gate and needs independent scientific method review before attribution.",
            }
        )

    all_ready = bool(candidate_results) and all(item["status"] == "ready_for_method_review" for item in candidate_results)
    status = "ready_for_method_review" if all_ready else "insufficient_evidence"
    return {
        "status": status,
        "message": (
            "Evidence passed the minimum gate and needs independent scientific method review before attribution."
            if all_ready else INSUFFICIENT_ATTRIBUTION_MESSAGE
        ),
        "eligible_for_attribution": False,
        "ranking": [],
        "confidence": None,
        "ambient_evidence": {
            "evidence_type": resolved_ambient_type,
            "validated_record_count": len(validated_ambient),
            "quality_eligible_record_count": len(usable_ambient),
            "temporal_statuses": sorted(set(validated_ambient.get("temporal_status", []))),
            "excluded_reason": excluded_reason,
            "validation_error": validation_error,
            "source_fields_preserved": bool(not validated_ambient.empty),
        },
        "candidates": candidate_results,
    }

"""Validation helpers for the Edayar candidate-facility inventory."""

from __future__ import annotations

import math
from datetime import date


EVIDENCE_STATUSES = {"verified", "historical", "unverified", "unavailable"}
FACILITY_STATUS_FIELDS = (
    "candidate_basis_status",
    "industrial_area_status",
    "historical_consent_or_effluent_record_status",
    "identity_status",
    "address_status",
    "coordinates_status",
    "industry_type_status",
    "fuel_use_status",
    "emissions_limits_status",
    "measured_emissions_status",
    "air_emissions_data_status",
    "current_consent_evidence_status",
    "environmental_clearance_evidence_status",
    "ranking_evidence_status",
    "source_url_status",
)


class FacilityInventoryError(ValueError):
    """Raised when facility evidence is internally inconsistent."""


def normalize_identity(value: str) -> str:
    """Return a conservative case- and punctuation-insensitive name key."""
    return "".join(character for character in str(value).casefold() if character.isalnum())


def _iso_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise FacilityInventoryError(f"{field} must be an ISO date") from error


def consent_temporal_status(record: dict, as_of: date | str) -> str:
    """Classify the age of a documented consent record without implying current operation."""
    reference_date = _iso_date(as_of, "as_of") if isinstance(as_of, str) else as_of
    expiry = str(record.get("valid_until", "")).strip()
    if expiry:
        return "verified" if _iso_date(expiry, "valid_until") >= reference_date else "historical"

    event_date = str(record.get("decision_or_issue_date", "")).strip()
    if event_date:
        return "historical" if _iso_date(event_date, "decision_or_issue_date") < reference_date else "verified"
    return "unavailable"


def validate_facility_inventory(rows: list[dict]) -> None:
    """Check identity uniqueness and that unsupported fields remain explicitly unavailable."""
    identifiers: set[str] = set()
    names: dict[str, str] = {}

    for row in rows:
        facility_id = str(row.get("facility_id", "")).strip()
        if not facility_id or facility_id in identifiers:
            raise FacilityInventoryError(f"Missing or duplicate facility_id: {facility_id!r}")
        identifiers.add(facility_id)

        official_name = str(row.get("official_name", "")).strip()
        if not official_name:
            raise FacilityInventoryError(f"{facility_id}: official_name is required")
        if not str(row.get("source_url", "")).startswith("https://"):
            raise FacilityInventoryError(f"{facility_id}: source_url must be present")
        _iso_date(row.get("retrieved_on", ""), "retrieved_on")
        identities = [official_name]
        identities.extend(
            alias.strip()
            for alias in str(row.get("name_aliases", "")).split("|")
            if alias.strip()
        )
        for identity in identities:
            key = normalize_identity(identity)
            previous = names.get(key)
            if previous and previous != facility_id:
                raise FacilityInventoryError(
                    f"Duplicate facility identity {identity!r}: {previous} and {facility_id}"
                )
            names[key] = facility_id

        for field in FACILITY_STATUS_FIELDS:
            if row.get(field) not in EVIDENCE_STATUSES:
                raise FacilityInventoryError(
                    f"{facility_id}: {field} must be one of {sorted(EVIDENCE_STATUSES)}"
                )

        latitude = str(row.get("facility_latitude", "")).strip()
        longitude = str(row.get("facility_longitude", "")).strip()
        if bool(latitude) != bool(longitude):
            raise FacilityInventoryError(f"{facility_id}: coordinates must be both present or both missing")
        if not latitude:
            if row["coordinates_status"] != "unavailable":
                raise FacilityInventoryError(
                    f"{facility_id}: missing facility coordinates must be labeled unavailable"
                )
            if "not quantifiable" not in str(row.get("coordinate_uncertainty", "")).casefold():
                raise FacilityInventoryError(
                    f"{facility_id}: missing coordinates must state that uncertainty is not quantifiable"
                )
        else:
            try:
                lat, lon = float(latitude), float(longitude)
            except ValueError as error:
                raise FacilityInventoryError(f"{facility_id}: coordinates must be numeric") from error
            if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                raise FacilityInventoryError(f"{facility_id}: coordinates are outside valid ranges")
            if row["coordinates_status"] != "verified":
                raise FacilityInventoryError(
                    f"{facility_id}: populated coordinates require verified evidence"
                )

        if not str(row.get("measured_emissions_value", "")).strip() and row[
            "measured_emissions_status"
        ] != "unavailable":
            raise FacilityInventoryError(
                f"{facility_id}: missing measured emissions must be labeled unavailable"
            )
        if not str(row.get("emissions_limits_value", "")).strip() and row[
            "emissions_limits_status"
        ] != "unavailable":
            raise FacilityInventoryError(
                f"{facility_id}: missing emission limits must be labeled unavailable"
            )
        if row.get("ranking_status") != "Candidate only; not ranked":
            raise FacilityInventoryError(f"{facility_id}: unsupported source ranking is not allowed")


def validate_consent_records(rows: list[dict], facility_ids: set[str], as_of: date | str) -> None:
    """Check consent references and ensure their temporal evidence labels are accurate."""
    seen: set[str] = set()
    for row in rows:
        record_id = str(row.get("record_id", "")).strip()
        facility_id = str(row.get("facility_id", "")).strip()
        if not record_id or record_id in seen:
            raise FacilityInventoryError(f"Missing or duplicate consent record_id: {record_id!r}")
        seen.add(record_id)
        if facility_id not in facility_ids:
            raise FacilityInventoryError(f"{record_id}: unknown facility_id {facility_id!r}")
        if row.get("evidence_status") not in EVIDENCE_STATUSES:
            raise FacilityInventoryError(f"{record_id}: invalid evidence_status")
        if not str(row.get("source_url", "")).startswith("https://"):
            raise FacilityInventoryError(f"{record_id}: source_url must be present")
        _iso_date(row.get("retrieved_on", ""), "retrieved_on")
        if row.get("evidence_status") != consent_temporal_status(row, as_of):
            raise FacilityInventoryError(f"{record_id}: evidence_status does not match record dates")
        if row.get("decision") not in {"Approved", "Rejected"}:
            raise FacilityInventoryError(f"{record_id}: decision must be Approved or Rejected")
        if row.get("decision") == "Rejected" and str(row.get("valid_until", "")).strip():
            raise FacilityInventoryError(f"{record_id}: rejected application cannot have a consent expiry")

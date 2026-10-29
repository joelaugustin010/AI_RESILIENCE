"""Transparent source registry for datasets used by the disaster workflow.

Registry presence is not evidence that a dataset is suitable for a particular
scientific claim. Unknown metadata stays explicitly unknown; this module never
infers a licence, coordinate system, time zone, or validation status.
"""
from __future__ import annotations

from typing import Any

from src.hydrology_analytics import DATASETS


# These notes are deliberately conservative and tied to the current repository
# audit. They are not substitutes for checking the original publisher's terms.
_REVIEW_NOTES = {
    "rainfall_manual": {
        "publisher": "Kerala Surface Water Department (as described by NWDP)",
        "observation_type": "Recorded rainfall observations",
        "license_status": "Not independently verified; check source terms before redistribution",
        "retrieval_date": "Not recorded in repository metadata",
        "checksum_match": "Not verified against portal export",
        "time_zone": "Not documented in the local source metadata",
        "spatial_reference": "Station coordinates/CRS not supplied by this registry",
        "validation_status": "Descriptive-only; local timestamp coverage differs from filename period",
        "permitted_use": "Exploratory display and descriptive QA only; not flood prediction",
        "known_limitation": "Local timestamps span 2000–2014 although filename says 1991–2020; sampling is irregular.",
    },
    "rainfall_cwc": {
        "publisher": "CWC (agency label in local file; portal match not checksum-confirmed)",
        "observation_type": "Telemetry rainfall observations",
        "license_status": "Not independently verified; check source terms before redistribution",
        "retrieval_date": "Not recorded in repository metadata",
        "checksum_match": "Not verified against portal export",
        "time_zone": "Not documented in the local source metadata",
        "spatial_reference": "Station coordinates/CRS not supplied by this registry",
        "validation_status": "QA flags retained; 324 conflicting station-time groups reported",
        "permitted_use": "Exploratory display and descriptive QA only; do not silently deduplicate or accumulate",
        "known_limitation": "Conflicting station-time records exist; raw points must remain distinguishable.",
    },
    "river_manual": {
        "publisher": "Kerala Surface Water Department (as described by NWDP)",
        "observation_type": "Recorded river-level observations",
        "license_status": "Not independently verified; check source terms before redistribution",
        "retrieval_date": "Not recorded in repository metadata",
        "checksum_match": "Not verified against portal export",
        "time_zone": "Not documented in the local source metadata",
        "spatial_reference": "Gauge datum/reference and station spatial attribution unresolved",
        "validation_status": "Descriptive-only; no threshold comparison permitted",
        "permitted_use": "Exploratory display and gap QA only; not flood prediction",
        "known_limitation": "Gauge zero/vertical reference unresolved; some river/basin labels conflict with station context.",
    },
    "river_telemetry": {
        "publisher": "Kerala Surface Water Department (as described by NWDP)",
        "observation_type": "Telemetry river-level observations",
        "license_status": "Not independently verified; check source terms before redistribution",
        "retrieval_date": "Not recorded in repository metadata",
        "checksum_match": "Not verified against portal export",
        "time_zone": "Not documented in the local source metadata",
        "spatial_reference": "Gauge datum/reference and station spatial attribution unresolved",
        "validation_status": "Descriptive-only; no threshold comparison permitted",
        "permitted_use": "Exploratory display and gap QA only; not flood prediction",
        "known_limitation": "Gauge zero/vertical reference unresolved; long gaps and anomalous changes need provider review.",
    },
}


def build_source_registry() -> list[dict[str, Any]]:
    """Return one provenance/fitness record per hydrology dataset known to the app."""
    registry: list[dict[str, Any]] = []
    for dataset_id, spec in DATASETS.items():
        review = _REVIEW_NOTES.get(dataset_id, {})
        registry.append({
            "dataset_id": dataset_id,
            "name": spec.label,
            "local_file": spec.file_name,
            "publisher": review.get("publisher", "Unknown; verify with publisher"),
            "source_url": spec.source_url or None,
            "data_type": review.get("observation_type", spec.mode),
            "unit": spec.unit or "Unknown",
            "retrieval_date": review.get("retrieval_date", "Not recorded"),
            "license_status": review.get("license_status", "Not verified"),
            "checksum_match": review.get("checksum_match", "Not verified"),
            "time_zone": review.get("time_zone", "Not documented"),
            "spatial_reference": review.get("spatial_reference", "Not documented"),
            "validation_status": review.get("validation_status", "Not assessed"),
            "permitted_use": review.get("permitted_use", "Exploratory use only until reviewed"),
            "known_limitation": review.get("known_limitation", spec.warning),
            "source_warning": spec.warning,
        })
    return registry


def validate_source_record(record: dict[str, Any]) -> list[str]:
    """Report missing/unsafe provenance fields without pretending to validate data."""
    problems: list[str] = []
    required = (
        "dataset_id", "name", "local_file", "publisher", "source_url", "data_type",
        "unit", "retrieval_date", "license_status", "checksum_match", "time_zone",
        "spatial_reference", "validation_status", "permitted_use", "known_limitation",
    )
    for field in required:
        value = record.get(field)
        if value is None or not str(value).strip():
            problems.append(f"Missing required provenance field: {field}")
    for field in ("license_status", "checksum_match", "time_zone", "spatial_reference", "validation_status"):
        value = str(record.get(field, "")).lower()
        if value in {"verified", "validated", "confirmed", "approved"}:
            problems.append(
                f"{field} uses a blanket positive status; provide specific evidence and scope instead"
            )
    if record.get("source_url") and not str(record["source_url"]).startswith(("https://", "http://")):
        problems.append("source_url must be an HTTP(S) URL or unknown")
    return problems


def source_fitness_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Separate catalog completeness from scientific fitness for a use case."""
    problems = validate_source_record(record)
    status = str(record.get("validation_status", "")).lower()
    fit_for_claim = status.startswith("independently validated for")
    return {
        "metadata_complete": not problems,
        "metadata_problems": problems,
        "scientific_fitness": "Fit only for the explicitly validated use case" if fit_for_claim else "Not established",
        "prediction_permitted": False,
        "official_warning_permitted": False,
    }

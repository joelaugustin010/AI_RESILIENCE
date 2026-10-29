"""Multi-source evidence gate for flood scenarios.

This module is deliberately an evidence-fusion/readiness layer, not a flood
probability model. It checks source independence, location/time alignment,
units, and quality flags before allowing evidence to be described as
corroborated. It never turns missing data into zero or emits a risk score.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SOURCE_REGISTRY = {
    "ksdma_historical_raster": {
        "family": "official_hazard_mapping",
        "title": "KSDMA historical flood-return raster",
        "status": "not_eligible_pixel_semantics_and_reuse_unresolved",
        "unit": None,
        "url": "https://sdma.kerala.gov.in/hazard-maps/",
        "use": "Context only; do not sample or threshold pixels until exact value semantics and reuse terms are confirmed.",
    },
    "ksdma_ernakulam_pdf": {
        "family": "official_hazard_mapping",
        "title": "KSDMA Ernakulam district flood-hazard maps",
        "status": "district_context_only",
        "unit": None,
        "url": "https://sdma.kerala.gov.in/hazard-maps/",
        "use": "District-level contextual review only; not ward-level or facility-level exposure.",
    },
    "cwc_rainfall_observations": {
        "family": "rain_gauge_observations",
        "title": "CWC hourly rainfall observations in the project repository",
        "status": "raw_observations_conflicts_and_coverage_gaps",
        "unit": "mm",
        "url": "https://cwc.gov.in/",
        "use": "Only after station-time conflicts, time zone, observation interval, and missingness are handled.",
    },
    "cwc_river_observations": {
        "family": "river_gauge_observations",
        "title": "CWC river-level observations in the project repository",
        "status": "raw_observations_gauge_reference_unresolved",
        "unit": "m",
        "url": "https://cwc.gov.in/",
        "use": "Source-reported reading only until gauge datum, station identity, and warning thresholds are confirmed.",
    },
    "eidc_rainfall_ddf": {
        "family": "gridded_rainfall_frequency",
        "title": "Kerala gridded rainfall depth-duration-frequency estimates (1979–2020)",
        "status": "candidate_not_ingested_license_not_provided",
        "unit": "mm",
        "url": "https://catalogue.ceh.ac.uk/documents/4a08e6f1-e508-4bb6-b571-b3145dd1588e",
        "use": "Historical modelled rainfall-frequency context; not live forecast rainfall.",
    },
    "eidc_flood_frequency": {
        "family": "gridded_flood_frequency",
        "title": "Kerala gridded flood-frequency estimates",
        "status": "candidate_not_ingested_license_not_provided",
        "unit": "m³/s",
        "url": "https://catalogue.ceh.ac.uk/documents/cba9f9db-4706-4f1e-aaf4-fd7769e00db0",
        "use": "River-network peak-flow frequency context; not local inundation depth or flood probability.",
    },
    "imd_forecast": {
        "family": "meteorological_forecast",
        "title": "India Meteorological Department official forecasts and warnings",
        "status": "not_integrated",
        "unit": None,
        "url": "https://mausam.imd.gov.in/",
        "use": "Operational context only after source, issue time, valid time, spatial coverage, and product are captured.",
    },
    "terrain_drainage": {
        "family": "terrain_and_drainage",
        "title": "Terrain, drainage, and local infrastructure evidence",
        "status": "no_validated_kochi_layer_in_model",
        "unit": None,
        "url": "https://bhuvan.nrsc.gov.in/",
        "use": "Required for local waterlogging mechanisms; source, resolution, and reuse must be checked before ingestion.",
    },
}


def audit_multisource_evidence(
    evidence: list[dict[str, Any]] | None,
    *,
    now: datetime | None = None,
    max_age_hours: float = 24.0,
    minimum_independent_families: int = 3,
) -> dict[str, Any]:
    """Audit evidence records without generating a probability or severity score.

    Each candidate record needs: source_id, value, unit, timestamp_utc,
    location_match='verified', quality_status='verified', and source_id must
    refer to a registered source. A source only counts if its registry status
    is explicitly 'verified_for_observation_use'. The current registry
    intentionally has no such entries because no live source is yet approved
    for automated numerical fusion.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware.")
    if max_age_hours <= 0:
        raise ValueError("max_age_hours must be positive.")
    if minimum_independent_families < 2:
        raise ValueError("At least two independent source families are required.")

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen_source_ids: set[str] = set()
    seen_families: set[str] = set()

    for index, item in enumerate(evidence or []):
        source_id = str(item.get("source_id", "")).strip()
        reason = ""
        source = SOURCE_REGISTRY.get(source_id)
        if source is None:
            reason = "Source is not in the reviewed source registry."
        elif source_id in seen_source_ids:
            reason = "Duplicate source record; a repeated row does not add independent evidence."
        elif source.get("status") != "verified_for_observation_use":
            reason = "Source is not approved for automated numerical fusion."
        elif item.get("quality_status") != "verified":
            reason = "Observation quality has not been verified."
        elif item.get("location_match") != "verified":
            reason = "Location/station match has not been verified."
        else:
            try:
                value = float(item.get("value"))
            except (TypeError, ValueError):
                reason = "Value must be numeric."
            else:
                if not (value == value and abs(value) != float("inf")):
                    reason = "Value must be finite."
                elif item.get("unit") != source.get("unit"):
                    reason = "Observation unit does not match the reviewed source unit."
                else:
                    try:
                        timestamp = datetime.fromisoformat(str(item.get("timestamp_utc", "")).replace("Z", "+00:00"))
                    except (TypeError, ValueError):
                        timestamp = None
                    if timestamp is None or timestamp.tzinfo is None:
                        reason = "Timestamp must be ISO-8601 with an explicit timezone."
                    else:
                        age_hours = (now - timestamp.astimezone(timezone.utc)).total_seconds() / 3600
                        if age_hours < 0:
                            reason = "Future-dated observation is not eligible."
                        elif age_hours > max_age_hours:
                            reason = f"Observation is older than the {max_age_hours:g}-hour alignment window."
                        elif source["family"] in seen_families:
                            reason = "A second record from the same source family is not independent corroboration."
                        else:
                            accepted.append({
                                "source_id": source_id,
                                "source_family": source["family"],
                                "value": value,
                                "unit": item["unit"],
                                "timestamp_utc": timestamp.astimezone(timezone.utc).isoformat(),
                            })
                            seen_source_ids.add(source_id)
                            seen_families.add(source["family"])
        if reason:
            rejected.append({"record": str(index + 1), "source_id": source_id or "(missing)", "reason": reason})

    blockers = []
    if len(seen_families) < minimum_independent_families:
        blockers.append(
            f"Only {len(seen_families)} independent verified source families are available; "
            f"{minimum_independent_families} are required."
        )
    if not any(family in seen_families for family in ("rain_gauge_observations", "meteorological_forecast")):
        blockers.append("No verified rainfall observation or time-aligned meteorological forecast is available.")
    if not any(family in seen_families for family in ("river_gauge_observations", "official_hazard_mapping", "gridded_flood_frequency")):
        blockers.append("No independent river-gauge or hazard-context evidence is available.")

    return {
        "status": "INSUFFICIENT_EVIDENCE" if blockers else "MULTI_SOURCE_REVIEW_ONLY",
        "numeric_prediction_allowed": False,
        "risk_score": None,
        "accepted_count": len(accepted),
        "independent_source_families": sorted(seen_families),
        "accepted_evidence": accepted,
        "rejected_evidence": rejected,
        "blockers": blockers,
        "source_registry": SOURCE_REGISTRY,
        "interpretation": (
            "This gate checks source diversity and data validity only. Even when multiple sources pass, "
            "it does not calculate flood probability, depth, severity, or an operational warning."
        ),
    }

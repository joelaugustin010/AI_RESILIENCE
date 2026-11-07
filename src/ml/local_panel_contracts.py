"""Strict observed-outcome panel contracts for local hazard ML datasets.

Unknown or unreported intervals are never converted into non-events. Synthetic
and simulated rows are retained in audit counts but excluded from observed
training readiness.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Mapping, Sequence

VALID_HAZARDS = {
    "Flood", "Landslide", "Industrial incident", "Infrastructure failure",
    "Heatwave", "Drought", "Cyclone", "Earthquake",
}
REQUIRED_FIELDS = {
    "hazard", "unit_id", "observation_start", "observation_end",
    "event_label", "observation_status", "label_source_id", "record_origin",
    "latitude", "longitude",
}


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def audit_observed_hazard_panel(
    records: Sequence[Mapping[str, Any]],
    *,
    hazard: str,
    minimum_events: int = 50,
    minimum_non_events: int = 50,
) -> dict[str, Any]:
    """Audit panel rows; only source-verified observed event/non-event windows count."""
    if hazard not in VALID_HAZARDS:
        raise ValueError(f"Unsupported hazard panel: {hazard!r}")
    if minimum_events < 1 or minimum_non_events < 1:
        raise ValueError("Minimum event and non-event counts must be positive.")

    issues: list[str] = []
    counts: Counter[str] = Counter()
    observed_keys: set[tuple[str, str, str]] = set()
    event_rows = 0
    non_event_rows = 0

    for index, row in enumerate(records):
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            issues.append(f"row {index}: missing fields {', '.join(missing)}")
            continue
        if row.get("hazard") != hazard:
            issues.append(f"row {index}: hazard does not match requested panel {hazard!r}")
            continue
        origin = str(row.get("record_origin", "")).strip().casefold()
        if origin != "observed":
            counts[f"excluded_{origin or 'unknown'}"] += 1
            continue

        start = _parse_timestamp(row.get("observation_start"))
        end = _parse_timestamp(row.get("observation_end"))
        if start is None or end is None or start > end:
            issues.append(f"row {index}: invalid observation interval")
            continue
        unit_id = str(row.get("unit_id") or "").strip()
        source_id = str(row.get("label_source_id") or "").strip()
        if not unit_id or not source_id:
            issues.append(f"row {index}: observed labels require unit_id and label_source_id")
            continue
        try:
            latitude = float(row.get("latitude"))
            longitude = float(row.get("longitude"))
        except (TypeError, ValueError):
            issues.append(f"row {index}: observed panel requires numeric coordinates")
            continue
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            issues.append(f"row {index}: coordinates are outside valid geographic bounds")
            continue

        label = row.get("event_label")
        status = str(row.get("observation_status") or "").strip().casefold()
        if label not in (0, 1, False, True):
            issues.append(f"row {index}: event_label must be binary 0/1 or null")
            continue
        label = int(label)
        if label == 1 and status != "verified_event":
            issues.append(f"row {index}: positive labels require observation_status=verified_event")
            continue
        if label == 0 and status != "verified_non_event":
            issues.append(
                f"row {index}: negative labels require a surveyed/monitored verified_non_event interval"
            )
            continue

        key = (unit_id, start.isoformat(), end.isoformat())
        if key in observed_keys:
            issues.append(f"row {index}: duplicate unit/time observation interval")
            continue
        observed_keys.add(key)
        if label == 1:
            event_rows += 1
            counts["verified_events"] += 1
        else:
            non_event_rows += 1
            counts["verified_non_events"] += 1

    ready = (
        not issues
        and event_rows >= minimum_events
        and non_event_rows >= minimum_non_events
    )
    if event_rows < minimum_events:
        issues.append(f"only {event_rows} verified event rows; minimum configured is {minimum_events}")
    if non_event_rows < minimum_non_events:
        issues.append(
            f"only {non_event_rows} verified non-event rows; minimum configured is {minimum_non_events}"
        )
    return {
        "hazard": hazard,
        "rows_received": len(records),
        "verified_event_rows": event_rows,
        "verified_non_event_rows": non_event_rows,
        "excluded_rows": sum(value for key, value in counts.items() if key.startswith("excluded_")),
        "counts": dict(counts),
        "schema_and_label_audit_passed": not any(
            not issue.startswith("only ") for issue in issues
        ),
        "training_ready": ready,
        "issues": issues,
        "interpretation": (
            "Only observed, source-verified event and explicitly monitored non-event intervals "
            "count toward readiness. Unreported intervals and synthetic/simulated rows are not negatives."
        ),
    }


__all__ = ["REQUIRED_FIELDS", "VALID_HAZARDS", "audit_observed_hazard_panel"]

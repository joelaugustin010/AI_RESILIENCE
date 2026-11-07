"""Audit flood and landslide observation panels without treating unknown as negative."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FLOOD_REQUIRED = (
    "event_id", "site_id", "observation_time_utc",
    "rain_gauge_id", "rain_observed_at_utc", "rain_mm_24h",
    "river_gauge_id", "river_observed_at_utc", "river_level_m", "river_datum",
    "tide_station_id", "tide_observed_at_utc", "tide_level_m", "tide_datum",
    "flood_observed", "observation_coverage_fraction", "inspection_method",
    "inspected_by", "sar_scene_id", "sar_acquired_at_utc", "sar_processing_version",
    "sar_quality", "sar_coverage_fraction", "footprint_uri",
    "source_record_id", "source_publisher", "license", "adjudication_status",
)
LANDSLIDE_REQUIRED = (
    "site_id", "slope_unit_id", "monitoring_start_utc", "monitoring_end_utc",
    "monitoring_coverage_fraction", "inspection_method", "inspected_by",
    "event_observed", "source_record_id", "source_publisher", "license",
    "adjudication_status",
)
REVIEWED = {"reviewed", "confirmed", "adjudicated"}
ACCEPTED_SAR_QUALITY = {"good", "accepted", "reviewed", "high"}


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include an explicit UTC offset")
    return parsed.astimezone(timezone.utc)


def _number(row: dict[str, Any], field: str) -> float:
    value = float(row[field])
    if not math.isfinite(value):
        raise ValueError(f"{field} must be finite")
    return value


def audit(rows: list[dict[str, Any]], kind: str, max_offset_hours: float = 6.0) -> dict[str, Any]:
    if kind not in {"flood", "landslide"}:
        raise ValueError("kind must be flood or landslide")
    if not rows:
        raise ValueError("Observation panel is empty.")
    if not math.isfinite(max_offset_hours) or not 0 <= max_offset_hours <= 24:
        raise ValueError("max_offset_hours must be finite and between 0 and 24")

    required = FLOOD_REQUIRED if kind == "flood" else LANDSLIDE_REQUIRED
    missing = sorted(set(required) - set(rows[0]))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))

    problems: list[dict[str, Any]] = []
    unknown = 0
    duplicate: set[tuple[str, ...]] = set()
    for index, row in enumerate(rows, start=2):
        identity_fields = ("event_id", "site_id") if kind == "flood" else ("site_id", "slope_unit_id")
        if any(not str(row.get(field, "")).strip() for field in identity_fields):
            problems.append({"row": index, "issue": "MISSING_PANEL_IDENTITY"})
        if any(not str(row.get(field, "")).strip() for field in ("source_record_id", "source_publisher", "license")):
            problems.append({"row": index, "issue": "MISSING_SOURCE_PROVENANCE"})

        try:
            if kind == "flood":
                for field in ("rain_gauge_id", "river_gauge_id", "tide_station_id", "sar_scene_id"):
                    if not str(row.get(field, "")).strip():
                        problems.append({"row": index, "issue": "MISSING_SENSOR_IDENTITY", "field": field})
                observed_at = _dt(str(row["observation_time_utc"]))
                key = (str(row["event_id"]), str(row["site_id"]), observed_at.isoformat())
                if key in duplicate:
                    problems.append({"row": index, "issue": "DUPLICATE_PANEL_KEY"})
                duplicate.add(key)

                for field in ("rain_observed_at_utc", "river_observed_at_utc",
                              "tide_observed_at_utc", "sar_acquired_at_utc"):
                    offset = abs((_dt(str(row[field])) - observed_at).total_seconds()) / 3600
                    if offset > max_offset_hours:
                        problems.append({"row": index, "issue": "TIME_ALIGNMENT_EXCEEDED",
                                         "field": field, "offset_hours": round(offset, 3)})

                rain = _number(row, "rain_mm_24h")
                river = _number(row, "river_level_m")
                tide = _number(row, "tide_level_m")
                observation_coverage = _number(row, "observation_coverage_fraction")
                sar_coverage = _number(row, "sar_coverage_fraction")
                if rain < 0:
                    problems.append({"row": index, "issue": "NEGATIVE_RAINFALL"})
                if not 0 <= observation_coverage <= 1 or not 0 <= sar_coverage <= 1:
                    problems.append({"row": index, "issue": "INVALID_OBSERVATION_COVERAGE"})
                if not str(row["river_datum"]).strip() or not str(row["tide_datum"]).strip():
                    problems.append({"row": index, "issue": "MISSING_VERTICAL_DATUM"})
                del river, tide  # Parsed and finite-checked; values retain their source units/datums.

                label = str(row.get("flood_observed", ""))
                reviewed = str(row.get("adjudication_status", "")).casefold() in REVIEWED
                if label not in {"0", "1"} or not reviewed:
                    problems.append({"row": index, "issue": "FLOOD_LABEL_NOT_ADJUDICATED"})
                if not str(row.get("footprint_uri", "")).strip() and label == "1":
                    problems.append({"row": index, "issue": "EVENT_WITHOUT_FOOTPRINT_REFERENCE"})
                if label == "0":
                    monitored = (
                        observation_coverage >= 0.9
                        and sar_coverage >= 0.9
                        and str(row.get("inspection_method", "")).strip()
                        and str(row.get("inspected_by", "")).strip()
                        and str(row.get("sar_quality", "")).casefold() in ACCEPTED_SAR_QUALITY
                        and reviewed
                    )
                    if not monitored:
                        problems.append({"row": index, "issue": "UNSUPPORTED_FLOOD_NON_EVENT"})
                if label == "1" and not str(row.get("sar_scene_id", "")).strip():
                    problems.append({"row": index, "issue": "EVENT_WITHOUT_SAR_SCENE"})
                if not str(row.get("sar_processing_version", "")).strip():
                    problems.append({"row": index, "issue": "MISSING_SAR_PROCESSING_VERSION"})
            else:
                key = (str(row["site_id"]), str(row["slope_unit_id"]),
                       str(_dt(str(row["monitoring_start_utc"]))),
                       str(_dt(str(row["monitoring_end_utc"]))))
                if key in duplicate:
                    problems.append({"row": index, "issue": "DUPLICATE_PANEL_KEY"})
                duplicate.add(key)
                start = _dt(str(row["monitoring_start_utc"]))
                end = _dt(str(row["monitoring_end_utc"]))
                if end <= start:
                    problems.append({"row": index, "issue": "INVALID_MONITORING_INTERVAL"})
                coverage = _number(row, "monitoring_coverage_fraction")
                if not 0 <= coverage <= 1:
                    problems.append({"row": index, "issue": "INVALID_MONITORING_COVERAGE"})
                label = str(row.get("event_observed", ""))
                reviewed = str(row.get("adjudication_status", "")).casefold() in REVIEWED
                if label not in {"0", "1"}:
                    unknown += 1
                elif not reviewed:
                    problems.append({"row": index, "issue": "LANDSLIDE_LABEL_NOT_ADJUDICATED"})
                if label == "0" and (
                    coverage < 0.9 or not str(row.get("inspection_method", "")).strip()
                    or not str(row.get("inspected_by", "")).strip() or not reviewed
                ):
                    problems.append({"row": index, "issue": "UNSUPPORTED_NON_EVENT"})
        except (ValueError, TypeError, KeyError) as exc:
            problems.append({"row": index, "issue": "INVALID_OR_MISSING_VALUE", "detail": str(exc)})

    blocking = sum(problem["issue"] not in {"NON_BLOCKING_NOTE"} for problem in problems)
    return {
        "panel_kind": kind,
        "rows": len(rows),
        "problems": problems,
        "problem_count": len(problems),
        "unknown_or_unlabelled_rows": unknown,
        "training_ready": False,
        "status": "BLOCKED_DATA_QUALITY" if blocking else "AUDIT_ONLY_REQUIRES_HUMAN_ADJUDICATION",
        "interpretation": (
            "Schema, provenance, coverage and timing audit only. Does not establish source truth, "
            "licence sufficiency, spatial accuracy, independent event adjudication or model suitability."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=["flood", "landslide"], required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="reports/observation_panel_audit.json")
    parser.add_argument("--max-offset-hours", type=float, default=6)
    args = parser.parse_args()
    with Path(args.input).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    report = audit(rows, args.kind, args.max_offset_hours)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "rows": report["rows"],
                      "problems": report["problem_count"], "training_ready": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Audit acquired public hydrology CSVs without altering source files.

The audit is descriptive only. It flags issues for review and never creates flood
labels, repairs station metadata, imputes zero rainfall, or trains a model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "external" / "raw"
DEFAULT_OUTPUT = ROOT / "data" / "external" / "audit_report.json"

DATASETS = {
    "kerala_sw_rainfall_telemetry_2021_2025": {
        "filename": "rainfall_tel_hr_kerala_sw_kl_2021_2025.csv",
        "value_column": "Telemetry Hourly Rainfall (mm)",
        "kind": "rainfall",
    },
    "kerala_sw_river_level_telemetry_2021_2025": {
        "filename": "rwl_tel_hr_kerala_sw_999_2021_2025.csv",
        "value_column": "River Water Level Telemetry Hourly (meter)",
        "kind": "river_level",
    },
    "kerala_sw_river_level_manual_2021_2025": {
        "filename": "rwl_manual_hr_kerala_sw_031_2021_2025.csv",
        "value_column": "River Water Level Manual Hourly (meter)",
        "kind": "river_level_manual",
    },
}
TIME_COLUMN = "Data Acquisition Time"
STATION_COLUMN = "Station"
DISTRICT_COLUMN = "District"
LAT_COLUMN = "Latitude"
LON_COLUMN = "Longitude"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _safe_int(value: Any) -> int:
    return int(value) if pd.notna(value) else 0


def audit_one(path: Path, source_id: str, config: dict[str, str]) -> dict[str, Any]:
    frame = pd.read_csv(path, low_memory=False)
    required = [STATION_COLUMN, TIME_COLUMN, config["value_column"]]
    missing_columns = [column for column in required if column not in frame.columns]
    if missing_columns:
        return {
            "source_id": source_id,
            "path": str(path),
            "status": "BLOCKED_SCHEMA",
            "missing_columns": missing_columns,
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }

    times = pd.to_datetime(
        frame[TIME_COLUMN].astype("string"),
        format="%d-%m-%Y %H:%M",
        errors="coerce",
    )
    values = pd.to_numeric(frame[config["value_column"]], errors="coerce")
    stations = frame[STATION_COLUMN].astype("string")
    districts = frame[DISTRICT_COLUMN].astype("string") if DISTRICT_COLUMN in frame else pd.Series(pd.NA, index=frame.index, dtype="string")

    duplicate_table = pd.DataFrame({
        "station": stations,
        "timestamp_source_string": frame[TIME_COLUMN].astype("string"),
        "value": values,
    })
    grouped = duplicate_table.groupby(
        ["station", "timestamp_source_string"], dropna=False
    )["value"].agg(["size", "nunique"])
    duplicate_groups = grouped[grouped["size"] > 1]
    conflicting_groups = duplicate_groups[duplicate_groups["nunique"] > 1]

    lat = pd.to_numeric(frame[LAT_COLUMN], errors="coerce") if LAT_COLUMN in frame else pd.Series(float("nan"), index=frame.index)
    lon = pd.to_numeric(frame[LON_COLUMN], errors="coerce") if LON_COLUMN in frame else pd.Series(float("nan"), index=frame.index)
    coord_outlier_mask = lat.notna() & lon.notna() & (
        (lat < 8.0) | (lat > 13.0) | (lon < 74.0) | (lon > 78.0)
    )
    coordinate_outliers = []
    if coord_outlier_mask.any():
        coords = frame.loc[coord_outlier_mask, [STATION_COLUMN, DISTRICT_COLUMN, LAT_COLUMN, LON_COLUMN]].drop_duplicates()
        coordinate_outliers = [
            {
                "station": str(row[STATION_COLUMN]),
                "district": str(row[DISTRICT_COLUMN]) if DISTRICT_COLUMN in row else None,
                "latitude": float(row[LAT_COLUMN]),
                "longitude": float(row[LON_COLUMN]),
            }
            for _, row in coords.head(30).iterrows()
        ]

    station_summaries = []
    temp = pd.DataFrame({
        "station": stations,
        "district": districts,
        "time": times,
        "value": values,
        "latitude": lat,
        "longitude": lon,
    })
    for (district, station), part in temp.groupby(["district", "station"], dropna=False, sort=True):
        valid_times = part["time"].dropna().sort_values()
        gaps = valid_times.diff().dt.total_seconds().div(3600).dropna()
        station_summaries.append({
            "district": None if pd.isna(district) else str(district),
            "station": None if pd.isna(station) else str(station),
            "rows": int(len(part)),
            "first_timestamp": valid_times.min().isoformat(sep=" ") if not valid_times.empty else None,
            "last_timestamp": valid_times.max().isoformat(sep=" ") if not valid_times.empty else None,
            "median_gap_hours": float(gaps.median()) if not gaps.empty else None,
            "p95_gap_hours": float(gaps.quantile(0.95)) if not gaps.empty else None,
            "max_gap_hours": float(gaps.max()) if not gaps.empty else None,
            "min_value": float(part["value"].min()) if part["value"].notna().any() else None,
            "max_value": float(part["value"].max()) if part["value"].notna().any() else None,
            "latitude": float(part["latitude"].dropna().iloc[0]) if part["latitude"].notna().any() else None,
            "longitude": float(part["longitude"].dropna().iloc[0]) if part["longitude"].notna().any() else None,
        })

    valid_times = times.dropna()
    valid_values = values.dropna()
    missing_values = {str(k): _safe_int(v) for k, v in frame.isna().sum().items() if v}
    issues: list[str] = []
    if times.isna().any():
        issues.append(f"{int(times.isna().sum())} timestamp(s) did not parse with the documented day-first format.")
    if len(duplicate_groups):
        issues.append(f"{len(duplicate_groups)} duplicate station/timestamp groups; inspect before any aggregation.")
    if len(conflicting_groups):
        issues.append(f"{len(conflicting_groups)} duplicate station/timestamp groups contain conflicting values.")
    if coord_outlier_mask.any():
        issues.append(f"{int(coord_outlier_mask.sum())} row(s) have coordinates outside the broad Kerala screening box (8-13 N, 74-78 E).")
    if config["kind"] == "rainfall" and len(valid_values) and not (valid_values == 0).any():
        issues.append("No zero-rainfall observations are present; do not assume absent rows mean dry hours.")
    if config["kind"].startswith("river_level") and {"RL_of_zeroGauge", "MeanSeaLevel"}.issubset(frame.columns):
        if frame["RL_of_zeroGauge"].nunique(dropna=False) == 1 and frame["MeanSeaLevel"].nunique(dropna=False) == 1:
            issues.append("Gauge reference fields are constant across this file; verify their meaning and station datum with the provider.")
    if config["kind"] == "river_level_manual" and len(valid_values) and valid_values.max() > 100:
        issues.append("At least one river-level value exceeds 100 m; investigate scale, datum and station metadata before interpretation.")

    district_summary = {}
    if DISTRICT_COLUMN in frame:
        district_summary = {
            str(k): int(v)
            for k, v in frame[DISTRICT_COLUMN].value_counts(dropna=False).items()
        }
    ernakulam_mask = districts.astype("string").str.strip().str.upper().eq("ERNAKULAM")
    ernakulam = frame.loc[ernakulam_mask]
    ernakulam_stations = sorted(ernakulam[STATION_COLUMN].dropna().astype(str).unique().tolist()) if not ernakulam.empty else []

    return {
        "source_id": source_id,
        "filename": path.name,
        "path": str(path),
        "status": "AUDITED_WITH_LIMITATIONS",
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "rows": int(len(frame)),
        "columns": list(frame.columns),
        "station_count": int(stations.nunique(dropna=True)),
        "district_count": int(districts.nunique(dropna=True)),
        "district_row_counts": district_summary,
        "timestamp_column": TIME_COLUMN,
        "timestamp_parse_format": "%d-%m-%Y %H:%M",
        "source_timezone": "Not established; parsed values remain timezone-naive",
        "first_timestamp": valid_times.min().isoformat(sep=" ") if not valid_times.empty else None,
        "last_timestamp": valid_times.max().isoformat(sep=" ") if not valid_times.empty else None,
        "invalid_timestamps": int(times.isna().sum()),
        "missing_values_by_column": missing_values,
        "value_column": config["value_column"],
        "valid_numeric_values": int(len(valid_values)),
        "nonnumeric_nonmissing_values": int((frame[config["value_column"]].notna() & values.isna()).sum()),
        "min_value": float(valid_values.min()) if not valid_values.empty else None,
        "max_value": float(valid_values.max()) if not valid_values.empty else None,
        "zero_value_rows": int((values == 0).sum()),
        "negative_value_rows": int((values < 0).sum()),
        "duplicate_station_timestamp_groups": int(len(duplicate_groups)),
        "conflicting_duplicate_groups": int(len(conflicting_groups)),
        "coordinate_screen": {
            "screening_box": "8.0 <= latitude <= 13.0 and 74.0 <= longitude <= 78.0",
            "outlier_rows": int(coord_outlier_mask.sum()),
            "unique_outlier_station_coordinates": coordinate_outliers,
            "warning": "Broad screening only, not a verified boundary/CRS test."
        },
        "ernakulam_rows": int(ernakulam_mask.sum()),
        "ernakulam_station_names": ernakulam_stations,
        "station_summaries": station_summaries,
        "issues": issues,
        "interpretation": "Descriptive quality audit only; no flood labels are created and no model is trained."
    }


def build_report(input_dir: Path) -> dict[str, Any]:
    results = []
    missing_files = []
    for source_id, config in DATASETS.items():
        path = input_dir / config["filename"]
        if not path.is_file():
            missing_files.append({"source_id": source_id, "expected_path": str(path)})
            continue
        results.append(audit_one(path, source_id, config))
    return {
        "report_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_directory": str(input_dir),
        "missing_expected_files": missing_files,
        "datasets": results,
        "scientific_conclusion": (
            "The downloaded files are observational inputs, not verified flood outcomes. "
            "Do not train or report flood-prediction metrics until event labels, feature timing, "
            "station metadata and evaluation design are independently verified."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = build_report(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote audit report: {args.output}")
    print(f"Datasets audited: {len(report['datasets'])}; expected files missing: {len(report['missing_expected_files'])}")
    for dataset in report["datasets"]:
        print(f"- {dataset['filename']}: {dataset['rows']:,} rows, {dataset['station_count']} stations")
        for issue in dataset["issues"]:
            print(f"  WARNING: {issue}")
    return 1 if report["missing_expected_files"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

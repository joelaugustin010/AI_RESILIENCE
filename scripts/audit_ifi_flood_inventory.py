"""Descriptive audit of the IFI-Impacts public historical flood tables.

The audit preserves source files and reports their structure, coverage, missingness,
and event-level mentions of Kerala/Ernakulam. It does not create ward/hour labels,
infer flooded locations from district names, or train a prediction model.
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
DEFAULT_OUTPUT = ROOT / "data" / "external" / "ifi_audit_report.json"
FILES = {
    "ifi_impacts_inventory_v3": "India_Flood_Inventory_v3.csv",
    "ifi_impacts_district_flood_impact": "District_FloodImpact.csv",
    "ifi_impacts_district_flooded_area": "District_FloodedArea.csv",
    "ifi_impacts_dfsi": "DFSI.csv",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_csv(path: Path, source_id: str) -> dict[str, Any]:
    frame = pd.read_csv(path, low_memory=False)
    missing = {str(column): int(count) for column, count in frame.isna().sum().items() if count}
    report: dict[str, Any] = {
        "source_id": source_id,
        "filename": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "rows": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "missing_values_by_column": missing,
        "exact_duplicate_rows": int(frame.duplicated().sum()),
        "status": "DESCRIPTIVE_AUDIT_ONLY",
    }
    if path.name == "India_Flood_Inventory_v3.csv":
        for column in ("Start Date", "End Date"):
            if column in frame.columns:
                parsed = pd.to_datetime(frame[column], dayfirst=True, errors="coerce")
                report[f"{column.lower().replace(' ', '_')}_invalid_count"] = int(parsed.isna().sum())
                report[f"{column.lower().replace(' ', '_')}_first"] = parsed.min().isoformat() if parsed.notna().any() else None
                report[f"{column.lower().replace(' ', '_')}_last"] = parsed.max().isoformat() if parsed.notna().any() else None
        if "UEI" in frame.columns:
            ids = frame["UEI"].astype("string").str.strip()
            report["event_id_unique_count"] = int(ids.nunique(dropna=True))
            report["event_id_duplicate_rows"] = int(ids.duplicated(keep=False).sum())
        state = frame["State"].astype("string") if "State" in frame.columns else pd.Series("", index=frame.index, dtype="string")
        districts = frame["Districts"].astype("string") if "Districts" in frame.columns else pd.Series("", index=frame.index, dtype="string")
        kerala = state.str.contains(r"\bKerala\b", case=False, na=False)
        ernakulam = districts.str.contains(r"\bErnakulam\b", case=False, na=False)
        report["rows_with_state_field_mentioning_kerala"] = int(kerala.sum())
        report["rows_with_district_field_mentioning_ernakulam"] = int(ernakulam.sum())
        report["rows_mentioning_both_kerala_and_ernakulam"] = int((kerala & ernakulam).sum())
        if "UEI" in frame.columns:
            report["ernakulam_event_ids"] = sorted(ids[ernakulam].dropna().unique().astype(str).tolist())
        if {"Latitude", "Longitude"}.issubset(frame.columns):
            lat = pd.to_numeric(frame["Latitude"], errors="coerce")
            lon = pd.to_numeric(frame["Longitude"], errors="coerce")
            report["coordinate_pairs_numeric"] = int((lat.notna() & lon.notna()).sum())
            report["coordinate_pairs_missing_or_invalid"] = int((lat.isna() | lon.isna()).sum())
            report["coordinate_screen_outside_broad_India_box"] = int(
                (lat.notna() & lon.notna() & (~lat.between(6, 38) | ~lon.between(67, 98))).sum()
            )
        report["interpretation_warning"] = (
            "A row mentioning Ernakulam is event-level context only. It does not prove that every location in "
            "the district flooded, and it is not an hourly station outcome. Missing coordinates remain missing."
        )
    return report


def build_report(input_dir: Path) -> dict[str, Any]:
    reports = []
    missing_files = []
    for source_id, filename in FILES.items():
        path = input_dir / filename
        if not path.is_file():
            missing_files.append({"source_id": source_id, "expected_path": str(path)})
            continue
        reports.append(audit_csv(path, source_id))
    return {
        "report_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "publisher": "HydroSense Lab, IIT Delhi; IFI-Impacts hosted by Zenodo",
        "record_url": "https://zenodo.org/records/16994648",
        "input_directory": str(input_dir),
        "missing_expected_files": missing_files,
        "datasets": reports,
        "scientific_conclusion": (
            "Use these data as independent historical event/district context after checking the paper, schema and licence. "
            "Do not convert district mentions or district severity values into ward-level or station-hour labels. "
            "A flood prediction claim remains blocked until independently verified outcomes match the intended spatial unit, "
            "time interval, issue time and prediction horizon."
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
    print(f"Wrote IFI audit report: {args.output}")
    for dataset in report["datasets"]:
        print(f"- {dataset['filename']}: {dataset['rows']:,} rows; {len(dataset['columns'])} columns")
        if dataset.get("rows_mentioning_district_field_mentioning_ernakulam") is not None:
            print(f"  District-field Ernakulam mentions: {dataset['rows_mentioning_district_field_mentioning_ernakulam']}")
    print(f"Expected files missing: {len(report['missing_expected_files'])}")
    return 1 if report["missing_expected_files"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

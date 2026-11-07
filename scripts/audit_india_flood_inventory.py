"""Acquire and audit the open India Flood Inventory–Impacts v4 event CSV.

This is an event-inventory provenance/coverage audit, not a flood model.
The report deliberately does not treat representative coordinates as flood
footprints or district impact fields as local inundation depth observations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd

SOURCE_URL = (
    "https://zenodo.org/records/16994648/files/"
    "India_Flood_Inventory_v3.csv?download=1"
)
EXPECTED_MD5 = "fea75a9ff9eba8fb328eaddfacd21d67"
REQUIRED_COLUMNS = {
    "UEI", "Start Date", "End Date", "State", "Districts",
    "Latitude", "Longitude", "Severity", "Area Affected",
    "Human fatality", "Human injured", "Human Displaced", "Event Source",
}
IMPACT_COLUMNS = (
    "Area Affected", "Human fatality", "Human injured", "Human Displaced",
)


def audit_inventory(frame: pd.DataFrame, *, md5: str | None = None) -> dict[str, Any]:
    missing = sorted(REQUIRED_COLUMNS - set(frame.columns))
    if missing:
        return {
            "schema_version": "india-flood-inventory-audit/1.0.0",
            "status": "BLOCKED_SCHEMA",
            "problems": [f"Missing required columns: {missing}"],
            "training_ready": False,
        }
    data = frame.copy()
    problems: list[str] = []
    warnings: list[str] = []
    ids = data["UEI"].astype("string").str.strip()
    if ids.isna().any() or ids.eq("").any():
        problems.append("UEI contains blank event identifiers.")
    if ids.duplicated().any():
        problems.append("UEI is not unique; duplicate events require source review.")
    start = pd.to_datetime(data["Start Date"], errors="coerce", dayfirst=True)
    end = pd.to_datetime(data["End Date"], errors="coerce", dayfirst=True)
    if start.isna().any():
        problems.append("Start Date contains missing or invalid dates.")
    if end.isna().any():
        problems.append("End Date contains missing or invalid dates.")
    if not start.isna().any() and not end.isna().any() and (end < start).any():
        problems.append("End Date precedes Start Date for one or more events.")

    lat = pd.to_numeric(data["Latitude"], errors="coerce")
    lon = pd.to_numeric(data["Longitude"], errors="coerce")
    coordinate_pairs = lat.notna() & lon.notna()
    one_sided = lat.notna() ^ lon.notna()
    invalid_coordinates = coordinate_pairs & (
        ~lat.between(-90, 90) | ~lon.between(-180, 180)
    )
    if one_sided.any():
        warnings.append(f"{int(one_sided.sum())} rows have only one coordinate; they are not geolocatable.")
    if invalid_coordinates.any():
        problems.append(f"{int(invalid_coordinates.sum())} rows have out-of-range coordinates.")

    state = data["State"].fillna("").astype(str)
    districts = data["Districts"].fillna("").astype(str)
    kerala = state.str.contains(r"\bKerala\b", case=False, regex=True) | districts.str.contains(
        r"\bErnakulam\b", case=False, regex=True
    )
    impact_coverage = {
        column: int(pd.to_numeric(data[column], errors="coerce").notna().sum())
        for column in IMPACT_COLUMNS
    }
    missing_impact = {
        column: int(pd.to_numeric(data[column], errors="coerce").isna().sum())
        for column in IMPACT_COLUMNS
    }
    if not coordinate_pairs.any():
        warnings.append("No event has a complete latitude/longitude pair.")
    if not kerala.any():
        warnings.append("No Kerala/Ernakulam text match was found; inspect source geography fields.")
    if not any(impact_coverage.values()):
        warnings.append("No numeric impact fields are populated.")

    return {
        "schema_version": "india-flood-inventory-audit/1.0.0",
        "status": "AUDITED_EVENT_INVENTORY_NOT_LOCAL_INUNDATION_GROUND_TRUTH" if not problems else "BLOCKED_DATA_QUALITY",
        "source_url": SOURCE_URL,
        "source_md5": md5,
        "row_count": int(len(data)),
        "unique_uei_count": int(ids.nunique(dropna=True)),
        "date_min": None if start.dropna().empty else start.min().date().isoformat(),
        "date_max": None if start.dropna().empty else start.max().date().isoformat(),
        "complete_coordinate_pair_count": int(coordinate_pairs.sum()),
        "one_sided_coordinate_count": int(one_sided.sum()),
        "kerala_or_ernakulam_text_match_count": int(kerala.sum()),
        "impact_field_non_missing_counts": impact_coverage,
        "impact_field_missing_counts": missing_impact,
        "problems": problems,
        "warnings": warnings,
        "training_ready": False,
        "interpretation": (
            "Public historical event inventory and district-impact context only. "
            "Representative or missing coordinates are not inundation polygons; "
            "reported district impacts are not site-level depth/duration observations. "
            "Do not use this audit as flood occurrence or impact model validation."
        ),
    }


def acquire_and_audit(output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ai-resilience-ifi-") as temp_dir:
        csv_path = Path(temp_dir) / "India_Flood_Inventory_v3.csv"
        request = urllib.request.Request(
            SOURCE_URL,
            headers={"User-Agent": "AI-RESILIENCE-evidence-audit/1.0"},
        )
        digest = hashlib.md5()
        with urllib.request.urlopen(request, timeout=90) as response, csv_path.open("wb") as stream:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                stream.write(chunk)
        actual_md5 = digest.hexdigest()
        if actual_md5 != EXPECTED_MD5:
            raise ValueError(
                f"Source checksum mismatch: expected {EXPECTED_MD5}, got {actual_md5}."
            )
        frame = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)
        report = audit_inventory(frame, md5=actual_md5)
    report["checksum_verified"] = True
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("reports/india_flood_inventory_audit.json"))
    args = parser.parse_args()
    report = acquire_and_audit(args.output)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["status"] == "AUDITED_EVENT_INVENTORY_NOT_LOCAL_INUNDATION_GROUND_TRUTH" else 2


if __name__ == "__main__":
    raise SystemExit(main())

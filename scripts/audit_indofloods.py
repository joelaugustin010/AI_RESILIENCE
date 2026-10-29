"""Descriptive audit of the INDOFLOODS gauge-event research dataset.

This audit checks event IDs, dates, gauge metadata, Kerala station coverage and
join coverage across the published tables. It does not create non-event labels,
merge stations to NWDP by name, train a model, or claim predictive skill.
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
DEFAULT_OUTPUT = ROOT / "data" / "external" / "indofloods_audit_report.json"
FILES = {
    "events": "floodevents_indofloods.csv",
    "metadata": "metadata_indofloods.csv",
    "catchment": "catchment_characteristics_indofloods.csv",
    "precipitation": "precipitation_variables_indofloods.csv",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_table(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False)


def summarize_table(path: Path, table_id: str) -> dict[str, Any]:
    frame = read_table(path)
    report: dict[str, Any] = {
        "table_id": table_id,
        "filename": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "rows": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "missing_values_by_column": {
            str(column): int(count)
            for column, count in frame.isna().sum().items()
            if count
        },
        "exact_duplicate_rows": int(frame.duplicated().sum()),
    }
    if "GaugeID" in frame.columns:
        ids = frame["GaugeID"].astype("string").str.strip()
        report["gauge_id_missing"] = int(ids.isna().sum() + ids.eq("").sum())
        report["unique_gauge_ids"] = int(ids.nunique(dropna=True))
    if "Privacy" in frame.columns:
        privacy = frame["Privacy"].astype("string").str.strip().str.casefold()
        report["source_privacy_counts"] = {
            str(label): int(count)
            for label, count in privacy.fillna("<missing>").value_counts().items()
        }
    if "EventID" in frame.columns:
        ids = frame["EventID"].astype("string").str.strip()
        report["event_id_missing"] = int(ids.isna().sum() + ids.eq("").sum())
        report["unique_event_ids"] = int(ids.nunique(dropna=True))
        report["duplicate_event_id_rows"] = int(ids.duplicated(keep=False).sum())
        parsed_gauge_ids = ids.str.extract(r"^(INDOFLOODS-gauge-[0-9]+)-")[0]
        report["event_ids_without_recognized_gauge_prefix"] = int(
            (ids.notna() & ids.ne("") & parsed_gauge_ids.isna()).sum()
        )
    if "Start Date" in frame.columns:
        dates = pd.to_datetime(frame["Start Date"], errors="coerce")
        report["start_date_invalid_count"] = int(dates.isna().sum())
        report["start_date_first"] = dates.min().isoformat() if dates.notna().any() else None
        report["start_date_last"] = dates.max().isoformat() if dates.notna().any() else None
    if "End Date" in frame.columns:
        dates = pd.to_datetime(frame["End Date"], errors="coerce")
        report["end_date_invalid_count"] = int(dates.isna().sum())
        report["end_date_first"] = dates.min().isoformat() if dates.notna().any() else None
        report["end_date_last"] = dates.max().isoformat() if dates.notna().any() else None
    if {"Start Date", "End Date"}.issubset(frame.columns):
        starts = pd.to_datetime(frame["Start Date"], errors="coerce")
        ends = pd.to_datetime(frame["End Date"], errors="coerce")
        valid_dates = starts.notna() & ends.notna()
        report["event_end_before_start_count"] = int((valid_dates & ends.lt(starts)).sum())
    if {"Latitude", "Longitude"}.issubset(frame.columns):
        lat = pd.to_numeric(frame["Latitude"], errors="coerce")
        lon = pd.to_numeric(frame["Longitude"], errors="coerce")
        valid = lat.notna() & lon.notna()
        report["coordinate_pairs_numeric"] = int(valid.sum())
        report["coordinate_pairs_missing_or_invalid"] = int((~valid).sum())
        report["coordinate_pairs_outside_broad_India_screen"] = int(
            (valid & (~lat.between(6, 38) | ~lon.between(67, 98))).sum()
        )
    return report


def build_report(input_dir: Path) -> dict[str, Any]:
    missing = [
        {"table_id": table_id, "expected_path": str(input_dir / filename)}
        for table_id, filename in FILES.items()
        if not (input_dir / filename).is_file()
    ]
    tables: dict[str, pd.DataFrame] = {}
    reports = []
    for table_id, filename in FILES.items():
        path = input_dir / filename
        if path.is_file():
            tables[table_id] = read_table(path)
            reports.append(summarize_table(path, table_id))

    crosswalk: dict[str, Any] = {
        "status": "NOT_EVALUATED_MISSING_TABLES" if missing else "DESCRIPTIVE_ONLY",
        "kerala_gauge_count": None,
        "kerala_gauge_ids": [],
        "event_rows_for_kerala_gauges": None,
        "event_ids_missing_from_precipitation_table": None,
        "event_gauges_missing_from_metadata": None,
        "event_gauges_missing_from_catchment_table": None,
        "kerala_gauge_privacy_counts": None,
    }
    if "metadata" in tables:
        metadata = tables["metadata"]
        required = {"GaugeID", "State"}
        if required.issubset(metadata.columns):
            state = metadata["State"].astype("string").str.strip().str.casefold()
            kerala = metadata.loc[state.eq("kerala")].copy()
            gauge_ids = sorted(kerala["GaugeID"].dropna().astype(str).str.strip().unique().tolist())
            crosswalk["kerala_gauge_count"] = len(gauge_ids)
            crosswalk["kerala_gauge_ids"] = gauge_ids
            if "Privacy" in kerala.columns:
                privacy = kerala["Privacy"].astype("string").str.strip().str.casefold()
                crosswalk["kerala_gauge_privacy_counts"] = {
                    str(label): int(count)
                    for label, count in privacy.fillna("<missing>").value_counts().items()
                }
            else:
                crosswalk["kerala_gauge_privacy_counts"] = {"<privacy_column_missing>": len(kerala)}
            crosswalk["kerala_station_names"] = (
                sorted(kerala["Station"].dropna().astype(str).str.strip().unique().tolist())
                if "Station" in kerala.columns else []
            )
            crosswalk["kerala_basins"] = (
                sorted(kerala["Basin"].dropna().astype(str).str.strip().unique().tolist())
                if "Basin" in kerala.columns else []
            )
            if {"Latitude", "Longitude"}.issubset(kerala.columns):
                lat = pd.to_numeric(kerala["Latitude"], errors="coerce")
                lon = pd.to_numeric(kerala["Longitude"], errors="coerce")
                crosswalk["kerala_coordinates_missing_or_outside_screen"] = int(
                    (lat.isna() | lon.isna() | ~lat.between(6, 15) | ~lon.between(74, 78)).sum()
                )
            if "events" in tables and "EventID" in tables["events"].columns:
                # Event IDs embed the dataset's explicit GaugeID prefix, e.g.
                # INDOFLOODS-gauge-411-1. Parse that identifier; never join by station name.
                event_ids = tables["events"]["EventID"].astype("string").str.extract(
                    r"^(INDOFLOODS-gauge-[0-9]+)-"
                )[0]
                event_gauges = set(event_ids.dropna().astype(str))
                crosswalk["event_rows_for_kerala_gauges"] = int(event_ids.isin(gauge_ids).sum())
                crosswalk["kerala_gauges_with_at_least_one_event"] = sorted(event_gauges.intersection(gauge_ids))
                metadata_gauges = set(metadata["GaugeID"].dropna().astype(str))
                crosswalk["event_gauges_missing_from_metadata"] = sorted(event_gauges - metadata_gauges)
                if "precipitation" in tables and "EventID" in tables["precipitation"] and "EventID" in tables["events"]:
                    events = set(tables["events"]["EventID"].dropna().astype(str))
                    precip = set(tables["precipitation"]["EventID"].dropna().astype(str))
                    crosswalk["event_ids_missing_from_precipitation_table"] = len(events - precip)
                if "catchment" in tables and "GaugeID" in tables["catchment"]:
                    catchment_gauges = set(tables["catchment"]["GaugeID"].dropna().astype(str))
                    crosswalk["metadata_gauges_missing_from_catchment_table"] = len(metadata_gauges - catchment_gauges)
                    crosswalk["catchment_gauges_missing_from_metadata"] = len(catchment_gauges - metadata_gauges)
                    crosswalk["event_gauges_missing_from_catchment_table"] = sorted(event_gauges - catchment_gauges)

    return {
        "report_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_record": "https://zenodo.org/records/14584655",
        "dataset_doi": "10.5281/zenodo.14584654",
        "input_directory": str(input_dir),
        "missing_expected_files": missing,
        "tables": reports,
        "crosswalk_checks": crosswalk,
        "scientific_conclusion": (
            "INDOFLOODS contains historical gauge-event records and is a stronger outcome candidate than district-only inventories. "
            "It is not automatically a Kochi model dataset: confirm local basin/station coverage, gauge identity, target timing, "
            "feature availability and licence. Flood-event rows alone do not provide representative non-event examples. "
            "Event-scale precipitation variables may leak information unless their windows are proven to precede the issue time. "
            "Never match stations by name alone or interpret this descriptive audit as predictive validation."
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
    print(f"Wrote INDOFLOODS audit report: {args.output}")
    for table in report["tables"]:
        print(f"- {table['filename']}: {table['rows']:,} rows; {len(table['columns'])} columns")
    print(f"Missing expected files: {len(report['missing_expected_files'])}")
    crosswalk = report["crosswalk_checks"]
    if crosswalk["kerala_gauge_count"] is not None:
        print(f"Kerala gauges in metadata: {crosswalk['kerala_gauge_count']}")
        print(f"Flood-event rows associated with Kerala gauges: {crosswalk['event_rows_for_kerala_gauges']}")
    return 1 if report["missing_expected_files"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

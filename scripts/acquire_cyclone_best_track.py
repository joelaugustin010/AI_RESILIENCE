"""Acquire and descriptively audit the IMD/RSMC North Indian Ocean cyclone best-track mirror.

The mirror contains parsed tables derived from the official IMD workbook. Raw
Parquet files are stored outside Git and uploaded only as a short-lived private
artifact. The script preserves all rows and source quality flags; it does not
predict cyclone impacts or issue warnings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


MIRROR_BASE = "https://raw.githubusercontent.com/syedhamidali/imdtrack/main/data/"
ORIGINAL_IMD_BEST_TRACK_URL = "https://rsmcnewdelhi.imd.gov.in/download.php?path=uploads/best-track/78b4b0_Best_Tracks__Data__1982-2026_.xlsx"
KOCHI_REFERENCE = {"latitude": 9.9312, "longitude": 76.2673, "label": "approximate Kochi city-centre screening point"}
ALLOWED_HOST = "raw.githubusercontent.com"
MAX_FILE_BYTES = 80 * 1024 * 1024
FILE_NAMES = ("manifest.json", "observations.parquet", "storms.parquet", "remarks.parquet")
EXPECTED_COLUMNS = {"storm_id", "time", "lat", "lon", "basin", "year"}


def validate_source_manifest(manifest: dict) -> None:
    required = ("source_url", "source_sha256", "generated_at", "n_storms", "n_obs", "n_remarks", "year_min", "year_max")
    missing = [key for key in required if key not in manifest or manifest[key] in (None, "")]
    if missing:
        raise ValueError("Source manifest missing required field(s): " + ", ".join(missing))
    parsed = urlparse(str(manifest["source_url"]))
    if parsed.scheme != "https" or parsed.hostname != "rsmcnewdelhi.imd.gov.in":
        raise ValueError("Manifest source_url is not the allowlisted official IMD/RSMC host")
    digest = str(manifest["source_sha256"]).lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("source_sha256 must be a 64-character hexadecimal digest")
    for key in ("n_storms", "n_obs", "n_remarks", "year_min", "year_max"):
        if int(manifest[key]) < 0:
            raise ValueError(f"{key} cannot be negative")
    if int(manifest["year_min"]) > int(manifest["year_max"]):
        raise ValueError("year_min must not exceed year_max")


def _download(url: str, destination: Path) -> dict:
    parsed = urlparse(url)
    expected_prefix = "/syedhamidali/imdtrack/main/data/"
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST or not parsed.path.startswith(expected_prefix):
        raise ValueError("Only allowlisted HTTPS raw files from syedhamidali/imdtrack/main/data are permitted")
    if Path(parsed.path).name not in FILE_NAMES:
        raise ValueError("Requested file is not on the fixed best-track file allowlist")
    request = Request(url, headers={"User-Agent": "AI-RESILIENCE-Research-Data-Acquisition/1.0"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    total = 0
    final_url = url
    content_type = "unknown"
    try:
        with urlopen(request, timeout=60) as response:
            final = urlparse(response.geturl())
            if final.scheme != "https" or final.hostname != ALLOWED_HOST or not final.path.startswith(expected_prefix):
                raise ValueError("Download redirected outside the allowlisted raw GitHub path")
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "unknown")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > MAX_FILE_BYTES:
                raise ValueError("Source file exceeds the configured size limit")
            with temporary.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_FILE_BYTES:
                        raise ValueError("Source file exceeded the configured size limit")
                    digest.update(chunk)
                    output.write(chunk)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "source_url": url,
        "final_url": final_url,
        "local_file": str(destination),
        "bytes": total,
        "sha256": digest.hexdigest(),
        "content_type": content_type,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _flag_mask(series: pd.Series | None, index: pd.Index) -> pd.Series:
    if series is None:
        return pd.Series(False, index=index, dtype=bool)
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.fillna(False).astype(bool)
    return series.astype("string").str.strip().str.casefold().isin({"true", "1", "yes", "y"}).fillna(False)


def haversine_km(latitudes, longitudes, target_lat: float = KOCHI_REFERENCE["latitude"], target_lon: float = KOCHI_REFERENCE["longitude"]):
    """Great-circle distance in km; intended for coarse track screening only."""
    lat = np.radians(np.asarray(latitudes, dtype=float))
    lon = np.radians(np.asarray(longitudes, dtype=float))
    target_lat_r = math.radians(target_lat)
    target_lon_r = math.radians(target_lon)
    dlat = lat - target_lat_r
    dlon = lon - target_lon_r
    a = np.sin(dlat / 2) ** 2 + np.cos(target_lat_r) * np.cos(lat) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _first_value(series: pd.Series):
    values = series.dropna()
    if values.empty:
        return None
    value = values.iloc[0]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    return str(value) if not isinstance(value, (str, int, float, bool)) else value


def build_audit_report(
    observations: pd.DataFrame,
    storms: pd.DataFrame,
    remarks: pd.DataFrame,
    source_manifest: dict,
    file_hashes: dict[str, str] | None = None,
) -> dict:
    """Audit row counts, source flags and approximate track proximity without altering data."""
    validate_source_manifest(source_manifest)
    missing = sorted(EXPECTED_COLUMNS - set(observations.columns))
    if missing:
        raise ValueError("Observations table missing required column(s): " + ", ".join(missing))
    for label, frame in (("storms", storms), ("remarks", remarks)):
        if "storm_id" not in frame.columns:
            raise ValueError(f"{label} table is missing required storm_id column")
    expected_counts = {
        "observations": int(source_manifest["n_obs"]),
        "storms": int(source_manifest["n_storms"]),
        "remarks": int(source_manifest["n_remarks"]),
    }
    actual_counts = {"observations": len(observations), "storms": len(storms), "remarks": len(remarks)}
    if actual_counts != expected_counts:
        raise ValueError(f"Downloaded table counts do not match mirror manifest: expected={expected_counts}, actual={actual_counts}")

    obs = observations.copy()
    obs["time_utc"] = pd.to_datetime(obs["time"], errors="coerce", utc=True)
    obs["lat_numeric"] = pd.to_numeric(obs["lat"], errors="coerce")
    obs["lon_numeric"] = pd.to_numeric(obs["lon"], errors="coerce")
    pos_flags = _flag_mask(obs["pos_suspect"] if "pos_suspect" in obs.columns else None, obs.index)
    date_flags = _flag_mask(obs["date_suspect"] if "date_suspect" in obs.columns else None, obs.index)
    coords_present = obs["lat_numeric"].notna() & obs["lon_numeric"].notna()
    coords_in_range = coords_present & obs["lat_numeric"].between(-90, 90) & obs["lon_numeric"].between(-180, 180)
    obs["pos_suspect_flag"] = pos_flags
    obs["date_suspect_flag"] = date_flags
    obs["distance_to_kochi_km"] = np.nan
    if coords_in_range.any():
        obs.loc[coords_in_range, "distance_to_kochi_km"] = haversine_km(
            obs.loc[coords_in_range, "lat_numeric"], obs.loc[coords_in_range, "lon_numeric"]
        )
    usable = coords_in_range & ~pos_flags
    duplicate_mask = obs["time_utc"].notna() & obs.duplicated(subset=["storm_id", "time_utc"], keep=False)

    storm_rows = []
    for storm_id, group in obs.groupby("storm_id", dropna=False, sort=False):
        good = group.loc[usable.loc[group.index]]
        distance = good["distance_to_kochi_km"].min() if not good.empty else np.nan
        item = {
            "storm_id": str(storm_id),
            "nearest_non_suspect_fix_km": float(distance) if pd.notna(distance) else None,
            "first_non_suspect_fix_utc": good["time_utc"].min().isoformat() if not good.empty and good["time_utc"].notna().any() else None,
            "last_non_suspect_fix_utc": good["time_utc"].max().isoformat() if not good.empty and good["time_utc"].notna().any() else None,
            "non_suspect_fix_count": int(len(good)),
            "position_suspect_fix_count": int(group["pos_suspect_flag"].sum()),
            "date_suspect_fix_count": int(group["date_suspect_flag"].sum()),
        }
        for column in ("name", "basin", "year"):
            if column in group.columns:
                item[column] = _first_value(group[column])
        if "wind" in group.columns:
            wind = pd.to_numeric(group["wind"], errors="coerce").dropna()
            item["peak_recorded_wind_knots"] = float(wind.max()) if not wind.empty else None
        storm_rows.append(item)
    nearest = [row for row in storm_rows if row["nearest_non_suspect_fix_km"] is not None]
    nearest.sort(key=lambda row: row["nearest_non_suspect_fix_km"])
    count_100 = sum(row["nearest_non_suspect_fix_km"] <= 100 for row in nearest)
    count_300 = sum(row["nearest_non_suspect_fix_km"] <= 300 for row in nearest)

    times = obs["time_utc"].dropna()
    return {
        "audit_version": 1,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DESCRIPTIVE_AUDIT_ONLY_NOT_VALIDATED_FOR_IMPACT_PREDICTION",
        "source": {
            "original_publisher": "India Meteorological Department / RSMC New Delhi",
            "official_best_track_page": "https://rsmcnewdelhi.imd.gov.in/report.php?internal_menu=MzM%3D",
            "original_workbook_url": source_manifest["source_url"],
            "original_workbook_sha256_as_reported_by_mirror": source_manifest["source_sha256"],
            "mirror_repository": "https://github.com/syedhamidali/imdtrack",
            "mirror_repository_license": "BSD-3-Clause for the parser repository; underlying IMD data are © IMD and terms require confirmation",
            "mirror_generated_at": source_manifest["generated_at"],
            "year_min": int(source_manifest["year_min"]),
            "year_max": int(source_manifest["year_max"]),
            "expected_table_counts": expected_counts,
            "actual_table_counts": actual_counts,
            "file_sha256": file_hashes or {},
        },
        "data_quality": {
            "valid_timestamp_rows": int(obs["time_utc"].notna().sum()),
            "invalid_timestamp_rows": int(obs["time_utc"].isna().sum()),
            "missing_coordinate_rows": int((~coords_present).sum()),
            "out_of_range_coordinate_rows": int((coords_present & ~coords_in_range).sum()),
            "duplicate_storm_time_rows": int(duplicate_mask.sum()),
            "position_suspect_rows": int(pos_flags.sum()),
            "date_suspect_rows": int(date_flags.sum()),
            "rows_without_position_or_date_flag_columns": [name for name in ("pos_suspect", "date_suspect") if name not in obs.columns],
            "time_range_utc": [times.min().isoformat(), times.max().isoformat()] if not times.empty else None,
            "basin_counts": {str(k): int(v) for k, v in obs["basin"].value_counts(dropna=False).items()},
            "rows_with_valid_non_suspect_coordinates": int(usable.sum()),
        },
        "kochi_proximity_screening": {
            "reference_point": KOCHI_REFERENCE,
            "storms_with_at_least_one_non_suspect_fix_within_100_km": int(count_100),
            "storms_with_at_least_one_non_suspect_fix_within_300_km": int(count_300),
            "nearest_storms": nearest[:25],
            "interpretation": "Track-to-point distance is a discovery statistic only. It is not a wind footprint, rainfall footprint, storm-surge extent, landfall impact or probability of consequences in Kochi.",
        },
        "limitations": [
            "No source rows or flags were corrected, dropped, or overwritten.",
            "The mirror notes that the latest season may be tentative until IMD post-season review.",
            "Historical best-track fixes do not provide local damage labels, storm-surge heights, flood depth, or building-level exposure.",
            "Track distance to an approximate city-centre point is not a municipal-boundary intersection or a hazard impact model.",
            "Underlying data are © IMD; verify source terms before redistribution or operational use.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/external/cyclone_best_track"))
    args = parser.parse_args(argv)
    output_dir = args.output_dir
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    source_manifest_url = MIRROR_BASE + "manifest.json"
    source_manifest_file = raw_dir / "manifest.json"
    manifest_download = _download(source_manifest_url, source_manifest_file)
    source_manifest = json.loads(source_manifest_file.read_text(encoding="utf-8"))
    validate_source_manifest(source_manifest)

    file_hashes = {"manifest.json": manifest_download["sha256"]}
    downloads = [manifest_download]
    for filename in ("observations.parquet", "storms.parquet", "remarks.parquet"):
        record = _download(MIRROR_BASE + filename, raw_dir / filename)
        downloads.append(record)
        file_hashes[filename] = record["sha256"]

    observations = pd.read_parquet(raw_dir / "observations.parquet")
    storms = pd.read_parquet(raw_dir / "storms.parquet")
    remarks = pd.read_parquet(raw_dir / "remarks.parquet")
    audit = build_audit_report(observations, storms, remarks, source_manifest, file_hashes)
    acquisition_manifest = {
        "acquisition_status": "DOWNLOADED_RAW_UNVALIDATED",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "mirror_base_url": MIRROR_BASE,
        "original_official_workbook_downloaded": False,
        "downloads": downloads,
        "source_manifest": source_manifest,
        "repository_license_note": "BSD-3-Clause parser repository; underlying IMD dataset is copyright IMD; verify terms before redistribution.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "acquisition_manifest.json").write_text(json.dumps(acquisition_manifest, indent=2) + "\n", encoding="utf-8")
    (output_dir / "cyclone_best_track_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(f"IMD/RSMC best-track mirror: {audit['source']['actual_table_counts']}")
    print(f"Valid timestamps: {audit['data_quality']['valid_timestamp_rows']}; position-suspect fixes: {audit['data_quality']['position_suspect_rows']}; date-suspect fixes: {audit['data_quality']['date_suspect_rows']}")
    print("Storms within 100 km / 300 km of approximate Kochi point:",
          audit["kochi_proximity_screening"]["storms_with_at_least_one_non_suspect_fix_within_100_km"], "/",
          audit["kochi_proximity_screening"]["storms_with_at_least_one_non_suspect_fix_within_300_km"])
    print("Historical track screening is not an impact prediction; no source flags were corrected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

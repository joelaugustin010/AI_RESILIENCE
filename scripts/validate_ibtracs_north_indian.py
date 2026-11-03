"""Validate a preserved NOAA IBTrACS North Indian Ocean CSV snapshot."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = (
    "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-"
    "stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv"
)
SOURCE_PAGE = "https://www.ncei.noaa.gov/products/international-best-track-archive"
DOI_METADATA = "https://api.datacite.org/dois/10.25921/82ty-9e16"
OUTPUT = ROOT / "data" / "raw" / "ibtracs" / "ibtracs.NI.list.v04r01.csv"
METADATA = OUTPUT.with_name(OUTPUT.name + ".metadata.json")
USER_AGENT = "AI_RESILIENCE data foundation research (read-only public dataset retrieval)"
REQUIRED_COLUMNS = ("SID", "BASIN", "NAME", "ISO_TIME", "LAT", "LON", "WMO_WIND", "WMO_PRES")
KOCHI = (9.9312, 76.2673)
EARTH_RADIUS_KM = 6371.0088


class IBTrACSDataError(ValueError):
    """Raised when the source snapshot fails structural or coordinate checks."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _distance_km(lat: float, lon: float) -> float:
    lat1, lat2 = math.radians(KOCHI[0]), math.radians(lat)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(lon - KOCHI[1])
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return EARTH_RADIUS_KM * 2 * math.asin(min(1.0, math.sqrt(haversine)))


def validate_csv(path: Path) -> dict[str, Any]:
    """Scan all rows and report schema, time, coordinate and local-coverage QA."""
    row_count = 0
    storm_ids: set[str] = set()
    nearby_storm_ids: set[str] = set()
    seen_keys: set[tuple[str, str]] = set()
    duplicate_keys = 0
    missing: Counter[str] = Counter()
    basins: Counter[str] = Counter()
    years: list[int] = []
    bounds = [math.inf, -math.inf, math.inf, -math.inf]
    invalid_coordinates = 0
    near_kochi_points = 0

    try:
        with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source)
            columns = next(reader, None)
            units = next(reader, None)
            if not columns or not units:
                raise IBTrACSDataError("CSV must have a column header row and a units row.")
            if len(columns) != len(set(columns)):
                raise IBTrACSDataError("CSV contains duplicate column names.")
            missing_columns = sorted(set(REQUIRED_COLUMNS) - set(columns))
            if missing_columns:
                raise IBTrACSDataError("CSV is missing required columns: " + ", ".join(missing_columns))
            if len(columns) != len(units):
                raise IBTrACSDataError("Column and units rows have different lengths.")
            unit_by_column = dict(zip(columns, units))
            expected_units = {
                "LAT": "degrees_north",
                "LON": "degrees_east",
                "WMO_WIND": "kts",
                "WMO_PRES": "mb",
                "DIST2LAND": "km",
            }
            unit_mismatches = {
                name: unit_by_column.get(name, "").strip()
                for name, expected in expected_units.items()
                if name in unit_by_column and unit_by_column[name].strip() != expected
            }
            if unit_mismatches:
                raise IBTrACSDataError(f"Unexpected units for required variables: {unit_mismatches}")
            rows = csv.DictReader(source, fieldnames=columns)
            for row in rows:
                if not any((value or "").strip() for value in row.values()):
                    continue
                if None in row or any(value is None for value in row.values()):
                    raise IBTrACSDataError(
                        f"CSV observation row {row_count + 3} does not match the declared column count."
                    )
                row_count += 1
                storm_id = (row.get("SID") or "").strip()
                basin = (row.get("BASIN") or "").strip()
                if basin:
                    basins[basin] += 1
                time_value = (row.get("ISO_TIME") or "").strip()
                if not storm_id:
                    missing["SID"] += 1
                else:
                    storm_ids.add(storm_id)
                try:
                    parsed_time = datetime.strptime(time_value, "%Y-%m-%d %H:%M:%S")
                    years.append(parsed_time.year)
                except ValueError:
                    missing["ISO_TIME"] += 1
                key = (storm_id, time_value)
                if key in seen_keys:
                    duplicate_keys += 1
                seen_keys.add(key)

                try:
                    latitude = float((row.get("LAT") or "").strip())
                    longitude = float((row.get("LON") or "").strip())
                except ValueError:
                    missing["coordinate_pair"] += 1
                    continue
                if not (
                    math.isfinite(latitude)
                    and math.isfinite(longitude)
                    and -90 <= latitude <= 90
                    and -180 <= longitude <= 180
                ):
                    invalid_coordinates += 1
                    continue
                bounds[0] = min(bounds[0], longitude)
                bounds[1] = max(bounds[1], longitude)
                bounds[2] = min(bounds[2], latitude)
                bounds[3] = max(bounds[3], latitude)
                if _distance_km(latitude, longitude) <= 300:
                    near_kochi_points += 1
                    if storm_id:
                        nearby_storm_ids.add(storm_id)
    except (OSError, UnicodeError, csv.Error, StopIteration) as error:
        raise IBTrACSDataError(f"Could not read IBTrACS CSV: {error}") from error

    if not row_count:
        raise IBTrACSDataError("CSV contains no observation rows.")
    if missing or invalid_coordinates:
        raise IBTrACSDataError(
            f"Missing required values: {dict(missing)}; invalid coordinates: {invalid_coordinates}."
        )
    if duplicate_keys:
        raise IBTrACSDataError(f"Found {duplicate_keys} duplicate SID/ISO_TIME key(s).")
    if not math.isfinite(bounds[0]):
        raise IBTrACSDataError("No valid coordinates were found.")

    return {
        "row_count": row_count,
        "column_count": len(columns),
        "unit_row_column_count": len(units),
        "unit_mismatches": unit_mismatches,
        "storm_id_count": len(storm_ids),
        "year_min": min(years),
        "year_max": max(years),
        "basin_row_counts": dict(sorted(basins.items())),
        "geographic_bounds_lon_lat": bounds,
        "missing_required_value_counts": dict(missing),
        "invalid_coordinate_count": invalid_coordinates,
        "duplicate_sid_iso_time_key_count": duplicate_keys,
        "points_within_300_km_of_kochi_reference": near_kochi_points,
        "storm_ids_with_points_within_300_km_of_kochi_reference": len(nearby_storm_ids),
        "local_radius_method": (
            "Haversine great-circle distance from 9.9312 N, 76.2673 E; 300 km is a "
            "discovery/coverage QA radius only, not a cyclone impact radius."
        ),
    }


def acquire() -> Path:
    """Download only when the versioned raw output does not already exist."""
    if OUTPUT.exists() or METADATA.exists():
        raise FileExistsError(f"Refusing to overwrite an existing snapshot or sidecar: {OUTPUT}")
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            payload = response.read()
            content_type = response.headers.get("Content-Type", "")
    except Exception as error:
        raise IBTrACSDataError(f"NOAA source download failed: {error}") from error
    if "text/csv" not in content_type.casefold() or not payload:
        raise IBTrACSDataError(f"Unexpected NOAA response content type or empty body: {content_type!r}.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_name(OUTPUT.name + ".partial")
    try:
        temporary.write_bytes(payload)
        validation = validate_csv(temporary)
        temporary.replace(OUTPUT)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    _write_metadata(OUTPUT, payload, validation, datetime.now(timezone.utc).isoformat())
    return OUTPUT


def _write_metadata(
    path: Path,
    payload: bytes,
    validation: dict[str, Any],
    retrieved_at_utc: str,
) -> None:
    metadata = {
        "dataset_id": "noaa_ibtracs_north_indian_v04r01",
        "title": "IBTrACS Version 4r01 North Indian Ocean basin CSV snapshot",
        "source_url": SOURCE_URL,
        "source_page": SOURCE_PAGE,
        "publisher": "NOAA National Centers for Environmental Information (NCEI)",
        "retrieved_at_utc": retrieved_at_utc,
        "retrieved_on": retrieved_at_utc[:10],
        "publication_date": "Continuously updated; source listing modified 2026-11-01; snapshot accessed 2026-11-01 UTC",
        "doi": "https://doi.org/10.25921/82ty-9e16",
        "citation": (
            "Gahtan, J., K. R. Knapp, C. J. Schreck, H. J. Diamond, J. P. Kossin, "
            "M. C. Kruk, 2024: IBTrACS Project, Version 4r01 [North Indian Ocean "
            "subset]. NOAA NCEI. doi:10.25921/82ty-9e16."
        ),
        "license": (
            "No dataset-level licence or rights statement was found on the inspected NCEI "
            "product page or DataCite DOI metadata (rightsList empty), retrieved 2026-11-02. "
            "Do not redistribute, bundle, or integrate until NCEI confirms applicable reuse terms."
        ),
        "crs": "WGS 84 longitude/latitude coordinates in separate LAT and LON columns (EPSG:4326 semantics)",
        "units": (
            "ISO_TIME as source timestamps; LAT degrees_north; LON degrees_east; "
            "WMO_WIND knots; WMO_PRES millibars; DIST2LAND km where supplied. "
            "Per-agency fields may use other units documented in the source units row."
        ),
        "geographic_coverage": (
            "North Indian Ocean basin CSV; observed record coordinate bounds are recorded in "
            "validation. CSV includes some cross-basin rows as encoded in its BASIN field. "
            "Kochi-area presence is assessed independently in validation."
        ),
        "temporal_coverage": "Observed record period is determined from ISO_TIME during validation.",
        "file": path.relative_to(ROOT).as_posix(),
        "bytes": len(payload),
        "sha256": _sha256(payload),
        "validation": validation,
        "reuse_status": "ACQUIRED_AND_STRUCTURALLY_VALIDATED_NOT_INTEGRATED_RIGHTS_UNRESOLVED",
        "limitations": [
            "IBTrACS is a harmonized best-track archive combining agency records; agency conventions and observation uncertainty vary.",
            "Best-track positions/intensity are historical observations/reanalyses, not forecasts and not local wind, surge, rainfall, damage, or consequence estimates.",
            "The source version is frequently updated; this preserved snapshot is not an automatically refreshed product.",
            "The source CSV units row is present and length-aligned; unit values are retained and checked against documented key variables.",
            "No dataset-specific licence was identified in the inspected official product page or DOI record, so this dataset is withheld from application integration pending rights clarification.",
            "Kochi radius counts are coverage diagnostics only and must not be interpreted as impact, landfall, risk, or return period."
        ],
    }
    METADATA.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def verify_existing() -> dict[str, Any]:
    if not OUTPUT.is_file():
        raise FileNotFoundError(f"IBTrACS snapshot not found: {OUTPUT}")
    payload = OUTPUT.read_bytes()
    validation = validate_csv(OUTPUT)
    if not METADATA.is_file():
        raise FileNotFoundError(
            f"Provenance sidecar is missing; file modification time is not accepted as retrieval evidence: {METADATA}"
        )
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    if metadata.get("sha256") != _sha256(payload):
        raise IBTrACSDataError("Snapshot checksum does not match its provenance sidecar.")
    if metadata.get("validation") != validation:
        raise IBTrACSDataError("Snapshot QA results differ from the stored provenance sidecar.")
    return validation | {"sha256": _sha256(payload), "bytes": len(payload), "sidecar": METADATA.relative_to(ROOT).as_posix()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Download only if no snapshot or sidecar exists.")
    args = parser.parse_args()
    if args.download:
        path = acquire()
        print(f"Downloaded {path.relative_to(ROOT).as_posix()}")
    print(json.dumps(verify_existing(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

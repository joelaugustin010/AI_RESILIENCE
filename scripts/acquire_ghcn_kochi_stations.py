"""Acquire and quality-review NOAA GHCN-Daily rainfall station records near Kochi."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "raw" / "ghcn"
BASE_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily"
STATIONS_URL = f"{BASE_URL}/ghcnd-stations.txt"
STATION_IDS = ("IN010032300", "IN010033100")
USER_AGENT = "AI_RESILIENCE historical rainfall data research (read-only public dataset retrieval)"
PRCP_ELEMENT = "PRCP"


class GHCNDataError(ValueError):
    """Raised when a GHCN station file fails schema, identity, or record checks."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_station_inventory(payload: bytes) -> dict[str, dict[str, Any]]:
    """Parse fixed-width GHCN station metadata for the requested station IDs."""
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise GHCNDataError("GHCN station inventory is not ASCII text.") from error
    requested = set(STATION_IDS)
    stations: dict[str, dict[str, Any]] = {}
    for line in lines:
        station_id = line[0:11].strip()
        if station_id not in requested:
            continue
        try:
            latitude = float(line[12:20])
            longitude = float(line[21:30])
            elevation_m = float(line[31:37])
        except ValueError as error:
            raise GHCNDataError(f"Invalid coordinate/elevation fields for station {station_id}.") from error
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise GHCNDataError(f"Station {station_id} has coordinates outside WGS 84 ranges.")
        stations[station_id] = {
            "station_id": station_id,
            "latitude": latitude,
            "longitude": longitude,
            "elevation_m": elevation_m,
            "state": line[38:40].strip(),
            "name": line[41:71].strip(),
            "gsn_flag": line[72:75].strip(),
            "hcn_flag": line[76:79].strip(),
            "wmo_id": line[80:85].strip(),
        }
    missing = requested - stations.keys()
    if missing:
        raise GHCNDataError("Requested station IDs absent from NOAA inventory: " + ", ".join(sorted(missing)))
    return stations


def validate_station_daily(payload: bytes, expected_station_id: str) -> dict[str, Any]:
    """Validate GHCN .dly fixed-width records and summarize PRCP observations."""
    try:
        lines = payload.decode("ascii").splitlines()
    except UnicodeDecodeError as error:
        raise GHCNDataError(f"{expected_station_id} daily file is not ASCII text.") from error
    if not lines:
        raise GHCNDataError(f"{expected_station_id} daily file is empty.")
    if any(len(line) != 269 for line in lines):
        lengths = sorted({len(line) for line in lines})
        raise GHCNDataError(f"GHCN .dly record length mismatch: {lengths}; expected 269 characters.")

    record_keys: set[tuple[int, int, str]] = set()
    precipitation = 0
    missing_values = 0
    quality_flagged_values = 0
    measurement_flags: Counter[str] = Counter()
    source_flags: Counter[str] = Counter()
    years = []
    precipitation_years = []
    for line_number, line in enumerate(lines, start=1):
        station_id = line[0:11]
        try:
            year = int(line[11:15])
            month = int(line[15:17])
        except ValueError as error:
            raise GHCNDataError(f"Invalid year/month on .dly record {line_number}.") from error
        element = line[17:21]
        if station_id != expected_station_id:
            raise GHCNDataError(
                f"Station identity mismatch on record {line_number}: expected {expected_station_id}, got {station_id}."
            )
        if not 1 <= month <= 12:
            raise GHCNDataError(f"Invalid month {month} on .dly record {line_number}.")
        key = (year, month, element)
        if key in record_keys:
            raise GHCNDataError(f"Duplicate station/year/month/element record: {key}.")
        record_keys.add(key)
        years.append(year)
        if element != PRCP_ELEMENT:
            continue
        precipitation_years.append(year)
        for day in range(1, 32):
            offset = 21 + (day - 1) * 8
            value_text = line[offset : offset + 5]
            mflag = line[offset + 5]
            qflag = line[offset + 6]
            sflag = line[offset + 7]
            try:
                value = int(value_text)
            except ValueError as error:
                raise GHCNDataError(
                    f"Invalid PRCP value on station {station_id}, {year}-{month:02d}, day {day}."
                ) from error
            if value == -9999:
                missing_values += 1
                continue
            precipitation += 1
            quality_flagged_values += bool(qflag.strip())
            measurement_flags[mflag.strip() or "blank"] += 1
            source_flags[sflag.strip() or "blank"] += 1

    if precipitation == 0:
        raise GHCNDataError(f"No non-missing PRCP observations found for {expected_station_id}.")
    return {
        "station_id": expected_station_id,
        "record_count": len(lines),
        "element_record_count": sum(key[2] == PRCP_ELEMENT for key in record_keys),
        "record_year_min": min(years),
        "record_year_max": max(years),
        "precipitation_year_min": min(precipitation_years),
        "precipitation_year_max": max(precipitation_years),
        "precipitation_observation_count": precipitation,
        "precipitation_missing_value_count": missing_values,
        "precipitation_quality_flagged_count": quality_flagged_values,
        "precipitation_measurement_flag_counts": dict(sorted(measurement_flags.items())),
        "precipitation_source_flag_counts": dict(sorted(source_flags.items())),
        "precipitation_units": "tenths of millimetres in raw GHCN-Daily source; divide by 10 for mm",
        "quality_policy": "Original values and M/Q/S flags are preserved; nonblank Q flags require review before analysis.",
    }


def _request(url: str) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read()
            if not payload:
                raise GHCNDataError(f"Empty response from {url}.")
            return payload, dict(response.headers)
    except GHCNDataError:
        raise
    except Exception as error:
        raise GHCNDataError(f"Download failed for {url}: {error}") from error


def acquire() -> dict[str, Any]:
    """Download the original inventory and two Kochi-area daily station files."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    inventory_path = OUTPUT / "ghcnd-stations.txt"
    if inventory_path.exists() or inventory_path.with_name(inventory_path.name + ".metadata.json").exists():
        raise FileExistsError(f"Refusing to overwrite an existing NOAA station inventory: {inventory_path}")
    inventory_bytes, inventory_headers = _request(STATIONS_URL)
    stations = parse_station_inventory(inventory_bytes)
    fetched: dict[str, tuple[Path, bytes, dict[str, str], dict[str, Any]]] = {}
    for station_id in STATION_IDS:
        path = OUTPUT / f"{station_id}.dly"
        sidecar_path = path.with_name(path.name + ".metadata.json")
        if path.exists() or sidecar_path.exists():
            raise FileExistsError(f"Refusing to overwrite an existing NOAA station file: {path}")
        source_url = f"{BASE_URL}/all/{station_id}.dly"
        payload, headers = _request(source_url)
        validation = validate_station_daily(payload, station_id)
        fetched[station_id] = (path, payload, headers, validation)

    retrieved_at = datetime.now(timezone.utc).isoformat()
    staged: list[tuple[Path, Path, bytes, dict[str, Any]]] = []
    inventory_sidecar = inventory_path.with_name(inventory_path.name + ".metadata.json")
    inventory_metadata = {
        "dataset_id": "noaa_ghcnd_station_inventory_2026",
        "title": "NOAA GHCN-Daily global station metadata inventory snapshot",
        "source_url": STATIONS_URL,
        "publisher": "NOAA National Centers for Environmental Information (NCEI)",
        "retrieved_at_utc": retrieved_at,
        "retrieved_on": retrieved_at[:10],
        "publication_date": "Continuously updated inventory; snapshot retrieved on the recorded date",
        "license": (
            "Publicly downloadable NOAA NCEI product; no explicit dataset-level downstream licence "
            "statement identified in the product documentation reviewed. Keep out of application "
            "distribution until reuse terms are confirmed."
        ),
        "crs": "Station inventory supplies latitude and longitude coordinates; WGS 84 datum is not stated in the file.",
        "units": "Latitude/longitude in decimal degrees; elevation in metres as documented in GHCN-Daily readme",
        "geographic_coverage": "Global station inventory; only two Kochi-area station rows are used for this acquisition.",
        "file": inventory_path.relative_to(ROOT).as_posix(),
        "bytes": len(inventory_bytes),
        "sha256": _sha256(inventory_bytes),
        "content_type": inventory_headers.get("Content-Type"),
        "selected_stations": stations,
        "reuse_status": "ACQUIRED_PUBLIC_DOWNLOAD_TERMS_REQUIRE_REVIEW_NOT_INTEGRATED",
        "limitations": [
            "Inventory coordinates and station identities are publisher-supplied metadata, not independently surveyed locations.",
            "The inventory does not establish current operation, data completeness, instrument condition, or positional accuracy.",
            "The original global inventory is retained to support a reproducible lookup of the selected station records.",
        ],
    }
    staged.append((inventory_path, inventory_sidecar, inventory_bytes, inventory_metadata))

    for station_id, (path, payload, headers, validation) in fetched.items():
        station = stations[station_id]
        sidecar_path = path.with_name(path.name + ".metadata.json")
        metadata = {
            "dataset_id": f"noaa_ghcnd_{station_id.lower()}_prcp",
            "title": f"NOAA GHCN-Daily station {station_id} ({station['name']}) source record",
            "source_url": f"{BASE_URL}/all/{station_id}.dly",
            "publisher": "NOAA National Centers for Environmental Information (NCEI), GHCN-Daily",
            "retrieved_at_utc": retrieved_at,
            "retrieved_on": retrieved_at[:10],
            "publication_date": "Station record is updated as the GHCN-Daily archive is revised",
            "license": (
                "Publicly downloadable NOAA NCEI product; no explicit dataset-level downstream licence "
                "statement identified in the product documentation reviewed. Keep out of application "
                "distribution until reuse terms are confirmed."
            ),
            "crs": "Station coordinates from ghcnd-stations.txt; WGS 84 datum is not explicitly stated in the inventory",
            "units": validation["precipitation_units"],
            "geographic_coverage": (
                f"NOAA station {station_id}, {station['name']}; source-inventory coordinate "
                f"{station['latitude']}, {station['longitude']}."
            ),
            "station_metadata": station,
            "station_inventory_file": inventory_path.relative_to(ROOT).as_posix(),
            "station_inventory_sha256": _sha256(inventory_bytes),
            "file": path.relative_to(ROOT).as_posix(),
            "bytes": len(payload),
            "sha256": _sha256(payload),
            "content_type": headers.get("Content-Type"),
            "validation": validation,
            "reuse_status": "ACQUIRED_STRUCTURALLY_VALIDATED_RIGHTS_REVIEW_REQUIRED_NOT_INTEGRATED",
            "limitations": [
                "GHCN-Daily international station data are assembled from national data providers; source flags and quality flags must be retained.",
                "The NCEI product page says Indian precipitation records in the international collection generally ended in 1970; actual period and data availability for this station are reported in validation.",
                "Daily observations are historical station records, not sub-hourly rainfall, flood footprints, forecasts, or impact outcomes.",
                "The station file contains all GHCN elements; PRCP is identified explicitly and no unflagged value is treated as independently confirmed.",
                "No explicit downstream reuse licence was located in the inspected product documentation; not integrated into application distribution pending terms review.",
            ],
        }
        staged.append((path, sidecar_path, payload, metadata))

    written: list[Path] = []
    try:
        for data_path, sidecar_path, payload, metadata in staged:
            temporary = data_path.with_name(data_path.name + ".partial")
            temporary.write_bytes(payload)
            data_path.parent.mkdir(parents=True, exist_ok=True)
            temporary.replace(data_path)
            written.append(data_path)
            sidecar_path.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            written.append(sidecar_path)
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return {
        "inventory": {"path": inventory_path.relative_to(ROOT).as_posix(), "sha256": _sha256(inventory_bytes)},
        "stations": {
            station_id: {
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": _sha256(payload),
                "station": stations[station_id],
                "validation": validation,
            }
            for station_id, (path, payload, _, validation) in fetched.items()
        },
    }


def main() -> None:
    print(json.dumps(acquire(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

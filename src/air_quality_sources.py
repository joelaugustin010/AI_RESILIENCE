"""Acquisition and validation for KSPCB's public year-labeled AQI summaries.

These are source-reported annual average index values, not pollutant
observations. They must not be treated as live or used to infer a daily AQI.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd


KSPCB_PAGE_URL = "https://kspcbipam.kerala.gov.in/Dashboard/airQuality"
KSPCB_ANNUAL_URL = "https://kspcbipam.kerala.gov.in/Dashboard/fetch_air_quality_data?year={year}"
AQI_SOURCE_COLUMNS = (
    "year",
    "source_station_code",
    "source_station",
    "monitoring_mode",
    "average_aqi",
    "reference_station",
)


class AirQualitySourceError(ValueError):
    """Raised when an official AQI summary cannot be validated safely."""


def _station_key(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^A-Z0-9]", "", value.strip().upper())


def prepare_kspcb_annual_aqi(
    payload: Mapping[str, object],
    year: int,
    station_inventory: Iterable[Mapping[str, str]],
) -> pd.DataFrame:
    """Validate and normalize source-reported annual AQI rows.

    Reference station labels are attached only for exact name matches after
    case, punctuation, and whitespace normalization. Similar names are left
    unmatched; this function never fuzzy-joins stations.
    """
    if not isinstance(payload, Mapping) or not isinstance(payload.get("station_data"), list):
        raise AirQualitySourceError("KSPCB payload must contain a station_data list.")
    reference: dict[tuple[str, str], str] = {}
    for item in station_inventory:
        name = item.get("station") if isinstance(item, Mapping) else None
        key = _station_key(name)
        if not key:
            raise AirQualitySourceError("Reference station names must be non-empty strings.")
        program = str(item.get("program", "")).strip().upper()
        if not program:
            raise AirQualitySourceError("Reference station program is required for station mapping.")
        reference_key = (key, program)
        if reference_key in reference and reference[reference_key] != name:
            raise AirQualitySourceError(f"Ambiguous reference station name: {name!r}.")
        reference[reference_key] = name

    rows = []
    seen = set()
    for position, item in enumerate(payload["station_data"]):
        if not isinstance(item, Mapping):
            raise AirQualitySourceError(f"Station row {position} is not an object.")
        name = item.get("station_name")
        mode = item.get("mode")
        code = item.get("stn_code")
        if not isinstance(name, str) or not name.strip():
            raise AirQualitySourceError(f"Station row {position} has no station name.")
        if not isinstance(mode, str) or not mode.strip():
            raise AirQualitySourceError(f"Station row {position} has no monitoring mode.")
        try:
            average_aqi = float(item.get("average_aqi"))
        except (TypeError, ValueError, OverflowError) as error:
            raise AirQualitySourceError(f"Station row {position} has an invalid average_aqi.") from error
        if not math.isfinite(average_aqi):
            raise AirQualitySourceError(f"Station row {position} average_aqi is not finite.")
        if not 0 <= average_aqi <= 500:
            raise AirQualitySourceError(f"Station row {position} AQI is outside 0-500.")
        identity = (int(year), _station_key(name), mode.strip().upper())
        if identity in seen:
            raise AirQualitySourceError(f"Duplicate station summary in {year}: {name!r}.")
        seen.add(identity)
        rows.append(
            {
                "year": int(year),
                "source_station_code": str(code or "").strip(),
                "source_station": name.strip(),
                "monitoring_mode": mode.strip(),
                "average_aqi": average_aqi,
                "reference_station": reference.get((_station_key(name), mode.strip().upper())),
            }
        )
    if not rows:
        raise AirQualitySourceError(f"KSPCB returned no station summaries for {year}.")
    return pd.DataFrame(rows, columns=AQI_SOURCE_COLUMNS)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_processed_summary(
    prepared: list[pd.DataFrame], raw_records: list[dict[str, object]], processed_directory: Path
) -> tuple[pd.DataFrame, Path]:
    combined = pd.concat(prepared, ignore_index=True).sort_values(
        ["year", "source_station"], kind="stable"
    ).reset_index(drop=True)
    processed_path = processed_directory / "kspcb_annual_aqi.csv"
    combined.to_csv(processed_path, index=False)
    processed_metadata = {
        "dataset": "KSPCB year-labeled Annual Average Air Quality Index summaries",
        "source_page": KSPCB_PAGE_URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_files": raw_records,
        "processed_file": processed_path.name,
        "processed_sha256": hashlib.sha256(processed_path.read_bytes()).hexdigest(),
        "rows": int(len(combined)),
        "years": sorted(int(value) for value in combined["year"].unique()),
        "statewide_source_rows": int(len(combined)),
        "exact_reference_station_matches": int(combined["reference_station"].notna().sum()),
        "unmatched_station_rows": int(combined["reference_station"].isna().sum()),
        "transformation": "Strict schema/range validation; normalized source names; exact punctuation/case/space station mapping with matching monitoring program only; no interpolation or estimate.",
        "period_limit": "Endpoint exposes year labels and average_aqi values, but no precise aggregation cutoff or observation timestamps.",
        "reuse_terms": "Dataset-specific reuse terms were not located; review before republication outside this attributed project display.",
        "not_pollutant_observations": True,
    }
    _write_json(processed_directory / "kspcb_annual_aqi.metadata.json", processed_metadata)
    return combined, processed_path


def acquire_kspcb_annual_aqi(
    years: Iterable[int],
    station_inventory: Iterable[Mapping[str, str]],
    raw_directory: Path,
    processed_directory: Path,
) -> tuple[pd.DataFrame, Path]:
    """Download official annual summaries, preserve raw bytes, validate, process.

    Raw downloads use a UTC timestamp in each filename and are never replaced.
    The processed table is derived from exactly those downloaded payloads.
    """
    raw_directory.mkdir(parents=True, exist_ok=True)
    processed_directory.mkdir(parents=True, exist_ok=True)
    station_inventory = list(station_inventory)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prepared = []
    raw_records = []
    for year in years:
        url = KSPCB_ANNUAL_URL.format(year=int(year))
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "AI_RESILIENCE air-quality data review", "Referer": KSPCB_PAGE_URL},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            raw_bytes = response.read()
            content_type = response.headers.get("Content-Type", "")
        raw_path = raw_directory / f"kspcb_annual_aqi_{int(year)}_{stamp}.json"
        with raw_path.open("xb") as raw_file:
            raw_file.write(raw_bytes)
        digest = hashlib.sha256(raw_bytes).hexdigest()
        try:
            payload = json.loads(raw_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise AirQualitySourceError(f"KSPCB returned invalid JSON for {year}; raw bytes preserved.") from error
        rows = prepare_kspcb_annual_aqi(payload, int(year), station_inventory)
        prepared.append(rows)
        retrieved_at = datetime.now(timezone.utc).isoformat()
        metadata = {
            "publisher": "Kerala State Pollution Control Board (KSPCB)",
            "source_page": KSPCB_PAGE_URL,
            "source_url": url,
            "retrieved_at_utc": retrieved_at,
            "year_label": int(year),
            "source_measure_label": "Annual Average Air Quality Index",
            "period_cutoff": "Not supplied by the endpoint; 2026 may be year-to-date.",
            "measurement_timestamp": "Not supplied; these are annual summary values, not timestamped observations.",
            "content_type": content_type,
            "raw_bytes": len(raw_bytes),
            "raw_sha256": digest,
            "validated_station_rows": int(len(rows)),
            "units": "AQI index (dimensionless)",
            "geographic_coverage": "KSPCB statewide station rows; includes but is not limited to Kochi/Ernakulam.",
            "reuse_terms": "Dataset-specific reuse terms were not located; KSPCB portal is copyrighted.",
            "limitations": [
                "No pollutant concentrations, averaging periods, observation timestamps, quality flags, or station coordinates in this payload.",
                "Station references are attached only on exact normalized station-name matches.",
                "Source rows are not live readings and do not support factory attribution.",
            ],
        }
        meta_path = raw_path.with_suffix(".metadata.json")
        _write_json(meta_path, metadata)
        raw_records.append({"path": raw_path.name, "metadata": meta_path.name, "sha256": digest, "year": int(year)})

    return _write_processed_summary(prepared, raw_records, processed_directory)


def rebuild_kspcb_annual_aqi_from_raw(
    raw_directory: Path,
    processed_directory: Path,
    station_inventory: Iterable[Mapping[str, str]],
) -> tuple[pd.DataFrame, Path]:
    """Recreate the processed table from the newest preserved raw file per year."""
    station_inventory = list(station_inventory)
    latest: dict[int, tuple[datetime, Path, dict[str, object]]] = {}
    for meta_path in raw_directory.glob("kspcb_annual_aqi_*.metadata.json"):
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        year = int(metadata["year_label"])
        retrieved = datetime.fromisoformat(str(metadata["retrieved_at_utc"]))
        raw_path = meta_path.with_name(meta_path.name.removesuffix(".metadata.json") + ".json")
        if not raw_path.is_file():
            raise AirQualitySourceError(f"Raw KSPCB file referenced by {meta_path.name} is missing.")
        if year not in latest or retrieved > latest[year][0]:
            latest[year] = (retrieved, raw_path, metadata)
    if not latest:
        raise AirQualitySourceError("No preserved KSPCB annual AQI downloads were found.")

    prepared = []
    raw_records = []
    for year in sorted(latest):
        _, raw_path, metadata = latest[year]
        raw_bytes = raw_path.read_bytes()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        if digest != metadata.get("raw_sha256"):
            raise AirQualitySourceError(f"Raw KSPCB file hash mismatch: {raw_path.name}.")
        payload = json.loads(raw_bytes.decode("utf-8"))
        prepared.append(prepare_kspcb_annual_aqi(payload, year, station_inventory))
        raw_records.append(
            {"path": raw_path.name, "metadata": raw_path.with_suffix(".metadata.json").name, "sha256": digest, "year": year}
        )
    processed_directory.mkdir(parents=True, exist_ok=True)
    return _write_processed_summary(prepared, raw_records, processed_directory)

"""Acquire only the pinned official air-quality source snapshots.

Downloads are verified against hashes already recorded in processed metadata.
This command never rebuilds or writes processed datasets.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.air_quality_sources import (
    KSPCB_ANNUAL_URL,
    KSPCB_PAGE_URL,
    prepare_kspcb_annual_aqi,
)


ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "AI_RESILIENCE pinned source acquisition/1.0"
ALLOWED_HOSTS = {
    "kspcbipam.kerala.gov.in",
    "kspcb.kerala.gov.in",
    "industry.kerala.gov.in",
}


class AcquisitionError(RuntimeError):
    """Raised when a source cannot be safely acquired or verified."""


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AcquisitionError(f"Cannot read acquisition metadata {path.relative_to(ROOT)}: {error}") from error
    if not isinstance(value, dict):
        raise AcquisitionError(f"Expected a JSON object in {path.relative_to(ROOT)}")
    return value


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _validate_url(url: str, expected_host: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != expected_host or expected_host not in ALLOWED_HOSTS:
        raise AcquisitionError(f"Refusing unexpected source URL: {url}")


def _fetch(url: str, expected_host: str) -> tuple[bytes, str, str]:
    _validate_url(url, expected_host)
    request = Request(url, headers={"User-Agent": USER_AGENT, "Referer": KSPCB_PAGE_URL})
    try:
        with urlopen(request, timeout=30) as response:
            content = response.read()
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            status = response.status
    except OSError as error:
        raise AcquisitionError(f"Could not download official source {url}: {error}") from error
    if status != 200:
        raise AcquisitionError(f"{url}: expected HTTP 200, received {status}")
    if urlparse(final_url).scheme != "https" or urlparse(final_url).hostname != expected_host:
        raise AcquisitionError(f"{url}: unexpected final URL {final_url}")
    return content, content_type, final_url


def _existing_file_matches(path: Path, expected_hash: str) -> bool:
    if not path.exists():
        return False
    actual_hash = _sha256(path.read_bytes())
    if actual_hash != expected_hash:
        raise AcquisitionError(
            f"Refusing to overwrite conflicting file {path.relative_to(ROOT)}: "
            f"expected SHA256 {expected_hash}, found {actual_hash}"
        )
    return True


def _check_sidecar(path: Path, expected_hash: str, source_url: str) -> bool:
    if not path.exists():
        return False
    metadata = _read_json(path)
    recorded_hash = metadata.get("raw_sha256", metadata.get("sha256"))
    if recorded_hash != expected_hash or metadata.get("source_url") != source_url:
        raise AcquisitionError(
            f"Refusing to overwrite conflicting provenance metadata {path.relative_to(ROOT)}"
        )
    return True


def _write_exclusive(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as output:
            output.write(content)
    except FileExistsError as error:
        raise AcquisitionError(f"Refusing to overwrite existing file {path.relative_to(ROOT)}") from error


def _stage_annual_sources(station_inventory: list[dict]) -> list[dict]:
    manifest_path = ROOT / "data/processed/air_quality/kspcb_annual_aqi.metadata.json"
    manifest = _read_json(manifest_path)
    records = []
    for item in manifest.get("raw_files", []):
        relative_path = Path("data/raw/air_quality") / item["path"]
        raw_path = ROOT / relative_path
        sidecar_path = raw_path.with_suffix(".metadata.json")
        expected_hash = str(item["sha256"]).lower()
        year = int(item["year"])
        url = KSPCB_ANNUAL_URL.format(year=year)
        host = urlparse(url).hostname
        if host is None:
            raise AcquisitionError(f"Invalid annual source URL: {url}")
        raw_exists = _existing_file_matches(raw_path, expected_hash)
        sidecar_exists = _check_sidecar(sidecar_path, expected_hash, url)

        content, content_type, final_url = _fetch(url, host)
        actual_hash = _sha256(content)
        if actual_hash != expected_hash:
            raise AcquisitionError(
                f"KSPCB annual AQI {year} changed: expected SHA256 {expected_hash}, "
                f"received {actual_hash}. Nothing from this response was saved; review the source before updating pins."
            )
        try:
            payload = json.loads(content.decode("utf-8"))
            rows = prepare_kspcb_annual_aqi(payload, year, station_inventory)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            raise AcquisitionError(f"KSPCB annual AQI {year} failed schema validation: {error}") from error

        metadata = {
            "publisher": "Kerala State Pollution Control Board (KSPCB)",
            "source_page": KSPCB_PAGE_URL,
            "source_url": url,
            "final_url": final_url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "year_label": year,
            "source_measure_label": "Annual Average Air Quality Index",
            "period_cutoff": "Not supplied by the endpoint; 2026 may be year-to-date.",
            "measurement_timestamp": "Not supplied; these are annual summary values, not timestamped observations.",
            "content_type": content_type,
            "raw_bytes": len(content),
            "raw_sha256": actual_hash,
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
        records.append(
            {
                "path": raw_path,
                "sidecar": sidecar_path,
                "content": content,
                "metadata": metadata,
                "raw_exists": raw_exists,
                "sidecar_exists": sidecar_exists,
                "sha256": actual_hash,
            }
        )
    if not records:
        raise AcquisitionError(f"No annual source entries found in {manifest_path.relative_to(ROOT)}")
    return records


def _stage_pdf_source(source: dict) -> dict:
    raw_path = ROOT / source["raw_file"]
    sidecar_path = raw_path.with_name(raw_path.name + ".metadata.json")
    expected_hash = str(source["raw_sha256"]).lower()
    source_url = source["source_url"]
    host = urlparse(source_url).hostname
    if host is None:
        raise AcquisitionError(f"Invalid PDF source URL: {source_url}")
    raw_exists = _existing_file_matches(raw_path, expected_hash)
    sidecar_exists = _check_sidecar(sidecar_path, expected_hash, source_url)

    content, content_type, final_url = _fetch(source_url, host)
    if not content.startswith(b"%PDF-"):
        raise AcquisitionError(f"Official source {source_url} did not return a PDF; nothing was saved.")
    actual_hash = _sha256(content)
    if actual_hash != expected_hash:
        raise AcquisitionError(
            f"Official PDF changed at {source_url}: expected SHA256 {expected_hash}, "
            f"received {actual_hash}. Nothing from this response was saved; review the source before updating pins."
        )

    metadata = {
        "publisher": source["publisher"],
        "source_url": source_url,
        "listing_url": source.get("listing_url"),
        "retrieved_on": datetime.now(timezone.utc).date().isoformat(),
        "final_url": final_url,
        "content_type": content_type,
        "sha256": actual_hash,
        "bytes": len(content),
        "licence": source.get("licence"),
        "validation": "The downloaded bytes match the SHA256 pinned in committed processed metadata and begin with the PDF signature.",
    }
    return {
        "path": raw_path,
        "sidecar": sidecar_path,
        "content": content,
        "metadata": metadata,
        "raw_exists": raw_exists,
        "sidecar_exists": sidecar_exists,
        "sha256": actual_hash,
    }


def acquire() -> list[dict]:
    station_inventory = _read_json(ROOT / "data/reference/air_quality_acquisition.json")[
        "kspcb_namp_ernakulam_stations"
    ]
    annual_records = _stage_annual_sources(station_inventory)
    air_metadata = _read_json(ROOT / "data/processed/air_quality/kspcb_caaqms_eloor_2026-09.metadata.json")
    air_sources = air_metadata["sources"]
    pdf_records = [
        _stage_pdf_source(air_sources["kspcb_caaqms_eloor_2026_09"]),
        _stage_pdf_source(air_sources["dic_edayar_allotment_2022"]),
    ]
    records = annual_records + pdf_records

    # All downloads have passed pinned hashes before any new source file is written.
    for record in records:
        if not record["raw_exists"]:
            _write_exclusive(record["path"], record["content"])
        if not record["sidecar_exists"]:
            encoded = (json.dumps(record["metadata"], indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            _write_exclusive(record["sidecar"], encoded)
    return records


def main() -> None:
    try:
        records = acquire()
    except (AcquisitionError, OSError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"Air-quality source acquisition stopped: {error}") from error
    for record in records:
        print(f"Verified {record['path'].relative_to(ROOT)} SHA256 {record['sha256']}")
    print("No processed datasets were written or rebuilt.")


if __name__ == "__main__":
    main()

"""Inspect the official KSDMA/GSI Ernakulam landslide ZIP without extracting it.

This is an acquisition/metadata audit only. It does not promote the archive to a
map layer, infer missing CRS/units, or authorize reuse.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_URL = "https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip"
DEFAULT_ARCHIVE = Path("data/raw/landslides/Ernakulam_GSI_2022.zip")
DEFAULT_REPORT = Path("reports/gsi_ernakulam_landslide_archive_inspection.json")


def _read_dbf_header(data: bytes) -> dict[str, Any]:
    if len(data) < 33:
        raise ValueError("DBF header is shorter than the minimum 33 bytes.")
    record_count = struct.unpack_from("<I", data, 4)[0]
    header_length = struct.unpack_from("<H", data, 8)[0]
    record_length = struct.unpack_from("<H", data, 10)[0]
    if header_length < 33 or header_length > len(data):
        raise ValueError("DBF field-descriptor header length is invalid or truncated.")
    fields = []
    offset = 32
    while offset < header_length and data[offset] != 0x0D:
        if offset + 32 > header_length:
            raise ValueError("DBF field descriptor is truncated.")
        descriptor = data[offset:offset + 32]
        name = descriptor[:11].split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
        fields.append({
            "name": name,
            "type": chr(descriptor[11]),
            "width": int(descriptor[16]),
            "decimals": int(descriptor[17]),
        })
        offset += 32
    return {
        "record_count": record_count,
        "header_length_bytes": header_length,
        "record_length_bytes": record_length,
        "fields": fields,
    }


def _read_shp_header(data: bytes) -> dict[str, Any]:
    if len(data) < 100:
        raise ValueError("SHP header is shorter than 100 bytes.")
    file_code = struct.unpack_from(">i", data, 0)[0]
    file_length_words = struct.unpack_from(">i", data, 24)[0]
    version, shape_type = struct.unpack_from("<ii", data, 28)
    bounds = struct.unpack_from("<4d", data, 36)
    if file_code != 9994:
        raise ValueError(f"Unexpected SHP file code {file_code}; expected 9994.")
    if version != 1000:
        raise ValueError(f"Unexpected SHP version {version}; expected 1000.")
    if file_length_words < 50:
        raise ValueError("SHP declared file length is shorter than its header.")
    return {
        "file_code": file_code,
        "version": version,
        "shape_type_code": shape_type,
        "declared_file_length_bytes": file_length_words * 2,
        "xy_bounds": list(bounds),
    }


def inspect_archive(archive_path: Path) -> dict[str, Any]:
    archive_path = Path(archive_path)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise ValueError(f"ZIP CRC check failed for {bad_member!r}.")
        names = [name for name in archive.namelist() if not name.endswith("/")]
        shapefiles = [name for name in names if PurePosixPath(name).suffix.casefold() == ".shp"]
        layers = []
        for shp_name in shapefiles:
            shp_path = PurePosixPath(shp_name)
            stem = str(shp_path.with_suffix("")).casefold()
            members_by_stem = {
                str(PurePosixPath(name).with_suffix("")).casefold(): name
                for name in names
            }
            sidecars = {}
            for suffix in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
                sidecars[suffix[1:]] = members_by_stem.get(stem + suffix)
            missing_required = [
                suffix for suffix in ("shp", "shx", "dbf", "prj")
                if not sidecars[suffix]
            ]
            layer: dict[str, Any] = {
                "shp_member": shp_name,
                "sidecars": sidecars,
                "missing_required_sidecars": missing_required,
                "complete_required_sidecars": not missing_required,
            }
            if sidecars["shp"]:
                with archive.open(sidecars["shp"]) as member:
                    layer["shp_header"] = _read_shp_header(member.read(100))
            if sidecars["dbf"]:
                with archive.open(sidecars["dbf"]) as member:
                    layer["dbf_header"] = _read_dbf_header(member.read(65536))
            if sidecars["prj"]:
                with archive.open(sidecars["prj"]) as member:
                    layer["prj_text"] = member.read(65536).decode("utf-8", errors="replace").strip()
                    layer["crs_declared"] = bool(layer["prj_text"])
            else:
                layer["crs_declared"] = False
            layers.append(layer)

    return {
        "dataset": "GSI 2022 Ernakulam landslide susceptibility shapefile",
        "source_url": SOURCE_URL,
        "retrieved_or_inspected_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "archive_path": str(archive_path),
        "archive_bytes": archive_path.stat().st_size,
        "sha256": digest,
        "zip_crc_check": "passed",
        "archive_member_count": len(names),
        "archive_members": names,
        "shapefile_layers": layers,
        "licence_status": "NOT_CONFIRMED",
        "ingestion_status": "INSPECTION_ONLY_PENDING_LICENCE_AND_EXPERT_QA",
        "ingestion_eligible": False,
        "safeguards": [
            "No archive member was extracted or modified.",
            "CRS is reported only from a supplied .prj sidecar; no CRS is guessed.",
            "DBF fields and SHP header bounds are metadata inspection, not geometry validation.",
            "Licence/reuse permission, scale suitability, topology, coverage and expert review remain required.",
            "District susceptibility must not be presented as a ward-level forecast or event probability.",
        ],
    }


def download_archive(destination: Path, *, force: bool = False) -> Path:
    destination = Path(destination)
    if destination.exists() and not force:
        raise FileExistsError(
            f"{destination} already exists; inspect it or pass --force to replace it."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "AI-RESILIENCE-research-data-audit/1.0"},
    )
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--download", action="store_true", help="Download from the official KSDMA URL first.")
    parser.add_argument("--force", action="store_true", help="Allow --download to replace an existing archive.")
    args = parser.parse_args()

    archive = download_archive(args.archive, force=args.force) if args.download else args.archive
    report = inspect_archive(archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "archive": str(archive),
        "report": str(args.output),
        "sha256": report["sha256"],
        "shapefile_layers": len(report["shapefile_layers"]),
        "ingestion_status": report["ingestion_status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

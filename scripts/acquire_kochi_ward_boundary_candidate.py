"""Acquire and structurally audit the OpenCity 2024 Kochi ward KML as an unapproved candidate.

This never replaces the map's configured boundary automatically. It records the
catalogue metadata, downloaded URL, SHA-256, KML structure, ward count, names,
coordinate ranges, and ring-closure checks for human/source comparison.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESOURCE_ID = "24a3de7a-4b14-436e-ae0c-e9ec7b1749e0"
RESOURCE_API = f"https://data.opencity.in/api/3/action/resource_show?id={RESOURCE_ID}"
DATASET_URL = "https://data.opencity.in/dataset/kochi-wards-map"
RESOURCE_PAGE = f"https://data.opencity.in/dataset/kochi-wards-map/resource/{RESOURCE_ID}"
OFFICIAL_PORTAL = "https://wardmap.ksmart.live/"
OFFICIAL_CORPORATION_PAGE = "https://kochicorporation.lsgkerala.gov.in/en/delimitation-commission-kerala-notification/590"
USER_AGENT = "AI_RESILIENCE educational research; preserve source attribution"
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "external" / "map_reference"


def fetch(url: str, timeout: int = 90) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,application/vnd.google-earth.kml+xml,application/xml,*/*"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(), response.geturl(), response.headers.get("Content-Type", "")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _coordinate_pairs(value: Any):
    """Yield finite-looking longitude/latitude pairs from nested GeoJSON coordinates."""
    if isinstance(value, list):
        if len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
            yield float(value[0]), float(value[1])
        else:
            for child in value:
                yield from _coordinate_pairs(child)


def compare_to_configured_boundary(candidate_bounds: list[float], boundary_path: Path) -> dict[str, Any]:
    """Compare extents only; never treat a bounding-box match as geometry validation."""
    boundary_path = Path(boundary_path)
    if not boundary_path.exists():
        return {"status": "NOT_RUN_CONFIGURED_BOUNDARY_FILE_MISSING"}
    try:
        boundary = json.loads(boundary_path.read_text(encoding="utf-8-sig"))
        geometry = boundary.get("geometry") if boundary.get("type") == "Feature" else None
        if geometry is None:
            return {"status": "NOT_RUN_UNSUPPORTED_BOUNDARY_GEOJSON_SHAPE"}
        pairs = list(_coordinate_pairs(geometry.get("coordinates", [])))
        if not pairs:
            return {"status": "NOT_RUN_NO_BOUNDARY_COORDINATES"}
        xs = [point[0] for point in pairs]
        ys = [point[1] for point in pairs]
        current = [min(xs), min(ys), max(xs), max(ys)]
        candidate = candidate_bounds
        keys = ("west", "south", "east", "north")
        deltas = [abs(candidate[i] - current[i]) for i in range(4)]
        mean_lat = (candidate[1] + candidate[3] + current[1] + current[3]) / 4
        import math
        metres = [
            deltas[0] * 111320 * math.cos(math.radians(mean_lat)),
            deltas[1] * 111320,
            deltas[2] * 111320 * math.cos(math.radians(mean_lat)),
            deltas[3] * 111320,
        ]
        return {
            "status": "BOUNDING_BOX_ONLY_REQUIRES_FULL_GEOMETRY_COMPARISON",
            "configured_boundary_file": boundary_path.name,
            "configured_boundary_sha256": hashlib.sha256(boundary_path.read_bytes()).hexdigest(),
            "configured_boundary_bounds_lonlat": current,
            "candidate_bounds_lonlat": candidate,
            "absolute_edge_deltas_degrees": dict(zip(keys, deltas)),
            "approximate_edge_deltas_metres": {key: round(value, 1) for key, value in zip(keys, metres)},
            "warning": "Bounding boxes do not establish polygon equality, legal currency, topology, or spatial coverage. Do not promote the candidate on this comparison alone.",
        }
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        return {"status": "BOUNDARY_COMPARISON_FAILED", "error": f"{type(error).__name__}: {error}"}


def audit_kml(data: bytes) -> dict[str, Any]:
    """Inspect KML structure without converting or repairing source coordinates."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as error:
        raise ValueError(f"Response is not well-formed XML/KML: {error}") from error
    if local_name(root.tag) != "kml":
        raise ValueError("Downloaded resource is XML but its root element is not KML.")

    placemarks = [element for element in root.iter() if local_name(element.tag) == "Placemark"]
    names: list[str] = []
    polygon_count = 0
    rings_checked = 0
    unclosed_rings = 0
    invalid_coordinate_tuples = 0
    out_of_range_coordinates = 0
    all_lons: list[float] = []
    all_lats: list[float] = []

    for placemark in placemarks:
        # ArcGIS-exported KML commonly stores ward names in ExtendedData /
        # SimpleData rather than a Placemark <name> element.
        name = ""
        for child in placemark.iter():
            if local_name(child.tag) == "SimpleData" and child.attrib.get("name", "").casefold() in {
                "ward_lgd_name", "ward_name", "wardname", "sourcewardname", "name"
            } and child.text and child.text.strip():
                name = child.text.strip()
                break
        if not name:
            name = next((child.text.strip() for child in placemark.iter()
                         if local_name(child.tag) == "name" and child.text and child.text.strip()), "")
        if name:
            names.append(name)
        for polygon in (child for child in placemark.iter() if local_name(child.tag) == "Polygon"):
            polygon_count += 1
            for coord_node in (child for child in polygon.iter() if local_name(child.tag) == "coordinates"):
                tuples: list[tuple[float, float]] = []
                for token in (coord_node.text or "").split():
                    parts = token.split(",")
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                        if not (lon == lon and lat == lat and abs(lon) != float("inf") and abs(lat) != float("inf")):
                            raise ValueError("non-finite")
                    except (ValueError, IndexError):
                        invalid_coordinate_tuples += 1
                        continue
                    tuples.append((lon, lat))
                    all_lons.append(lon)
                    all_lats.append(lat)
                    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                        out_of_range_coordinates += 1
                if tuples:
                    rings_checked += 1
                    if len(tuples) < 4 or tuples[0] != tuples[-1]:
                        unclosed_rings += 1

    if not placemarks:
        raise ValueError("KML contains no Placemark features.")
    if polygon_count == 0:
        raise ValueError("KML contains no Polygon geometries.")
    if not all_lons or invalid_coordinate_tuples or out_of_range_coordinates:
        raise ValueError("KML contains no usable coordinates, malformed coordinate tuples, or out-of-range coordinates.")

    unique_names = sorted(set(names), key=str.casefold)
    return {
        "kml_root": local_name(root.tag),
        "placemark_count": len(placemarks),
        "named_placemark_count": len(names),
        "unique_placemark_name_count": len(set(names)),
        "polygon_count": polygon_count,
        "coordinate_rings_checked": rings_checked,
        "unclosed_ring_count": unclosed_rings,
        "invalid_coordinate_tuple_count": invalid_coordinate_tuples,
        "out_of_range_coordinate_count": out_of_range_coordinates,
        "coordinate_bounds_lonlat": [min(all_lons), min(all_lats), max(all_lons), max(all_lats)],
        "placemark_names": names,
        "unique_placemark_names": unique_names,
        "expected_74_ward_count_matches": len(placemarks) == 74 and len(set(names)) == 74,
        "structural_status": "STRUCTURE_CHECKED_CANDIDATE_ONLY",
        "limitations": [
            "OpenCity catalogue metadata describes this as a 74-ward 2024 map and labels reuse as public domain; this does not prove alignment with the final legal notification.",
            "KML coordinates are longitude/latitude; no legal boundary or independent positional-accuracy validation is implied.",
            "Ring closure and coordinate ranges are structural checks, not a complete topology validation.",
            "Do not promote this candidate to the production map boundary without comparison to the final official notification and the configured boundary.",
        ],
    }


def acquire(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "dataset_id": "opencity_kochi_wards_2024_candidate",
        "title": "Kochi Wards Map 2024",
        "publisher": "OpenCity.in; catalogue credits source as Esri India Living Atlas",
        "dataset_url": DATASET_URL,
        "resource_page": RESOURCE_PAGE,
        "resource_api": RESOURCE_API,
        "official_comparison_sources": [OFFICIAL_PORTAL, OFFICIAL_CORPORATION_PAGE],
        "catalogue_reported_format": "KML",
        "catalogue_reported_ward_count": 74,
        "catalogue_reported_license": "Other (Public Domain) — catalogue label; independent rights verification not performed",
        "catalogue_reported_source": "livingatlas.esri.in",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACQUISITION_FAILED",
        "validation_status": "NOT_VALIDATED",
    }
    manifest_path = output / "kochi_wards_2024_candidate.metadata.json"
    atomic_write(manifest_path, json.dumps(record, indent=2, ensure_ascii=False).encode("utf-8"))
    try:
        api_bytes, api_final_url, api_content_type = fetch(RESOURCE_API)
        api_payload = json.loads(api_bytes.decode("utf-8-sig"))
        if api_payload.get("success") is not True or not isinstance(api_payload.get("result"), dict):
            raise ValueError("OpenCity resource metadata API did not return success=true with a result object.")
        resource = api_payload["result"]
        download_url = str(resource.get("url") or "").strip()
        if not download_url.startswith(("https://", "http://")):
            raise ValueError("OpenCity resource metadata does not contain an HTTP(S) download URL.")
        data, final_url, content_type = fetch(download_url)
        if not data:
            raise ValueError("OpenCity KML resource download was empty.")
        audit = audit_kml(data)
        audit["comparison_to_configured_boundary"] = compare_to_configured_boundary(
            audit["coordinate_bounds_lonlat"],
            ROOT / "data" / "reference" / "kochi_corporation_boundary.geojson",
        )
        raw_path = output / "kochi_wards_2024_candidate.kml"
        atomic_write(raw_path, data)
        record.update({
            "metadata_api_final_url": api_final_url,
            "metadata_api_content_type": api_content_type,
            "download_url": download_url,
            "final_url": final_url,
            "content_type": content_type,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "raw_file": raw_path.name,
            "resource_metadata": {
                key: resource.get(key) for key in (
                    "name", "format", "mimetype", "license_title", "license_id",
                    "last_modified", "created", "size", "source", "state", "package_id"
                ) if key in resource
            },
            "audit": audit,
            "status": "DOWNLOADED_RAW_CANDIDATE",
            "validation_status": audit["structural_status"],
            "overall_approval": "NOT_APPROVED_FOR_PRODUCTION_BOUNDARY_OR_EXPOSURE_ANALYSIS",
        })
    except Exception as error:
        record["error"] = f"{type(error).__name__}: {error}"
        record["status"] = "ACQUISITION_FAILED"
        record["validation_status"] = "BLOCKED"
    record["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    atomic_write(manifest_path, json.dumps(record, indent=2, ensure_ascii=False).encode("utf-8"))
    if record["status"] != "DOWNLOADED_RAW_CANDIDATE":
        raise RuntimeError(f"Kochi ward boundary candidate acquisition failed: {record.get('error')}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = acquire(args.output_dir)
    audit = result["audit"]
    print(f"{result['raw_file']}: {result['validation_status']} ({result['size_bytes']} bytes)")
    print(f"Placemarks={audit['placemark_count']}; polygons={audit['polygon_count']}; unique names={audit['unique_placemark_name_count']}")
    print(f"Bounds (lon/lat): {audit['coordinate_bounds_lonlat']}")
    print("Candidate only: final-notification comparison and topology review are still required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

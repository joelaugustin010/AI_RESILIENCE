"""Prepare review-only major-road and bridge context from a preserved OSM snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.spatial_data import SpatialDataError, validate_geojson


SOURCE = (
    ROOT
    / "data"
    / "raw"
    / "experimental"
    / "openstreetmap_roads_provisional_kochi_bounds.json"
)
SOURCE_METADATA = SOURCE.with_name(SOURCE.name + ".metadata.json")
OUTPUT_ROOT = ROOT / "data" / "processed" / "spatial_layers"
MAJOR_ROADS = {
    "motorway",
    "motorway_link",
    "trunk",
    "trunk_link",
    "primary",
    "primary_link",
    "secondary",
    "secondary_link",
    "tertiary",
    "tertiary_link",
}
OUTPUTS = {
    "major_roads": "openstreetmap_major_roads_kochi_context",
    "bridges": "openstreetmap_bridges_kochi_context",
}


class OSMPreparationError(ValueError):
    """Raised when the source snapshot cannot safely be converted to context layers."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _feature(element: dict[str, Any]) -> dict[str, Any]:
    geometry = element.get("geometry")
    if not isinstance(geometry, list) or len(geometry) < 2:
        raise OSMPreparationError(f"OSM way {element.get('id')} has fewer than two geometry positions.")
    coordinates = []
    for position in geometry:
        latitude, longitude = position.get("lat"), position.get("lon")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            raise OSMPreparationError(f"OSM way {element.get('id')} has a nonnumeric coordinate.")
        coordinates.append([float(longitude), float(latitude)])
    return {
        "type": "Feature",
        "id": f"way/{element['id']}",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": dict(element.get("tags") or {}),
    }


def _metadata(
    *,
    dataset_id: str,
    title: str,
    source_metadata: dict[str, Any],
    source_sha256: str,
    source_bytes: int,
    validation: dict[str, Any],
    feature_count: int,
    source_feature_count: int,
    filter_description: str,
) -> dict[str, Any]:
    bounds = source_metadata["query_bounds"]
    return {
        "dataset_id": dataset_id,
        "title": title,
        "source_url": source_metadata["source_url"],
        "publisher": "OpenStreetMap contributors",
        "retrieved_on": source_metadata["retrieved_at_utc"][:10],
        "publication_date": source_metadata["osm_base_timestamp"][:10],
        "license": (
            "Open Database License (ODbL) 1.0; © OpenStreetMap contributors. "
            "Attribution required; database adaptations are subject to ODbL share-alike terms."
        ),
        "crs": "EPSG:4326",
        "units": "Line geometries and OpenStreetMap tags; tag values are not uniformly measured quantities",
        "geographic_coverage": (
            f"Query rectangle only: {bounds['west']}–{bounds['east']} E, "
            f"{bounds['south']}–{bounds['north']} N. This is not a validated or complete "
            "Kochi Corporation boundary."
        ),
        "limitations": [
            "Community mapping is not an authoritative inventory; completeness, positional accuracy, access, condition, and operational status are not independently validated.",
            "The query rectangle was derived from the observed extent of a provisional ward snapshot and is not a legal or complete city boundary.",
            "Only tagged OSM highway ways meeting the recorded filter are included; mapped bridges are road ways tagged with bridge=* and may not be a complete bridge register.",
            "These layers provide map context only. They are not used to calculate route availability, hazard exposure, damage, service disruption, or consequences.",
            "ODbL attribution and share-alike obligations apply to these derived databases.",
        ],
        "source_snapshot_file": SOURCE.relative_to(ROOT).as_posix(),
        "source_snapshot_sha256": source_sha256,
        "source_snapshot_bytes": source_bytes,
        "source_coordinate_order": "Source OSM point geometry uses lat/lon; converted to GeoJSON [longitude, latitude] order.",
        "source_snapshot_base_timestamp": source_metadata["osm_base_timestamp"],
        "source_feature_count": source_feature_count,
        "processed_feature_count": feature_count,
        "processing_filter": filter_description,
        "layer_role": "context",
        "analysis_status": "Integrated as OpenStreetMap community-mapped context only; not an authoritative inventory or exposure input.",
        "attribution": "© OpenStreetMap contributors",
        "validation": validation,
    }


def prepare_layers(root: Path = ROOT, *, replace: bool = False) -> dict[str, Any]:
    """Create validated major-road and bridge GeoJSON layers without overwriting."""
    root = Path(root)
    source = root / SOURCE.relative_to(ROOT)
    source_sidecar = root / SOURCE_METADATA.relative_to(ROOT)
    if not source.is_file() or not source_sidecar.is_file():
        raise FileNotFoundError(f"OSM source snapshot or metadata is missing: {source}")
    raw_bytes = source.read_bytes()
    source_hash = _sha256(raw_bytes)
    source_metadata = json.loads(source_sidecar.read_text(encoding="utf-8"))
    if source_metadata.get("sha256") != source_hash:
        raise OSMPreparationError("OSM source checksum does not match its provenance sidecar.")
    if "odbl" not in str(source_metadata.get("license", "")).casefold():
        raise OSMPreparationError("OSM source sidecar does not record ODbL reuse terms.")
    if source_metadata.get("crs") != "WGS 84 latitude/longitude per OSM API convention":
        raise OSMPreparationError("OSM source coordinate convention is not the reviewed WGS 84 convention.")

    document = json.loads(raw_bytes)
    elements = document.get("elements")
    if not isinstance(elements, list) or not elements:
        raise OSMPreparationError("OSM source must contain a non-empty elements array.")
    ids = set()
    major_roads = []
    bridges = []
    highway_counts: Counter[str] = Counter()
    for element in elements:
        if element.get("type") != "way" or not isinstance(element.get("id"), int):
            raise OSMPreparationError("Expected OSM way elements with integer IDs.")
        if element["id"] in ids:
            raise OSMPreparationError(f"Duplicate OSM way ID {element['id']}.")
        ids.add(element["id"])
        tags = element.get("tags") or {}
        highway = tags.get("highway")
        if highway:
            highway_counts[highway] += 1
        if highway in MAJOR_ROADS:
            major_roads.append(_feature(element))
        if highway and tags.get("bridge", "").casefold() not in {"", "no", "false", "0"}:
            bridges.append(_feature(element))

    if not major_roads or not bridges:
        raise OSMPreparationError(
            f"Expected major road and mapped bridge features; got {len(major_roads)} and {len(bridges)}."
        )
    layer_dir = root / OUTPUT_ROOT.relative_to(ROOT)
    layer_dir.mkdir(parents=True, exist_ok=True)
    outputs = {}
    for key, features, title, filter_description in (
        (
            "major_roads",
            major_roads,
            "OpenStreetMap major road ways in the Kochi review rectangle (context only)",
            "OSM highway ways with highway in: " + ", ".join(sorted(MAJOR_ROADS)),
        ),
        (
            "bridges",
            bridges,
            "OpenStreetMap road ways tagged as bridges in the Kochi review rectangle (context only)",
            "OSM highway ways with a non-empty bridge tag other than no/false/0",
        ),
    ):
        dataset_id = OUTPUTS[key]
        destination = layer_dir / f"{dataset_id}.geojson"
        metadata_path = layer_dir / f"{dataset_id}.metadata.json"
        if (destination.exists() or metadata_path.exists()) and not replace:
            raise FileExistsError(f"Refusing to overwrite an existing processed layer: {destination}")
        geojson = {"type": "FeatureCollection", "features": features}
        metadata = _metadata(
            dataset_id=dataset_id,
            title=title,
            source_metadata=source_metadata,
            source_sha256=source_hash,
            source_bytes=len(raw_bytes),
            validation={},
            feature_count=len(features),
            source_feature_count=len(elements),
            filter_description=filter_description,
        )
        temporary = destination.with_name(destination.stem + ".partial.geojson")
        temporary.write_text(
            json.dumps(geojson, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        report = validate_geojson(temporary, metadata)
        if report["errors"]:
            temporary.unlink(missing_ok=True)
            raise SpatialDataError("Converted OSM layer failed QA: " + " ".join(report["errors"]))
        report["source_file"] = destination.relative_to(root).as_posix()
        metadata["validation"] = report
        outputs[key] = (temporary, destination, metadata_path, metadata, report)

    try:
        for temporary, destination, metadata_path, metadata, report in outputs.values():
            temporary.replace(destination)
            metadata_path.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    except Exception:
        for temporary, destination, metadata_path, _, _ in outputs.values():
            temporary.unlink(missing_ok=True)
        raise

    return {
        key: {
            "dataset_id": metadata["dataset_id"],
            "processed_file": destination.relative_to(root).as_posix(),
            "feature_count": metadata["processed_feature_count"],
            "source_feature_count": metadata["source_feature_count"],
            "source_sha256": source_hash,
            "processed_sha256": _sha256(destination.read_bytes()),
            "validation": report,
        }
        for key, (_, destination, _, metadata, report) in outputs.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace only the two processed layers generated by this script; raw source snapshots are never modified.",
    )
    args = parser.parse_args()
    print(json.dumps(prepare_layers(args.root, replace=args.replace), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

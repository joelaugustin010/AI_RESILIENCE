"""Rebuild Kochi major-road and bridge context from a verified OSM road snapshot.

This avoids relying on the untracked November raw acquisition file. The source
snapshot is the committed, hash-verified 2026-10-28 OSM road layer. Outputs are
context-only and never used for exposure or route-availability analysis.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.spatial_data import SpatialDataError, read_geojson, validate_geojson

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/spatial_layers/osm_kochi_roads_20261028T192808Z.geojson"
SOURCE_METADATA = SOURCE.with_name(SOURCE.stem + ".metadata.json")
OUTPUT_ROOT = ROOT / "data/processed/spatial_layers"

MAJOR_ROAD_CLASSES = {
    "motorway", "motorway_link", "trunk", "trunk_link",
    "primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link",
}
OUTPUTS = {
    "major_roads": ("openstreetmap_major_roads_kochi_context", "osm_kochi_major_roads_context"),
    "bridges": ("openstreetmap_bridges_kochi_context", "osm_kochi_bridges_context"),
}


class RebuildError(ValueError):
    """Raised when the source OSM layer cannot support a reproducible rebuild."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _build_metadata(
    source_metadata: dict[str, Any],
    *,
    dataset_id: str,
    logical_layer_id: str,
    title: str,
    filter_description: str,
    feature_count: int,
    source_count: int,
    source_hash: str,
) -> dict[str, Any]:
    limitations = list(source_metadata.get("limitations") or [])
    limitations.extend([
        "This is a deterministic subset of a separately validated OSM road snapshot; it is not a complete or authoritative road/bridge inventory.",
        "The subset is for map context only and is not used for exposure, route availability, road condition, damage, service disruption, or emergency response calculations.",
        "The provisional Kochi boundary extent defines the upstream query rectangle only; no clipping to a legal or validated municipal boundary was performed.",
        "OpenStreetMap ODbL attribution and share-alike obligations apply.",
    ])
    return {
        "dataset_id": dataset_id,
        "logical_layer_id": logical_layer_id,
        "title": title,
        "source_url": source_metadata["source_url"],
        "publisher": source_metadata["publisher"],
        "retrieved_on": source_metadata["retrieved_on"],
        "publication_date": source_metadata["publication_date"],
        "license": source_metadata["license"],
        "crs": source_metadata["crs"],
        "units": source_metadata["units"],
        "geographic_coverage": source_metadata["geographic_coverage"],
        "limitations": limitations,
        "layer_role": "context",
        "validation_status": "PROVISIONAL",
        "analysis_status": "Context display only; not used for exposure, safety, source-attribution, or emergency-access conclusions.",
        "attribution": source_metadata.get("attribution", "© OpenStreetMap contributors"),
        "copyright_url": source_metadata.get("copyright_url", "https://www.openstreetmap.org/copyright"),
        "license_url": source_metadata.get("license_url", "https://opendatacommons.org/licenses/odbl/1-0/"),
        "source_snapshot_file": SOURCE.relative_to(ROOT).as_posix(),
        "source_snapshot_sha256": source_hash,
        "upstream_raw_snapshot_sha256": source_metadata.get("source_snapshot_sha256"),
        "source_database_timestamp": source_metadata.get("source_database_timestamp"),
        "source_feature_count": source_count,
        "processed_feature_count": feature_count,
        "processing_filter": filter_description,
        "required_properties": list(source_metadata.get("required_properties") or []),
    }


def rebuild(root: Path = ROOT, *, replace: bool = False) -> dict[str, Any]:
    root = Path(root)
    source = root / SOURCE.relative_to(ROOT)
    sidecar_path = root / SOURCE_METADATA.relative_to(ROOT)
    if not source.is_file() or not sidecar_path.is_file():
        raise FileNotFoundError(f"Verified OSM source or sidecar is missing: {source}")

    raw_bytes = source.read_bytes()
    source_hash = _sha256(raw_bytes)
    source_metadata = json.loads(sidecar_path.read_text(encoding="utf-8"))
    source_report = validate_geojson(
        source,
        source_metadata,
        required_properties=source_metadata.get("required_properties"),
    )
    expected_hash = (source_metadata.get("validation") or {}).get("source_sha256")
    if not expected_hash or expected_hash != source_hash:
        raise RebuildError("Committed OSM source content hash does not match its provenance sidecar.")
    if source_report["errors"] or not source_report["provenance_valid"]:
        raise RebuildError("Committed OSM source failed provenance/geometry QA: " + " ".join(source_report["errors"]))
    if "odbl" not in str(source_metadata.get("license", "")).casefold():
        raise RebuildError("Source metadata does not establish ODbL reuse terms.")
    if source_metadata.get("crs") != "EPSG:4326":
        raise RebuildError("Source coordinate reference is not EPSG:4326.")

    document, source_features = read_geojson(source)
    if document.get("type") != "FeatureCollection" or not source_features:
        raise RebuildError("The verified OSM road source is not a non-empty FeatureCollection.")

    major_roads = []
    bridges = []
    for feature in source_features:
        properties = feature.get("properties") or {}
        highway = str(properties.get("highway") or "").strip().casefold()
        bridge = str(properties.get("bridge") or "").strip().casefold()
        if highway in MAJOR_ROAD_CLASSES:
            major_roads.append(feature)
        if highway and bridge not in {"", "no", "false", "0"}:
            bridges.append(feature)

    if not major_roads:
        raise RebuildError("The verified OSM source contains no features in the reviewed major-road classes.")
    if not bridges:
        raise RebuildError("The verified OSM source contains no highway ways with a non-empty bridge tag.")

    output_root = root / OUTPUT_ROOT.relative_to(ROOT)
    output_root.mkdir(parents=True, exist_ok=True)
    prepared: dict[str, tuple[Path, Path, Path, dict[str, Any], dict[str, Any]]] = {}

    for key, features, title, description in (
        (
            "major_roads",
            major_roads,
            "OpenStreetMap major road ways in the Kochi review rectangle (context only)",
            "Deterministic subset of the verified 2026-10-28 OSM road snapshot; highway in: "
            + ", ".join(sorted(MAJOR_ROAD_CLASSES)),
        ),
        (
            "bridges",
            bridges,
            "OpenStreetMap road ways tagged as bridges in the Kochi review rectangle (context only)",
            "Deterministic subset of the verified 2026-10-28 OSM road snapshot; highway is populated and bridge tag is not empty/no/false/0",
        ),
    ):
        dataset_id, logical_id = OUTPUTS[key]
        destination = output_root / f"{dataset_id}.geojson"
        metadata_path = output_root / f"{dataset_id}.metadata.json"
        if (destination.exists() or metadata_path.exists()) and not replace:
            raise FileExistsError(f"Refusing to overwrite existing output: {destination}")

        temporary = output_root / f".{dataset_id}.rebuild.geojson"
        temporary_metadata = output_root / f".{dataset_id}.rebuild.metadata.json"
        geojson = {"type": "FeatureCollection", "features": features}
        temporary.write_text(
            json.dumps(geojson, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        metadata = _build_metadata(
            source_metadata,
            dataset_id=dataset_id,
            logical_layer_id=logical_id,
            title=title,
            filter_description=description,
            feature_count=len(features),
            source_count=len(source_features),
            source_hash=source_hash,
        )
        report = validate_geojson(
            temporary,
            metadata,
            required_properties=metadata.get("required_properties"),
        )
        if report["errors"] or not report["provenance_valid"]:
            temporary.unlink(missing_ok=True)
            raise SpatialDataError("Rebuilt OSM context failed QA: " + " ".join(report["errors"]))
        report["source_file"] = destination.relative_to(root).as_posix()
        metadata["validation"] = report
        metadata["processed_sha256"] = report["source_sha256"]
        prepared[key] = (temporary, destination, metadata_path, metadata, report)

    # Only replace the two derived outputs after both candidates pass QA.
    for temporary, destination, metadata_path, metadata, _ in prepared.values():
        temporary.replace(destination)
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    return {
        key: {
            "dataset_id": metadata["dataset_id"],
            "feature_count": metadata["processed_feature_count"],
            "source_snapshot_sha256": metadata["source_snapshot_sha256"],
            "processed_sha256": metadata["processed_sha256"],
            "validation_errors": metadata["validation"]["errors"],
            "validation_warnings": metadata["validation"]["warnings"],
        }
        for key, (_, _, _, metadata, _) in prepared.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    print(json.dumps(rebuild(args.root, replace=args.replace), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

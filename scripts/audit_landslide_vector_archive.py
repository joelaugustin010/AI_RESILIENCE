"""Audit GSI landslide-susceptibility shapefile metadata and geometry without repairing source data."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import shapefile
from pyproj import CRS, Transformer
from shapely.geometry import box, shape
from shapely.ops import transform as transform_geometry
from shapely.validation import explain_validity


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "data" / "external" / "map_reference" / "gsi_landslide_susceptibility_ernakulam.zip"
DEFAULT_OUTPUT = ROOT / "data" / "external" / "map_reference" / "landslide_vector_audit.json"
KOCHI_SCREENING_BBOX = (76.1, 9.7, 76.6, 10.1)


def inspect_archive(archive_path: Path) -> dict:
    """Return structural/geometry diagnostics; never fixes or promotes source geometries."""
    if not archive_path.is_file() or not zipfile.is_zipfile(archive_path):
        raise RuntimeError(f"Missing or invalid landslide vector ZIP: {archive_path}")
    archive_bytes = archive_path.read_bytes()
    archive_sha = hashlib.sha256(archive_bytes).hexdigest()
    layers = []
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"Landslide ZIP CRC check failed at member: {bad_member}")
        names = [name for name in archive.namelist() if not name.endswith("/")]
        name_lookup = {name.lower(): name for name in names}
        shp_names = [name for name in names if name.lower().endswith(".shp")]
        if not shp_names:
            raise RuntimeError("Landslide ZIP contains no shapefile")
        for shp_name in shp_names:
            stem = shp_name[:-4]
            sidecars = {
                suffix: name_lookup.get((stem + suffix).lower())
                for suffix in (".shx", ".dbf", ".prj", ".cpg")
            }
            if not sidecars[".shx"] or not sidecars[".dbf"]:
                raise RuntimeError(f"Shapefile {shp_name} is missing required .shx/.dbf sidecars")
            reader = shapefile.Reader(
                shp=io.BytesIO(archive.read(shp_name)),
                shx=io.BytesIO(archive.read(sidecars[".shx"])),
                dbf=io.BytesIO(archive.read(sidecars[".dbf"])),
            )
            try:
                fields = [field[0] for field in reader.fields[1:]]
                geometry_counts: dict[str, int] = {}
                invalid_features = []
                empty_count = 0
                feature_bounds = []
                geometries = []
                class_fields = [
                    field for field in fields
                    if any(term in field.casefold() for term in ("class", "suscept", "hazard", "zone", "landslide", "rank"))
                ]
                class_values = {field: [] for field in class_fields}
                for index, item in enumerate(reader.iterShapeRecords()):
                    geom = shape(item.shape.__geo_interface__)
                    geometries.append(geom)
                    geometry_counts[geom.geom_type] = geometry_counts.get(geom.geom_type, 0) + 1
                    if geom.is_empty:
                        empty_count += 1
                    else:
                        feature_bounds.append(geom.bounds)
                    properties = dict(zip(fields, item.record))
                    for field in class_fields:
                        value = properties.get(field)
                        if value not in (None, "") and value not in class_values[field] and len(class_values[field]) < 30:
                            class_values[field].append(value)
                    if not geom.is_valid:
                        invalid_features.append({
                            "record_index_0_based": index,
                            "reason": explain_validity(geom),
                            "class_values": {field: properties.get(field) for field in class_fields},
                        })

                crs_text = archive.read(sidecars[".prj"]).decode("utf-8", "replace").strip() if sidecars[".prj"] else ""
                crs = None
                crs_error = None
                if crs_text:
                    try:
                        crs = CRS.from_wkt(crs_text)
                    except Exception as exc:
                        crs_error = f"{type(exc).__name__}: {exc}"

                source_bounds = None
                bounds_epsg4326 = None
                screening_bbox_overlap = None
                if feature_bounds:
                    source_bounds = [
                        min(b[0] for b in feature_bounds),
                        min(b[1] for b in feature_bounds),
                        max(b[2] for b in feature_bounds),
                        max(b[3] for b in feature_bounds),
                    ]
                if feature_bounds and crs is not None:
                    transformed_bounds = []
                    for geom in geometries:
                        if geom.is_empty:
                            continue
                        if crs.to_epsg() != 4326:
                            transformer = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)
                            geom = transform_geometry(transformer.transform, geom)
                        transformed_bounds.append(geom.bounds)
                    if transformed_bounds:
                        bounds_epsg4326 = [
                            min(b[0] for b in transformed_bounds),
                            min(b[1] for b in transformed_bounds),
                            max(b[2] for b in transformed_bounds),
                            max(b[3] for b in transformed_bounds),
                        ]
                        # This is a bounding-box overlap only, not polygon intersection or exposure.
                        screening_bbox_overlap = box(*bounds_epsg4326).intersects(box(*KOCHI_SCREENING_BBOX))

                layers.append({
                    "shapefile": shp_name,
                    "sidecars": sidecars,
                    "feature_count": len(reader),
                    "shape_type": reader.shapeTypeName,
                    "geometry_type_counts": geometry_counts,
                    "field_names": fields,
                    "candidate_class_fields": class_fields,
                    "candidate_class_field_values": class_values,
                    "crs_wkt_present": bool(crs_text),
                    "crs": crs.to_string() if crs else None,
                    "crs_epsg": crs.to_epsg() if crs else None,
                    "crs_parse_error": crs_error,
                    "bounds_in_source_crs": source_bounds,
                    "bounds_epsg4326": bounds_epsg4326,
                    "kochi_screening_bbox_overlap": screening_bbox_overlap,
                    "invalid_geometry_count": len(invalid_features),
                    "invalid_features": invalid_features,
                    "empty_geometry_count": empty_count,
                    "status": "METADATA_READ_NOT_SCIENTIFICALLY_VALIDATED",
                })
            finally:
                reader.close()
    return {
        "audit_version": 1,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": archive_sha,
        "archive_bytes": len(archive_bytes),
        "archive_crc_check": "PASS",
        "layer_count": len(layers),
        "layers": layers,
        "kochi_screening_bbox_epsg4326": list(KOCHI_SCREENING_BBOX),
        "status": "METADATA_READ_NOT_APPROVED_FOR_LANDSLIDE_PREDICTION",
        "limitations": [
            "CRS, fields and geometry validity are diagnostics, not proof that susceptibility classes are scientifically meaningful or current.",
            "The Kochi rectangle is a rough screening bounding box, not the official municipal boundary; overlap does not establish city exposure.",
            "Invalid source geometries are reported but never repaired, dissolved or used for spatial joins.",
            "Susceptibility zoning is not a time-specific landslide prediction or a quantified consequence estimate.",
            "Dataset-specific reuse terms, source scale and class legend must be confirmed with the publisher.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = inspect_archive(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for layer in report["layers"]:
        print(
            f"{layer['shapefile']}: {layer['status']} features={layer['feature_count']} "
            f"CRS={layer['crs']} invalid={layer['invalid_geometry_count']} "
            f"Kochi-bbox-overlap={layer['kochi_screening_bbox_overlap']}"
        )
    print("The layer is not approved for landslide prediction or ward/facility exposure analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

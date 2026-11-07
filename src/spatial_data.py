"""Auditable GeoJSON validation, ingestion, and spatial exposure helpers.

This module intentionally supports GeoJSON in WGS 84 only. It performs
topological checks in longitude/latitude coordinates and does not calculate
distance, area, hazard depth, or risk. Its lightweight checks are not a complete
replacement for GEOS/QGIS validity checks on complex production geometries.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
from datetime import date
from pathlib import Path
from typing import Any, Iterable


PROVENANCE_FIELDS = (
    "dataset_id",
    "title",
    "source_url",
    "publisher",
    "retrieved_on",
    "publication_date",
    "license",
    "crs",
    "units",
    "geographic_coverage",
    "limitations",
)
SUPPORTED_GEOMETRIES = {
    "Point", "MultiPoint", "LineString", "MultiLineString", "Polygon",
    "MultiPolygon", "GeometryCollection",
}


class SpatialDataError(ValueError):
    """Raised when a source cannot safely be validated or ingested."""


def review_coordinate_csv(
    source_path: Path,
    processed_path: Path,
    metadata_path: Path,
    metadata: dict[str, Any],
    state_value: str,
    district_value: str,
    required_columns: tuple[str, ...] = ("State", "District", "Location_Coordinates"),
    retain_columns: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Preserve a CSV subset and report coordinate syntax without assigning CRS/order.

    This is deliberately a review output, not a spatial layer. No geometry is
    created because many source CSVs do not document coordinate order or CRS.
    """
    source_path, processed_path, metadata_path = Path(source_path), Path(processed_path), Path(metadata_path)
    if processed_path.exists() or metadata_path.exists():
        raise SpatialDataError("Coordinate review outputs already exist; review will not overwrite them.")
    required_metadata = ("title", "source_url", "publisher", "retrieved_on", "publication_date", "license", "limitations")
    missing_metadata = [key for key in required_metadata if not metadata.get(key)]
    if missing_metadata:
        raise SpatialDataError("Missing source-review metadata: " + ", ".join(missing_metadata))
    try:
        with source_path.open("r", encoding="utf-8-sig", newline="") as input_file:
            reader = csv.DictReader(input_file)
            fieldnames = reader.fieldnames or []
            missing_columns = [column for column in required_columns if column not in fieldnames]
            if missing_columns:
                raise SpatialDataError("CSV is missing required columns: " + ", ".join(missing_columns))
            selected = [row for row in reader
                        if (row.get("State") or "").strip().casefold() == state_value.strip().casefold()
                        and (row.get("District") or "").strip().casefold() == district_value.strip().casefold()]
    except (OSError, UnicodeError, csv.Error) as error:
        raise SpatialDataError(f"Could not read coordinate CSV {source_path}: {error}") from error
    if not selected:
        raise SpatialDataError(f"No records found for {state_value} / {district_value}.")

    parsed_pairs: list[tuple[float, float] | None] = []
    for row in selected:
        raw = (row.get("Location_Coordinates") or "").strip()
        try:
            parts = [part.strip() for part in raw.split(",")]
            pair = (float(parts[0]), float(parts[1])) if len(parts) == 2 else None
            if pair is not None and not all(math.isfinite(value) for value in pair):
                pair = None
        except (ValueError, IndexError):
            pair = None
        parsed_pairs.append(pair)
    pair_counts: dict[tuple[float, float], int] = {}
    for pair in parsed_pairs:
        if pair is not None:
            pair_counts[pair] = pair_counts.get(pair, 0) + 1

    retained_columns = list(retain_columns or fieldnames)
    missing_retained = [column for column in retained_columns if column not in fieldnames]
    if missing_retained:
        raise SpatialDataError("CSV is missing retained columns: " + ", ".join(missing_retained))
    output_columns = retained_columns + [
        "coordinate_pair_parse_status",
        "coordinate_values_within_lat_lon_numeric_ranges",
        "duplicate_coordinate_pair_count_in_subset",
        "spatial_validation_status",
    ]
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    with processed_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=output_columns)
        writer.writeheader()
        for row, pair in zip(selected, parsed_pairs):
            in_ranges = pair is not None and -90 <= pair[0] <= 90 and -180 <= pair[1] <= 180
            row["coordinate_pair_parse_status"] = "two finite numeric values" if pair is not None else "missing or nonnumeric pair"
            row["coordinate_values_within_lat_lon_numeric_ranges"] = "yes" if in_ranges else "no / unavailable"
            row["duplicate_coordinate_pair_count_in_subset"] = str(pair_counts.get(pair, 0)) if pair is not None else ""
            row["spatial_validation_status"] = "NOT VALIDATED: coordinate order and CRS are not stated by the source"
            writer.writerow({column: row.get(column, "") for column in retained_columns} | {
                "coordinate_pair_parse_status": row["coordinate_pair_parse_status"],
                "coordinate_values_within_lat_lon_numeric_ranges": row["coordinate_values_within_lat_lon_numeric_ranges"],
                "duplicate_coordinate_pair_count_in_subset": row["duplicate_coordinate_pair_count_in_subset"],
                "spatial_validation_status": row["spatial_validation_status"],
            })

    report = {
        "dataset_id": metadata.get("dataset_id"),
        "source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "processed_sha256": hashlib.sha256(processed_path.read_bytes()).hexdigest(),
        "selected_record_count": len(selected),
        "coordinate_pair_parseable_count": sum(pair is not None for pair in parsed_pairs),
        "coordinate_pair_unparseable_count": sum(pair is None for pair in parsed_pairs),
        "numeric_pair_in_lat_lon_ranges_count": sum(pair is not None and -90 <= pair[0] <= 90 and -180 <= pair[1] <= 180 for pair in parsed_pairs),
        "duplicate_coordinate_pair_group_count": sum(count > 1 for count in pair_counts.values()),
        "records_in_duplicate_coordinate_pair_groups": sum(count for count in pair_counts.values() if count > 1),
        "coordinate_order": "Not documented by source; comma-delimited pair preserved without interpretation.",
        "crs": "Not documented by source; no point geometries created.",
        "processed_file": str(processed_path),
    }
    sidecar = dict(metadata) | {"validation": report, "processed_file": processed_path.name}
    metadata_path.write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def provenance_errors(metadata: dict[str, Any]) -> list[str]:
    """Validate required provenance fields without guessing unknown metadata."""
    errors = []
    for field in PROVENANCE_FIELDS:
        value = metadata.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"Missing provenance field: {field}.")
    source_url = str(metadata.get("source_url", ""))
    if source_url and not source_url.startswith(("https://", "http://")):
        errors.append("source_url must be an HTTP(S) URL.")
    license_name = str(metadata.get("license", "")).strip().casefold()
    if license_name and any(token in license_name for token in ("unknown", "not known", "not stated", "not available", "not found", "not verified", "no dataset-level")):
        errors.append("A specific reuse licence or rights statement is required before ingestion.")
    retrieved_on = str(metadata.get("retrieved_on", ""))
    if retrieved_on:
        try:
            date.fromisoformat(retrieved_on)
        except ValueError:
            errors.append("retrieved_on must use YYYY-MM-DD format.")
    crs = str(metadata.get("crs", "")).strip().upper().replace(" ", "")
    if crs not in {"EPSG:4326", "OGC:CRS84", "WGS84"}:
        errors.append("Only documented WGS 84 longitude/latitude (EPSG:4326) input is supported; reproject before ingestion.")
    if not isinstance(metadata.get("limitations"), list) or not metadata.get("limitations"):
        errors.append("limitations must be a non-empty list, including an explicit unknown/none statement.")
    if metadata.get("layer_role") not in (None, "asset", "hazard", "context"):
        errors.append("layer_role, when provided, must be asset, hazard, or context.")
    if metadata.get("publication_date") in (None, ""):
        errors.append("publication_date must state a date or explicitly say it is not stated by the source.")
    elif not any(token in str(metadata["publication_date"]).casefold() for token in ("not stated", "not available", "not published", "unknown from source")):
        try:
            date.fromisoformat(str(metadata["publication_date"]))
        except ValueError:
            errors.append("publication_date must use YYYY-MM-DD or explicitly say that the source does not state it.")
    return errors


def _positions(geometry: dict[str, Any]) -> Iterable[list[float]]:
    """Yield GeoJSON coordinate positions for supported geometry types."""
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind == "GeometryCollection":
        for child in geometry.get("geometries", []):
            yield from _positions(child)
        return
    if kind == "Point":
        yield coords
    elif kind == "MultiPoint" or kind == "LineString":
        yield from coords
    elif kind == "MultiLineString" or kind == "Polygon":
        for line_or_ring in coords:
            yield from line_or_ring
    elif kind == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                yield from ring


def _orient(a: list[float], b: list[float], c: list[float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: list[float], b: list[float], point: list[float], eps: float = 1e-12) -> bool:
    return (
        abs(_orient(a, b, point)) <= eps
        and min(a[0], b[0]) - eps <= point[0] <= max(a[0], b[0]) + eps
        and min(a[1], b[1]) - eps <= point[1] <= max(a[1], b[1]) + eps
    )


def _segments_intersect(a: list[float], b: list[float], c: list[float], d: list[float]) -> bool:
    o1, o2, o3, o4 = _orient(a, b, c), _orient(a, b, d), _orient(c, d, a), _orient(c, d, b)
    eps = 1e-12
    if ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps)) and ((o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps)):
        return True
    return any((abs(value) <= eps and _on_segment(start, end, point)) for value, start, end, point in (
        (o1, a, b, c), (o2, a, b, d), (o3, c, d, a), (o4, c, d, b)
    ))


def _ring_errors(ring: Any, path: str) -> list[str]:
    errors = []
    if not isinstance(ring, list) or len(ring) < 4:
        return [f"{path} must contain at least four positions."]
    if ring[0] != ring[-1]:
        errors.append(f"{path} is not closed.")
    if any(not isinstance(pos, list) or len(pos) < 2 for pos in ring):
        return errors + [f"{path} contains an invalid coordinate position."]
    try:
        area_twice = sum(
            float(start[0]) * float(end[1]) - float(end[0]) * float(start[1])
            for start, end in zip(ring, ring[1:])
        )
    except (TypeError, ValueError, OverflowError):
        return errors + [f"{path} contains non-numeric coordinates."]
    if abs(area_twice) <= 1e-18:
        errors.append(f"{path} has zero area.")
    segments = list(zip(ring, ring[1:]))
    # A quadratic self-crossing check is suitable for city-scale polygons; very
    # large rings are explicitly flagged rather than causing an unbounded scan.
    if len(segments) > 8000:
        errors.append(f"{path} has more than 8,000 segments; simplify or validate it with a GIS tool before ingestion.")
        return errors
    for i, (a, b) in enumerate(segments):
        for j in range(i + 1, len(segments)):
            if j in (i, i + 1) or (i == 0 and j == len(segments) - 1):
                continue
            c, d = segments[j]
            if _segments_intersect(a, b, c, d):
                errors.append(f"{path} self-intersects between segments {i} and {j}.")
                return errors
    return errors


def geometry_errors(geometry: Any) -> list[str]:
    """Check supported GeoJSON geometry structure, closure, and WGS 84 ranges."""
    if not isinstance(geometry, dict):
        return ["Feature geometry must be a GeoJSON geometry object, not null."]
    kind = geometry.get("type")
    coords = geometry.get("coordinates")
    if kind not in SUPPORTED_GEOMETRIES:
        return [f"Unsupported or missing geometry type: {kind!r}."]
    errors: list[str] = []
    if kind == "GeometryCollection":
        children = geometry.get("geometries")
        if not isinstance(children, list) or not children:
            return ["GeometryCollection must contain geometries."]
        for i, child in enumerate(children):
            errors.extend(f"geometries[{i}]: {message}" for message in geometry_errors(child))
        return errors
    if coords is None:
        return ["Geometry coordinates are missing."]
    if kind == "Point" and not isinstance(coords, list):
        return ["Point coordinates must be a numeric position list."]
    try:
        positions = list(_positions(geometry))
    except (TypeError, ValueError):
        return ["Geometry coordinates have an invalid nested structure."]
    if not positions:
        return ["Geometry contains no positions."]
    for index, position in enumerate(positions):
        if not isinstance(position, list) or len(position) < 2:
            errors.append(f"Coordinate position {index} must contain longitude and latitude.")
            continue
        try:
            longitude, latitude = float(position[0]), float(position[1])
        except (TypeError, ValueError):
            errors.append(f"Coordinate position {index} is not numeric.")
            continue
        if not math.isfinite(longitude) or not math.isfinite(latitude):
            errors.append(f"Coordinate position {index} is not finite.")
        elif not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            errors.append(f"Coordinate position {index} is outside WGS 84 longitude/latitude ranges.")
    if kind == "Point" and len(coords) < 2:
        errors.append("Point must have at least two ordinates.")
    elif kind in {"MultiPoint", "LineString"} and len(coords) < (2 if kind == "LineString" else 1):
        errors.append(f"{kind} has too few positions.")
    elif kind == "MultiLineString" and any(len(line) < 2 for line in coords):
        errors.append("Each MultiLineString part must have at least two positions.")
    elif kind == "Polygon":
        if not coords:
            errors.append("Polygon must have an exterior ring.")
        for i, ring in enumerate(coords):
            errors.extend(_ring_errors(ring, f"polygon ring {i}"))
        if coords and len(coords[0]) >= 4 and not errors:
            for i, hole in enumerate(coords[1:], start=1):
                if not point_in_ring(hole[0], coords[0]):
                    errors.append(f"Polygon hole {i} is outside its exterior ring.")
                    continue
                if any(_segments_intersect(a, b, c, d)
                       for a, b in zip(coords[0], coords[0][1:])
                       for c, d in zip(hole, hole[1:])):
                    errors.append(f"Polygon hole {i} intersects its exterior ring.")
                for previous_index, previous_hole in enumerate(coords[1:i], start=1):
                    if (any(_segments_intersect(a, b, c, d)
                            for a, b in zip(previous_hole, previous_hole[1:])
                            for c, d in zip(hole, hole[1:]))
                            or point_in_ring(hole[0], previous_hole)
                            or point_in_ring(previous_hole[0], hole)):
                        errors.append(f"Polygon holes {previous_index} and {i} overlap or touch.")
    elif kind == "MultiPolygon":
        if not coords:
            errors.append("MultiPolygon must contain polygons.")
        for polygon_index, polygon in enumerate(coords):
            if not polygon:
                errors.append(f"MultiPolygon member {polygon_index} has no exterior ring.")
                continue
            for ring_index, ring in enumerate(polygon):
                errors.extend(_ring_errors(ring, f"polygon {polygon_index} ring {ring_index}"))
    return errors


def point_in_ring(point: list[float], ring: list[list[float]]) -> bool:
    """Return true for interior or boundary points using ray casting."""
    inside = False
    x, y = float(point[0]), float(point[1])
    for start, end in zip(ring, ring[1:]):
        if _on_segment(start, end, [x, y]):
            return True
        x1, y1 = start[0], start[1]
        x2, y2 = end[0], end[1]
        if (y1 > y) != (y2 > y):
            crossing_x = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < crossing_x:
                inside = not inside
    return inside


def _point_on_ring(point: list[float], ring: list[list[float]]) -> bool:
    return any(_on_segment(start, end, point) for start, end in zip(ring, ring[1:]))


def _polygon_contains_point(point: list[float], rings: list[list[list[float]]]) -> bool:
    if not rings:
        return False
    # Every ring boundary belongs to the polygon boundary, including hole edges.
    if any(_point_on_ring(point, ring) for ring in rings):
        return True
    return point_in_ring(point, rings[0]) and not any(point_in_ring(point, hole) for hole in rings[1:])


def _geometry_lines(geometry: dict[str, Any]) -> list[list[list[float]]]:
    kind, coords = geometry.get("type"), geometry.get("coordinates")
    if kind == "LineString":
        return [coords]
    if kind == "MultiLineString":
        return coords
    if kind == "Polygon":
        return coords
    if kind == "MultiPolygon":
        return [ring for polygon in coords for ring in polygon]
    if kind == "GeometryCollection":
        return [line for child in geometry["geometries"] for line in _geometry_lines(child)]
    return []


def _geometry_points(geometry: dict[str, Any]) -> list[list[float]]:
    kind, coords = geometry.get("type"), geometry.get("coordinates")
    if kind == "Point":
        return [coords]
    if kind == "MultiPoint":
        return coords
    if kind == "GeometryCollection":
        return [point for child in geometry["geometries"] for point in _geometry_points(child)]
    return []


def _polygons(geometry: dict[str, Any]) -> list[list[list[list[float]]]]:
    kind, coords = geometry.get("type"), geometry.get("coordinates")
    if kind == "Polygon":
        return [coords]
    if kind == "MultiPolygon":
        return coords
    if kind == "GeometryCollection":
        return [polygon for child in geometry["geometries"] for polygon in _polygons(child)]
    return []


def _point_intersects(point: list[float], geometry: dict[str, Any]) -> bool:
    kind = geometry.get("type")
    if kind == "Point":
        return point[:2] == geometry["coordinates"][:2]
    if kind == "MultiPoint":
        return any(point[:2] == other[:2] for other in geometry["coordinates"])
    for polygon in _polygons(geometry):
        if _polygon_contains_point(point, polygon):
            return True
    for line in _geometry_lines(geometry):
        if any(_on_segment(a, b, point) for a, b in zip(line, line[1:])):
            return True
    return False


def geometry_intersects(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Topological intersection for GeoJSON geometry in WGS 84 (no distances)."""
    left_positions, right_positions = list(_positions(left)), list(_positions(right))
    if not left_positions or not right_positions:
        return False
    if (max(p[0] for p in left_positions) < min(p[0] for p in right_positions)
        or max(p[0] for p in right_positions) < min(p[0] for p in left_positions)
        or max(p[1] for p in left_positions) < min(p[1] for p in right_positions)
        or max(p[1] for p in right_positions) < min(p[1] for p in left_positions)):
        return False
    if any(_point_intersects(point, right) for point in _geometry_points(left)):
        return True
    if any(_point_intersects(point, left) for point in _geometry_points(right)):
        return True
    left_lines, right_lines = _geometry_lines(left), _geometry_lines(right)
    if any(_point_intersects(position, right) for line in left_lines for position in line):
        return True
    if any(_point_intersects(position, left) for line in right_lines for position in line):
        return True
    for left_line in left_lines:
        for right_line in right_lines:
            for a, b in zip(left_line, left_line[1:]):
                for c, d in zip(right_line, right_line[1:]):
                    if _segments_intersect(a, b, c, d):
                        return True
    # Detect a polygon wholly contained by another without crossing boundaries.
    left_polygons, right_polygons = _polygons(left), _polygons(right)
    for left_polygon in left_polygons:
        if any(_polygon_contains_point(position, right_polygon)
               for right_polygon in right_polygons for ring in left_polygon[:1] for position in ring[:-1]):
            return True
    for right_polygon in right_polygons:
        if any(_polygon_contains_point(position, left_polygon)
               for left_polygon in left_polygons for ring in right_polygon[:1] for position in ring[:-1]):
            return True
    return False


def read_geojson(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Read a GeoJSON Feature/FeatureCollection; reject other formats clearly."""
    path = Path(path)
    if path.suffix.lower() not in {".json", ".geojson"}:
        raise SpatialDataError("Only .geojson/.json Feature or FeatureCollection input is currently supported; convert other formats in a GIS tool first.")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpatialDataError(f"Cannot read valid UTF-8 GeoJSON from {path}: {error}") from error
    if not isinstance(document, dict):
        raise SpatialDataError("GeoJSON root must be an object.")
    if document.get("type") == "FeatureCollection":
        features = document.get("features")
    elif document.get("type") == "Feature":
        features = [document]
    else:
        raise SpatialDataError("GeoJSON root must be a Feature or FeatureCollection.")
    if not isinstance(features, list):
        raise SpatialDataError("FeatureCollection features must be a list.")
    return document, features


def validate_geojson(
    path: Path,
    metadata: dict[str, Any],
    coverage_geometry: dict[str, Any] | None = None,
    required_properties: list[str] | None = None,
) -> dict[str, Any]:
    """Return deterministic structural, coordinate, duplicate, and coverage QA."""
    errors = provenance_errors(metadata)
    document, features = read_geojson(Path(path))
    if coverage_geometry is not None:
        if coverage_geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            errors.append("Coverage geometry must be a Polygon or MultiPolygon.")
        coverage_errors = geometry_errors(coverage_geometry)
        errors.extend(f"Invalid coverage geometry: {message}" for message in coverage_errors)
    if document.get("crs"):
        crs_value = document["crs"]
        embedded_name = ""
        if isinstance(crs_value, dict):
            embedded_name = str((crs_value.get("properties") or {}).get("name", ""))
        if embedded_name.upper().replace(" ", "") not in {"EPSG:4326", "OGC:CRS84", "WGS84", "URN:OGC:DEF:CRS:OGC:1.3:CRS84"}:
            errors.append("Embedded GeoJSON CRS is not a recognized WGS 84 longitude/latitude declaration.")
        metadata_name = str(metadata.get("crs", "")).upper().replace(" ", "")
        if metadata_name not in {"EPSG:4326", "OGC:CRS84", "WGS84"}:
            errors.append("Embedded GeoJSON CRS does not match documented WGS 84.")
    geometry_types: dict[str, int] = {}
    invalid_features: list[dict[str, Any]] = []
    missing_values = 0
    duplicate_feature_count = 0
    seen: set[str] = set()
    ids: set[str] = set()
    duplicate_id_count = 0
    in_coverage = 0
    outside_coverage = 0
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            invalid_features.append({"feature_index": index, "errors": ["Entry is not a GeoJSON Feature."]})
            continue
        geometry = feature.get("geometry")
        problems = geometry_errors(geometry)
        if geometry:
            geometry_types[geometry.get("type", "Unknown")] = geometry_types.get(geometry.get("type", "Unknown"), 0) + 1
        if problems:
            invalid_features.append({"feature_index": index, "id": feature.get("id"), "errors": problems})
        properties = feature.get("properties") or {}
        if not isinstance(properties, dict):
            invalid_features.append({"feature_index": index, "id": feature.get("id"), "errors": ["Feature properties must be an object or null."]})
            properties = {}
        missing_values += sum(value is None or (isinstance(value, str) and not value.strip()) for value in properties.values())
        missing_values += sum(key not in properties for key in (required_properties or []))
        fingerprint = json.dumps(feature, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        if fingerprint in seen:
            duplicate_feature_count += 1
        seen.add(fingerprint)
        if feature.get("id") is not None:
            feature_id = str(feature["id"])
            if feature_id in ids:
                duplicate_id_count += 1
            ids.add(feature_id)
        if coverage_geometry and geometry and not problems:
            if geometry_intersects(geometry, coverage_geometry):
                in_coverage += 1
            else:
                outside_coverage += 1
    if not features:
        errors.append("GeoJSON contains no features.")
    if invalid_features:
        errors.append(f"{len(invalid_features)} feature(s) have invalid geometry or properties.")
    warnings = []
    if duplicate_feature_count:
        warnings.append(f"Found {duplicate_feature_count} exact duplicate feature row(s).")
    if duplicate_id_count:
        warnings.append(f"Found {duplicate_id_count} repeated feature id(s).")
    if missing_values:
        warnings.append(f"Found {missing_values} missing/blank property value(s), including required-field checks.")
    if coverage_geometry is not None and outside_coverage:
        warnings.append(f"{outside_coverage} feature(s) do not intersect the supplied coverage geometry; verify intended extent.")
    return {
        "dataset_id": metadata.get("dataset_id", Path(path).stem),
        "source_file": str(path),
        "source_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "provenance_valid": not provenance_errors(metadata),
        "feature_count": len(features),
        "geometry_types": geometry_types,
        "invalid_features": invalid_features,
        "exact_duplicate_features": duplicate_feature_count,
        "duplicate_ids": duplicate_id_count,
        "missing_property_values": missing_values,
        "features_intersecting_coverage": in_coverage if coverage_geometry is not None else None,
        "features_outside_coverage": outside_coverage if coverage_geometry is not None else None,
        "errors": errors,
        "warnings": warnings,
        "intersection_method": "Planar topological overlay in longitude/latitude (EPSG:4326); boundary counts as intersection; no distance/area calculation.",
    }


def ingest_geojson(
    source_path: Path,
    processed_root: Path,
    metadata: dict[str, Any],
    coverage_geometry: dict[str, Any] | None = None,
    required_properties: list[str] | None = None,
) -> dict[str, Any]:
    """Validate then copy the untouched GeoJSON and provenance into processed storage."""
    required_properties = required_properties or metadata.get("required_properties")
    report = validate_geojson(source_path, metadata, coverage_geometry, required_properties)
    if report["errors"]:
        raise SpatialDataError("Dataset rejected: " + " ".join(report["errors"]))
    destination_dir = Path(processed_root) / "spatial_layers"
    destination_dir.mkdir(parents=True, exist_ok=True)
    dataset_id = str(metadata["dataset_id"])
    if not re.fullmatch(r"[A-Za-z0-9_-]+", dataset_id):
        raise SpatialDataError("dataset_id may contain only letters, numbers, hyphens, and underscores.")
    destination = destination_dir / f"{dataset_id}.geojson"
    if destination.resolve() == Path(source_path).resolve():
        raise SpatialDataError("Processed destination must be separate from the source file.")
    metadata_destination = destination_dir / f"{dataset_id}.metadata.json"
    if destination.exists() or metadata_destination.exists():
        raise SpatialDataError(f"Processed layer {dataset_id!r} already exists; ingestion will not overwrite it.")
    shutil.copy2(source_path, destination)
    stored_metadata = dict(metadata)
    stored_metadata.update({"processed_file": destination.name, "validation": report})
    metadata_destination.write_text(
        json.dumps(stored_metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report | {"processed_file": str(destination)}


def ingest_geojson_feature_lines(
    source_path: Path,
    processed_root: Path,
    metadata: dict[str, Any],
    required_properties: list[str] | None = None,
) -> dict[str, Any]:
    """Normalize line-delimited Feature objects, excluding invalid geometries transparently.

    Some source exports store one GeoJSON Feature per line instead of a single
    FeatureCollection. The original bytes remain untouched. The processed copy
    is a standard FeatureCollection containing only geometry-valid features;
    exclusions and both source/processed hashes are recorded in the sidecar.
    """
    source_path = Path(source_path)
    try:
        source_bytes = source_path.read_bytes()
        lines = source_bytes.decode("utf-8").splitlines()
        features = [json.loads(line) for line in lines if line.strip()]
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SpatialDataError(f"Cannot read line-delimited GeoJSON Features from {source_path}: {error}") from error
    if not features or any(not isinstance(feature, dict) or feature.get("type") != "Feature" for feature in features):
        raise SpatialDataError("Line-delimited input must contain one GeoJSON Feature object per non-empty line.")

    valid_features = []
    excluded = []
    for index, feature in enumerate(features):
        problems = geometry_errors(feature.get("geometry"))
        if problems:
            excluded.append({"feature_index": index, "source_fid": (feature.get("properties") or {}).get("fid"), "errors": problems})
        else:
            valid_features.append(feature)
    if not valid_features:
        raise SpatialDataError("No geometry-valid features remain after source validation.")

    normalized = {"type": "FeatureCollection", "features": valid_features}
    problems = provenance_errors(metadata)
    if problems:
        raise SpatialDataError("Dataset rejected: " + " ".join(problems))
    dataset_id = str(metadata.get("dataset_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]+", dataset_id):
        raise SpatialDataError("dataset_id may contain only letters, numbers, hyphens, and underscores.")
    destination_dir = Path(processed_root) / "spatial_layers"
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = destination_dir / f"{dataset_id}.geojson"
    metadata_destination = destination_dir / f"{dataset_id}.metadata.json"
    if destination.exists() or metadata_destination.exists():
        raise SpatialDataError(f"Processed layer {dataset_id!r} already exists; ingestion will not overwrite it.")
    destination.write_text(json.dumps(normalized, ensure_ascii=False), encoding="utf-8")
    try:
        report = validate_geojson(destination, metadata, required_properties=required_properties or metadata.get("required_properties"))
        if report["errors"]:
            raise SpatialDataError("Normalized dataset rejected: " + " ".join(report["errors"]))
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    stored_metadata = dict(metadata)
    stored_metadata.update({"processed_file": destination.name, "validation": report})
    stored_metadata.update({
        "source_format": "newline-delimited GeoJSON Feature objects",
        "source_snapshot_file": source_path.name,
        "source_snapshot_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_feature_count": len(features),
        "processed_feature_count": len(valid_features),
        "excluded_invalid_features": excluded,
        "processing_note": "Normalized source Feature lines into a FeatureCollection; geometry-invalid source features are listed and excluded. Other properties are retained as supplied.",
    })
    stored_metadata["validation"]["source_snapshot_sha256"] = hashlib.sha256(source_bytes).hexdigest()
    stored_metadata["validation"]["source_feature_count"] = len(features)
    stored_metadata["validation"]["excluded_invalid_feature_count"] = len(excluded)
    stored_metadata["validation"]["excluded_invalid_features"] = excluded
    if excluded:
        stored_metadata["validation"]["warnings"].append(
            f"Excluded {len(excluded)} geometry-invalid source feature(s); original snapshot retained separately."
        )
    metadata_destination.write_text(json.dumps(stored_metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return report | {"processed_file": str(destination),
        "source_snapshot_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "source_feature_count": len(features),
        "processed_feature_count": len(valid_features),
        "excluded_invalid_features": excluded,
    }


def _latest_processed_layer_paths(layer_dir: Path) -> list[Path]:
    """Return newest metadata-described snapshot per logical layer."""
    latest: dict[str, tuple[tuple[str, str, str], Path]] = {}
    ungrouped: list[Path] = []
    for geojson_path in sorted(layer_dir.glob("*.geojson")) if layer_dir.is_dir() else []:
        metadata_path = geojson_path.with_name(f"{geojson_path.stem}.metadata.json")
        if not metadata_path.is_file():
            ungrouped.append(geojson_path)
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            ungrouped.append(geojson_path)
            continue
        dataset_id = str(metadata.get("dataset_id") or geojson_path.stem)
        logical_id = str(metadata.get("logical_layer_id") or f"dataset:{dataset_id}")
        order = (
            str(metadata.get("retrieved_at_utc") or metadata.get("retrieved_on") or ""),
            str(metadata.get("source_database_timestamp") or ""),
            dataset_id,
        )
        current = latest.get(logical_id)
        if current is None or order > current[0]:
            latest[logical_id] = (order, geojson_path)
    return sorted(ungrouped + [entry[1] for entry in latest.values()])


def read_processed_layers(processed_root: Path, coverage_geometry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Load only the newest snapshot per logical layer when its validation passes."""
    layer_dir = Path(processed_root) / "spatial_layers"
    layers = []
    for geojson_path in _latest_processed_layer_paths(layer_dir):
        metadata_path = geojson_path.with_name(f"{geojson_path.stem}.metadata.json")
        if not metadata_path.is_file():
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("dataset_id") != geojson_path.stem:
                continue
            report = validate_geojson(geojson_path, metadata, coverage_geometry, metadata.get("required_properties"))
            expected_hash = (metadata.get("validation") or {}).get("source_sha256")
            if not expected_hash or expected_hash != report["source_sha256"]:
                continue
            if report["errors"] or not report["provenance_valid"]:
                continue
            document, features = read_geojson(geojson_path)
        except (OSError, json.JSONDecodeError, SpatialDataError):
            continue
        layers.append({"metadata": metadata, "report": report, "geojson": document, "features": features})
    return layers


def processed_layer_issues(processed_root: Path, coverage_geometry: dict[str, Any] | None = None) -> list[str]:
    """Describe processed files hidden from the map because metadata/QA failed."""
    layer_dir = Path(processed_root) / "spatial_layers"
    issues = []
    if not layer_dir.is_dir():
        return issues
    for geojson_path in _latest_processed_layer_paths(layer_dir):
        metadata_path = geojson_path.with_name(f"{geojson_path.stem}.metadata.json")
        if not metadata_path.is_file():
            issues.append(f"{geojson_path.name}: missing provenance metadata sidecar; layer not loaded.")
            continue
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("dataset_id") != geojson_path.stem:
                issues.append(f"{geojson_path.name}: sidecar dataset_id does not match the file name; layer not loaded.")
                continue
            expected_hash = (metadata.get("validation") or {}).get("source_sha256")
            actual_hash = hashlib.sha256(geojson_path.read_bytes()).hexdigest()
            if not expected_hash or expected_hash != actual_hash:
                issues.append(f"{geojson_path.name}: content hash does not match the ingestion sidecar; layer not loaded.")
                continue
            report = validate_geojson(geojson_path, metadata, coverage_geometry, metadata.get("required_properties"))
        except (OSError, json.JSONDecodeError, SpatialDataError) as error:
            issues.append(f"{geojson_path.name}: could not be read or validated ({error}); layer not loaded.")
            continue
        if report["errors"]:
            issues.append(f"{geojson_path.name}: {' '.join(report['errors'])}; layer not loaded.")
        elif geojson_path.stem == "kochi_wards_datameet_2022":
            # Six legacy polygons are retained as contextual shapes but lack both
            # Ward_No and Ward_Name. Report the affected feature count explicitly;
            # display labels use feature indices and never infer official identities.
            _, ward_features = read_geojson(geojson_path)
            missing_ward_features = 0
            for feature in ward_features:
                properties = feature.get("properties") or {}
                missing_number = properties.get("Ward_No") is None or not str(properties.get("Ward_No")).strip()
                missing_name = properties.get("Ward_Name") is None or not str(properties.get("Ward_Name")).strip()
                if missing_number or missing_name:
                    missing_ward_features += 1
            if missing_ward_features:
                issues.append(
                    f"{geojson_path.name}: {missing_ward_features} of {len(ward_features)} legacy polygons "
                    f"have missing Ward_No and/or Ward_Name ({report['missing_property_values']} missing/blank "
                    "values); retained as unlabelled context only, with no inferred ward identities."
                )
            for warning in report["warnings"]:
                if "missing/blank property value" not in warning:
                    issues.append(f"{geojson_path.name}: {warning}")
        elif report["warnings"]:
            issues.append(f"{geojson_path.name}: {' '.join(report['warnings'])}")
    return issues


def classify_exposure(
    assets: list[dict[str, Any]],
    hazards: list[dict[str, Any]] | None,
    asset_id_property: str = "id",
    hazard_id_property: str = "id",
) -> list[dict[str, Any]]:
    """Classify each asset as intersecting, not detected in available zones, or unknown."""
    valid_hazards = [feature for feature in (hazards or []) if feature.get("geometry") and not geometry_errors(feature["geometry"])]
    if not valid_hazards:
        return [{
            "asset_id": (feature.get("properties") or {}).get(asset_id_property, feature.get("id", f"asset-{i}")),
            "exposure_status": "Unknown exposure",
            "intersecting_hazard_ids": [],
            "method": "No compatible valid hazard geometry was supplied; absence of data is not evidence of safety.",
        } for i, feature in enumerate(assets)]
    result = []
    for i, asset in enumerate(assets):
        properties = asset.get("properties") or {}
        asset_id = properties.get(asset_id_property, asset.get("id", f"asset-{i}"))
        if not asset.get("geometry") or geometry_errors(asset["geometry"]):
            result.append({
                "asset_id": asset_id,
                "exposure_status": "Unknown exposure",
                "intersecting_hazard_ids": [],
                "method": "The asset geometry is missing or invalid; no intersection conclusion is possible.",
            })
            continue
        matches = []
        for j, hazard in enumerate(valid_hazards):
            if geometry_intersects(asset["geometry"], hazard["geometry"]):
                hazard_properties = hazard.get("properties") or {}
                matches.append(hazard_properties.get(hazard_id_property, hazard.get("id", f"hazard-{j}")))
        result.append({
            "asset_id": asset_id,
            "exposure_status": "Geometric intersection detected (spatial exposure indicator)" if matches else "No detected intersection within available hazard layer",
            "intersecting_hazard_ids": matches,
            "method": "Topological geometry intersection in documented EPSG:4326 coordinates; no distance, clearance, vulnerability, or safety inferred. A non-intersection applies only within the supplied layer's coverage and completeness.",
        })
    return result


def _main() -> int:
    parser = argparse.ArgumentParser(description="Validate and optionally ingest a provenance-documented WGS 84 GeoJSON layer.")
    parser.add_argument("source", type=Path, help="Source GeoJSON file (kept unchanged)")
    parser.add_argument("--metadata", required=True, type=Path, help="JSON file with required provenance fields")
    parser.add_argument("--coverage-geojson", type=Path, help="Optional valid Polygon/MultiPolygon GeoJSON used only to report intersecting/outside feature counts")
    parser.add_argument("--processed-root", type=Path, default=Path("data/processed"))
    parser.add_argument("--validate-only", action="store_true", help="Write validation JSON to stdout without copying")
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    coverage_geometry = None
    if args.coverage_geojson:
        _, coverage_features = read_geojson(args.coverage_geojson)
        coverage_geometries = [feature.get("geometry") for feature in coverage_features]
        if len(coverage_geometries) != 1 or not coverage_geometries[0] or coverage_geometries[0].get("type") not in {"Polygon", "MultiPolygon"}:
            raise SpatialDataError("Coverage GeoJSON must contain exactly one Polygon or MultiPolygon feature.")
        coverage_geometry = coverage_geometries[0]
    report = validate_geojson(args.source, metadata, coverage_geometry)
    if not args.validate_only and not report["errors"]:
        report = ingest_geojson(args.source, args.processed_root, metadata, coverage_geometry)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(_main())

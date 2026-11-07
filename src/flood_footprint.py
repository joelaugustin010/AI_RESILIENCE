"""Summarize a supplied, quality-checked flood-depth GeoJSON footprint.

This is an evidence-ingestion and measurement tool, not a hydraulic model or
flood forecast. Every polygon must carry a non-negative depth_m attribute.
Areas are measured in an equal-area projection; overlapping polygons are
rejected to avoid double counting.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

try:
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform
    from shapely.strtree import STRtree
except ImportError:  # optional spatial stack
    Transformer = None
    shape = None
    transform = None
    STRtree = None


class FloodFootprintError(ValueError):
    """Raised when supplied flood-depth geometry cannot be measured safely."""


def summarize_flood_depth_geojson(
    payload: Mapping[str, Any],
    *,
    depth_field: str = "depth_m",
    source_crs: str = "EPSG:4326",
    max_features: int = 25_000,
) -> dict[str, Any]:
    """Measure extent and depth statistics from a supplied polygon depth layer."""
    if shape is None or Transformer is None or transform is None or STRtree is None:
        raise FloodFootprintError("Flood-depth analysis requires optional shapely and pyproj packages.")
    if source_crs != "EPSG:4326":
        raise FloodFootprintError("Only EPSG:4326 GeoJSON is accepted; reproject and document the source first.")
    if not isinstance(payload, Mapping) or payload.get("type") != "FeatureCollection":
        raise FloodFootprintError("Flood-depth input must be a GeoJSON FeatureCollection.")
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise FloodFootprintError("Flood-depth GeoJSON contains no features.")
    if len(features) > max_features:
        raise FloodFootprintError(f"Flood-depth GeoJSON exceeds the {max_features:,}-feature limit.")

    project = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
    measured: list[tuple[Any, float, float]] = []
    for index, feature in enumerate(features):
        props = feature.get("properties") or {}
        try:
            depth = float(props[depth_field])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise FloodFootprintError(f"Feature {index} requires a numeric {depth_field!r} property.") from exc
        if not math.isfinite(depth) or depth <= 0 or depth > 100:
            raise FloodFootprintError(f"Feature {index} depth must be finite, greater than 0 and at most 100 metres.")
        try:
            geom = shape(feature["geometry"])
        except Exception as exc:
            raise FloodFootprintError(f"Feature {index} has invalid geometry: {exc}") from exc
        if geom.is_empty or not geom.is_valid or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise FloodFootprintError(f"Feature {index} must be a valid Polygon or MultiPolygon.")
        min_x, min_y, max_x, max_y = geom.bounds
        if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
            raise FloodFootprintError(f"Feature {index} coordinates are outside EPSG:4326 bounds.")
        projected = transform(project, geom)
        area = projected.area
        if not math.isfinite(area) or area <= 0:
            raise FloodFootprintError(f"Feature {index} has invalid or zero area.")
        measured.append((projected, depth, area))

    # Use a spatial index so overlap QA does not require all-pairs comparisons.
    geometries = [item[0] for item in measured]
    spatial_index = STRtree(geometries)
    for position, (geom, _, _) in enumerate(measured):
        for candidate in spatial_index.query(geom):
            other_position = int(candidate)
            if other_position <= position:
                continue
            other = geometries[other_position]
            overlap = geom.intersection(other).area
            if overlap > max(1e-4, min(geom.area, other.area) * 1e-10):
                raise FloodFootprintError("Depth polygons overlap; resolve overlaps before calculating extent.")

    total_area = sum(area for _, _, area in measured)
    weighted_depth = sum(depth * area for _, depth, area in measured) / total_area
    depth_values = [depth for _, depth, _ in measured]
    bands = {
        "0_to_0.15_m": sum(area for _, depth, area in measured if 0 < depth <= 0.15),
        "0.15_to_0.5_m": sum(area for _, depth, area in measured if 0.15 < depth <= 0.5),
        "0.5_to_1.0_m": sum(area for _, depth, area in measured if 0.5 < depth <= 1.0),
        "above_1.0_m": sum(area for _, depth, area in measured if depth > 1.0),
    }
    return {
        "status": "SUPPLIED_FLOOD_DEPTH_LAYER_SUMMARIZED_NOT_FORECAST",
        "flooded_extent_km2": round(total_area / 1_000_000, 4),
        "area_weighted_mean_depth_m": round(weighted_depth, 3),
        "maximum_polygon_depth_m": round(max(depth_values), 3),
        "minimum_polygon_depth_m": round(min(depth_values), 3),
        "polygon_count": len(measured),
        "area_by_depth_band_km2": {key: round(value / 1_000_000, 4) for key, value in bands.items()},
        "method": "Polygon areas measured in EPSG:6933; depth is area-weighted from supplied depth_m attributes.",
        "limitations": [
            "This summarizes a supplied depth layer; it does not generate or forecast flood depth or extent.",
            "Source date, vertical datum, depth reference, event identity, spatial coverage and licence must be verified independently.",
            "Depth bands are descriptive bins, not safety, building-damage or casualty thresholds.",
            "The result is not operationally validated and must not guide evacuation or route safety.",
        ],
    }


__all__ = ["FloodFootprintError", "summarize_flood_depth_geojson"]

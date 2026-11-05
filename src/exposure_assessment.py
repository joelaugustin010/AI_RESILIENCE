"""Modelled flood-depth screening at provisional community-mapped asset locations.

This module answers a narrow, explicitly limited question: *what does the JRC
GloFAS RP100 modelled depth field show at the representative point of each
mapped asset?*  It does **not** produce an operational exposure count.

Why the result is labelled provisional screening
------------------------------------------------
* The JRC layer is a global modelled 100-year river-flood scenario at about
  90 m.  It is not an observation, forecast, official warning, or engineering
  result.
* Asset geometry comes from OpenStreetMap, a community-mapped source whose
  completeness and positional accuracy are not independently verified.
* Representative points are bounding-box centres of the mapped geometry, not
  surveyed facility entrances.
* Only the RP100 depth field and the matching permanent-water tiles were
  downloaded.  Permanent-water cells are excluded from the screening; the
  documented spurious-depth artifact mask is unavailable, so those artifact
  flags are not applied.

Consequently a positive modelled cell is a screening signal worth field
checking, and a zero or NoData cell is not evidence of safety.  Population
exposure is not assessed because no verified population layer exists.

The reader is the pure-Python :class:`src.flood_raster.JrcDepthTile`, so this
module adds no new dependency and keeps the same pinned NoData semantics.
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from src.flood_raster import FloodRasterError, JrcDepthTile, JrcPermanentWaterTile


ASSET_LAYERS: tuple[dict[str, str], ...] = (
    {
        "layer_id": "osm_kochi_healthcare",
        "label": "Healthcare facilities",
        "file": "osm_kochi_healthcare_20261028T192850Z.geojson",
    },
    {
        "layer_id": "osm_kochi_emergency",
        "label": "Emergency facilities",
        "file": "osm_kochi_emergency_20261028T192850Z.geojson",
    },
    {
        "layer_id": "osm_kochi_roads",
        "label": "Mapped roads",
        "file": "osm_kochi_roads_20261028T192808Z.geojson",
    },
    {
        "layer_id": "osm_kochi_transit",
        "label": "Rail and transit ways",
        "file": "osm_kochi_transit_20261028T192808Z.geojson",
    },
    {
        "layer_id": "osm_kochi_industry",
        "label": "Mapped industrial features",
        "file": "osm_kochi_industry_20261028T192850Z.geojson",
    },
)

STATUS_POSITIVE = "positive modelled depth cell (provisional screening)"
STATUS_ZERO = "zero modelled depth cell (provisional screening)"
STATUS_NODATA = "NoData in modelled source"
STATUS_OUTSIDE = "outside modelled source coverage"
STATUS_INVALID = "invalid or missing geometry"
STATUS_PERMANENT_WATER = "permanent-water cell (excluded from flood screening)"

METHOD_NOTE = (
    "Nearest raster cell sampled at the bounding-box centre of a provisional "
    "OpenStreetMap geometry. This is not a facility entrance, an observed flood "
    "depth, or a validated exposure count. Permanent-water cells are excluded. "
    "NoData means no depth value is stored, not confirmed absence of flooding; "
    "a NoData cell does not establish safety."
)

_NAME_KEYS = (
    "name",
    "name:en",
    "official_name",
    "operator",
    "amenity",
    "healthcare",
    "highway",
    "landuse",
    "ref",
)
_ID_KEYS = ("@id", "id", "osm_id", "osmId")


class ExposureAssessmentError(ValueError):
    """Raised when the screening inputs cannot be used safely."""


def _coordinate_pairs(geometry: Any) -> Iterable[tuple[float, float]]:
    """Yield every (longitude, latitude) pair in a GeoJSON geometry."""
    if not isinstance(geometry, Mapping):
        return
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "GeometryCollection":
        for item in geometry.get("geometries") or []:
            yield from _coordinate_pairs(item)
        return
    if geometry_type == "Point":
        if isinstance(coordinates, Sequence) and len(coordinates) >= 2:
            yield float(coordinates[0]), float(coordinates[1])
        return
    if not isinstance(coordinates, Sequence):
        return
    stack = [coordinates]
    while stack:
        item = stack.pop()
        if not isinstance(item, Sequence):
            continue
        if (
            len(item) >= 2
            and isinstance(item[0], (int, float))
            and isinstance(item[1], (int, float))
        ):
            yield float(item[0]), float(item[1])
        else:
            stack.extend(item)


def representative_point(geometry: Any) -> tuple[float, float] | None:
    """Return the bounding-box centre of a geometry, or None when unusable.

    A bounding-box centre is used deliberately: it needs no projection and is
    reproducible, and it is clearly not a surveyed facility entrance.
    """
    points = list(_coordinate_pairs(geometry))
    if not points:
        return None
    longitudes = [point[0] for point in points]
    latitudes = [point[1] for point in points]
    lon = (min(longitudes) + max(longitudes)) / 2
    lat = (min(latitudes) + max(latitudes)) / 2
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return lon, lat


def _feature_label(properties: Mapping[str, Any], fallback: str) -> str:
    for key in _NAME_KEYS:
        value = properties.get(key)
        if value not in (None, "", "nan", "None"):
            return str(value)
    return fallback


def _feature_id(properties: Mapping[str, Any], index: int) -> str:
    for key in _ID_KEYS:
        value = properties.get(key)
        if value not in (None, "", "nan", "None"):
            return str(value)
    return f"feature-{index}"


def load_asset_features(path: Path, layer: Mapping[str, str]) -> list[dict[str, Any]]:
    """Load representative points for one provisional asset layer."""
    path = Path(path)
    if not path.is_file():
        raise ExposureAssessmentError(f"Asset layer not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "FeatureCollection":
        raise ExposureAssessmentError(f"Expected a FeatureCollection: {path}")
    features: list[dict[str, Any]] = []
    for index, feature in enumerate(payload.get("features") or []):
        geometry = feature.get("geometry")
        properties = feature.get("properties") or {}
        point = representative_point(geometry)
        features.append(
            {
                "layer_id": layer["layer_id"],
                "layer_label": layer["label"],
                "feature_id": _feature_id(properties, index),
                "feature_name": _feature_label(properties, f"{layer['label']} feature {index}"),
                "geometry_type": (geometry or {}).get("type") if isinstance(geometry, Mapping) else None,
                "longitude": point[0] if point else None,
                "latitude": point[1] if point else None,
            }
        )
    return features


def tile_contains(tile: Any, longitude: float, latitude: float) -> bool:
    """Return True when the coordinate falls inside the tile's pixel grid."""
    return (
        tile.west <= longitude < tile.west + tile.width * tile.pixel_x
        and tile.north - tile.height * tile.pixel_y < latitude <= tile.north
    )


def classify_screening(
    depth_m: float | None,
    within_coverage: bool,
    permanent_water: int | None = None,
) -> str:
    """Label a sampled modelled depth without implying verified exposure.

    A permanent-water cell is excluded even when the flood-depth raster stores a
    positive value there, because the JRC product patches permanent water into
    the flood map.  Counting a river or lake as flood exposure would overstate
    the screening result.
    """
    if permanent_water == 1:
        return STATUS_PERMANENT_WATER
    if not within_coverage:
        return STATUS_OUTSIDE
    if depth_m is None or not math.isfinite(depth_m):
        return STATUS_NODATA
    if depth_m < 0:
        return STATUS_INVALID
    return STATUS_POSITIVE if depth_m > 0 else STATUS_ZERO


def _permanent_water_at(
    longitude: float, latitude: float, water_tiles: Sequence[JrcPermanentWaterTile]
) -> int | None:
    for tile in water_tiles:
        if tile_contains(tile, longitude, latitude):
            value = tile.sample(longitude, latitude)
            if value is not None:
                return value
    return None


def sample_feature(
    feature: Mapping[str, Any],
    tiles: Sequence[JrcDepthTile],
    water_tiles: Sequence[JrcPermanentWaterTile] = (),
) -> dict[str, Any]:
    """Sample the modelled depth field at one asset representative point."""
    longitude, latitude = feature.get("longitude"), feature.get("latitude")
    if longitude is None or latitude is None:
        return {**feature, "status": STATUS_INVALID, "depth_m": None, "source_tile": None}
    water = _permanent_water_at(longitude, latitude, water_tiles)
    within = False
    for tile in tiles:
        if tile_contains(tile, longitude, latitude):
            within = True
            value = tile.sample(longitude, latitude)
            if value is not None:
                return {
                    **feature,
                    "status": classify_screening(value, True, water),
                    "depth_m": value,
                    "source_tile": tile.path.name,
                    "permanent_water": water,
                }
    return {
        **feature,
        "status": classify_screening(None, within, water),
        "depth_m": None,
        "source_tile": None,
        "permanent_water": water,
    }


def summarize_layer(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate one layer's screening rows without turning them into risk."""
    counts = {
        STATUS_POSITIVE: 0,
        STATUS_ZERO: 0,
        STATUS_NODATA: 0,
        STATUS_OUTSIDE: 0,
        STATUS_INVALID: 0,
        STATUS_PERMANENT_WATER: 0,
    }
    positive_depths: list[float] = []
    for row in rows:
        status = str(row.get("status"))
        if status in counts:
            counts[status] += 1
        depth = row.get("depth_m")
        if status == STATUS_POSITIVE and isinstance(depth, (int, float)) and depth > 0:
            positive_depths.append(float(depth))
    total = len(rows)
    sampled = counts[STATUS_POSITIVE] + counts[STATUS_ZERO] + counts[STATUS_PERMANENT_WATER]
    return {
        "features_total": total,
        "features_sampled_in_coverage": sampled,
        "positive_modelled_depth": counts[STATUS_POSITIVE],
        "zero_modelled_depth": counts[STATUS_ZERO],
        "nodata_in_source": counts[STATUS_NODATA],
        "outside_source_coverage": counts[STATUS_OUTSIDE],
        "invalid_geometry": counts[STATUS_INVALID],
        "permanent_water_cells": counts[STATUS_PERMANENT_WATER],
        "positive_depth_min_m": min(positive_depths) if positive_depths else None,
        "positive_depth_median_m": statistics.median(positive_depths) if positive_depths else None,
        "positive_depth_max_m": max(positive_depths) if positive_depths else None,
        "sampled_fraction": round(sampled / total, 4) if total else None,
        "status": "PROVISIONAL SCREENING ONLY — not verified exposure",
    }


def assess_assets(
    assets_root: Path,
    tiles: Sequence[JrcDepthTile],
    layers: Sequence[Mapping[str, str]] = ASSET_LAYERS,
    water_tiles: Sequence[JrcPermanentWaterTile] = (),
) -> dict[str, Any]:
    """Screen every registered provisional asset layer against the depth field."""
    if not tiles:
        raise ExposureAssessmentError("At least one JRC depth tile is required.")
    layer_results: list[dict[str, Any]] = []
    for layer in layers:
        features = load_asset_features(Path(assets_root) / layer["file"], layer)
        rows = [sample_feature(feature, tiles, water_tiles) for feature in features]
        summary = summarize_layer(rows)
        summary["layer_id"] = layer["layer_id"]
        summary["layer_label"] = layer["label"]
        summary["source_file"] = layer["file"]
        layer_results.append(summary)
    aggregate = {
        "features_total": sum(item["features_total"] for item in layer_results),
        "features_sampled_in_coverage": sum(
            item["features_sampled_in_coverage"] for item in layer_results
        ),
        "positive_modelled_depth": sum(
            item["positive_modelled_depth"] for item in layer_results
        ),
        "zero_modelled_depth": sum(item["zero_modelled_depth"] for item in layer_results),
        "nodata_in_source": sum(item["nodata_in_source"] for item in layer_results),
        "outside_source_coverage": sum(
            item["outside_source_coverage"] for item in layer_results
        ),
        "invalid_geometry": sum(item["invalid_geometry"] for item in layer_results),
        "permanent_water_cells": sum(
            item["permanent_water_cells"] for item in layer_results
        ),
        "status": "PROVISIONAL SCREENING ONLY — not verified exposure",
    }
    return {"aggregate": aggregate, "layers": layer_results, "method": METHOD_NOTE}


def extent_statistics(
    tiles: Sequence[JrcDepthTile],
    bounds: Sequence[float],
    water_tiles: Sequence[JrcPermanentWaterTile] = (),
) -> dict[str, Any]:
    """Count modelled-depth cells inside a display rectangle.

    The rectangle is the preview crop (the provisional boundary's bounding box),
    **not** a validated municipal mask.  Results therefore describe the crop,
    not the legal corporation area.
    """
    if len(bounds) != 4:
        raise ExposureAssessmentError("Bounds must be (west, south, east, north).")
    west, south, east, north = (float(value) for value in bounds)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ExposureAssessmentError("Bounds must be an ordered EPSG:4326 rectangle.")
    tile = tiles[0]
    pixel_x, pixel_y = tile.pixel_x, tile.pixel_y
    columns = max(1, math.ceil((east - west) / pixel_x))
    rows = max(1, math.ceil((north - south) / pixel_y))
    valid = positive = permanent = 0
    positive_area = 0.0
    valid_area = 0.0
    permanent_area = 0.0
    max_depth = 0.0
    for row in range(rows):
        latitude = north - (row + 0.5) * (north - south) / rows
        metres_per_degree_lon = 111_320.0 * math.cos(math.radians(latitude))
        metres_per_degree_lat = 110_574.0
        cell_area_km2 = (
            (east - west) / columns * metres_per_degree_lon
            * (north - south) / rows * metres_per_degree_lat
        ) / 1_000_000
        for column in range(columns):
            longitude = west + (column + 0.5) * (east - west) / columns
            value = None
            for candidate in tiles:
                if tile_contains(candidate, longitude, latitude):
                    value = candidate.sample(longitude, latitude)
                    break
            if value is None:
                continue
            valid += 1
            valid_area += cell_area_km2
            if value > 0:
                if _permanent_water_at(longitude, latitude, water_tiles) == 1:
                    permanent += 1
                    permanent_area += cell_area_km2
                    continue
                positive += 1
                positive_area += cell_area_km2
                max_depth = max(max_depth, value)
    return {
        "bounds_epsg4326": [west, south, east, north],
        "grid_cells_evaluated": rows * columns,
        "valid_cells": valid,
        "positive_depth_cells": positive,
        "permanent_water_cells_excluded": permanent,
        "valid_area_km2": round(valid_area, 3),
        "positive_depth_area_km2": round(positive_area, 3),
        "permanent_water_area_km2": round(permanent_area, 3),
        "positive_fraction_of_valid": round(positive / valid, 4) if valid else None,
        "maximum_modelled_depth_m": max_depth or None,
        "area_method": (
            "Cell-centre sampling of the source raster at 3 arc-second spacing; "
            "per-row latitude scaling. Area is within the display rectangle, not a "
            "validated municipal boundary mask."
        ),
        "caveat": (
            "Modelled RP100 scenario area, not observed inundation. Permanent-water "
            "cells are excluded. The auxiliary spurious-depth mask was not downloaded, "
            "so artifact cells cannot be excluded."
        ),
    }


def build_report(
    assets_root: Path,
    tile_paths: Sequence[Path],
    bounds: Sequence[float],
    water_tile_paths: Sequence[Path] = (),
) -> dict[str, Any]:
    """Build the complete screening report for storage and display."""
    tiles = [JrcDepthTile(path) for path in tile_paths]
    water_tiles = [JrcPermanentWaterTile(path) for path in water_tile_paths]
    report = assess_assets(assets_root, tiles, water_tiles=water_tiles)
    report["extent"] = extent_statistics(tiles, bounds, water_tiles)
    report["source_tiles"] = [
        {
            "file": tile.path.name,
            "sha256": __import__("hashlib").sha256(tile.path.read_bytes()).hexdigest(),
            "crs": "EPSG:4326",
            "nodata": tile.nodata,
            "pixel_size_degrees": [tile.pixel_x, tile.pixel_y],
        }
        for tile in tiles
    ]
    report["permanent_water_tiles"] = [
        {
            "file": tile.path.name,
            "sha256": __import__("hashlib").sha256(tile.path.read_bytes()).hexdigest(),
            "crs": "EPSG:4326",
            "nodata": tile.nodata,
            "permanent_water_value": 1,
        }
        for tile in water_tiles
    ]
    report["licence"] = (
        "JRC GloFAS v2.1.2 used under ODbL 1.0 (dataset README); CC BY 4.0 also "
        "stated by JRC. Attribution and change indication required; share-alike "
        "applies to publicly distributed derived databases. OSM asset context "
        "used under ODbL 1.0 with © OpenStreetMap contributors attribution."
    )
    report["limitations"] = [
        "Modelled 100-year river-flood scenario, not observed flooding, a forecast, or an official warning.",
        "Asset locations are provisional OpenStreetMap community-mapped geometry; completeness and positional accuracy are not verified.",
        "Representative points are bounding-box centres, not surveyed facility entrances.",
        "Only the RP100 depth field and the permanent-water mask were downloaded; the spurious-depth artifact mask is unavailable.",
        "Permanent-water cells are excluded from the positive-depth screening because the JRC product patches permanent water into the flood map.",
        "Cells outside the modelled inundation extent are stored as NoData (−9999), not as zero depth; NoData means no depth value is stored, not confirmed absence of flooding.",
        "Zero and NoData cells do not establish safety. Population exposure and damage are not assessed.",
        "No result here is an operational exposure count, risk class, or casualty estimate.",
    ]
    return report

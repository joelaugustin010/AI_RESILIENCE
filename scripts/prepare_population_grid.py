"""Clip a population-count GeoTIFF to an administrative boundary as GeoJSON cells.

The output is an input-preparation artifact for the population exposure
screening calculator. It is not a population forecast or a validated count.
Boundary-edge cells are area-prorated to the boundary and missing raster
coverage is reported rather than silently filled.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from rasterio.mask import mask as raster_mask
from shapely.geometry import mapping, shape
from shapely.ops import transform as transform_geometry, unary_union
from pyproj import Transformer


def _read_boundary(path: str | Path) -> tuple[Any, str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("type") == "FeatureCollection":
        geometries = [shape(item["geometry"]) for item in payload.get("features", [])]
    elif payload.get("type") == "Feature":
        geometries = [shape(payload["geometry"])]
    else:
        geometries = [shape(payload)]
    geometries = [geom for geom in geometries if not geom.is_empty]
    if not geometries:
        raise ValueError("Boundary file contains no non-empty geometry.")
    boundary = unary_union(geometries)
    if not boundary.is_valid or boundary.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Boundary must resolve to a valid Polygon or MultiPolygon.")
    return boundary, "GeoJSON"


def prepare_population_grid(
    raster_path: str | Path,
    boundary_path: str | Path,
    output_path: str | Path,
    *,
    boundary_crs: str,
    population_year: int,
    source_url: str,
    source_title: str,
    source_license: str,
    max_features: int = 250_000,
) -> dict[str, Any]:
    """Prepare clipped, area-prorated population cells and a provenance sidecar."""
    if not boundary_crs.strip():
        raise ValueError("An explicit boundary CRS is required.")
    if not source_url.startswith("https://"):
        raise ValueError("source_url must be an HTTPS source reference.")
    if not source_title.strip() or not source_license.strip():
        raise ValueError("Source title and licence are required.")

    boundary, _ = _read_boundary(boundary_path)
    output_features = []
    with rasterio.open(raster_path) as dataset:
        if dataset.count != 1:
            raise ValueError("Population raster must contain exactly one band.")
        if dataset.crs is None:
            raise ValueError("Population raster has no CRS.")
        boundary_to_raster = Transformer.from_crs(
            boundary_crs, dataset.crs, always_xy=True
        ).transform
        raster_boundary = transform_geometry(boundary_to_raster, boundary)
        if raster_boundary.is_empty or not raster_boundary.is_valid:
            raise ValueError("Boundary could not be transformed into a valid raster geometry.")

        clipped, clipped_transform = raster_mask(
            dataset, [mapping(raster_boundary)], crop=True,
            filled=False, all_touched=True,
        )
        band = clipped[0]
        scale = float(dataset.scales[0] or 1.0)
        offset = float(dataset.offsets[0] or 0.0)
        if not math.isfinite(scale) or not math.isfinite(offset):
            raise ValueError("Raster scale/offset metadata must be finite.")
        values = np.asarray(band.filled(np.nan), dtype=float) * scale + offset
        valid = (~np.ma.getmaskarray(band)) & np.isfinite(values)
        if np.any(values[valid] < 0):
            raise ValueError("Population raster contains negative population counts.")

        to_equal_area = Transformer.from_crs(
            dataset.crs, "EPSG:6933", always_xy=True
        ).transform
        to_wgs84 = Transformer.from_crs(
            dataset.crs, "EPSG:4326", always_xy=True
        ).transform
        boundary_equal = transform_geometry(to_equal_area, raster_boundary)
        boundary_area = float(boundary_equal.area)
        if not math.isfinite(boundary_area) or boundary_area <= 0:
            raise ValueError("Boundary has invalid area after equal-area projection.")

        rows, cols = values.shape
        if int(valid.sum()) > max_features:
            raise ValueError(
                f"Clipped raster has {int(valid.sum()):,} valid cells; "
                f"limit is {max_features:,}. Use a coarser grid or raise the reviewed limit."
            )

        from affine import Affine
        cell_geometries_equal = []
        for row in range(rows):
            for col in range(cols):
                if not valid[row, col]:
                    continue
                cell = rasterio.features.geometry_window if False else None
                x0, y0 = clipped_transform * (col, row)
                x1, y1 = clipped_transform * (col + 1, row + 1)
                # Handles north-up rasters; rotated grids are rejected explicitly.
                if abs(clipped_transform.b) > 1e-12 or abs(clipped_transform.d) > 1e-12:
                    raise ValueError("Rotated population rasters are not supported.")
                from shapely.geometry import box
                cell_geom = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
                intersection = cell_geom.intersection(raster_boundary)
                if intersection.is_empty:
                    continue
                cell_equal = transform_geometry(to_equal_area, cell_geom)
                intersection_equal = transform_geometry(to_equal_area, intersection)
                cell_area = float(cell_equal.area)
                intersection_area = float(intersection_equal.area)
                if cell_area <= 0 or intersection_area <= 0:
                    continue
                fraction = min(1.0, max(0.0, intersection_area / cell_area))
                clipped_population = float(values[row, col]) * fraction
                if not math.isfinite(clipped_population) or clipped_population < 0:
                    raise ValueError("Computed population count is invalid.")
                output_geom = transform_geometry(to_wgs84, intersection)
                if output_geom.is_empty or not output_geom.is_valid:
                    raise ValueError("A clipped population cell produced invalid geometry.")
                cell_id = f"r{row:06d}_c{col:06d}"
                output_features.append({
                    "type": "Feature",
                    "id": cell_id,
                    "properties": {
                        "grid_id": cell_id,
                        "population": clipped_population,
                        "population_year": int(population_year),
                    },
                    "geometry": mapping(output_geom),
                })
                cell_geometries_equal.append(intersection_equal)

        covered_area = float(unary_union(cell_geometries_equal).area) if cell_geometries_equal else 0.0
        coverage_percent = min(100.0, max(0.0, 100.0 * covered_area / boundary_area))
        metadata = {
            "schema_version": "population-grid-preparation/1.0.0",
            "source_title": source_title,
            "source_url": source_url,
            "source_license": source_license,
            "population_year": int(population_year),
            "source_raster": str(Path(raster_path).name),
            "source_raster_crs": str(dataset.crs),
            "boundary_crs": boundary_crs,
            "output_crs": "EPSG:4326",
            "method": "Raster-cell polygonization with equal-area boundary-edge proration",
            "valid_source_cells_intersecting_boundary": len(output_features),
            "population_sum_after_boundary_proration": float(
                sum(item["properties"]["population"] for item in output_features)
            ),
            "boundary_coverage_percent": coverage_percent,
            "coverage_complete_at_99_5_percent": bool(coverage_percent >= 99.5),
            "no_data_cells_are_not_imputed": True,
            "interpretation": "GRID_ESTIMATE_NOT_VALIDATED",
            "limitations": [
                "Population is a gridded model estimate, not a household census count.",
                "Boundary-edge cells are prorated assuming uniform population within each source cell.",
                "NoData areas remain uncovered and are not imputed.",
                "The population reference year must not be interpreted as a current live count.",
                "Ward-level estimates require a separately validated ward boundary layer.",
            ],
        }

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    collection = {
        "type": "FeatureCollection",
        "name": output.stem,
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": output_features,
    }
    output.write_text(json.dumps(collection, allow_nan=False), encoding="utf-8")
    sidecar = output.with_suffix(".metadata.json")
    sidecar.write_text(json.dumps(metadata, indent=2, allow_nan=False), encoding="utf-8")
    return {"output": str(output), "metadata": str(sidecar), **metadata}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raster", required=True, help="Single-band population-count GeoTIFF.")
    parser.add_argument("--boundary", required=True, help="Boundary GeoJSON.")
    parser.add_argument("--boundary-crs", required=True, help="Explicit CRS of boundary GeoJSON.")
    parser.add_argument("--output", required=True, help="Output population-grid GeoJSON.")
    parser.add_argument("--population-year", type=int, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--source-title", required=True)
    parser.add_argument("--source-license", required=True)
    parser.add_argument("--max-features", type=int, default=250_000)
    args = parser.parse_args()
    result = prepare_population_grid(
        args.raster, args.boundary, args.output,
        boundary_crs=args.boundary_crs,
        population_year=args.population_year,
        source_url=args.source_url,
        source_title=args.source_title,
        source_license=args.source_license,
        max_features=args.max_features,
    )
    print(json.dumps({
        "output": result["output"],
        "metadata": result["metadata"],
        "valid_cells": result["valid_source_cells_intersecting_boundary"],
        "boundary_coverage_percent": result["boundary_coverage_percent"],
        "population_sum_after_boundary_proration": result["population_sum_after_boundary_proration"],
        "interpretation": result["interpretation"],
    }, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

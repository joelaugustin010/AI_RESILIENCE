"""Evidence-gated population exposure screening from polygon-grid population data.

This is a transparent areal-intersection screening method, not a casualty,
displacement, or operational forecast. Population is allocated uniformly within
each source grid cell; results must be labelled as approximate screening
estimates and must not be reported when source geometry/CRS or grid integrity
cannot be established.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Mapping

try:
    from pyproj import Transformer
    from shapely.geometry import shape
    from shapely.ops import transform, unary_union
    from shapely.strtree import STRtree
except ImportError:  # optional spatial stack
    Transformer = None
    shape = None
    transform = None
    unary_union = None
    STRtree = None


class PopulationExposureError(ValueError):
    """Raised when source geometry or population values cannot be used safely."""


def estimate_population_exposure(
    population_grid: Mapping[str, Any],
    hazard_footprint: Mapping[str, Any],
    *,
    population_field: str = "population",
    grid_id_field: str = "grid_id",
    ward_field: str | None = None,
    source_crs: str = "EPSG:4326",
    max_features: int = 250_000,
) -> dict[str, Any]:
    """Estimate population inside a hazard footprint using equal-area intersections.

    Both inputs must be GeoJSON FeatureCollections in the same declared CRS.
    Each population feature must be a non-overlapping polygon cell with a
    non-negative total population count. The function prorates each cell's
    population by the fraction of its area intersecting the hazard footprint.
    """
    if shape is None or Transformer is None or transform is None or unary_union is None or STRtree is None:
        raise PopulationExposureError(
            "Population exposure requires the optional shapely and pyproj packages."
        )
    if source_crs != "EPSG:4326":
        raise PopulationExposureError(
            "Only EPSG:4326 GeoJSON is currently accepted; reproject and document sources first."
        )
    for label, payload in (("population grid", population_grid), ("hazard footprint", hazard_footprint)):
        if not isinstance(payload, Mapping) or payload.get("type") != "FeatureCollection":
            raise PopulationExposureError(f"{label} must be a GeoJSON FeatureCollection.")
        features = payload.get("features")
        if not isinstance(features, list) or not features:
            raise PopulationExposureError(f"{label} contains no features.")
        if len(features) > max_features:
            raise PopulationExposureError(f"{label} exceeds the {max_features:,}-feature safety limit.")

    forward = Transformer.from_crs("EPSG:4326", "EPSG:6933", always_xy=True).transform
    hazard_geometries = []
    footprint_bounds = []
    for index, feature in enumerate(hazard_footprint["features"]):
        try:
            geom = shape(feature["geometry"])
        except Exception as exc:
            raise PopulationExposureError(f"Invalid hazard geometry at feature {index}: {exc}") from exc
        if geom.is_empty or not geom.is_valid or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise PopulationExposureError(f"Hazard feature {index} must be a valid polygon.")
        min_x, min_y, max_x, max_y = geom.bounds
        if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
            raise PopulationExposureError(f"Hazard feature {index} has coordinates outside EPSG:4326 bounds.")
        footprint_bounds.append((min_x, min_y, max_x, max_y))
        hazard_geometries.append(transform(forward, geom))
    hazard_union = unary_union(hazard_geometries)
    if hazard_union.is_empty or not hazard_union.is_valid:
        raise PopulationExposureError("Combined hazard footprint is empty or invalid.")

    cells = []
    seen_ids = set()
    for index, feature in enumerate(population_grid["features"]):
        props = feature.get("properties") or {}
        raw_population = props.get(population_field)
        try:
            population = float(raw_population)
        except (TypeError, ValueError):
            raise PopulationExposureError(
                f"Population feature {index} has no numeric {population_field!r} value."
            )
        if not math.isfinite(population) or population < 0:
            raise PopulationExposureError(
                f"Population feature {index} has a negative or non-finite population."
            )
        raw_id = props.get(grid_id_field, index)
        cell_id = str(raw_id)
        if cell_id in seen_ids:
            raise PopulationExposureError(f"Duplicate population grid identifier: {cell_id}")
        seen_ids.add(cell_id)
        try:
            geom = shape(feature["geometry"])
        except Exception as exc:
            raise PopulationExposureError(f"Invalid population geometry at feature {index}: {exc}") from exc
        if geom.is_empty or not geom.is_valid or geom.geom_type not in {"Polygon", "MultiPolygon"}:
            raise PopulationExposureError(f"Population feature {index} must be a valid polygon.")
        min_x, min_y, max_x, max_y = geom.bounds
        if min_x < -180 or max_x > 180 or min_y < -90 or max_y > 90:
            raise PopulationExposureError(f"Population feature {index} has coordinates outside EPSG:4326 bounds.")
        projected = transform(forward, geom)
        area = projected.area
        if not math.isfinite(area) or area <= 0:
            raise PopulationExposureError(f"Population feature {index} has invalid area.")
        cells.append((cell_id, props, population, projected, area))

    # Reject overlapping cells: otherwise the same residents could be counted
    # more than once. The conservative pairwise check is intentionally explicit.
    cell_geometries = [cell[3] for cell in cells]
    spatial_index = STRtree(cell_geometries)
    for index, (_, _, _, geom, _) in enumerate(cells):
        for candidate in spatial_index.query(geom):
            other_index = int(candidate)
            if other_index <= index:
                continue
            other = cell_geometries[other_index]
            if geom.intersection(other).area > max(1e-4, min(geom.area, other.area) * 1e-10):
                raise PopulationExposureError(
                    f"Population grid cells overlap ({cells[index][0]!r}, {cells[other_index][0]!r}); "
                    "deduplicate or repair the source grid before estimating."
                )

    total_population = 0.0
    exposed_population = 0.0
    exposed_cells = 0
    ward_totals: dict[str, float] = defaultdict(float)
    grid_union = unary_union(cell_geometries)
    hazard_area = hazard_union.area
    covered_hazard_area = hazard_union.intersection(grid_union).area
    coverage_percent = (
        100.0 * covered_hazard_area / hazard_area if hazard_area > 0 else 0.0
    )
    complete_coverage = coverage_percent >= 99.5
    for cell_id, props, population, geom, area in cells:
        total_population += population
        intersection_area = geom.intersection(hazard_union).area
        if intersection_area <= 0:
            continue
        fraction = min(1.0, max(0.0, intersection_area / area))
        estimate = population * fraction
        exposed_population += estimate
        exposed_cells += 1
        if ward_field and props.get(ward_field) not in (None, ""):
            ward_totals[str(props[ward_field])] += estimate

    return {
        "status": (
            "SCREENING_ESTIMATE_NOT_VALIDATED"
            if complete_coverage else "PARTIAL_POPULATION_GRID_COVERAGE"
        ),
        "estimated_population_in_footprint": round(exposed_population) if complete_coverage else None,
        "estimated_population_in_covered_part": round(exposed_population),
        "estimated_population_fractional": round(exposed_population, 2),
        "hazard_footprint_area_covered_percent": round(coverage_percent, 3),
        "population_grid_covers_full_footprint": complete_coverage,
        "footprint_bounds_wgs84": [
            min(item[0] for item in footprint_bounds),
            min(item[1] for item in footprint_bounds),
            max(item[2] for item in footprint_bounds),
            max(item[3] for item in footprint_bounds),
        ],
        "population_grid_total": round(total_population),
        "population_grid_cells": len(cells),
        "intersecting_population_cells": exposed_cells,
        "exposure_share_of_grid_percent": round(
            100.0 * exposed_population / total_population, 3
        ) if total_population else None,
        "ward_screening_estimates": [
            {"ward": ward, "estimated_population": round(value)}
            for ward, value in sorted(ward_totals.items(), key=lambda item: item[1], reverse=True)
        ],
        "method": (
            "Population is prorated by polygon-area intersection in EPSG:6933 "
            "equal-area projection, assuming uniform population within each cell."
        ),
        "limitations": [
            "This is approximate population presence inside a supplied footprint, not people harmed, displaced, injured or killed.",
            "The population grid and hazard footprint must be independently validated for date, coverage, CRS, resolution, licence and scientific fitness.",
            "Uniform within-cell population is an assumption; building-level distribution, time-of-day and mobility are not represented.",
            "Ward summaries are emitted only from a source-provided ward attribute; no ward identity is inferred.",
            "The function does not establish hazard probability, depth, duration, warning lead time or safety.",
        ],
        "causal_effect_estimated": False,
        "validated_exposure": False,
    }

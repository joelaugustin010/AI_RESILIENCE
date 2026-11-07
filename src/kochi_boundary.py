"""Display-only repair of provisional Kochi boundary geometry.

The source GeoJSON is never modified. A valid polygonal derivative may be used
for map orientation only; it is never returned as a coverage or exposure mask.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


class BoundaryDisplayError(ValueError):
    """Raised when no safe polygonal orientation geometry can be produced."""


def build_display_boundary(feature: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a valid display-only polygon derivative and a transparent QA report."""
    try:
        from shapely import make_valid
        from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, mapping, shape
        from shapely.ops import unary_union
    except ImportError as error:  # pragma: no cover - deployment dependency check
        raise BoundaryDisplayError(
            "Shapely 2.x is required to create a safe display-only boundary outline."
        ) from error

    geometry_data = feature.get("geometry")
    if not isinstance(geometry_data, dict):
        raise BoundaryDisplayError("The provisional boundary has no GeoJSON geometry.")
    try:
        source_geometry = shape(geometry_data)
    except Exception as error:
        raise BoundaryDisplayError(f"The provisional boundary geometry could not be parsed: {error}") from error

    source_valid = bool(source_geometry.is_valid)
    repaired = source_geometry if source_valid else make_valid(source_geometry)
    polygon_parts: list[Polygon] = []

    def collect(candidate: Any) -> None:
        if isinstance(candidate, Polygon):
            if not candidate.is_empty and candidate.area > 0:
                polygon_parts.append(candidate)
        elif isinstance(candidate, (MultiPolygon, GeometryCollection)):
            for child in candidate.geoms:
                collect(child)

    collect(repaired)
    if not polygon_parts:
        raise BoundaryDisplayError("Geometry repair produced no polygonal component to display.")

    display_geometry = unary_union(polygon_parts)
    if display_geometry.is_empty or not display_geometry.is_valid:
        raise BoundaryDisplayError("The derived orientation geometry did not pass Shapely validity checks.")
    if display_geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise BoundaryDisplayError(
            f"Geometry repair produced unsupported display type {display_geometry.geom_type!r}."
        )

    display_feature = deepcopy(feature)
    display_feature["geometry"] = mapping(display_geometry)
    properties = display_feature.get("properties")
    if not isinstance(properties, dict):
        properties = {}
        display_feature["properties"] = properties
    properties["display_geometry_status"] = (
        "SOURCE_GEOMETRY_VALID" if source_valid else "REPAIRED_DERIVATIVE_FOR_ORIENTATION_ONLY"
    )
    properties["display_geometry_is_analysis_eligible"] = False
    properties["display_geometry_note"] = (
        "Derived with Shapely make_valid from the unchanged provisional source. "
        "Orientation only; not a legal boundary, coverage mask, or exposure-analysis input."
    )

    min_x, min_y, max_x, max_y = display_geometry.bounds
    report = {
        "source_geometry_valid": source_valid,
        "display_geometry_valid": bool(display_geometry.is_valid),
        "display_geometry_type": display_geometry.geom_type,
        "polygon_component_count": len(polygon_parts),
        "discarded_non_polygon_components": (
            len(repaired.geoms) - len(polygon_parts)
            if isinstance(repaired, (MultiPolygon, GeometryCollection))
            else 0
        ),
        "bounds_wgs84": [float(min_x), float(min_y), float(max_x), float(max_y)],
        "analysis_eligible": False,
        "source_file_modified": False,
        "method": "Shapely make_valid; retain polygonal components; unary_union; display-only",
    }
    return display_feature, report

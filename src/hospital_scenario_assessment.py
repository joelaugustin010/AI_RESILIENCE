"""Reproducible, low-confidence hospital scenario screening from mapped context."""

from __future__ import annotations

import math
from typing import Any

from src.hospital_vulnerability import DISASTER_TYPES


_EARTH_RADIUS_M = 6_371_008.8
_ACCESS_COLORS = {
    "Likely Accessible": [40, 122, 69, 230],
    "At Risk of Disruption": [218, 145, 35, 235],
    "Likely Inaccessible": [177, 52, 48, 235],
    "Insufficient Information": [142, 148, 153, 210],
}


def _geometry_positions(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    positions: list[tuple[float, float]] = []

    def visit(value: Any) -> None:
        if isinstance(value, (list, tuple)) and len(value) >= 2 and not isinstance(value[0], (list, tuple)):
            try:
                longitude, latitude = float(value[0]), float(value[1])
            except (TypeError, ValueError):
                return
            if math.isfinite(longitude) and math.isfinite(latitude) and -180 <= longitude <= 180 and -90 <= latitude <= 90:
                positions.append((longitude, latitude))
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)

    visit(geometry.get("coordinates"))
    return positions


def _facility_point(feature: dict[str, Any]) -> tuple[float, float] | None:
    geometry = feature.get("geometry") or {}
    positions = _geometry_positions(geometry)
    if not positions:
        return None
    if geometry.get("type") == "Point":
        return positions[0]
    return (
        sum(point[0] for point in positions) / len(positions),
        sum(point[1] for point in positions) / len(positions),
    )


def _geometry_paths(geometry: dict[str, Any]) -> list[list[tuple[float, float]]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    raw_paths: list[Any]
    if geometry_type == "Point":
        raw_paths = [[coordinates]] if coordinates else []
    elif geometry_type == "LineString":
        raw_paths = [coordinates]
    elif geometry_type in {"MultiLineString", "Polygon"}:
        raw_paths = coordinates or []
    elif geometry_type == "MultiPolygon":
        raw_paths = [ring for polygon in (coordinates or []) for ring in polygon]
    else:
        raw_paths = []
    paths = []
    for raw_path in raw_paths:
        path = []
        for item in raw_path:
            if not isinstance(item, (list, tuple)) or len(item) < 2:
                continue
            try:
                longitude, latitude = float(item[0]), float(item[1])
            except (TypeError, ValueError):
                continue
            if math.isfinite(longitude) and math.isfinite(latitude) and -180 <= longitude <= 180 and -90 <= latitude <= 90:
                path.append((longitude, latitude))
        if path:
            paths.append(path)
    return paths


def _point_to_segment_distance_m(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> float:
    longitude, latitude = point
    latitude_scale = math.pi / 180 * _EARTH_RADIUS_M
    longitude_scale = latitude_scale * math.cos(math.radians(latitude))
    start_xy = ((start[0] - longitude) * longitude_scale, (start[1] - latitude) * latitude_scale)
    end_xy = ((end[0] - longitude) * longitude_scale, (end[1] - latitude) * latitude_scale)
    dx, dy = end_xy[0] - start_xy[0], end_xy[1] - start_xy[1]
    denominator = dx * dx + dy * dy
    fraction = 0.0 if denominator == 0 else max(
        0.0, min(1.0, -(start_xy[0] * dx + start_xy[1] * dy) / denominator)
    )
    return math.hypot(start_xy[0] + fraction * dx, start_xy[1] + fraction * dy)


def prepare_scenario_context(
    waterways: list[dict[str, Any]],
    industrial_features: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Pre-filter and index the OSM context features shared by many facilities."""
    water_context = []
    for feature in waterways:
        properties = feature.get("properties") or {}
        if str(properties.get("waterway", "")).casefold() not in {"river", "canal"}:
            continue
        paths = _geometry_paths(feature.get("geometry") or {})
        positions = [position for path in paths for position in path]
        if positions:
            water_context.append({
                "paths": paths,
                "bounds": (
                    min(point[0] for point in positions),
                    min(point[1] for point in positions),
                    max(point[0] for point in positions),
                    max(point[1] for point in positions),
                ),
                "name": str(properties.get("feature_name") or properties.get("name") or "Mapped river/canal"),
            })

    industry_context = []
    for feature in industrial_features:
        properties = feature.get("properties") or {}
        if not (
            str(properties.get("man_made", "")).casefold() == "works"
            or str(properties.get("landuse", "")).casefold() == "industrial"
            or bool(str(properties.get("industrial", "")).strip())
        ):
            continue
        paths = _geometry_paths(feature.get("geometry") or {})
        positions = [position for path in paths for position in path]
        if positions:
            industry_context.append({
                "paths": paths,
                "bounds": (
                    min(point[0] for point in positions),
                    min(point[1] for point in positions),
                    max(point[0] for point in positions),
                    max(point[1] for point in positions),
                ),
                "name": str(properties.get("feature_name") or properties.get("name") or "Mapped industrial candidate"),
            })
    return {"waterways": water_context, "industrial": industry_context}


def _nearest_context_feature(
    point: tuple[float, float],
    candidates: list[dict[str, Any]],
    radius_m: float,
) -> tuple[float, str] | None:
    longitude, latitude = point
    latitude_scale = math.pi / 180 * _EARTH_RADIUS_M
    longitude_scale = latitude_scale * math.cos(math.radians(latitude))
    closest: tuple[float, str] | None = None
    for candidate in candidates:
        west, south, east, north = candidate["bounds"]
        dx = max(west - longitude, longitude - east, 0.0) * longitude_scale
        dy = max(south - latitude, latitude - north, 0.0) * latitude_scale
        if math.hypot(dx, dy) > radius_m:
            continue
        distance = min(
            _point_to_segment_distance_m(point, start, end)
            for path in candidate["paths"]
            for start, end in (
                zip(path, path[1:]) if len(path) > 1 else [(path[0], path[0])]
            )
        )
        if distance <= radius_m and (closest is None or distance < closest[0]):
            closest = (distance, candidate["name"])
    return closest


def _facility_id(properties: dict[str, Any]) -> str:
    osm_type = str(properties.get("osm_type", "")).strip()
    osm_id = str(properties.get("osm_id", "")).strip()
    return f"{osm_type}/{osm_id}" if osm_type and osm_id else ""


def assess_hospital_scenario(
    feature: dict[str, Any],
    disaster_type: str,
    *,
    waterways: list[dict[str, Any]],
    industrial_features: list[dict[str, Any]],
    road_assessment: dict[str, Any] | None,
    prepared_context: dict[str, list[dict[str, Any]]] | None = None,
    verified_route_disruption: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Estimate scenario screening categories without representing them as observations.

    Flood and industrial screening uses proximity to mapped OSM context features.
    No source in the bundled data supports a closure or inundation prediction.
    """
    if disaster_type not in DISASTER_TYPES:
        raise ValueError(f"Unsupported disaster type: {disaster_type}")
    properties = feature.get("properties") or {}
    point = _facility_point(feature)
    context = prepared_context or prepare_scenario_context(waterways, industrial_features)
    has_location = point is not None
    facility_id = _facility_id(properties)
    road = road_assessment or {}
    road_linked = bool(facility_id and road.get("facility_id") == facility_id)
    accessibility_confidence = "Low"
    reasons: list[str] = []
    missing: list[str] = []
    exposure = "Unknown"
    vulnerability = "Unknown"
    vulnerability_reason = "Scenario-specific site hazard evidence is unavailable."
    exposure_distance_m: float | None = None
    exposure_feature = ""

    if not has_location:
        missing.append("Usable mapped facility geometry")

    if disaster_type == "Floods" and has_location:
        nearest = _nearest_context_feature(point, context["waterways"], 750)
        if nearest is None:
            if context["waterways"]:
                exposure = "No close mapped river/canal signal (over 750 m)"
                vulnerability = "Low"
                vulnerability_reason = (
                    "Low mapped-proximity screening tier only; it is not evidence that the site is flood-safe."
                )
                exposure_feature = "No mapped river/canal within 750 m"
            else:
                missing.append("Mapped river/canal context within the study layer")
        else:
            exposure_distance_m, exposure_feature = nearest
            if exposure_distance_m <= 100:
                exposure = "High mapped river/canal proximity"
                vulnerability = "Critical"
                vulnerability_reason = (
                    "Critical screening tier: hospital-tagged facility is within 100 m of a mapped river/canal; "
                    "structural resilience is unknown."
                )
            elif exposure_distance_m <= 250:
                exposure = "High mapped river/canal proximity"
                vulnerability = "High"
                vulnerability_reason = (
                    "High screening tier: mapped river/canal is within 250 m; this does not establish inundation "
                    "or building damage."
                )
            elif exposure_distance_m <= 750:
                exposure = "Moderate mapped river/canal proximity"
                vulnerability = "Moderate"
                vulnerability_reason = (
                    "Moderate screening tier: mapped river/canal is within 750 m; local flood depth and resilience "
                    "are unavailable."
                )
            else:
                exposure = "No close mapped river/canal signal (over 750 m)"
                vulnerability = "Low"
                vulnerability_reason = (
                    "Low mapped-proximity screening tier only; it is not evidence that the site is flood-safe."
                )
            reasons.append(
                f"Nearest mapped river/canal: {exposure_feature}, approximately {exposure_distance_m:.0f} m "
                "(provisional OSM geometry)."
            )
    elif disaster_type == "Industrial incidents" and has_location:
        nearest = _nearest_context_feature(point, context["industrial"], 1500)
        if nearest is None:
            if context["industrial"]:
                exposure = "No close mapped industrial candidate (over 1.5 km)"
                vulnerability = "Low"
                vulnerability_reason = (
                    "Industrial-site proximity screening only; the mapped feature is not a verified hazardous installation "
                    "or incident footprint, and structural/service resilience is unknown."
                )
                exposure_feature = "No mapped industrial candidate within 1.5 km"
            else:
                missing.append("Mapped industrial-site candidates")
        else:
            exposure_distance_m, exposure_feature = nearest
            if exposure_distance_m <= 100:
                exposure = "High proximity to mapped industrial candidate"
                vulnerability = "Critical"
            elif exposure_distance_m <= 500:
                exposure = "High proximity to mapped industrial candidate"
                vulnerability = "High"
            elif exposure_distance_m <= 1500:
                exposure = "Moderate proximity to mapped industrial candidate"
                vulnerability = "Moderate"
            else:
                exposure = "No close mapped industrial candidate (over 1.5 km)"
                vulnerability = "Low"
            vulnerability_reason = (
                "Industrial-site proximity screening only; the mapped feature is not a verified hazardous installation "
                "or incident footprint, and structural/service resilience is unknown."
            )
            reasons.append(
                f"Nearest mapped industrial candidate: {exposure_feature}, approximately {exposure_distance_m:.0f} m "
                "(provisional OSM context, not a hazard zone)."
            )
    else:
        missing.append({
            "Coastal flooding": "Coastal inundation/storm-surge geometry",
            "Cyclones": "Cyclone wind field, coastal exposure, or scenario-specific road impact",
            "Landslides": "Landslide susceptibility or event footprint",
            "Heatwaves": "Scenario-specific heat exposure and facility cooling/backup data",
        }.get(disaster_type, f"Eligible {disaster_type.lower()} hazard evidence"))

    if verified_route_disruption and (
        verified_route_disruption.get("scenario") == disaster_type
        and verified_route_disruption.get("evidence_status") == "verified"
        and verified_route_disruption.get("status") == "closed"
    ):
        accessibility = "Likely Inaccessible"
        accessibility_confidence = "High"
        reasons.append("A verified, scenario-matched route closure is recorded.")
    elif not road_linked:
        accessibility = "Insufficient Information"
        reasons.append("No matching hospital-to-road graph link; this may reflect incomplete map coverage.")
        missing.append("Hospital-specific link to the modeled road graph")
    elif exposure_distance_m is not None and exposure_distance_m <= (
        750 if disaster_type == "Floods" else 1500
    ):
        accessibility = "At Risk of Disruption"
        reasons.append(
            "Mapped hazard-context proximity raises a screening concern; no event depth, road crossing, or closure is known."
        )
    elif (
        disaster_type == "Floods" and bool(context["waterways"]) and vulnerability == "Low"
    ) or (
        disaster_type == "Industrial incidents" and bool(context["industrial"]) and vulnerability == "Low"
    ):
        accessibility = "Likely Accessible"
        reasons.append(
            "A local road-graph link exists and no close mapped scenario-context feature was found; route-wide impacts remain unassessed."
        )
    else:
        accessibility = "Insufficient Information"
        reasons.append(f"No supported {disaster_type.lower()} disruption evidence is available.")

    if accessibility == "Insufficient Information":
        accessibility_confidence = "Unknown"

    if vulnerability == "Unknown":
        missing.extend([
            "Building/structural resilience",
            "Backup power, water, supplies, and service-continuity information",
        ])
    else:
        missing.extend([
            "Building/structural resilience and floor elevation",
            "Backup power, water, supplies, and service-continuity information",
        ])

    return {
        "scenario": disaster_type,
        "accessibility": accessibility,
        "accessibility_confidence": accessibility_confidence,
        "accessibility_reasons": reasons,
        "vulnerability": vulnerability,
        "vulnerability_confidence": "Low" if vulnerability != "Unknown" else "Unknown",
        "vulnerability_reason": vulnerability_reason,
        "hazard_exposure": exposure,
        "exposure_distance_m": round(exposure_distance_m, 1) if exposure_distance_m is not None else None,
        "exposure_feature": exposure_feature,
        "road_linked": road_linked,
        "road_snap_distance_m": road.get("road_snap_distance_m"),
        "missing_information": list(dict.fromkeys(missing)),
        "method": (
            "Low-confidence geographic screening using distances to mapped river/canal lines (Floods) or "
            "mapped industrial candidates (Industrial incidents), plus presence of a hospital-to-road graph link. "
            "Bands: Flood vulnerability Critical <=100 m, High <=250 m, Moderate <=750 m, Low >750 m; "
            "industrial screening Critical <=100 m, High <=500 m, Moderate <=1,500 m, Low >1,500 m. "
            "Accessibility disruption screening radius: 750 m for mapped rivers/canals and 1,500 m for mapped industrial candidates. "
            "These are proximity heuristics, not hazard intensity or damage probabilities."
        ),
    }


def assess_hospital_operational_outlook(
    assessment: dict[str, Any],
    *,
    alternative_catchment_count: int = 0,
    recorded_services: str = "",
) -> dict[str, Any]:
    """Translate screening results into a non-live service-continuity outlook."""
    access = assessment["accessibility"]
    vulnerability = assessment["vulnerability"]
    if access == "Likely Inaccessible" or vulnerability in {"High", "Critical"}:
        condition = "High Risk of Service Disruption"
        action = "Prepare alternate routing and transfer contingencies; confirm status directly with the facility."
    elif access == "At Risk of Disruption" or vulnerability == "Moderate":
        condition = "Operational with Possible Disruption"
        action = "Verify access, backup arrangements, and service continuity before relying on this facility."
    elif access == "Likely Accessible" and vulnerability == "Low":
        condition = "Likely Operational"
        action = "Treat as a potential option only; confirm live operating status through official channels."
    else:
        condition = "Unknown"
        action = "Do not assume availability; obtain verified facility and route status from an authorized source."

    services = (
        f"Source-recorded services ({recorded_services}) could be affected; the directory tags do not confirm current provision."
        if recorded_services
        else "Facility-specific emergency/critical-care services are not documented in the mapped record."
    )
    alternative = (
        f"Mapped in the normal-condition network; {alternative_catchment_count} ward representative points "
        "fall within its modeled 15-minute catchment. Disaster-time alternative role is unverified."
        if alternative_catchment_count > 0
        else "No modeled ward-center catchment is recorded; do not infer that no real-world alternative exists."
    )
    return {
        "condition": condition,
        "access_maintained": access,
        "services": services,
        "alternative_role": alternative,
        "recommended_action": action,
        "live_status": "Not available; this is not a live operating or bed-capacity feed.",
    }


def scenario_map_properties(assessment: dict[str, Any]) -> dict[str, Any]:
    """Return display-ready map fields for a scenario assessment."""
    accessibility = assessment["accessibility"]
    return {
        "predicted_accessibility": accessibility,
        "predicted_vulnerability": assessment["vulnerability"],
        "predicted_exposure": assessment["hazard_exposure"],
        "predicted_operation": assessment.get("operation", "Unknown"),
        "prediction_confidence": assessment["accessibility_confidence"],
        "prediction_reasons": "; ".join(assessment["accessibility_reasons"]),
        "prediction_marker_color": _ACCESS_COLORS[accessibility],
        "predicted_vulnerability_reason": assessment["vulnerability_reason"],
        "predicted_missing_information": "; ".join(assessment["missing_information"]),
        "predicted_operational_action": assessment.get("operation_details", {}).get(
            "recommended_action", "Confirm directly with an authorized source."
        ),
    }

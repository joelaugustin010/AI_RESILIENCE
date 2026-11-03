"""Normal-condition, OSM-based hospital road-network access estimates."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree


_SPEED_KMH = {
    "trunk": 50.0,
    "primary": 40.0,
    "secondary": 35.0,
    "tertiary": 30.0,
    "unclassified": 25.0,
    "residential": 20.0,
    "living_street": 10.0,
}
_ROAD_SNAP_LIMIT_M = 750.0
_WARD_SNAP_LIMIT_M = 1500.0
_EARTH_RADIUS_M = 6_371_008.8


def _point_distance_m(first: tuple[float, float], second: tuple[float, float]) -> float:
    lon1, lat1 = map(math.radians, first)
    lon2, lat2 = map(math.radians, second)
    delta_lon, delta_lat = lon2 - lon1, lat2 - lat1
    value = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(value)))


def _coords(geometry: dict[str, Any]) -> list[tuple[float, float]]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point" and isinstance(coordinates, list) and len(coordinates) >= 2:
        return [(float(coordinates[0]), float(coordinates[1]))]
    if geometry_type == "Polygon" and coordinates and coordinates[0]:
        ring = coordinates[0]
        if len(ring) < 4:
            return []
        twice_area = 0.0
        x_sum = y_sum = 0.0
        for first, second in zip(ring, ring[1:]):
            cross = float(first[0]) * float(second[1]) - float(second[0]) * float(first[1])
            twice_area += cross
            x_sum += (float(first[0]) + float(second[0])) * cross
            y_sum += (float(first[1]) + float(second[1])) * cross
        if abs(twice_area) < 1e-15:
            return []
        return [(x_sum / (3 * twice_area), y_sum / (3 * twice_area))]
    return []


def _project(point: tuple[float, float], reference_latitude: float) -> tuple[float, float]:
    return (
        math.radians(point[0]) * _EARTH_RADIUS_M * math.cos(math.radians(reference_latitude)),
        math.radians(point[1]) * _EARTH_RADIUS_M,
    )


def _network(
    road_features: list[dict[str, Any]],
) -> tuple[list[tuple[float, float]], Any, Any]:
    node_ids: dict[tuple[float, float], int] = {}
    coordinates: list[tuple[float, float]] = []
    rows_distance: list[int] = []
    columns_distance: list[int] = []
    lengths: list[float] = []
    rows_time: list[int] = []
    columns_time: list[int] = []
    times: list[float] = []

    def node_id(point: object) -> int | None:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            return None
        try:
            longitude, latitude = float(point[0]), float(point[1])
        except (TypeError, ValueError):
            return None
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            return None
        key = (round(longitude, 7), round(latitude, 7))
        if key not in node_ids:
            node_ids[key] = len(coordinates)
            coordinates.append(key)
        return node_ids[key]

    def add_edge(start: int, end: int, length: float, speed: float) -> None:
        if length <= 0:
            return
        rows_distance.append(start)
        columns_distance.append(end)
        lengths.append(length)
        rows_time.append(start)
        columns_time.append(end)
        times.append(length / (speed / 3.6))

    for feature in road_features:
        geometry = feature.get("geometry", {})
        properties = feature.get("properties", {})
        if geometry.get("type") != "LineString":
            continue
        highway = str(properties.get("highway", "")).casefold()
        speed = _SPEED_KMH.get(highway)
        if speed is None:
            continue
        raw_points = geometry.get("coordinates", [])
        way_nodes = [node_id(point) for point in raw_points]
        one_way = str(properties.get("oneway", "")).strip().casefold()
        reverse_only = one_way == "-1"
        directed_one_way = one_way in {"yes", "true", "1", "-1"}
        for index, (first, second) in enumerate(zip(raw_points, raw_points[1:])):
            a, b = way_nodes[index], way_nodes[index + 1]
            if a is None or b is None or a == b:
                continue
            length = _point_distance_m(
                (float(first[0]), float(first[1])),
                (float(second[0]), float(second[1])),
            )
            if reverse_only:
                add_edge(b, a, length, speed)
            else:
                add_edge(a, b, length, speed)
            if not directed_one_way:
                add_edge(b, a, length, speed)

    size = len(coordinates)
    if not size or not lengths:
        return coordinates, None, None
    distance_graph = coo_matrix(
        (lengths, (rows_distance, columns_distance)),
        shape=(size, size),
        dtype=np.float64,
    ).tocsr()
    time_graph = coo_matrix(
        (times, (rows_time, columns_time)),
        shape=(size, size),
        dtype=np.float64,
    ).tocsr()
    return coordinates, distance_graph, time_graph


def _snap_points(
    points: list[tuple[float, float] | None],
    road_coordinates: list[tuple[float, float]],
    max_distance_m: float,
) -> tuple[list[int | None], list[float | None]]:
    if not road_coordinates:
        return [None] * len(points), [None] * len(points)
    reference_latitude = float(np.mean([point[1] for point in road_coordinates]))
    road_xy = np.asarray([_project(point, reference_latitude) for point in road_coordinates])
    tree = cKDTree(road_xy)
    snapped: list[int | None] = []
    distances: list[float | None] = []
    for point in points:
        if point is None:
            snapped.append(None)
            distances.append(None)
            continue
        _, index = tree.query(_project(point, reference_latitude), k=1)
        distance = _point_distance_m(point, road_coordinates[int(index)])
        if distance > max_distance_m:
            snapped.append(None)
            distances.append(distance)
        else:
            snapped.append(int(index))
            distances.append(distance)
    return snapped, distances


def _facility_records(
    facility_features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for feature in facility_features:
        properties = feature.get("properties", {})
        if str(properties.get("amenity", "")).casefold() != "hospital" and str(
            properties.get("healthcare", "")
        ).casefold() != "hospital":
            continue
        name = str(properties.get("name") or "").strip()
        osm_type = str(properties.get("osm_type", ""))
        osm_id = str(properties.get("osm_id", feature.get("id", "")))
        if not name or not osm_id or (osm_type, osm_id) in seen:
            continue
        point = _coords(feature.get("geometry", {}))
        if not point:
            continue
        seen.add((osm_type, osm_id))
        records.append({
            "facility_id": f"{osm_type}/{osm_id}",
            "name": name,
            "facility_type": str(
                properties.get("healthcare") or properties.get("amenity") or "Not stated"
            ),
            "location": str(
                properties.get("addr:suburb")
                or properties.get("addr:city")
                or properties.get("addr:district")
                or "Kochi urban map coverage; facility address not stated"
            ),
            "operator": str(properties.get("operator") or ""),
            "emergency_tag": str(properties.get("emergency") or ""),
            "beds_source_reported": str(properties.get("beds") or ""),
            "coordinate": point[0],
            "geometry_type": feature.get("geometry", {}).get("type"),
            "placement_method": str(properties.get("placement_method") or "OSM mapped geometry"),
            "source": "OpenStreetMap contributors",
        })
    return records


def _ward_records(ward_features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records = []
    for index, feature in enumerate(ward_features, start=1):
        centroid = _coords(feature.get("geometry", {}))
        if not centroid:
            continue
        properties = feature.get("properties", {})
        ward_no = str(properties.get("Ward_No") or "").strip()
        ward_name = str(properties.get("Ward_Name") or "").strip()
        label = " — ".join(part for part in (ward_no, ward_name) if part) or f"Ward feature {index}"
        records.append({"ward": label, "coordinate": centroid[0]})
    return records


def calculate_normal_condition_access(
    road_features: list[dict[str, Any]],
    hospital_features: list[dict[str, Any]],
    ward_features: list[dict[str, Any]],
    *,
    catchment_minutes: float = 15.0,
) -> dict[str, Any]:
    """Estimate ward-center routes to mapped hospitals on the OSM road graph.

    Travel times use class-based assumed driving speeds; they are not observed
    travel times. The analysis represents only the coverage of the supplied
    road/facility/ward layers, not a district-wide or disaster-time network.
    """
    if catchment_minutes <= 0:
        raise ValueError("catchment_minutes must be positive")
    road_coordinates, distance_graph, time_graph = _network(road_features)
    hospitals = _facility_records(hospital_features)
    wards = _ward_records(ward_features)
    empty = {
        "wards": pd.DataFrame(),
        "hospitals": pd.DataFrame(),
        "summary": {
            "road_nodes": len(road_coordinates),
            "road_segments": int(distance_graph.nnz) if distance_graph is not None else 0,
            "mapped_hospitals": len(hospitals),
            "routed_hospitals": 0,
            "wards": len(wards),
            "routed_wards": 0,
            "catchment_minutes": catchment_minutes,
        },
        "limitations": [
            "A routable OSM road graph or mapped hospitals are unavailable in this coverage."
        ],
    }
    if distance_graph is None or not hospitals or not wards:
        return empty

    hospital_nodes, hospital_snaps = _snap_points(
        [record["coordinate"] for record in hospitals],
        road_coordinates,
        _ROAD_SNAP_LIMIT_M,
    )
    ward_nodes, ward_snaps = _snap_points(
        [record["coordinate"] for record in wards],
        road_coordinates,
        _WARD_SNAP_LIMIT_M,
    )
    routed_hospitals = [
        (record, node, snap)
        for record, node, snap in zip(hospitals, hospital_nodes, hospital_snaps)
        if node is not None and snap is not None
    ]
    routed_wards = [
        (record, node, snap)
        for record, node, snap in zip(wards, ward_nodes, ward_snaps)
        if node is not None and snap is not None
    ]
    if not routed_hospitals or not routed_wards:
        empty["summary"].update({
            "routed_hospitals": len(routed_hospitals),
            "routed_wards": len(routed_wards),
        })
        empty["limitations"] = [
            "No hospital and ward representative-point pair could be snapped to the road network within documented snap limits."
        ]
        return empty

    ward_node_indices = [node for _, node, _ in routed_wards]
    distance_matrix = dijkstra(
        distance_graph,
        directed=True,
        indices=ward_node_indices,
        return_predecessors=False,
    )
    time_matrix = dijkstra(
        time_graph,
        directed=True,
        indices=ward_node_indices,
        return_predecessors=False,
    )
    if distance_matrix.ndim == 1:
        distance_matrix = distance_matrix.reshape(1, -1)
        time_matrix = time_matrix.reshape(1, -1)

    ward_rows: list[dict[str, Any]] = []
    hospital_coverage: dict[str, int] = {record["facility_id"]: 0 for record, _, _ in routed_hospitals}
    for row_index, (ward, _, snap) in enumerate(routed_wards):
        reachable = []
        for facility, node, _ in routed_hospitals:
            distance_m = float(distance_matrix[row_index, node])
            seconds = float(time_matrix[row_index, node])
            if math.isfinite(distance_m) and math.isfinite(seconds):
                reachable.append((seconds, distance_m, facility))
        reachable.sort(key=lambda result: (result[0], result[1], result[2]["name"].casefold()))
        if reachable:
            nearest_seconds, nearest_distance, nearest_hospital = reachable[0]
            for seconds, _, facility in reachable:
                if seconds <= catchment_minutes * 60:
                    hospital_coverage[facility["facility_id"]] += 1
            alternatives = [
                f"{facility['name']} ({distance / 1000:.1f} km; {seconds / 60:.1f} min)"
                for seconds, distance, facility in reachable[1:4]
            ]
            ward_rows.append({
                "ward": ward["ward"],
                "nearest_hospital": nearest_hospital["name"],
                "network_distance_km": round(nearest_distance / 1000, 2),
                "estimated_drive_minutes": round(nearest_seconds / 60, 1),
                "road_snap_distance_m": round(float(snap), 1),
                "hospitals_within_catchment": sum(
                    1 for seconds, _, _ in reachable if seconds <= catchment_minutes * 60
                ),
                "nearby_alternatives": "; ".join(alternatives),
                "coordinate_status": "OSM ward centroid; representative point, not population location",
            })
        else:
            ward_rows.append({
                "ward": ward["ward"],
                "nearest_hospital": "No connected mapped hospital",
                "network_distance_km": None,
                "estimated_drive_minutes": None,
                "road_snap_distance_m": round(float(snap), 1),
                "hospitals_within_catchment": 0,
                "nearby_alternatives": "",
                "coordinate_status": "OSM ward centroid; representative point, not population location",
            })

    hospital_rows = []
    for facility, _, snap in routed_hospitals:
        hospital_rows.append({
            **{
                key: facility[key]
                for key in (
                    "facility_id",
                    "name",
                    "facility_type",
                    "location",
                    "operator",
                    "emergency_tag",
                    "beds_source_reported",
                    "source",
                    "geometry_type",
                    "placement_method",
                )
            },
            "road_snap_distance_m": round(float(snap), 1),
            "ward_centers_within_catchment": hospital_coverage[facility["facility_id"]],
            "coordinate_status": "Community-mapped OSM location; not independently verified",
        })
    ward_frame = pd.DataFrame(ward_rows).sort_values(
        ["estimated_drive_minutes", "ward"], ascending=[False, True], na_position="first"
    ).reset_index(drop=True)
    hospital_frame = pd.DataFrame(hospital_rows).sort_values(
        ["ward_centers_within_catchment", "name"], ascending=[False, True]
    ).reset_index(drop=True)
    return {
        "wards": ward_frame,
        "hospitals": hospital_frame,
        "summary": {
            "road_nodes": len(road_coordinates),
            "road_segments": int(distance_graph.nnz),
            "mapped_hospitals": len(hospitals),
            "routed_hospitals": len(routed_hospitals),
            "wards": len(wards),
            "routed_wards": len(routed_wards),
            "connected_wards": int(ward_frame["estimated_drive_minutes"].notna().sum()),
            "catchment_minutes": catchment_minutes,
        },
        "limitations": [
            "OSM road and hospital features are community-mapped, provisional, and not independently ground-verified.",
            "Coverage is limited to the supplied Kochi urban road and 2022 ward layers; it is not Ernakulam-district coverage.",
            "Ward polygon centroids are unweighted representative points, not population-weighted origins.",
            "Drive times use assumed speeds by road class (trunk 50, primary 40, secondary 35, tertiary 30, unclassified 25, residential 20, living street 10 km/h); no observed traffic or turn penalties are modeled.",
            "No scenario-specific road closure or inundation data is available; these are normal-condition estimates and cannot classify disaster-time accessibility.",
        ],
    }

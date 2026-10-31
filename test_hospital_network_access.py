from pathlib import Path

import pytest

from src.hospital_network_access import calculate_normal_condition_access
from src.spatial_data import read_processed_layers


ROOT = Path(__file__).resolve().parent


def _road(coordinates, *, highway="residential", oneway="no"):
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {"highway": highway, "oneway": oneway},
    }


def _hospital(name, osm_id, coordinates):
    return {
        "type": "Feature",
        "id": osm_id,
        "geometry": {"type": "Point", "coordinates": coordinates},
        "properties": {
            "name": name,
            "amenity": "hospital",
            "osm_type": "node",
            "osm_id": osm_id,
            "source": "OpenStreetMap contributors",
        },
    }


def _ward(coordinates, *, ward_no="1", ward_name="Test ward"):
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [coordinates]},
        "properties": {"Ward_No": ward_no, "Ward_Name": ward_name},
    }


def test_network_routes_ranked_destinations_and_nearby_hospital_alternatives():
    roads = [_road([[76.0, 9.0], [76.001, 9.0], [76.002, 9.0]])]
    hospitals = [
        _hospital("Far Hospital", "2", [76.002, 9.0]),
        _hospital("Nearest Hospital", "1", [76.001, 9.0]),
    ]
    wards = [_ward([
        [75.9999, 8.9999],
        [76.0001, 8.9999],
        [76.0001, 9.0001],
        [75.9999, 9.0001],
        [75.9999, 8.9999],
    ])]

    result = calculate_normal_condition_access(roads, hospitals, wards)

    assert result["summary"]["routed_hospitals"] == 2
    assert result["summary"]["connected_wards"] == 1
    ward = result["wards"].iloc[0]
    assert ward["nearest_hospital"] == "Nearest Hospital"
    assert ward["network_distance_km"] == pytest.approx(0.11, abs=0.02)
    assert ward["estimated_drive_minutes"] > 0
    assert "Far Hospital" in ward["nearby_alternatives"]
    assert result["hospitals"]["ward_centers_within_catchment"].max() == 1


def test_one_way_roads_are_not_routed_against_their_direction():
    roads = [_road([[76.0, 9.0], [76.001, 9.0], [76.002, 9.0]], oneway="yes")]
    hospitals = [_hospital("Hospital", "1", [76.0, 9.0])]
    wards = [_ward([
        [76.0019, 8.9999],
        [76.0021, 8.9999],
        [76.0021, 9.0001],
        [76.0019, 9.0001],
        [76.0019, 8.9999],
    ])]

    result = calculate_normal_condition_access(roads, hospitals, wards)

    assert result["wards"].iloc[0]["nearest_hospital"] == "No connected mapped hospital"
    assert result["summary"]["connected_wards"] == 0


def test_non_hospital_and_unnamed_osm_features_are_not_hospital_destinations():
    roads = [_road([[76.0, 9.0], [76.001, 9.0]])]
    facilities = [
        _hospital("Named hospital", "1", [76.001, 9.0]),
        {
            **_hospital("Clinic", "2", [76.001, 9.0]),
            "properties": {"name": "Clinic", "amenity": "clinic", "osm_type": "node", "osm_id": "2"},
        },
        {
            **_hospital("Unnamed", "3", [76.001, 9.0]),
            "properties": {"amenity": "hospital", "osm_type": "node", "osm_id": "3"},
        },
    ]
    wards = [_ward([
        [75.9999, 8.9999],
        [76.0001, 8.9999],
        [76.0001, 9.0001],
        [75.9999, 9.0001],
        [75.9999, 8.9999],
    ])]

    result = calculate_normal_condition_access(roads, facilities, wards)

    assert result["summary"]["mapped_hospitals"] == 1
    assert result["hospitals"]["name"].tolist() == ["Named hospital"]


def test_bundled_road_and_hospital_layers_produce_routable_urban_results():
    layers = read_processed_layers(ROOT / "data" / "processed")
    by_id = {
        layer["metadata"].get("logical_layer_id")
        or layer["metadata"].get("dataset_id"): layer
        for layer in layers
    }

    result = calculate_normal_condition_access(
        by_id["osm_kochi_roads"]["features"],
        by_id["osm_kochi_healthcare"]["features"],
        by_id["kochi_wards_datameet_2022"]["features"],
    )

    assert result["summary"]["road_nodes"] > 50_000
    assert result["summary"]["mapped_hospitals"] > 300
    assert result["summary"]["routed_hospitals"] > 100
    assert result["summary"]["routed_wards"] > 60
    assert result["summary"]["connected_wards"] > 60
    assert result["wards"]["estimated_drive_minutes"].notna().any()
    assert result["hospitals"]["coordinate_status"].str.contains("not independently verified").all()
    assert any("normal-condition" in limitation for limitation in result["limitations"])


def test_catchment_window_must_be_positive():
    with pytest.raises(ValueError, match="catchment_minutes"):
        calculate_normal_condition_access([], [], [], catchment_minutes=0)

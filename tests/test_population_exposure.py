import pytest

pytest.importorskip("shapely")
pytest.importorskip("pyproj")

from src.population_exposure import PopulationExposureError, estimate_population_exposure


def feature(geometry, properties):
    return {"type": "Feature", "geometry": geometry, "properties": properties}


def polygon(x1, y1, x2, y2):
    return {
        "type": "Polygon",
        "coordinates": [[[x1, y1], [x2, y1], [x2, y2], [x1, y2], [x1, y1]]],
    }


def collection(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def test_population_is_prorated_by_equal_area_intersection_and_ward():
    grid = collection(
        feature(polygon(76.0, 9.0, 76.1, 9.1), {"grid_id": "a", "population": 100, "ward": "Ward A"}),
        feature(polygon(76.1, 9.0, 76.2, 9.1), {"grid_id": "b", "population": 200, "ward": "Ward B"}),
    )
    footprint = collection(feature(polygon(76.0, 9.0, 76.05, 9.1), {}))
    result = estimate_population_exposure(grid, footprint, ward_field="ward")
    assert result["status"] == "SCREENING_ESTIMATE_NOT_VALIDATED"
    assert 45 <= result["estimated_population_in_footprint"] <= 55
    assert result["intersecting_population_cells"] == 1
    assert result["ward_screening_estimates"][0]["ward"] == "Ward A"
    assert result["validated_exposure"] is False
    assert result["causal_effect_estimated"] is False
    assert result["population_grid_covers_full_footprint"] is True
    assert result["hazard_footprint_area_covered_percent"] == 100.0


def test_negative_population_is_rejected():
    grid = collection(feature(polygon(76, 9, 76.1, 9.1), {"population": -1}))
    footprint = collection(feature(polygon(76, 9, 76.1, 9.1), {}))
    with pytest.raises(PopulationExposureError, match="negative"):
        estimate_population_exposure(grid, footprint)


def test_overlapping_population_cells_are_rejected_to_prevent_double_counting():
    grid = collection(
        feature(polygon(76, 9, 76.1, 9.1), {"grid_id": "a", "population": 100}),
        feature(polygon(76.05, 9, 76.15, 9.1), {"grid_id": "b", "population": 100}),
    )
    footprint = collection(feature(polygon(76, 9, 76.15, 9.1), {}))
    with pytest.raises(PopulationExposureError, match="overlap"):
        estimate_population_exposure(grid, footprint)


def test_missing_or_invalid_geojson_is_rejected():
    with pytest.raises(PopulationExposureError, match="FeatureCollection"):
        estimate_population_exposure({}, collection(feature(polygon(76, 9, 76.1, 9.1), {})))



def test_partial_population_grid_coverage_withholds_total_exposure_estimate():
    grid = collection(feature(polygon(76, 9, 76.1, 9.1), {"grid_id": "a", "population": 100}))
    footprint = collection(feature(polygon(76, 9, 76.2, 9.1), {}))
    result = estimate_population_exposure(grid, footprint)
    assert result["population_grid_covers_full_footprint"] is False
    assert result["estimated_population_in_footprint"] is None
    assert result["estimated_population_in_covered_part"] > 0
    assert result["status"] == "PARTIAL_POPULATION_GRID_COVERAGE"


def test_out_of_range_coordinates_are_rejected():
    grid = collection(feature(polygon(190, 9, 191, 9.1), {"grid_id": "a", "population": 100}))
    footprint = collection(feature(polygon(190, 9, 191, 9.1), {}))
    with pytest.raises(PopulationExposureError, match="EPSG:4326 bounds"):
        estimate_population_exposure(grid, footprint)

import pytest

pytest.importorskip("shapely")
pytest.importorskip("pyproj")

from src.flood_footprint import FloodFootprintError, summarize_flood_depth_geojson


def polygon(x1, y1, x2, y2):
    return {"type": "Polygon", "coordinates": [[[x1,y1],[x2,y1],[x2,y2],[x1,y2],[x1,y1]]]}


def feature(geom, depth):
    return {"type": "Feature", "geometry": geom, "properties": {"depth_m": depth}}


def collection(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def test_summarizes_supplied_depth_layer_and_area_weighted_depth():
    data = collection(feature(polygon(76,9,76.01,9.01),0.2),
                      feature(polygon(76.01,9,76.02,9.01),0.8))
    result = summarize_flood_depth_geojson(data)
    assert result["status"] == "SUPPLIED_FLOOD_DEPTH_LAYER_SUMMARIZED_NOT_FORECAST"
    assert result["polygon_count"] == 2
    assert result["maximum_polygon_depth_m"] == 0.8
    assert result["area_weighted_mean_depth_m"] == pytest.approx(0.5, abs=0.01)
    assert result["flooded_extent_km2"] > 0


@pytest.mark.parametrize("depth", [-0.1, 0, float("nan"), 101, "unknown"])
def test_rejects_invalid_depth(depth):
    with pytest.raises(FloodFootprintError):
        summarize_flood_depth_geojson(collection(feature(polygon(76,9,76.01,9.01), depth)))


def test_rejects_overlapping_polygons():
    data = collection(feature(polygon(76,9,76.02,9.02),0.2),
                      feature(polygon(76.01,9,76.03,9.02),0.4))
    with pytest.raises(FloodFootprintError, match="overlap"):
        summarize_flood_depth_geojson(data)


def test_rejects_missing_depth_field():
    data = {"type":"FeatureCollection","features":[{"type":"Feature","geometry":polygon(76,9,76.01,9.01),"properties":{}}]}
    with pytest.raises(FloodFootprintError, match="depth_m"):
        summarize_flood_depth_geojson(data)

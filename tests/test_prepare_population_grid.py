"""Tests for provenance-aware population raster preparation."""
import json

import pytest

rasterio = pytest.importorskip("rasterio")
np = pytest.importorskip("numpy")
pytest.importorskip("shapely")
pytest.importorskip("pyproj")

from rasterio.transform import from_origin

from scripts.prepare_population_grid import prepare_population_grid


def test_population_raster_is_clipped_and_emits_provenance(tmp_path):
    raster_path = tmp_path / "population.tif"
    boundary_path = tmp_path / "boundary.geojson"
    output_path = tmp_path / "population_grid.geojson"

    values = np.asarray([[10, 20], [30, 40]], dtype="float32")
    with rasterio.open(
        raster_path,
        "w",
        driver="GTiff",
        height=2,
        width=2,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(0, 0.02, 0.01, 0.01),
        nodata=-9999,
    ) as dataset:
        dataset.write(values, 1)

    boundary_path.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.02, 0], [0.02, 0.02],
                                 [0, 0.02], [0, 0]]],
            },
        }],
    }), encoding="utf-8")

    result = prepare_population_grid(
        raster_path,
        boundary_path,
        output_path,
        boundary_crs="EPSG:4326",
        population_year=2025,
        source_url="https://example.org/population.tif",
        source_title="Test population raster",
        source_license="CC BY 4.0",
    )

    collection = json.loads(output_path.read_text(encoding="utf-8"))
    metadata = json.loads((tmp_path / "population_grid.metadata.json").read_text(encoding="utf-8"))
    assert len(collection["features"]) == 4
    assert sum(item["properties"]["population"] for item in collection["features"]) == pytest.approx(100)
    assert result["boundary_coverage_percent"] == pytest.approx(100, abs=0.01)
    assert metadata["population_year"] == 2025
    assert metadata["no_data_cells_are_not_imputed"] is True
    assert metadata["interpretation"] == "GRID_ESTIMATE_NOT_VALIDATED"


def test_population_raster_requires_https_source_reference(tmp_path):
    raster_path = tmp_path / "population.tif"
    boundary_path = tmp_path / "boundary.geojson"
    boundary_path.write_text(json.dumps({
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match="HTTPS"):
        prepare_population_grid(
            raster_path,
            boundary_path,
            tmp_path / "out.geojson",
            boundary_crs="EPSG:4326",
            population_year=2025,
            source_url="http://example.org/population.tif",
            source_title="Test",
            source_license="CC BY 4.0",
        )

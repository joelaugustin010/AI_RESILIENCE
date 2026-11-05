"""Tests for modelled flood-depth screening at provisional asset locations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.exposure_assessment import (
    ASSET_LAYERS,
    STATUS_INVALID,
    STATUS_NODATA,
    STATUS_OUTSIDE,
    STATUS_PERMANENT_WATER,
    STATUS_POSITIVE,
    STATUS_ZERO,
    assess_assets,
    build_report,
    classify_screening,
    extent_statistics,
    load_asset_features,
    representative_point,
    sample_feature,
    summarize_layer,
    tile_contains,
)
from src.flood_raster import JrcDepthTile, JrcPermanentWaterTile


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"
SPATIAL = ROOT / "data" / "processed" / "spatial_layers"
DEPTH_TILES = (
    RAW / "jrc_glofas_rp100_ID185_N20_E70_depth.tif",
    RAW / "jrc_glofas_rp100_ID186_N10_E70_depth.tif",
)
WATER_TILES = (
    RAW / "ID185_N20_E70_permanent_water.tif",
    RAW / "ID186_N10_E70_permanent_water.tif",
)
METADATA = SPATIAL / "jrc_glofas_rp100_kochi_preview.metadata.json"


def _real_inputs_available() -> bool:
    return all(path.is_file() for path in (*DEPTH_TILES, *WATER_TILES, METADATA))


class TestRepresentativePoint:
    def test_point_geometry_returns_its_coordinates(self):
        geometry = {"type": "Point", "coordinates": [76.27, 9.96]}
        assert representative_point(geometry) == (76.27, 9.96)

    def test_polygon_returns_bounding_box_centre(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[76.20, 9.90], [76.30, 9.90], [76.30, 10.00], [76.20, 10.00], [76.20, 9.90]]],
        }
        lon, lat = representative_point(geometry)
        assert lon == pytest.approx(76.25)
        assert lat == pytest.approx(9.95)

    def test_line_and_collection_are_supported(self):
        geometry = {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "LineString", "coordinates": [[76.20, 9.90], [76.30, 10.00]]},
                {"type": "Point", "coordinates": [76.10, 9.80]},
            ],
        }
        assert representative_point(geometry) == (pytest.approx(76.20), pytest.approx(9.90))

    def test_empty_or_invalid_geometry_returns_none(self):
        assert representative_point(None) is None
        assert representative_point({"type": "Point", "coordinates": []}) is None
        assert representative_point({"type": "Point", "coordinates": [999, 9.9]}) is None


class TestScreeningClassification:
    def test_positive_zero_nodata_outside_and_permanent_water(self):
        assert classify_screening(1.2, True) == STATUS_POSITIVE
        assert classify_screening(0.0, True) == STATUS_ZERO
        assert classify_screening(None, True) == STATUS_NODATA
        assert classify_screening(None, False) == STATUS_OUTSIDE
        assert classify_screening(3.0, True, permanent_water=1) == STATUS_PERMANENT_WATER
        assert classify_screening(3.0, True, permanent_water=0) == STATUS_POSITIVE

    def test_summary_excludes_permanent_water_from_positive_counts(self):
        rows = [
            {"status": STATUS_POSITIVE, "depth_m": 1.0},
            {"status": STATUS_POSITIVE, "depth_m": 3.0},
            {"status": STATUS_PERMANENT_WATER, "depth_m": 5.0},
            {"status": STATUS_NODATA, "depth_m": None},
            {"status": STATUS_OUTSIDE, "depth_m": None},
            {"status": STATUS_INVALID, "depth_m": None},
        ]
        summary = summarize_layer(rows)
        assert summary["positive_modelled_depth"] == 2
        assert summary["permanent_water_cells"] == 1
        assert summary["features_sampled_in_coverage"] == 3
        assert summary["positive_depth_median_m"] == 2.0
        assert "PROVISIONAL SCREENING ONLY" in summary["status"]


class TestRealRasterScreening:
    @pytest.mark.skipif(not _real_inputs_available(), reason="JRC raster inputs not present")
    def test_permanent_water_tile_reads_uint8_mask(self):
        tile = JrcPermanentWaterTile(WATER_TILES[1])
        assert tile.nodata == 255
        # A point in the Kochi backwater network should resolve to a value or NoData,
        # never raise; the exact cell is not asserted.
        assert tile.sample(76.28, 9.97) in (0, 1, None)

    @pytest.mark.skipif(not _real_inputs_available(), reason="JRC raster inputs not present")
    def test_build_report_is_provisional_and_excludes_permanent_water(self):
        metadata = json.loads(METADATA.read_text(encoding="utf-8"))
        bounds = metadata["processing"]["bounds_epsg4326"]
        report = build_report(SPATIAL, DEPTH_TILES, bounds, WATER_TILES)
        aggregate = report["aggregate"]
        assert aggregate["features_total"] > 1000
        assert aggregate["positive_modelled_depth"] > 0
        assert aggregate["permanent_water_cells"] > 0
        assert "PROVISIONAL SCREENING ONLY" in aggregate["status"]
        assert report["extent"]["positive_depth_cells"] > 0
        assert report["extent"]["permanent_water_cells_excluded"] > 0
        assert report["extent"]["positive_depth_area_km2"] < report["extent"]["valid_area_km2"]
        assert "ODbL" in report["licence"]
        assert any("not observed" in item for item in report["limitations"])
        assert all(layer["status"].startswith("PROVISIONAL") for layer in report["layers"])

    @pytest.mark.skipif(not _real_inputs_available(), reason="JRC raster inputs not present")
    def test_real_asset_layer_loads_with_representative_points(self):
        layer = next(item for item in ASSET_LAYERS if item["layer_id"] == "osm_kochi_emergency")
        features = load_asset_features(SPATIAL / layer["file"], layer)
        assert features
        assert all(feature["longitude"] is not None for feature in features)
        assert all(feature["latitude"] is not None for feature in features)
        tiles = [JrcDepthTile(path) for path in DEPTH_TILES]
        water = [JrcPermanentWaterTile(path) for path in WATER_TILES]
        rows = [sample_feature(feature, tiles, water) for feature in features]
        assert {row["status"] for row in rows} <= {
            STATUS_POSITIVE,
            STATUS_ZERO,
            STATUS_NODATA,
            STATUS_OUTSIDE,
            STATUS_INVALID,
            STATUS_PERMANENT_WATER,
        }


class TestTileContainment:
    def test_bounds_check_matches_source_extent(self):
        if not DEPTH_TILES[1].is_file():
            pytest.skip("JRC raster inputs not present")
        tile = JrcDepthTile(DEPTH_TILES[1])
        assert tile_contains(tile, 76.28, 9.97)
        assert not tile_contains(tile, 76.28, 10.5)
        assert not tile_contains(tile, 60.0, 9.97)

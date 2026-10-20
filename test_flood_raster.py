"""Tests for the real JRC raster metadata and fail-closed depth-sample labels."""

import hashlib
import json
import unittest
from pathlib import Path

from PIL import Image
from src.flood_raster import FloodRasterError, JrcDepthTile, classify_depth_sample


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data" / "raw"


class JrcRasterSourceTests(unittest.TestCase):
    def test_downloaded_kochi_tiles_have_expected_schema_and_hashes(self):
        expected = {
            "jrc_glofas_rp100_ID185_N20_E70_depth.tif": "93ba198ffeb0fb7436c6b97d66cf6b47b10cd59c4e6cf742a8aff59f46bdaf3b",
            "jrc_glofas_rp100_ID186_N10_E70_depth.tif": "cd78d43b91c235e39aa443550319ab099b816ca679f76ab83c339b5e7a9f1a30",
        }
        for name, digest in expected.items():
            path = RAW / name
            tile = JrcDepthTile(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            self.assertEqual((tile.width, tile.height, tile.mode), (11999, 11999, "F"))
            self.assertEqual(tile.nodata, -9999.0)
            self.assertAlmostEqual(tile.pixel_x * 3600, 3.0, places=4)
            self.assertAlmostEqual(tile.pixel_y * 3600, 3.0, places=4)

    def test_real_tile_sampling_distinguishes_positive_depth_nodata_and_outside(self):
        tile = JrcDepthTile(RAW / "jrc_glofas_rp100_ID186_N10_E70_depth.tif")
        self.assertGreater(tile.sample(76.33, 9.9), 0.0)
        self.assertIsNone(tile.sample(76.25, 9.95))
        self.assertIsNone(tile.sample(80.1, 9.9))

    def test_processed_preview_and_source_provenance_are_pinned(self):
        output = ROOT / "data" / "processed" / "spatial_layers" / "jrc_glofas_rp100_kochi_preview.png"
        metadata_path = output.with_name("jrc_glofas_rp100_kochi_preview.metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(), metadata["processing"]["preview_sha256"])
        self.assertEqual(metadata["license"].split(";")[0], "Free and open Copernicus product")
        self.assertEqual(len(metadata["source_files"]), 2)
        with Image.open(output) as preview:
            self.assertEqual(preview.mode, "RGBA")
            self.assertEqual(preview.size, (520, 520))
        catalog = json.loads((ROOT / "data" / "reference" / "spatial_sources.json").read_text(encoding="utf-8"))
        entry = next(item for item in catalog["datasets"] if item["layer_id"] == "flood_hazard_jrc_glofas_rp100")
        self.assertIn("assets_unavailable", entry["status"])

    def test_missing_or_unreadable_raster_fails_clearly(self):
        with self.assertRaises(FloodRasterError):
            JrcDepthTile(ROOT / "missing_raster.tif")
        with self.assertRaises(FloodRasterError):
            JrcDepthTile(ROOT / "test_flood_raster.py")


class RasterExposureLabelTests(unittest.TestCase):
    def test_unvalidated_asset_coordinates_always_mean_unknown(self):
        result = classify_depth_sample(2.0, within_coverage=True, coordinates_validated=False)
        self.assertEqual(result["status"], "unknown / unassessable")
        self.assertIsNone(result["depth_m"])

    def test_positive_depth_is_a_cell_sample_not_damage(self):
        result = classify_depth_sample(1.2, within_coverage=True, coordinates_validated=True)
        self.assertEqual(result["status"], "positive modeled depth cell")
        self.assertIn("not proof of damage", result["reason"])

    def test_zero_and_missing_coverage_are_not_safety_claims(self):
        zero = classify_depth_sample(0.0, within_coverage=True, coordinates_validated=True)
        missing = classify_depth_sample(None, within_coverage=False, coordinates_validated=True)
        self.assertEqual(zero["status"], "no positive depth detected in sampled cell")
        self.assertIn("does not establish safety", zero["reason"])
        self.assertEqual(missing["status"], "unknown / unassessable")

    def test_invalid_depth_is_unknown(self):
        result = classify_depth_sample(-2.0, within_coverage=True, coordinates_validated=True)
        self.assertEqual(result["status"], "unknown / unassessable")


if __name__ == "__main__":
    unittest.main()

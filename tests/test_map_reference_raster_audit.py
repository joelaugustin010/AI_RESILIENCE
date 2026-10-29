"""Tests for the raster metadata audit using synthetic rasters only."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

try:
    import rasterio
    from rasterio.transform import from_origin
except ImportError:
    rasterio = None

from scripts import audit_map_reference_raster as audit


@unittest.skipIf(rasterio is None, "rasterio is installed in the spatial acquisition workflow")
class RasterMetadataAuditTests(unittest.TestCase):
    def test_transforms_projected_bounds_and_reports_kochi_screening_overlap(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tif = root / "candidate.tif"
            archive = root / "candidate.zip"
            with rasterio.open(
                tif,
                "w",
                driver="GTiff",
                height=40,
                width=40,
                count=1,
                dtype="uint8",
                crs="EPSG:32643",
                transform=from_origin(620000, 1120000, 1000, 1000),
                nodata=0,
            ) as dataset:
                import numpy as np
                dataset.write(np.ones((1, 40, 40), dtype="uint8"))

            with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
                zipped.write(tif, arcname="candidate.tif")

            report = audit.inspect_archive(archive)
            self.assertEqual(report["status"], "METADATA_READ_NOT_APPROVED_FOR_MAP")
            raster = report["rasters"][0]
            self.assertEqual(raster["crs_epsg"], 32643)
            self.assertIsNotNone(raster["bounds_epsg4326"])
            self.assertTrue(raster["kochi_screening_box_overlap"])
            self.assertEqual(report["approval"], "NOT_APPROVED_FOR_MAP_OR_EXPOSURE_ANALYSIS")

    def test_rejects_missing_or_invalid_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "Missing or invalid raster ZIP"):
                audit.inspect_archive(Path(folder) / "missing.zip")


if __name__ == "__main__":
    unittest.main()

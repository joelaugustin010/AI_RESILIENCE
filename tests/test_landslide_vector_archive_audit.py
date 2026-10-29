"""Tests for GSI landslide vector archive audit using synthetic shapefile fixtures."""
from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

import shapefile
from pyproj import CRS

from scripts.audit_landslide_vector_archive import inspect_archive


class LandslideVectorArchiveAuditTests(unittest.TestCase):
    def _make_archive(self, folder: Path, include_prj: bool = True, invalid: bool = False) -> Path:
        shp_path = folder / "synthetic_susceptibility.shp"
        writer = shapefile.Writer(str(shp_path), shapeType=shapefile.POLYGON)
        writer.field("SUSC_CLASS", "C")
        writer.field("OBJECTID", "N")
        if invalid:
            coords = [[76.2, 9.8], [76.4, 10.0], [76.4, 9.8], [76.2, 10.0], [76.2, 9.8]]
        else:
            coords = [[76.2, 9.8], [76.4, 9.8], [76.4, 10.0], [76.2, 10.0], [76.2, 9.8]]
        writer.poly([coords])
        writer.record("High", 1)
        writer.close()
        if include_prj:
            shp_path.with_suffix(".prj").write_text(CRS.from_epsg(4326).to_wkt(), encoding="utf-8")
        archive_path = folder / "synthetic_susceptibility.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in folder.iterdir():
                if path.suffix.lower() in {".shp", ".shx", ".dbf", ".prj"}:
                    archive.write(path, arcname=path.name)
        return archive_path

    def test_reads_fields_crs_and_bounding_box_without_approving_layer(self):
        with tempfile.TemporaryDirectory() as folder:
            report = inspect_archive(self._make_archive(Path(folder)))
            layer = report["layers"][0]
            self.assertEqual(report["status"], "METADATA_READ_NOT_APPROVED_FOR_LANDSLIDE_PREDICTION")
            self.assertEqual(layer["feature_count"], 1)
            self.assertEqual(layer["crs_epsg"], 4326)
            self.assertTrue(layer["kochi_screening_bbox_overlap"])
            self.assertEqual(layer["invalid_geometry_count"], 0)
            self.assertEqual(layer["candidate_class_field_values"]["SUSC_CLASS"], ["High"])
            self.assertEqual(layer["status"], "METADATA_READ_NOT_SCIENTIFICALLY_VALIDATED")

    def test_missing_prj_does_not_guess_crs_or_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            layer = inspect_archive(self._make_archive(Path(folder), include_prj=False))["layers"][0]
            self.assertIsNone(layer["crs"])
            self.assertIsNone(layer["bounds_epsg4326"])
            self.assertIsNone(layer["kochi_screening_bbox_overlap"])

    def test_invalid_geometry_is_reported_not_repaired(self):
        with tempfile.TemporaryDirectory() as folder:
            layer = inspect_archive(self._make_archive(Path(folder), invalid=True))["layers"][0]
            self.assertEqual(layer["invalid_geometry_count"], 1)
            self.assertIn("Self-intersection", layer["invalid_features"][0]["reason"])
            self.assertEqual(layer["feature_count"], 1)

    def test_rejects_invalid_zip_and_zip_without_shapefile(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            invalid = root / "invalid.zip"
            invalid.write_text("not a zip", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Missing or invalid landslide vector ZIP"):
                inspect_archive(invalid)
            empty = root / "empty.zip"
            with zipfile.ZipFile(empty, "w") as archive:
                archive.writestr("readme.txt", "no GIS data")
            with self.assertRaisesRegex(RuntimeError, "contains no shapefile"):
                inspect_archive(empty)


if __name__ == "__main__":
    unittest.main()

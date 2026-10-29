"""Tests for candidate spatial-data acquisition; all network responses are mocked."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import acquire_map_reference_data as acquisition


class FakeResponse:
    def __init__(self, body: bytes, content_type: str):
        self.body = body
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body

    def geturl(self):
        return "https://example.org/final"


class MapReferenceAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.output = Path(self.temp.name) / "out"

    def tearDown(self):
        self.temp.cleanup()

    @patch.object(acquisition, "fetch")
    def test_downloads_candidates_with_provenance_but_does_not_approve_them(self, mocked_fetch):
        hospitals = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"state_name": "Kerala", "district_name": "Ernakulam", "health_facility_name": "Test Hospital"},
                "geometry": {"type": "Point", "coordinates": [76.3, 9.9]},
            }],
        }
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as archive:
            archive.writestr("candidate.tif", b"not a real raster; archive integrity only")
        mocked_fetch.side_effect = [
            (json.dumps(hospitals).encode(), "https://example.org/hospitals", "application/geo+json"),
            (memory.getvalue(), "https://example.org/flood.zip", "application/zip"),
        ]

        manifest = acquisition.acquire(self.output)
        self.assertEqual(manifest["overall_status"], "RAW_CANDIDATES_NOT_APPROVED_FOR_MAP")
        self.assertEqual(len(manifest["files"]), 2)
        self.assertTrue((self.output / "hospital_directory_ernakulam.geojson").exists())
        self.assertTrue((self.output / "ksdma_flood_return_probability_historical_10_25_50.zip").exists())
        stored = json.loads((self.output / "map_reference_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["files"][0]["feature_count"], 1)
        self.assertEqual(stored["files"][0]["validation_status"], "STRUCTURE_CHECKED_SPATIAL_ACCURACY_AND_LICENCE_UNVERIFIED")
        self.assertEqual(stored["files"][1]["validation_status"], "ZIP_INTEGRITY_CHECKED_RASTER_SEMANTICS_UNVERIFIED")
        self.assertTrue(all(item["sha256"] for item in stored["files"]))

    @patch.object(acquisition, "fetch")
    def test_rejects_html_instead_of_flood_zip(self, mocked_fetch):
        hospitals = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature", "properties": {"state_name": "Kerala", "district_name": "Ernakulam", "health_facility_name": "Test Hospital"},
                "geometry": {"type": "Point", "coordinates": [76.3, 9.9]},
            }],
        }
        mocked_fetch.side_effect = [
            (json.dumps(hospitals).encode(), "https://example.org/hospitals", "application/geo+json"),
            (b"<html>error</html>", "https://example.org/error", "text/html"),
        ]
        with self.assertRaisesRegex(RuntimeError, "One or more map reference downloads failed"):
            acquisition.acquire(self.output)
        manifest = json.loads((self.output / "map_reference_manifest.json").read_text(encoding="utf-8"))
        self.assertIn("not a ZIP archive", manifest["files"][1]["error"])
        self.assertEqual(manifest["overall_status"], "PARTIAL_ACQUISITION_FAILED")
        self.assertFalse((self.output / "ksdma_flood_return_probability_historical_10_25_50.zip").exists())

    @patch.object(acquisition, "fetch")
    def test_partial_failure_preserves_manifest_for_both_sources(self, mocked_fetch):
        hospitals = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"state_name": "Kerala", "district_name": "Ernakulam", "health_facility_name": "Test Hospital"},
                "geometry": {"type": "Point", "coordinates": [76.3, 9.9]},
            }],
        }
        mocked_fetch.side_effect = [
            (json.dumps(hospitals).encode(), "https://example.org/hospitals", "application/geo+json"),
            (b"<html>download failed</html>", "https://example.org/error", "text/html"),
        ]
        with self.assertRaisesRegex(RuntimeError, "Partial provenance manifest saved"):
            acquisition.acquire(self.output)
        manifest_path = self.output / "map_reference_manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["overall_status"], "PARTIAL_ACQUISITION_FAILED")
        self.assertEqual(len(manifest["files"]), 2)
        self.assertEqual(manifest["files"][0]["status"], "DOWNLOADED_RAW_CANDIDATE")
        self.assertEqual(manifest["files"][1]["status"], "ACQUISITION_FAILED")
        self.assertTrue(manifest["files"][0]["sha256"])
        self.assertIn("not a ZIP archive", manifest["files"][1]["error"])

    @patch.object(acquisition, "fetch")
    def test_counts_invalid_points_and_filter_mismatches(self, mocked_fetch):
        hospitals = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"state_name": "Tamil Nadu", "district_name": "Other"},
                    "geometry": {"type": "Point", "coordinates": [999, 9.9]},
                },
                {
                    "type": "Feature",
                    "properties": {"state_name": "Tamil Nadu", "district_name": "Other", "health_facility_name": "Out-of-area test"},
                    "geometry": {"type": "Point", "coordinates": [99, 9.9]},
                },
            ],
        }
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as archive:
            archive.writestr("candidate.tif", b"placeholder")
        mocked_fetch.side_effect = [
            (json.dumps(hospitals).encode(), "https://example.org/hospitals", "application/geo+json"),
            (memory.getvalue(), "https://example.org/flood.zip", "application/zip"),
        ]
        manifest = acquisition.acquire(self.output)
        record = manifest["files"][0]
        self.assertEqual(record["invalid_point_count"], 1)
        self.assertEqual(record["district_filter_mismatch_count"], 1)
        self.assertEqual(record["outside_kerala_screening_box_count"], 1)
        self.assertEqual(record["missing_facility_name_count"], 1)
        self.assertEqual(record["validation_status"], "STRUCTURE_CHECKED_WITH_SPATIAL_QA_FLAGS")
        self.assertEqual(manifest["overall_status"], "RAW_CANDIDATES_NOT_APPROVED_FOR_MAP")


if __name__ == "__main__":
    unittest.main()

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

BOUNDARY = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"ward": "Test Ward A"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[76.2, 9.8], [76.4, 9.8], [76.4, 10.0], [76.2, 10.0], [76.2, 9.8]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"ward": "Test Ward B"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[76.5, 9.8], [76.6, 9.8], [76.6, 10.0], [76.5, 10.0], [76.5, 9.8]]],
            },
        },
    ],
}


def make_landslide_zip() -> bytes:
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w") as archive:
        archive.writestr("Ernakulam_Susceptibility.shp", b"placeholder-shp")
        archive.writestr("Ernakulam_Susceptibility.shx", b"placeholder-shx")
        archive.writestr("Ernakulam_Susceptibility.dbf", b"placeholder-dbf")
        archive.writestr("Ernakulam_Susceptibility.prj", b"placeholder-prj")
    return memory.getvalue()


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
                "properties": {"statename": "Kerala", "districtname": "Ernakulam", "facilityname": "Test Hospital", "facilityaddress": "Kochi", "facilitytype": "District Hospital"},
                "geometry": {"type": "Point", "coordinates": [76.3, 9.9]},
            }],
        }
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as archive:
            archive.writestr("candidate.tif", b"not a real raster; archive integrity only")
        mocked_fetch.side_effect = [
            (json.dumps({"objectIds": [1]}).encode(), "https://example.org/ids", "application/json"),
            (json.dumps(hospitals).encode(), "https://example.org/hospitals", "application/geo+json"),
            (memory.getvalue(), "https://example.org/flood.zip", "application/zip"),
            (make_landslide_zip(), "https://example.org/landslide.zip", "application/zip"),
            (b"%PDF-1.4\\nmock official institution list", "https://example.org/institutions.pdf", "application/pdf"),
            (json.dumps(BOUNDARY).encode(), "https://example.org/boundary.geojson", "application/geo+json"),
        ]

        manifest = acquisition.acquire(self.output)
        self.assertEqual(manifest["overall_status"], "RAW_CANDIDATES_NOT_APPROVED_FOR_MAP")
        self.assertEqual(len(manifest["files"]), 5)
        self.assertTrue((self.output / "health_facilities_ernakulam.geojson").exists())
        self.assertTrue((self.output / "ksdma_flood_return_probability_historical_10_25_50.zip").exists())
        self.assertTrue((self.output / "gsi_landslide_susceptibility_ernakulam.zip").exists())
        self.assertTrue((self.output / "kerala_health_department_institutions_2024_25.pdf").exists())
        self.assertTrue((self.output / "kochi_corporation_boundary_candidate.geojson").exists())
        stored = json.loads((self.output / "map_reference_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["files"][0]["feature_count"], 1)
        self.assertEqual(stored["files"][0]["validation_status"], "STRUCTURE_CHECKED_SPATIAL_ACCURACY_AND_LICENCE_UNVERIFIED")
        self.assertEqual(stored["files"][1]["validation_status"], "ZIP_INTEGRITY_CHECKED_RASTER_SEMANTICS_UNVERIFIED")
        self.assertEqual(stored["files"][2]["validation_status"], "ZIP_INTEGRITY_CHECKED_VECTOR_SCHEMA_PENDING")
        self.assertEqual(stored["files"][2]["vector_candidates"], ["Ernakulam_Susceptibility.shp"])
        self.assertEqual(stored["files"][3]["validation_status"], "PDF_SIGNATURE_CHECKED_FACILITY_MATCHING_REQUIRED")
        self.assertEqual(stored["files"][4]["validation_status"], "BOUNDARY_GEOJSON_STRUCTURE_CHECKED_LEGAL_STATUS_UNVERIFIED")
        self.assertEqual(stored["files"][4]["geometry_type"], "MultiPolygon")
        self.assertEqual(stored["files"][4]["boundary_feature_count"], 2)
        self.assertEqual(stored["files"][0]["city_boundary_screening"]["points_inside_candidate_boundary"], 1)
        self.assertEqual(stored["files"][0]["city_boundary_screening"]["points_outside_candidate_boundary"], 0)
        self.assertTrue(all(item["sha256"] for item in stored["files"]))

    @patch.object(acquisition, "fetch")
    def test_falls_back_to_state_filter_if_spatial_envelope_is_empty(self, mocked_fetch):
        hospitals = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {
                    "state_name": "Kerala",
                    "district_name": "Ernakulam",
                    "health_facility_name": "Fallback Hospital",
                },
                "geometry": {"type": "Point", "coordinates": [76.3, 9.9]},
            }],
        }
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as archive:
            archive.writestr("candidate.tif", b"placeholder")
        mocked_fetch.side_effect = [
            (json.dumps({"objectIds": []}).encode(), "https://example.org/empty-state", "application/json"),
            (json.dumps({"objectIds": [7]}).encode(), "https://example.org/spatial-ids", "application/json"),
            (json.dumps(hospitals).encode(), "https://example.org/hospitals", "application/geo+json"),
            (memory.getvalue(), "https://example.org/flood.zip", "application/zip"),
            (make_landslide_zip(), "https://example.org/landslide.zip", "application/zip"),
            (b"%PDF-1.4\\nmock official institution list", "https://example.org/institutions.pdf", "application/pdf"),
            (json.dumps(BOUNDARY).encode(), "https://example.org/boundary.geojson", "application/geo+json"),
        ]

        manifest = acquisition.acquire(self.output)
        self.assertEqual(manifest["overall_status"], "RAW_CANDIDATES_NOT_APPROVED_FOR_MAP")
        self.assertEqual(manifest["files"][0]["feature_count"], 1)
        self.assertEqual(manifest["files"][2]["validation_status"], "ZIP_INTEGRITY_CHECKED_VECTOR_SCHEMA_PENDING")
        self.assertEqual(manifest["files"][3]["validation_status"], "PDF_SIGNATURE_CHECKED_FACILITY_MATCHING_REQUIRED")
        self.assertEqual(manifest["files"][4]["validation_status"], "BOUNDARY_GEOJSON_STRUCTURE_CHECKED_LEGAL_STATUS_UNVERIFIED")
        self.assertTrue((self.output / "kerala_health_department_institutions_2024_25.pdf").exists())
        first_url = mocked_fetch.call_args_list[0].args[0]
        fallback_url = mocked_fetch.call_args_list[1].args[0]
        self.assertIn("geometryType=esriGeometryEnvelope", first_url)
        self.assertIn("inSR=4326", first_url)
        self.assertIn("75.9", first_url)
        self.assertIn("77.0", first_url)
        self.assertIn("statename%3D%27Kerala%27", fallback_url)

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
            (json.dumps({"objectIds": [1]}).encode(), "https://example.org/ids", "application/json"),
            (json.dumps(hospitals).encode(), "https://example.org/hospitals", "application/geo+json"),
            (b"<html>error</html>", "https://example.org/error", "text/html"),
            (make_landslide_zip(), "https://example.org/landslide.zip", "application/zip"),
            (b"%PDF-1.4\\nmock official institution list", "https://example.org/institutions.pdf", "application/pdf"),
            (json.dumps(BOUNDARY).encode(), "https://example.org/boundary.geojson", "application/geo+json"),
        ]
        with self.assertRaisesRegex(RuntimeError, "One or more map reference downloads failed"):
            acquisition.acquire(self.output)
        manifest = json.loads((self.output / "map_reference_manifest.json").read_text(encoding="utf-8"))
        self.assertIn("not a ZIP archive", manifest["files"][1]["error"])
        self.assertEqual(manifest["overall_status"], "PARTIAL_ACQUISITION_FAILED")
        self.assertFalse((self.output / "ksdma_flood_return_probability_historical_10_25_50.zip").exists())

    @patch.object(acquisition, "fetch")
    def test_partial_failure_preserves_manifest_for_all_sources(self, mocked_fetch):
        hospitals = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"state_name": "Kerala", "district_name": "Ernakulam", "health_facility_name": "Test Hospital"},
                "geometry": {"type": "Point", "coordinates": [76.3, 9.9]},
            }],
        }
        mocked_fetch.side_effect = [
            (json.dumps({"objectIds": [1]}).encode(), "https://example.org/ids", "application/json"),
            (json.dumps(hospitals).encode(), "https://example.org/hospitals", "application/geo+json"),
            (b"<html>download failed</html>", "https://example.org/error", "text/html"),
            (make_landslide_zip(), "https://example.org/landslide.zip", "application/zip"),
            (b"%PDF-1.4\\nmock official institution list", "https://example.org/institutions.pdf", "application/pdf"),
            (json.dumps(BOUNDARY).encode(), "https://example.org/boundary.geojson", "application/geo+json"),
        ]
        with self.assertRaisesRegex(RuntimeError, "Partial provenance manifest saved"):
            acquisition.acquire(self.output)
        manifest_path = self.output / "map_reference_manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["overall_status"], "PARTIAL_ACQUISITION_FAILED")
        self.assertEqual(len(manifest["files"]), 5)
        self.assertEqual(manifest["files"][0]["status"], "DOWNLOADED_RAW_CANDIDATE")
        self.assertEqual(manifest["files"][1]["status"], "ACQUISITION_FAILED")
        self.assertEqual(manifest["files"][2]["status"], "DOWNLOADED_RAW_CANDIDATE")
        self.assertEqual(manifest["files"][2]["validation_status"], "ZIP_INTEGRITY_CHECKED_VECTOR_SCHEMA_PENDING")
        self.assertEqual(manifest["files"][3]["status"], "DOWNLOADED_RAW_CANDIDATE")
        self.assertEqual(manifest["files"][3]["validation_status"], "PDF_SIGNATURE_CHECKED_FACILITY_MATCHING_REQUIRED")
        self.assertEqual(manifest["files"][4]["status"], "DOWNLOADED_RAW_CANDIDATE")
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
                    "properties": {"state_name": "Kerala", "district_name": "Ernakulam", "health_facility_name": "Out-of-area test"},
                    "geometry": {"type": "Point", "coordinates": [99, 9.9]},
                },
            ],
        }
        memory = io.BytesIO()
        with zipfile.ZipFile(memory, "w") as archive:
            archive.writestr("candidate.tif", b"placeholder")
        mocked_fetch.side_effect = [
            (json.dumps({"objectIds": [1]}).encode(), "https://example.org/ids", "application/json"),
            (json.dumps(hospitals).encode(), "https://example.org/hospitals", "application/geo+json"),
            (memory.getvalue(), "https://example.org/flood.zip", "application/zip"),
            (make_landslide_zip(), "https://example.org/landslide.zip", "application/zip"),
            (b"%PDF-1.4\\nmock official institution list", "https://example.org/institutions.pdf", "application/pdf"),
            (json.dumps(BOUNDARY).encode(), "https://example.org/boundary.geojson", "application/geo+json"),
        ]
        manifest = acquisition.acquire(self.output)
        record = manifest["files"][0]
        self.assertEqual(record["source_feature_count"], 2)
        self.assertEqual(record["feature_count"], 1)
        self.assertEqual(record["invalid_point_count"], 0)
        self.assertEqual(record["district_filter_mismatch_count"], 0)
        self.assertEqual(record["outside_kerala_screening_box_count"], 1)
        self.assertEqual(record["missing_facility_name_count"], 0)
        self.assertEqual(record["validation_status"], "STRUCTURE_CHECKED_WITH_SPATIAL_QA_FLAGS")
        self.assertEqual(record["city_boundary_screening"]["points_inside_candidate_boundary"], 0)
        self.assertEqual(record["city_boundary_screening"]["points_outside_candidate_boundary"], 1)
        self.assertEqual(manifest["overall_status"], "RAW_CANDIDATES_NOT_APPROVED_FOR_MAP")


if __name__ == "__main__":
    unittest.main()

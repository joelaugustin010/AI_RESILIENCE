"""Tests for OpenCity Kochi ward KML acquisition and structural audit."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import acquire_kochi_ward_boundary_candidate as acquisition

KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<Placemark><ExtendedData><SchemaData><SimpleData name="ward_lgd_name">Ward 1</SimpleData></SchemaData></ExtendedData><Polygon><outerBoundaryIs><LinearRing><coordinates>
76.20,9.80,0 76.30,9.80,0 76.30,9.90,0 76.20,9.90,0 76.20,9.80,0
</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
<Placemark><ExtendedData><SchemaData><SimpleData name="ward_lgd_name">Ward 2</SimpleData></SchemaData></ExtendedData><Polygon><outerBoundaryIs><LinearRing><coordinates>
76.31,9.80,0 76.40,9.80,0 76.40,9.90,0 76.31,9.90,0 76.31,9.80,0
</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
</Document></kml>"""


class KochiWardBoundaryCandidateTests(unittest.TestCase):
    def test_audits_kml_without_promoting_candidate(self):
        audit = acquisition.audit_kml(KML)
        self.assertEqual(audit["placemark_count"], 2)
        self.assertEqual(audit["polygon_count"], 2)
        self.assertEqual(audit["unique_placemark_name_count"], 2)
        self.assertEqual(audit["unclosed_ring_count"], 0)
        self.assertEqual(audit["coordinate_bounds_lonlat"], [76.2, 9.8, 76.4, 9.9])
        self.assertFalse(audit["expected_74_ward_count_matches"])
        self.assertEqual(audit["structural_status"], "STRUCTURE_CHECKED_CANDIDATE_ONLY")

    def test_rejects_non_kml_xml(self):
        with self.assertRaisesRegex(ValueError, "root element is not KML"):
            acquisition.audit_kml(b"<html><body>not KML</body></html>")

    def test_rejects_malformed_coordinate_tuple(self):
        malformed = KML.replace(b"76.30,9.90,0", b"bad,9.90,0")
        with self.assertRaisesRegex(ValueError, "malformed coordinate tuples"):
            acquisition.audit_kml(malformed)

    @patch.object(acquisition, "fetch")
    def test_acquisition_persists_raw_candidate_and_checksum(self, mocked_fetch):
        api = {
            "success": True,
            "result": {
                "url": "https://example.org/kochi.kml",
                "name": "Kochi Wards Map 2024",
                "format": "KML",
                "license_title": "Other (Public Domain)",
                "size": len(KML),
            },
        }
        mocked_fetch.side_effect = [
            (json.dumps(api).encode(), acquisition.RESOURCE_API, "application/json"),
            (KML, "https://example.org/kochi.kml", "application/vnd.google-earth.kml+xml"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            result = acquisition.acquire(Path(directory))
            self.assertEqual(result["status"], "DOWNLOADED_RAW_CANDIDATE")
            self.assertEqual(result["validation_status"], "STRUCTURE_CHECKED_CANDIDATE_ONLY")
            self.assertTrue((Path(directory) / "kochi_wards_2024_candidate.kml").exists())
            metadata = json.loads((Path(directory) / "kochi_wards_2024_candidate.metadata.json").read_text())
            self.assertEqual(metadata["sha256"], result["sha256"])
            self.assertEqual(len(result["sha256"]), 64)
            self.assertEqual(mocked_fetch.call_count, 2)

    @patch.object(acquisition, "fetch")
    def test_failed_api_is_recorded_and_raises(self, mocked_fetch):
        mocked_fetch.return_value = (b'{"success": false}', acquisition.RESOURCE_API, "application/json")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "acquisition failed"):
                acquisition.acquire(Path(directory))
            metadata = json.loads((Path(directory) / "kochi_wards_2024_candidate.metadata.json").read_text())
            self.assertEqual(metadata["status"], "ACQUISITION_FAILED")
            self.assertIn("success=true", metadata["error"])


if __name__ == "__main__":
    unittest.main()

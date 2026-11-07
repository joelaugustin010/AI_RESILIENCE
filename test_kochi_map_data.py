"""Integrity checks for the bundled, attributed Kochi boundary snapshot."""

import base64
import hashlib
import json
import unittest
from pathlib import Path

import pydeck as pdk

from src.kochi_map_layers import build_jrc_preview_layer
from src.kochi_boundary import build_display_boundary
from src.spatial_data import processed_layer_issues, validate_geojson


ROOT = Path(__file__).resolve().parent
REFERENCE = ROOT / "data" / "reference"


class KochiBoundaryDataTests(unittest.TestCase):
    def test_boundary_is_a_closed_wgs84_polygon_with_pinned_hash(self):
        geojson_path = REFERENCE / "kochi_corporation_boundary.geojson"
        metadata = json.loads((REFERENCE / "kochi_corporation_boundary.metadata.json").read_text(encoding="utf-8"))
        raw = geojson_path.read_bytes()
        feature = json.loads(raw)

        self.assertEqual(hashlib.sha256(raw).hexdigest(), metadata["sha256"])
        self.assertEqual(feature["type"], "Feature")
        self.assertEqual(feature["geometry"]["type"], "Polygon")
        ring = feature["geometry"]["coordinates"][0]
        self.assertGreater(len(ring), 4)
        self.assertEqual(ring[0], ring[-1])
        for longitude, latitude in ring:
            self.assertTrue(76.0 <= longitude <= 77.0)
            self.assertTrue(9.0 <= latitude <= 11.0)
        self.assertEqual(metadata["source_publication_or_update_date"], None)
        self.assertIn("CC BY-SA 2.5 India", metadata["license"])

    def test_jrc_bitmap_image_is_serialized_as_a_literal_data_url(self):
        image_path = ROOT / "data" / "processed" / "spatial_layers" / "jrc_glofas_rp100_kochi_preview.png"
        metadata_path = image_path.with_name("jrc_glofas_rp100_kochi_preview.metadata.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        bounds = metadata["processing"]["bounds_epsg4326"]

        layer = build_jrc_preview_layer(image_path, bounds)
        specification = json.loads(pdk.Deck(layers=[layer]).to_json())
        image = specification["layers"][0]["image"]

        self.assertTrue(image.startswith("data:image/png;base64,"))
        self.assertFalse(image.startswith("@@="))
        self.assertEqual(base64.b64decode(image.split(",", 1)[1]), image_path.read_bytes())

    def test_boundary_is_reported_as_provisional_when_topology_check_finds_issue(self):
        geojson_path = REFERENCE / "kochi_corporation_boundary.geojson"
        metadata = json.loads((REFERENCE / "kochi_corporation_boundary.metadata.json").read_text(encoding="utf-8"))
        report = validate_geojson(geojson_path, metadata)
        self.assertFalse(report["invalid_features"] == [])
        self.assertTrue(any("self-intersects" in message for issue in report["invalid_features"] for message in issue["errors"]))
        self.assertEqual(hashlib.sha256(geojson_path.read_bytes()).hexdigest(), metadata["sha256"])


    def test_self_intersecting_boundary_gets_valid_display_only_derivative_without_source_mutation(self):
        source_feature = {
            "type": "Feature",
            "properties": {"name": "Provisional Kochi boundary"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]]],
            },
        }
        original = json.loads(json.dumps(source_feature))

        display_feature, report = build_display_boundary(source_feature)

        self.assertEqual(source_feature, original)
        self.assertFalse(report["source_geometry_valid"])
        self.assertTrue(report["display_geometry_valid"])
        self.assertIn(report["display_geometry_type"], {"Polygon", "MultiPolygon"})
        self.assertFalse(report["analysis_eligible"])
        self.assertFalse(display_feature["properties"]["display_geometry_is_analysis_eligible"])
        self.assertEqual(
            display_feature["properties"]["display_geometry_status"],
            "REPAIRED_DERIVATIVE_FOR_ORIENTATION_ONLY",
        )



class KochiWardLayerIntegrationTests(unittest.TestCase):
    def test_ward_snapshot_and_processed_subset_have_pinned_provenance_and_quality_counts(self):
        raw_path = ROOT / "data" / "raw" / "koch_wards_2022.geojson"
        raw_metadata_path = ROOT / "data" / "raw" / "koch_wards_2022.metadata.json"
        processed_path = ROOT / "data" / "processed" / "spatial_layers" / "kochi_wards_datameet_2022.geojson"
        processed_metadata_path = processed_path.with_name("kochi_wards_datameet_2022.metadata.json")
        raw_metadata = json.loads(raw_metadata_path.read_text(encoding="utf-8"))
        metadata = json.loads(processed_metadata_path.read_text(encoding="utf-8"))
        raw_bytes = raw_path.read_bytes()
        raw = [json.loads(line) for line in raw_bytes.decode("utf-8").splitlines() if line.strip()]
        processed = json.loads(processed_path.read_text(encoding="utf-8"))

        self.assertEqual(hashlib.sha256(raw_bytes).hexdigest(), raw_metadata["source_sha256"])
        self.assertEqual(hashlib.sha256(raw_bytes).hexdigest(), metadata["source_snapshot_sha256"])
        self.assertEqual(len(raw), 77)
        self.assertEqual(len(processed["features"]), 74)
        self.assertEqual(len(metadata["excluded_invalid_features"]), 3)
        self.assertEqual(metadata["validation"]["missing_property_values"], 12)
        self.assertEqual(metadata["layer_role"], "context")
        issues = processed_layer_issues(ROOT / "data" / "processed")
        ward_issue = next(issue for issue in issues if "kochi_wards_datameet_2022.geojson" in issue)
        self.assertIn("6 of 74 legacy polygons", ward_issue)
        self.assertIn("no inferred ward identities", ward_issue)
        self.assertEqual(metadata["license"], raw_metadata["license"])


if __name__ == "__main__":
    unittest.main()

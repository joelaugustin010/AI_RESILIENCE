"""Regression tests for non-empty, unambiguous map boundary/ward labels."""

import json
import unittest
from pathlib import Path

from app_pages.kochi_map import normalize_geojson_for_tooltip, resolve_inspector_ward_name


class MapNameFallbackTests(unittest.TestCase):
    def test_missing_properties_get_clear_nonempty_fallbacks_without_inventing_names(self):
        source = {
            "type": "FeatureCollection",
            "features": [
                {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [76.2, 9.9]}},
                {"type": "Feature", "properties": {"Ward_No": 12}, "geometry": {"type": "Point", "coordinates": [76.3, 9.9]}},
            ],
        }
        result = normalize_geojson_for_tooltip(source)
        first, second = result["features"]

        self.assertEqual(first["properties"]["display_bound"], "Boundary feature 1 (source label unavailable)")
        self.assertEqual(first["properties"]["display_ward"], "Ward name unavailable (source feature 1)")
        self.assertIn("ward no. 12", second["properties"]["display_ward"])
        self.assertNotEqual(second["properties"]["display_ward"], "12")
        for feature in result["features"]:
            self.assertTrue(feature["properties"]["display_bound"].strip())
            self.assertTrue(feature["properties"]["display_ward"].strip())

    def test_recovers_alternate_and_suffixed_gis_fields(self):
        source = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "properties": {"WardName_1": "Test Ward", "Bound_Name_1": "Test Boundary"},
                "geometry": {"type": "Point", "coordinates": [76.2, 9.9]},
            }],
        }
        result = normalize_geojson_for_tooltip(source)
        props = result["features"][0]["properties"]
        self.assertEqual(props["display_ward"], "Test Ward")
        self.assertEqual(props["display_bound"], "Test Boundary")

    def test_inspector_uses_boundary_name_when_ward_name_is_missing(self):
        self.assertEqual(
            resolve_inspector_ward_name("Ward name unavailable (feature 4)", "Example Boundary", "12", 4),
            "Example Boundary",
        )
        self.assertEqual(
            resolve_inspector_ward_name("Ward name unavailable (feature 4)", "Boundary label unavailable (feature 4)", "12", 4),
            "Ward name unavailable (ward no. 12; source feature 4)",
        )
        self.assertEqual(
            resolve_inspector_ward_name("Ward name unavailable (feature 4)", "Boundary label unavailable (feature 4)", "", 4),
            "Ward name unavailable (source feature 4)",
        )

    def test_all_retained_legacy_ward_features_render_nonempty_labels(self):
        root = Path(__file__).resolve().parents[1]
        path = root / "data" / "processed" / "spatial_layers" / "kochi_wards_datameet_2022.geojson"
        source = json.loads(path.read_text(encoding="utf-8"))
        original_geometry = [feature["geometry"] for feature in source["features"]]
        result = normalize_geojson_for_tooltip(source)

        self.assertEqual(len(result["features"]), 74)
        self.assertEqual([feature["geometry"] for feature in result["features"]], original_geometry)
        for index, feature in enumerate(result["features"], start=1):
            props = feature["properties"]
            self.assertTrue(props["display_bound"].strip(), f"Empty boundary label at feature {index}")
            self.assertTrue(props["display_ward"].strip(), f"Empty ward label at feature {index}")


if __name__ == "__main__":
    unittest.main()

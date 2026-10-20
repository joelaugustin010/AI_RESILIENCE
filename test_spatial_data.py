"""Tests for source provenance and reusable local spatial ingestion."""

import json
import csv
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.spatial_data import (
    SpatialDataError,
    classify_exposure,
    geometry_errors,
    geometry_intersects,
    ingest_geojson,
    ingest_geojson_feature_lines,
    provenance_errors,
    processed_layer_issues,
    read_processed_layers,
    validate_geojson,
    review_coordinate_csv,
)


def metadata(**changes):
    result = {
        "dataset_id": "test-layer",
        "title": "Test layer",
        "source_url": "https://example.test/dataset",
        "publisher": "Documented publisher",
        "retrieved_on": "2026-10-20",
        "publication_date": "2025-01-01",
        "license": "CC0 1.0",
        "crs": "EPSG:4326",
        "units": "Degrees longitude and latitude",
        "geographic_coverage": "Test extent only",
        "limitations": ["Test data only; not a real Kochi dataset."],
    }
    result.update(changes)
    return result


def point(lon, lat, feature_id="p"):
    return {"type": "Feature", "id": feature_id, "properties": {"name": feature_id}, "geometry": {"type": "Point", "coordinates": [lon, lat]}}


def polygon(coords, feature_id="zone"):
    return {"type": "Feature", "id": feature_id, "properties": {"zone": feature_id}, "geometry": {"type": "Polygon", "coordinates": [coords]}}


SQUARE = [[76.0, 9.0], [77.0, 9.0], [77.0, 10.0], [76.0, 10.0], [76.0, 9.0]]


class ProvenanceTests(unittest.TestCase):
    def test_complete_provenance_passes(self):
        self.assertEqual(provenance_errors(metadata()), [])

    def test_unknown_license_and_missing_source_are_rejected(self):
        problems = provenance_errors(metadata(license="Unknown", source_url=""))
        self.assertTrue(any("licence" in problem.lower() for problem in problems))
        self.assertTrue(any("source_url" in problem for problem in problems))

    def test_unknown_crs_is_rejected_without_guessing(self):
        self.assertTrue(any("Only documented WGS 84" in message for message in provenance_errors(metadata(crs="Unknown"))))

    def test_unknown_crs_is_rejected_without_guessing(self):
        self.assertTrue(any("Only documented WGS 84" in message for message in provenance_errors(metadata(crs="Unknown"))))


class GeometryValidationTests(unittest.TestCase):
    def test_out_of_range_coordinate_is_rejected(self):
        self.assertTrue(any("outside WGS 84" in message for message in geometry_errors(point(200, 10)["geometry"])))

    def test_unclosed_and_self_intersecting_polygon_is_rejected(self):
        unclosed = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]}
        crossed = {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]]}
        self.assertTrue(any("not closed" in message for message in geometry_errors(unclosed)))
        self.assertTrue(any("self-intersects" in message for message in geometry_errors(crossed)))

    def test_polygon_hole_is_respected(self):
        donut = {"type": "Polygon", "coordinates": [SQUARE, [[76.4, 9.4], [76.6, 9.4], [76.6, 9.6], [76.4, 9.6], [76.4, 9.4]]]}
        self.assertFalse(geometry_intersects(point(76.5, 9.5)["geometry"], donut))
        self.assertTrue(geometry_intersects(point(76.4, 9.5)["geometry"], donut))

    def test_topology_supports_point_line_polygon_and_multipolygon(self):
        square = polygon(SQUARE)
        self.assertTrue(geometry_intersects(point(76.5, 9.5)["geometry"], square["geometry"]))
        line = {"type": "LineString", "coordinates": [[76.2, 9.2], [76.8, 9.8]]}
        self.assertTrue(geometry_intersects(line, square["geometry"]))
        contained_line = {"type": "LineString", "coordinates": [[76.2, 9.2], [76.8, 9.2]]}
        self.assertTrue(geometry_intersects(contained_line, square["geometry"]))
        multi = {"type": "MultiPolygon", "coordinates": [[SQUARE]]}
        self.assertTrue(geometry_intersects(point(76.5, 9.5)["geometry"], multi))
        self.assertFalse(geometry_intersects(point(77.5, 9.5)["geometry"], multi))


class DatasetValidationAndIngestionTests(unittest.TestCase):
    def _write_geojson(self, path, features):
        path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")

    def test_duplicate_missing_values_and_coverage_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "points.geojson"
            feature = point(76.5, 9.5, "same")
            feature["properties"]["operator"] = None
            self._write_geojson(source, [feature, feature, point(70, 9, "outside")])
            report = validate_geojson(source, metadata(), {"type": "Polygon", "coordinates": [SQUARE]})
        self.assertEqual(report["exact_duplicate_features"], 1)
        self.assertGreater(report["missing_property_values"], 0)
        self.assertEqual(report["features_intersecting_coverage"], 2)
        self.assertEqual(report["features_outside_coverage"], 1)

    def test_ingestion_copies_valid_data_and_leaves_source_identical(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.geojson"
            self._write_geojson(source, [point(76.5, 9.5)])
            original_bytes = source.read_bytes()
            report = ingest_geojson(source, root / "processed", metadata())
            copied = Path(report["processed_file"])
            self.assertTrue(copied.is_file())
            self.assertEqual(copied.read_bytes(), original_bytes)
            self.assertEqual(source.read_bytes(), original_bytes)
            self.assertTrue(copied.with_name("test-layer.metadata.json").is_file())

    def test_invalid_provenance_blocks_ingestion(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.geojson"
            self._write_geojson(source, [point(76.5, 9.5)])
            with self.assertRaises(SpatialDataError):
                ingest_geojson(source, root / "processed", metadata(license="Unknown"))

    def test_existing_processed_layer_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.geojson"
            self._write_geojson(source, [point(76.5, 9.5)])
            processed_root = root / "processed"
            ingest_geojson(source, processed_root, metadata())
            with self.assertRaisesRegex(SpatialDataError, "will not overwrite"):
                ingest_geojson(source, processed_root, metadata())

    def test_processed_layer_requires_intact_hash_sidecar(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.geojson"
            self._write_geojson(source, [point(76.5, 9.5)])
            processed_root = root / "processed"
            ingest_geojson(source, processed_root, metadata())
            self.assertEqual(len(read_processed_layers(processed_root)), 1)
            processed_file = processed_root / "spatial_layers" / "test-layer.geojson"
            processed_file.write_text("{}", encoding="utf-8")
            self.assertEqual(read_processed_layers(processed_root), [])
            self.assertTrue(any("content hash does not match" in issue for issue in processed_layer_issues(processed_root)))

    def test_non_geojson_format_is_explicitly_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "layer.shp"
            source.write_bytes(b"not a shapefile")
            with self.assertRaisesRegex(SpatialDataError, "Only .geojson/.json"):
                validate_geojson(source, metadata())

    def test_line_delimited_features_are_normalized_and_invalid_geometries_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "wards.geojson"
            valid = point(76.5, 9.5, "ward-a")
            invalid = {"type": "Feature", "properties": {"fid": "bad"}, "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]]}}
            original = (json.dumps(valid) + "\n" + json.dumps(invalid) + "\n").encode()
            source.write_bytes(original)
            info = metadata(dataset_id="ward-lines", required_properties=["name"])
            report = ingest_geojson_feature_lines(source, root / "processed", info)
            processed = Path(report["processed_file"])
            layer = read_processed_layers(root / "processed")
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(report["source_feature_count"], 2)
            self.assertEqual(report["processed_feature_count"], 1)
            self.assertEqual(len(report["excluded_invalid_features"]), 1)
            self.assertEqual(len(layer), 1)
            self.assertEqual(len(layer[0]["features"]), 1)
            sidecar = json.loads(processed.with_name("ward-lines.metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(sidecar["source_snapshot_sha256"], __import__("hashlib").sha256(original).hexdigest())

    def test_line_delimited_input_rejects_non_feature_records(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "bad.geojson"
            source.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")
            with self.assertRaisesRegex(SpatialDataError, "one GeoJSON Feature object per"):
                ingest_geojson_feature_lines(source, Path(folder) / "processed", metadata())


class ExposureUncertaintyTests(unittest.TestCase):
    def test_missing_hazard_layer_means_unknown_not_safe(self):
        result = classify_exposure([point(76.5, 9.5)], None)
        self.assertEqual(result[0]["exposure_status"], "Unknown exposure")
        self.assertIn("not evidence of safety", result[0]["method"])

    def test_invalid_asset_geometry_is_unknown(self):
        invalid_asset = {"type": "Feature", "properties": {"id": "broken"}, "geometry": None}
        result = classify_exposure([invalid_asset], [polygon(SQUARE)])
        self.assertEqual(result[0]["exposure_status"], "Unknown exposure")

    def test_intersecting_and_no_detected_intersection_have_distinct_labels(self):
        assets = [point(76.5, 9.5, "inside"), point(77.5, 9.5, "outside")]
        zones = [polygon(SQUARE, "flood-a")]
        results = classify_exposure(assets, zones)
        self.assertEqual(results[0]["exposure_status"], "Geometric intersection detected (spatial exposure indicator)")
        self.assertEqual(results[0]["intersecting_hazard_ids"], ["flood-a"])
        self.assertEqual(results[1]["exposure_status"], "No detected intersection within available hazard layer")
        self.assertIn("no distance, clearance, vulnerability", results[1]["method"].lower())


class AcquiredSourceReviewTests(unittest.TestCase):
    def test_synthetic_coordinate_review_preserves_ambiguity_and_flags_duplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "source.csv"
            processed = root / "review.csv"
            sidecar = root / "review.metadata.json"
            rows = [
                {"State": "Kerala", "District": "Ernakulam", "Location_Coordinates": "10.0,76.0", "Hospital_Name": "A"},
                {"State": "Kerala", "District": "Ernakulam", "Location_Coordinates": "10.0,76.0", "Hospital_Name": "B"},
                {"State": "Kerala", "District": "Ernakulam", "Location_Coordinates": "", "Hospital_Name": "C"},
                {"State": "Kerala", "District": "Thrissur", "Location_Coordinates": "10.0,76.0", "Hospital_Name": "Other"},
            ]
            with source.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            info = {
                "dataset_id": "synthetic-review-test",
                "title": "Controlled test CSV only",
                "source_url": "https://example.test/synthetic",
                "publisher": "Test fixture",
                "retrieved_on": "2026-10-20",
                "publication_date": "Not stated by test fixture",
                "license": "CC0 1.0 test fixture",
                "limitations": ["Synthetic test rows; not real facilities or Kochi data."],
            }
            report = review_coordinate_csv(
                source, processed, sidecar, info, "Kerala", "Ernakulam",
                retain_columns=("State", "District", "Location_Coordinates", "Hospital_Name"),
            )
            self.assertEqual(report["selected_record_count"], 3)
            self.assertEqual(report["coordinate_pair_parseable_count"], 2)
            self.assertEqual(report["coordinate_pair_unparseable_count"], 1)
            self.assertEqual(report["duplicate_coordinate_pair_group_count"], 1)
            self.assertEqual(report["records_in_duplicate_coordinate_pair_groups"], 2)
            with processed.open(encoding="utf-8", newline="") as handle:
                reviewed = list(csv.DictReader(handle))
            self.assertEqual(reviewed[0]["Location_Coordinates"], "10.0,76.0")
            self.assertIn("NOT VALIDATED", reviewed[0]["spatial_validation_status"])
            self.assertNotIn("geometry", reviewed[0])
            self.assertIn("not documented", report["coordinate_order"].lower())

    def test_downloaded_ksdma_archive_and_hospital_source_hashes_match_sidecars(self):
        root = Path(__file__).resolve().parent
        flood_path = root / "data/raw/ksdma_flood_return_probability_historical_10_25_50.zip"
        flood_meta = json.loads((root / "data/raw/ksdma_flood_return_probability_historical_10_25_50.metadata.json").read_text(encoding="utf-8"))
        hospital_path = root / "data/raw/nihfw_national_hospital_directory.csv"
        hospital_meta = json.loads((root / "data/raw/nihfw_national_hospital_directory.metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256(flood_path.read_bytes()).hexdigest(), flood_meta["sha256"])
        self.assertEqual(hashlib.sha256(hospital_path.read_bytes()).hexdigest(), hospital_meta["source_sha256"])
        with zipfile.ZipFile(flood_path) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(len([name for name in archive.namelist() if name.lower().endswith(".tif")]), 3)
        review_meta = json.loads((root / "data/processed/nihfw_ernakulam_hospitals_coordinate_review.metadata.json").read_text(encoding="utf-8"))
        validation = review_meta["validation"]
        self.assertEqual(validation["selected_record_count"], 180)
        self.assertEqual(validation["coordinate_pair_unparseable_count"], 31)
        self.assertEqual(validation["duplicate_coordinate_pair_group_count"], 18)
        self.assertEqual(validation["records_in_duplicate_coordinate_pair_groups"], 63)
        self.assertIn("not documented", validation["coordinate_order"].lower())
        self.assertEqual(review_meta["crs"], "Not stated in resource schema or CSV")
        self.assertTrue(hospital_meta["license"].startswith("Government Open Data License - India"))
        alternatives = review_meta["alternative_sources_reviewed"]
        self.assertEqual(alternatives[0]["status"], "candidate_identity_reference_only_not_spatially_ingested")
        self.assertIn("no downloadable GIS", alternatives[0]["blocker"])
        review_path = root / "data/processed/nihfw_ernakulam_hospitals_coordinate_review.csv"
        with review_path.open(encoding="utf-8", newline="") as handle:
            records = list(csv.DictReader(handle))
        self.assertEqual(len(records), 180)
        self.assertEqual(sum(row["coordinate_pair_parse_status"] != "two finite numeric values" for row in records), 31)
        self.assertTrue(all("NOT VALIDATED" in row["spatial_validation_status"] for row in records))
        self.assertTrue(all("geometry" not in row for row in records))


if __name__ == "__main__":
    unittest.main()

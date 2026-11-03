"""Tests for Phase 2 external-data parsing and provenance safeguards."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from scripts.acquire_phase2_data import (
    _local_comparison,
    _tabular_quality,
    build_register,
)
from src.phase2_data import (
    NASA_PARAMETERS,
    Phase2DataError,
    Phase2DataUnavailable,
    load_imd_rainfall_cell,
    load_nasa_power,
    load_osm_road_snapshot,
    load_usgs_earthquake_query,
)


class Phase2ExternalDataTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "data" / "raw" / "experimental").mkdir(parents=True)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def _write_json_snapshot(self, filename, response, metadata):
        path = self.root / "data" / "raw" / "experimental" / filename
        payload = json.dumps(response).encode()
        path.write_bytes(payload)
        metadata["sha256"] = hashlib.sha256(payload).hexdigest()
        path.with_name(path.name + ".metadata.json").write_text(
            json.dumps(metadata),
            encoding="utf-8",
        )
        return path

    def test_nasa_power_daily_series_and_fill_values_are_parsed(self):
        path = self.root / "data" / "raw" / "experimental" / (
            "nasa_power_kochi_center_daily_20200101_20250101.json"
        )
        response = {
            "header": {"time_standard": "UTC", "fill_value": -999},
            "properties": {
                "parameter": {
                    name: {"20200101": 1.0, "20200102": -999}
                    for name in NASA_PARAMETERS
                }
            },
            "parameters": {
                name: {"units": "documented", "longname": name}
                for name in NASA_PARAMETERS
            },
            "geometry": {"coordinates": [76.27, 9.93, 47.32]},
        }
        payload = json.dumps(response).encode()
        path.write_bytes(payload)
        path.with_name(path.name + ".metadata.json").write_text(
            json.dumps({"sha256": hashlib.sha256(payload).hexdigest()}),
            encoding="utf-8",
        )

        frame, metadata, summary = load_nasa_power(self.root)

        self.assertEqual(len(frame), 2)
        self.assertEqual(frame.iloc[0]["date"].date().isoformat(), "2020-01-01")
        self.assertTrue(np.isnan(frame.iloc[1]["PRECTOTCORR"]))
        self.assertEqual(summary["missing_values_by_parameter"]["PRECTOTCORR"], 1)
        self.assertEqual(summary["time_standard"], "UTC")
        self.assertEqual(summary["coordinate"], [76.27, 9.93, 47.32])
        self.assertIn("sha256", metadata)

    def test_nasa_power_hash_mismatch_fails_closed(self):
        path = self.root / "data" / "raw" / "experimental" / (
            "nasa_power_kochi_center_daily_20200101_20250101.json"
        )
        path.write_text("{}", encoding="utf-8")
        path.with_name(path.name + ".metadata.json").write_text(
            json.dumps({"sha256": "incorrect"}),
            encoding="utf-8",
        )

        with self.assertRaises(Phase2DataError):
            load_nasa_power(self.root)

    def test_optional_nasa_snapshot_is_reported_as_unavailable(self):
        with self.assertRaises(Phase2DataUnavailable):
            load_nasa_power(self.root)

    def test_imd_netcdf_nearest_grid_cell_extracts_daily_values(self):
        from scipy.io import netcdf_file

        path = self.root / "data" / "raw" / "experimental" / (
            "imd_daily_gridded_rainfall_2024_025deg.nc"
        )
        with netcdf_file(path, mode="w") as dataset:
            dataset.createDimension("TIME", None)
            dataset.createDimension("LATITUDE", 2)
            dataset.createDimension("LONGITUDE", 2)
            longitude = dataset.createVariable("LONGITUDE", "d", ("LONGITUDE",))
            latitude = dataset.createVariable("LATITUDE", "d", ("LATITUDE",))
            time = dataset.createVariable("TIME", "d", ("TIME",))
            rainfall = dataset.createVariable(
                "RAINFALL", "f", ("TIME", "LATITUDE", "LONGITUDE")
            )
            longitude.units = b"degrees_east"
            latitude.units = b"degrees_north"
            time.units = b"days since 1900-12-31 00:00:00"
            rainfall.units = b"mm"
            rainfall.long_name = b"Rainfall"
            rainfall.missing_value = np.float32(-999)
            longitude[:] = [76.0, 76.25]
            latitude[:] = [9.75, 10.0]
            time[:] = [44926, 44927]
            rainfall[:] = [
                [[1, 2], [3, 4]],
                [[5, 6], [7, -999]],
            ]
        payload_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        path.with_name(path.name + ".metadata.json").write_text(
            json.dumps({"sha256": payload_hash}),
            encoding="utf-8",
        )

        frame, metadata, summary = load_imd_rainfall_cell(self.root, 2024)

        self.assertEqual(
            frame["date"].dt.strftime("%Y-%m-%d").tolist(),
            ["2024-01-01", "2024-01-02"],
        )
        self.assertEqual(frame["rainfall_mm"].iloc[0], 4)
        self.assertTrue(np.isnan(frame["rainfall_mm"].iloc[1]))
        self.assertEqual(summary["grid_cell_center"], {"latitude": 10.0, "longitude": 76.25})
        self.assertEqual(summary["valid_days"], 1)
        self.assertEqual(summary["missing_days"], 1)
        self.assertEqual(metadata["sha256"], payload_hash)

    def test_imd_netcdf_hash_mismatch_fails_closed(self):
        path = self.root / "data" / "raw" / "experimental" / (
            "imd_daily_gridded_rainfall_2024_025deg.nc"
        )
        path.write_bytes(b"not-a-netcdf")
        path.with_name(path.name + ".metadata.json").write_text(
            json.dumps({"sha256": "incorrect"}),
            encoding="utf-8",
        )

        with self.assertRaises(Phase2DataError):
            load_imd_rainfall_cell(self.root, 2024)

    def test_missing_imd_year_is_explicitly_unavailable(self):
        with self.assertRaises(Phase2DataUnavailable):
            load_imd_rainfall_cell(self.root, 2018)

    def test_osm_snapshot_reports_mapped_ways_without_access_inference(self):
        self._write_json_snapshot(
            "openstreetmap_roads_provisional_kochi_bounds.json",
            {
                "elements": [
                    {"type": "way", "tags": {"highway": "residential"}},
                    {"type": "way", "tags": {"highway": "primary"}},
                    {"type": "node", "tags": {"highway": "crossing"}},
                    {"type": "way", "tags": {"building": "yes"}},
                ],
                "osm3s": {"timestamp_osm_base": "2026-11-01T18:27:21Z"},
            },
            {"query_bounds": {"south": 9.89, "west": 76.23}},
        )

        metadata, summary = load_osm_road_snapshot(self.root)

        self.assertEqual(summary["road_way_count"], 2)
        self.assertEqual(summary["snapshot_timestamp"], "2026-11-01T18:27:21Z")
        self.assertIn("not verified", summary["inference"])
        self.assertEqual(metadata["query_bounds"]["south"], 9.89)

    def test_empty_usgs_query_is_not_interpreted_as_zero_hazard(self):
        self._write_json_snapshot(
            "usgs_earthquakes_kerala_bbox_1900_present_m0.geojson",
            {"type": "FeatureCollection", "features": []},
            {
                "query_bounds": {"min_lat": 8, "max_lat": 12},
                "time_range": {"start": "1900-01-01", "end": "2026-11-01"},
                "minimum_magnitude": 0,
                "response_status": 200,
            },
        )

        _, summary = load_usgs_earthquake_query(self.root)

        self.assertEqual(summary["catalogue_event_count"], 0)
        self.assertIn("does not establish zero", summary["inference"])

    def test_line_ending_only_local_copy_difference_is_detectable(self):
        local_path = self.root / "local.csv"
        source = b"Station,Data Acquisition Time,Telemetry Hourly Rainfall (mm)\nA,01-01-2024 00:00,1.0\n"
        local_path.write_bytes(source.replace(b"\n", b"\r\n"))

        comparison = _local_comparison(
            local_path,
            source,
            {"rows": 1, "observed_start": "2024-01-01", "observed_end": "2024-01-01"},
        )

        self.assertFalse(comparison["same_sha256"])
        self.assertTrue(comparison["same_sha256_after_crlf_to_lf_normalization"])

    def test_tabular_quality_preserves_duplicate_and_conflict_counts(self):
        payload = (
            b"Station,Data Acquisition Time,Telemetry Hourly Rainfall (mm)\n"
            b"A,01-01-2024 00:00,1\n"
            b"A,01-01-2024 00:00,1\n"
            b"A,01-01-2024 01:00,2\n"
            b"A,01-01-2024 01:00,3\n"
        )

        quality = _tabular_quality(payload)

        self.assertEqual(quality["rows"], 4)
        self.assertEqual(quality["duplicate_station_time_groups"], 2)
        self.assertEqual(quality["conflicting_station_time_groups"], 1)
        self.assertEqual(quality["invalid_timestamp_rows"], 0)
        self.assertEqual(quality["invalid_measurement_rows"], 0)

    def test_register_inventories_sources_and_excludes_browser_profile(self):
        raw = self.root / "data" / "raw"
        (raw / "example.csv").write_bytes(b"a\n1\n")
        browser_cache = self.root / "data" / "processed" / "edge_pdf_profile"
        browser_cache.mkdir(parents=True)
        (browser_cache / "History").write_text("not dataset data", encoding="utf-8")

        register = build_register(self.root)

        self.assertEqual(register["asset_count"], 1)
        self.assertEqual(register["assets"][0]["path"], "data/raw/example.csv")
        self.assertEqual(register["assets"][0]["provenance_status"], "provenance_sidecar_not_found")
        self.assertEqual(register["assets"][0]["sha256"], hashlib.sha256(b"a\n1\n").hexdigest())


    def test_register_inventories_ghcn_files_without_claiming_validation(self):
        raw = self.root / "data" / "raw" / "ghcn"
        raw.mkdir(parents=True)
        (raw / "ghcnd-stations.txt").write_text("station inventory", encoding="utf-8")
        (raw / "IN010032300.dly").write_text("daily station data", encoding="utf-8")

        register = build_register(self.root)
        assets = {asset["path"]: asset for asset in register["assets"]}
        expected = {
            "data/raw/ghcn/ghcnd-stations.txt",
            "data/raw/ghcn/IN010032300.dly",
        }
        self.assertTrue(expected.issubset(assets))
        for relative in expected:
            status = assets[relative]["provenance_status"]
            self.assertEqual(status, "present_inventory_only_not_integrated_provenance_unverified")
            self.assertNotIn("validated", status)
            self.assertNotIn("integrated", status.replace("not_integrated", ""))

    def test_ibtracs_rights_are_explicitly_unresolved_and_not_integrated(self):
        raw = self.root / "data" / "raw" / "ibtracs"
        raw.mkdir(parents=True)
        snapshot = raw / "ibtracs.NI.list.v04r01.csv"
        snapshot.write_text("SID,ISO_TIME\nexample,2020-01-01 00:00:00\n", encoding="utf-8")
        snapshot.with_name(snapshot.name + ".metadata.json").write_text(
            json.dumps({"dataset_id": "noaa_ibtracs_north_indian_v04r01"}),
            encoding="utf-8",
        )

        register = build_register(self.root)
        asset = next(item for item in register["assets"] if item["path"].endswith(snapshot.name))
        status = asset["provenance_status"]
        self.assertEqual(status, "present_not_integrated_rights_unresolved")
        self.assertNotIn("validated", status)
        self.assertNotIn("integrated", status.replace("not_integrated", ""))

    def test_register_discovers_stem_sidecar_for_processed_png(self):
        layer_dir = self.root / "data" / "processed" / "spatial_layers"
        layer_dir.mkdir(parents=True)
        image = layer_dir / "context.png"
        image.write_bytes(b"processed preview")
        sidecar = layer_dir / "context.metadata.json"
        sidecar.write_text(json.dumps({"dataset_id": "context"}), encoding="utf-8")

        register = build_register(self.root)
        asset = next(item for item in register["assets"] if item["path"].endswith("context.png"))
        self.assertEqual(asset["provenance_sidecar"], "data/processed/spatial_layers/context.metadata.json")
        self.assertEqual(
            asset["provenance_status"],
            "sidecar_available_requires_dataset_specific_suitability_review",
        )

    def test_register_excludes_browser_and_machine_artifacts_and_inventories_xlsx(self):
        raw = self.root / "data" / "raw"
        (raw / "example.csv").write_bytes(b"a\n1\n")
        (raw / "official_tables.xlsx").write_bytes(b"workbook snapshot")
        profile = self.root / "data" / "processed" / "edge_pdf_profile"
        profile.mkdir(parents=True)
        (profile / "History.csv").write_text("browser history", encoding="utf-8")
        (self.root / "data" / "processed" / "aqi_daily_preview.png").write_bytes(b"non-spatial preview")
        reference = self.root / "data" / "reference"
        reference.mkdir(parents=True)
        (reference / "DATA_PROVENANCE_REGISTER-LAPTOP-TBN5N220.json").write_text(
            "{}", encoding="utf-8"
        )
        (reference / "spatial_sources-LAPTOP-TBN5N220.json").write_text(
            "{}", encoding="utf-8"
        )

        register = build_register(self.root)
        assets = {asset["path"]: asset for asset in register["assets"]}
        self.assertEqual(set(assets), {"data/raw/example.csv", "data/raw/official_tables.xlsx"})
        self.assertEqual(assets["data/raw/example.csv"]["provenance_status"], "provenance_sidecar_not_found")
        self.assertEqual(
            assets["data/raw/official_tables.xlsx"]["sha256"],
            hashlib.sha256(b"workbook snapshot").hexdigest(),
        )


    def test_ibtracs_validation_claim_requires_matching_sidecar_checksum(self):
        raw = self.root / "data" / "raw" / "ibtracs"
        raw.mkdir(parents=True)
        snapshot = raw / "ibtracs.NI.list.v04r01.csv"
        payload = b"SID,ISO_TIME\\nexample,2020-01-01 00:00:00\\n"
        snapshot.write_bytes(payload)
        metadata = {
            "dataset_id": "noaa_ibtracs_north_indian_v04r01",
            "license": "No dataset-level licence or rights statement was found.",
            "reuse_status": "ACQUIRED_AND_STRUCTURALLY_VALIDATED_NOT_INTEGRATED_RIGHTS_UNRESOLVED",
            "validation": {"row_count": 1},
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        sidecar = snapshot.with_name(snapshot.name + ".metadata.json")
        sidecar.write_text(json.dumps(metadata), encoding="utf-8")

        register = build_register(self.root)
        asset = next(item for item in register["assets"] if item["path"].endswith(snapshot.name))
        self.assertEqual(asset["provenance_status"], "acquired_validated_not_integrated_rights_unresolved")

        metadata["sha256"] = "incorrect"
        sidecar.write_text(json.dumps(metadata), encoding="utf-8")
        register = build_register(self.root)
        asset = next(item for item in register["assets"] if item["path"].endswith(snapshot.name))
        self.assertEqual(asset["provenance_status"], "present_not_integrated_rights_unresolved")
        self.assertNotIn("validated", asset["provenance_status"])

    def test_ghcn_status_uses_hash_verified_sidecar_without_claiming_integration(self):
        raw = self.root / "data" / "raw" / "ghcn"
        raw.mkdir(parents=True)
        snapshot = raw / "IN010032300.dly"
        payload = b"daily station snapshot"
        snapshot.write_bytes(payload)
        metadata = {
            "dataset_id": "noaa_ghcnd_in010032300_prcp",
            "license": "No explicit dataset-level downstream licence statement; rights review required.",
            "reuse_status": "ACQUIRED_STRUCTURALLY_VALIDATED_RIGHTS_REVIEW_REQUIRED_NOT_INTEGRATED",
            "validation": {"record_count": 1, "station_id": "IN010032300"},
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        snapshot.with_name(snapshot.name + ".metadata.json").write_text(
            json.dumps(metadata), encoding="utf-8"
        )

        register = build_register(self.root)
        asset = next(item for item in register["assets"] if item["path"].endswith(snapshot.name))
        self.assertEqual(
            asset["provenance_status"],
            "acquired_structurally_validated_rights_review_required_not_integrated",
        )


if __name__ == "__main__":
    unittest.main()

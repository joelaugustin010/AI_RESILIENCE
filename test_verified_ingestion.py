"""Tests for source snapshots, canonical statuses and fail-closed readiness."""
from __future__ import annotations

import hashlib
import importlib.machinery
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import pytest

from src.ingestion_audit import (
    DATA_STATUS_DEFINITIONS,
    build_ingestion_report,
    read_json_strict,
    validate_annual_aqi_file,
    validate_dwg_file,
    validate_html_file,
    validate_pdf_file,
)
from src.spatial_data import classify_exposure, geometry_intersects, provenance_errors


ROOT = Path(__file__).resolve().parent
TEST_TMP = ROOT / ".test_tmp"


def _point(lon: float, lat: float, name: str = "fixture") -> dict:
    return {
        "type": "Feature",
        "properties": {"name": name},
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
    }


def _polygon() -> dict:
    return {
        "type": "Polygon",
        "coordinates": [[[76, 9], [77, 9], [77, 10], [76, 10], [76, 9]]],
    }


class TemporaryAuditCase(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP.mkdir(exist_ok=True)
        self._temporary = tempfile.TemporaryDirectory(prefix="ingestion-", dir=TEST_TMP)
        self.root = Path(self._temporary.name)

    def tearDown(self) -> None:
        self._temporary.cleanup()

    def _annual_input(self, *, rows=None, year=2026, aqi_data=None):
        raw = self.root / f"kspcb_annual_aqi_{year}_fixture.json"
        sidecar = raw.with_suffix(".metadata.json")
        payload = {
            "aqi_data": aqi_data,
            "station_data": rows if rows is not None else [
                {"stn_code": "123", "station_name": "ELOOR", "mode": "CAAQMS", "average_aqi": "88"}
            ],
        }
        raw_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        raw.write_bytes(raw_bytes)
        metadata = {
            "publisher": "Kerala State Pollution Control Board",
            "source_url": f"https://kspcbipam.kerala.gov.in/Dashboard/fetch_air_quality_data?year={year}",
            "retrieved_at_utc": "2026-10-23T15:47:20+00:00",
            "year_label": year,
            "raw_bytes": len(raw_bytes),
            "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "validated_station_rows": len(payload["station_data"]),
            "units": "AQI index (dimensionless)",
            "geographic_coverage": "Statewide",
            "period_cutoff": "Not supplied by endpoint",
            "reuse_terms": "Dataset-specific reuse terms were not located.",
        }
        sidecar.write_text(json.dumps(metadata), encoding="utf-8")
        return raw, sidecar, metadata


class StatusAndCatalogTests(TemporaryAuditCase):
    def test_status_definitions_are_canonical_and_machine_readable(self):
        status_file = ROOT / "data/reference/data_status_definitions.json"
        catalog = json.loads(status_file.read_text(encoding="utf-8"))
        self.assertEqual(set(catalog["statuses"]), set(DATA_STATUS_DEFINITIONS))
        self.assertTrue(all(value.strip() for value in catalog["statuses"].values()))

    def test_existing_catalogs_have_unique_ids_and_canonical_statuses(self):
        for path, key, id_field in (
            ("data/reference/air_quality_acquisition.json", "sources", "dataset_id"),
            ("data/reference/spatial_sources.json", "datasets", "layer_id"),
            ("data/reference/hydrology_data_sources.json", "station_metadata_sources", "source_id"),
        ):
            catalog = json.loads((ROOT / path).read_text(encoding="utf-8"))
            entries = catalog[key]
            ids = [entry.get("dataset_id", entry.get(id_field)) for entry in entries]
            statuses = [entry["evidence_status"] for entry in entries]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertTrue(all(ids))
            self.assertTrue(set(statuses).issubset(DATA_STATUS_DEFINITIONS))

    @pytest.mark.local_research(
        "data/processed/air_quality/kspcb_annual_aqi.metadata.json",
        "data/processed/air_quality/kspcb_annual_aqi.csv",
        "data/raw/air_quality/kspcb_annual_aqi_2023_20261023T154709Z.json",
        "data/raw/air_quality/kspcb_annual_aqi_2023_20261023T154709Z.metadata.json",
        "data/raw/air_quality/kspcb_annual_aqi_2024_20261023T154709Z.json",
        "data/raw/air_quality/kspcb_annual_aqi_2024_20261023T154709Z.metadata.json",
        "data/raw/air_quality/kspcb_annual_aqi_2025_20261023T154709Z.json",
        "data/raw/air_quality/kspcb_annual_aqi_2025_20261023T154709Z.metadata.json",
        "data/raw/air_quality/kspcb_annual_aqi_2026_20261023T154709Z.json",
        "data/raw/air_quality/kspcb_annual_aqi_2026_20261023T154709Z.metadata.json",
        "data/processed/air_quality/kspcb_air_reports.metadata.json",
        "data/raw/air_quality_reports/KSPCB_AQI_daily_average_2026-10-16.pdf",
        "data/raw/air_quality_reports/KSPCB_CAAQMS_monthly_report_2026-08.pdf",
        "data/raw/air_quality_reports/KSPCB_NAMP_report_2025-08.pdf",
        "data/processed/air_quality/kspcb_daily_aqi_2026-10-16.csv",
        "data/processed/air_quality/kspcb_daily_aqi_status_2026-10-16.csv",
        "data/processed/air_quality/kspcb_caaqms_eloor_daily_2026-08.csv",
        "data/processed/air_quality/kspcb_caaqms_eloor_aqi_2026-08.csv",
        "data/processed/air_quality/kspcb_caaqms_eloor_weather_2026-08.csv",
        "data/processed/air_quality/kspcb_namp_ernakulam_2025-06.csv",
        "data/processed/air_quality/kspcb_caaqms_eloor_2026-09.metadata.json",
        "data/raw/air_quality_reports/KSPCB_CAAQMS_monthly_report_2026-09.pdf",
        "data/raw/air_quality_reports/KSPCB_CAAQMS_monthly_report_2026-09.pdf.metadata.json",
        "data/raw/industrial/DIC_DA_Edayar_allotment_details_2022.pdf",
        "data/raw/industrial/DIC_DA_Edayar_allotment_details_2022.pdf.metadata.json",
        "data/raw/industrial/KWA_Edayar_CETP_DER_2022.pdf",
        "data/raw/industrial/KWA_Edayar_CETP_DER_2022.pdf.metadata.json",
        "data/raw/industrial/DIC_DA_EDAYAR.dwg",
        "data/raw/industrial/DIC_DA_EDAYAR.dwg.metadata.json",
        "data/raw/industrial/KSPCB_OCMMS_CTO_red_page2_2015-2019.html",
        "data/raw/industrial/KSPCB_OCMMS_CTO_red_page2_2015-2019.html.metadata.json",
    )
    def test_local_research_hashes_and_derived_output_hashes_match(self):
        report = build_ingestion_report(ROOT, validated_at_utc="2026-10-29T00:00:00+00:00")
        self.assertEqual(report["catalog_errors"], [])
        by_id = {item["dataset_id"]: item for item in report["recovered_sources"]}
        self.assertEqual(len([key for key in by_id if key.startswith("kspcb_annual_aqi_")]), 4)
        self.assertEqual(by_id["kspcb_annual_aqi_2026"]["row_count"], 41)
        self.assertEqual(by_id["kspcb_namp_ernakulam_2025_06"]["status"], "unsuitable")
        self.assertEqual(by_id["dic_edayar_site_plan"]["status"], "provisional")
        for item in by_id.values():
            self.assertEqual(item["validation_checks"].get("sha256", item["validation_checks"].get("dwg_signature")), "passed")
            for output in item["documented_derived_outputs"]:
                self.assertEqual(output["status"], "passed", output["path"])

    def test_audit_with_missing_optional_data_is_reported_without_prediction(self):
        (self.root / "data/reference").mkdir(parents=True)
        (self.root / "data/processed/air_quality").mkdir(parents=True)
        (self.root / "data/reference/spatial_sources.json").write_text(
            json.dumps({"datasets": []}), encoding="utf-8"
        )
        (self.root / "data/reference/air_quality_acquisition.json").write_text(
            json.dumps({"sources": []}), encoding="utf-8"
        )
        (self.root / "data/processed/air_quality/kspcb_annual_aqi.metadata.json").write_text(
            json.dumps({"raw_files": []}), encoding="utf-8"
        )
        first = build_ingestion_report(self.root, validated_at_utc="2026-10-29T00:00:00+00:00")
        second = build_ingestion_report(self.root, validated_at_utc="2026-10-29T00:00:00+00:00")
        self.assertEqual(first, second)
        self.assertTrue(first["recovered_sources"])
        self.assertTrue(all(item["status"] == "unavailable" for item in first["recovered_sources"]))
        self.assertEqual(first["flood_analysis"]["status"], "unavailable")
        self.assertFalse(first["flood_analysis"]["operational"])

    def test_real_flood_analysis_stays_blocked_with_named_source_evidence(self):
        (self.root / "data/reference").mkdir(parents=True)
        for catalog in ("spatial_sources.json", "air_quality_acquisition.json"):
            (self.root / "data/reference" / catalog).write_bytes(
                (ROOT / "data/reference" / catalog).read_bytes()
            )
        report = build_ingestion_report(self.root, validated_at_utc="2026-10-29T00:00:00+00:00")
        flood = report["flood_analysis"]
        self.assertEqual(flood["status"], "unavailable")
        self.assertFalse(flood["operational"])
        self.assertEqual(flood["conclusion"], "No real asset-to-flood exposure count is currently supported.")
        self.assertIn("ODbL 1.0", flood["available_hazard_context"])
        self.assertIn("CC BY 4.0", flood["available_hazard_context"])
        blockers = " ".join(flood["blockers"])
        for evidence in ("KSDMA", "NIHFW", "Sametham", "2022 flood-probability report", "OSM", "LRIS", "CWC", "NWIC", "Ernakulam district administration"):
            self.assertIn(evidence.casefold(), blockers.casefold())
        spatial = {item["dataset_id"]: item for item in report["spatial_catalog"]}
        self.assertEqual(spatial["schools_kerala_sametham"]["status"], "unavailable")
        self.assertEqual(spatial["flood_exposure_report_ksdma_2022"]["status"], "unavailable")
        self.assertEqual(spatial["flood_hazard_jrc_glofas_rp100"]["status"], "provisional")
        source_catalog = json.loads((self.root / "data/reference/spatial_sources.json").read_text(encoding="utf-8"))
        jrc = next(item for item in source_catalog["datasets"] if item["layer_id"] == "flood_hazard_jrc_glofas_rp100")
        self.assertIn("licence_resolved", jrc["status"])
        self.assertEqual(
            jrc["validation_status"],
            "MODELLED SCENARIO CONTEXT; LICENCE RESOLVED; "
            "PERMANENT-WATER EXCLUSION APPLIED; NOT OBSERVED FLOODING",
        )

    def test_new_cwc_and_nwic_hydrology_leads_do_not_create_spatial_data(self):
        catalog = json.loads((ROOT / "data/reference/hydrology_data_sources.json").read_text(encoding="utf-8"))
        sources = {item["source_id"]: item for item in catalog["station_metadata_sources"]}

        cwc = sources["cwc_kerala_station_register_2012"]
        self.assertEqual(cwc["evidence_status"], "provisional")
        self.assertEqual(cwc["feature_count"], 0)
        self.assertIsNone(cwc["local_file"])
        self.assertIn("Kalampur", cwc["source_content_reviewed"])
        self.assertIn("Not stated", cwc["coordinate_reference_system"])
        self.assertTrue(any("2012" in item for item in cwc["limitations"]))

        nwic = sources["nwic_kerala_sw_telemetry_hourly_2026_2030"]
        self.assertEqual(nwic["evidence_status"], "unavailable")
        self.assertEqual(nwic["feature_count"], 0)
        self.assertIsNone(nwic["local_file"])
        self.assertIn("cache-miss", nwic["retrieval_result"])
        self.assertIn("not_retrieved", nwic["status"])


class AnnualAqiValidationTests(TemporaryAuditCase):
    def test_null_optional_aqi_object_and_year_to_date_rows_are_validated_conservatively(self):
        raw, sidecar, _ = self._annual_input(aqi_data=None)
        result = validate_annual_aqi_file(raw, sidecar)
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["row_count"], 1)
        self.assertIn("not pollutant concentrations", " ".join(result["warnings"]).lower())

    def test_duplicate_station_rows_are_rejected(self):
        rows = [
            {"stn_code": "1", "station_name": "Eloor", "mode": "CAAQMS", "average_aqi": "88"},
            {"stn_code": "2", "station_name": "ELOOR", "mode": "caaqms", "average_aqi": "89"},
        ]
        raw, sidecar, _ = self._annual_input(rows=rows)
        result = validate_annual_aqi_file(raw, sidecar)
        self.assertEqual(result["status"], "unsuitable")
        self.assertTrue(any("duplicate" in error.lower() for error in result["errors"]))

    def test_missing_nonnumeric_or_out_of_range_values_are_rejected(self):
        for value in (None, "not available", "-1", "501", "NaN"):
            with self.subTest(value=value):
                row = {"stn_code": "1", "station_name": "Eloor", "mode": "NAMP", "average_aqi": value}
                raw, sidecar, _ = self._annual_input(rows=[row])
                self.assertEqual(validate_annual_aqi_file(raw, sidecar)["status"], "unsuitable")

    def test_invalid_retrieval_date_and_hash_mismatch_are_reported(self):
        raw, sidecar, metadata = self._annual_input()
        metadata["retrieved_at_utc"] = "2026-02-30T15:00:00+00:00"
        metadata["raw_sha256"] = "0" * 64
        sidecar.write_text(json.dumps(metadata), encoding="utf-8")
        result = validate_annual_aqi_file(raw, sidecar)
        self.assertEqual(result["status"], "unsuitable")
        self.assertEqual(result["checks"]["sha256"], "failed")
        self.assertTrue(any("retrieval date is invalid" in error.lower() for error in result["errors"]))

    def test_missing_provenance_fails_closed(self):
        raw, sidecar, _ = self._annual_input()
        sidecar.unlink()
        self.assertEqual(validate_annual_aqi_file(raw, sidecar)["status"], "unsuitable")

    def test_strict_json_rejects_duplicate_keys_and_nonstandard_numbers(self):
        duplicate = self.root / "duplicate.json"
        duplicate.write_text('{"station_data":[],"station_data":[]}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            read_json_strict(duplicate)
        nonstandard = self.root / "nan.json"
        nonstandard.write_text('{"value":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Non-standard JSON"):
            read_json_strict(nonstandard)


class DocumentValidationTests(TemporaryAuditCase):
    def _metadata(self, path, **extra):
        content = path.read_bytes()
        return {
            "publisher": "Test agency",
            "source_url": "https://example.test/source",
            "retrieved_on": "2026-10-29",
            "sha256": hashlib.sha256(content).hexdigest(),
            "bytes": len(content),
            "reuse_terms": "Terms not identified.",
            **extra,
        }

    def test_invalid_pdf_signature_is_unsuitable(self):
        path = self.root / "bad.pdf"
        path.write_bytes(b"<!DOCTYPE html><html></html>")
        result = validate_pdf_file(path, self._metadata(path))
        self.assertEqual(result["status"], "unsuitable")
        self.assertEqual(result["checks"]["pdf_signature"], "failed")

    def test_pdf_parser_failure_is_reported_when_parser_is_available(self):
        path = self.root / "broken.pdf"
        path.write_bytes(b"%PDF-1.7\nnot a complete PDF")
        metadata = self._metadata(path)
        fake = types.ModuleType("pypdf")
        fake.__spec__ = importlib.machinery.ModuleSpec("pypdf", loader=None)

        class BrokenReader:
            def __init__(self, *_args, **_kwargs):
                raise ValueError("broken fixture")

        fake.PdfReader = BrokenReader
        with mock.patch("src.ingestion_audit.importlib.util.find_spec", return_value=fake.__spec__):
            with mock.patch.dict(sys.modules, {"pypdf": fake}):
                result = validate_pdf_file(path, metadata)
        self.assertEqual(result["status"], "unsuitable")
        self.assertIn("PDF parsing failed", result["errors"][0])

    def test_html_audit_counts_structure_without_exposing_page_text(self):
        path = self.root / "public_listing.html"
        path.write_text(
            "<table><tr><td>public record</td></tr></table>"
            "<form><input name='q'></form><script src='https://example.test/a.js'></script>",
            encoding="utf-8",
        )
        result = validate_html_file(path, self._metadata(path))
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["html_summary"]["table_count"], 1)
        self.assertEqual(result["html_summary"]["form_count"], 1)
        self.assertEqual(result["html_summary"]["input_control_count"], 1)
        self.assertNotIn("public record", json.dumps(result))

    def test_dwg_signature_and_hash_are_checked_but_geometry_remains_unknown(self):
        path = self.root / "plan.dwg"
        path.write_bytes(b"AC1018" + b"fixture")
        metadata = self._metadata(path, drawing_format_signature="AutoCAD AC1018")
        result = validate_dwg_file(path, metadata)
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["checks"]["dwg_signature"], "passed")
        self.assertTrue(any("CRS" in warning for warning in result["warnings"]))

    def test_invalid_dwg_signature_is_not_promoted(self):
        path = self.root / "not_a_dwg.dwg"
        path.write_bytes(b"R12DXF")
        result = validate_dwg_file(path, self._metadata(path))
        self.assertEqual(result["status"], "unsuitable")


class SpatialReadinessRegressionTests(unittest.TestCase):
    def test_unknown_crs_and_missing_hazard_do_not_create_exposure(self):
        metadata = {
            "dataset_id": "fixture", "title": "Synthetic fixture",
            "source_url": "https://example.test", "publisher": "Test only",
            "retrieved_on": "2026-10-29", "publication_date": "2026-10-29",
            "license": "CC0", "crs": "EPSG:3857", "units": "metres",
            "geographic_coverage": "Synthetic test area", "limitations": ["Synthetic only"],
        }
        self.assertTrue(provenance_errors(metadata))
        self.assertTrue(geometry_intersects(_point(76.5, 9.5)["geometry"], _polygon()))
        result = classify_exposure([_point(76.5, 9.5)], None)
        self.assertEqual(result[0]["exposure_status"], "Unknown exposure")


if __name__ == "__main__":
    unittest.main()

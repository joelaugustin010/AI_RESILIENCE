"""Checks that the pollution page only presents source-verified context."""

import hashlib
import json
import unittest
from pathlib import Path

import pandas as pd
import pytest

from src.air_quality import (
    AirQualityDataError,
    cpcb_aqi_category,
    station_comparison,
    time_series_summary,
    validate_observations,
)
from src.air_quality_sources import (
    AirQualitySourceError,
    prepare_kspcb_annual_aqi,
)
from src.air_quality_attribution import (
    SOURCE_EVIDENCE_REQUIREMENTS,
    source_attribution_readiness,
)


ROOT = Path(__file__).resolve().parent
STATIONS = ["Eloor", "Vyttila"]


def observation_rows():
    return pd.DataFrame(
        [
            {
                "observed_at": "2026-06-01T08:00:00+05:30",
                "station": "ELOOR",
                "pollutant": "pm 2.5",
                "value": 20,
                "unit": "µg/m³",
                "averaging_period": "24-hour",
                "quality_flag": "VALID",
            },
            {
                "observed_at": "2026-06-01T08:00:00+05:30",
                "station": "Vyttila",
                "pollutant": "PM2.5",
                "value": 28,
                "unit": "ug/m3",
                "averaging_period": "24-hour",
                "quality_flag": "valid",
            },
            {
                "observed_at": "2026-06-02T08:00:00+05:30",
                "station": "Eloor",
                "pollutant": "PM2.5",
                "value": 900,
                "unit": "ug/m3",
                "averaging_period": "24-hour",
                "quality_flag": "suspect",
            },
        ]
    )


class AirQualityAcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = json.loads(
            (ROOT / "data" / "reference" / "air_quality_acquisition.json").read_text(encoding="utf-8")
        )
        cls.page = (ROOT / "app_pages" / "air_pollution.py").read_text(encoding="utf-8")

    def test_kspcb_station_inventory_is_source_linked_and_nonspatial(self):
        stations = self.register["kspcb_namp_ernakulam_stations"]
        self.assertEqual(len(stations), 7)
        self.assertTrue(all(row["program"] == "NAMP" for row in stations))
        self.assertTrue(all("latitude" not in row and "longitude" not in row for row in stations))
        kspcb = next(source for source in self.register["sources"] if "KSPCB" in source["publisher"])
        self.assertIn("kspcb.kerala.gov.in", kspcb["url"])
        self.assertIn("not", kspcb["reuse_status"].lower())

    def test_cpcb_source_is_catalogued_with_api_access_blocker(self):
        cpcb = next(source for source in self.register["sources"] if "CPCB" in source["publisher"])
        self.assertIn("data.gov.in", cpcb["url"])
        self.assertIn("API-key", cpcb["blocker"])
        self.assertIn("NDSAP", cpcb["evidence"])

    def test_illustrative_csv_is_explicitly_not_analyzed(self):
        self.assertIn("Illustrative sample only", self.page)
        self.assertNotIn('read_csv(ROOT / "data" / "raw" / "air_pollution_data.csv")', self.page)
        self.assertNotIn("load_dataset", self.page)
        self.assertIn("never used for this assessment", self.page)
        self.assertIn("cannot establish a source", self.page)

    def test_page_exposes_readiness_and_station_reference(self):
        self.assertIn("Near-real-time CAMS model estimate", self.page)
        self.assertIn("Historical KSPCB Eloor monthly reports", self.page)
        self.assertIn("NAMP report observations and station references", self.page)
        self.assertIn('register["not_obtained"]', self.page)
        self.assertIn('register["sources"]', self.page)
        self.assertIn("Dated Eloor pollutant trends", self.page)
        self.assertIn("date-only precision", self.page.lower())
        self.assertIn("aqi_values.mod(1).ne(0)", self.page)
        self.assertIn("float(raw_eloor_aqi).is_integer()", self.page)

    def test_page_separates_current_aqi_annual_summary_and_factory_assessment(self):
        self.assertIn("not live readings", self.page)
        self.assertIn("AQI categories and CPCB method", self.page)
        self.assertIn("No potential-source ranking is supported", self.page)
        self.assertIn("Historical water-effluent permissions are not air-emissions evidence", self.page)


class KspcbAnnualSummaryTests(unittest.TestCase):
    def test_source_station_mapping_requires_exact_name_and_matching_program(self):
        inventory = [
            {"station": "Eloor", "program": "NAMP"},
            {"station": "M.G. Road", "program": "NAMP"},
            {"station": "Vyttila", "program": "NAMP"},
            {"station": "Kalamessery", "program": "NAMP"},
        ]
        rows = prepare_kspcb_annual_aqi(
            {
                "station_data": [
                    {"stn_code": "545", "station_name": "M G ROAD", "mode": "NAMP", "average_aqi": "52.3"},
                    {"stn_code": "544", "station_name": "VYTTILA", "mode": "NAMP", "average_aqi": "58"},
                    {"stn_code": "KLCAAQMS04", "station_name": "ELOOR", "mode": "CAAQMS", "average_aqi": "52"},
                    {"stn_code": "546", "station_name": "KALAMASSERY", "mode": "NAMP", "average_aqi": "57"},
                ]
            },
            2026,
            inventory,
        )
        matches = rows.set_index("source_station")["reference_station"]
        self.assertEqual(matches["M G ROAD"], "M.G. Road")
        self.assertEqual(matches["VYTTILA"], "Vyttila")
        self.assertTrue(pd.isna(matches["ELOOR"]))
        self.assertTrue(pd.isna(matches["KALAMASSERY"]))

    def test_invalid_and_duplicate_annual_summary_rows_are_rejected(self):
        inventory = [{"station": "Vyttila", "program": "NAMP"}]
        invalid = {"station_data": [{"station_name": "VYTTILA", "mode": "NAMP", "average_aqi": "NaN"}]}
        with self.assertRaisesRegex(AirQualitySourceError, "average_aqi is not finite"):
            prepare_kspcb_annual_aqi(invalid, 2026, inventory)

        out_of_range = {"station_data": [{"station_name": "VYTTILA", "mode": "NAMP", "average_aqi": "501"}]}
        with self.assertRaisesRegex(AirQualitySourceError, "outside 0-500"):
            prepare_kspcb_annual_aqi(out_of_range, 2026, inventory)

        duplicate = {
            "station_data": [
                {"station_name": "VYTTILA", "mode": "NAMP", "average_aqi": "60"},
                {"station_name": "Vyttila", "mode": "NAMP", "average_aqi": "61"},
            ]
        }
        with self.assertRaisesRegex(AirQualitySourceError, "Duplicate station summary"):
            prepare_kspcb_annual_aqi(duplicate, 2026, inventory)

    @pytest.mark.local_research(
        "data/processed/air_quality/kspcb_annual_aqi.csv",
        "data/processed/air_quality/kspcb_annual_aqi.metadata.json",
        "data/raw/air_quality/kspcb_annual_aqi_2023_20261023T154709Z.json",
        "data/raw/air_quality/kspcb_annual_aqi_2023_20261023T154709Z.metadata.json",
        "data/raw/air_quality/kspcb_annual_aqi_2024_20261023T154709Z.json",
        "data/raw/air_quality/kspcb_annual_aqi_2024_20261023T154709Z.metadata.json",
        "data/raw/air_quality/kspcb_annual_aqi_2025_20261023T154709Z.json",
        "data/raw/air_quality/kspcb_annual_aqi_2025_20261023T154709Z.metadata.json",
        "data/raw/air_quality/kspcb_annual_aqi_2026_20261023T154709Z.json",
        "data/raw/air_quality/kspcb_annual_aqi_2026_20261023T154709Z.metadata.json",
    )
    def test_downloaded_summaries_are_labeled_and_not_pollutant_observations(self):
        summary_path = ROOT / "data" / "processed" / "air_quality" / "kspcb_annual_aqi.csv"
        metadata_path = ROOT / "data" / "processed" / "air_quality" / "kspcb_annual_aqi.metadata.json"
        rows = pd.read_csv(summary_path)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 130)
        self.assertEqual(rows["year"].unique().tolist(), [2023, 2024, 2025, 2026])
        self.assertEqual(int(rows["reference_station"].notna().sum()), 9)
        self.assertTrue(metadata["not_pollutant_observations"])
        source_directory = ROOT / "data" / "raw" / "air_quality"
        for source in metadata["raw_files"]:
            source_path = source_directory / source["path"]
            source_metadata_path = source_directory / source["metadata"]
            self.assertTrue(
                source_path.is_file(),
                f"Missing required KSPCB source data: {source_path.relative_to(ROOT)}. "
                "Run `python scripts/acquire_air_quality_sources.py` first.",
            )
            self.assertTrue(
                source_metadata_path.is_file(),
                f"Missing required KSPCB source metadata: {source_metadata_path.relative_to(ROOT)}. "
                "Run `python scripts/acquire_air_quality_sources.py` first.",
            )
            raw_bytes = source_path.read_bytes()
            source_metadata = json.loads(source_metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(hashlib.sha256(raw_bytes).hexdigest(), source["sha256"])
            self.assertEqual(source_metadata["raw_sha256"], source["sha256"])
            self.assertIn("period_cutoff", source_metadata)


class CpcbAqiCategoryTests(unittest.TestCase):
    def test_official_category_edges_and_meanings(self):
        self.assertEqual(cpcb_aqi_category(50)[0], "Good")
        self.assertEqual(cpcb_aqi_category(51)[0], "Satisfactory")
        self.assertEqual(cpcb_aqi_category(101)[0], "Moderately polluted")
        self.assertEqual(cpcb_aqi_category(201)[0], "Poor")
        self.assertEqual(cpcb_aqi_category(301)[0], "Very Poor")
        self.assertEqual(cpcb_aqi_category(401)[0], "Severe")
        self.assertIn("sensitive people", cpcb_aqi_category(51)[1])

    def test_invalid_aqi_values_are_rejected(self):
        for value in (-1, 50.5, 501, float("nan"), "not AQI"):
            with self.subTest(value=value), self.assertRaises(AirQualityDataError):
                cpcb_aqi_category(value)


class VerifiedAirQualityPipelineTests(unittest.TestCase):
    def test_unverified_rows_are_rejected(self):
        with self.assertRaisesRegex(AirQualityDataError, "Unverified"):
            validate_observations(observation_rows(), STATIONS, verified=False)

    def test_validates_and_summarizes_only_valid_observations(self):
        validated = validate_observations(observation_rows(), STATIONS, verified=True)

        self.assertTrue(validated.attrs["ai_resilience_verified_air_quality"])
        self.assertEqual(validated.loc[0, "station"], "Eloor")
        self.assertEqual(validated.loc[0, "pollutant"], "PM2.5")
        self.assertEqual(str(validated.loc[0, "observed_at"].tz), "UTC")

        comparison = station_comparison(validated, "PM2.5")
        self.assertEqual(comparison["station"].tolist(), ["Eloor", "Vyttila"])
        self.assertEqual(comparison["observation_count"].tolist(), [1, 1])
        self.assertEqual(comparison["mean_value"].tolist(), [20.0, 28.0])

        series = time_series_summary(validated, "PM2.5")
        self.assertEqual(len(series), 2)
        self.assertEqual(series["station"].tolist(), ["Eloor", "Vyttila"])

    def test_analysis_requires_validator_output(self):
        with self.assertRaisesRegex(AirQualityDataError, "Run validate_observations"):
            station_comparison(observation_rows(), "PM2.5")

    def test_cpcb_lead_pollutant_is_supported_in_verified_observation_schema(self):
        rows = observation_rows().iloc[[0]].copy()
        rows["pollutant"] = "Pb"
        validated = validate_observations(rows, STATIONS, verified=True)
        self.assertEqual(validated.loc[0, "pollutant"], "Pb")
        self.assertEqual(validated.loc[0, "unit"], "ug/m3")

    def test_missing_fields_and_naive_timestamps_are_rejected(self):
        rows = observation_rows()
        rows.loc[0, "station"] = " "
        with self.assertRaisesRegex(AirQualityDataError, "Missing values.*station"):
            validate_observations(rows, STATIONS, verified=True)

        rows = observation_rows()
        rows.loc[0, "value"] = pd.NA
        with self.assertRaisesRegex(AirQualityDataError, "Missing values.*value"):
            validate_observations(rows, STATIONS, verified=True)

        rows = observation_rows()
        rows.loc[0, "observed_at"] = "2026-06-01 08:00:00"
        with self.assertRaisesRegex(AirQualityDataError, "must include a timezone"):
            validate_observations(rows, STATIONS, verified=True)

    def test_unknown_station_incompatible_unit_and_negative_values_are_rejected(self):
        rows = observation_rows()
        rows.loc[0, "station"] = "Unknown"
        with self.assertRaisesRegex(AirQualityDataError, "Unknown monitoring station"):
            validate_observations(rows, STATIONS, verified=True)

        rows = observation_rows()
        rows.loc[0, "unit"] = "mg/m3"
        with self.assertRaisesRegex(AirQualityDataError, "not supported for pollutant PM2.5"):
            validate_observations(rows, STATIONS, verified=True)

        rows = observation_rows()
        rows.loc[0, "pollutant"] = "PM1"
        with self.assertRaisesRegex(AirQualityDataError, "Unsupported pollutant"):
            validate_observations(rows, STATIONS, verified=True)

        rows = observation_rows()
        rows.loc[0, "value"] = -1
        with self.assertRaisesRegex(AirQualityDataError, "Negative pollutant"):
            validate_observations(rows, STATIONS, verified=True)

    def test_legacy_illustrative_fixture_does_not_match_observation_schema(self):
        sample = pd.DataFrame({"Year": [2020], "PM2.5": [42]})
        with self.assertRaisesRegex(AirQualityDataError, "Missing required column"):
            validate_observations(sample, STATIONS, verified=True)

    def test_duplicate_station_measurement_identity_is_rejected(self):
        rows = observation_rows()
        duplicate = pd.concat([rows, rows.iloc[[0]]], ignore_index=True)
        with self.assertRaisesRegex(AirQualityDataError, "Duplicate station"):
            validate_observations(duplicate, STATIONS, verified=True)

    def test_source_date_precision_is_preserved_without_inventing_a_time(self):
        path = ROOT / "data" / "processed" / "air_quality" / "kspcb_caaqms_eloor_daily_2026-08.csv"
        raw = pd.read_csv(path)
        validated = validate_observations(raw, ["Eloor"], verified=True)

        self.assertEqual(len(validated), 279)
        self.assertEqual(validated.loc[0, "observed_at"], "2026-08-01")
        self.assertEqual(validated.loc[0, "timestamp_precision"], "day")
        self.assertEqual(set(validated["quality_flag"]), {"unassessed"})
        with self.assertRaisesRegex(AirQualityDataError, "No eligible PM2.5"):
            station_comparison(validated, "PM2.5")

        comparison = station_comparison(validated, "PM2.5", include_unassessed=True)
        self.assertEqual(comparison.loc[0, "station"], "Eloor")
        self.assertEqual(comparison.loc[0, "observation_count"], 31)
        series = time_series_summary(validated, "PM2.5", include_unassessed=True)
        self.assertEqual(len(series), 31)
        self.assertEqual(series.loc[0, "mean_value"], 21.02)

    def test_date_only_and_timestamp_rows_cannot_be_mixed(self):
        rows = observation_rows()
        rows.loc[0, "observed_at"] = "2026-06-01"
        with self.assertRaisesRegex(AirQualityDataError, "cannot be mixed"):
            validate_observations(rows, STATIONS, verified=True)


class KspcbReportExtractTests(unittest.TestCase):
    def test_report_extract_counts_and_source_dates(self):
        processed = ROOT / "data" / "processed" / "air_quality"
        monthly = pd.read_csv(processed / "kspcb_caaqms_eloor_daily_2026-08.csv")
        monthly_aqi = pd.read_csv(processed / "kspcb_caaqms_eloor_aqi_2026-08.csv")
        monthly_weather = pd.read_csv(processed / "kspcb_caaqms_eloor_weather_2026-08.csv")
        daily = pd.read_csv(processed / "kspcb_daily_aqi_2026-10-16.csv")
        daily_status = pd.read_csv(processed / "kspcb_daily_aqi_status_2026-10-16.csv")

        self.assertEqual(len(monthly), 31 * 9)
        self.assertEqual(len(monthly_aqi), 31)
        self.assertEqual(len(monthly_weather), 31)
        self.assertEqual(len(daily), 5)
        self.assertEqual(len(daily_status), 4)
        self.assertEqual(daily.loc[daily["station"].eq("Eloor"), "source_aqi"].item(), 62)
        self.assertEqual(set(monthly["unit"]), {"ug/m3", "mg/m3"})
        self.assertTrue(monthly["averaging_period"].str.contains("not stated").all())
        self.assertEqual(set(daily_status["source_status"]), {"INSUFFICIENT DATA", "POWER FAILURE"})

    def test_namp_extract_preserves_report_month_mismatch_and_missing_units(self):
        processed = ROOT / "data" / "processed" / "air_quality"
        namp = pd.read_csv(processed / "kspcb_namp_ernakulam_2025-06.csv")
        metadata = json.loads((processed / "kspcb_air_reports.metadata.json").read_text(encoding="utf-8"))

        self.assertEqual(len(namp), 62)
        self.assertEqual(set(pd.to_datetime(namp["observed_at"]).dt.strftime("%Y-%m")), {"2025-06"})
        self.assertEqual(namp["station_code"].nunique(), 8)
        self.assertTrue(namp["unit_status"].str.contains("not stated").all())
        self.assertIn(
            "Some coordinates vary within the Kuttippadam page",
            " ".join(metadata["sources"]["namp"]["limitations"]),
        )
        self.assertIn(
            "pypdf emitted four unresolved indirect-object warnings",
            " ".join(metadata["sources"]["namp"]["limitations"]),
        )
        self.assertTrue(namp["latitude"].notna().all())

    def test_industrial_inventory_is_candidate_only_and_has_no_firm_coordinates(self):
        inventory = pd.read_csv(
            ROOT / "data" / "processed" / "industrial" / "edayar_candidate_facilities.csv"
        )
        self.assertEqual(len(inventory), 8)
        self.assertTrue(inventory["facility_latitude"].isna().all())
        self.assertTrue(inventory["facility_longitude"].isna().all())
        self.assertEqual(set(inventory["coordinates_status"]), {"unavailable"})
        self.assertTrue(inventory["measured_emissions_value"].isna().all())
        self.assertEqual(set(inventory["measured_emissions_status"]), {"unavailable"})
        self.assertTrue(inventory["ranking_status"].str.contains("not ranked").all())


class SourceAttributionEvidenceGateTests(unittest.TestCase):
    def test_incomplete_source_evidence_never_returns_a_ranking_or_confidence(self):
        result = source_attribution_readiness({})
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertFalse(result["eligible_for_ranking"])
        self.assertEqual(result["ranking"], [])
        self.assertIsNone(result["confidence"])
        self.assertEqual(len(result["missing_evidence"]), len(SOURCE_EVIDENCE_REQUIREMENTS))

    def test_complete_evidence_only_opens_review_gate_and_never_fabricates_a_score(self):
        result = source_attribution_readiness(
            {field: True for field in SOURCE_EVIDENCE_REQUIREMENTS}
        )
        self.assertEqual(result["status"], "ready_for_method_review")
        self.assertTrue(result["eligible_for_ranking"])
        self.assertEqual(result["ranking"], [])
        self.assertIsNone(result["confidence"])


if __name__ == "__main__":
    unittest.main()

"""Tests for conservative, evidence-gated industrial-source assessment."""

import unittest
from datetime import date

import pandas as pd

from src.air_quality import AirQualityDataError
from src.air_quality_attribution import (
    INSUFFICIENT_ATTRIBUTION_MESSAGE,
    assess_industrial_sources,
    validate_attribution_observations,
)


SOURCE_URL = "https://kspcb.kerala.gov.in/reports/air-quality.pdf"
VERIFIED_DOCUMENT = {
    "evidence_status": "verified",
    "description": "Reviewed source document for the evidence domain.",
    "source_url": SOURCE_URL,
    "retrieved_on": "2026-10-25",
}


def ambient_rows(*, observed_at="2026-10-25T08:00:00+00:00", quality_flag="valid"):
    return pd.DataFrame(
        [
            {
                "observed_at": observed_at,
                "station": "Eloor",
                "station_id": "EL-01",
                "pollutant": "PM2.5",
                "value": 18.5,
                "unit": "ug/m3",
                "averaging_period": "1-hour",
                "quality_flag": quality_flag,
                "source_url": SOURCE_URL,
            }
        ]
    )


def facility(facility_id="E-1", **updates):
    result = {
        "facility_id": facility_id,
        "official_name": f"Facility {facility_id}",
        "coordinates_status": "unavailable",
        "facility_latitude": "",
        "facility_longitude": "",
        "coordinate_uncertainty": "Not quantifiable",
        "measured_emissions_status": "unavailable",
        "measured_emissions_value": "",
        "emissions_limits_value": "PM 100 mg/Nm3",
        "emissions_limits_status": "historical",
        "current_consent_evidence_status": "unverified",
    }
    result.update(updates)
    return result


class AssessmentObservationValidationTests(unittest.TestCase):
    def test_valid_measurement_preserves_source_units_dates_station_and_provenance(self):
        source = ambient_rows(observed_at="2026-10-25")
        validated = validate_attribution_observations(
            source, ["Eloor"], provenance_verified=True, as_of=date(2026, 10, 25)
        )

        row = validated.iloc[0]
        self.assertEqual(row["source_observed_at"], "2026-10-25")
        self.assertEqual(row["source_station_label"], "Eloor")
        self.assertEqual(row["source_station_identifier"], "EL-01")
        self.assertEqual(row["source_unit"], "ug/m3")
        self.assertEqual(row["source_url"], SOURCE_URL)
        self.assertEqual(row["timestamp_precision"], "day")
        self.assertEqual(row["temporal_status"], "current")
        self.assertEqual(row["evidence_type"], "measured")
        # Validation returns a copy and leaves the source record intact.
        self.assertEqual(source.loc[0, "observed_at"], "2026-10-25")

    def test_source_urls_require_a_valid_https_host_without_credentials(self):
        invalid_urls = (
            "http://kspcb.kerala.gov.in/report.pdf",
            "https://",
            "https://user:password@kspcb.kerala.gov.in/report.pdf",
            "https://kspcb.kerala.gov.in:invalid/report.pdf",
            "https://kspcb.kerala.gov.in/reports/air quality.pdf",
        )
        for source_url in invalid_urls:
            with self.subTest(source_url=source_url):
                source = ambient_rows()
                source.loc[0, "source_url"] = source_url
                with self.assertRaisesRegex(AirQualityDataError, "HTTPS source_url"):
                    validate_attribution_observations(
                        source, ["Eloor"], provenance_verified=True, as_of="2026-10-25"
                    )

    def test_evidence_action_plan_explains_all_gates_and_missing_actions(self):
        from src.air_quality_attribution import (
            SOURCE_EVIDENCE_REQUIREMENTS,
            evidence_action_plan,
        )

        plan = evidence_action_plan({"observation_window": True})
        self.assertEqual(len(plan), len(SOURCE_EVIDENCE_REQUIREMENTS))
        self.assertEqual(plan[0]["status"], "Available for review")
        self.assertEqual(plan[1]["status"], "Missing")
        self.assertTrue(all(item["next_action"].strip() for item in plan))
        self.assertIn("Permit limits are not measurements", plan[2]["next_action"])

    def test_evidence_action_plan_rejects_unknown_fields(self):
        from src.air_quality_attribution import evidence_action_plan

        with self.assertRaisesRegex(ValueError, "Unknown source-evidence"):
            evidence_action_plan({"factory_distance": True})

    def test_missing_timestamp_and_unit_are_rejected(self):
        missing_timestamp = ambient_rows()
        missing_timestamp.loc[0, "observed_at"] = None
        with self.assertRaisesRegex(AirQualityDataError, "observed_at"):
            validate_attribution_observations(
                missing_timestamp, ["Eloor"], provenance_verified=True, as_of="2026-10-25"
            )

        missing_unit = ambient_rows().drop(columns=["unit"])
        with self.assertRaisesRegex(AirQualityDataError, "unit"):
            validate_attribution_observations(
                missing_unit, ["Eloor"], provenance_verified=True, as_of="2026-10-25"
            )

    def test_invalid_measurement_and_unverified_provenance_are_rejected(self):
        invalid = ambient_rows()
        invalid.loc[0, "value"] = -1
        with self.assertRaisesRegex(AirQualityDataError, "Negative pollutant"):
            validate_attribution_observations(
                invalid, ["Eloor"], provenance_verified=True, as_of="2026-10-25"
            )

        with self.assertRaisesRegex(AirQualityDataError, "Unverified observations"):
            validate_attribution_observations(
                ambient_rows(), ["Eloor"], provenance_verified=False, as_of="2026-10-25"
            )

    def test_historical_and_current_dates_are_labeled_separately(self):
        rows = pd.concat(
            [ambient_rows(observed_at="2026-10-24"), ambient_rows(observed_at="2026-10-25")],
            ignore_index=True,
        )
        validated = validate_attribution_observations(
            rows, ["Eloor"], provenance_verified=True, as_of="2026-10-25"
        )
        self.assertEqual(validated["temporal_status"].tolist(), ["historical", "current"])

    def test_date_only_observations_need_a_daily_window(self):
        day_only = ambient_rows(observed_at="2026-10-25")
        day_only.loc[0, "averaging_period"] = "1-hour"
        result = assess_industrial_sources(
            [facility()],
            day_only,
            ["Eloor"],
            None,
            as_of="2026-10-25",
            ambient_provenance_verified=True,
        )
        self.assertFalse(result["candidates"][0]["evidence"]["observation_window"])


class IndustrialSourceAssessmentTests(unittest.TestCase):
    def test_missing_coordinates_and_stack_emissions_block_each_candidate(self):
        candidates = [facility("E-1"), facility("E-2")]
        result = assess_industrial_sources(
            candidates,
            ambient_rows(),
            ["Eloor"],
            None,
            as_of="2026-10-25",
            ambient_provenance_verified=True,
        )

        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertEqual(result["message"], INSUFFICIENT_ATTRIBUTION_MESSAGE)
        self.assertEqual(result["ranking"], [])
        self.assertIsNone(result["confidence"])
        self.assertEqual(len(result["candidates"]), 2)
        for candidate in result["candidates"]:
            self.assertFalse(candidate["evidence"]["facility_locations"])
            self.assertFalse(candidate["evidence"]["pollutant_emissions"])
            self.assertFalse(candidate["evidence"]["consent_is_stack_emissions_evidence"])
            self.assertEqual(candidate["explanation"], INSUFFICIENT_ATTRIBUTION_MESSAGE)

    def test_permit_limits_do_not_count_as_measured_stack_emissions(self):
        result = assess_industrial_sources(
            [facility(emissions_limits_value="PM 80 mg/Nm3")],
            ambient_rows(),
            ["Eloor"],
            None,
            as_of="2026-10-25",
            ambient_provenance_verified=True,
        )
        candidate_result = result["candidates"][0]
        self.assertFalse(candidate_result["evidence"]["pollutant_emissions"])
        self.assertEqual(candidate_result["evidence"]["inventory_emissions_limits_status"], "historical")
        self.assertEqual(candidate_result["evidence"]["current_consent_evidence_status"], "unverified")
        self.assertFalse(candidate_result["evidence"]["consent_is_stack_emissions_evidence"])

        permit_record = {
            "record_type": "permit_limit",
            "evidence_type": "measured",
            "evidence_status": "verified",
            "pollutant": "PM2.5",
            "value": 80,
            "unit": "mg/Nm3",
            "sampled_at": "2026-10-25",
            "reporting_authority": "KSPCB",
            "source_url": SOURCE_URL,
            "retrieved_on": "2026-10-25",
        }
        permit_result = assess_industrial_sources(
            [facility(stack_emissions=[permit_record])],
            ambient_rows(),
            ["Eloor"],
            None,
            as_of="2026-10-25",
            ambient_provenance_verified=True,
        )
        self.assertFalse(permit_result["candidates"][0]["evidence"]["pollutant_emissions"])

    def test_absent_ambient_data_is_reported_as_missing(self):
        result = assess_industrial_sources(
            [facility()], None, ["Eloor"], None, as_of="2026-10-25"
        )
        self.assertEqual(result["ambient_evidence"]["evidence_type"], "missing")
        self.assertEqual(result["ambient_evidence"]["validated_record_count"], 0)
        self.assertIn("No ambient concentration", result["ambient_evidence"]["excluded_reason"])

    def test_illustrative_estimated_and_unverified_records_are_excluded(self):
        for evidence_type, provenance, phrase in (
            ("illustrative", True, "Illustrative records"),
            ("estimated", True, "Estimated records"),
            ("unverified", False, "lack verified source provenance"),
        ):
            with self.subTest(evidence_type=evidence_type):
                result = assess_industrial_sources(
                    [facility()],
                    ambient_rows(),
                    ["Eloor"],
                    None,
                    as_of="2026-10-25",
                    ambient_evidence_type=evidence_type,
                    ambient_provenance_verified=provenance,
                )
                self.assertEqual(result["ambient_evidence"]["quality_eligible_record_count"], 0)
                self.assertIn(phrase, result["ambient_evidence"]["excluded_reason"])
                self.assertEqual(result["ranking"], [])

    def test_unassessed_ambient_rows_are_descriptive_only(self):
        result = assess_industrial_sources(
            [facility()],
            ambient_rows(quality_flag="unassessed"),
            ["Eloor"],
            None,
            as_of="2026-10-25",
            ambient_provenance_verified=True,
        )
        self.assertEqual(result["ambient_evidence"]["validated_record_count"], 1)
        self.assertEqual(result["ambient_evidence"]["quality_eligible_record_count"], 0)
        self.assertFalse(result["candidates"][0]["evidence"]["observation_window"])
        self.assertEqual(result["status"], "insufficient_evidence")

    def test_validated_evidence_only_reaches_method_review_and_never_attributes(self):
        candidate = facility(
            coordinates_status="verified",
            facility_latitude="10.1",
            facility_longitude="76.3",
            coordinate_reference_system="EPSG:4326",
            coordinates_source_url=SOURCE_URL,
            coordinates_retrieved_on="2026-10-25",
            stack_emissions=[
                {
                    "record_type": "measured_stack_emission",
                    "evidence_type": "measured",
                    "evidence_status": "verified",
                    "pollutant": "PM2.5",
                    "value": 2.3,
                    "unit": "mg/Nm3",
                    "sampled_at": "2026-10-25T08:00:00+00:00",
                    "reporting_authority": "KSPCB",
                    "source_url": SOURCE_URL,
                    "retrieved_on": "2026-10-25",
                }
            ],
            source_signature_evidence=VERIFIED_DOCUMENT,
        )
        meteorology = pd.DataFrame(
            [
                {
                    "observed_at": "2026-10-25T08:00:00+00:00",
                    "station": "Eloor",
                    "wind_speed": 1.2,
                    "wind_speed_unit": "m/s",
                    "wind_direction": 90,
                    "wind_direction_unit": "degrees",
                    "averaging_period": "1-hour",
                    "source_url": SOURCE_URL,
                }
            ]
        )
        result = assess_industrial_sources(
            [candidate],
            ambient_rows(),
            ["Eloor"],
            meteorology,
            as_of="2026-10-25",
            ambient_provenance_verified=True,
            meteorology_provenance_verified=True,
            meteorology_site_verified=True,
            context_evidence={
                "alternatives_and_background": VERIFIED_DOCUMENT,
                "transport_method": VERIFIED_DOCUMENT,
            },
        )
        self.assertEqual(result["status"], "ready_for_method_review")
        self.assertFalse(result["eligible_for_attribution"])
        self.assertEqual(result["ranking"], [])
        self.assertIsNone(result["confidence"])

    def test_unverified_or_missing_coordinates_and_emissions_are_not_repaired(self):
        candidate = facility(
            coordinates_status="unverified",
            facility_latitude="10.1",
            facility_longitude="76.3",
            stack_emissions=[
                {
                    "record_type": "measured_stack_emission",
                    "evidence_type": "measured",
                    "evidence_status": "unverified",
                    "pollutant": "PM2.5",
                    "value": 2,
                    "unit": "mg/Nm3",
                    "sampled_at": "2026-10-25",
                    "reporting_authority": "Unknown",
                    "source_url": SOURCE_URL,
                    "retrieved_on": "2026-10-25",
                }
            ],
        )
        result = assess_industrial_sources(
            [candidate],
            ambient_rows(),
            ["Eloor"],
            None,
            as_of="2026-10-25",
            ambient_provenance_verified=True,
        )
        self.assertFalse(result["candidates"][0]["evidence"]["facility_locations"])
        self.assertFalse(result["candidates"][0]["evidence"]["pollutant_emissions"])
        self.assertEqual(result["message"], INSUFFICIENT_ATTRIBUTION_MESSAGE)


if __name__ == "__main__":
    unittest.main()

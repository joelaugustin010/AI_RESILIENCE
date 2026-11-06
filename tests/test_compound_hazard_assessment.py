"""Tests for the evidence-aware cyclone/flood scenario engine."""
import unittest
from datetime import date
from src.compound_hazard_assessment import assess_compound_scenario

class CompoundHazardAssessmentTests(unittest.TestCase):
    def base(self, **overrides):
        values = {
            "area": "Kochi", "hazards": ["Flood", "Cyclone"],
            "services": ["Hospitals", "Roads and bridges", "Drainage"],
            "evidence_type": "Hypothetical scenario",
            "evidence_source": "User-defined exercise",
            "observation_time": "2026-11-02T10:00:00+05:30",
            "period_start": date(2026, 11, 2), "period_end": date(2026, 11, 3),
        }
        values.update(overrides)
        return values

    def test_compound_interaction_pathway_is_included(self):
        result = assess_compound_scenario(self.base())
        self.assertTrue(result["compound"])
        self.assertEqual(result["status"], "SCENARIO_REVIEW_ONLY_NOT_A_VALIDATED_FORECAST")
        self.assertTrue(any(p["hazard"] == "Multi-hazard interaction" for p in result["pathways"]))

    def test_no_probability_or_damage_estimate_is_generated(self):
        result = assess_compound_scenario(self.base(rainfall_mm=120, river_level_m=4.2))
        self.assertFalse(result["numerical_probability_provided"])
        self.assertFalse(result["damage_or_casualty_estimate_provided"])
        self.assertIsNone(result["reported_inputs"]["river_reference_level_m"])

    def test_threshold_comparison_requires_both_values(self):
        result = assess_compound_scenario(self.base(
            river_level_m=4.2, river_reference_level_m=4.0,
            river_gauge_id="CWC-001", river_gauge_datum="m above gauge zero",
        ))
        self.assertEqual(len(result["reference_comparisons"]), 1)
        self.assertEqual(result["reference_comparisons"][0]["result"], "At or above supplied reference")

    def test_missing_threshold_does_not_invent_danger_level(self):
        result = assess_compound_scenario(self.base(river_level_m=4.2))
        self.assertEqual(result["reference_comparisons"], [])

    def test_rainfall_reference_requires_matching_station_and_period(self):
        mismatch = assess_compound_scenario(self.base(
            rainfall_mm=80, rainfall_reference_mm=60,
            rainfall_station_id="RG-1", rainfall_period="24 h",
            rainfall_reference_station_id="RG-1", rainfall_reference_period="1 h",
        ))
        self.assertEqual(mismatch["reference_comparisons"], [])
        self.assertTrue(any("Rainfall reference not compared" in gap for gap in mismatch["data_gaps"]))
        matched = assess_compound_scenario(self.base(
            rainfall_mm=80, rainfall_reference_mm=60,
            rainfall_station_id="RG-1", rainfall_period="24 h",
            rainfall_reference_station_id="RG-1", rainfall_reference_period="24 h",
        ))
        self.assertEqual(matched["reference_comparisons"][0]["measure"], "Rainfall")
        wrong_station = assess_compound_scenario(self.base(
            rainfall_mm=80, rainfall_reference_mm=60,
            rainfall_station_id="RG-1", rainfall_period="24 h",
            rainfall_reference_station_id="RG-2", rainfall_reference_period="24 h",
        ))
        self.assertEqual(wrong_station["reference_comparisons"], [])

    def test_service_review_contains_hazard_and_compound_pathways(self):
        result = assess_compound_scenario(self.base())
        hospital = next(x for x in result["service_reviews"] if x["service"] == "Hospitals")
        self.assertEqual(len(hospital["review_points"]), 3)

    def test_rainfall_drainage_compound_reviews_infrastructure_component(self):
        result = assess_compound_scenario(self.base(
            hazards=["Compound: heavy rainfall + drainage failure"],
            services=["Drainage"],
        ))
        drainage = next(item for item in result["service_reviews"] if item["service"] == "Drainage")
        self.assertTrue(any("Infrastructure failure:" in point for point in drainage["review_points"]))
        self.assertTrue(any("Flood" in point or "drain" in point.lower() for point in drainage["review_points"]))

    def test_invalid_hazard_and_negative_measurement_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_compound_scenario(self.base(hazards=["Wildfire"]))
        with self.assertRaises(ValueError):
            assess_compound_scenario(self.base(rainfall_mm=-1))

    def test_end_date_cannot_precede_start_date(self):
        with self.assertRaisesRegex(ValueError, "end date"):
            assess_compound_scenario(self.base(period_start=date(2026, 11, 3), period_end=date(2026, 11, 2)))

    def test_registered_compound_option_expands_component_level_evidence_gaps(self):
        result = assess_compound_scenario(self.base(
            hazards=["Compound: cyclone + flood"],
            rainfall_mm=80,
            cyclone_distance_km=120,
        ))
        self.assertEqual(set(result["components"]), {"Cyclone", "Flood"})
        self.assertIn("Rainfall accumulation period", result["data_gaps"])
        self.assertIn("Rainfall station ID", result["data_gaps"])
        self.assertIn("Cyclone track-fix timestamp", result["data_gaps"])
        self.assertIn("Cyclone storm ID or official storm name", result["data_gaps"])

    def test_registered_compound_option_checks_date_types(self):
        with self.assertRaisesRegex(ValueError, "start date must be a date"):
            assess_compound_scenario(self.base(period_start="not-a-date"))

    def test_drainage_and_infrastructure_status_are_reported_with_verification_gaps(self):
        result = assess_compound_scenario(self.base(
            hazards=["Compound: heavy rainfall + drainage failure"],
            drainage_status="Reported failed",
            infrastructure_status="Disruption reported by user",
        ))
        self.assertEqual(result["reported_inputs"]["drainage_status"], "Reported failed")
        self.assertEqual(result["reported_inputs"]["infrastructure_status"], "Disruption reported by user")
        self.assertTrue(any("Geotagged drainage inspection" in gap for gap in result["data_gaps"]))
        self.assertTrue(any("affected asset ID" in gap for gap in result["data_gaps"]))

    def test_non_finite_measurements_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            assess_compound_scenario(self.base(rainfall_mm="nan"))
        with self.assertRaisesRegex(ValueError, "finite"):
            assess_compound_scenario(self.base(river_level_m="inf"))

    def test_user_supplied_forecast_requires_issue_and_valid_times_without_authentication(self):
        result = assess_compound_scenario(self.base(
            evidence_type="Forecast supplied by user (not independently verified)",
            cyclone_distance_km=180,
        ))
        self.assertIn("Forecast bulletin issue time", result["data_gaps"])
        self.assertIn("Forecast valid time", result["data_gaps"])
        self.assertIn("not independently verified", result["evidence_type"])

    def test_station_and_forecast_time_metadata_gaps_are_reported(self):
        result = assess_compound_scenario(self.base(rainfall_mm=25, river_level_m=2.1, cyclone_distance_km=180))
        self.assertIn("River gauge ID and station location", result["data_gaps"])
        self.assertIn("Cyclone track-fix timestamp", result["data_gaps"])
        self.assertIn("Forecast issue time, valid time, wind/rainfall fields and coastal-water evidence", result["data_gaps"])
        forecast = assess_compound_scenario(self.base(
            evidence_type="Official forecast product",
            cyclone_distance_km=180,
        ))
        self.assertIn("Forecast valid time", forecast["data_gaps"])

if __name__ == "__main__":
    unittest.main()

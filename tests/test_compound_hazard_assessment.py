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
        self.assertTrue(any(p["hazard"] == "Compound interaction" for p in result["pathways"]))

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

    def test_invalid_hazard_and_negative_measurement_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_compound_scenario(self.base(hazards=["Earthquake"]))
        with self.assertRaises(ValueError):
            assess_compound_scenario(self.base(rainfall_mm=-1))

    def test_end_date_cannot_precede_start_date(self):
        with self.assertRaisesRegex(ValueError, "end date"):
            assess_compound_scenario(self.base(period_start=date(2026, 11, 3), period_end=date(2026, 11, 2)))

    def test_non_finite_measurements_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            assess_compound_scenario(self.base(rainfall_mm="nan"))
        with self.assertRaisesRegex(ValueError, "finite"):
            assess_compound_scenario(self.base(river_level_m="inf"))

    def test_station_and_forecast_time_metadata_gaps_are_reported(self):
        result = assess_compound_scenario(self.base(rainfall_mm=25, river_level_m=2.1, cyclone_distance_km=180))
        self.assertIn("River gauge ID and station location", result["data_gaps"])
        self.assertIn("Cyclone track-fix timestamp", result["data_gaps"])
        self.assertIn("Cyclone forecast valid time (if forecast evidence is used)", result["data_gaps"])

if __name__ == "__main__":
    unittest.main()

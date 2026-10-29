import unittest

from src.scenario_input_quality import evaluate_scenario_readiness


class ScenarioInputQualityTests(unittest.TestCase):
    def test_extreme_temperature_is_flagged_not_used_as_a_prediction(self):
        result = evaluate_scenario_readiness("Heatwave", {
            "hazard": "Heatwave", "location": "Kochi", "temperature_c": 60.0,
            "rainfall_mm": 40.0, "rainfall_period": "Last 24 hours",
            "source_and_time": "user input", "input_classification": "Unknown / unverified",
        })
        self.assertEqual(result["input_status"], "Review required")
        self.assertTrue(any("outside the broad" in warning for warning in result["warnings"]))
        self.assertFalse(result["numerical_prediction_enabled"])

    def test_rainfall_without_period_is_flagged(self):
        result = evaluate_scenario_readiness("Flood", {
            "location": "Kochi", "rainfall_mm": 40.0, "rainfall_period": "Not supplied",
        })
        self.assertTrue(any("accumulation period" in warning for warning in result["warnings"]))

    def test_river_level_requires_station_and_datum_context(self):
        result = evaluate_scenario_readiness("Flood", {"river_level_m": 5.0})
        joined = " ".join(result["warnings"])
        self.assertIn("named station", joined)
        self.assertIn("datum/reference", joined)

    def test_hazard_specific_missing_factors_are_explicit(self):
        result = evaluate_scenario_readiness("Earthquake", {"location": "Kochi"})
        self.assertTrue(any("magnitude" in item for item in result["evidence_factors_missing_or_unverified"]))

    def test_complete_inputs_never_automatically_enable_prediction(self):
        result = evaluate_scenario_readiness("Flood", {
            "location": "Kochi", "source_and_time": "official source, timestamp, station",
            "rainfall_mm": 40.0, "rainfall_period": "Last 24 hours",
            "river_level_m": 2.0, "river_station": "Station A", "river_reference": "documented datum",
            "drainage_status": "Reported functioning",
        })
        self.assertFalse(result["numerical_prediction_enabled"])
        self.assertEqual(result["readiness"], "Evidence-gated scenario review only")

    def test_all_ten_current_scenarios_have_a_specific_checklist(self):
        hazards = [
            "Flood", "Cyclone", "Earthquake", "Landslide", "Heatwave", "Drought",
            "Industrial incident", "Infrastructure failure", "Compound: cyclone + flood",
            "Compound: heavy rainfall + drainage failure",
        ]
        for hazard in hazards:
            with self.subTest(hazard=hazard):
                result = evaluate_scenario_readiness(hazard, {})
                self.assertTrue(result["evidence_factors_missing_or_unverified"])
                self.assertEqual(result["hazard"], hazard)


if __name__ == "__main__":
    unittest.main()

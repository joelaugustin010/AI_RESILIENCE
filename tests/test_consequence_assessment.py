import unittest

from src.consequence_assessment import build_consequence_assessment


class ConsequenceAssessmentTests(unittest.TestCase):
    def test_earthquake_always_returns_consequence_categories_and_probability_status(self):
        result = build_consequence_assessment(
            "Earthquake", "Kochi", "Hypothetical scenario assumption"
        )
        self.assertIn("Ground shaking and structural damage scenarios", result["consequence_categories"])
        self.assertIn("Not estimated", result["occurrence_probability"])
        self.assertIn("Not established", result["affected_area"])
        self.assertFalse(result["prediction_permitted"])

    def test_probability_and_affected_area_are_separate_outputs(self):
        result = build_consequence_assessment("Flood", "Kochi", "Hypothetical scenario assumption")
        self.assertIn("Occurrence probability", result["probability_semantics"])
        self.assertNotEqual(result["occurrence_probability"], result["affected_area"])

    def test_pollution_does_not_claim_factory_attribution_without_evidence(self):
        result = build_consequence_assessment("Air pollution", "Eloor, Kochi", "Unknown / unverified")
        self.assertTrue(any("source attribution" in x.lower() for x in result["consequence_categories"]))
        self.assertIn("Not established", result["affected_area"])

    def test_hypothetical_scenario_is_labelled(self):
        result = build_consequence_assessment("Cyclone", "Kochi", "Hypothetical scenario assumption")
        self.assertEqual(result["scenario_type"], "Hypothetical scenario")

    def test_missing_source_and_time_are_reported(self):
        result = build_consequence_assessment("Flood", "Kochi", "Hypothetical scenario assumption")
        self.assertIn("source_and_time", result["missing_context"])

    def test_unknown_hazard_does_not_generate_fake_predictions(self):
        result = build_consequence_assessment("Volcano", "Kochi", "Hypothetical scenario assumption")
        self.assertFalse(result["prediction_permitted"])
        self.assertFalse(result["official_warning_permitted"])


if __name__ == "__main__":
    unittest.main()

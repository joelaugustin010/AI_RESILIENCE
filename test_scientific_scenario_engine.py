"""Regression tests for evidence-gated scenario framing."""
import unittest
from src.scientific_scenario_engine import build_scientific_scenario_frame

class ScientificScenarioFrameTests(unittest.TestCase):
    def test_compound_hazard_retains_both_components(self):
        f = build_scientific_scenario_frame({"hazard": "Compound: cyclone + flood"})
        self.assertEqual(set(f["components"]), {"Cyclone", "Flood"})
        self.assertFalse(f["prediction_permitted"])
    def test_frame_has_hazard_exposure_vulnerability_consequence(self):
        f = build_scientific_scenario_frame({"hazard": "Flood"})
        stages = {x["Reasoning stage"] for x in f["pathways"]}
        self.assertTrue({"Hazard", "Exposure", "Vulnerability", "Consequence to examine"}.issubset(stages))
        self.assertTrue(all(x["Status"] == "Not established by this form" for x in f["pathways"]))
    def test_unknown_hazard_is_not_guessed(self):
        f = build_scientific_scenario_frame({"hazard": "Unknown"})
        self.assertEqual(f["components"], [])
        self.assertEqual(f["pathways"], [])
        self.assertFalse(f["prediction_permitted"])
        self.assertFalse(f["warning_permitted"])
    def test_pollution_requires_source_evidence(self):
        f = build_scientific_scenario_frame({"hazard": "Air pollution"})
        self.assertTrue(any("source-specific evidence" in x.lower() for x in f["required_evidence"]))
        self.assertTrue(any("source attribution" in x.lower() for x in f["limitations"]))
    def test_missing_source_is_explicit(self):
        f = build_scientific_scenario_frame({"hazard": "Flood", "river_level_m": 701.962})
        self.assertEqual(f["missing_provenance_fields"], ["Source, timestamp, and units"])
        self.assertFalse(f["prediction_permitted"])
    def test_compound_requirements_are_deduplicated(self):
        f = build_scientific_scenario_frame({"hazard": "Compound: heavy rainfall + drainage failure"})
        self.assertEqual(len(f["required_evidence"]), len(set(f["required_evidence"])))
        self.assertGreater(len(f["required_evidence"]), 4)

if __name__ == "__main__":
    unittest.main()

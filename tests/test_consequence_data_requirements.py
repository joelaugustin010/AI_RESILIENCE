import unittest

from src.consequence_data_requirements import (
    HAZARD_REQUIREMENTS,
    requirements_for_hazard,
    requirements_table,
)


class ConsequenceDataRequirementsTests(unittest.TestCase):
    def test_matrix_covers_all_required_hazard_families(self):
        expected = {
            "Flood", "Cyclone", "Earthquake", "Landslide", "Heatwave", "Drought",
            "Air pollution", "Industrial incident", "Infrastructure failure",
            "Compound: cyclone + flood",
            "Compound: heavy rainfall + drainage failure",
            "Compound: earthquake + infrastructure disruption",
        }
        self.assertTrue(expected.issubset(HAZARD_REQUIREMENTS))

    def test_every_hazard_has_data_process_outcomes_and_blockers(self):
        for hazard in HAZARD_REQUIREMENTS:
            record = requirements_for_hazard(hazard)
            for key in ("hazard_inputs", "process_data", "impact_labels", "model_family", "current_blockers", "starter_sources"):
                self.assertTrue(str(record[key]).strip(), (hazard, key))

    def test_matrix_never_claims_prediction_is_approved(self):
        for hazard in HAZARD_REQUIREMENTS:
            record = requirements_for_hazard(hazard)
            self.assertTrue(record["current_blockers"])
            self.assertNotIn("prediction approved", str(record).lower())

    def test_unknown_hazard_does_not_guess_requirements(self):
        record = requirements_for_hazard("Volcano")
        self.assertFalse(record["supported"])
        self.assertIn("Do not infer", record["current_blockers"])

    def test_table_contains_shared_exposure_vulnerability_and_outcome_requirements(self):
        rows = requirements_table("Flood")
        names = {row["Data layer"] for row in rows}
        self.assertTrue({"Exposure", "Vulnerability", "Observed outcomes"}.issubset(names))

    def test_returns_defensive_copies(self):
        first = requirements_for_hazard("Flood")
        first["common_requirements"][0]["stage"] = "modified"
        second = requirements_for_hazard("Flood")
        self.assertEqual(second["common_requirements"][0]["stage"], "Exposure")


if __name__ == "__main__":
    unittest.main()

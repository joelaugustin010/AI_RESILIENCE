"""Tests for Phase 1B evidence-state, uncertainty, and recommendation gates."""

import unittest
from pathlib import Path

import pandas as pd

from src.decision_workflow import recommendation_priority_readiness
from src.evidence_quality import EvidenceRecord, EvidenceState, classify_evidence, evidence_quality_inventory
from src.uncertainty import UNCERTAINTY_TYPES, build_uncertainty_register


ROOT = Path(__file__).resolve().parent


def evidence_record(**changes):
    values = {
        "evidence_id": "test-evidence",
        "local_path": "data/test.csv",
        "publisher": "Documented publisher",
        "source_url": "https://example.org/source",
        "publication_date": "2025-01-01",
        "retrieval_date": "2025-02-01",
        "geographic_relevance": "Confirmed for the stated study area",
        "temporal_relevance": "Relevant to the stated retrospective period",
        "measurement_quality": "Documented",
        "spatial_resolution": "Station observations; CRS confirmed",
        "completeness": "Complete for the stated scope",
        "licence": "Reuse terms documented",
        "verification": "Verified",
        "limitations": (),
        "available": True,
    }
    values.update(changes)
    return EvidenceRecord(**values)


class EvidenceQualityTests(unittest.TestCase):
    def test_quality_states_cover_unavailable_conflicting_outdated_unverified(self):
        cases = (
            (evidence_record(available=False), EvidenceState.UNAVAILABLE),
            (evidence_record(measurement_quality="Conflicting measurements"), EvidenceState.CONFLICTING),
            (evidence_record(temporal_relevance="Outdated for current assessment"), EvidenceState.OUTDATED),
            (evidence_record(verification="Unverified"), EvidenceState.UNVERIFIED),
            (evidence_record(verification="Provisionally verified"), EvidenceState.PROVISIONALLY_VERIFIED),
            (evidence_record(completeness="Partial coverage"), EvidenceState.INCOMPLETE),
            (evidence_record(), EvidenceState.VERIFIED),
        )
        for record, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_evidence(record), expected)

    def test_missing_source_dates_do_not_become_verified(self):
        record = evidence_record(publication_date="Not stated")
        self.assertEqual(classify_evidence(record), EvidenceState.INCOMPLETE)

    def test_project_inventory_includes_quality_dimensions_and_local_conflicts(self):
        inventory = pd.DataFrame(evidence_quality_inventory(ROOT))
        cwc = inventory.loc[inventory["Evidence ID"].eq("cwc_telemetry_rainfall")].iloc[0]
        hospital = inventory.loc[inventory["Evidence ID"].eq("hospital_directory")].iloc[0]
        self.assertEqual(cwc["Evidence state"], "Conflicting")
        self.assertIn("324 duplicate", cwc["Measurement quality"])
        self.assertIn("coordinate", hospital["Spatial resolution / CRS"].lower())
        self.assertTrue(
            {
                "Source authority",
                "Publication / update date",
                "Retrieval / review date",
                "Geographic relevance",
                "Temporal relevance",
                "Measurement quality",
                "Spatial resolution / CRS",
                "Completeness",
                "Licence",
                "Verification status",
            }.issubset(inventory.columns)
        )

    def test_missing_project_files_are_unavailable_not_zero_or_verified(self):
        inventory = evidence_quality_inventory(ROOT / "missing_project")
        self.assertTrue(all(row["Evidence state"] == "Unavailable" for row in inventory))


class UncertaintyTests(unittest.TestCase):
    def test_uncertainty_register_distinguishes_all_required_categories(self):
        result = build_uncertainty_register(
            {
                "rainfall_mm": 80,
                "assets": ["Hospitals"],
                "input_classification": "Hypothetical scenario assumption",
            },
            pd.DataFrame({"Evidence state": ["Conflicting", "Incomplete"]}),
        )
        self.assertEqual(tuple(result["Uncertainty type"]), UNCERTAINTY_TYPES)
        data_quality = result.loc[result["Uncertainty type"].eq("Data-quality uncertainty")].iloc[0]
        spatial = result.loc[result["Uncertainty type"].eq("Spatial uncertainty")].iloc[0]
        model = result.loc[result["Uncertainty type"].eq("Model uncertainty")].iloc[0]
        self.assertIn("Conflicting", data_quality["Evidence / source of uncertainty"])
        self.assertIn("no validated asset coordinates", spatial["Evidence / source of uncertainty"])
        self.assertEqual(model["Status"], "Not assessed")
        self.assertFalse(result.astype(str).apply(lambda column: column.str.contains(r"\d+%", regex=True)).any().any())

    def test_missing_measurements_are_not_reported_as_zero(self):
        result = build_uncertainty_register({"assets": [], "input_classification": "Unknown / unverified"})
        measurement = result.loc[result["Uncertainty type"].eq("Measurement uncertainty")].iloc[0]
        self.assertEqual(measurement["Status"], "Not assessed")
        self.assertIn("No physical measurements supplied", measurement["Evidence / source of uncertainty"])
        self.assertIn("not converted to zero hazard", result.iloc[1]["Downstream consequence"])


class RecommendationPriorityTests(unittest.TestCase):
    def test_missing_or_unverified_criteria_do_not_produce_a_rank(self):
        result = recommendation_priority_readiness({})
        self.assertEqual(result["status"], "Not ranked; evidence is insufficient")
        self.assertTrue(result["blockers"])
        self.assertIn("No score", result["ranking_basis"])

    def test_estimated_benefit_is_distinguished_from_demonstrated_benefit(self):
        criteria = {
            name: {
                "value": 1,
                "unit": "documented scale",
                "source": "https://example.org/evidence",
                "evidence_state": "Verified",
            }
            for name in (
                "expected_risk_reduction",
                "population_affected",
                "infrastructure_importance",
                "feasibility",
                "implementation_cost",
                "implementation_time",
                "uncertainty",
            )
        }
        criteria["expected_risk_reduction"]["benefit_status"] = "Estimated"
        result = recommendation_priority_readiness(criteria)
        self.assertEqual(result["status"], "Not ranked; evidence is insufficient")
        self.assertIn("distinguish a validated estimate", " ".join(result["blockers"]))
        criteria["expected_risk_reduction"]["benefit_status"] = "Demonstrated benefit"
        result = recommendation_priority_readiness(criteria)
        self.assertEqual(result["status"], "Evidence gate passed; stakeholder weighting still required")
        self.assertIn("No score or priority order produced", result["ranking_basis"])


if __name__ == "__main__":
    unittest.main()

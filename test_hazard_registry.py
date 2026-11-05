"""Regression tests for the single authoritative hazard registry.

These tests lock the registry to every consumer that previously kept a private
copy of the hazard lists.  They also run one representative scenario for each of
the ten Decision Workflow hazards through the same pure building blocks the
workflow page uses, so a drift in any one module fails here rather than only in
a browser session.
"""

import unittest

from src.consequence_data_requirements import (
    HAZARD_REQUIREMENTS,
    requirements_for_hazard,
    validate_requirements_matrix,
)
from src.decision_workflow import (
    HAZARD_OPTIONS,
    mitigation_actions_for,
    recommendation_candidates,
    validate_workflow_inputs,
)
from src.disaster_models import MODEL_DISPATCH, assess_disaster, disaster_model_mapping
from src.hazard_registry import (
    COMPONENT_HAZARDS,
    HAZARD_COMPONENTS,
    HAZARD_EVIDENCE_FACTORS,
    HAZARD_NOTES,
    HAZARD_REGISTRY,
    MODEL_DISPATCH_KEYS,
    REQUIREMENT_HAZARDS,
    SCIENTIFIC_HAZARDS,
    WORKFLOW_HAZARDS,
    components_for,
    is_workflow_hazard,
    scientific_components_for,
    validate_registry,
)
from src.map_integration import build_map_context, hazard_layer_availability
from src.scenario_input_quality import evaluate_scenario_readiness
from src.scenario_output_model import HAZARDS as PREDICTABLE_HAZARDS
from src.scenario_output_model import predict_scenario_outcome
from src.scientific_scenario_engine import build_scientific_scenario_frame


def minimal_inputs(hazard: str) -> dict:
    """Return the smallest plausible scenario accepted for a workflow hazard."""
    return {
        "hazard": hazard,
        "location": "Kochi Municipal Corporation; area not specified",
        "input_classification": "Hypothetical scenario assumption",
        "source_and_time": "Synthetic test scenario; not an observation",
        "assets": ["Hospitals", "Roads and bridges"],
        "condition_notes": "Registry regression test scenario only.",
    }


class RegistryIntegrityTests(unittest.TestCase):
    def test_registry_is_internally_consistent(self):
        self.assertEqual(validate_registry(), [])

    def test_exactly_ten_workflow_hazards_are_registered(self):
        self.assertEqual(len(WORKFLOW_HAZARDS), 10)
        self.assertEqual(len(set(WORKFLOW_HAZARDS)), 10)
        self.assertEqual(tuple(HAZARD_REGISTRY), WORKFLOW_HAZARDS)

    def test_every_workflow_hazard_has_a_complete_definition(self):
        for hazard in WORKFLOW_HAZARDS:
            with self.subTest(hazard=hazard):
                definition = HAZARD_REGISTRY[hazard]
                self.assertEqual(definition.name, hazard)
                self.assertIn(definition.kind, {"single", "compound"})
                self.assertTrue(definition.components)
                self.assertTrue(definition.evidence_factors)
                self.assertTrue(definition.summary)
                self.assertEqual(HAZARD_COMPONENTS[hazard], definition.components)
                self.assertEqual(HAZARD_EVIDENCE_FACTORS[hazard], definition.evidence_factors)
                self.assertEqual(HAZARD_NOTES[hazard], definition.summary)
                self.assertEqual(MODEL_DISPATCH_KEYS[hazard], hazard)

    def test_compound_components_are_the_documented_decomposition(self):
        self.assertEqual(
            components_for("Compound: cyclone + flood"),
            ["Cyclone", "Flood"],
        )
        self.assertEqual(
            components_for("Compound: heavy rainfall + drainage failure"),
            ["Flood", "Infrastructure failure"],
        )

    def test_compound_components_exist_in_the_component_vocabulary(self):
        for hazard in WORKFLOW_HAZARDS:
            for component in components_for(hazard):
                with self.subTest(hazard=hazard, component=component):
                    self.assertIn(component, COMPONENT_HAZARDS)

    def test_scientific_and_requirement_scopes_are_supersets_of_workflow(self):
        self.assertEqual(len(SCIENTIFIC_HAZARDS), 12)
        self.assertEqual(len(REQUIREMENT_HAZARDS), 12)
        self.assertTrue(set(WORKFLOW_HAZARDS) <= set(SCIENTIFIC_HAZARDS))
        self.assertTrue(set(WORKFLOW_HAZARDS) <= set(REQUIREMENT_HAZARDS))
        self.assertEqual(set(SCIENTIFIC_HAZARDS), set(REQUIREMENT_HAZARDS))
        self.assertIn("Air pollution", SCIENTIFIC_HAZARDS)
        self.assertIn(
            "Compound: earthquake + infrastructure disruption", SCIENTIFIC_HAZARDS
        )

    def test_adjacent_workstreams_are_not_selectable_workflow_hazards(self):
        self.assertFalse(is_workflow_hazard("Air pollution"))
        self.assertFalse(
            is_workflow_hazard("Compound: earthquake + infrastructure disruption")
        )
        self.assertEqual(scientific_components_for("Air pollution"), ["Air pollution"])

    def test_unknown_hazard_is_rejected_everywhere(self):
        self.assertFalse(is_workflow_hazard("Volcano"))
        self.assertEqual(components_for("Volcano"), [])
        self.assertEqual(scientific_components_for("Volcano"), [])
        with self.assertRaises(ValueError):
            assess_disaster({"hazard": "Volcano"})
        with self.assertRaises(ValueError):
            predict_scenario_outcome({"hazard": "Volcano"})


class ConsumerConsistencyTests(unittest.TestCase):
    def test_decision_workflow_options_match_the_registry(self):
        self.assertEqual(HAZARD_OPTIONS, list(WORKFLOW_HAZARDS))

    def test_scenario_output_model_matches_the_registry(self):
        self.assertEqual(list(PREDICTABLE_HAZARDS), list(WORKFLOW_HAZARDS))

    def test_model_dispatch_matches_the_registry(self):
        self.assertEqual(list(MODEL_DISPATCH), list(WORKFLOW_HAZARDS))
        mapping = disaster_model_mapping()
        self.assertEqual(
            [row["workflow_option"] for row in mapping],
            list(WORKFLOW_HAZARDS),
        )
        for row in mapping:
            with self.subTest(hazard=row["workflow_option"]):
                self.assertTrue(row["model_id"])
                self.assertTrue(row["method"])

    def test_requirements_matrix_is_consistent_and_covers_every_hazard(self):
        self.assertEqual(validate_requirements_matrix(), [])
        self.assertEqual(set(HAZARD_REQUIREMENTS), set(REQUIREMENT_HAZARDS))
        for hazard in WORKFLOW_HAZARDS:
            with self.subTest(hazard=hazard):
                record = requirements_for_hazard(hazard)
                self.assertTrue(record["supported"])
                self.assertTrue(record["workflow_supported"])
                self.assertTrue(record["hazard_inputs"])
                self.assertTrue(record["current_blockers"])

    def test_requirements_for_adjacent_workstreams_are_not_workflow_supported(self):
        for hazard in (
            "Air pollution",
            "Compound: earthquake + infrastructure disruption",
        ):
            with self.subTest(hazard=hazard):
                record = requirements_for_hazard(hazard)
                self.assertTrue(record["supported"])
                self.assertFalse(record["workflow_supported"])

    def test_map_availability_covers_every_workflow_hazard(self):
        rows = hazard_layer_availability()
        self.assertEqual([row["Hazard"] for row in rows], list(WORKFLOW_HAZARDS))
        for row in rows:
            with self.subTest(hazard=row["Hazard"]):
                self.assertIn(
                    row["Validated hazard footprint"],
                    {"Not available", "Not displayed"},
                )
                self.assertTrue(row["Why no footprint is shown"])
                self.assertEqual(
                    row["Components"], ", ".join(components_for(row["Hazard"]))
                )


class UnifiedTenHazardPipelineTests(unittest.TestCase):
    """Run every workflow hazard through the same pure pipeline stages."""

    def test_every_hazard_passes_intake_and_produces_a_complete_assessment(self):
        for hazard in WORKFLOW_HAZARDS:
            with self.subTest(hazard=hazard):
                inputs = minimal_inputs(hazard)

                self.assertEqual(validate_workflow_inputs(inputs), [])

                prediction = predict_scenario_outcome(inputs)
                self.assertEqual(prediction["hazard"], hazard)
                self.assertIsNone(prediction["numerical_probability"])
                self.assertFalse(prediction["is_trained_ml"])
                self.assertFalse(prediction["is_official_warning"])
                self.assertTrue(prediction["concern_level"])
                self.assertTrue(prediction["conditional_outcome"])
                self.assertTrue(prediction["evidence_used"])
                self.assertTrue(prediction["recommended_checks"])
                self.assertTrue(prediction["limitations"])

                assessment = assess_disaster(inputs)
                self.assertEqual(assessment["disaster"], hazard)
                self.assertFalse(assessment["validated_prediction_available"])
                self.assertIn("severity", assessment["hazard_assessment"])
                self.assertTrue(
                    "indicators" in assessment["hazard_assessment"]
                    or "components" in assessment["hazard_assessment"]
                )
                self.assertTrue(assessment["methodology"]["name"])
                self.assertTrue(assessment["methodology"]["scientific_basis"])
                self.assertTrue(assessment["methodology"]["calculation"])
                self.assertTrue(assessment["evidence"]["sources"])
                self.assertTrue(assessment["uncertainty"])
                self.assertTrue(assessment["data_gaps"])
                self.assertIn(
                    "Not performed", assessment["validation"]["historical_validation"]
                )

                consequences = assessment["potential_consequences"]
                self.assertEqual(consequences["human_population"]["status"], "unavailable")
                self.assertIsNone(
                    consequences["human_population"]["value_people"]
                )
                self.assertEqual(
                    consequences["infrastructure"]["status"],
                    "user_nominated_not_spatially_verified",
                )
                self.assertEqual(
                    consequences["infrastructure"]["nominated_assets"],
                    ["Hospitals", "Roads and bridges"],
                )
                self.assertIn("categories", consequences)
                self.assertIn("cascading_or_compound_pathways", consequences)

                self.assertEqual(
                    set(assessment["recommendations"]),
                    {"before", "during", "after", "long_term"},
                )
                for phase, items in assessment["recommendations"].items():
                    self.assertTrue(items, f"{hazard} has no {phase} actions")
                    for item in items:
                        self.assertTrue(item["action"])
                        self.assertTrue(item["priority"])
                        self.assertTrue(item["evidence_or_authority"])

                frame = build_scientific_scenario_frame(inputs)
                self.assertEqual(frame["hazard"], hazard)
                self.assertEqual(
                    frame["components"], components_for(hazard)
                )
                self.assertFalse(frame["prediction_permitted"])
                self.assertFalse(frame["warning_permitted"])
                self.assertTrue(frame["pathways"])
                self.assertTrue(frame["limitations"])

                quality = evaluate_scenario_readiness(hazard, inputs)
                self.assertEqual(quality["hazard"], hazard)
                self.assertFalse(quality["numerical_prediction_enabled"])
                self.assertEqual(quality["errors"], [])
                self.assertTrue(quality["readiness"])
                self.assertTrue(quality["reason"])
                self.assertIn("input_status", quality)
                self.assertIn("warnings", quality)
                self.assertIn("evidence_factors_missing_or_unverified", quality)

                context = build_map_context(inputs, assessment)
                self.assertEqual(context["hazard"], hazard)
                self.assertEqual(context["location"], inputs["location"])
                self.assertEqual(
                    context["assessment"]["result_status"],
                    assessment["result_status"],
                )

                availability = {
                    row["Hazard"]: row for row in hazard_layer_availability(hazard)
                }[hazard]
                self.assertTrue(availability["Selected"])
                self.assertIn(
                    availability["Validated hazard footprint"],
                    {"Not available", "Not displayed"},
                )

    def test_workflow_recommendation_and_mitigation_tables_exist_for_every_hazard(self):
        for hazard in WORKFLOW_HAZARDS:
            with self.subTest(hazard=hazard):
                inputs = minimal_inputs(hazard)
                candidates = recommendation_candidates(inputs)
                self.assertFalse(candidates.empty)
                self.assertTrue(
                    {"Action candidate", "Priority"}.issubset(candidates.columns)
                )
                mitigation = mitigation_actions_for(hazard)
                self.assertFalse(mitigation.empty)
                self.assertTrue(
                    {"Action", "Hazard", "Prerequisite / evidence needed"}.issubset(
                        mitigation.columns
                    )
                )
                self.assertTrue(
                    set(mitigation["Hazard"]) <= set(components_for(hazard))
                )


if __name__ == "__main__":
    unittest.main()

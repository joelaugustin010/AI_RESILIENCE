"""Tests for scenario transfer and feature inspection on the Kochi map."""

import unittest

from src.hazard_registry import WORKFLOW_HAZARDS, components_for
from src.map_integration import (
    build_map_context,
    hazard_layer_availability,
    selected_feature_properties,
)


class MapIntegrationTests(unittest.TestCase):
    def test_map_context_keeps_hazard_and_relevant_entered_conditions(self):
        context = build_map_context(
            {
                "hazard": "Flood",
                "location": "Kochi; area not specified",
                "input_classification": "Hypothetical scenario assumption",
                "rainfall_mm": 80.0,
                "rainfall_period": "Last 24 hours",
                "monthly_precipitation_csv": "not copied to map context",
                "assets": ["Hospitals"],
            },
            {
                "assessment_type": "Scenario assessment (not a prediction)",
                "result_status": "physical_indicator_only_not_local_flood_severity",
                "model_id": "flood_rational_method_screening",
                "hazard_assessment": {"severity": "Not classified"},
                "recommendations": {"before": [{"action": "Check observed river conditions."}]},
                "unrelated": "not copied",
            },
        )

        self.assertEqual(context["hazard"], "Flood")
        self.assertEqual(context["conditions"]["rainfall_mm"], 80.0)
        self.assertEqual(context["conditions"]["assets"], ["Hospitals"])
        self.assertNotIn("monthly_precipitation_csv", context["conditions"])
        self.assertEqual(
            context["assessment"]["result_status"],
            "physical_indicator_only_not_local_flood_severity",
        )
        self.assertEqual(
            context["assessment"]["recommendations"]["before"][0]["action"],
            "Check observed river conditions.",
        )
        self.assertNotIn("unrelated", context["assessment"])

    def test_missing_assessment_does_not_invent_map_result(self):
        context = build_map_context({"hazard": "Cyclone"}, None)

        self.assertEqual(context["hazard"], "Cyclone")
        self.assertNotIn("assessment", context)
        self.assertEqual(context["conditions"], {})

    def test_selected_feature_exposes_only_properties_not_geometry(self):
        selected = selected_feature_properties(
            {
                "selection": {
                    "objects": {
                        "kochi-wards": [
                            {
                                "properties": {
                                    "Ward_Name": "Example ward label",
                                    "Ward_No": 7,
                                    "geometry": {"type": "Polygon"},
                                }
                            }
                        ]
                    }
                }
            }
        )

        self.assertEqual(
            selected,
            [{"Ward_Name": "Example ward label", "Ward_No": 7}],
        )

    def test_unrecognized_selection_shape_returns_no_features(self):
        self.assertEqual(selected_feature_properties({"selection": None}), [])


class HazardLayerAvailabilityTests(unittest.TestCase):
    def test_availability_has_one_explicit_row_for_every_workflow_hazard(self):
        rows = hazard_layer_availability()
        self.assertEqual(len(rows), len(WORKFLOW_HAZARDS))
        self.assertEqual([row["Hazard"] for row in rows], list(WORKFLOW_HAZARDS))
        for row in rows:
            with self.subTest(hazard=row["Hazard"]):
                self.assertFalse(row["Selected"])
                self.assertIn(
                    row["Validated hazard footprint"],
                    {
                        "Not available",
                        "Modelled scenario context available",
                        "Modelled flood component only",
                    },
                )
                self.assertTrue(row["Why no footprint is shown"])
                self.assertEqual(
                    row["Components"], ", ".join(components_for(row["Hazard"]))
                )

    def test_selected_hazard_is_marked_without_changing_availability(self):
        rows = hazard_layer_availability("Cyclone")
        selected = [row for row in rows if row["Selected"]]
        self.assertEqual([row["Hazard"] for row in selected], ["Cyclone"])
        self.assertEqual(
            selected[0]["Validated hazard footprint"],
            "Not available",
        )

    def test_flood_components_are_not_promoted_to_validated_hazard_footprints(self):
        by_hazard = {row["Hazard"]: row for row in hazard_layer_availability()}
        self.assertEqual(
            by_hazard["Flood"]["Validated hazard footprint"],
            "Modelled scenario context available",
        )
        self.assertIn(
            "not observed flooding",
            by_hazard["Flood"]["Why no footprint is shown"],
        )
        self.assertEqual(
            by_hazard["Compound: cyclone + flood"]["Validated hazard footprint"],
            "Modelled flood component only",
        )
        self.assertEqual(
            by_hazard["Compound: heavy rainfall + drainage failure"][
                "Validated hazard footprint"
            ],
            "Modelled flood component only",
        )
        for hazard in ("Earthquake", "Industrial incident", "Infrastructure failure"):
            with self.subTest(hazard=hazard):
                self.assertEqual(
                    by_hazard[hazard]["Validated hazard footprint"], "Not available"
                )
                self.assertEqual(by_hazard[hazard]["Context layer"], "None")

    def test_unknown_hazard_selection_does_not_claim_a_footprint(self):
        rows = hazard_layer_availability("Volcano")
        self.assertFalse(any(row["Selected"] for row in rows))
        self.assertEqual(
            {row["Validated hazard footprint"] for row in rows},
            {
                "Not available",
                "Modelled scenario context available",
                "Modelled flood component only",
            },
        )


if __name__ == "__main__":
    unittest.main()

"""Tests for scenario transfer and feature inspection on the Kochi map."""

import unittest

from src.map_integration import build_map_context, selected_feature_properties


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


if __name__ == "__main__":
    unittest.main()

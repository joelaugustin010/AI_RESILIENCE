"""Streamlit integration test for the existing decision workflow."""

import unittest

from streamlit.testing.v1 import AppTest


class DecisionWorkflowStreamlitTests(unittest.TestCase):
    def test_decision_workflow_hero_renders_html(self):
        app = AppTest.from_file("app.py", default_timeout=60).run()

        self.assertEqual(len(app.exception), 0)
        hero = next(
            element for element in app.markdown if "<section class=\"wf-hero\">" in element.value
        )
        self.assertTrue(hero.proto.allow_html)
        self.assertIn("Disaster decision workflow", hero.value)

    def test_default_intake_renders_assessment_evidence_and_reports(self):
        app = AppTest.from_file("app.py", default_timeout=45).run()
        self.assertEqual(len(app.exception), 0)
        app.form_submit_button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        headings = [element.value for element in app.subheader]
        self.assertIn("Evidence by decision dimension", headings)
        self.assertIn("Uncertainty register", headings)
        self.assertIn("Conceptual infrastructure dependencies", headings)
        self.assertIn("4. Hazard-specific scientific assessment", [element.value for element in app.header])
        self.assertTrue(
            any("never a validated prediction" in str(element.value).lower() for element in app.caption)
        )
        self.assertTrue(
            any("Before: prevention and preparedness" in str(element.value) for element in app.markdown)
        )
        self.assertTrue(
            any("After: recovery" in str(element.value) for element in app.markdown)
        )
        self.assertTrue(
            any(
                "Long-term risk reduction and resilience planning" in str(element.label)
                for element in app.expander
            )
        )
        self.assertTrue(
            any(
                "INSUFFICIENT EVIDENCE"
                in element.value["Evidence status"].tolist()
                for element in app.dataframe
                if "Evidence status" in element.value.columns
            )
        )
        self.assertTrue(any("recommendation" in str(element.value).lower() for element in app.header))
        self.assertGreaterEqual(len(app.dataframe), 6)

    def test_compound_model_renders_component_separation_in_existing_workflow(self):
        app = AppTest.from_file("app.py", default_timeout=60).run()
        app.session_state["wf_hazard"] = "Compound: cyclone + flood"
        app.run()
        app.form_submit_button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any("4. Hazard-specific scientific assessment" == element.value for element in app.header)
        )
        self.assertTrue(
            any("Compound interaction remains unresolved" in str(element.value) for element in app.info)
        )
        self.assertTrue(
            any("Cyclone + flood evidence review" == element.value for element in app.subheader)
        )
        self.assertTrue(
            any("No joint probability" in str(element.value) for element in app.caption)
        )

    def test_drainage_scenario_inputs_render_the_dynamic_capacity_consequence(self):
        app = AppTest.from_file("app.py", default_timeout=60).run()
        for key, value in {
            "wf_hazard": "Compound: heavy rainfall + drainage failure",
            "wf_rainfall": 24.0,
            "wf_rainfall_period": "Last 1 hour",
            "wf_catchment_area": 1.0,
            "wf_runoff_coefficient": 0.5,
            "wf_drainage_capacity": 0.005,
        }.items():
            app.session_state[key] = value
        app.run()
        app.form_submit_button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        consequences = next(
            element.value
            for element in app.dataframe
            if "Model output" in element.value.columns
        )
        infrastructure = consequences.loc[
            consequences["Consequence category"].eq("Infrastructure")
        ].iloc[0]
        self.assertIn("SIMULATED SCENARIO", infrastructure["Model estimate"])
        self.assertIn("0.033333", infrastructure["Model output"])
        self.assertIn("scenario_runoff_exceeds_user_supplied_capacity", infrastructure["Model output"])
        self.assertIn("surcharge or inundation is not calculated or confirmed", infrastructure["Interpretation"])

    def test_optional_phase2_context_is_available_without_replacing_workflow(self):
        app = AppTest.from_file("app.py", default_timeout=60).run()
        self.assertEqual(len(app.exception), 0)
        load_button = next(
            button
            for button in app.button
            if button.label == "Load research-only context snapshots"
        )
        load_button.click().run()
        self.assertEqual(len(app.exception), 0)
        rendered_text = "\n".join(
            str(element.value)
            for elements in (app.markdown, app.info, app.error)
            for element in elements
        )
        context_states = {
            "IMD 0.25-degree daily rainfall": "IMD rainfall grid unavailable in this checkout",
            "NASA POWER daily gridded/model-derived data": "NASA POWER snapshot unavailable in this checkout",
            "OpenStreetMap road context": "OpenStreetMap road snapshot unavailable",
            "USGS catalog query": "USGS earthquake query unavailable",
        }
        for available_label, unavailable_label in context_states.items():
            self.assertTrue(
                available_label in rendered_text or unavailable_label in rendered_text,
                f"Expected the optional context to be rendered or clearly marked unavailable: {available_label}",
            )
        self.assertIn("Unified disaster decision workflow", [e.value for e in app.title])

    def test_map_navigation_preserves_submitted_hazard_and_assessment_context(self):
        app = AppTest.from_file("app.py", default_timeout=90).run()
        app.session_state["wf_hazard"] = "Flood"
        app.session_state["wf_rainfall"] = 80.0
        app.session_state["wf_rainfall_period"] = "Last 24 hours"
        app.run()
        app.form_submit_button[0].click().run()
        self.assertEqual(len(app.exception), 0)

        map_button = next(
            button
            for button in app.button
            if button.label == "View prone areas on the Kochi map"
        )
        map_button.click().run()

        self.assertEqual(len(app.exception), 0)
        context = app.session_state["kochimap_assessment_context"]
        self.assertEqual(context["hazard"], "Flood")
        self.assertEqual(context["conditions"]["rainfall_mm"], 80.0)
        self.assertEqual(
            context["assessment"]["result_status"],
            "physical_indicator_only_not_local_flood_severity",
        )
        self.assertTrue(
            any("Scenario carried over from the Decision Workflow" == item.value for item in app.subheader)
        )
        self.assertTrue(
            any("Scenario recommendation candidates" in str(item.label) for item in app.expander)
        )
        self.assertTrue(
            any("No facility is assumed safe or exposed" in str(item.value) for item in app.info)
        )
        self.assertTrue(
            any("WorldCover 2021 land-cover context" in item.label for item in app.checkbox)
        )
        self.assertTrue(
            any(
                "Land-cover classes only; not hazard severity or exposure"
                in element.value["Meaning"].tolist()
                for element in app.dataframe
                if "Meaning" in element.value.columns
            )
        )

    def test_map_hides_flood_scenario_for_unrelated_selected_hazard(self):
        app = AppTest.from_file("app.py", default_timeout=90).run()
        app.session_state["wf_hazard"] = "Heatwave"
        app.session_state["wf_temperature"] = 35.0
        app.session_state["wf_relative_humidity"] = 60.0
        app.run()
        app.form_submit_button[0].click().run()
        next(
            button
            for button in app.button
            if button.label == "View prone areas on the Kochi map"
        ).click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            app.session_state["kochimap_assessment_context"]["hazard"],
            "Heatwave",
        )
        self.assertFalse(
            any("JRC modeled river flood depth" in element.label for element in app.checkbox)
        )
        self.assertTrue(
            any("No compatible Heatwave hazard layer" in str(element.value) for element in app.info)
        )


if __name__ == "__main__":
    unittest.main()

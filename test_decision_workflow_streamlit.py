"""Streamlit integration test for the existing decision workflow."""

import unittest

from streamlit.testing.v1 import AppTest

from src.map_integration import MAP_CONTEXT_KEY


def open_workflow(timeout: int = 90):
    """Start the app and navigate to the Decision Workflow.

    The Command Centre is the default landing page, so workflow tests must
    explicitly open the workspace they exercise.
    """
    app = AppTest.from_file("app.py", default_timeout=timeout).run()
    app.switch_page("app_pages/decision_workflow.py").run()
    return app


class DecisionWorkflowStreamlitTests(unittest.TestCase):
    def test_decision_workflow_hero_renders_html(self):
        app = open_workflow()

        self.assertEqual(len(app.exception), 0)
        hero = next(
            element for element in app.markdown if "<section class=\"wf-hero\">" in element.value
        )
        self.assertTrue(hero.proto.allow_html)
        self.assertIn("Disaster decision workflow", hero.value)

    def test_default_intake_renders_assessment_evidence_and_reports(self):
        app = open_workflow()
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
        app = open_workflow()
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
        app = open_workflow()
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
        app = open_workflow()
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
        app = open_workflow()
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
        app = open_workflow()
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


class CommandCentreLandingTests(unittest.TestCase):
    def test_command_centre_is_the_default_landing_page(self):
        app = AppTest.from_file("app.py", default_timeout=60).run()

        self.assertEqual(len(app.exception), 0)
        rendered = "\n".join(str(element.value) for element in app.markdown)
        self.assertIn("Command centre", rendered)
        self.assertIn(
            "Where would you like to start?",
            [heading.value for heading in app.subheader],
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Research workspaces"], "12")
        self.assertEqual(metrics["Official emergency alerts"], "Not enabled")
        self.assertEqual(metrics["Validated live predictions"], "Not enabled")
        self.assertTrue(
            any(link.label == "Open Decision Workflow" for link in app.page_link)
        )
        self.assertFalse(
            any(
                title.value == "Unified disaster decision workflow"
                for title in app.title
            )
        )

    def test_command_centre_links_open_the_integrated_cyclone_flood_workspace(self):
        app = AppTest.from_file("app.py", default_timeout=60).run()

        self.assertTrue(
            any("Cyclone + Flood" in str(element.value) for element in app.markdown)
        )
        compound_links = [
            link
            for link in app.page_link
            if str(link.proto.page) == "compound_scenario"
        ]
        self.assertEqual(len(compound_links), 1)
        self.assertEqual(compound_links[0].label, "Open workspace")


class WorkflowStateTests(unittest.TestCase):
    def _submit_flood(self, app):
        app.session_state["wf_hazard"] = "Flood"
        app.session_state["wf_rainfall"] = 80.0
        app.session_state["wf_rainfall_period"] = "Last 24 hours"
        app.run()
        app.form_submit_button[0].click().run()
        self.assertEqual(len(app.exception), 0)

    def test_result_survives_navigation_away_and_back(self):
        app = open_workflow()
        self._submit_flood(app)
        self.assertIsNotNone(app.session_state["decision_workflow_inputs"])

        app.switch_page("app_pages/home.py").run()
        self.assertEqual(len(app.exception), 0)
        app.switch_page("app_pages/decision_workflow.py").run()

        self.assertEqual(len(app.exception), 0)
        self.assertIsNotNone(app.session_state["decision_workflow_inputs"])
        self.assertTrue(
            any(
                heading.value == "2. Immediate scenario result"
                for heading in app.header
            )
        )

    def test_changing_hazard_clears_previous_result_and_map_context(self):
        app = open_workflow()
        self._submit_flood(app)
        next(
            button
            for button in app.button
            if button.label == "View prone areas on the Kochi map"
        ).click().run()
        self.assertIn(MAP_CONTEXT_KEY, app.session_state)

        app.switch_page("app_pages/decision_workflow.py").run()
        self.assertIsNotNone(app.session_state["decision_workflow_inputs"])

        app.session_state["wf_hazard"] = "Heatwave"
        app.run()

        self.assertIsNone(app.session_state["decision_workflow_inputs"])
        self.assertNotIn(MAP_CONTEXT_KEY, app.session_state)
        self.assertFalse(
            any(
                heading.value == "2. Immediate scenario result"
                for heading in app.header
            )
        )

    def test_resubmission_clears_the_previous_map_context(self):
        app = open_workflow()
        self._submit_flood(app)
        next(
            button
            for button in app.button
            if button.label == "View prone areas on the Kochi map"
        ).click().run()
        self.assertIn(MAP_CONTEXT_KEY, app.session_state)

        app.switch_page("app_pages/decision_workflow.py").run()
        app.form_submit_button[0].click().run()

        self.assertEqual(len(app.exception), 0)
        self.assertNotIn(MAP_CONTEXT_KEY, app.session_state)


if __name__ == "__main__":
    unittest.main()

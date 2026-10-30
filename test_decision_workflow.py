"""Tests for the connected workflow's rules, scenarios, budget, and reports."""

import unittest
from pathlib import Path

import pandas as pd

from src.scenario_screening import build_scenario_screening

from src.decision_workflow import (
    HAZARD_OPTIONS,
    assessment_summary,
    build_scenario_comparison,
    budget_summary,
    compare_action_combinations,
    evidence_inventory,
    hazard_evidence_checklist,
    mitigation_actions_for,
    report_html,
    report_rows,
    validate_workflow_inputs,
)


def valid_inputs(**changes):
    values = {
        "hazard": "Flood",
        "location": "Kochi, area not specified",
        "input_classification": "Hypothetical scenario assumption",
        "rainfall_mm": 100.0,
        "rainfall_period": "Last 24 hours",
        "river_level_m": None,
        "assets": ["Hospitals"],
        "condition_notes": "Example only",
    }
    values.update(changes)
    return values


class DecisionWorkflowValidationTests(unittest.TestCase):
    def test_hazard_catalog_includes_single_and_compound_hazards(self):
        self.assertIn("Flood", HAZARD_OPTIONS)
        self.assertIn("Earthquake", HAZARD_OPTIONS)
        self.assertIn("Industrial incident", HAZARD_OPTIONS)
        self.assertIn("Compound: cyclone + flood", HAZARD_OPTIONS)
        self.assertIn("Compound: heavy rainfall + drainage failure", HAZARD_OPTIONS)

    def test_valid_inputs_pass(self):
        self.assertEqual(validate_workflow_inputs(valid_inputs()), [])

    def test_missing_hazard_or_location_is_rejected(self):
        problems = validate_workflow_inputs(valid_inputs(hazard="not-a-hazard", location="  "))
        self.assertTrue(any("hazard" in message.lower() for message in problems))
        self.assertTrue(any("location" in message.lower() for message in problems))

    def test_negative_or_nonfinite_measurements_are_rejected(self):
        problems = validate_workflow_inputs(valid_inputs(rainfall_mm=-1, river_level_m=float("inf")))
        self.assertTrue(any("Rainfall" in message for message in problems))
        self.assertTrue(any("River level" in message for message in problems))

    def test_negative_gauge_reference_and_temperature_are_allowed(self):
        self.assertEqual(
            validate_workflow_inputs(valid_inputs(rainfall_mm=None, river_level_m=-0.5, temperature_c=-2.0)),
            [],
        )

    def test_rainfall_requires_time_period(self):
        problems = validate_workflow_inputs(valid_inputs(rainfall_period="Not supplied"))
        self.assertTrue(any("time period" in message for message in problems))

    def test_blank_optional_conditions_are_allowed(self):
        self.assertEqual(
            validate_workflow_inputs(valid_inputs(rainfall_mm=None, rainfall_period="Not supplied")),
            [],
        )


class ScenarioAndAssessmentTests(unittest.TestCase):
    def test_compound_scenario_expands_and_stays_qualitative(self):
        scenarios = build_scenario_comparison(
            valid_inputs(hazard="Compound: cyclone + flood", wind_speed_kmh=80)
        )
        self.assertEqual(len(scenarios), 3)
        self.assertIn("Cyclone, Flood", scenarios.iloc[0]["Assumptions"])
        self.assertIn("Hypothetical", scenarios.iloc[2]["Classification"])
        self.assertTrue(all(any(word in text.lower() for word in ("calculated", "unknown", "estimated")) for text in scenarios["Possible consequences to review"]))

    def test_hypothetical_inputs_complete_a_qualitative_assessment_without_claiming_prediction(self):
        result = assessment_summary(valid_inputs())
        self.assertIn("Qualitative scenario assessment completed", result["status"])
        self.assertIn("numerical prediction not validated", result["status"])
        self.assertIn("Hypothetical values are valid inputs", result["interpretation"])
        self.assertNotIn("%", result["interpretation"])
        self.assertIn("not used", result["additional_caution"])

    def test_flood_hypothetical_values_produce_conditional_assessment(self):
        result = build_scenario_screening(valid_inputs(
            rainfall_mm=120,
            rainfall_period="Last 24 hours",
            drainage_status="Hypothetical partial failure",
            river_level_m=3.2,
            river_station="Example gauge",
            river_reference="hypothetical datum",
            affected_population=500,
        ))
        self.assertGreaterEqual(len(result), 4)
        combined = " ".join(result["Conditional assessment"].tolist()).lower()
        self.assertIn("surface-water accumulation", combined)
        self.assertIn("not a verified exposed or affected population", combined)
        self.assertIn("hypothetical assumption", " ".join(result["Evidence class"].str.lower().unique()))

    def test_24_hour_hypothetical_rainfall_gets_official_imd_category_not_flood_probability(self):
        result = build_scenario_screening(valid_inputs(
            rainfall_mm=100,
            rainfall_period="Last 24 hours",
        ))
        category = result.loc[result["Scenario signal"].str.contains("IMD 24-hour station rainfall category")]
        self.assertEqual(len(category), 1)
        self.assertIn("Heavy", category.iloc[0]["Scenario signal"])
        self.assertIn("not a Kochi flood prediction", category.iloc[0]["Conditional assessment"])
        self.assertIn("mausam.imd.gov.in", category.iloc[0]["Next check / action"])

    def test_non_24_hour_rainfall_does_not_get_daily_imd_category(self):
        result = build_scenario_screening(valid_inputs(
            rainfall_mm=100,
            rainfall_period="Last 1 hour",
        ))
        self.assertFalse(result["Scenario signal"].str.contains("IMD 24-hour station rainfall category").any())

    def test_every_hazard_returns_at_least_one_scenario_output(self):
        for hazard in HAZARD_OPTIONS:
            with self.subTest(hazard=hazard):
                result = build_scenario_screening(valid_inputs(hazard=hazard))
                self.assertGreater(len(result), 0)
                self.assertTrue(result["Conditional assessment"].str.strip().ne("").all())
                self.assertTrue(result["Next check / action"].str.strip().ne("").all())

    def test_scenario_screen_does_not_claim_river_level_is_dangerous_without_threshold(self):
        result = build_scenario_screening(valid_inputs(river_level_m=99.0))
        river = result.loc[result["Scenario signal"].str.contains("River-level assumption")]
        self.assertEqual(len(river), 1)
        self.assertIn("cannot establish whether the river is dangerous", river.iloc[0]["Conditional assessment"])

    def test_mitigation_candidates_have_no_fabricated_cost_or_effectiveness(self):
        actions = mitigation_actions_for("Flood")
        self.assertFalse(actions.empty)
        self.assertTrue(actions["Cost INR"].isna().all())
        self.assertTrue(actions["User priority (1=highest)"].isna().all())


class BudgetTests(unittest.TestCase):
    def test_budget_totals_partial_costs_and_flags_unknown(self):
        result = budget_summary([1000, None, 2500], 5000)
        self.assertEqual(result["entered_total"], 3500)
        self.assertEqual(result["unknown_or_invalid_count"], 1)
        self.assertEqual(result["remaining"], 1500)
        self.assertIsNone(result["within_budget"])

    def test_negative_or_invalid_cost_is_not_silently_counted(self):
        result = budget_summary([100, -5, "bad"], 1000)
        self.assertEqual(result["entered_total"], 100)
        self.assertEqual(result["unknown_or_invalid_count"], 2)

    def test_combinations_are_cost_checks_and_require_complete_prices(self):
        actions = pd.DataFrame({"Action": ["A", "B"], "Cost INR": [200, None]})
        result = compare_action_combinations(actions, 500, {"A": ["A"], "B": ["A", "B"]})
        self.assertEqual(result.iloc[0]["Budget status"], "Fits entered budget")
        self.assertIn("missing or invalid", result.iloc[1]["Budget status"])
        self.assertIn("no risk reduction", result.iloc[0]["Basis"])

    def test_combinations_flag_unknown_and_repeated_action_selections(self):
        actions = pd.DataFrame({"Action": ["A", "B"], "Cost INR": [200, 100]})
        result = compare_action_combinations(
            actions, 500,
            {"Unknown": ["A", "Typo"], "Repeated": ["A", "A"]},
        ).set_index("Combination")
        self.assertIn("not in the action table", result.loc["Unknown", "Budget status"])
        self.assertIn("Unknown action: Typo", result.loc["Unknown", "Selection issues"])
        self.assertIn("duplicate selections", result.loc["Repeated", "Budget status"])
        self.assertIn("Repeated selection: A", result.loc["Repeated", "Selection issues"])

    def test_combinations_flag_duplicate_action_rows(self):
        actions = pd.DataFrame({"Action": ["A", "A"], "Cost INR": [200, 300]})
        result = compare_action_combinations(actions, 1000, {"A": ["A"]})
        self.assertIn("duplicate action names", result.iloc[0]["Budget status"])
        self.assertIn("Duplicate action row: A", result.iloc[0]["Selection issues"])


class EvidenceAndReportTests(unittest.TestCase):
    def test_flood_checklist_identifies_missing_verification(self):
        checklist = hazard_evidence_checklist(valid_inputs(), Path(__file__).resolve().parent)
        self.assertGreaterEqual(len(checklist), 4)
        self.assertTrue(checklist["Evidence needed"].str.contains("exposed assets", case=False).any())
        self.assertTrue(checklist["Known limitation"].str.contains("licence", case=False).any())

    def test_compound_checklist_covers_both_hazards(self):
        checklist = hazard_evidence_checklist(
            valid_inputs(hazard="Compound: cyclone + flood"),
            Path(__file__).resolve().parent,
        )
        self.assertEqual(set(checklist["Hazard component"]), {"Flood", "Cyclone"})

    def test_industrial_checklist_cautions_against_unverified_source_claims(self):
        checklist = hazard_evidence_checklist(
            valid_inputs(hazard="Industrial incident"),
            Path(__file__).resolve().parent,
        )
        limitations = " ".join(checklist["Known limitation"].tolist()).lower()
        self.assertIn("aqi alone", limitations)
        self.assertTrue(checklist["Next verification step"].str.contains("pollutant", case=False).any())

    def test_report_includes_evidence_readiness_checklist(self):
        inputs = valid_inputs()
        evidence = evidence_inventory(Path(__file__).resolve().parent)
        scenarios = build_scenario_comparison(inputs)
        actions = mitigation_actions_for("Flood").head(1).copy()
        combinations = compare_action_combinations(actions, None, {"A": actions["Action"].tolist()})
        checklist = hazard_evidence_checklist(inputs, Path(__file__).resolve().parent)
        report = report_rows(
            inputs, evidence, scenarios, actions, None, combinations,
            Path(__file__).resolve().parent, evidence_checklist=checklist
        )
        rows = report.loc[report["Section"].eq("Evidence readiness checklist")]
        self.assertGreater(len(rows), 0)

    def test_missing_data_is_reported_without_blocking_inventory(self):
        inventory = evidence_inventory(Path(__file__).resolve().parent / "missing_project")
        self.assertTrue((inventory["Available"] == "No").all())
        self.assertTrue(inventory["Known limitation / role in this assessment"].str.contains("not present").all())

    def test_historical_rainfall_benchmark_is_evidence_but_not_a_hazard_prediction(self):
        backtest = {
            "summary": {
                "train_end_exclusive": "2012-06-15 13:30:00",
                "test_period_start": "2012-06-22 14:30:00",
                "test_period_end": "2014-12-31 13:00:00",
                "test_pairs": 11675,
                "test_stations": 15,
                "all_stations": 21,
            },
            "metrics": {
                "gradient_boosting": {"mae_mm": 3.0221, "rmse_mm": 5.2122},
                "station_median": {"mae_mm": 3.0902, "rmse_mm": 5.7189},
                "persistence": {"mae_mm": 3.9594, "rmse_mm": 6.7252},
            },
        }
        inventory = evidence_inventory(Path(__file__).resolve().parent, backtest)
        row = inventory.loc[inventory["Dataset / file"].eq("Historical manual-rainfall benchmark")].iloc[0]
        self.assertIn("3.022", row["Contents / units"])
        self.assertIn("5.212", row["Contents / units"])
        self.assertIn("not a current rainfall/flood forecast", row["Known limitation / role in this assessment"])

    def test_csv_and_html_report_include_inputs_method_limitations_and_escaped_text(self):
        inputs = valid_inputs(location="<script>alert('x')</script>")
        evidence = evidence_inventory(Path(__file__).resolve().parent)
        scenarios = build_scenario_comparison(inputs)
        actions = mitigation_actions_for("Flood").head(1).copy()
        actions.loc[actions.index[0], "Cost INR"] = 125000
        combinations = compare_action_combinations(actions, 200000, {"Selected": actions["Action"].tolist()})
        report = report_rows(inputs, evidence, scenarios, actions, 200000, combinations, Path(__file__).resolve().parent)
        self.assertTrue(report["Value"].str.contains("numerical prediction not validated", case=False, regex=False).any())
        self.assertTrue(report["Value"].str.contains("Qualitative scenario assessment completed", regex=False).any())
        self.assertTrue(report["Value"].str.contains("125000", regex=False).any())
        rendered = report_html(report)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<script>alert", rendered)
        self.assertIn("not an official warning", rendered)


if __name__ == "__main__":
    unittest.main()

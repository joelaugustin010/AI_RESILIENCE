"""Tests for the connected workflow's rules, scenarios, budget, and reports."""

import unittest
from pathlib import Path

import pandas as pd

from src.decision_workflow import (
    HAZARD_OPTIONS,
    assessment_evidence_matrix,
    assessment_summary,
    build_scenario_comparison,
    budget_summary,
    compare_action_combinations,
    evidence_inventory,
    mitigation_actions_for,
    recommendation_candidates,
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

    def test_unrecognized_input_classification_is_rejected(self):
        problems = validate_workflow_inputs(valid_inputs(input_classification="Verified by app"))
        self.assertTrue(any("classified" in message for message in problems))

    def test_unhashable_input_classification_is_rejected_without_exception(self):
        problems = validate_workflow_inputs(valid_inputs(input_classification=["unknown"]))
        self.assertTrue(any("classified" in message for message in problems))

    def test_population_must_be_a_whole_number(self):
        problems = validate_workflow_inputs(valid_inputs(affected_population=1.5))
        self.assertTrue(any("whole number" in message for message in problems))

    def test_other_rainfall_period_requires_notes(self):
        problems = validate_workflow_inputs(
            valid_inputs(rainfall_period="Other / state in notes", condition_notes="")
        )
        self.assertTrue(any("condition notes" in message for message in problems))

    def test_asset_and_service_conditions_use_supported_options(self):
        problems = validate_workflow_inputs(
            valid_inputs(assets=["Unknown asset"], drainage_status="Verified")
        )
        self.assertTrue(any("assets from the available list" in message for message in problems))
        self.assertTrue(any("valid drainage condition" in message for message in problems))


class ScenarioAndAssessmentTests(unittest.TestCase):
    def test_compound_scenario_expands_and_stays_qualitative(self):
        scenarios = build_scenario_comparison(
            valid_inputs(hazard="Compound: cyclone + flood", wind_speed_kmh=80)
        )
        self.assertEqual(len(scenarios), 3)
        self.assertIn("Cyclone, Flood", scenarios.iloc[0]["Assumptions"])
        self.assertIn("Hypothetical", scenarios.iloc[2]["Classification"])
        self.assertTrue(all(any(word in text.lower() for word in ("calculated", "unknown", "estimated")) for text in scenarios["Possible consequences to review"]))

    def test_assessment_refuses_unsupported_probability(self):
        result = assessment_summary(valid_inputs())
        self.assertIn("Insufficient evidence", result["status"])
        self.assertNotIn("%", result["interpretation"])
        self.assertIn("not used", result["additional_caution"])

    def test_mitigation_candidates_have_no_fabricated_cost_or_effectiveness(self):
        actions = mitigation_actions_for("Flood")
        self.assertFalse(actions.empty)
        self.assertTrue(actions["Cost INR"].isna().all())
        self.assertTrue(actions["User priority (1=highest)"].isna().all())

    def test_compound_rainfall_and_drainage_remain_distinct_drivers(self):
        scenarios = build_scenario_comparison(
            valid_inputs(hazard="Compound: heavy rainfall + drainage failure")
        )
        self.assertIn("Heavy rainfall, Drainage failure", scenarios.iloc[0]["Assumptions"])
        self.assertNotIn("Flood, Infrastructure failure", scenarios.iloc[0]["Assumptions"])

    def test_evidence_matrix_separates_risk_dimensions_without_inventing_scores(self):
        inputs = valid_inputs(rainfall_mm=100, affected_population=150, assets=["Hospitals"])
        matrix = assessment_evidence_matrix(inputs)
        vulnerability = matrix.loc[matrix["Dimension"].eq("Vulnerability")].iloc[0]
        risk = matrix.loc[matrix["Dimension"].eq("Risk")].iloc[0]
        compound = matrix.loc[matrix["Dimension"].eq("Compound interactions")].iloc[0]
        hazard = matrix.loc[matrix["Dimension"].eq("Hazard")].iloc[0]
        exposure = matrix.loc[matrix["Dimension"].eq("Exposure")].iloc[0]
        self.assertEqual(vulnerability["Status"], "Not assessed")
        self.assertEqual(risk["Status"], "Not estimated; no risk class assigned")
        self.assertIn("not be added", compound["Gap / uncertainty"])
        self.assertIn("unverified", matrix.iloc[0]["Status"])
        self.assertNotIn("population context", hazard["Evidence available"])
        self.assertIn("150", exposure["Evidence available"])

    def test_compound_evidence_matrix_requires_overlap_and_dependency_evidence(self):
        matrix = assessment_evidence_matrix(
            valid_inputs(hazard="Compound: cyclone + flood")
        )
        compound = matrix.loc[matrix["Dimension"].eq("Compound interactions")].iloc[0]
        self.assertEqual(compound["Status"], "Components identified separately; interaction not modeled.")
        self.assertIn("Temporal overlap", compound["Gap / uncertainty"])
        self.assertIn("Cyclone, Flood", compound["Evidence available"])

    def test_recommendations_name_the_assessment_trigger_and_remain_unranked(self):
        candidates = recommendation_candidates(
            valid_inputs(
                drainage_status="Reported partially impaired",
                source_and_time="Local report, 2026-10-01",
                assets=["Hospitals"],
            )
        )
        drainage = candidates.loc[
            candidates["Action candidate"].eq("Drainage inspection and maintenance")
        ].iloc[0]
        hospital = candidates.loc[
            candidates["Action candidate"].eq("Hospital continuity and flood preparedness")
        ].iloc[0]
        self.assertIn("Reported partially impaired", drainage["Assessment evidence / trigger"])
        self.assertIn("not verified", hospital["Assessment evidence / trigger"])
        self.assertTrue(candidates["Action candidate"].eq("Verify condition source, location, units, and time").any())
        self.assertTrue(candidates["Priority"].eq("Not ranked; local review required").all())
        self.assertFalse(candidates["Assessment evidence / trigger"].str.contains("risk reduction").any())


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


class EvidenceAndReportTests(unittest.TestCase):
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
        self.assertTrue(report["Value"].str.contains("Insufficient evidence", regex=False).any())
        self.assertTrue(report["Value"].str.contains("125000", regex=False).any())
        rendered = report_html(report)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<script>alert", rendered)
        self.assertIn("not an official warning", rendered)
        self.assertTrue(report["Section"].eq("Assessment dimensions").any())
        self.assertTrue(report["Section"].eq("Evidence-linked recommendation candidate").any())

    def test_report_does_not_claim_missing_sources_have_known_quality_findings(self):
        root = Path(__file__).resolve().parent / "missing_project"
        inputs = valid_inputs(rainfall_mm=None, rainfall_period="Not supplied")
        report = report_rows(
            inputs,
            evidence_inventory(root),
            build_scenario_comparison(inputs),
            mitigation_actions_for("Flood").head(1),
            None,
            pd.DataFrame(),
            root,
        )
        self.assertFalse(report["Value"].str.contains("324 station-time", regex=False).any())
        self.assertTrue(report["Value"].str.contains("not present in this workspace", regex=False).any())


if __name__ == "__main__":
    unittest.main()

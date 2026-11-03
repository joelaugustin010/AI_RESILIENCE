"""Scientific behavior and fail-closed tests for the ten workflow models."""

import unittest
from datetime import datetime

from src.decision_workflow import HAZARD_OPTIONS
from src.disaster_models import MODEL_DISPATCH, assess_disaster, disaster_model_mapping
from src.disaster_models.cyclone import assess as assess_cyclone
from src.disaster_models.drought import (
    calculate_spi1,
    parse_monthly_precipitation_csv,
)
from src.disaster_models.earthquake import assess as assess_earthquake
from src.disaster_models.flood import assess as assess_flood
from src.disaster_models.heatwave import (
    assess as assess_heatwave,
    heat_index_fahrenheit,
)
from src.disaster_models.industrial_incident import assess as assess_industrial
from src.disaster_models.landslide import assess as assess_landslide


def scenario(hazard="Flood", **overrides):
    values = {
        "hazard": hazard,
        "location": "Kochi; area not geocoded",
        "input_classification": "Hypothetical scenario assumption",
        "assets": ["Hospitals", "Roads and bridges"],
        "affected_population": None,
    }
    values.update(overrides)
    return values


def monthly_test_series():
    """Synthetic values for software tests only; never used as project evidence."""
    records = []
    for year in range(1991, 2021):
        for month in range(1, 13):
            records.append(
                {
                    "month": datetime(year, month, 1),
                    "precipitation_mm": float(40 + month * 4 + (year - 1991) % 9),
                }
            )
    return records


class DisasterModelMappingTests(unittest.TestCase):
    def test_every_existing_option_has_its_own_model(self):
        self.assertEqual(list(MODEL_DISPATCH), HAZARD_OPTIONS)
        mapping = disaster_model_mapping()
        self.assertEqual(len(mapping), 10)
        self.assertEqual(
            [row["workflow_option"] for row in mapping],
            HAZARD_OPTIONS,
        )
        self.assertEqual(len({row["model_id"] for row in mapping}), 10)

    def test_all_models_return_the_same_structured_contract_without_prediction(self):
        for hazard in HAZARD_OPTIONS:
            with self.subTest(hazard=hazard):
                result = assess_disaster(scenario(hazard))
                self.assertEqual(result["disaster"], hazard)
                self.assertIn(result["assessment_type"], {
                    "Scenario assessment (not a prediction)",
                    "Evidence review; no classified observation or scenario",
                })
                self.assertFalse(result["validated_prediction_available"])
                self.assertIn("hazard_assessment", result)
                self.assertIn("potential_consequences", result)
                self.assertEqual(
                    set(result["recommendations"]),
                    {"before", "during", "after", "long_term"},
                )
                self.assertIn("historical_validation", result["validation"])
                self.assertTrue(result["evidence"]["sources"])

    def test_unknown_hazard_does_not_fall_back_to_another_model(self):
        with self.assertRaises(ValueError):
            assess_disaster(scenario("Tsunami"))

    def test_population_and_assets_are_never_claimed_as_estimated_exposure(self):
        result = assess_disaster(
            scenario("Flood", affected_population=200, assets=["Hospitals"])
        )
        consequence = result["potential_consequences"]
        self.assertEqual(
            consequence["human_population"]["status"],
            "user_supplied_context_not_estimated",
        )
        self.assertEqual(
            consequence["infrastructure"]["status"],
            "user_nominated_not_spatially_verified",
        )

    def test_all_hazards_expose_fail_closed_consequences_and_four_recommendation_phases(self):
        expected_categories = {"human", "infrastructure", "environmental", "economic"}
        for hazard in HAZARD_OPTIONS:
            with self.subTest(hazard=hazard):
                result = assess_disaster(scenario(hazard))
                categories = result["potential_consequences"]["categories"]
                self.assertEqual(set(categories), expected_categories)
                for category in categories.values():
                    self.assertEqual(category["status"], "INSUFFICIENT EVIDENCE")
                    self.assertIsNone(category["observed_impacts"]["value"])
                    self.assertIsNone(category["modelled_estimate"]["value"])
                    self.assertFalse(category["location_specific"])
                    self.assertFalse(category["validated"])
                    self.assertTrue(category["data_requirements"])

                recommendations = result["recommendations"]
                self.assertEqual(
                    set(recommendations),
                    {"before", "during", "after", "long_term"},
                )
                all_items = [
                    item
                    for phase_items in recommendations.values()
                    for item in phase_items
                ]
                recommendation_categories = {item["category"] for item in all_items}
                self.assertTrue(
                    {"prevention", "preparedness", "response", "recovery"}
                    .issubset(recommendation_categories)
                )
                self.assertTrue(
                    all(item["category"] == "long_term" for item in recommendations["long_term"])
                )
                for item in all_items:
                    self.assertTrue(item["relevance"])
                    self.assertTrue(item["evidence_or_authority"])
                    self.assertTrue(item["scope"])
                    self.assertTrue(item["limitations"])
                    self.assertEqual(
                        item["priority"],
                        "Unranked; follow competent authority guidance.",
                    )

    def test_user_population_context_never_becomes_a_consequence_estimate(self):
        result = assess_disaster(scenario("Flood", affected_population=200))
        human = result["potential_consequences"]["categories"]["human"]
        self.assertEqual(
            human["user_supplied_context"]["value_people"],
            200,
        )
        self.assertIsNone(human["modelled_estimate"]["value"])


class FloodAndCycloneTests(unittest.TestCase):
    def test_flood_rational_method_calculates_only_with_complete_inputs(self):
        result = assess_flood(
            scenario(
                rainfall_mm=24,
                rainfall_period="Last 24 hours",
                catchment_area_ha=1,
                runoff_coefficient=0.5,
            )
        )
        indicators = result["hazard_assessment"]["indicators"]
        self.assertEqual(indicators["rainfall_depth_and_period"]["value"], 1)
        self.assertAlmostEqual(
            indicators["rational_method_peak_runoff_m3_s"]["value"],
            0.001388888888888889,
        )
        self.assertIn("not_local_flood_severity", result["result_status"])

    def test_flood_missing_duration_does_not_assume_hourly_rainfall(self):
        result = assess_flood(scenario(rainfall_mm=100, rainfall_period="Other / state in notes"))
        self.assertIsNone(
            result["hazard_assessment"]["indicators"]["rainfall_depth_and_period"]["value"]
        )
        self.assertIsNone(
            result["hazard_assessment"]["indicators"]["rational_method_peak_runoff_m3_s"]["value"]
        )

    def test_flood_invalid_physical_inputs_fail_explicitly(self):
        with self.assertRaises(ValueError):
            assess_flood(scenario(rainfall_mm=-1, rainfall_period="Last 1 hour"))
        with self.assertRaises(ValueError):
            assess_flood(scenario(catchment_area_ha=1, runoff_coefficient=1.1))

    def test_cyclone_dynamic_pressure_is_physical_indicator_not_damage_score(self):
        result = assess_cyclone(scenario("Cyclone", wind_speed_kmh=36))
        indicators = result["hazard_assessment"]["indicators"]
        self.assertEqual(indicators["wind_speed_m_s"], 10)
        self.assertAlmostEqual(indicators["idealized_dynamic_pressure_pa"], 61.25)
        self.assertIn("not a structural", result["methodology"]["scientific_basis"])

    def test_cyclone_wind_range_is_validated(self):
        with self.assertRaises(ValueError):
            assess_cyclone(scenario("Cyclone", wind_speed_kmh=501))


class EarthquakeAndLandslideTests(unittest.TestCase):
    def test_earthquake_reports_optional_mmi_without_predicting_shaking(self):
        result = assess_earthquake(scenario("Earthquake", earthquake_mmi=7))
        self.assertEqual(result["hazard_assessment"]["indicators"]["reported_mmi"], 7)
        self.assertIn("Very strong", result["hazard_assessment"]["indicators"]["mmi_description"])
        self.assertFalse(result["validated_prediction_available"])

    def test_earthquake_rejects_non_integer_or_out_of_scale_mmi(self):
        for value in (0, 13, 3.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                assess_earthquake(scenario("Earthquake", earthquake_mmi=value))

    def test_landslide_computes_rainfall_mean_only_and_withholds_trigger_class(self):
        result = assess_landslide(
            scenario("Landslide", rainfall_mm=72, rainfall_period="Last 3 days")
        )
        indicator = result["hazard_assessment"]["indicators"]["mean_rainfall_intensity"]
        self.assertEqual(indicator["value"], 1)
        self.assertIn("threshold", result["hazard_assessment"]["indicators"]["threshold_comparison"])
        self.assertIn("no_susceptibility", result["result_status"])

    def test_landslide_rainfall_and_antecedent_values_are_bounded(self):
        with self.assertRaises(ValueError):
            assess_landslide(
                scenario("Landslide", antecedent_rainfall_mm=-1)
            )


class HeatAndDroughtTests(unittest.TestCase):
    def test_heat_index_matches_nws_example(self):
        index = heat_index_fahrenheit(100, 55)
        self.assertIsNotNone(index)
        self.assertEqual(round(index), 124)

    def test_heatwave_requires_humidity_and_valid_domain(self):
        missing = assess_heatwave(scenario("Heatwave", temperature_c=38))
        self.assertIsNone(missing["hazard_assessment"]["indicators"]["heat_index_f"])
        outside = assess_heatwave(
            scenario("Heatwave", temperature_c=20, relative_humidity_percent=60)
        )
        self.assertIsNone(outside["hazard_assessment"]["indicators"]["heat_index_f"])

    def test_heatwave_rejects_humidity_outside_physical_range(self):
        with self.assertRaises(ValueError):
            assess_heatwave(
                scenario("Heatwave", temperature_c=40, relative_humidity_percent=101)
            )

    def test_spi_refuses_short_climatology(self):
        result = calculate_spi1(monthly_test_series()[:120])
        self.assertEqual(result["status"], "insufficient_evidence")
        self.assertIsNone(result["spi1"])

    def test_spi_calculates_standardized_anomaly_with_30_year_series(self):
        result = calculate_spi1(monthly_test_series())
        self.assertEqual(result["status"], "descriptive_spi1_calculated")
        self.assertEqual(result["calendar_month_reference_count"], 30)
        self.assertTrue(-7 <= result["spi1"] <= 7)
        self.assertIn(result["category"], {
            "Extremely dry",
            "Severely dry",
            "Moderately dry",
            "Near normal",
            "Moderately wet",
            "Very wet",
            "Extremely wet",
        })

    def test_spi_rejects_duplicate_or_gapped_months(self):
        duplicate = monthly_test_series()
        duplicate[1] = dict(duplicate[0])
        with self.assertRaises(ValueError):
            calculate_spi1(duplicate)
        gap = monthly_test_series()
        gap.pop(20)
        self.assertEqual(
            calculate_spi1(gap)["status"],
            "insufficient_evidence",
        )

    def test_drought_csv_requires_named_columns_and_nonnegative_rainfall(self):
        with self.assertRaises(ValueError):
            parse_monthly_precipitation_csv("date,value\n1991-01,10\n")
        with self.assertRaises(ValueError):
            parse_monthly_precipitation_csv(
                "month,precipitation_mm\n1991-01,-1\n"
            )
        self.assertEqual(
            len(
                parse_monthly_precipitation_csv(
                    "month,precipitation_mm\n1991-01,10\n"
                )
            ),
            1,
        )


class IndustrialAndCompoundTests(unittest.TestCase):
    def test_industrial_comparison_requires_matching_unit_and_averaging_period(self):
        result = assess_industrial(
            scenario(
                "Industrial incident",
                pollutant_name="PM2.5",
                pollutant_concentration=30,
                pollutant_reference_value=15,
                pollutant_unit="µg/m³",
                pollutant_reference_unit="µg/m³",
                pollutant_averaging_period="24-hour",
                pollutant_reference_averaging_period="24-hour",
            )
        )
        self.assertEqual(
            result["hazard_assessment"]["indicators"]["concentration_to_reference_ratio"],
            2,
        )
        self.assertIn("No industrial incident", result["hazard_assessment"]["severity"])

    def test_industrial_comparison_rejects_mismatched_unit_or_period(self):
        base = scenario(
            "Industrial incident",
            pollutant_concentration=30,
            pollutant_reference_value=15,
            pollutant_unit="µg/m³",
            pollutant_reference_unit="mg/m³",
            pollutant_averaging_period="24-hour",
            pollutant_reference_averaging_period="24-hour",
        )
        with self.assertRaises(ValueError):
            assess_industrial(base)
        base["pollutant_reference_unit"] = "µg/m³"
        base["pollutant_reference_averaging_period"] = "annual"
        with self.assertRaises(ValueError):
            assess_industrial(base)

    def test_compound_cyclone_flood_keeps_components_separate(self):
        result = assess_disaster(
            scenario(
                "Compound: cyclone + flood",
                wind_speed_kmh=90,
                rainfall_mm=120,
                rainfall_period="Last 24 hours",
            )
        )
        self.assertEqual(
            set(result["hazard_assessment"]["components"]),
            {"cyclone", "flood"},
        )
        self.assertEqual(
            result["hazard_assessment"]["interaction_status"],
            "unresolved_dependency",
        )
        self.assertNotIn("combined_score", result["hazard_assessment"])
        self.assertIn("component_assessments", result)

    def test_compound_rainfall_drainage_compares_only_explicit_scenario_values(self):
        result = assess_disaster(
            scenario(
                "Compound: heavy rainfall + drainage failure",
                rainfall_mm=24,
                rainfall_period="Last 1 hour",
                catchment_area_ha=1,
                runoff_coefficient=0.5,
                drainage_capacity_m3_s=0.001,
            )
        )
        indicators = result["hazard_assessment"]["indicators"]
        self.assertAlmostEqual(indicators["estimated_peak_runoff_m3_s"], 0.03333333333333333)
        self.assertGreater(indicators["runoff_to_capacity_ratio"], 1)
        self.assertEqual(
            indicators["hydraulic_relation"],
            "scenario_runoff_exceeds_user_supplied_capacity",
        )
        self.assertIn("not proof", result["hazard_assessment"]["severity"])

    def test_rainfall_drainage_consequence_indicator_changes_with_capacity(self):
        base = {
            "hazard": "Compound: heavy rainfall + drainage failure",
            "rainfall_mm": 24,
            "rainfall_period": "Last 1 hour",
            "catchment_area_ha": 1,
            "runoff_coefficient": 0.5,
        }
        exceeded = assess_disaster(
            scenario(**base, drainage_capacity_m3_s=0.005)
        )
        not_exceeded = assess_disaster(
            scenario(**base, drainage_capacity_m3_s=0.05)
        )
        high_impact = exceeded["potential_consequences"]["categories"]["infrastructure"]
        lower_impact = not_exceeded["potential_consequences"]["categories"]["infrastructure"]

        self.assertIn("SCENARIO INDICATOR", high_impact["status"])
        self.assertEqual(
            high_impact["modelled_estimate"]["value"]["hydraulic_relation"],
            "scenario_runoff_exceeds_user_supplied_capacity",
        )
        self.assertGreater(
            high_impact["modelled_estimate"]["value"]["scenario_excess_flow_m3_s"],
            0,
        )
        self.assertEqual(
            lower_impact["modelled_estimate"]["value"]["hydraulic_relation"],
            "scenario_runoff_does_not_exceed_user_supplied_capacity",
        )
        self.assertEqual(
            lower_impact["modelled_estimate"]["value"]["scenario_excess_flow_m3_s"],
            0,
        )
        for consequence in (high_impact, lower_impact):
            self.assertFalse(consequence["location_specific"])
            self.assertFalse(consequence["validated"])
            self.assertIn("not observed", consequence["modelled_estimate"]["status"])

    def test_compound_drainage_model_does_not_compute_without_capacity(self):
        result = assess_disaster(
            scenario(
                "Compound: heavy rainfall + drainage failure",
                rainfall_mm=24,
                rainfall_period="Last 1 hour",
                catchment_area_ha=1,
                runoff_coefficient=0.5,
            )
        )
        self.assertIsNone(
            result["hazard_assessment"]["indicators"]["runoff_to_capacity_ratio"]
        )
        self.assertEqual(
            result["hazard_assessment"]["indicators"]["hydraulic_relation"],
            "unavailable",
        )


if __name__ == "__main__":
    unittest.main()

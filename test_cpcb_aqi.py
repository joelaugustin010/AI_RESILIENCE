"""Reference and boundary tests for the CPCB National AQI implementation."""

import unittest

from src.cpcb_aqi import (
    CPCBAQIError,
    CPCB_AQI_REPORT_URL,
    calculate_ind_aqi,
    calculate_pollutant_subindex,
    cpcb_aqi_category,
)


def record(pollutant, concentration, *, unit=None, averaging_period=None, valid_hours=24):
    from src.cpcb_aqi import CPCB_AVERAGING_PERIODS, CPCB_UNITS

    return {
        "pollutant": pollutant,
        "concentration": concentration,
        "unit": unit or CPCB_UNITS[pollutant],
        "averaging_period": averaging_period or CPCB_AVERAGING_PERIODS[pollutant],
        "valid_hours": valid_hours,
    }


class CPCBSubIndexTests(unittest.TestCase):
    def test_documented_good_and_satisfactory_reference_values(self):
        self.assertEqual(calculate_pollutant_subindex("PM10", 0)["sub_index"], 0)
        self.assertEqual(calculate_pollutant_subindex("PM10", 50)["sub_index"], 50)
        self.assertEqual(calculate_pollutant_subindex("PM2.5", 30)["sub_index"], 50)
        self.assertEqual(calculate_pollutant_subindex("CO", 1.0)["sub_index"], 50)

    def test_breakpoint_boundaries_are_monotonic(self):
        for pollutant, edges in {
            "PM10": (50, 100, 250, 350, 430),
            "PM2.5": (30, 60, 90, 120, 250),
            "NO2": (40, 80, 180, 280, 400),
            "O3": (50, 100, 168, 208, 748),
            "CO": (1, 2, 10, 17, 34),
            "SO2": (40, 80, 380, 800, 1600),
            "NH3": (200, 400, 800, 1200, 1800),
            "Pb": (0.5, 1, 2, 3, 3.5),
        }.items():
            values = [calculate_pollutant_subindex(pollutant, edge)["sub_index"] for edge in edges]
            self.assertEqual(values, [50, 100, 200, 300, 400], pollutant)

    def test_severe_open_ended_band_is_top_coded_not_extrapolated(self):
        result = calculate_pollutant_subindex("PM2.5", 251)
        self.assertEqual(result["sub_index"], 500)
        self.assertTrue(result["capped_at_500"])

    def test_invalid_concentrations_and_pollutants_are_rejected(self):
        for value in (-1, float("nan"), float("inf"), True):
            with self.assertRaises(CPCBAQIError):
                calculate_pollutant_subindex("PM10", value)
        with self.assertRaises(CPCBAQIError):
            calculate_pollutant_subindex("NOx", 10)

    def test_category_boundaries(self):
        self.assertEqual(cpcb_aqi_category(50)[0], "Good")
        self.assertEqual(cpcb_aqi_category(51)[0], "Satisfactory")
        self.assertEqual(cpcb_aqi_category(100)[0], "Satisfactory")
        self.assertEqual(cpcb_aqi_category(101)[0], "Moderate")
        self.assertEqual(cpcb_aqi_category(201)[0], "Poor")
        self.assertEqual(cpcb_aqi_category(301)[0], "Very Poor")
        self.assertEqual(cpcb_aqi_category(401)[0], "Severe")
        for value in (-1, 501, 50.5, True):
            with self.assertRaises(CPCBAQIError):
                cpcb_aqi_category(value)


class CPCBOverallAQITests(unittest.TestCase):
    def test_three_pollutants_including_particulate_produce_maximum_subindex(self):
        result = calculate_ind_aqi([
            record("PM2.5", 60),
            record("NO2", 40),
            record("SO2", 80),
        ])
        self.assertEqual(result["status"], "calculated")
        self.assertEqual(result["aqi"], 100)
        self.assertEqual(result["category"], "Satisfactory")
        self.assertEqual(result["dominant_pollutant"], "PM2.5")
        self.assertEqual(result["evidence_status"], "CALCULATED INDICATOR")

    def test_official_method_source_is_recorded(self):
        result = calculate_ind_aqi([record("PM10", 20)])
        self.assertEqual(result["method_source"], CPCB_AQI_REPORT_URL)

    def test_missing_pollutants_are_not_zero_and_cannot_make_overall_aqi(self):
        result = calculate_ind_aqi([record("PM2.5", 20), record("NO2", 10)])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(result["aqi"])
        self.assertEqual(len(result["sub_indices"]), 2)

    def test_three_pollutants_without_pm_cannot_make_overall_aqi(self):
        result = calculate_ind_aqi([
            record("NO2", 20), record("SO2", 20), record("CO", 0.5),
        ])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(result["aqi"])
        self.assertTrue(any("PM2.5 or PM10" in item for item in result["missing_requirements"]))

    def test_insufficient_valid_hours_excludes_record(self):
        result = calculate_ind_aqi([
            record("PM2.5", 20, valid_hours=15),
            record("NO2", 20),
            record("SO2", 20),
        ])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["eligible_pollutant_count"], 2)

    def test_pollutant_specific_averaging_periods_are_enforced(self):
        result = calculate_ind_aqi([
            record("PM2.5", 20),
            record("NO2", 20),
            record("CO", 0.5, averaging_period="24-hour"),
        ])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIn("Requires 8-hour averaging.", result["excluded_records"][0]["reason"])

    def test_unit_mismatch_is_excluded_not_silently_converted(self):
        result = calculate_ind_aqi([
            record("PM2.5", 20, unit="mg/m3"),
            record("NO2", 20),
            record("SO2", 20),
        ])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIn("Expected unit ug/m3.", result["excluded_records"][0]["reason"])

    def test_duplicate_pollutants_and_negative_values_are_rejected(self):
        with self.assertRaises(CPCBAQIError):
            calculate_ind_aqi([record("PM2.5", 10), record("PM2.5", 20)])
        with self.assertRaises(CPCBAQIError):
            calculate_ind_aqi([record("PM2.5", -1)])

    def test_empty_input_is_explicitly_insufficient(self):
        result = calculate_ind_aqi([])
        self.assertEqual(result["status"], "insufficient_data")
        self.assertIsNone(result["aqi"])


if __name__ == "__main__":
    unittest.main()

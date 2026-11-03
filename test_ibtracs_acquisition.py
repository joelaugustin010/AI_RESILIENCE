"""Validation tests for the preserved NOAA IBTrACS snapshot pipeline."""

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.validate_ibtracs_north_indian import IBTrACSDataError, validate_csv


class IBTrACSValidationTests(unittest.TestCase):
    def _write_csv(self, directory: str, rows: list[list[str]]) -> Path:
        path = Path(directory) / "ibtracs.csv"
        with path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(
                ["SID", "BASIN", "NAME", "ISO_TIME", "LAT", "LON", "WMO_WIND", "WMO_PRES", "DIST2LAND"]
            )
            writer.writerow(
                ["", "", "", "", "degrees_north", "degrees_east", "kts", "mb", "km"]
            )
            writer.writerows(rows)
        return path

    def test_scans_rows_units_coordinates_and_koch_area_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_csv(
                directory,
                [
                    ["storm-1", "NI", "EXAMPLE", "2020-05-01 00:00:00", "10", "76.3", "50", "990", "5"],
                    ["storm-2", "NI", "OTHER", "2021-06-02 03:00:00", "15", "80", "40", "995", "25"],
                ],
            )
            result = validate_csv(path)

        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["storm_id_count"], 2)
        self.assertEqual(result["year_min"], 2020)
        self.assertEqual(result["year_max"], 2021)
        self.assertEqual(result["unit_mismatches"], {})
        self.assertEqual(result["points_within_300_km_of_kochi_reference"], 1)

    def test_rejects_invalid_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_csv(
                directory,
                [["storm-1", "NI", "EXAMPLE", "2020-05-01 00:00:00", "91", "76.3", "50", "990", "5"]],
            )
            with self.assertRaises(IBTrACSDataError):
                validate_csv(path)

    def test_rejects_duplicate_storm_time_keys(self):
        row = ["storm-1", "NI", "EXAMPLE", "2020-05-01 00:00:00", "10", "76.3", "50", "990", "5"]
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_csv(directory, [row, row])
            with self.assertRaisesRegex(IBTrACSDataError, "duplicate SID/ISO_TIME"):
                validate_csv(path)

    def test_rejects_rows_with_a_different_number_of_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self._write_csv(
                directory,
                [["storm-1", "NI", "EXAMPLE", "2020-05-01 00:00:00", "10", "76.3", "50", "990"]],
            )
            with self.assertRaisesRegex(IBTrACSDataError, "column count"):
                validate_csv(path)


if __name__ == "__main__":
    unittest.main()

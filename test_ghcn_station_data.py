"""Tests for NOAA GHCN-Daily fixed-width station inventory and observations."""

import unittest

from scripts.acquire_ghcn_kochi_stations import (
    GHCNDataError,
    parse_station_inventory,
    validate_station_daily,
)


def _dly_record(station: str, year: int, month: int, element: str, observations: dict[int, tuple[int, str, str, str]]) -> str:
    fields = []
    for day in range(1, 32):
        value, mflag, qflag, sflag = observations.get(day, (-9999, " ", " ", " "))
        fields.append(f"{value:5d}{mflag}{qflag}{sflag}")
    return f"{station:<11}{year:04d}{month:02d}{element:<4}" + "".join(fields)


class GHCNStationDataTests(unittest.TestCase):
    def test_reads_fixed_width_station_metadata_for_koch_area_stations(self):
        lines = [
            f"{'IN010032300':<11} {9.98:8.4f} {76.28:9.4f} {3.0:6.1f} {'':2} {'ERNAKULAM':<30} {'':3} {'':3} {''}",
            f"{'IN010033100':<11} {9.967:8.4f} {76.233:9.4f} {3.0:6.1f} {'':2} {'FORT COCHIN':<30} {'':3} {'':3} {''}",
        ]

        stations = parse_station_inventory("\n".join(lines).encode("ascii"))

        self.assertEqual(stations["IN010032300"]["name"], "ERNAKULAM")
        self.assertAlmostEqual(stations["IN010033100"]["longitude"], 76.233)

    def test_reads_prcp_units_and_retains_quality_source_flags(self):
        rows = [
            _dly_record(
                "IN010032300",
                1969,
                1,
                "PRCP",
                {
                    1: (0, " ", " ", "W"),
                    2: (125, " ", " ", "W"),
                    3: (20, " ", "I", "W"),
                },
            )
        ]

        result = validate_station_daily("\n".join(rows).encode("ascii"), "IN010032300")

        self.assertEqual(result["precipitation_observation_count"], 3)
        self.assertEqual(result["precipitation_quality_flagged_count"], 1)
        self.assertEqual(result["precipitation_source_flag_counts"]["W"], 3)
        self.assertIn("tenths of millimetres", result["precipitation_units"])

    def test_rejects_wrong_station_id(self):
        row = _dly_record("IN010033100", 1969, 1, "PRCP", {1: (5, " ", " ", "W")})

        with self.assertRaisesRegex(GHCNDataError, "identity mismatch"):
            validate_station_daily(row.encode("ascii"), "IN010032300")


if __name__ == "__main__":
    unittest.main()

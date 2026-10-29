"""Unit tests for USGS regional earthquake catalogue acquisition and audit."""
from __future__ import annotations

import unittest

import pandas as pd

from scripts.acquire_earthquake_catalog import build_audit_report, haversine_km, iter_windows, normalize_feature


class EarthquakeCatalogAuditTests(unittest.TestCase):
    def test_haversine_distance_is_zero_at_reference_point(self):
        self.assertAlmostEqual(float(haversine_km([9.9312], [76.2673])[0]), 0.0, places=5)

    def test_time_windows_are_contiguous_and_non_overlapping(self):
        windows = list(iter_windows(2020, end_date=__import__("datetime").date(2026, 10, 29), window_years=3))
        self.assertEqual(windows[0]["starttime"], "2020-01-01T00:00:00")
        self.assertEqual(windows[-1]["endtime"], "2026-10-29T23:59:59")
        for left, right in zip(windows, windows[1:]):
            self.assertLess(left["endtime"], right["starttime"])

    def test_normalizes_geojson_feature_without_losing_source_fields(self):
        feature = {
            "id": "us700test",
            "properties": {"time": 1735689600000, "mag": 3.4, "magType": "ml", "place": "near Kochi", "url": "https://earthquake.usgs.gov/event/us700test", "status": "reviewed", "tsunami": 0, "sig": 42, "net": "us", "type": "earthquake"},
            "geometry": {"type": "Point", "coordinates": [76.2673, 9.9312, 12.0]},
        }
        row = normalize_feature(feature, {"starttime": "2025-01-01T00:00:00", "endtime": "2025-12-31T23:59:59"})
        self.assertEqual(row["event_id"], "us700test")
        self.assertAlmostEqual(row["latitude"], 9.9312)
        self.assertAlmostEqual(row["depth_km"], 12.0)
        self.assertEqual(row["magnitude"], 3.4)

    def test_audit_counts_events_and_keeps_duplicate_ids_visible(self):
        events = pd.DataFrame([
            {"event_id": "a", "time_utc": "2024-01-01T00:00:00Z", "latitude": 9.9312, "longitude": 76.2673, "depth_km": 10, "magnitude": 3.2, "place": "Kochi"},
            {"event_id": "b", "time_utc": "2024-01-02T00:00:00Z", "latitude": 10.5, "longitude": 76.5, "depth_km": 20, "magnitude": 4.1, "place": "near Kerala"},
            {"event_id": "a", "time_utc": "2024-01-03T00:00:00Z", "latitude": 20.0, "longitude": 80.0, "depth_km": 30, "magnitude": 5.1, "place": "far"},
        ])
        audit = build_audit_report(events, [], {"start_year": 2020, "end_date_utc": "2024-01-03", "min_magnitude": 2.5, "radius_km": 1000})
        self.assertEqual(audit["source"]["event_count"], 3)
        self.assertEqual(audit["data_quality"]["duplicate_event_id_rows"], 2)
        self.assertEqual(audit["kochi_proximity_screening"]["events_within_100_km"], 2)
        self.assertEqual(audit["kochi_proximity_screening"]["events_within_1000_km"], 2)
        self.assertEqual(audit["status"], "DESCRIPTIVE_REGIONAL_SEISMICITY_ONLY_NOT_VALIDATED_FOR_LOCAL_GROUND_SHAKING")

    def test_required_fields_are_checked(self):
        with self.assertRaisesRegex(ValueError, "missing required field"):
            build_audit_report(pd.DataFrame({"event_id": ["x"]}), [], {})


if __name__ == "__main__":
    unittest.main()

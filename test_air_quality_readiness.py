"""Checks that the pollution page only presents source-verified context."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class AirQualityAcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.register = json.loads(
            (ROOT / "data" / "reference" / "air_quality_acquisition.json").read_text(encoding="utf-8")
        )
        cls.page = (ROOT / "app_pages" / "air_pollution.py").read_text(encoding="utf-8")

    def test_kspcb_station_inventory_is_source_linked_and_nonspatial(self):
        stations = self.register["kspcb_namp_ernakulam_stations"]
        self.assertEqual(len(stations), 7)
        self.assertTrue(all(row["program"] == "NAMP" for row in stations))
        self.assertTrue(all("latitude" not in row and "longitude" not in row for row in stations))
        kspcb = next(source for source in self.register["sources"] if "KSPCB" in source["publisher"])
        self.assertIn("kspcb.kerala.gov.in", kspcb["url"])
        self.assertIn("not", kspcb["reuse_status"].lower())

    def test_cpcb_source_is_catalogued_with_api_access_blocker(self):
        cpcb = next(source for source in self.register["sources"] if "CPCB" in source["publisher"])
        self.assertIn("data.gov.in", cpcb["url"])
        self.assertIn("API-key", cpcb["blocker"])
        self.assertIn("NDSAP", cpcb["evidence"])

    def test_illustrative_csv_is_explicitly_not_analyzed(self):
        self.assertIn("intentionally does not rank or analyze those rows", self.page)
        self.assertNotIn("load_dataset", self.page)
        self.assertIn("cannot currently be identified", self.page)


if __name__ == "__main__":
    unittest.main()

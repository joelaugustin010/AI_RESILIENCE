"""Regression checks for the official Kochi ward-name/code reference."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ROSTER_PATH = ROOT / "data" / "reference" / "kochi_official_ward_roster_2025.json"


class OfficialKochiWardRosterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
        cls.wards = cls.roster["wards"]

    def test_official_roster_has_76_unique_ward_codes_and_names(self):
        self.assertEqual(self.roster["expected_ward_count"], 76)
        self.assertEqual(len(self.wards), 76)
        codes = [ward[0] for ward in self.wards]
        names = [ward[1] for ward in self.wards]
        self.assertEqual(len(set(codes)), 76)
        self.assertEqual(len(set(names)), 76)
        self.assertTrue(all(code.startswith("C07003") for code in codes))
        self.assertTrue(all(name and name == name.strip() for name in names))

    def test_ward_codes_are_sequential_and_roster_is_not_spatial_data(self):
        self.assertEqual(
            [ward[0] for ward in self.wards],
            [f"C07003{number:03d}" for number in range(1, 77)],
        )
        self.assertEqual(self.roster["spatial_use"], "reference_only_not_geometry")
        self.assertIn("sec.kerala.gov.in", self.roster["source_url"])

    def test_known_problematic_names_are_preserved_exactly(self):
        names = {name for _, name in self.wards}
        self.assertIn("KALOOR-NORTH", names)
        self.assertIn("PALLURUTHY-KACHERIPADY", names)
        self.assertIn("FORTKOCHI VELI", names)
        self.assertIn("EDAKOCHI SOUTH", names)


if __name__ == "__main__":
    unittest.main()

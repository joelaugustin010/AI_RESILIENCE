"""Beginner-friendly tests for the demonstration assessment rules."""

import unittest

from assessment import assess_conditions


class AssessConditionsTests(unittest.TestCase):
    def test_rainfall_rule_at_boundary(self):
        self.assertEqual(assess_conditions(99.9, 0, "Normal"), 0)
        self.assertEqual(assess_conditions(100, 0, "Normal"), 1)

    def test_river_level_rule_at_boundary(self):
        self.assertEqual(assess_conditions(0, 4.9, "Normal"), 0)
        self.assertEqual(assess_conditions(0, 5, "Normal"), 1)

    def test_waterlogged_ground_adds_one_point(self):
        self.assertEqual(assess_conditions(0, 0, "Waterlogged"), 1)

    def test_unstable_ground_adds_one_point(self):
        self.assertEqual(assess_conditions(0, 0, "Unstable"), 1)

    def test_normal_and_dry_ground_add_no_points(self):
        self.assertEqual(assess_conditions(0, 0, "Normal"), 0)
        self.assertEqual(assess_conditions(0, 0, "Dry"), 0)

    def test_all_three_rules_can_add_up_to_three_points(self):
        self.assertEqual(assess_conditions(100, 5, "Waterlogged"), 3)

    def test_two_rules_add_two_points(self):
        self.assertEqual(assess_conditions(100, 5, "Dry"), 2)


if __name__ == "__main__":
    unittest.main()
"""Tests for explicitly unresolved infrastructure cascade pathways."""

import unittest

from src.infrastructure_dependencies import (
    CONCEPTUAL_DEPENDENCIES,
    DependencyEdge,
    dependency_review_table,
    find_dependency_paths,
)


class InfrastructureDependencyTests(unittest.TestCase):
    def test_road_hospital_cascade_is_represented_but_unresolved(self):
        paths = find_dependency_paths(
            CONCEPTUAL_DEPENDENCIES,
            "urban_flooding",
            "hospital_service_continuity",
        )
        road_path = next(path for path in paths if "road_passability" in path["Path"])
        self.assertEqual(road_path["Evidence state"], "Unresolved dependency")
        self.assertIn("service_dependency", road_path["Relationship types"])
        self.assertIn("Unverified", road_path["Evidence gaps"])

    def test_conceptual_edges_do_not_claim_local_kochi_evidence(self):
        table = dependency_review_table()
        self.assertTrue(table["Evidence state"].eq("Unverified").all())
        self.assertTrue(table["Evidence reference"].eq("No local evidence attached").all())
        cyclone_rain = table.loc[
            table["From"].eq("cyclone conditions") & table["To"].eq("heavy rainfall")
        ].iloc[0]
        self.assertEqual(cyclone_rain["Relationship type"], "possible_causal_driver")
        self.assertIn("causality must be established", cyclone_rain["Relationship to investigate"])

    def test_only_fully_referenced_verified_edges_form_verified_path(self):
        edges = [
            DependencyEdge(
                "road",
                "access",
                "road supports access",
                "service_dependency",
                "Verified",
                "event-record-1",
            ),
            DependencyEdge(
                "access",
                "hospital",
                "access supports hospital service",
                "service_dependency",
                "Unverified",
            ),
        ]
        result = find_dependency_paths(edges, "road", "hospital")
        self.assertEqual(result[0]["Evidence state"], "Unresolved dependency")
        edges[1] = DependencyEdge(
            "access",
            "hospital",
            "access supports hospital service",
            "service_dependency",
            "Verified",
            "event-record-2",
        )
        result = find_dependency_paths(edges, "road", "hospital")
        self.assertEqual(result[0]["Evidence state"], "Verified links")

    def test_path_search_rejects_bad_input_and_avoids_cycles(self):
        with self.assertRaises(ValueError):
            find_dependency_paths([], "", "hospital")
        with self.assertRaises(ValueError):
            find_dependency_paths([], "road", "hospital", max_depth=0)
        edges = [
            DependencyEdge("a", "b", "first"),
            DependencyEdge("b", "a", "cycle"),
            DependencyEdge("b", "c", "last"),
        ]
        self.assertEqual(len(find_dependency_paths(edges, "a", "c")), 1)


if __name__ == "__main__":
    unittest.main()

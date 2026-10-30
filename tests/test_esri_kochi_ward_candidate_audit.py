"""Regression tests for the Esri/KSMART-linked ward geometry candidate audit."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EsriKochiWardCandidateAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(
            (ROOT / "reports" / "kochi_esri_ward_candidate_audit.json").read_text(encoding="utf-8")
        )
        cls.catalog = json.loads(
            (ROOT / "data" / "reference" / "spatial_sources.json").read_text(encoding="utf-8")
        )

    def test_candidate_has_76_valid_nonoverlapping_polygons_but_is_not_promoted(self):
        self.assertEqual(self.report["status"], "CANDIDATE_AUDITED_NOT_PROMOTED")
        self.assertFalse(self.report["summary"]["production_geometry_promoted"])
        candidate = self.report["candidate_towns"][0]
        audit = candidate["geometry_query"]
        topology = audit["topology_and_coverage"]
        self.assertEqual(audit["feature_count"], 76)
        self.assertEqual(audit["valid_polygon_count"], 76)
        self.assertEqual(audit["invalid_geometry_count"], 0)
        self.assertEqual(audit["source_name_count"], 76)
        self.assertEqual(audit["unique_source_code_count"], 76)
        self.assertTrue(audit["source_code_numbers_exactly_1_to_76"])
        self.assertTrue(topology["ward_union_is_valid"])
        self.assertEqual(topology["pairwise_interior_overlap_pairs_over_1m2"], 0)

    def test_source_name_crosswalk_keeps_sec_and_final_pdf_differences_visible(self):
        audit = self.report["candidate_towns"][0]["geometry_query"]
        self.assertEqual(audit["exact_SEC_name_match_count_by_source_code_number"], 65)
        self.assertEqual(audit["exact_final_PDF_label_match_count_by_source_code_number"], 75)
        self.assertEqual(len(audit["source_code_name_crosswalk"]), 76)
        self.assertEqual(
            sum(not row["exact_SEC_name_match_for_same_number"] for row in audit["source_code_name_crosswalk"]),
            11,
        )
        self.assertTrue(
            any(row["parsed_ward_number"] == 62 and not row["final_PDF_label_for_same_number"]
                for row in audit["source_code_name_crosswalk"])
        )

    def test_boundary_discrepancy_and_older_draft_difference_block_promotion(self):
        audit = self.report["candidate_towns"][0]["geometry_query"]
        boundary = audit["topology_and_coverage"]["configured_boundary_comparison"]
        draft = audit["comparison_with_older_draft_candidate"]
        self.assertGreater(boundary["symmetric_difference_area_km2"], 1.0)
        self.assertLess(boundary["intersection_over_union"], 0.99)
        self.assertEqual(draft["common_valid_ward_numbers"], 73)
        self.assertLess(draft["mean_per_ward_iou"], 0.99)
        self.assertIn("not legal approval", boundary["status"].casefold().replace("_", " "))

    def test_catalog_marks_candidate_as_provisional_and_not_production(self):
        entries = [
            item for item in self.catalog["datasets"]
            if item.get("layer_id") == "kochi_wards_esri_kmap_candidate_2026"
        ]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["status"], "candidate_not_integrated")
        self.assertEqual(entry["evidence_status"], "provisional")
        self.assertEqual(entry["spatial_use"], "candidate_only_not_production")
        self.assertIsNone(entry["local_file"])
        self.assertIn("reuse licence", entry["license"].casefold())


if __name__ == "__main__":
    unittest.main()

"""Regression tests for the official final-map reference audit.

These tests verify provenance and guardrails only. They do not assert that PDF
cartography is a valid GIS boundary layer.
"""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FinalMapReferenceAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(
            (ROOT / "reports" / "kochi_final_map_source_discovery.json").read_text(encoding="utf-8")
        )
        cls.catalog = json.loads(
            (ROOT / "data" / "reference" / "spatial_sources.json").read_text(encoding="utf-8")
        )

    def test_official_final_map_pdf_is_registered_as_reference_only(self):
        entries = [
            row for row in self.catalog["datasets"]
            if row.get("layer_id") == "kochi_final_ward_map_pdf_reference"
        ]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["spatial_use"], "reference_only_not_geometry")
        self.assertEqual(entry["evidence_status"], "reference_only")
        self.assertIn("NOT GIS GEOMETRY", entry["validation_status"])
        self.assertEqual(entry["source_sha256"], self.report["final_map_pdf_audit"]["sha256"])

    def test_pdf_audit_covers_all_official_ward_numbers_without_claiming_geometry(self):
        audit = self.report["final_map_pdf_audit"]
        self.assertTrue(audit["pdf_signature_valid"])
        self.assertEqual(audit["page_count"], 1)
        self.assertEqual(len(audit["numbered_comparison"]), 76)
        self.assertEqual(
            {row["ward_number"] for row in audit["numbered_comparison"]},
            set(range(1, 77)),
        )
        self.assertEqual(
            audit["status"],
            "OFFICIAL_FINAL_MAP_PDF_REFERENCE_ONLY_NOT_GIS_GEOMETRY",
        )

    def test_name_differences_and_unreadable_labels_are_explicit(self):
        audit = self.report["final_map_pdf_audit"]
        rows = audit["numbered_comparison"]
        for row in rows:
            if not row["exact_normalized_match"]:
                self.assertTrue(row["official_sec_name"])
                self.assertTrue(row["final_map_labels"] or row["ward_number"] > 0)
        self.assertLessEqual(audit["numbered_map_labels_extracted"], 76)
        self.assertLess(audit["numbered_comparison_exact_name_matches"], 76)

    def test_vector_tile_access_failures_do_not_promote_unverified_geometry(self):
        report = self.report
        self.assertIn("NOT_SPATIAL_LAYER_PROMOTION", report["vector_tile_sample_audit"]["status"])
        self.assertIn("no GIS geometry", " ".join(report["limitations"]).casefold())


if __name__ == "__main__":
    unittest.main()

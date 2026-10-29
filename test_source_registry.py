import unittest

from src.source_registry import (
    build_source_registry,
    source_fitness_summary,
    validate_source_record,
)


class SourceRegistryTests(unittest.TestCase):
    def test_registry_covers_every_registered_hydrology_dataset(self):
        records = build_source_registry()
        self.assertEqual(
            {record["dataset_id"] for record in records},
            {"rainfall_manual", "rainfall_cwc", "river_manual", "river_telemetry"},
        )

    def test_records_keep_unknown_metadata_explicit(self):
        for record in build_source_registry():
            self.assertIn("Not", record["license_status"])
            self.assertIn("Not", record["retrieval_date"])
            self.assertTrue(record["source_url"].startswith("https://"))

    def test_cwc_conflicts_are_not_hidden(self):
        record = next(r for r in build_source_registry() if r["dataset_id"] == "rainfall_cwc")
        self.assertIn("324", record["validation_status"])
        self.assertIn("conflicting", record["known_limitation"].lower())

    def test_river_data_does_not_claim_threshold_or_prediction_fitness(self):
        for record in build_source_registry():
            if record["dataset_id"].startswith("river_"):
                self.assertIn("no threshold", record["validation_status"].lower())
                self.assertFalse(source_fitness_summary(record)["prediction_permitted"])

    def test_missing_provenance_field_is_reported(self):
        record = build_source_registry()[0]
        record["license_status"] = ""
        self.assertIn(
            "Missing required provenance field: license_status",
            validate_source_record(record),
        )

    def test_blanket_verified_status_is_not_accepted_as_evidence(self):
        record = build_source_registry()[0]
        record["checksum_match"] = "verified"
        self.assertTrue(any("specific evidence and scope" in item for item in validate_source_record(record)))

    def test_registry_completeness_is_not_scientific_validation(self):
        for record in build_source_registry():
            summary = source_fitness_summary(record)
            self.assertTrue(summary["metadata_complete"])
            self.assertEqual(summary["scientific_fitness"], "Not established")
            self.assertFalse(summary["prediction_permitted"])
            self.assertFalse(summary["official_warning_permitted"])


if __name__ == "__main__":
    unittest.main()

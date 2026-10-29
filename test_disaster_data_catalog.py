import unittest

from src.disaster_data_catalog import get_catalog, validate_catalog_record


class DisasterDataCatalogTests(unittest.TestCase):
    def test_catalog_has_unique_ids_and_covers_multiple_hazards(self):
        records = get_catalog()
        ids = [record["id"] for record in records]
        self.assertEqual(len(ids), len(set(ids)))
        hazards = {hazard for record in records for hazard in record["hazards"]}
        self.assertGreaterEqual(len(hazards), 8)

    def test_every_record_has_required_metadata(self):
        for record in get_catalog():
            self.assertEqual(validate_catalog_record(record), [], record["id"])

    def test_acquisition_status_is_explicit_for_every_source(self):
        for record in get_catalog():
            status = record["status"].lower()
            self.assertTrue(status.strip(), record["id"])
            self.assertNotIn("scientifically validated", status, record["id"])
            self.assertNotIn("prediction approved", status, record["id"])

    def test_catalog_does_not_mutate_global_records(self):
        records = get_catalog()
        records[0]["hazards"].append("Fake hazard")
        self.assertNotIn("Fake hazard", get_catalog()[0]["hazards"])

    def test_invalid_priority_is_rejected(self):
        record = get_catalog()[0]
        record["priority"] = "P9"
        self.assertIn("priority must be P0, P1, or P2", validate_catalog_record(record))


if __name__ == "__main__":
    unittest.main()

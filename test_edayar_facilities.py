"""Evidence and integrity checks for the Edayar facility candidate inventory."""

import csv
import json
import unittest
from datetime import date
from pathlib import Path

from src.edayar_facilities import (
    FacilityInventoryError,
    consent_temporal_status,
    validate_consent_records,
    validate_facility_inventory,
)


ROOT = Path(__file__).resolve().parent
INDUSTRIAL = ROOT / "data" / "processed" / "industrial"
AS_OF = date(2026, 10, 23)


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


class EdayarInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.facilities = read_csv(INDUSTRIAL / "edayar_candidate_facilities.csv")
        cls.consents = read_csv(INDUSTRIAL / "edayar_consent_records.csv")
        cls.metadata = json.loads(
            (INDUSTRIAL / "edayar_facilities.metadata.json").read_text(encoding="utf-8")
        )

    def test_all_eight_candidates_have_unique_identities_and_valid_consent_links(self):
        self.assertEqual(len(self.facilities), 8)
        validate_facility_inventory(self.facilities)
        validate_consent_records(
            self.consents,
            {row["facility_id"] for row in self.facilities},
            AS_OF,
        )

    def test_duplicate_canonical_identity_or_alias_is_rejected(self):
        duplicate = [dict(row) for row in self.facilities]
        duplicate[1]["official_name"] = duplicate[0]["official_name"].upper()
        with self.assertRaisesRegex(FacilityInventoryError, "Duplicate facility identity"):
            validate_facility_inventory(duplicate)

        duplicate = [dict(row) for row in self.facilities]
        duplicate[1]["name_aliases"] += "|" + duplicate[0]["official_name"]
        with self.assertRaisesRegex(FacilityInventoryError, "Duplicate facility identity"):
            validate_facility_inventory(duplicate)

    def test_missing_coordinates_are_explicit_and_estate_coordinates_are_not_substituted(self):
        self.assertTrue(all(not row["facility_latitude"] and not row["facility_longitude"] for row in self.facilities))
        self.assertTrue(all(row["coordinates_status"] == "unavailable" for row in self.facilities))
        self.assertTrue(all("not quantifiable" in row["coordinate_uncertainty"].lower() for row in self.facilities))
        self.assertTrue(all("individual plant coordinate" in row["coordinates_evidence"] for row in self.facilities))

        inconsistent = [dict(row) for row in self.facilities]
        inconsistent[0]["coordinates_status"] = "verified"
        with self.assertRaisesRegex(FacilityInventoryError, "missing facility coordinates"):
            validate_facility_inventory(inconsistent)

        partial = [dict(row) for row in self.facilities]
        partial[0]["facility_latitude"] = "10.1"
        with self.assertRaisesRegex(FacilityInventoryError, "both present or both missing"):
            validate_facility_inventory(partial)

    def test_consent_dates_distinguish_historical_expired_and_documented_validity(self):
        by_id = {row["record_id"]: row for row in self.consents}
        self.assertEqual(consent_temporal_status(by_id["RUBBER-O-MALABAR-CTO-2020"], AS_OF), "historical")
        self.assertEqual(by_id["RUBBER-O-MALABAR-CTO-2020"]["evidence_status"], "historical")
        self.assertEqual(consent_temporal_status(by_id["CMRL-CTO-2023"], AS_OF), "verified")
        self.assertEqual(by_id["SUD-CTO-AIR-REJECTED-2023"]["evidence_status"], "historical")

        invalid = [dict(row) for row in self.consents]
        invalid[0]["valid_until"] = "2018-01-01"
        invalid[0]["evidence_status"] = "verified"
        with self.assertRaisesRegex(FacilityInventoryError, "does not match record dates"):
            validate_consent_records(
                invalid,
                {row["facility_id"] for row in self.facilities},
                AS_OF,
            )

    def test_missing_measured_emissions_are_unavailable_and_never_zero(self):
        self.assertTrue(all(not row["measured_emissions_value"] for row in self.facilities))
        self.assertTrue(all(row["measured_emissions_status"] == "unavailable" for row in self.facilities))
        self.assertTrue(all(row["ranking_status"] == "Candidate only; not ranked" for row in self.facilities))

        inconsistent = [dict(row) for row in self.facilities]
        inconsistent[0]["measured_emissions_status"] = "verified"
        with self.assertRaisesRegex(FacilityInventoryError, "missing measured emissions"):
            validate_facility_inventory(inconsistent)

    def test_source_metadata_preserves_prior_raw_hashes_and_states_download_blocker(self):
        preserved = {item["path"]: item for item in self.metadata["raw_files"]}
        self.assertEqual(
            preserved["data/raw/industrial/KWA_Edayar_CETP_DER_2022.pdf"]["sha256"],
            "649955b4008cdbf1e1f14133fa4cac6d33afdb046ca0dddfc57d6a053abe0d07",
        )
        self.assertEqual(
            preserved["data/raw/industrial/DIC_DA_EDAYAR.dwg"]["sha256"],
            "6a366806a35eb55eb25da4b9093780e4c8f9249ab18b5efabedb3acf5bc42a0a",
        )
        self.assertEqual(
            preserved["data/raw/industrial/KSPCB_OCMMS_CTO_red_page2_2015-2019.html"]["sha256"],
            "5763c6e94dda44e3a37babce22276c02a2011a17db294c7dc23529a53bc84893",
        )
        self.assertFalse(self.metadata["attempted_downloads"]["error_pages_retained"])
        self.assertIn("497-byte HTML", self.metadata["attempted_downloads"]["result"])
        self.assertEqual(len(self.metadata["attempted_downloads"]["attempted_targets"]), 10)
        source_ids = {source["source_id"] for source in self.metadata["sources"]}
        self.assertEqual(len(source_ids), len(self.metadata["sources"]))
        for source_map in self.metadata["field_source_map"].values():
            for source_ids_for_field in source_map.values():
                self.assertTrue(set(source_ids_for_field).issubset(source_ids))


if __name__ == "__main__":
    unittest.main()

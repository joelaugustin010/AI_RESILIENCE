"""Integrity checks for the additional KSPCB and Kerala DIC source records."""

import csv
import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


class NewOfficialAirEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.air_metadata = json.loads(
            (ROOT / "data/processed/air_quality/kspcb_caaqms_eloor_2026-09.metadata.json").read_text(encoding="utf-8")
        )
        cls.air = cls.air_metadata["sources"]["kspcb_caaqms_eloor_2026_09"]
        cls.dic = cls.air_metadata["sources"]["dic_edayar_allotment_2022"]

    def test_original_official_files_match_recorded_hashes_and_pdf_signatures(self):
        for source in (self.air, self.dic):
            raw_path = ROOT / source["raw_file"]
            self.assertTrue(
                raw_path.is_file(),
                f"Missing required official source: {source['raw_file']}. "
                "Run `python scripts/acquire_air_quality_sources.py` first.",
            )
            data = raw_path.read_bytes()
            self.assertTrue(data.startswith(b"%PDF-"))
            self.assertEqual(hashlib.sha256(data).hexdigest(), source["raw_sha256"])
        self.assertIn("kspcb.kerala.gov.in", self.air["source_url"])
        self.assertIn("industry.kerala.gov.in", self.dic["source_url"])

    def test_eloor_daily_pollutant_and_weather_extracts_preserve_dates_units_and_source(self):
        pollutants = read_rows(ROOT / "data/processed/air_quality/kspcb_caaqms_eloor_daily_2026-09.csv")
        weather = read_rows(ROOT / "data/processed/air_quality/kspcb_caaqms_eloor_weather_2026-09.csv")
        aqi = read_rows(ROOT / "data/processed/air_quality/kspcb_caaqms_eloor_aqi_2026-09.csv")
        self.assertEqual((len(pollutants), len(weather), len(aqi)), (270, 30, 30))
        self.assertEqual({row["observed_at"] for row in aqi}, {f"2026-09-{day:02}" for day in range(1, 31)})
        self.assertEqual({row["station"] for row in pollutants}, {"Eloor"})
        self.assertEqual({row["source_url"] for row in pollutants}, {self.air["source_url"]})
        self.assertTrue(all(row["value"] and float(row["value"]) >= 0 for row in pollutants))
        self.assertEqual({row["quality_flag"] for row in pollutants}, {"unassessed"})
        self.assertIn("not stated", " ".join(self.air["limitations"]).casefold())
        self.assertIn("coordinates", " ".join(self.air["limitations"]).casefold())
        self.assertIn("not facility stack testing", " ".join(self.air["limitations"]).casefold())

    def test_dic_crosswalk_records_only_published_historical_fields(self):
        rows = read_rows(ROOT / "data/processed/industrial/edayar_dic_allotment_crosswalk_2022.csv")
        self.assertEqual({row["facility_id"] for row in rows}, {"EDAYAR-002", "EDAYAR-004"})
        by_id = {row["facility_id"]: row for row in rows}
        self.assertEqual(by_id["EDAYAR-002"]["plot_number_as_published"], "")
        self.assertEqual(by_id["EDAYAR-002"]["facility_name_as_published"], "SUD CHEMIE INDIA PVT LTD")
        self.assertEqual(by_id["EDAYAR-004"]["plot_number_as_published"], "28")
        self.assertEqual(by_id["EDAYAR-004"]["facility_name_as_published"], "TMS LEATHERS")
        inventory = {
            row["facility_id"]: row["facility_name_as_published"]
            for row in read_rows(ROOT / "data/processed/industrial/edayar_candidate_facilities.csv")
        }
        self.assertIn("Sud", inventory["EDAYAR-002"])
        self.assertIn("TMS", inventory["EDAYAR-004"])
        self.assertEqual({row["status_reference_date"] for row in rows}, {"2022-02-15"})
        self.assertTrue(all("not" in row["interpretation_limit"].casefold() for row in rows))
        self.assertNotIn("latitude", rows[0])
        self.assertNotIn("measured_emissions", rows[0])


if __name__ == "__main__":
    unittest.main()

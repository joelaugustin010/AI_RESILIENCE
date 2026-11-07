"""Cross-platform checkout integrity for registered CRLF CSV sources."""

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
PROVENANCE_PATH = ROOT / "data" / "reference" / "DATA_PROVENANCE_REGISTER.json"
HASHED_CSV_PATHS = (
    "data/processed/nihfw_ernakulam_hospitals_coordinate_review.csv",
    "data/processed/air_quality/kspcb_annual_aqi.csv",
    "data/processed/air_quality/kspcb_caaqms_eloor_aqi_2026-08.csv",
    "data/processed/air_quality/kspcb_caaqms_eloor_aqi_2026-09.csv",
    "data/processed/air_quality/kspcb_caaqms_eloor_daily_2026-08.csv",
    "data/processed/air_quality/kspcb_caaqms_eloor_daily_2026-09.csv",
    "data/processed/air_quality/kspcb_caaqms_eloor_weather_2026-08.csv",
    "data/processed/air_quality/kspcb_caaqms_eloor_weather_2026-09.csv",
    "data/processed/air_quality/kspcb_daily_aqi_2026-10-16.csv",
    "data/processed/air_quality/kspcb_daily_aqi_status_2026-10-16.csv",
    "data/processed/air_quality/kspcb_namp_ernakulam_2025-06.csv",
    "data/processed/industrial/edayar_dic_allotment_crosswalk_2022.csv",
)


class ProvenanceLineEndingTests(unittest.TestCase):
    def test_registered_csv_hashes_survive_a_linux_checkout(self):
        register = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
        expected = {
            item.get("path"): item.get("sha256")
            for item in register["assets"]
            if item.get("path") and item.get("sha256")
        }

        for relative_path in HASHED_CSV_PATHS:
            with self.subTest(path=relative_path):
                self.assertIn(relative_path, expected)
                                # Canonicalize the registered source CSVs to CRLF before hashing.
                # Git stores normalized text blobs, so checkout settings must not
                # change the byte representation used by this provenance register.
                raw = (ROOT / relative_path).read_bytes()
                canonical = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n").replace(b"\n", b"\r\n")
                actual = hashlib.sha256(canonical).hexdigest()
                self.assertEqual(actual, expected[relative_path])


if __name__ == "__main__":
    unittest.main()

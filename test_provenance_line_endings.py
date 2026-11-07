"""Cross-platform checkout integrity for registered CSV source files."""

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
                raw = (ROOT / relative_path).read_bytes()
                # Git may materialize either LF or CRLF depending on checkout
                # configuration. Compare both byte representations against the
                # recorded source digest; do not silently rewrite the register.
                lf = raw.replace(b"\\r\\n", b"\\n").replace(b"\\r", b"\\n")
                crlf = lf.replace(b"\\n", b"\\r\\n")
                candidates = {
                    hashlib.sha256(raw).hexdigest(),
                    hashlib.sha256(lf).hexdigest(),
                    hashlib.sha256(crlf).hexdigest(),
                }
                self.assertIn(
                    expected[relative_path],
                    candidates,
                    f"{relative_path}: registered SHA-256 {expected[relative_path]} "
                    f"did not match raw/LF/CRLF checkout bytes",
                )


if __name__ == "__main__":
    unittest.main()

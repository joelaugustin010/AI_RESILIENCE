
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.data_validation import validate_csv


class TestDataValidation(unittest.TestCase):

    def test_valid_rainfall_csv(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rainfall.csv"

            pd.DataFrame({
                "date": ["2025-06-01"],
                "location": ["Kochi"],
                "rainfall_mm": [42.5],
            }).to_csv(path, index=False)

            valid, messages = validate_csv(path, "rainfall")
            self.assertTrue(valid, messages)

    def test_negative_rainfall_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rainfall.csv"

            pd.DataFrame({
                "date": ["2025-06-01"],
                "location": ["Kochi"],
                "rainfall_mm": [-5],
            }).to_csv(path, index=False)

            valid, messages = validate_csv(path, "rainfall")
            self.assertFalse(valid)
            self.assertTrue(any("negative" in m for m in messages))

    def test_missing_column_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rainfall.csv"

            pd.DataFrame({
                "date": ["2025-06-01"],
                "rainfall_mm": [42.5],
            }).to_csv(path, index=False)

            valid, messages = validate_csv(path, "rainfall")
            self.assertFalse(valid)
            self.assertTrue(any("location" in m for m in messages))


if __name__ == "__main__":
    unittest.main()

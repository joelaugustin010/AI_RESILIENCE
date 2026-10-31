import unittest

import pandas as pd
import pyarrow as pa

from src.dataframe_display import normalize_mixed_columns_for_display
from src.hazard_manifest import build_hazard_manifest_frame


class MixedColumnDisplayTests(unittest.TestCase):
    def test_integer_and_empty_string_rows_serialize_as_nullable_integers(self):
        source = pd.DataFrame({"Rows": [7, ""]})

        with self.assertRaises(pa.ArrowInvalid):
            pa.Table.from_pandas(source)

        display = normalize_mixed_columns_for_display(source)
        table = pa.Table.from_pandas(display)

        self.assertEqual(str(display["Rows"].dtype), "Int64")
        self.assertEqual(table.column("Rows").to_pylist(), [7, None])
        self.assertEqual(source["Rows"].tolist(), [7, ""])

    def test_valid_integers_and_missing_values_remain_integer_and_null(self):
        source = pd.DataFrame({"Rows": pd.Series([4, None], dtype=object)})

        display = normalize_mixed_columns_for_display(source)
        table = pa.Table.from_pandas(display)

        self.assertEqual(str(display["Rows"].dtype), "Int64")
        self.assertEqual(table.column("Rows").to_pylist(), [4, None])

    def test_nan_is_preserved_as_a_nullable_missing_value(self):
        source = pd.DataFrame({"Rows": pd.Series([4, float("nan")], dtype=object)})

        display = normalize_mixed_columns_for_display(source)
        table = pa.Table.from_pandas(display)

        self.assertEqual(str(display["Rows"].dtype), "Int64")
        self.assertEqual(table.column("Rows").to_pylist(), [4, None])

    def test_whitespace_only_blank_is_a_missing_numeric_value(self):
        source = pd.DataFrame({"Rows": [4, "  "]})

        display = normalize_mixed_columns_for_display(source)
        table = pa.Table.from_pandas(display)

        self.assertEqual(table.column("Rows").to_pylist(), [4, None])

    def test_fractional_numeric_values_keep_numeric_type_and_blank_as_missing(self):
        source = pd.DataFrame({"Rows": [1.5, 2, ""]})

        display = normalize_mixed_columns_for_display(source)
        table = pa.Table.from_pandas(display)

        self.assertEqual(str(display["Rows"].dtype), "Float64")
        self.assertEqual(table.column("Rows").to_pylist(), [1.5, 2.0, None])

    def test_other_mixed_values_are_displayed_as_strings_without_losing_missingness(self):
        source = pd.DataFrame({"Rows": [3, "not reported", ""]})

        display = normalize_mixed_columns_for_display(source)
        table = pa.Table.from_pandas(display)

        self.assertEqual(str(display["Rows"].dtype), "string")
        self.assertEqual(table.column("Rows").to_pylist(), ["3", "not reported", None])
        self.assertEqual(source["Rows"].tolist(), [3, "not reported", ""])

    def test_text_labels_and_empty_text_are_not_retyped(self):
        source = pd.DataFrame({"Ward_Name": ["Ward 1", ""]})

        display = normalize_mixed_columns_for_display(source)
        table = pa.Table.from_pandas(display)

        self.assertEqual(display["Ward_Name"].tolist(), ["Ward 1", ""])
        self.assertEqual(table.column("Ward_Name").to_pylist(), ["Ward 1", ""])

    def test_hazard_manifest_frame_serializes_integer_rows_and_missing_rows(self):
        entries = [
            {
                "file": "observations.csv",
                "status": "downloaded",
                "data_rows": 47,
                "bytes": 1024,
            },
            {
                "file": "skipped.csv",
                "status": "skipped",
                "data_rows": None,
                "bytes": None,
            },
        ]

        frame = build_hazard_manifest_frame(entries)
        table = pa.Table.from_pandas(frame)

        self.assertEqual(table.column("Rows").to_pylist(), [47, None])
        self.assertEqual(table.column("Bytes").to_pylist(), [1024, None])
        self.assertEqual(entries[1]["data_rows"], None)


if __name__ == "__main__":
    unittest.main()

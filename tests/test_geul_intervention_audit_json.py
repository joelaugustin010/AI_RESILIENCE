""""Regression tests for strict-JSON and feature-grouping diagnostics."""
import json
import math

import pytest

pytest.importorskip("geopandas")
pytest.importorskip("numpy")
pytest.importorskip("openpyxl")
pytest.importorskip("rasterio")
pytest.importorskip("pandas")

from scripts.audit_geul_intervention_results import (
    _group_damage_diagnostics,
    _json_safe,
)


def test_json_safe_converts_nan_nodata_to_null():
    payload = {"water_depth_raster": {"nodata": float("nan")}}
    safe = _json_safe(payload)
    assert safe["water_depth_raster"]["nodata"] is None
    assert json.loads(json.dumps(safe, allow_nan=False)) == safe


def test_json_safe_preserves_finite_values_and_nested_numpy_scalars():
    import numpy as np

    payload = {"stats": [np.float64(1.25), np.int64(3), np.bool_(True), float("inf")]}
    safe = _json_safe(payload)
    assert safe == {"stats": [1.25, 3, True, None]}
    assert math.isfinite(safe["stats"][0])
    json.dumps(safe, allow_nan=False)


def test_group_damage_diagnostics_reports_duplicate_keys_without_validating_aggregation():
    import pandas as pd

    result = _group_damage_diagnostics(
        pd.Series(["building-a", "building-a", "building-b", None]),
        pd.Series([10.0, 4.0, 7.0, 99.0]),
    )

    assert result["groups"] == 2
    assert result["rows_with_key"] == 3
    assert result["duplicate_groups"] == 1
    assert result["rows_in_duplicate_groups"] == 2
    assert result["maximum_rows_per_group"] == 2
    assert result["raw_damage_sum"] == 21.0
    assert result["sum_of_group_max_damage"] == 17.0
    # Mean per group: (10 + 4) / 2 + 7 = 14.
    assert result["sum_of_group_mean_damage"] == 14.0
    assert result["aggregation_is_validated"] is False


def test_group_damage_diagnostics_handles_no_identifiers():
    import pandas as pd

    result = _group_damage_diagnostics(
        pd.Series([None, None]), pd.Series([1.0, 2.0])
    )

    assert result["groups"] == 0
    assert result["rows_with_key"] == 0
    assert result["aggregation_is_validated"] is False


def test_group_damage_diagnostics_counts_rows_even_when_damage_is_missing():
    import pandas as pd

    result = _group_damage_diagnostics(
        pd.Series(["building-a", "building-a", "building-b"]),
        pd.Series([10.0, None, 7.0]),
    )

    assert result["rows_with_key"] == 3
    assert result["rows_with_non_null_damage_and_key"] == 2
    assert result["duplicate_groups"] == 1
    assert result["rows_in_duplicate_groups"] == 2

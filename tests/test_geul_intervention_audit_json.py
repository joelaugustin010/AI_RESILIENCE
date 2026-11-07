"""Regression tests for strict-JSON serialization in the Geul audit utility."""
import json
import math

import pytest

pytest.importorskip("geopandas")
pytest.importorskip("numpy")
pytest.importorskip("openpyxl")
pytest.importorskip("rasterio")

from scripts.audit_geul_intervention_results import _json_safe


def test_json_safe_converts_nan_nodata_to_null():
    payload = {"water_depth_raster": {"nodata": float("nan")}}

    safe = _json_safe(payload)

    assert safe["water_depth_raster"]["nodata"] is None
    assert json.loads(json.dumps(safe, allow_nan=False)) == safe


def test_json_safe_preserves_finite_values_and_nested_numpy_scalars():
    import numpy as np

    payload = {
        "stats": [np.float64(1.25), np.int64(3), np.bool_(True), float("inf")],
    }

    safe = _json_safe(payload)

    assert safe == {"stats": [1.25, 3, True, None]}
    assert math.isfinite(safe["stats"][0])
    json.dumps(safe, allow_nan=False)

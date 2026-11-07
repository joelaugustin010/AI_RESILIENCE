""""Audit paired Geul SFINCS intervention outputs without extracting the full archive.

This is a data-quality and descriptive-comparison utility, not a causal model
or training pipeline. It reads one matched model/event/RP100 slice, diagnoses
GeoPackage identifiers and damage fields, compares full-resolution raster
depth distributions, and records workbook EAD values. No model is trained.
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import geopandas as gpd
import numpy as np
import openpyxl
import rasterio


SCENARIOS = {
    "baseline": "baseline_blokbui",
    "retention_ponds": "waterbuffers_blokbui",
    "reforestation": "reforestation_blokbui",
    "grassland_conversion": "grassland_conversion_blokbui",
    "dryproofing": "dry_proofing_blokbui",
    "wetproofing": "wet_proofing_blokbui",
}
MODEL_ID = "23250850"
EVENT_ID = "20210716T000000"
RETURN_PERIOD = "RP100"
DEPTH_THRESHOLDS_M = (0.01, 0.05, 0.10, 0.20, 0.50, 1.0)


def _member(names: list[str], prefix: str, contains: str) -> str:
    matches = [
        name for name in names
        if name.startswith(prefix) and contains.lower() in name.lower()
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one archive member containing {contains!r} "
            f"under {prefix!r}; found {len(matches)}: {matches[:8]}"
        )
    return matches[0]


def _json_safe(value: Any) -> Any:
    """Convert NumPy values and non-finite floats to strict-JSON-safe values.

    NaN is a legitimate nodata marker in some GeoTIFFs, but JSON has no NaN
    literal. Preserve the field while representing non-finite numbers as null.
    """
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (float, np.floating)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def _finite_stats(values: np.ndarray) -> dict[str, float | int | None]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if not values.size:
        return {"count": 0, "minimum": None, "maximum": None, "mean": None}
    return {
        "count": int(values.size),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "mean": float(values.mean()),
    }


def _gpkg_diagnostics(path: Path) -> dict[str, Any]:
    frame = gpd.read_file(path)
    result: dict[str, Any] = {
        "feature_count": int(len(frame)),
        "crs": str(frame.crs),
        "geometry_types": {
            str(k): int(v) for k, v in frame.geometry.geom_type.value_counts(dropna=False).items()
        },
        "null_counts": {
            str(k): int(v) for k, v in frame.isna().sum().items()
        },
        "columns": [str(c) for c in frame.columns if c != "geometry"],
    }
    for column in ("osm_id", "osm_way_id", "object_type"):
        if column in frame:
            values = frame[column]
            result[f"{column}_unique_non_null"] = int(values.nunique(dropna=True))
            result[f"{column}_null_rows"] = int(values.isna().sum())
            result[f"{column}_duplicate_non_null_rows"] = int(
                values.notna().sum() - values.nunique(dropna=True)
            )
            result[f"{column}_top_values"] = [
                {"value": str(k), "rows": int(v)}
                for k, v in values.value_counts(dropna=True).head(10).items()
            ]
    for column in ("damages", "maximum_damage"):
        if column in frame:
            numeric = __import__("pandas").to_numeric(frame[column], errors="coerce")
            result[column] = {
                **_finite_stats(numeric.to_numpy(dtype=float)),
                "positive_rows": int((numeric > 0).sum()),
                "zero_rows": int((numeric == 0).sum()),
                "negative_rows": int((numeric < 0).sum()),
                "missing_or_non_numeric_rows": int(numeric.isna().sum()),
                "sum": float(numeric.sum(skipna=True)),
            }
    if "object_type" in frame and "damages" in frame:
        numeric = __import__("pandas").to_numeric(frame["damages"], errors="coerce")
        grouped = frame.assign(_damage=numeric).groupby(
            "object_type", dropna=False
        )["_damage"].agg(["count", "sum", "max"])
        result["damage_by_object_type"] = [
            {
                "object_type": str(index),
                "rows": int(row["count"]),
                "sum": float(row["sum"]),
                "max": float(row["max"]),
            }
            for index, row in grouped.iterrows()
        ]
    if "osm_id" in frame and "damages" in frame:
        numeric = __import__("pandas").to_numeric(frame["damages"], errors="coerce")
        grouped = frame.assign(_damage=numeric).dropna(subset=["osm_id"]).groupby(
            "osm_id"
        )["_damage"].agg(["count", "sum", "max"])
        result["osm_grouping_diagnostic"] = {
            "groups": int(len(grouped)),
            "rows_in_groups": int(grouped["count"].sum()),
            "sum_of_row_damage": float(grouped["sum"].sum()),
            "sum_of_group_max_damage": float(grouped["max"].sum()),
            "groups_with_multiple_rows": int((grouped["count"] > 1).sum()),
        }
    return result


def _raster_diagnostics(path: Path, baseline_path: Path | None = None) -> dict[str, Any]:
    thresholds = {f"pixels_gt_{t:g}m": 0 for t in DEPTH_THRESHOLDS_M}
    count = 0
    total = 0.0
    min_value = math.inf
    max_value = -math.inf
    histogram_edges = np.asarray(
        [0, .01, .05, .1, .2, .5, 1, 2, 3, 5, 10, 20, 100], dtype=float
    )
    histogram = np.zeros(len(histogram_edges) - 1, dtype=np.int64)
    comparison = None
    with rasterio.open(path) as ds:
        metadata = {
            "width": int(ds.width),
            "height": int(ds.height),
            "crs": str(ds.crs),
            "transform": tuple(float(v) for v in ds.transform),
            "resolution": tuple(float(v) for v in ds.res),
            "nodata": None if ds.nodata is None else float(ds.nodata),
        }
        base = rasterio.open(baseline_path) if baseline_path else None
        if base:
            same_grid = (
                ds.width == base.width and ds.height == base.height
                and ds.crs == base.crs and ds.transform == base.transform
            )
            comparison = {
                "same_grid": bool(same_grid),
                "compared_pixels": 0,
                "exactly_equal_pixels": 0,
                "absolute_difference_sum": 0.0,
                "absolute_difference_max": 0.0,
                "baseline_valid_pixels": 0,
                "candidate_valid_pixels": 0,
                "joint_valid_pixels": 0,
            }
        try:
            for _, window in ds.block_windows(1):
                values = ds.read(1, window=window, masked=True)
                valid = np.asarray(values.compressed(), dtype=float)
                if valid.size:
                    count += int(valid.size)
                    total += float(valid.sum())
                    min_value = min(min_value, float(valid.min()))
                    max_value = max(max_value, float(valid.max()))
                    for threshold in DEPTH_THRESHOLDS_M:
                        thresholds[f"pixels_gt_{threshold:g}m"] += int(
                            (valid > threshold).sum()
                        )
                    histogram += np.histogram(valid, bins=histogram_edges)[0]
                if base and comparison["same_grid"]:
                    other = base.read(1, window=window, masked=True)
                    left = np.asarray(values.filled(np.nan), dtype=float)
                    right = np.asarray(other.filled(np.nan), dtype=float)
                    joint = np.isfinite(left) & np.isfinite(right)
                    if joint.any():
                        diff = np.abs(left[joint] - right[joint])
                        comparison["compared_pixels"] += int(joint.sum())
                        comparison["exactly_equal_pixels"] += int(
                            np.count_nonzero(diff == 0)
                        )
                        comparison["absolute_difference_sum"] += float(diff.sum())
                        comparison["absolute_difference_max"] = max(
                            comparison["absolute_difference_max"], float(diff.max())
                        )
                    comparison["baseline_valid_pixels"] += int(
                        np.isfinite(right).sum()
                    )
                    comparison["candidate_valid_pixels"] += int(
                        np.isfinite(left).sum()
                    )
                    comparison["joint_valid_pixels"] += int(joint.sum())
        finally:
            if base:
                base.close()
    result = {
        **metadata,
        "valid_pixels": count,
        "valid_cell_area_m2": float(count * abs(metadata["resolution"][0] * metadata["resolution"][1])),
        "minimum_depth_m": None if not count else min_value,
        "maximum_depth_m": None if not count else max_value,
        "mean_depth_m": None if not count else total / count,
        **thresholds,
        "depth_histogram_bins_m": [
            [float(histogram_edges[i]), float(histogram_edges[i + 1]), int(histogram[i])]
            for i in range(len(histogram))
        ],
    }
    if comparison is not None:
        n = comparison["joint_valid_pixels"]
        comparison["mean_absolute_difference_m"] = (
            comparison["absolute_difference_sum"] / n if n else None
        )
        result["baseline_comparison"] = comparison
    return result


def _workbook_overview(zf: zipfile.ZipFile, names: list[str]) -> dict[str, Any]:
    workbook_member = _member(names, "final_results/", "results_scaled_and_blokbui.xlsx")
    wb = openpyxl.load_workbook(
        __import__("io").BytesIO(zf.read(workbook_member)),
        read_only=True, data_only=True,
    )
    try:
        ws = wb["overview"]
        rows = list(ws.iter_rows(values_only=True))
    finally:
        wb.close()

    columns = {
        "baseline": 2, "retention_ponds": 3, "reforestation": 4,
        "grassland_conversion": 5, "dryproofing": 6, "wetproofing": 7,
    }
    sections: dict[str, Any] = {}
    section = None
    for row in rows:
        label = str(row[0]).strip().lower() if row and row[0] is not None else ""
        if label in {"scaled 2021", "blokbui"}:
            section = label
            sections[section] = {"return_period_damage": {}, "ead": {}, "benefits": {}}
            continue
        if not section:
            continue
        if label == "rp" and len(row) > 1:
            continue
        if label == "ead":
            sections[section]["ead"] = {
                key: row[index] for key, index in columns.items()
            }
        elif label == "benefits":
            sections[section]["benefits"] = {
                key: row[index] for key, index in columns.items()
            }
        elif isinstance(row[1], (int, float)) and row[0] is None:
            rp = str(int(row[1])) if float(row[1]).is_integer() else str(row[1])
            sections[section]["return_period_damage"][rp] = {
                key: row[index] for key, index in columns.items()
            }
    for section_data in sections.values():
        baseline = section_data["ead"].get("baseline")
        section_data["ead_reduction_vs_baseline"] = {}
        if isinstance(baseline, (int, float)) and baseline:
            for key, value in section_data["ead"].items():
                if key != "baseline" and isinstance(value, (int, float)):
                    section_data["ead_reduction_vs_baseline"][key] = {
                        "absolute": float(baseline - value),
                        "percent": float(100 * (baseline - value) / baseline),
                    }
    return {"member": workbook_member, "sections": sections}


def audit_archive(archive: Path, output: Path) -> dict[str, Any]:
    if not archive.is_file():
        raise FileNotFoundError(archive)
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        report: dict[str, Any] = {
            "schema_version": "geul-intervention-audit/1.0.0",
            "archive": archive.name,
            "matched_slice": {
                "model_id": MODEL_ID,
                "event_id": EVENT_ID,
                "return_period": RETURN_PERIOD,
                "rainfall_forcing": "blokbui",
            },
            "workbook": _workbook_overview(zf, names),
            "scenario_outputs": {},
            "interpretation_limits": [
                "Workbook EAD is a published model-derived summary, not observed intervention outcomes.",
                "A valid raster cell is not automatically a flooded cell; depth thresholds must be evaluated separately.",
                "Building GeoPackage row sums may double-count fragmented or repeated OSM features; inspect identifier and geometry structure before aggregation.",
                "Building-level proofing can change damage without changing the hydrodynamic water-depth raster.",
                "This single matched event/model/RP slice is descriptive and is not an independent validation split.",
                "Geul catchment simulation results are not directly transferable to Kochi.",
            ],
        }
        with tempfile.TemporaryDirectory(prefix="geul_audit_") as tmp:
            tmp_path = Path(tmp)
            baseline_raster = None
            for label, folder in SCENARIOS.items():
                prefix = f"final_results/{folder}/SFINCS/{MODEL_ID}/"
                gpkg_member = _member(
                    names, prefix + "damage/", "building structure_RP100.gpkg"
                )
                tif_member = _member(
                    names, prefix + f"simulations/{EVENT_ID}/", "hmax RP 100.tif"
                )
                gpkg_path = tmp_path / f"{label}.gpkg"
                tif_path = tmp_path / f"{label}.tif"
                gpkg_path.write_bytes(zf.read(gpkg_member))
                tif_path.write_bytes(zf.read(tif_member))
                if label == "baseline":
                    baseline_raster = tif_path
                report["scenario_outputs"][label] = {
                    "geopackage_member": gpkg_member,
                    "raster_member": tif_member,
                    "building_layer": _gpkg_diagnostics(gpkg_path),
                    "water_depth_raster": _raster_diagnostics(
                        tif_path,
                        None if label == "baseline" else baseline_raster,
                    ),
                }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(_json_safe(report), indent=2, allow_nan=False), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        default="data/external/geul_intervention/final_results.zip",
    )
    parser.add_argument(
        "--output",
        default="reports/geul_intervention_quality_audit.json",
    )
    args = parser.parse_args()
    report = audit_archive(Path(args.archive), Path(args.output))
    print(json.dumps({
        "report": args.output,
        "scenarios_audited": len(report["scenario_outputs"]),
        "workbook_sections": list(report["workbook"]["sections"]),
        "training_performed": False,
        "interpretation": "DESCRIPTIVE_SIMULATION_AUDIT_ONLY",
    }, indent=2))
    for scenario, item in report["scenario_outputs"].items():
        damage = item["building_layer"].get("damages", {})
        raster = item["water_depth_raster"]
        print(
            f"{scenario}: building_damage_row_sum={damage.get('sum')}; "
            f"unique_osm_id={item['building_layer'].get('osm_id_unique_non_null')}; "
            f"valid_pixels={raster['valid_pixels']}; "
            f"pixels_gt_0.1m={raster['pixels_gt_0.1m']}; "
            f"max_depth_m={raster['maximum_depth_m']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

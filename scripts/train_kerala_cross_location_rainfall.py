"""Train a Kerala cross-location next-day rainfall transfer model.

The Kochi record is excluded from every fitting and model-selection step.
Only observations from Kottayam, Wayanad and Thiruvananthapuram are used for
training/validation. The final evaluation is on Kochi target dates from 2020
onwards. This is a research transfer experiment, not a flood prediction.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.data import WEATHER_FILES, build_weather_target_dataset
from src.ml.estimators import REGRESSION_CANDIDATES, build_regressor

HELD_OUT_LOCATION = "kochi"
TRAIN_LOCATIONS = tuple(name for name in WEATHER_FILES if name != HELD_OUT_LOCATION)
VALIDATION_START = pd.Timestamp("2015-01-01")
TEST_START = pd.Timestamp("2020-01-01")
TARGET = "target_rain_nextday"
DATE = "target_date"
BASELINE = "precipitation_sum"


def _metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float | int]:
    return {
        "mae_mm": float(mean_absolute_error(actual, predicted)),
        "rmse_mm": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)) if len(actual) > 1 else 0.0,
        "n": int(len(actual)),
    }


def _wet_day_metrics(
    actual: np.ndarray, predicted: np.ndarray, threshold_mm: float = 1.0
) -> dict[str, float | int]:
    """Evaluate wet-day occurrence at an explicit 1 mm/day threshold.

    These are thresholded point-regression diagnostics, not calibrated
    probabilities and not a public warning classifier.
    """
    if len(actual) != len(predicted) or len(actual) == 0:
        raise ValueError("Wet-day metrics require paired non-empty arrays.")
    actual_wet = np.asarray(actual, dtype=float) >= threshold_mm
    predicted_wet = np.asarray(predicted, dtype=float) >= threshold_mm
    return {
        "threshold_mm": float(threshold_mm),
        "actual_wet_days": int(actual_wet.sum()),
        "predicted_wet_days": int(predicted_wet.sum()),
        "precision": float(precision_score(actual_wet, predicted_wet, zero_division=0)),
        "recall": float(recall_score(actual_wet, predicted_wet, zero_division=0)),
        "f1": float(f1_score(actual_wet, predicted_wet, zero_division=0)),
        "n": int(len(actual_wet)),
    }


def _seasonal_metrics(
    actual: np.ndarray, predicted: np.ndarray, dates: pd.Series
) -> dict[str, dict[str, float | int]]:
    """Report holdout regression skill separately for monsoon and other months."""
    month = pd.to_datetime(dates).dt.month
    masks = {
        "southwest_monsoon_jun_sep": month.between(6, 9).to_numpy(),
        "other_months": (~month.between(6, 9)).to_numpy(),
    }
    result: dict[str, dict[str, float | int]] = {}
    for name, mask in masks.items():
        if not mask.any():
            result[name] = {"n": 0}
            continue
        metrics = _metrics(actual[mask], predicted[mask])
        metrics["mean_bias_mm"] = float(np.mean(actual[mask] - predicted[mask]))
        result[name] = metrics
    return result


def _load_location(location: str) -> tuple[pd.DataFrame, list[str], str]:
    dataset = build_weather_target_dataset(
        location, lead_days=1, target="extreme_rainfall"
    )
    columns = list(dataset.feature_columns)
    forbidden = {
        TARGET, "target_tmax_nextday", "target_rain30_future", DATE,
        "date", "location",
    }
    columns = [name for name in columns if name not in forbidden]
    if not columns or any(name.startswith("target_") for name in columns):
        raise ValueError("Feature contract is empty or contains a target column.")
    selected_columns = list(dict.fromkeys([DATE, TARGET, BASELINE, *columns]))
    frame = dataset.frame[selected_columns].copy()
    frame["location"] = location
    frame[DATE] = pd.to_datetime(frame[DATE], errors="coerce")
    frame[TARGET] = pd.to_numeric(frame[TARGET], errors="coerce")
    frame = frame.dropna(subset=[DATE, TARGET]).sort_values(DATE).reset_index(drop=True)
    return frame, columns, str(dataset.provenance.get("source_type", "unknown"))


def _paired_block_ci(
    actual: np.ndarray,
    model: np.ndarray,
    baseline: np.ndarray,
    *,
    block: int = 7,
    draws: int = 1000,
    seed: int = 42,
) -> list[float]:
    """95% circular moving-block CI for baseline MAE minus model MAE."""
    delta = np.abs(actual - baseline) - np.abs(actual - model)
    if len(delta) < 2:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    width = min(block, len(delta))
    count = int(np.ceil(len(delta) / width))
    estimates = np.empty(draws, dtype=float)
    offsets = np.arange(width)
    for i in range(draws):
        starts = rng.integers(0, len(delta), size=count)
        idx = ((starts[:, None] + offsets) % len(delta)).ravel()[:len(delta)]
        estimates[i] = float(delta[idx].mean())
    low, high = np.quantile(estimates, [0.025, 0.975])
    return [float(low), float(high)]


def _regression_calibration_bins(
    actual: np.ndarray, predicted: np.ndarray, bins: int = 10
) -> list[dict[str, float | int]]:
    """Return equal-count prediction-reliability bins for a point regressor."""
    if bins < 2 or len(actual) != len(predicted) or len(actual) == 0:
        raise ValueError("Calibration bins require paired non-empty arrays and at least two bins.")
    order = np.argsort(predicted, kind="mergesort")
    groups = np.array_split(order, min(bins, len(order)))
    result = []
    for index, rows in enumerate(groups, start=1):
        if len(rows) == 0:
            continue
        mean_prediction = float(np.mean(predicted[rows]))
        mean_observed = float(np.mean(actual[rows]))
        result.append({
            "bin": index,
            "n": int(len(rows)),
            "mean_prediction_mm": mean_prediction,
            "mean_observed_mm": mean_observed,
            "bias_observed_minus_predicted_mm": mean_observed - mean_prediction,
        })
    return result


def _monthly_climatology(
    training_dates: pd.Series, training_targets: pd.Series, test_dates: pd.Series
) -> np.ndarray:
    """Predict each test date with the training-only median for its calendar month."""
    training_months = pd.to_datetime(training_dates).dt.month
    test_months = pd.to_datetime(test_dates).dt.month
    seasonal = pd.Series(training_targets.to_numpy(dtype=float)).groupby(training_months.to_numpy()).median()
    return test_months.map(seasonal).to_numpy(dtype=float)


def train(output_dir: Path) -> dict[str, Any]:
    if HELD_OUT_LOCATION in TRAIN_LOCATIONS:
        raise AssertionError("Kochi must never enter the training location list.")
    frames: list[pd.DataFrame] = []
    feature_sets: list[set[str]] = []
    source_types: dict[str, str] = {}
    for location in (*TRAIN_LOCATIONS, HELD_OUT_LOCATION):
        frame, features, source_type = _load_location(location)
        frames.append(frame)
        feature_sets.append(set(features))
        source_types[location] = source_type
    common_features = sorted(set.intersection(*feature_sets))
    if not common_features:
        raise ValueError("No common numeric features across the four weather records.")

    non_kochi = pd.concat(
        [frame for frame in frames if frame["location"].iloc[0] != HELD_OUT_LOCATION],
        ignore_index=True,
    )
    kochi = next(frame for frame in frames if frame["location"].iloc[0] == HELD_OUT_LOCATION)
    # The validation period is used only for candidate selection. Kochi is
    # excluded from both train and validation; its 2020+ period is untouched.
    fit_rows = non_kochi[non_kochi[DATE] < VALIDATION_START].copy()
    validation = non_kochi[
        (non_kochi[DATE] >= VALIDATION_START) & (non_kochi[DATE] < TEST_START)
    ].copy()
    final_fit = non_kochi[non_kochi[DATE] < TEST_START].copy()
    test = kochi[kochi[DATE] >= TEST_START].copy()
    if min(len(fit_rows), len(validation), len(final_fit), len(test)) < 100:
        raise ValueError(
            "Insufficient rows for the declared temporal/spatial split: "
            f"fit={len(fit_rows)}, validation={len(validation)}, "
            f"final_fit={len(final_fit)}, Kochi_test={len(test)}"
        )

    X_fit = fit_rows[common_features]
    y_fit = fit_rows[TARGET].to_numpy(dtype=float)
    X_val = validation[common_features]
    y_val = validation[TARGET].to_numpy(dtype=float)
    candidates: list[dict[str, Any]] = []
    for name in REGRESSION_CANDIDATES:
        estimator = build_regressor(name)
        estimator.fit(X_fit, y_fit)
        prediction = np.maximum(0.0, np.asarray(estimator.predict(X_val), dtype=float))
        candidates.append({"model_type": name, **_metrics(y_val, prediction)})
    selected = min(candidates, key=lambda row: (row["mae_mm"], row["rmse_mm"]))

    final_model = build_regressor(str(selected["model_type"]))
    final_model.fit(final_fit[common_features], final_fit[TARGET].to_numpy(dtype=float))
    actual = test[TARGET].to_numpy(dtype=float)
    predicted = np.maximum(0.0, np.asarray(final_model.predict(test[common_features]), dtype=float))
    baseline_values = pd.to_numeric(test[BASELINE], errors="coerce").to_numpy(dtype=float)
    climatology_values = _monthly_climatology(final_fit[DATE], final_fit[TARGET], test[DATE])
    valid_baseline = np.isfinite(baseline_values)
    valid_climatology = np.isfinite(climatology_values)
    if not np.isfinite(predicted).all() or not np.isfinite(actual).all():
        raise ValueError("Non-finite model predictions or test targets.")
    model_metrics = _metrics(actual, predicted)
    if int(valid_baseline.sum()) < 2:
        raise ValueError("Too few Kochi test rows for a persistence comparison.")
    if int(valid_climatology.sum()) < 2:
        raise ValueError("Too few Kochi test rows for a seasonal-climatology comparison.")

    baseline_metrics = _metrics(actual[valid_baseline], baseline_values[valid_baseline])
    persistence_model_metrics = _metrics(actual[valid_baseline], predicted[valid_baseline])
    persistence_ci = _paired_block_ci(
        actual[valid_baseline], predicted[valid_baseline], baseline_values[valid_baseline]
    )
    climatology_metrics = _metrics(actual[valid_climatology], climatology_values[valid_climatology])
    climatology_model_metrics = _metrics(actual[valid_climatology], predicted[valid_climatology])
    climatology_ci = _paired_block_ci(
        actual[valid_climatology], predicted[valid_climatology], climatology_values[valid_climatology]
    )
    persistence_skill = 1.0 - persistence_model_metrics["mae_mm"] / max(baseline_metrics["mae_mm"], 1e-12)
    climatology_skill = 1.0 - climatology_model_metrics["mae_mm"] / max(climatology_metrics["mae_mm"], 1e-12)
    baseline_gate_passed = bool(persistence_ci[0] > 0 and climatology_ci[0] > 0)

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_model, output_dir / "model.joblib")
    report: dict[str, Any] = {
        "schema_version": 1,
        "model_id": "kerala_cross_location_rainfall_nextday",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "task": "next-day precipitation regression",
        "target": TARGET,
        "unit": "mm/day",
        "training_locations": list(TRAIN_LOCATIONS),
        "validation_locations": list(TRAIN_LOCATIONS),
        "held_out_test_location": HELD_OUT_LOCATION,
        "temporal_split": {
            "candidate_fit_target_dates_before": VALIDATION_START.date().isoformat(),
            "validation_target_dates": (
                f"{VALIDATION_START.date().isoformat()} through before "
                f"{TEST_START.date().isoformat()}"
            ),
            "final_fit_target_dates_before": TEST_START.date().isoformat(),
            "held_out_test_target_dates_from": TEST_START.date().isoformat(),
        },
        "feature_columns": common_features,
        "feature_count": len(common_features),
        "selected_model_type": selected["model_type"],
        "candidate_validation_metrics": candidates,
        "held_out_kochi_metrics": model_metrics,
        "regression_calibration_bins": _regression_calibration_bins(actual, predicted),
        "wet_day_occurrence_metrics": _wet_day_metrics(actual, predicted, threshold_mm=1.0),
        "seasonal_holdout_metrics": _seasonal_metrics(actual, predicted, test[DATE]),
        "mean_prediction_bias_mm": float(np.mean(actual - predicted)),
        "paired_model_metrics_vs_persistence": persistence_model_metrics,
        "persistence_baseline_metrics": baseline_metrics,
        "paired_model_metrics_vs_climatology": climatology_model_metrics,
        "seasonal_climatology_baseline_metrics": climatology_metrics,
        "mae_skill_over_persistence": float(persistence_skill),
        "mae_skill_over_seasonal_climatology": float(climatology_skill),
        "paired_mae_improvement_vs_persistence_95ci_mm": persistence_ci,
        "paired_mae_improvement_vs_climatology_95ci_mm": climatology_ci,
        "baseline_gate_passed": baseline_gate_passed,
        "test_rows": len(test),
        "persistence_comparison_rows": int(valid_baseline.sum()),
        "climatology_comparison_rows": int(valid_climatology.sum()),
        "provenance": {
            "source_type_by_location": source_types,
            "description": (
                "Repository-held daily modelled reanalysis grid-point records; "
                "not station observations."
            ),
        },
        "status": "RESEARCH_TRANSFER_EXPERIMENT_NOT_INDEPENDENTLY_VALIDATED",
        "promotion_rule": (
            "Do not promote unless the paired MAE-improvement intervals against both "
            "persistence and training-only monthly-climatology baselines are wholly "
            "above zero, calibration/uncertainty is assessed, and an independent "
            "station-observation evaluation is completed."
        ),
        "limitations": [
            "Kochi is spatially held out from all fitting and model selection.",
            "Test period is also later than the training and validation periods.",
            "Reanalysis grid points are modelled products, not independent station observations.",
            "Rainfall regression is not flood occurrence, inundation, depth, or impact prediction.",
            "One held-out location is insufficient to claim Kerala-wide transfer.",
            "The reported test period is a single holdout, not independent operational validation.",
        ],
        "intended_use": "Research on cross-location transfer of next-day rainfall estimates only.",
        "prohibited_use": "No public warnings, flood forecasts, evacuation, or asset decisions.",
        "artifact": "model.joblib",
    }
    (output_dir / "model_card.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "models" / "research" / "kerala_cross_location_rainfall_nextday",
    )
    args = parser.parse_args()
    report = train(args.output_dir)
    print(json.dumps({
        "model_id": report["model_id"],
        "selected_model_type": report["selected_model_type"],
        "held_out_kochi_metrics": report["held_out_kochi_metrics"],
        "wet_day_occurrence_metrics": report["wet_day_occurrence_metrics"],
        "seasonal_holdout_metrics": report["seasonal_holdout_metrics"],
        "persistence_baseline_metrics": report["persistence_baseline_metrics"],
        "seasonal_climatology_baseline_metrics": report["seasonal_climatology_baseline_metrics"],
        "mae_skill_over_persistence": report["mae_skill_over_persistence"],
        "mae_skill_over_seasonal_climatology": report["mae_skill_over_seasonal_climatology"],
        "paired_mae_improvement_vs_persistence_95ci_mm": report["paired_mae_improvement_vs_persistence_95ci_mm"],
        "paired_mae_improvement_vs_climatology_95ci_mm": report["paired_mae_improvement_vs_climatology_95ci_mm"],
        "baseline_gate_passed": report["baseline_gate_passed"],
        "status": report["status"],
    }, indent=2))


if __name__ == "__main__":
    main()

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
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

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
    frame = dataset.frame[[DATE, TARGET, BASELINE, *columns]].copy()
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
    valid_baseline = np.isfinite(baseline_values)
    if not np.isfinite(predicted).all() or not np.isfinite(actual).all():
        raise ValueError("Non-finite model predictions or test targets.")
    model_metrics = _metrics(actual, predicted)
    baseline_metrics = _metrics(actual[valid_baseline], baseline_values[valid_baseline])
    paired_ci = _paired_block_ci(
        actual[valid_baseline], predicted[valid_baseline], baseline_values[valid_baseline]
    )
    skill = 1.0 - model_metrics["mae_mm"] / max(baseline_metrics["mae_mm"], 1e-12)

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
        "persistence_baseline_metrics": baseline_metrics,
        "mae_skill_over_persistence": float(skill),
        "paired_mae_improvement_95ci_mm": paired_ci,
        "test_rows": len(test),
        "baseline_comparison_rows": int(valid_baseline.sum()),
        "provenance": {
            "source_type_by_location": source_types,
            "description": (
                "Repository-held daily modelled reanalysis grid-point records; "
                "not station observations."
            ),
        },
        "status": "RESEARCH_TRANSFER_EXPERIMENT_NOT_INDEPENDENTLY_VALIDATED",
        "promotion_rule": (
            "Do not promote unless the paired MAE-improvement interval is wholly "
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
        "persistence_baseline_metrics": report["persistence_baseline_metrics"],
        "mae_skill_over_persistence": report["mae_skill_over_persistence"],
        "paired_mae_improvement_95ci_mm": report["paired_mae_improvement_95ci_mm"],
        "status": report["status"],
    }, indent=2))


if __name__ == "__main__":
    main()

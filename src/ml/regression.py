"""Continuous weather ML using temporal holdouts and naive baselines."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from src.ml.data import Dataset, build_weather_target_dataset, build_cyclone_intensification_dataset
from src.ml.estimators import REGRESSION_CANDIDATES, build_regressor
from src.ml.features import assert_no_leakage, feature_frame
from src.ml.persistence import save_model_bundle
from src.ml.registry import list_model_cards, register
from src.ml.training import temporal_split

VALIDATION_STATUS = "SINGLE_TEMPORAL_HOLDOUT_NOT_INDEPENDENTLY_VALIDATED"


def _regression_metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "r2": float(r2_score(actual, predicted)) if len(actual) > 1 else 0.0,
        "n": int(len(actual)),
    }


def _paired_mae_improvement_ci(
    actual: np.ndarray,
    model_prediction: np.ndarray,
    baseline_prediction: np.ndarray,
    *,
    group_ids: np.ndarray | None = None,
    block_length: int = 7,
    n_bootstrap: int = 1000,
    random_state: int = 42,
) -> list[float]:
    """Paired MAE interval that preserves event or short-range dependence."""
    actual = np.asarray(actual, dtype=float)
    model_prediction = np.asarray(model_prediction, dtype=float)
    baseline_prediction = np.asarray(baseline_prediction, dtype=float)
    if not (actual.ndim == model_prediction.ndim == baseline_prediction.ndim == 1):
        raise ValueError("Bootstrap inputs must be one-dimensional.")
    if not (len(actual) == len(model_prediction) == len(baseline_prediction)):
        raise ValueError("Bootstrap inputs must have equal lengths.")
    if len(actual) < 2 or not (
        np.isfinite(actual).all()
        and np.isfinite(model_prediction).all()
        and np.isfinite(baseline_prediction).all()
    ):
        return [float("nan"), float("nan")]

    differences = np.abs(actual - baseline_prediction) - np.abs(actual - model_prediction)
    rng = np.random.default_rng(random_state)
    means = np.empty(n_bootstrap, dtype=float)
    if group_ids is not None:
        groups = np.asarray(group_ids).astype(str)
        if len(groups) != len(differences) or pd.isna(groups).any():
            raise ValueError("Bootstrap group IDs must be complete and match score rows.")
        unique_groups = np.unique(groups)
        if len(unique_groups) < 2:
            return [float("nan"), float("nan")]
        members = [np.flatnonzero(groups == group) for group in unique_groups]
        for draw in range(n_bootstrap):
            chosen = rng.integers(0, len(members), size=len(members))
            sampled = np.concatenate([members[index] for index in chosen])
            means[draw] = differences[sampled].mean()
    else:
        if block_length < 1:
            raise ValueError("block_length must be at least one.")
        length = min(int(block_length), len(differences))
        n_blocks = int(np.ceil(len(differences) / length))
        offsets = np.arange(length)
        for draw in range(n_bootstrap):
            starts = rng.integers(0, len(differences), size=n_blocks)
            sampled = ((starts[:, None] + offsets[None, :]) % len(differences)).ravel()[:len(differences)]
            means[draw] = differences[sampled].mean()

    low, high = np.quantile(means, [0.025, 0.975])
    return [float(low), float(high)]


def train_regression_dataset(
    dataset: Dataset, *, model_id: str, hazard: str,
    persistence_column: str | None, unit: str,
    validation_start: str = "2015-01-01", test_start: str = "2020-01-01",
    group_column: str | None = None, label_end_column: str | None = None,
    baseline_constant: float | None = None,
    target_definition: str | None = None,
    extra_limitations: list[str] | None = None,
    prediction_lower_bound: float | None = None,
) -> dict[str, Any]:
    """Select by validation MAE and score once on a future temporal holdout."""
    frame = dataset.frame.copy()
    features, feature_columns = feature_frame(dataset)
    assert_no_leakage(feature_columns, dataset.target_column, date_column=dataset.date_column, frame=frame)
    target = pd.to_numeric(frame[dataset.target_column], errors="coerce")
    valid = target.notna() & np.isfinite(target.to_numpy(dtype=float)) & pd.to_datetime(frame[dataset.date_column]).notna()
    frame, features, target = frame.loc[valid].copy(), features.loc[valid].copy(), target.loc[valid].astype(float)
    order = np.argsort(pd.to_datetime(frame[dataset.date_column]).to_numpy(), kind="mergesort")
    frame, features, target = frame.iloc[order].reset_index(drop=True), features.iloc[order].reset_index(drop=True), target.iloc[order].reset_index(drop=True)
    frame["_continuous_target"] = target.to_numpy()
    train, validation, test, purge = temporal_split(
        frame, date_column=dataset.date_column,
        validation_start=pd.Timestamp(validation_start), test_start=pd.Timestamp(test_start),
        group_column=group_column, label_end_column=label_end_column,
    )
    if min(len(train), len(validation), len(test)) < 100:
        raise ValueError(f"{model_id}: insufficient temporal rows (train={len(train)}, validation={len(validation)}, test={len(test)}).")
    X_train, X_val, X_test = (features.loc[idx, feature_columns] for idx in (train.index, validation.index, test.index))
    y_train, y_val, y_test = (part["_continuous_target"].to_numpy(dtype=float) for part in (train, validation, test))
    candidates, fitted = [], {}
    for name in REGRESSION_CANDIDATES:
        model = build_regressor(name)
        model.fit(X_train, y_train)
        validation_prediction = np.asarray(model.predict(X_val), dtype=float)
        if prediction_lower_bound is not None:
            validation_prediction = np.maximum(validation_prediction, prediction_lower_bound)
        scores = _regression_metrics(y_val, validation_prediction)
        candidates.append({"model_type": name, **scores})
        fitted[name] = model
    selected = min(candidates, key=lambda row: (row["mae"], row["rmse"]))
    final_train = pd.concat([train, validation]).sort_values(dataset.date_column)
    final_model = build_regressor(selected["model_type"])
    final_model.fit(features.loc[final_train.index, feature_columns], final_train["_continuous_target"].to_numpy(dtype=float))
    predicted = np.asarray(final_model.predict(X_test), dtype=float)
    if prediction_lower_bound is not None:
        predicted = np.maximum(predicted, prediction_lower_bound)
    if not np.isfinite(predicted).all():
        raise ValueError(f"{model_id}: fitted model produced non-finite test predictions.")
    metrics = _regression_metrics(y_test, predicted)
    baseline: dict[str, Any] = {"available": False}
    baseline_prediction: np.ndarray | None = None
    comparison_actual = y_test
    comparison_model_prediction = predicted
    comparison_group_ids: np.ndarray | None = None
    if persistence_column and persistence_column in test.columns:
        persistence = pd.to_numeric(test[persistence_column], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(persistence) & np.isfinite(y_test)
        if mask.any():
            baseline_prediction = persistence[mask]
            comparison_actual = y_test[mask]
            comparison_model_prediction = predicted[mask]
            if group_column and group_column in test.columns:
                comparison_group_ids = test.loc[mask, group_column].to_numpy()
            baseline = {"available": True, "type": "persistence", **_regression_metrics(comparison_actual, baseline_prediction)}
    elif baseline_constant is not None:
        baseline_prediction = np.full_like(y_test, baseline_constant, dtype=float)
        if group_column and group_column in test.columns:
            comparison_group_ids = test[group_column].to_numpy()
        baseline = {"available": True, "type": "constant_no_change", **_regression_metrics(y_test, baseline_prediction)}
    median = _regression_metrics(y_test, np.full_like(y_test, float(np.median(final_train["_continuous_target"]))))
    baseline["training_median"] = median
    reference_mae = baseline.get("mae", median["mae"])
    comparison_model_mae = (
        _regression_metrics(comparison_actual, comparison_model_prediction)["mae"]
        if baseline_prediction is not None
        else metrics["mae"]
    )
    skill = 1.0 - comparison_model_mae / max(float(reference_mae), 1e-12)
    paired_ci = (
        _paired_mae_improvement_ci(
            comparison_actual,
            comparison_model_prediction,
            baseline_prediction,
            group_ids=comparison_group_ids,
            block_length=7,
        )
        if baseline_prediction is not None else [float("nan"), float("nan")]
    )
    bootstrap_method = (
        "cluster_bootstrap_by_" + group_column
        if comparison_group_ids is not None
        else "circular_moving_block_bootstrap_7_rows"
    )
    status = "WEAK_RESEARCH_SIGNAL" if paired_ci[0] > 0 else "NO_SKILL"
    card = {
        "schema_version": 1, "engine_version": "shared-ml-engine/1.1.0",
        "model_id": model_id, "hazard": hazard, "task_type": "regression",
        "dataset_name": dataset.name, "target_column": dataset.target_column,
        "target_definition": target_definition or f"Next-day {hazard.lower()}-related {unit} at a reanalysis grid point.",
        "prediction_unit": unit, "status": status, "skill_grade": status,
        "status_reason": (
            f"MAE skill over baseline: {skill:.3f}; paired bootstrap 95% CI for MAE improvement: {paired_ci}."
            if status == "WEAK_RESEARCH_SIGNAL" else
            f"MAE skill over baseline: {skill:.3f}, but the paired bootstrap 95% CI does not establish improvement."
        ),
        "validation_status": VALIDATION_STATUS,
        "trained_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "selected_model_type": selected["model_type"],
        "model_selection_metric": "Validation MAE, then RMSE.",
        "candidate_selection": candidates,
        "temporal_split": {"validation_start": validation_start, "test_start": test_start, "purged_rows": purge, "train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test)},
        "feature_columns": feature_columns, "feature_count": len(feature_columns),
        "metrics": {
            **metrics,
            "persistence_baseline": baseline,
            "mae_skill_over_persistence": float(skill),
            "mae_skill_comparison_rows": int(len(comparison_actual)) if baseline_prediction is not None else int(len(y_test)),
            "paired_mae_improvement_bootstrap_95ci": paired_ci,
            "paired_bootstrap_method": bootstrap_method,
            "prediction_lower_bound": prediction_lower_bound,
        },
        "provenance": dataset.provenance,
        "limitations": [
            "Single temporal holdout is not independent validation.",
            "Weather values are reanalysis grid-point data, not local station observations.",
            "A next-day weather estimate is not a flood, drought, heat-health, or impact prediction.",
            "No calibrated uncertainty interval is claimed.",
            *(extra_limitations or []),
        ],
        "intended_use": "Supplementary continuous weather research output only.",
        "prohibited_use": "Not for public warnings, evacuation decisions, or disaster-impact prediction.",
        "artifact": {"path": f"models/ml/{model_id}/model.joblib", "format": "joblib-pipeline", "loader": "src.ml.inference.predict_regression_from_context"},
    }
    save_model_bundle(model_id, final_model, card)
    return card


def train_continuous_regression_models() -> list[dict[str, Any]]:
    """Train continuous weather and cyclone-intensity models from real source records."""
    specs = (
        (build_weather_target_dataset("kochi", lead_days=1, target="extreme_rainfall"), "weather_precipitation_kochi_nextday_regression", "Flood", "mm/day", "precipitation_sum", {"prediction_lower_bound": 0.0}),
        (build_weather_target_dataset("kochi", lead_days=1, target="high_temperature"), "weather_tmax_kochi_nextday_regression", "Heatwave", "degrees Celsius", "temperature_2m_max", {}),
        (build_cyclone_intensification_dataset(), "cyclone_wind_change_24h_regression", "Cyclone", "knots", None, {
            "group_column": "storm_id",
            "label_end_column": "future_time_24h",
            "baseline_constant": 0.0,
            "target_definition": "Change in maximum sustained wind over the next approximately 24 hours, in knots, from IBTrACS best-track sequences.",
            "extra_limitations": [
                "Storm groups are held out intact and future outcome windows are purged at temporal boundaries.",
                "A best-track retrospective model is not an operational cyclone intensity forecast.",
            ],
        }),
    )
    cards = [
        train_regression_dataset(
            ds, model_id=mid, hazard=hazard, unit=unit,
            persistence_column=baseline, **options,
        )
        for ds, mid, hazard, unit, baseline, options in specs
    ]
    current = list_model_cards()
    merged = {card["model_id"]: card for card in current}
    merged.update({card["model_id"]: card for card in cards})
    register(merged.values(), extra={"validated_models": 0, "interpretation": "Regression models are supplementary continuous weather estimates; no operational model is validated."})
    return cards


# Backwards-compatible name used by the training entry point.
train_weather_regression_models = train_continuous_regression_models

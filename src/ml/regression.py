"""Continuous weather ML using temporal holdouts and naive baselines."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from src.ml.data import Dataset, build_weather_target_dataset
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


def train_regression_dataset(
    dataset: Dataset, *, model_id: str, hazard: str,
    persistence_column: str, unit: str,
    validation_start: str = "2015-01-01", test_start: str = "2020-01-01",
) -> dict[str, Any]:
    """Select by validation MAE and score once on a future temporal holdout."""
    frame = dataset.frame.copy()
    features, feature_columns = feature_frame(dataset)
    assert_no_leakage(feature_columns, dataset.target_column, date_column=dataset.date_column, frame=frame)
    target = pd.to_numeric(frame[dataset.target_column], errors="coerce")
    valid = target.notna() & pd.to_datetime(frame[dataset.date_column]).notna()
    frame, features, target = frame.loc[valid].copy(), features.loc[valid].copy(), target.loc[valid].astype(float)
    order = np.argsort(pd.to_datetime(frame[dataset.date_column]).to_numpy(), kind="mergesort")
    frame, features, target = frame.iloc[order].reset_index(drop=True), features.iloc[order].reset_index(drop=True), target.iloc[order].reset_index(drop=True)
    frame["_continuous_target"] = target.to_numpy()
    train, validation, test, purge = temporal_split(
        frame, date_column=dataset.date_column,
        validation_start=pd.Timestamp(validation_start), test_start=pd.Timestamp(test_start),
    )
    if min(len(train), len(validation), len(test)) < 100:
        raise ValueError(f"{model_id}: insufficient temporal rows (train={len(train)}, validation={len(validation)}, test={len(test)}).")
    X_train, X_val, X_test = (features.loc[idx, feature_columns] for idx in (train.index, validation.index, test.index))
    y_train, y_val, y_test = (part["_continuous_target"].to_numpy(dtype=float) for part in (train, validation, test))
    candidates, fitted = [], {}
    for name in REGRESSION_CANDIDATES:
        model = build_regressor(name)
        model.fit(X_train, y_train)
        scores = _regression_metrics(y_val, np.asarray(model.predict(X_val), dtype=float))
        candidates.append({"model_type": name, **scores})
        fitted[name] = model
    selected = min(candidates, key=lambda row: (row["mae"], row["rmse"]))
    final_train = pd.concat([train, validation]).sort_values(dataset.date_column)
    final_model = build_regressor(selected["model_type"])
    final_model.fit(features.loc[final_train.index, feature_columns], final_train["_continuous_target"].to_numpy(dtype=float))
    metrics = _regression_metrics(y_test, np.asarray(final_model.predict(X_test), dtype=float))
    baseline: dict[str, Any] = {"available": False}
    if persistence_column in test.columns:
        persistence = pd.to_numeric(test[persistence_column], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(persistence) & np.isfinite(y_test)
        if mask.any():
            baseline = {"available": True, **_regression_metrics(y_test[mask], persistence[mask])}
    median = _regression_metrics(y_test, np.full_like(y_test, float(np.median(final_train["_continuous_target"]))))
    baseline["training_median"] = median
    reference_mae = baseline.get("mae", median["mae"])
    skill = 1.0 - metrics["mae"] / max(float(reference_mae), 1e-12)
    status = "WEAK_RESEARCH_SIGNAL" if skill > 0 else "NO_SKILL"
    card = {
        "schema_version": 1, "engine_version": "shared-ml-engine/1.1.0",
        "model_id": model_id, "hazard": hazard, "task_type": "regression",
        "dataset_name": dataset.name, "target_column": dataset.target_column,
        "target_definition": f"Next-day {hazard.lower()}-related {unit} at a reanalysis grid point.",
        "prediction_unit": unit, "status": status, "skill_grade": status,
        "status_reason": f"MAE skill over persistence: {skill:.3f}.",
        "validation_status": VALIDATION_STATUS,
        "trained_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "selected_model_type": selected["model_type"],
        "model_selection_metric": "Validation MAE, then RMSE.",
        "candidate_selection": candidates,
        "temporal_split": {"validation_start": validation_start, "test_start": test_start, "purged_rows": purge, "train_rows": len(train), "validation_rows": len(validation), "test_rows": len(test)},
        "feature_columns": feature_columns, "feature_count": len(feature_columns),
        "metrics": {**metrics, "persistence_baseline": baseline, "mae_skill_over_persistence": float(skill)},
        "provenance": dataset.provenance,
        "limitations": [
            "Single temporal holdout is not independent validation.",
            "Weather values are reanalysis grid-point data, not local station observations.",
            "A next-day weather estimate is not a flood, drought, heat-health, or impact prediction.",
            "No calibrated uncertainty interval is claimed.",
        ],
        "intended_use": "Supplementary continuous weather research output only.",
        "prohibited_use": "Not for public warnings, evacuation decisions, or disaster-impact prediction.",
        "artifact": {"path": f"models/ml/{model_id}/model.joblib", "format": "joblib-pipeline", "loader": "src.ml.inference.predict_regression_from_context"},
    }
    save_model_bundle(model_id, final_model, card)
    return card


def train_weather_regression_models() -> list[dict[str, Any]]:
    """Train continuous next-day rainfall and temperature models from real weather records."""
    specs = (
        (build_weather_target_dataset("kochi", lead_days=1, target="extreme_rainfall"), "weather_precipitation_kochi_nextday_regression", "Flood", "mm/day", "precipitation_sum"),
        (build_weather_target_dataset("kochi", lead_days=1, target="high_temperature"), "weather_tmax_kochi_nextday_regression", "Heatwave", "degrees Celsius", "temperature_2m_max"),
    )
    cards = [train_regression_dataset(ds, model_id=mid, hazard=hazard, unit=unit, persistence_column=baseline) for ds, mid, hazard, unit, baseline in specs]
    current = list_model_cards()
    merged = {card["model_id"]: card for card in current}
    merged.update({card["model_id"]: card for card in cards})
    register(merged.values(), extra={"validated_models": 0, "interpretation": "Regression models are supplementary continuous weather estimates; no operational model is validated."})
    return cards

"""Evidence-gated project duration estimation from completed projects."""
from __future__ import annotations

import math
from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.mitigation_cost_ml import CostModelDataError, prepare_cost_records

CATS = ("intervention", "area_type", "scope_unit")
NUMS = ("scope_quantity", "actual_cost_inr")
FEATURES = CATS + NUMS


def train_duration_model(records: pd.DataFrame) -> dict[str, Any]:
    """Train an evidence-gated duration model and compare it with a median baseline."""
    frame = prepare_cost_records(records)
    if "duration_months" not in records.columns:
        raise CostModelDataError("Missing required duration outcome: duration_months.")
    durations = pd.to_numeric(records["duration_months"], errors="coerce")
    frame = frame.join(durations.rename("duration_months"))
    frame = frame.loc[
        frame["duration_months"].notna()
        & frame["duration_months"].map(lambda value: math.isfinite(float(value)) and float(value) > 0)
    ].reset_index(drop=True)
    if len(frame) < 40:
        raise CostModelDataError(
            f"Only {len(frame)} complete, sourced records include a valid duration. "
            "At least 40 are required before delivery-model training."
        )
    X = frame.loc[:, list(FEATURES)]
    y = frame["duration_months"].astype(float)
    n_test = max(8, math.ceil(len(frame) * 0.2))
    if len(frame) - n_test < 20:
        raise CostModelDataError("Not enough records remain for duration holdout evaluation.")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=n_test, random_state=42
    )
    preprocessor = ColumnTransformer([
        ("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), list(CATS)),
        ("num", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), list(NUMS)),
    ])
    model = Pipeline([
        ("prep", preprocessor),
        ("rf", RandomForestRegressor(
            n_estimators=300, min_samples_leaf=2, random_state=42, n_jobs=-1
        )),
    ])
    baseline = DummyRegressor(strategy="median")
    model.fit(X_train, y_train)
    baseline.fit(X_train, y_train)
    predictions = model.predict(X_test)
    baseline_predictions = baseline.predict(X_test)
    mae = float(mean_absolute_error(y_test, predictions))
    baseline_mae = float(mean_absolute_error(y_test, baseline_predictions))

    return {
        "model": model,
        "metrics": {
            "records_used": len(frame),
            "training_records": len(X_train),
            "validation_records": len(X_test),
            "mae_months": mae,
            "baseline_mae_months": baseline_mae,
            "r2": float(r2_score(y_test, predictions)),
            "beats_baseline": mae < baseline_mae,
            "validation_method": "Fixed 80/20 holdout; random_state=42",
        },
        "categories": {column: sorted(frame[column].unique().tolist()) for column in CATS},
    }


def estimate_duration(
    trained: dict[str, Any],
    *,
    intervention: str,
    area_type: str,
    scope_quantity: float,
    scope_unit: str,
    estimated_cost_inr: float,
) -> dict[str, float]:
    """Estimate duration for a comparable scope; error band is indicative only."""
    metrics = trained["metrics"]
    if not metrics["beats_baseline"]:
        raise CostModelDataError(
            "Duration model did not outperform the median baseline on held-out records."
        )
    numeric = {
        "scope_quantity": float(scope_quantity),
        "actual_cost_inr": float(estimated_cost_inr),
    }
    if any(not math.isfinite(value) or value <= 0 for value in numeric.values()):
        raise CostModelDataError("Scope quantity and estimated cost must be finite and greater than zero.")
    categorical = {
        "intervention": str(intervention).strip(),
        "area_type": str(area_type).strip(),
        "scope_unit": str(scope_unit).strip(),
    }
    if any(not value for value in categorical.values()):
        raise CostModelDataError("Choose an intervention, area type and scope unit.")

    sample = pd.DataFrame([{**categorical, **numeric}], columns=FEATURES)
    estimate = max(0.1, float(trained["model"].predict(sample)[0]))
    mae = float(metrics["mae_months"])
    return {
        "estimated_duration_months": estimate,
        "validation_error_months": mae,
        "lower_estimate_months": max(0.1, estimate - mae),
        "upper_estimate_months": estimate + mae,
    }

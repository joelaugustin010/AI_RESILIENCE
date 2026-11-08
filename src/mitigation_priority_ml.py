"""Evidence-gated supervised ML for mitigation investment priority labels."""
from __future__ import annotations
import math
from typing import Any
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, balanced_accuracy_score
from sklearn.model_selection import train_test_split

FEATURES = ("site_risk_severity", "urgency", "evidence_strength", "implementation_readiness")
TARGET = "historical_priority_label"
REQUIRED = FEATURES + (TARGET, "source_reference")
ALLOWED_LABELS = ("Higher assessed priority", "Moderate", "Further review")
MIN_RECORDS = 40
MIN_PER_CLASS = 5

class PriorityModelDataError(ValueError):
    """Historical priority data is not ready for supervised ML."""

def prepare_priority_records(records: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(records, pd.DataFrame):
        raise PriorityModelDataError("Upload a CSV of completed projects with expert-reviewed priority labels.")
    missing = [column for column in REQUIRED if column not in records.columns]
    if missing:
        raise PriorityModelDataError("Missing required columns: " + ", ".join(missing))
    frame = records.loc[:, list(REQUIRED)].copy()
    frame["source_reference"] = frame["source_reference"].fillna("").astype(str).str.strip()
    frame[TARGET] = frame[TARGET].fillna("").astype(str).str.strip()
    for column in FEATURES:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    finite = frame[list(FEATURES)].apply(
        lambda column: column.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    ).all(axis=1)
    valid = (
        frame["source_reference"].ne("")
        & frame[TARGET].isin(ALLOWED_LABELS)
        & finite
        & frame[list(FEATURES)].ge(1).all(axis=1)
        & frame[list(FEATURES)].le(5).all(axis=1)
    )
    frame = frame.loc[valid].copy()
    if len(frame) < MIN_RECORDS:
        raise PriorityModelDataError(
            f"Only {len(frame)} complete, sourced and labelled records are usable. At least {MIN_RECORDS} are required."
        )
    counts = frame[TARGET].value_counts()
    too_small = [label for label in frame[TARGET].unique() if counts[label] < MIN_PER_CLASS]
    if too_small:
        raise PriorityModelDataError(
            "Each priority class needs at least 5 records. Under-represented classes: " + ", ".join(too_small)
        )
    if frame[TARGET].nunique() < 2:
        raise PriorityModelDataError("At least two different historical priority labels are required.")
    return frame.reset_index(drop=True)

def train_priority_model(records: pd.DataFrame) -> dict[str, Any]:
    frame = prepare_priority_records(records)
    X = frame.loc[:, list(FEATURES)]
    y = frame[TARGET]
    n_test = max(8, math.ceil(len(frame) * 0.2))
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=n_test, random_state=42, stratify=y
    )
    model = RandomForestClassifier(
        n_estimators=400, min_samples_leaf=2, class_weight="balanced",
        random_state=42, n_jobs=-1,
    )
    baseline = DummyClassifier(strategy="most_frequent")
    model.fit(X_train, y_train)
    baseline.fit(X_train, y_train)
    predictions = model.predict(X_test)
    baseline_predictions = baseline.predict(X_test)
    accuracy = float(accuracy_score(y_test, predictions))
    baseline_accuracy = float(accuracy_score(y_test, baseline_predictions))
    return {
        "model": model,
        "metrics": {
            "records_used": len(frame),
            "training_records": len(X_train),
            "validation_records": len(X_test),
            "accuracy": accuracy,
            "baseline_accuracy": baseline_accuracy,
            "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
            "beats_baseline": accuracy > baseline_accuracy,
            "validation_method": "Stratified 80/20 holdout; random_state=42",
        },
        "class_counts": {str(k): int(v) for k, v in frame[TARGET].value_counts().items()},
    }

def predict_priority(trained: dict[str, Any], assessments: dict[str, Any]) -> dict[str, Any]:
    if not trained["metrics"].get("beats_baseline"):
        raise PriorityModelDataError("Priority model did not outperform the majority-class baseline.")
    values = {}
    for feature in FEATURES:
        try:
            value = float(assessments[feature])
        except (KeyError, TypeError, ValueError):
            raise PriorityModelDataError(f"Missing or invalid assessment: {feature}.")
        if not math.isfinite(value) or value < 1 or value > 5:
            raise PriorityModelDataError(f"{feature} must be a number from 1 to 5.")
        values[feature] = value
    sample = pd.DataFrame([values], columns=FEATURES)
    probabilities = trained["model"].predict_proba(sample)[0]
    classes = trained["model"].classes_
    best_index = int(probabilities.argmax())
    return {
        "predicted_priority": str(classes[best_index]),
        "confidence": float(probabilities[best_index]),
        "probabilities": {str(label): float(prob) for label, prob in zip(classes, probabilities)},
    }

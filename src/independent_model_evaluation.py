"""Independent evaluation helpers for disaster-specific models."""
from __future__ import annotations
from typing import Any, Sequence
import numpy as np
from sklearn.metrics import accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score, mean_absolute_error, mean_squared_error, precision_score, r2_score, recall_score

def evaluate_classifier(y_true: Sequence[Any], y_pred: Sequence[Any], *, labels: Sequence[Any] | None = None, y_probability: Sequence[float] | None = None) -> dict[str, Any]:
    """Score predictions on a held-out set; this does not train or certify a model."""
    actual, predicted = np.asarray(y_true), np.asarray(y_pred)
    if actual.ndim != 1 or predicted.ndim != 1 or len(actual) != len(predicted):
        raise ValueError("y_true and y_pred must be aligned one-dimensional arrays")
    if len(actual) == 0:
        raise ValueError("Evaluation requires at least one held-out example")
    if labels is None:
        labels = list(dict.fromkeys(actual.tolist() + predicted.tolist()))
    if not labels:
        raise ValueError("At least one class label is required")
    result = {
        "evaluation_type": "classification", "n_test": int(len(actual)), "labels": list(labels),
        "accuracy": float(accuracy_score(actual, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
        "macro_precision": float(precision_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
        "macro_recall": float(recall_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
        "macro_f1": float(f1_score(actual, predicted, labels=labels, average="macro", zero_division=0)),
        "confusion_matrix": confusion_matrix(actual, predicted, labels=labels).tolist(),
        "probability_metrics_available": False,
        "limitations": ["Metrics require test data independent of training and model selection.", "Scores do not establish calibration, geographic transferability, or operational readiness."]
    }
    if y_probability is not None:
        probabilities = np.asarray(y_probability, dtype=float)
        if probabilities.ndim != 1 or len(probabilities) != len(actual):
            raise ValueError("y_probability must contain one value per test row")
        if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
            raise ValueError("Probabilities must be finite and between 0 and 1")
        if len(labels) != 2:
            raise ValueError("Brier score helper requires exactly two labels")
        event_label = labels[1]
        result["brier_score"] = float(mean_squared_error((actual == event_label).astype(float), probabilities))
        result["probability_metrics_available"] = True
        result["probability_positive_class"] = event_label
    return result

def evaluate_regressor(y_true: Sequence[float], y_pred: Sequence[float]) -> dict[str, Any]:
    """Score continuous predictions on an independent held-out set."""
    actual, predicted = np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)
    if actual.ndim != 1 or predicted.ndim != 1 or len(actual) != len(predicted):
        raise ValueError("y_true and y_pred must be aligned one-dimensional arrays")
    if len(actual) < 2:
        raise ValueError("Regression evaluation requires at least two held-out examples")
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
        raise ValueError("Regression values must be finite")
    return {"evaluation_type": "regression", "n_test": int(len(actual)),
            "mae": float(mean_absolute_error(actual, predicted)),
            "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
            "r2": float(r2_score(actual, predicted)),
            "limitations": ["Metrics require test data independent of training and model selection.", "Scores do not establish geographic transferability or operational readiness."]}

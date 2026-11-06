"""Held-out evaluation, calibration diagnostics and honest skill grading.

All metrics here are retrospective.  A positive skill grade means only that a
single temporal holdout showed better-than-baseline ranking; it never means the
model is validated, calibrated for decisions, or operationally predictive.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

STATUS_NO_SKILL = "NO_SKILL"
STATUS_WEAK = "WEAK_RESEARCH_SIGNAL"
STATUS_SIGNAL = "RESEARCH_SIGNAL_NOT_VALIDATED"
STATUS_INSUFFICIENT = "INSUFFICIENT_TEST_EVENTS"


def event_threshold(values: Sequence[float], *, quantile: float, direction: str) -> float:
    """Estimate an event threshold from training-era target values only."""
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if array.size < 30:
        raise ValueError("At least 30 training outcomes are needed to estimate an event threshold.")
    if not 0.0 < quantile < 1.0:
        raise ValueError("quantile must be strictly between 0 and 1.")
    if direction not in {"high", "low"}:
        raise ValueError("direction must be 'high' or 'low'.")
    # For a low-rainfall event with quantile 0.10, the threshold is the 10th
    # percentile; for a high event with quantile 0.95 it is the 95th.
    return float(np.quantile(array, quantile))


def label_target(
    values: Sequence[float],
    *,
    threshold: float,
    direction: str,
) -> np.ndarray:
    """Convert a continuous target into a binary event label."""
    array = np.asarray(values, dtype=float)
    if direction == "high":
        return (array >= threshold).astype(int)
    if direction == "low":
        return (array <= threshold).astype(int)
    raise ValueError("direction must be 'high' or 'low'.")


def threshold_sweep(
    y_true: Sequence[int],
    probabilities: Sequence[float],
    *,
    candidates: Sequence[float] | None = None,
) -> list[dict[str, float]]:
    """Score decision thresholds, without choosing a final one."""
    actual = np.asarray(y_true, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if candidates is None:
        candidates = tuple(round(value, 3) for value in np.arange(0.02, 0.951, 0.02))
    rows: list[dict[str, float]] = []
    for threshold in candidates:
        predicted = (scores >= threshold).astype(int)
        rows.append(
            {
                "threshold": float(threshold),
                "precision": float(precision_score(actual, predicted, zero_division=0)),
                "recall": float(recall_score(actual, predicted, zero_division=0)),
                "f1": float(f1_score(actual, predicted, zero_division=0)),
                "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
                "predicted_positive_rate": float(predicted.mean()),
            }
        )
    return rows


def select_threshold(
    y_true: Sequence[int],
    probabilities: Sequence[float],
) -> dict[str, float]:
    """Choose the validation F1-maximising threshold (tie-break recall then precision)."""
    rows = threshold_sweep(y_true, probabilities)
    return max(
        rows,
        key=lambda item: (item["f1"], item["recall"], item["precision"], -item["threshold"]),
    )


def calibration_diagnostics(
    y_true: Sequence[int],
    probabilities: Sequence[float],
    *,
    n_bins: int = 10,
) -> dict[str, Any]:
    """Return Brier score, log loss, expected calibration error and a table."""
    actual = np.asarray(y_true, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if actual.size == 0 or actual.size != scores.size:
        raise ValueError("Calibration diagnostics require aligned non-empty arrays.")
    clipped = np.clip(scores, 1e-12, 1 - 1e-12)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    # np.digitize returns 1..n_bins for values in (0,1]; clip the top edge.
    indices = np.clip(np.digitize(clipped, bins) - 1, 0, n_bins - 1)
    table: list[dict[str, Any]] = []
    ece = 0.0
    for index in range(n_bins):
        mask = indices == index
        count = int(mask.sum())
        if count == 0:
            continue
        mean_score = float(clipped[mask].mean())
        observed = float(actual[mask].mean())
        gap = abs(mean_score - observed)
        ece += (count / actual.size) * gap
        table.append(
            {
                "bin_lower": float(bins[index]),
                "bin_upper": float(bins[index + 1]),
                "n": count,
                "mean_probability": mean_score,
                "observed_event_rate": observed,
                "absolute_gap": float(gap),
            }
        )
    return {
        "brier_score": float(brier_score_loss(actual, clipped)),
        "log_loss": float(log_loss(actual, clipped, labels=[0, 1])),
        "expected_calibration_error": float(ece),
        "calibration_table": table,
        "calibration_interpretation": (
            "Expected calibration error is descriptive for this holdout. "
            "It does not establish calibration in future or operational use."
        ),
    }


def binary_metrics(
    y_true: Sequence[int],
    probabilities: Sequence[float],
    *,
    threshold: float,
    train_prevalence: float | None = None,
) -> dict[str, Any]:
    """Score a binary classifier at a fixed, validation-selected threshold."""
    actual = np.asarray(y_true, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if actual.size == 0 or actual.size != scores.size:
        raise ValueError("Evaluation requires aligned non-empty arrays.")
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("Probabilities must be finite and in [0, 1].")
    predicted = (scores >= threshold).astype(int)
    prevalence = float(actual.mean())
    tn, fp, fn, tp = confusion_matrix(actual, predicted, labels=[0, 1]).ravel()
    both_classes = int(np.unique(actual).size) == 2
    metrics: dict[str, Any] = {
        "n_test": int(actual.size),
        "n_test_events": int(actual.sum()),
        "test_prevalence": prevalence,
        "accuracy": float(accuracy_score(actual, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
        "precision": float(precision_score(actual, predicted, zero_division=0)),
        "recall": float(recall_score(actual, predicted, zero_division=0)),
        "f1": float(f1_score(actual, predicted, zero_division=0)),
        "roc_auc": float(roc_auc_score(actual, scores)) if both_classes else None,
        "average_precision": float(average_precision_score(actual, scores)) if both_classes else None,
        "brier_score": float(brier_score_loss(actual, scores)),
        "confusion_matrix_tn_fp_fn_tp": [int(tn), int(fp), int(fn), int(tp)],
        "predicted_positive_rate": float(predicted.mean()),
    }
    metrics.update(calibration_diagnostics(actual, scores))
    metrics["majority_baseline"] = _majority_baseline(actual, train_prevalence)
    metrics["base_rate_brier_score"] = float(brier_score_loss(actual, np.full_like(scores, prevalence)))
    metrics["skill_over_base_rate_brier"] = float(
        metrics["base_rate_brier_score"] - metrics["brier_score"]
    )
    return metrics


def _majority_baseline(actual: np.ndarray, train_prevalence: float | None) -> dict[str, Any]:
    """Report the constant-class baseline implied by training prevalence."""
    if train_prevalence is None:
        train_prevalence = float(actual.mean())
    constant = int(train_prevalence >= 0.5)
    predicted = np.full(actual.size, constant, dtype=int)
    return {
        "predicted_class": constant,
        "accuracy": float(accuracy_score(actual, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(actual, predicted)),
        "f1": float(f1_score(actual, predicted, zero_division=0)),
    }


def persistence_baseline(
    actual: Sequence[int],
    source_values: Sequence[float],
    *,
    threshold: float,
    direction: str,
) -> dict[str, Any]:
    """Score a simple 'tomorrow looks like today' reference rule."""
    actual_array = np.asarray(actual, dtype=int)
    values = np.asarray(source_values, dtype=float)
    mask = np.isfinite(values)
    if not mask.any():
        return {"available": False, "reason": "No persistence values were available."}
    predicted = label_target(values[mask], threshold=threshold, direction=direction)
    truth = actual_array[mask]
    return {
        "available": True,
        "n": int(mask.sum()),
        "accuracy": float(accuracy_score(truth, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(truth, predicted)),
        "precision": float(precision_score(truth, predicted, zero_division=0)),
        "recall": float(recall_score(truth, predicted, zero_division=0)),
        "f1": float(f1_score(truth, predicted, zero_division=0)),
    }


def bootstrap_confidence_intervals(
    y_true: Sequence[int],
    probabilities: Sequence[float],
    *,
    threshold: float,
    n_resamples: int = 300,
    seed: int = 42,
) -> dict[str, list[float] | None]:
    """Percentile bootstrap intervals for F1, ROC-AUC and average precision."""
    actual = np.asarray(y_true, dtype=int)
    scores = np.asarray(probabilities, dtype=float)
    if actual.size < 10:
        return {"f1": None, "roc_auc": None, "average_precision": None}
    rng = np.random.default_rng(seed)
    values: dict[str, list[float]] = {"f1": [], "roc_auc": [], "average_precision": []}
    for _ in range(n_resamples):
        indices = rng.integers(0, actual.size, actual.size)
        sample_y = actual[indices]
        sample_p = scores[indices]
        if np.unique(sample_y).size < 2:
            continue
        predicted = (sample_p >= threshold).astype(int)
        values["f1"].append(float(f1_score(sample_y, predicted, zero_division=0)))
        values["roc_auc"].append(float(roc_auc_score(sample_y, sample_p)))
        values["average_precision"].append(float(average_precision_score(sample_y, sample_p)))
    result: dict[str, list[float] | None] = {}
    for name, samples in values.items():
        result[name] = (
            [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]
            if samples
            else None
        )
    return result


def two_by_two_association(
    exposure: Sequence[float],
    outcome: Sequence[int],
    *,
    exposure_name: str = "exposure",
) -> dict[str, Any]:
    """Describe an unadjusted 2x2 association with a Haldane-corrected odds ratio.

    This is a descriptive association, not a causal effect.  The correction is
    used only so a zero cell does not produce an infinite estimate; it is
    reported alongside the raw counts.
    """
    exposure_array = np.asarray(exposure, dtype=float)
    outcome_array = np.asarray(outcome, dtype=int)
    if exposure_array.size != outcome_array.size:
        raise ValueError("Exposure and outcome arrays must be aligned.")
    exposed = exposure_array >= 0.5
    event = outcome_array == 1
    a = int(np.sum(exposed & event))
    b = int(np.sum(exposed & ~event))
    c = int(np.sum(~exposed & event))
    d = int(np.sum(~exposed & ~event))
    odds_ratio = ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
    p_value = None
    try:
        from scipy.stats import fisher_exact

        p_value = float(fisher_exact([[a, b], [c, d]])[1])
    except ImportError:  # pragma: no cover - scipy is a project dependency
        p_value = None
    return {
        "exposure": exposure_name,
        "table": {
            "exposed_event": a,
            "exposed_no_event": b,
            "unexposed_event": c,
            "unexposed_no_event": d,
        },
        "odds_ratio_haldane_corrected": float(odds_ratio),
        "fisher_exact_p_value": p_value,
        "interpretation": (
            "Unadjusted association only; exposure is concurrent with the outcome "
            "and confounding by season and prior rainfall is unresolved."
        ),
    }


def grade_skill(metrics: dict[str, Any]) -> dict[str, str]:
    """Assign a deliberately conservative status from holdout metrics only."""
    n_events = int(metrics.get("n_test_events") or 0)
    prevalence = float(metrics.get("test_prevalence") or 0.0)
    roc_auc = metrics.get("roc_auc")
    average_precision = metrics.get("average_precision")
    if n_events < 10:
        return {
            "status": STATUS_INSUFFICIENT,
            "reason": (
                f"Only {n_events} held-out events; ranking metrics are too unstable "
                "for a skill statement."
            ),
        }
    if roc_auc is None or average_precision is None:
        return {
            "status": STATUS_NO_SKILL,
            "reason": "The held-out period contains only one class, so discrimination cannot be scored.",
        }
    if roc_auc < 0.55 or average_precision <= max(prevalence * 1.05, prevalence + 0.01):
        return {
            "status": STATUS_NO_SKILL,
            "reason": (
                f"ROC-AUC {roc_auc:.3f} and average precision {average_precision:.3f} "
                f"do not clearly exceed the no-skill prevalence {prevalence:.3f}."
            ),
        }
    if roc_auc < 0.65 or average_precision < prevalence * 1.5:
        return {
            "status": STATUS_WEAK,
            "reason": (
                f"ROC-AUC {roc_auc:.3f} and average precision {average_precision:.3f} "
                "show a weak ranking signal only."
            ),
        }
    brier = metrics.get("brier_score")
    base_brier = metrics.get("base_rate_brier_score")
    if isinstance(brier, (int, float)) and isinstance(base_brier, (int, float)) and brier >= base_brier:
        return {
            "status": STATUS_WEAK,
            "reason": (
                f"Ranking beats the no-skill prevalence (ROC-AUC {roc_auc:.3f}, "
                f"average precision {average_precision:.3f}), but probability error "
                f"(Brier {brier:.3f}) is not better than the base-rate reference "
                f"({base_brier:.3f}). Treat the score as a ranking signal only."
            ),
        }
    persistence = metrics.get("persistence_baseline")
    model_f1 = metrics.get("f1")
    if (
        isinstance(persistence, dict)
        and persistence.get("available")
        and isinstance(model_f1, (int, float))
        and isinstance(persistence.get("f1"), (int, float))
        and model_f1 <= float(persistence["f1"]) + 1e-9
    ):
        return {
            "status": STATUS_WEAK,
            "reason": (
                f"Holdout F1 ({model_f1:.3f}) does not exceed the persistence "
                f"baseline ({float(persistence['f1']):.3f}); the model has not "
                "demonstrated incremental thresholded skill over persistence."
            ),
        }
    calibration_gap = metrics.get("expected_calibration_error")
    caveat = (
        f" Calibration error is {calibration_gap:.3f}; probabilities are not suitable "
        "for decision thresholds without recalibration."
        if isinstance(calibration_gap, (int, float)) and calibration_gap > 0.10
        else ""
    )
    return {
        "status": STATUS_SIGNAL,
        "reason": (
            f"ROC-AUC {roc_auc:.3f} and average precision {average_precision:.3f} beat "
            f"the no-skill prevalence {prevalence:.3f} on one temporal holdout."
            + caveat
        ),
    }


__all__ = [
    "STATUS_INSUFFICIENT",
    "STATUS_NO_SKILL",
    "STATUS_SIGNAL",
    "STATUS_WEAK",
    "binary_metrics",
    "bootstrap_confidence_intervals",
    "calibration_diagnostics",
    "event_threshold",
    "grade_skill",
    "label_target",
    "persistence_baseline",
    "select_threshold",
    "threshold_sweep",
    "two_by_two_association",
]

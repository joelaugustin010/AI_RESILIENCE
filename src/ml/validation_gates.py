"""Evidence-gated validation utilities for disaster ML research models.

These utilities quantify calibration and interval uncertainty and define a
strict promotion gate. They do not make a model operational by themselves:
independent spatial/temporal evidence and provenance must be supplied in the
model card before the gate can pass.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np


def binary_calibration_report(
    y_true: Sequence[int],
    probabilities: Sequence[float],
    *,
    n_bins: int = 10,
) -> dict[str, Any]:
    """Return Brier, base-rate reference, ECE and reliability-bin statistics."""
    y = np.asarray(y_true, dtype=float)
    p = np.asarray(probabilities, dtype=float)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p) or len(y) == 0:
        raise ValueError("y_true and probabilities must be non-empty, equal-length vectors.")
    if not np.all(np.isfinite(y)) or not np.all(np.isfinite(p)):
        raise ValueError("Calibration inputs must be finite.")
    if not np.all(np.isin(y, [0.0, 1.0])):
        raise ValueError("y_true must contain only binary 0/1 labels.")
    if np.any((p < 0.0) | (p > 1.0)):
        raise ValueError("Probabilities must lie in [0, 1].")
    if isinstance(n_bins, bool) or not isinstance(n_bins, int) or n_bins < 1:
        raise ValueError("n_bins must be a positive integer.")

    prevalence = float(np.mean(y))
    brier = float(np.mean((p - y) ** 2))
    base_rate_brier = float(np.mean((prevalence - y) ** 2))
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins: list[dict[str, float | int]] = []
    ece = 0.0
    for index in range(n_bins):
        lower, upper = float(edges[index]), float(edges[index + 1])
        mask = (p >= lower) & ((p <= upper) if index == n_bins - 1 else (p < upper))
        count = int(np.sum(mask))
        if not count:
            continue
        mean_probability = float(np.mean(p[mask]))
        observed_rate = float(np.mean(y[mask]))
        gap = abs(mean_probability - observed_rate)
        ece += (count / len(y)) * gap
        bins.append({
            "lower": lower,
            "upper": upper,
            "n": count,
            "mean_probability": mean_probability,
            "observed_rate": observed_rate,
            "absolute_gap": gap,
        })
    return {
        "n": int(len(y)),
        "event_count": int(np.sum(y)),
        "prevalence": prevalence,
        "brier_score": brier,
        "base_rate_brier_score": base_rate_brier,
        "brier_skill_over_base_rate": (
            float(1.0 - brier / base_rate_brier) if base_rate_brier > 0 else None
        ),
        "expected_calibration_error": float(ece),
        "reliability_bins": bins,
        "interpretation": (
            "Descriptive calibration on the supplied evaluation sample only; "
            "not proof of future, spatial, or operational calibration."
        ),
    }


def split_conformal_interval(
    y_calibration: Sequence[float],
    prediction_calibration: Sequence[float],
    prediction_test: Sequence[float],
    *,
    alpha: float = 0.10,
) -> dict[str, Any]:
    """Build distribution-free split-conformal intervals from held-out residuals.

    Calibration and test rows must be independent of model fitting and of each
    other under the exchangeability assumption. Time-series use requires
    dependence-aware blocks or another justified design; iid exchangeability
    must not be assumed for disaster time series.
    """
    y = np.asarray(y_calibration, dtype=float)
    p_cal = np.asarray(prediction_calibration, dtype=float)
    p_test = np.asarray(prediction_test, dtype=float)
    if y.ndim != 1 or p_cal.ndim != 1 or p_test.ndim != 1:
        raise ValueError("Conformal inputs must be one-dimensional.")
    if len(y) == 0 or len(y) != len(p_cal) or len(p_test) == 0:
        raise ValueError("Calibration vectors must be non-empty and equal length; test predictions non-empty.")
    if not all(np.all(np.isfinite(a)) for a in (y, p_cal, p_test)):
        raise ValueError("Conformal inputs must be finite.")
    if not math.isfinite(alpha) or not 0.0 < alpha < 1.0:
        raise ValueError("alpha must lie strictly between 0 and 1.")

    residuals = np.abs(y - p_cal)
    rank = int(math.ceil((len(residuals) + 1) * (1.0 - alpha)))
    if rank > len(residuals):
        quantile = math.inf
    else:
        quantile = float(np.partition(residuals, rank - 1)[rank - 1])
    lower = p_test - quantile
    upper = p_test + quantile
    return {
        "alpha": float(alpha),
        "nominal_coverage": float(1.0 - alpha),
        "calibration_n": int(len(residuals)),
        "absolute_residual_quantile": quantile,
        "lower": lower.tolist(),
        "upper": upper.tolist(),
        "finite_interval": bool(math.isfinite(quantile)),
        "assumption": (
            "Exchangeability of calibration and future residuals. For temporal, "
            "storm-clustered, or spatially dependent data, use blocked/clustered "
            "calibration and validate coverage on separate groups."
        ),
    }


def model_card_validation_gate(card: Mapping[str, Any]) -> dict[str, Any]:
    """Classify evidence maturity without promoting weak cards to operational use."""
    model_id = str(card.get("model_id") or "unknown")
    status = str(card.get("status") or "UNKNOWN")
    validation_status = str(card.get("validation_status") or "UNKNOWN")
    metrics = card.get("metrics") if isinstance(card.get("metrics"), Mapping) else {}
    limitations = list(card.get("limitations", []))
    reasons: list[str] = []

    if status in {"NO_SKILL", "INSUFFICIENT_TEST_EVENTS", "EXPLORATORY_ASSOCIATION"}:
        reasons.append(f"Model status {status} is not eligible for operational use.")
    if validation_status != "INDEPENDENT_VALIDATION_PASSED":
        reasons.append("Independent validation status has not passed.")
    independent = card.get("independent_validation")
    if not isinstance(independent, Mapping):
        independent = {}
        reasons.append("No independent_validation evidence block is recorded.")
    required_true = (
        "temporal_holdouts_passed",
        "spatial_holdouts_passed",
        "calibration_passed",
        "baseline_skill_passed",
        "provenance_complete",
        "domain_transfer_passed",
    )
    for key in required_true:
        if independent.get(key) is not True:
            reasons.append(f"Independent validation requirement {key!r} is not passed.")
    if int(independent.get("independent_test_events", 0) or 0) < 100:
        reasons.append("Fewer than 100 independently held-out positive events are documented.")
    if not metrics:
        reasons.append("No evaluation metrics are recorded.")
    return {
        "model_id": model_id,
        "current_status": status,
        "validation_status": validation_status,
        "operational_eligible": not reasons,
        "readiness": "OPERATIONAL_GATE_PASSED" if not reasons else "RESEARCH_ONLY",
        "blocking_reasons": reasons,
        "limitations": limitations,
        "policy": (
            "This gate is intentionally conservative. Passing it is necessary but "
            "not sufficient: domain-owner review, prospective shadow monitoring, "
            "and deployment safety approval are still required."
        ),
    }


def registry_validation_summary(cards: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarise the strict gate across all supplied model cards."""
    results = [model_card_validation_gate(card) for card in cards]
    return {
        "model_count": len(results),
        "operational_eligible_count": sum(bool(item["operational_eligible"]) for item in results),
        "research_only_count": sum(not item["operational_eligible"] for item in results),
        "models": results,
        "interpretation": (
            "Model count and trained artifacts do not imply operational validity. "
            "Each model must pass independent spatial and temporal validation."
        ),
    }


__all__ = [
    "binary_calibration_report",
    "model_card_validation_gate",
    "registry_validation_summary",
    "split_conformal_interval",
]

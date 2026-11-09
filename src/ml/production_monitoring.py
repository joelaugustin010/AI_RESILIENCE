"""Distribution drift, freshness, latency and fail-safe monitoring.

Thresholds are caller-supplied deployment policy, not universal defaults.
The module never emits warnings or promotes a model.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import ks_2samp


def population_stability_index(reference: Sequence[float], current: Sequence[float],
                               bins: int = 10) -> float:
    ref, cur = np.asarray(reference, dtype=float), np.asarray(current, dtype=float)
    if ref.ndim != 1 or cur.ndim != 1 or len(ref) < 2 or len(cur) < 2:
        raise ValueError("PSI requires two one-dimensional samples with at least two values.")
    if not np.all(np.isfinite(ref)) or not np.all(np.isfinite(cur)):
        raise ValueError("Drift samples must be finite.")
    if bins < 2:
        raise ValueError("bins must be at least 2.")
    edges = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0 if np.array_equal(np.sort(ref), np.sort(cur)) else float("inf")
    edges[0], edges[-1] = -np.inf, np.inf
    a, _ = np.histogram(ref, bins=edges)
    b, _ = np.histogram(cur, bins=edges)
    pa, pb = np.clip(a / len(ref), 1e-6, None), np.clip(b / len(cur), 1e-6, None)
    return float(np.sum((pb - pa) * np.log(pb / pa)))


def evaluate_production_health(
    reference_features: Mapping[str, Sequence[float]],
    current_features: Mapping[str, Sequence[float]],
    latency_ms: Sequence[float],
    *,
    data_age_minutes: float,
    max_data_age_minutes: float,
    out_of_domain_rate: float,
    max_out_of_domain_rate: float,
    inference_failure_rate: float,
    max_inference_failure_rate: float,
    max_p95_latency_ms: float,
    psi_fallback_threshold: float = 0.20,
    ks_pvalue_threshold: float = 0.01,
) -> dict[str, Any]:
    """Return metrics and deterministic fallback signal; no automated actions."""
    numeric = (data_age_minutes, max_data_age_minutes, out_of_domain_rate,
               max_out_of_domain_rate, inference_failure_rate,
               max_inference_failure_rate, max_p95_latency_ms,
               psi_fallback_threshold, ks_pvalue_threshold)
    if any(not np.isfinite(v) or v < 0 for v in numeric):
        raise ValueError("Monitoring values and thresholds must be finite and non-negative.")
    if max_data_age_minutes <= 0 or max_p95_latency_ms <= 0:
        raise ValueError("Freshness and latency budgets must be positive.")
    if not reference_features or set(reference_features) != set(current_features):
        raise ValueError("Reference/current feature names must match and be non-empty.")
    latency = np.asarray(latency_ms, dtype=float)
    if latency.ndim != 1 or not len(latency) or not np.all(np.isfinite(latency)) or np.any(latency < 0):
        raise ValueError("Latency samples must be finite, non-negative and non-empty.")
    drift, reasons = {}, []
    for name in sorted(reference_features):
        ref, cur = np.asarray(reference_features[name], dtype=float), np.asarray(current_features[name], dtype=float)
        if ref.ndim != 1 or cur.ndim != 1 or len(ref) < 2 or len(cur) < 2:
            raise ValueError(f"Feature {name!r} requires at least two values in each sample.")
        if not np.all(np.isfinite(ref)) or not np.all(np.isfinite(cur)):
            raise ValueError(f"Feature {name!r} contains non-finite values.")
        ks = ks_2samp(ref, cur, alternative="two-sided", method="auto")
        psi = population_stability_index(ref, cur)
        drift[name] = {"ks_statistic": float(ks.statistic), "ks_pvalue": float(ks.pvalue), "psi": psi}
        if psi >= psi_fallback_threshold:
            reasons.append(f"{name}: PSI {psi:.4f} reached configured threshold.")
        if float(ks.pvalue) < ks_pvalue_threshold:
            reasons.append(f"{name}: KS p-value {float(ks.pvalue):.6g} crossed configured threshold.")
    p95 = float(np.percentile(latency, 95))
    if data_age_minutes > max_data_age_minutes:
        reasons.append("Input data exceeded configured freshness budget.")
    if out_of_domain_rate > max_out_of_domain_rate:
        reasons.append("Out-of-domain input rate exceeded configured budget.")
    if inference_failure_rate > max_inference_failure_rate:
        reasons.append("Inference failure rate exceeded configured budget.")
    if p95 > max_p95_latency_ms:
        reasons.append("P95 inference latency exceeded configured budget.")
    return {
        "feature_drift": drift, "data_age_minutes": float(data_age_minutes),
        "p95_latency_ms": p95, "out_of_domain_rate": float(out_of_domain_rate),
        "inference_failure_rate": float(inference_failure_rate),
        "fallback_required": bool(reasons),
        "action": "DETERMINISTIC_SCREENING_ONLY" if reasons else "RESEARCH_MONITORING_CONTINUES",
        "automated_warning_authorized": False,
        "rollback_note": "Deployment controller must perform and verify rollback separately.",
        "reasons": reasons,
    }

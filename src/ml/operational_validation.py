"""Spatial/event holdout evaluation for frozen disaster-model predictions."""
from __future__ import annotations

from typing import Any, Mapping, Sequence
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from src.ml.validation_gates import binary_calibration_report

FIELDS = ("partition", "region_id", "event_id", "y_true", "model_probability", "baseline_probability")

def _vectors(rows: Sequence[Mapping[str, Any]]):
    missing = [k for k in FIELDS if any(k not in r for r in rows)]
    if missing:
        raise ValueError(f"Missing required fields: {sorted(set(missing))}")
    y = np.asarray([int(r["y_true"]) for r in rows], dtype=int)
    p = np.asarray([float(r["model_probability"]) for r in rows], dtype=float)
    b = np.asarray([float(r["baseline_probability"]) for r in rows], dtype=float)
    if not len(y) or not np.isin(y, [0, 1]).all():
        raise ValueError("y_true must be non-empty binary labels.")
    if not np.isfinite(p).all() or not np.isfinite(b).all() or ((p < 0) | (p > 1)).any() or ((b < 0) | (b > 1)).any():
        raise ValueError("Probabilities must be finite and in [0, 1].")
    return y, p, b

def _metrics(y, p, threshold=0.5):
    predicted = p >= threshold
    tp = int(np.sum(predicted & (y == 1)))
    fp = int(np.sum(predicted & (y == 0)))
    fn = int(np.sum((~predicted) & (y == 1)))
    tn = int(np.sum((~predicted) & (y == 0)))
    return {
        "n": int(len(y)), "positive_rows": int(y.sum()),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, np.clip(p, 1e-8, 1-1e-8), labels=[0, 1])),
        "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None,
        "threshold": float(threshold),
        "precision": float(tp/(tp+fp)) if tp+fp else None,
        "recall": float(tp/(tp+fn)) if tp+fn else None,
        "false_positive_rate": float(fp/(fp+tn)) if fp+tn else None,
    }

def _bootstrap(y, p, b, events, iterations=1000, seed=20261107):
    groups = np.unique(events)
    if len(groups) < 2:
        return {"status": "INSUFFICIENT_INDEPENDENT_EVENTS", "groups": int(len(groups)), "ci95": None}
    indexes = {g: np.flatnonzero(events == g) for g in groups}
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(iterations):
        chosen = rng.choice(groups, size=len(groups), replace=True)
        ix = np.concatenate([indexes[g] for g in chosen])
        base = float(np.mean((b[ix] - y[ix]) ** 2))
        if base > 0:
            scores.append(1 - float(np.mean((p[ix] - y[ix]) ** 2)) / base)
    return {
        "status": "EVENT_CLUSTER_BOOTSTRAP", "groups": int(len(groups)),
        "ci95": [float(np.quantile(scores, .025)), float(np.quantile(scores, .975))] if scores else None,
    }

def evaluate_independent_spatial_holdout(
    rows: Sequence[Mapping[str, Any]], *, bootstrap_iterations: int = 1000, threshold: float = 0.5
):
    if not 0 < threshold < 1:
        raise ValueError("threshold must lie strictly between 0 and 1.")
    cal = [r for r in rows if str(r.get("partition", "")).lower() == "calibration"]
    test = [r for r in rows if str(r.get("partition", "")).lower() == "test"]
    if not cal or not test:
        raise ValueError("Both calibration and test partitions are required.")
    yc, pc, _ = _vectors(cal)
    yt, pt, bt = _vectors(test)
    cr = {str(r["region_id"]) for r in cal}
    tr = {str(r["region_id"]) for r in test}
    ce = {str(r["event_id"]) for r in cal}
    te = {str(r["event_id"]) for r in test}
    if cr & tr:
        raise ValueError(f"Geographic leakage: {sorted(cr & tr)}")
    if ce & te:
        raise ValueError(f"Event leakage: {sorted(ce & te)}")
    if any(not x for x in cr | tr | ce | te):
        raise ValueError("Region and event identifiers must be non-empty.")
    if len(np.unique(yc)) != 2:
        raise ValueError("Calibration partition needs both classes.")

    raw = _metrics(yt, pt, threshold)
    baseline = _metrics(yt, bt, threshold)
    calibrated = {}
    clipped = np.clip(pc, 1e-6, 1-1e-6)
    platt = LogisticRegression(random_state=0).fit(np.log(clipped/(1-clipped)).reshape(-1, 1), yc)
    z = np.clip(pt, 1e-6, 1-1e-6)
    pp = platt.predict_proba(np.log(z/(1-z)).reshape(-1, 1))[:, 1]
    calibrated["platt"] = _metrics(yt, pp, threshold)
    calibrated["platt"]["reliability"] = binary_calibration_report(yt, pp)
    if len(yc) >= 100:
        iso = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip").fit(pc, yc)
        ip = iso.predict(pt)
        calibrated["isotonic"] = _metrics(yt, ip, threshold)
        calibrated["isotonic"]["reliability"] = binary_calibration_report(yt, ip)
    else:
        calibrated["isotonic"] = {"status": "NOT_FIT", "reason": "At least 100 independent calibration rows required."}

    regions = np.asarray([str(r["region_id"]) for r in test])
    events = np.asarray([str(r["event_id"]) for r in test])
    per_region = {
        k: {"n": int((regions == k).sum()),
            "model": _metrics(yt[regions == k], pt[regions == k], threshold),
            "baseline": _metrics(yt[regions == k], bt[regions == k], threshold)}
        for k in sorted(set(regions))
    }
    worst = max(per_region, key=lambda k: per_region[k]["model"]["brier"])
    boot = _bootstrap(yt, pt, bt, events, bootstrap_iterations)
    skill = 1 - raw["brier"] / baseline["brier"] if baseline["brier"] > 0 else None
    ci = boot.get("ci95")
    positives = len(set(events[yt == 1]))
    screen = (len(per_region) >= 3 and positives >= 30 and skill is not None
              and skill > 0 and ci is not None and ci[0] > 0)
    return {
        "evaluation_type": "FROZEN_PREDICTIONS_SPATIAL_AND_EVENT_HOLDOUT",
        "calibration_rows": len(cal), "test": raw,
        "raw_reliability": binary_calibration_report(yt, pt),
        "baseline": baseline, "raw_brier_skill": skill,
        "calibration_methods": calibrated, "geographic_groups": len(per_region),
        "independent_positive_events": positives, "per_region": per_region,
        "worst_brier_region": worst, "event_cluster_bootstrap": boot,
        "candidate_review_screen_passed": bool(screen),
        "operational_clearance": False,
        "threshold_policy": "Threshold is externally pre-registered; this script does not optimise it on test data.",
        "interpretation": "Frozen prediction evaluation only. Reliability bins are descriptive on this holdout; prospective shadow testing and hazard-owner approval remain mandatory.",
    }

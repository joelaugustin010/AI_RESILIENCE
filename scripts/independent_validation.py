"""Independent spatial holdout, calibration, and prospective shadow audit.

This tool evaluates supplied, adjudicated observations only. It never creates
labels, treats synthetic rows as ground truth, or promotes a model to operational
status. CSV contract: split, spatial_group, event_id, y_true, probability.
Allowed split values: train, calibration, test. The test geography must be
disjoint from both development partitions.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score


REQUIRED = {"split", "spatial_group", "event_id", "y_true", "probability"}


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {sorted(missing)}")
        rows = []
        for line, raw in enumerate(reader, start=2):
            try:
                y = int(raw["y_true"])
                p = float(raw["probability"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid label/probability on CSV line {line}") from exc
            if y not in (0, 1) or not math.isfinite(p) or not 0 <= p <= 1:
                raise ValueError(f"Out-of-range label/probability on CSV line {line}")
            row = {**raw, "y_true": y, "probability": p}
            for key in ("split", "spatial_group", "event_id"):
                row[key] = str(row[key]).strip()
                if not row[key]:
                    raise ValueError(f"Blank {key} on CSV line {line}")
            if row["split"] not in {"train", "calibration", "test"}:
                raise ValueError(f"Unknown split {row['split']!r} on CSV line {line}")
            rows.append(row)
    if not rows:
        raise ValueError("No observations supplied.")
    return rows


def validate_partitions(rows: list[dict[str, Any]]) -> dict[str, int]:
    groups: dict[str, set[str]] = {name: set() for name in ("train", "calibration", "test")}
    event_splits: dict[str, set[str]] = {}
    for row in rows:
        groups[row["split"]].add(row["spatial_group"])
        event_splits.setdefault(row["event_id"], set()).add(row["split"])
    for left, right in (("train", "calibration"), ("train", "test"), ("calibration", "test")):
        overlap = groups[left] & groups[right]
        if overlap:
            raise ValueError(f"Spatial leakage: {left}/{right} share groups {sorted(overlap)}")
    crossing = sorted(event for event, splits in event_splits.items() if len(splits) > 1)
    if crossing:
        raise ValueError(f"Event leakage across partitions: {crossing[:10]}")
    counts = {name: sum(r["split"] == name for r in rows) for name in groups}
    if not counts["calibration"] or not counts["test"]:
        raise ValueError("Independent calibration and test partitions are both required.")
    return counts


def _metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float | int | None]:
    clipped = np.clip(p, 1e-7, 1 - 1e-7)
    prevalence = float(np.mean(y))
    brier = float(np.mean((p - y) ** 2))
    base_brier = float(np.mean((prevalence - y) ** 2))
    return {
        "n": int(len(y)),
        "events": int(y.sum()),
        "prevalence": prevalence,
        "brier": brier,
        "base_rate_brier": base_brier,
        "brier_skill_vs_base_rate": float(1 - brier / base_brier) if base_brier else None,
        "log_loss": float(log_loss(y, clipped, labels=[0, 1])),
        "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else None,
    }


def reliability_bins(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict[str, float | int]]:
    edges = np.linspace(0, 1, bins + 1)
    result = []
    for i in range(bins):
        mask = (p >= edges[i]) & ((p <= edges[i + 1]) if i == bins - 1 else (p < edges[i + 1]))
        if mask.any():
            result.append({
                "lower": float(edges[i]), "upper": float(edges[i + 1]),
                "n": int(mask.sum()), "mean_probability": float(p[mask].mean()),
                "observed_frequency": float(y[mask].mean()),
            })
    return result


def _cluster_bootstrap(y: np.ndarray, p: np.ndarray, events: np.ndarray, *,
                       iterations: int = 1000, seed: int = 20261107) -> dict[str, Any]:
    unique = np.unique(events)
    if len(unique) < 2:
        return {"clusters": int(len(unique)), "iterations": 0,
                "brier_95_ci": None, "reason": "At least two independent event clusters are required."}
    rng = np.random.default_rng(seed)
    event_indices = {event: np.flatnonzero(events == event) for event in unique}
    scores = []
    for _ in range(iterations):
        sampled = rng.choice(unique, size=len(unique), replace=True)
        idx = np.concatenate([event_indices[event] for event in sampled])
        scores.append(float(np.mean((p[idx] - y[idx]) ** 2)))
    low, high = np.quantile(scores, [0.025, 0.975])
    return {"clusters": int(len(unique)), "iterations": iterations,
            "brier_95_ci": [float(low), float(high)],
            "method": "percentile bootstrap resampling whole event clusters"}


def fit_calibrator(method: str, y_cal: np.ndarray, p_cal: np.ndarray):
    if len(np.unique(y_cal)) != 2 or int(y_cal.sum()) < 20 or int((1-y_cal).sum()) < 20:
        raise ValueError("Calibration withheld: require at least 20 positives and 20 negatives.")
    if method == "platt":
        eps = 1e-6
        logits = np.log(np.clip(p_cal, eps, 1-eps) / (1-np.clip(p_cal, eps, 1-eps))).reshape(-1, 1)
        model = LogisticRegression(random_state=0, solver="lbfgs")
        model.fit(logits, y_cal)
        return lambda values: model.predict_proba(
            np.log(np.clip(values, eps, 1-eps) / (1-np.clip(values, eps, 1-eps))).reshape(-1, 1)
        )[:, 1]
    if method == "isotonic":
        if len(y_cal) < 100:
            raise ValueError("Isotonic calibration withheld: require at least 100 calibration observations.")
        model = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
        model.fit(p_cal, y_cal)
        return lambda values: model.predict(values)
    raise ValueError(f"Unsupported calibration method: {method}")


def evaluate(rows: list[dict[str, Any]], method: str = "none") -> dict[str, Any]:
    counts = validate_partitions(rows)
    cal = [r for r in rows if r["split"] == "calibration"]
    test = [r for r in rows if r["split"] == "test"]
    y_cal = np.asarray([r["y_true"] for r in cal], dtype=int)
    p_cal = np.asarray([r["probability"] for r in cal], dtype=float)
    y = np.asarray([r["y_true"] for r in test], dtype=int)
    p = np.asarray([r["probability"] for r in test], dtype=float)
    calibration_status = "not_requested"
    if method != "none":
        calibrator = fit_calibrator(method, y_cal, p_cal)
        p = np.asarray(calibrator(p), dtype=float)
        calibration_status = f"{method}_fit_on_calibration_partition_only"
    events = np.asarray([r["event_id"] for r in test])
    groups = np.asarray([r["spatial_group"] for r in test])
    worst = []
    for group in sorted(np.unique(groups)):
        mask = groups == group
        worst.append({"spatial_group": str(group), **_metrics(y[mask], p[mask])})
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "independent spatial holdout evaluation of supplied observations; not operational clearance",
        "partition_rows": counts,
        "spatial_groups": {name: sorted({r["spatial_group"] for r in rows if r["split"] == name})
                           for name in ("train", "calibration", "test")},
        "calibration": {"method": method, "status": calibration_status,
                        "metrics_on_independent_test": _metrics(y, p),
                        "reliability_bins": reliability_bins(y, p)},
        "worst_location": worst,
        "event_cluster_uncertainty": _cluster_bootstrap(y, p, events),
        "clearance": {"operational": False,
                      "reason": "This tool does not establish prospective validity, source adjudication, warning authority, or operational safety."},
    }


def append_shadow_record(path: str | Path, record: dict[str, Any]) -> None:
    """Append an immutable shadow observation; this function never triggers action."""
    required = {"issued_at_utc", "data_as_of_utc", "model_id", "model_version",
                "location_id", "prediction", "input_status"}
    missing = required - set(record)
    if missing:
        raise ValueError(f"Missing shadow fields: {sorted(missing)}")
    issued = datetime.fromisoformat(str(record["issued_at_utc"]).replace("Z", "+00:00"))
    as_of = datetime.fromisoformat(str(record["data_as_of_utc"]).replace("Z", "+00:00"))
    if issued.tzinfo is None or as_of.tzinfo is None:
        raise ValueError("Shadow timestamps must include a timezone.")
    prediction = record["prediction"]
    if not isinstance(prediction, (int, float)) or not math.isfinite(prediction) or not 0 <= prediction <= 1:
        raise ValueError("Shadow prediction must be a finite probability in [0, 1].")
    payload = {**record, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
               "mode": "shadow_only_no_alerts_no_automated_actions"}
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Adjudicated CSV with the documented schema.")
    parser.add_argument("--output", required=True, help="JSON report output path.")
    parser.add_argument("--calibration", choices=("none", "platt", "isotonic"), default="none")
    args = parser.parse_args()
    report = evaluate(load_rows(args.input), args.calibration)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output, "clearance": report["clearance"],
                      "test_metrics": report["calibration"]["metrics_on_independent_test"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

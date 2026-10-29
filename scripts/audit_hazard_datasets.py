"""Audit local hazard datasets without pretending an event catalogue is a trained model.

Usage:
  python scripts/audit_hazard_datasets.py --data-dir data/external/hazards
CSV filenames should be <hazard_id>.csv. This script reports readiness only.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd

REGISTRY = Path("data/external/hazard_dataset_registry.json")
REQUIRED_LABEL_COLUMNS = ("target",)
GROUP_CANDIDATES = ("event_id", "storm_id", "year", "station_id", "location_id", "group_id")
TIME_CANDIDATES = ("timestamp", "time", "date", "datetime", "valid_time")

def audit_csv(path: Path) -> dict:
    result = {"file": str(path), "status": "NOT_READY", "issues": [], "rows": 0}
    try:
        frame = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        result["issues"].append(f"Could not read CSV: {type(exc).__name__}: {exc}")
        return result
    result["rows"] = int(len(frame))
    result["columns"] = list(frame.columns)
    if len(frame) < 100:
        result["issues"].append("Fewer than 100 rows; justify sample size before modelling.")
    target = next((c for c in REQUIRED_LABEL_COLUMNS if c in frame.columns), None)
    if target is None:
        result["issues"].append("No explicit 'target' label column; event records alone are not supervised training labels.")
    elif frame[target].nunique(dropna=True) < 2:
        result["issues"].append("Target has fewer than two non-null classes.")
    elif frame[target].isna().any():
        result["issues"].append("Target has missing labels; resolve or explicitly exclude them.")
    else:
        result["target_classes"] = int(frame[target].nunique())
    group = next((c for c in GROUP_CANDIDATES if c in frame.columns), None)
    if group is None:
        result["issues"].append("No event/storm/station/location grouping column found for leakage-safe validation.")
    else:
        result["group_column"] = group
        result["groups"] = int(frame[group].nunique(dropna=True))
        if result["groups"] < 5:
            result["issues"].append("Fewer than five independent groups; group-held-out evaluation is unreliable.")
    time_col = next((c for c in TIME_CANDIDATES if c in frame.columns), None)
    if time_col is None:
        result["issues"].append("No recognized time column; temporal leakage cannot be audited.")
    else:
        result["time_column"] = time_col
    predictors = [c for c in frame.columns if c not in {target, group, time_col} and not c.lower().endswith(("_id", "_url"))]
    if len(predictors) < 2:
        result["issues"].append("Fewer than two candidate predictor columns.")
    result["candidate_predictors"] = predictors
    if not result["issues"]:
        result["status"] = "CANDIDATE_READY_FOR_REVIEW"
        result["issues"].append("Human review still required: feature availability time, units, licence, target definition, class balance, and geographic relevance.")
    return result

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/external/hazards"))
    parser.add_argument("--output", type=Path, default=Path("reports/hazard_dataset_readiness.json"))
    args = parser.parse_args()
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    audits = []
    for hazard in registry["hazards"]:
        path = args.data_dir / f'{hazard["id"]}.csv'
        audits.append({"hazard_id": hazard["id"], "label": hazard["label"],
                       "source": hazard["source"], "source_url": hazard["url"],
                       "exists": path.is_file(),
                       "audit": audit_csv(path) if path.is_file() else {
                           "status": "MISSING_DATA", "issues": ["No local dataset file found; no model trained."]}})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {"status": "READINESS_AUDIT_ONLY", "trained_models": 0,
              "warning": "This report does not claim any model is trained or scientifically validated.",
              "hazards": audits}
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "hazards": len(audits),
                      "datasets_present": sum(x["exists"] for x in audits),
                      "candidate_ready": sum(x["audit"]["status"] == "CANDIDATE_READY_FOR_REVIEW" for x in audits),
                      "trained_models": 0}, indent=2))
    return 0
if __name__ == "__main__":
    raise SystemExit(main())

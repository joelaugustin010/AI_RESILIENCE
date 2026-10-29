"""Train one hazard-specific research baseline from a curated, labelled CSV.

The script refuses to run unless the dataset has target, timestamp and a grouping
column. Evaluation holds out entire groups, reducing event/location leakage.
This is not suitable for operational warnings without domain review.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

GROUP_COLUMNS = ("event_id", "storm_id", "station_id", "location_id", "group_id")
TIME_COLUMNS = ("timestamp", "time", "date", "datetime", "valid_time")

def train(csv_path: Path, hazard: str, output_dir: Path) -> dict:
    df = pd.read_csv(csv_path, low_memory=False)
    if "target" not in df:
        raise ValueError("Dataset must contain an explicit 'target' label column.")
    group_col = next((c for c in GROUP_COLUMNS if c in df), None)
    time_col = next((c for c in TIME_COLUMNS if c in df), None)
    if group_col is None or time_col is None:
        raise ValueError(f"Require a group column from {GROUP_COLUMNS} and a time column from {TIME_COLUMNS}.")
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce", utc=True)
    df = df.dropna(subset=["target", group_col, time_col]).copy()
    if len(df) < 100 or df["target"].nunique() < 2 or df[group_col].nunique() < 5:
        raise ValueError("Insufficient data: require >=100 rows, >=2 target classes and >=5 groups.")
    # Never treat identifiers or the target/time/group as predictors.
    excluded = {"target", group_col, time_col}
    features = [c for c in df.columns if c not in excluded and not c.lower().endswith(("_id", "_url"))]
    numeric = [c for c in features if pd.api.types.is_numeric_dtype(df[c])]
    categorical = [c for c in features if c not in numeric]
    if len(features) < 2:
        raise ValueError("At least two predictor columns are required.")
    X, y, groups = df[features], df["target"], df[group_col]
    split = GroupShuffleSplit(n_splits=1, test_size=.25, random_state=42)
    train_i, test_i = next(split.split(X, y, groups))
    transformers = []
    if numeric:
        transformers.append(("num", SimpleImputer(strategy="median"), numeric))
    if categorical:
        transformers.append(("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                                              ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical))
    model = Pipeline([("prep", ColumnTransformer(transformers)),
                      ("rf", RandomForestClassifier(n_estimators=400, min_samples_leaf=5,
                                                    class_weight="balanced_subsample",
                                                    random_state=42, n_jobs=-1))])
    model.fit(X.iloc[train_i], y.iloc[train_i])
    pred = model.predict(X.iloc[test_i])
    report = {
        "status": "RESEARCH_BASELINE_TRAINED_NOT_VALIDATED",
        "hazard": hazard, "dataset": str(csv_path),
        "target": "target", "time_column": time_col, "group_column": group_col,
        "rows": int(len(df)), "groups": int(groups.nunique()),
        "train_rows": int(len(train_i)), "test_rows": int(len(test_i)),
        "train_groups": int(groups.iloc[train_i].nunique()),
        "test_groups": int(groups.iloc[test_i].nunique()),
        "features": features,
        "metrics": {
            "accuracy": float(accuracy_score(y.iloc[test_i], pred)),
            "balanced_accuracy": float(balanced_accuracy_score(y.iloc[test_i], pred)),
            "precision_weighted": float(precision_score(y.iloc[test_i], pred, average="weighted", zero_division=0)),
            "recall_weighted": float(recall_score(y.iloc[test_i], pred, average="weighted", zero_division=0)),
            "f1_weighted": float(f1_score(y.iloc[test_i], pred, average="weighted", zero_division=0))
        },
        "limitations": [
            "Single group-held-out split is preliminary; perform repeated/time-based validation.",
            "Feature availability time, source licence, label validity, class balance, calibration and geographic relevance require review.",
            "Do not use for emergency warnings or claim local predictive validity without independent validation."
        ]
    }
    # ROC-AUC only for binary targets and only if both classes appear in test set.
    if y.nunique() == 2 and pd.Series(y.iloc[test_i]).nunique() == 2:
        probs = model.predict_proba(X.iloc[test_i])[:, 1]
        try:
            report["metrics"]["roc_auc_binary"] = float(roc_auc_score(y.iloc[test_i], probs))
        except ValueError:
            pass
    output_dir.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump(model, output_dir / f"{hazard}_research_baseline.joblib")
    (output_dir / f"{hazard}_evaluation.json").write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--hazard", required=True)
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, default=Path("models/hazards"))
    args = p.parse_args()
    print(json.dumps(train(args.csv, args.hazard, args.output_dir), indent=2))
if __name__ == "__main__":
    main()

"""Train a research baseline for flood-event danger-level exceedance.

Required local files (from the project's public hydrology acquisition bundle):
  data/external/raw/floodevents_indofloods.csv
  data/external/raw/precipitation_variables_indofloods.csv
  data/external/raw/metadata_indofloods.csv
  data/external/raw/catchment_characteristics_indofloods.csv

This predicts severity among recorded flood events only. It does NOT predict
whether/when a flood will occur, and is NOT an operational or Kochi-validated
warning model. See reports/flood_event_severity_baseline.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, confusion_matrix, f1_score,
    precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


PRECIPITATION_FEATURES = [f"T{i}d" for i in range(1, 11)]
NUMERIC_CATCHMENT_FEATURES = [
    "Drainage Area", "Catchment Relief", "Catchment Length",
    "Catchment Perimeter", "Sinuosity Index", "Form Factor", "Relief Ratio",
    "Elongation Ratio", "Circularity Ratio", "Drainage Density",
    "Ruggedness Number", "Annual Precipitation", "Precipitation Seasonality",
    "Population Density", "Urban percentage", "Road Density",
]
CATEGORICAL_CATCHMENT_FEATURES = [
    "Land cover", "Soil type", "lithology type", "KoppenGeiger Climate Type",
]


def load_training_table(raw_dir: Path) -> pd.DataFrame:
    events = pd.read_csv(raw_dir / "floodevents_indofloods.csv")
    precipitation = pd.read_csv(raw_dir / "precipitation_variables_indofloods.csv")
    metadata = pd.read_csv(raw_dir / "metadata_indofloods.csv")
    catchment = pd.read_csv(raw_dir / "catchment_characteristics_indofloods.csv")

    # Event IDs encode the same gauge identifier used in the other tables.
    events["GaugeID"] = events["EventID"].astype(str).str.extract(
        r"(INDOFLOODS-gauge-\\d+)-"
    )
    if events["GaugeID"].isna().any():
        raise ValueError("Some flood event IDs do not contain a recognized gauge ID.")

    table = events.merge(
        precipitation, on="EventID", how="left", validate="one_to_one"
    ).merge(
        metadata[["GaugeID", "Warning Level", "Danger Level", "Station", "State"]],
        on="GaugeID", how="left", validate="many_to_one",
    ).merge(
        catchment, on="GaugeID", how="left", validate="many_to_one",
        suffixes=("", "_catchment"),
    )

    required = ["Peak Flood Level (m)", "Danger Level"]
    table = table.dropna(subset=required).copy()
    table["target_danger_exceed"] = (
        table["Peak Flood Level (m)"] >= table["Danger Level"]
    ).astype(int)
    if table["target_danger_exceed"].nunique() != 2:
        raise ValueError("Training labels contain only one class after data quality filtering.")
    return table


def train(raw_dir: Path, model_path: Path, report_path: Path) -> dict:
    table = load_training_table(raw_dir)
    categorical = [c for c in CATEGORICAL_CATCHMENT_FEATURES if c in table.columns]
    numeric = [
        c for c in PRECIPITATION_FEATURES + NUMERIC_CATCHMENT_FEATURES
        if c in table.columns
    ]
    features = numeric + categorical
    if len(features) < 10:
        raise ValueError(f"Expected at least 10 usable features, found {len(features)}.")

    X = table[features]
    y = table["target_danger_exceed"]
    groups = table["GaugeID"]
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))

    transformers = [
        ("numeric", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric),
    ]
    if categorical:
        transformers.append((
            "categorical",
            Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("onehot", OneHotEncoder(handle_unknown="ignore")),
            ]),
            categorical,
        ))
    preprocessing = ColumnTransformer(transformers, remainder="drop")
    pipeline = Pipeline([
        ("preprocess", preprocessing),
        ("classifier", RandomForestClassifier(
            n_estimators=400, min_samples_leaf=5,
            class_weight="balanced_subsample", random_state=42,
            n_jobs=-1, max_features="sqrt",
        )),
    ])
    pipeline.fit(X.iloc[train_idx], y.iloc[train_idx])
    prediction = pipeline.predict(X.iloc[test_idx])
    probability = pipeline.predict_proba(X.iloc[test_idx])[:, 1]
    baseline_class = int(y.iloc[train_idx].mean() >= 0.5)
    baseline = [baseline_class] * len(test_idx)
    tn, fp, fn, tp = confusion_matrix(y.iloc[test_idx], prediction, labels=[0, 1]).ravel()

    report = {
        "status": "RESEARCH_BASELINE_TRAINED",
        "target": "Peak Flood Level (m) >= gauge-specific Danger Level",
        "interpretation": "Danger-level exceedance among already-recorded flood events only.",
        "dataset": {
            "name": "INDOFLOODS event, precipitation, metadata and catchment tables",
            "doi": "10.5281/zenodo.14584654",
            "url": "https://zenodo.org/records/14584655",
            "rows_after_required_label_join": int(len(table)),
            "unique_gauges": int(groups.nunique()),
            "positive_events": int(y.sum()),
            "positive_rate": float(y.mean()),
        },
        "validation": {
            "method": "One deterministic 75/25 GroupShuffleSplit by gauge; test gauges are unseen in training.",
            "random_state": 42,
            "train_rows": int(len(train_idx)),
            "test_rows": int(len(test_idx)),
            "train_gauges": int(groups.iloc[train_idx].nunique()),
            "test_gauges": int(groups.iloc[test_idx].nunique()),
            "test_positive_rate": float(y.iloc[test_idx].mean()),
        },
        "features": features,
        "model": {
            "type": "scikit-learn RandomForestClassifier",
            "n_estimators": 400,
            "min_samples_leaf": 5,
            "class_weight": "balanced_subsample",
            "random_state": 42,
        },
        "test_metrics": {
            "accuracy": float(accuracy_score(y.iloc[test_idx], prediction)),
            "balanced_accuracy": float(balanced_accuracy_score(y.iloc[test_idx], prediction)),
            "precision": float(precision_score(y.iloc[test_idx], prediction, zero_division=0)),
            "recall": float(recall_score(y.iloc[test_idx], prediction, zero_division=0)),
            "f1": float(f1_score(y.iloc[test_idx], prediction, zero_division=0)),
            "roc_auc": float(roc_auc_score(y.iloc[test_idx], probability)),
            "confusion_matrix_tn_fp_fn_tp": [int(tn), int(fp), int(fn), int(tp)],
        },
        "majority_baseline": {
            "accuracy": float(accuracy_score(y.iloc[test_idx], baseline)),
            "balanced_accuracy": float(balanced_accuracy_score(y.iloc[test_idx], baseline)),
        },
        "limitations": [
            "This is not a flood occurrence probability model: the dataset contains recorded flood events, not matched non-flood periods.",
            "The records span multiple Indian gauges; this does not establish Kochi or Ernakulam validity.",
            "Gauge-group holdout is useful but only one split; uncertainty intervals, repeated grouped validation, calibration, and independent external validation remain undone.",
            "The model must not issue public warnings or replace IMD, CWC, KSDMA or local-authority guidance.",
        ],
    }

    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "features": features, "target": report["target"]}, model_path, compress=3)
    report_path.write_text(json.dumps(report, indent=2) + "\\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/external/raw"))
    parser.add_argument("--model-out", type=Path, default=Path("models/flood_event_severity_baseline.joblib"))
    parser.add_argument("--report-out", type=Path, default=Path("reports/flood_event_severity_baseline.json"))
    args = parser.parse_args()
    print(json.dumps(train(args.raw_dir, args.model_out, args.report_out), indent=2))


if __name__ == "__main__":
    main()

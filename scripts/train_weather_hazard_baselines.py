"""Train cautious next-day weather-extreme research baselines from archived daily weather.

Only two targets are created: next-day high temperature and next-day extreme rainfall.
Thresholds are estimated on the training period only. This is not an official heatwave,
flood, cyclone, or emergency-warning model.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, balanced_accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline

ROOT = Path("data/external/hazards/raw/weather")
LOCATIONS = ("kochi", "kottayam", "wayanad", "thiruvananthapuram")
TRAIN_END = "2020-01-01"
OUT = Path("models/hazards/weather_baselines")
REPORT = Path("reports/weather_hazard_training.json")

def load_weather() -> pd.DataFrame:
    frames = []
    for loc in LOCATIONS:
        path = ROOT / f"{loc}_daily_weather_2000_2025.json"
        if not path.exists():
            print(f"[SKIP] Missing {path}")
            continue
        obj = json.loads(path.read_text(encoding="utf-8"))
        daily = pd.DataFrame(obj["daily"])
        daily["date"] = pd.to_datetime(daily["time"], errors="coerce")
        daily["location"] = loc
        for col in ("temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                    "wind_speed_10m_max", "wind_gusts_10m_max"):
            daily[col] = pd.to_numeric(daily[col], errors="coerce")
        frames.append(daily.drop(columns=["time"]))
    if len(frames) < 2:
        raise RuntimeError("Need at least two location weather files for a research baseline.")
    df = pd.concat(frames, ignore_index=True).sort_values(["location", "date"])
    return df

def make_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    day = out["date"].dt.dayofyear
    out["doy_sin"] = np.sin(2 * np.pi * day / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * day / 365.25)
    out["year"] = out["date"].dt.year
    for col in ("temperature_2m_max", "temperature_2m_min", "precipitation_sum",
                "wind_speed_10m_max", "wind_gusts_10m_max"):
        grouped = out.groupby("location", sort=False)[col]
        for lag in (1, 2, 3, 7):
            out[f"{col}_lag{lag}"] = grouped.shift(lag)
        out[f"{col}_prior7_mean"] = grouped.transform(lambda s: s.shift(1).rolling(7, min_periods=4).mean())
    # Forecast next day's event from today's and earlier observations only.
    out["target_temperature_nextday"] = out.groupby("location")["temperature_2m_max"].shift(-1)
    out["target_rain_nextday"] = out.groupby("location")["precipitation_sum"].shift(-1)
    out["target_date"] = out["date"] + pd.Timedelta(days=1)
    return out

def fit_target(df: pd.DataFrame, target_col: str, source_target: str, hazard: str) -> dict:
    train_period = df["date"] < pd.Timestamp(TRAIN_END)
    train_values = df.loc[train_period, source_target].dropna()
    if len(train_values) < 100:
        raise RuntimeError(f"Insufficient pre-2020 observations for {hazard}")
    threshold = float(train_values.quantile(0.95))
    data = df.dropna(subset=[target_col, "target_date"]).copy()
    data["target"] = (data[target_col] >= threshold).astype(int)
    # Strict temporal evaluation: no rows whose target date falls before the 2020 cutoff
    # may enter the test set, and training examples' target dates must precede the cutoff.
    cutoff = pd.Timestamp(TRAIN_END)
    train = data[data["target_date"] < cutoff].copy()
    test = data[data["target_date"] >= cutoff].copy()
    feature_cols = [c for c in data.columns if c.endswith(("_lag1", "_lag2", "_lag3", "_lag7", "_prior7_mean"))]
    feature_cols += ["doy_sin", "doy_cos", "year"]
    feature_cols = [c for c in feature_cols if c in data.columns]
    train = train.dropna(subset=feature_cols)
    test = test.dropna(subset=feature_cols)
    if len(train) < 1000 or len(test) < 1000 or train["target"].nunique() < 2:
        raise RuntimeError(f"Insufficient usable train/test data or class diversity for {hazard}: train={len(train)}, test={len(test)}")
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("rf", RandomForestClassifier(n_estimators=300, min_samples_leaf=10,
                                      class_weight="balanced_subsample", random_state=42, n_jobs=-1)),
    ])
    model.fit(train[feature_cols], train["target"])
    pred = model.predict(test[feature_cols])
    prob = model.predict_proba(test[feature_cols])[:, list(model.named_steps["rf"].classes_).index(1)]
    prevalence = float(train["target"].mean())
    baseline = np.full(len(test), int(prevalence >= 0.5), dtype=int)
    metrics = {
        "accuracy": float(accuracy_score(test["target"], pred)),
        "balanced_accuracy": float(balanced_accuracy_score(test["target"], pred)),
        "precision": float(precision_score(test["target"], pred, zero_division=0)),
        "recall": float(recall_score(test["target"], pred, zero_division=0)),
        "f1": float(f1_score(test["target"], pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(test["target"], prob)) if test["target"].nunique() == 2 else None,
        "majority_baseline_accuracy": float(accuracy_score(test["target"], baseline)),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    import joblib
    joblib.dump(model, OUT / f"{hazard}_nextday_research.joblib")
    report = {
        "status": "RESEARCH_BASELINE_TRAINED_NOT_VALIDATED",
        "hazard": hazard, "target_definition": f"next-day {source_target} >= training-period 95th percentile",
        "threshold": threshold, "threshold_units": "°C" if "temperature" in source_target else "mm/day",
        "threshold_training_period": f"2000-01-01 through 2019-12-31",
        "train_target_dates_before": TRAIN_END, "test_target_dates_from": TRAIN_END,
        "locations": sorted(data["location"].unique().tolist()),
        "train_rows": int(len(train)), "test_rows": int(len(test)),
        "train_positive_rate": prevalence, "test_positive_rate": float(test["target"].mean()),
        "features": feature_cols, "metrics": metrics,
        "limitations": [
            "Historical reanalysis/grid-point data are not station observations.",
            "Only four Kerala locations; performance may not generalize outside these grid points.",
            "The 95th-percentile threshold is a research event definition, not an IMD heatwave or official extreme-rainfall warning definition.",
            "A single future-period holdout is preliminary; assess calibration, drift and independent station data before any real-world use.",
            "Not an emergency-warning or scientifically approved operational model."
        ]
    }
    (OUT / f"{hazard}_evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report

def main() -> None:
    base = make_features(load_weather())
    reports = []
    errors = {}
    for hazard, target, source in (
        ("high_temperature", "target_temperature_nextday", "temperature_2m_max"),
        ("extreme_rainfall", "target_rain_nextday", "precipitation_sum"),
    ):
        try:
            reports.append(fit_target(base, target, source, hazard))
            print(f"[OK] Trained {hazard}")
        except Exception as exc:
            errors[hazard] = f"{type(exc).__name__}: {exc}"
            print(f"[BLOCKED] {hazard}: {errors[hazard]}")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    summary = {"status": "PARTIAL_RESEARCH_TRAINING", "trained": [r["hazard"] for r in reports],
               "blocked": errors, "models": reports,
               "not_trained": ["earthquake", "cyclone", "landslide", "drought", "wildfire", "tsunami", "air_pollution"],
               "reason": "Raw catalogs or incomplete labels are not sufficient for honest supervised prediction; do not fabricate negatives or targets."}
    REPORT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"trained": summary["trained"], "blocked": errors}, indent=2))
    if not reports:
        raise SystemExit(1)

if __name__ == "__main__":
    main()

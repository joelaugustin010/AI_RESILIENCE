"""Train and evaluate a cautious next-day rainfall regression research baseline.

The prediction is for the next calendar day's precipitation total, using only
observations from completed days before the prediction day. This is retrospective
research on archived gridded/reanalysis data, not an operational forecast.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline

DEFAULT_INPUT = Path("data/external/hazards/raw/weather")
DEFAULT_OUTPUT = Path("models/hazards/rainfall_regression")
LOCATIONS = ("kochi", "kottayam", "wayanad", "thiruvananthapuram")
TRAIN_END = pd.Timestamp("2015-01-01")
TEST_START = pd.Timestamp("2020-01-01")
WEATHER_COLUMNS = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
)


def load_daily_weather(input_dir: Path, locations: Iterable[str] = LOCATIONS) -> pd.DataFrame:
    """Load archived daily weather while rejecting duplicate or malformed dates."""
    frames: list[pd.DataFrame] = []
    for location in locations:
        path = input_dir / f"{location}_daily_weather_2000_2025.json"
        if not path.is_file():
            print(f"[SKIP] Missing {path}")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("daily"), dict):
            raise ValueError(f"Unexpected daily weather schema: {path}")
        daily = pd.DataFrame(payload["daily"])
        if "time" not in daily:
            raise ValueError(f"Missing daily.time in {path}")
        daily["date"] = pd.to_datetime(daily.pop("time"), errors="coerce")
        if daily["date"].isna().any():
            raise ValueError(f"Unparseable dates in {path}")
        if daily["date"].duplicated().any():
            raise ValueError(f"Duplicate dates in {path}")
        missing = sorted(set(WEATHER_COLUMNS) - set(daily.columns))
        if missing:
            raise ValueError(f"Missing weather columns in {path}: {missing}")
        for column in WEATHER_COLUMNS:
            daily[column] = pd.to_numeric(daily[column], errors="coerce")
        daily["location"] = location
        frames.append(daily[["date", "location", *WEATHER_COLUMNS]])
    if not frames:
        raise RuntimeError("No weather files were found; no model was trained.")
    return pd.concat(frames, ignore_index=True).sort_values(["location", "date"])


def build_supervised_frame(daily: pd.DataFrame) -> pd.DataFrame:
    """Create next-day targets from lagged, prior-day observations only.

    Reindexing to a daily calendar ensures a missing day cannot silently become
    the previous day's lag. Rows without a complete seven-day history are dropped.
    """
    required = {"date", "location", *WEATHER_COLUMNS}
    missing = required - set(daily.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    frames: list[pd.DataFrame] = []
    for location, group in daily.groupby("location", sort=True):
        group = group.sort_values("date").copy()
        if group["date"].duplicated().any():
            raise ValueError(f"Duplicate dates for {location}")
        indexed = group.set_index("date")[list(WEATHER_COLUMNS)]
        calendar = pd.date_range(indexed.index.min(), indexed.index.max(), freq="D")
        indexed = indexed.reindex(calendar)
        indexed.index.name = "feature_date"
        out = pd.DataFrame(index=calendar)
        out["location"] = location
        for column in WEATHER_COLUMNS:
            for lag in (1, 2, 3, 7):
                out[f"{column}_lag{lag}"] = indexed[column].shift(lag)
            out[f"{column}_prior7_mean"] = indexed[column].shift(1).rolling(7, min_periods=7).mean()
        out["target_date"] = out.index + pd.Timedelta(days=1)
        day = out["target_date"].dt.dayofyear
        out["target_doy_sin"] = np.sin(2 * np.pi * day / 365.25)
        out["target_doy_cos"] = np.cos(2 * np.pi * day / 365.25)
        out["target_year"] = out["target_date"].dt.year
        out["target_month"] = out["target_date"].dt.month
        out["target_rain_mm"] = indexed["precipitation_sum"].shift(-1).to_numpy()
        frames.append(out.reset_index(names="feature_date"))
    result = pd.concat(frames, ignore_index=True)
    feature_columns = [
        column for column in result.columns
        if column.endswith(("_lag1", "_lag2", "_lag3", "_lag7", "_prior7_mean"))
    ] + ["target_doy_sin", "target_doy_cos", "target_year", "target_month"]
    result = result.dropna(subset=[*feature_columns, "target_rain_mm"]).copy()
    result = result[np.isfinite(result["target_rain_mm"]) & (result["target_rain_mm"] >= 0)]
    return result.sort_values(["target_date", "location"]).reset_index(drop=True)


def make_model(kind: str) -> Pipeline:
    if kind == "random_forest":
        estimator = RandomForestRegressor(
            n_estimators=300, min_samples_leaf=3, max_features=0.8,
            random_state=42, n_jobs=-1,
        )
    elif kind == "extra_trees":
        estimator = ExtraTreesRegressor(
            n_estimators=300, min_samples_leaf=3, max_features=0.8,
            random_state=42, n_jobs=-1,
        )
    else:
        raise ValueError(f"Unsupported model: {kind}")
    return Pipeline([("imputer", SimpleImputer(strategy="median")), ("regressor", estimator)])


def regression_metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    return {
        "rows": int(len(actual)),
        "mae_mm": float(mean_absolute_error(actual, predicted)),
        "rmse_mm": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mean_observed_mm": float(actual.mean()),
    }


def evaluate(input_dir: Path = DEFAULT_INPUT, output_dir: Path = DEFAULT_OUTPUT) -> dict:
    raw = load_daily_weather(input_dir)
    data = build_supervised_frame(raw)
    feature_columns = [
        column for column in data.columns
        if column.endswith(("_lag1", "_lag2", "_lag3", "_lag7", "_prior7_mean"))
    ] + ["target_doy_sin", "target_doy_cos", "target_year", "target_month"]
    train = data[data["target_date"] < TRAIN_END]
    validation = data[(data["target_date"] >= TRAIN_END) & (data["target_date"] < TEST_START)]
    final_train = data[data["target_date"] < TEST_START]
    test = data[data["target_date"] >= TEST_START]
    if min(len(train), len(validation), len(final_train), len(test)) < 500:
        raise RuntimeError(
            f"Insufficient chronological data: train={len(train)}, "
            f"validation={len(validation)}, final_train={len(final_train)}, test={len(test)}"
        )
    if test["target_date"].min() < TEST_START:
        raise AssertionError("Test period overlaps the training period.")

    candidates = []
    for kind in ("random_forest", "extra_trees"):
        candidate = make_model(kind)
        candidate.fit(train[feature_columns], train["target_rain_mm"])
        prediction = np.maximum(0, candidate.predict(validation[feature_columns]))
        candidates.append({
            "model_type": kind,
            "validation": regression_metrics(validation["target_rain_mm"], prediction),
        })
    selected = min(candidates, key=lambda item: item["validation"]["mae_mm"])
    model = make_model(selected["model_type"])
    model.fit(final_train[feature_columns], final_train["target_rain_mm"])
    prediction = np.maximum(0, model.predict(test[feature_columns]))

    # Both baselines use no information from the test outcomes.
    persistence = test["precipitation_sum_lag1"].to_numpy(dtype=float)
    monthly = final_train.groupby("target_month")["target_rain_mm"].median()
    climatology = test["target_month"].map(monthly).to_numpy(dtype=float)
    metrics = {
        "selected_model": regression_metrics(test["target_rain_mm"], prediction),
        "persistence_baseline": regression_metrics(test["target_rain_mm"], persistence),
        "training_monthly_median_baseline": regression_metrics(test["target_rain_mm"], climatology),
    }
    model_mae = metrics["selected_model"]["mae_mm"]
    for baseline_name in ("persistence_baseline", "training_monthly_median_baseline"):
        baseline_mae = metrics[baseline_name]["mae_mm"]
        metrics[baseline_name]["mae_skill_vs_baseline"] = (
            float(1 - model_mae / baseline_mae) if baseline_mae > 0 else None
        )

    per_location = {}
    for location, subset in test.assign(prediction=prediction).groupby("location"):
        per_location[location] = regression_metrics(
            subset["target_rain_mm"], subset["prediction"].to_numpy()
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / "nextday_rainfall_research.joblib")
    report = {
        "status": "RESEARCH_BASELINE_TRAINED_NOT_VALIDATED",
        "target": "Next calendar day's gridded/reanalysis precipitation total (mm)",
        "forecast_information_cutoff": "End of the feature_date; only observations through feature_date minus one day are used",
        "training_target_dates_before": str(TRAIN_END.date()),
        "validation_target_dates": f"{TRAIN_END.date()} through {(TEST_START - pd.Timedelta(days=1)).date()}",
        "test_target_dates_from": str(TEST_START.date()),
        "selected_model": selected["model_type"],
        "candidate_validation_results": candidates,
        "metrics": metrics,
        "test_metrics_by_location": per_location,
        "rows": {"train": len(train), "validation": len(validation), "final_train": len(final_train), "test": len(test)},
        "locations": sorted(data["location"].unique().tolist()),
        "features": feature_columns,
        "limitations": [
            "Archived gridded/reanalysis values are not station observations or an operational numerical-weather-prediction forecast.",
            "The model is a retrospective research baseline; availability of the completed prior-day data at a real forecast issue time is not established.",
            "Four Kerala grid-point locations do not establish transfer to all of Kochi, Ernakulam, or other places.",
            "A single chronological holdout does not establish long-term stability, calibration, or independent station validity.",
            "Rainfall errors are location- and event-dependent; aggregate metrics can conceal local failures.",
            "This is not a flood prediction, flood probability, water-depth estimate, or emergency warning.",
        ],
    }
    (output_dir / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = evaluate(args.input_dir, args.output_dir)
    print(json.dumps({
        "status": report["status"],
        "selected_model": report["selected_model"],
        "metrics": report["metrics"],
        "test_metrics_by_location": report["test_metrics_by_location"],
    }, indent=2))


if __name__ == "__main__":
    main()

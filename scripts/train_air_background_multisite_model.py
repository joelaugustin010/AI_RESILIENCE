"""Train a location-aware model for CAMS/Open-Meteo atmospheric background PM2.5.

This is a background-pattern model only. It is not trained on incident releases,
station observations, smoke plumes, volcanic ash, or disaster labels.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "external" / "air_quality" / "open_meteo_cams_kerala_background_2024_2025_multisite.csv"
MODEL_DIR = ROOT / "models" / "air_quality"
MODEL = MODEL_DIR / "kerala_cams_pm25_next_hour_background.pkl"
REPORT = MODEL_DIR / "kerala_cams_pm25_next_hour_background.evaluation.json"


def make_table(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, list[str], pd.DataFrame]:
    frame = frame.copy()
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], utc=True, errors="coerce")
    frame = frame.sort_values(["location", "observed_at"]).drop_duplicates(["location", "observed_at"])
    frame["target_pm2_5_next_hour"] = frame.groupby("location")["pm2_5_ug_m3"].shift(-1)
    frame["hour_sin"] = np.sin(2 * np.pi * frame["observed_at"].dt.hour / 24)
    frame["hour_cos"] = np.cos(2 * np.pi * frame["observed_at"].dt.hour / 24)
    frame["wind_direction_sin"] = np.sin(np.deg2rad(frame["wind_direction_deg"]))
    frame["wind_direction_cos"] = np.cos(np.deg2rad(frame["wind_direction_deg"]))
    frame = pd.get_dummies(frame, columns=["location"], dtype=float)
    features = [
        "pm2_5_ug_m3", "pm10_ug_m3", "no2_ug_m3", "so2_ug_m3", "co_ug_m3", "o3_ug_m3",
        "temperature_c", "relative_humidity_pct", "wind_speed_kmh", "wind_direction_sin",
        "wind_direction_cos", "hour_sin", "hour_cos",
    ] + sorted(column for column in frame.columns if column.startswith("location_"))
    usable = frame.dropna(subset=features + ["target_pm2_5_next_hour"])
    return usable[features], usable["target_pm2_5_next_hour"], features, usable


def main() -> int:
    if not DATA.is_file():
        raise FileNotFoundError(f"Missing acquired dataset: {DATA}")
    source = pd.read_csv(DATA)
    X, y, features, usable = make_table(source)
    if len(X) < 30000:
        raise RuntimeError(f"Only {len(X)} usable rows; refusing to train a multisite model.")

    # All locations share timestamps, so this preserves a genuinely future test period.
    cutoff = usable["observed_at"].quantile(0.8)
    train_mask = usable["observed_at"] < cutoff
    test_mask = ~train_mask
    X_train, X_test = X.loc[train_mask], X.loc[test_mask]
    y_train, y_test = y.loc[train_mask], y.loc[test_mask]
    model = HistGradientBoostingRegressor(
        max_iter=350, learning_rate=0.05, max_leaf_nodes=31, l2_regularization=1.0, random_state=42
    )
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    naive = X_test["pm2_5_ug_m3"].to_numpy()
    metrics = {
        "model_mae_ug_m3": float(mean_absolute_error(y_test, predictions)),
        "model_rmse_ug_m3": float(np.sqrt(mean_squared_error(y_test, predictions))),
        "model_r2": float(r2_score(y_test, predictions)),
        "naive_previous_hour_mae_ug_m3": float(mean_absolute_error(y_test, naive)),
        "naive_previous_hour_rmse_ug_m3": float(np.sqrt(mean_squared_error(y_test, naive))),
    }
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    with MODEL.open("wb") as stream:
        pickle.dump({
            "model": model,
            "features": features,
            "target": "next-hour PM2.5 (µg/m³)",
            "locations": sorted(source["location"].unique().tolist()),
            "data_boundary": "CAMS/Open-Meteo modelled background only",
        }, stream)
    report = {
        "model_id": "kerala_cams_pm25_next_hour_background",
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_dataset": str(DATA.relative_to(ROOT)),
        "source_rows": int(len(source)), "usable_rows": int(len(X)),
        "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "locations": sorted(source["location"].unique().tolist()),
        "train_period": {"from": str(usable.loc[train_mask, "observed_at"].min()), "to": str(usable.loc[train_mask, "observed_at"].max())},
        "test_period": {"from": str(usable.loc[test_mask, "observed_at"].min()), "to": str(usable.loc[test_mask, "observed_at"].max())},
        "split": "timestamp-based chronological 80/20; no random shuffling; next-hour target grouped by location",
        "features": features, "target": "next-hour pm2_5_ug_m3",
        "algorithm": "HistGradientBoostingRegressor",
        "metrics": metrics,
        "scientific_boundary": "Surrogate for CAMS/Open-Meteo atmospheric-background values. Not trained on station observations, verified releases, plume measurements, volcanic ash, wildfire smoke, or cyclone incidents; not a disaster-plume predictor.",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"model": str(MODEL), "report": str(REPORT), "metrics": metrics}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

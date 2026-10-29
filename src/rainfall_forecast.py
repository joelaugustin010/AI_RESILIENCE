"""Chronological benchmark for the local manual hourly rainfall series.

This is a rainfall-measurement benchmark only. It has no flood outcome labels,
and it must not be interpreted as a flood forecast or an operational forecast.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from src.hydrology_analytics import HydrologyDataError, load_observations


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ID = "rainfall_manual"
TEST_FRACTION = 0.20
EMBARGO_DAYS = 7
RANDOM_STATE = 17


class RainfallForecastError(ValueError):
    """Raised when observations cannot support a fair historical benchmark."""


def _validated_frame(observations: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "station", "value"}
    missing = sorted(required - set(observations.columns))
    if missing:
        raise RainfallForecastError("Missing required column(s): " + ", ".join(missing))
    if observations.empty:
        raise RainfallForecastError("No rainfall observations were supplied.")

    frame = observations.loc[:, ["timestamp", "station", "value"]].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame["station"] = frame["station"].astype("string").str.strip()
    if frame["timestamp"].isna().any():
        raise RainfallForecastError("Invalid or missing timestamps must be reviewed before modeling.")
    if frame["timestamp"].dt.tz is not None:
        raise RainfallForecastError(
            "Timezone-aware timestamps are not supported until the source timezone is documented."
        )
    if frame["station"].isna().any() or frame["station"].eq("").any():
        raise RainfallForecastError("Missing station names must be reviewed before modeling.")
    if frame["value"].isna().any() or not np.isfinite(frame["value"].to_numpy(dtype=float)).all():
        raise RainfallForecastError("Missing or non-finite rainfall measurements must be reviewed.")
    if frame["value"].lt(0).any():
        raise RainfallForecastError("Negative rainfall measurements must be reviewed, not modeled.")
    if frame.duplicated(["station", "timestamp"]).any():
        raise RainfallForecastError(
            "Duplicate station-time rows are present. Resolve them with source evidence; this benchmark does not deduplicate."
        )
    return frame.sort_values(["station", "timestamp"], kind="stable").reset_index(drop=True)


def _make_features(pairs: pd.DataFrame) -> pd.DataFrame:
    month = pairs["timestamp"].dt.month.to_numpy(dtype=float)
    hour = pairs["timestamp"].dt.hour.to_numpy(dtype=float)
    day = pairs["timestamp"].dt.day_of_year.to_numpy(dtype=float)
    return pd.DataFrame(
        {
            "station": pairs["station"].astype(str).to_numpy(),
            "previous_hour_rainfall_mm": pairs["previous_value"].to_numpy(dtype=float),
            "hour_sin": np.sin(2 * np.pi * hour / 24.0),
            "hour_cos": np.cos(2 * np.pi * hour / 24.0),
            "day_of_year_sin": np.sin(2 * np.pi * day / 365.25),
            "day_of_year_cos": np.cos(2 * np.pi * day / 365.25),
        }
    )


def _scores(actual: pd.Series, predicted: pd.Series | np.ndarray) -> dict[str, float | int]:
    actual_values = actual.to_numpy(dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    return {
        "n": int(len(actual_values)),
        "mae_mm": float(mean_absolute_error(actual_values, predicted_values)),
        "rmse_mm": float(np.sqrt(mean_squared_error(actual_values, predicted_values))),
    }


def evaluate_hourly_rainfall(
    observations: pd.DataFrame,
    *,
    test_fraction: float = TEST_FRACTION,
    embargo_days: int = EMBARGO_DAYS,
) -> dict[str, Any]:
    """Compare a trained gradient-boosting candidate with simple baselines.

    The target is the next source record exactly one hour later, not an arbitrary
    accumulation period. A global timestamp cutoff keeps simultaneous station
    records on one side of the split. A temporal embargo separates training and
    test labels. Missing/irregular intervals are excluded, never interpolated.
    """
    if not 0.1 <= test_fraction <= 0.4:
        raise RainfallForecastError("test_fraction must be between 0.10 and 0.40.")
    if not isinstance(embargo_days, int) or embargo_days < 0:
        raise RainfallForecastError("embargo_days must be a non-negative whole number.")

    frame = _validated_frame(observations)
    timestamps = frame["timestamp"].drop_duplicates().sort_values().reset_index(drop=True)
    split_index = int(np.floor(len(timestamps) * (1.0 - test_fraction)))
    if split_index < 2 or split_index >= len(timestamps):
        raise RainfallForecastError("Not enough distinct timestamps for a chronological holdout.")
    test_start = pd.Timestamp(timestamps.iloc[split_index])
    train_end = test_start - pd.Timedelta(days=embargo_days)

    frame["previous_timestamp"] = frame.groupby("station", sort=False)["timestamp"].shift(1)
    frame["previous_value"] = frame.groupby("station", sort=False)["value"].shift(1)
    elapsed = frame["timestamp"] - frame["previous_timestamp"]
    one_hour = frame.loc[elapsed.eq(pd.Timedelta(hours=1))].copy()
    train_pairs = one_hour.loc[one_hour["timestamp"].lt(train_end)].copy()
    test_pairs = one_hour.loc[one_hour["timestamp"].ge(test_start)].copy()
    if len(train_pairs) < 20 or test_pairs.empty:
        raise RainfallForecastError(
            "Insufficient exact one-hour station pairs before/after the chronological split."
        )

    training_readings = frame.loc[frame["timestamp"].lt(train_end)]
    station_medians = training_readings.groupby("station")["value"].median()
    test_pairs["station_median_prediction"] = test_pairs["station"].map(station_medians)
    has_training_history = test_pairs["station_median_prediction"].notna()
    excluded_without_history = int((~has_training_history).sum())
    test_pairs = test_pairs.loc[has_training_history].copy()
    if test_pairs.empty:
        raise RainfallForecastError("No held-out station has readings before the training cutoff.")

    transformer = ColumnTransformer(
        [("station", OneHotEncoder(handle_unknown="ignore"), ["station"])],
        remainder="passthrough",
    )
    model = make_pipeline(
        transformer,
        GradientBoostingRegressor(
            loss="huber",
            learning_rate=0.05,
            n_estimators=100,
            max_depth=2,
            min_samples_leaf=50,
            random_state=RANDOM_STATE,
        ),
    )
    model.fit(_make_features(train_pairs), train_pairs["value"].to_numpy(dtype=float))

    predictions = test_pairs.loc[
        :, ["timestamp", "station", "previous_timestamp", "value", "previous_value", "station_median_prediction"]
    ].rename(columns={"value": "actual_mm", "previous_value": "persistence_prediction_mm"})
    predictions["model_prediction_mm"] = np.maximum(
        0.0, model.predict(_make_features(test_pairs))
    )

    metrics = {
        "persistence": _scores(predictions["actual_mm"], predictions["persistence_prediction_mm"]),
        "station_median": _scores(predictions["actual_mm"], predictions["station_median_prediction"]),
        "gradient_boosting": _scores(predictions["actual_mm"], predictions["model_prediction_mm"]),
    }
    per_station_rows: list[dict[str, Any]] = []
    for station, group in predictions.groupby("station", sort=True):
        station_result: dict[str, Any] = {"Station": station, "Test pairs": int(len(group))}
        for key, prediction_column in (
            ("Persistence", "persistence_prediction_mm"),
            ("Station median", "station_median_prediction"),
            ("Gradient boosting", "model_prediction_mm"),
        ):
            scores = _scores(group["actual_mm"], group[prediction_column])
            station_result[f"{key} MAE (mm)"] = scores["mae_mm"]
            station_result[f"{key} RMSE (mm)"] = scores["rmse_mm"]
        per_station_rows.append(station_result)

    zero_count = int(frame["value"].eq(0).sum())
    summary = {
        "dataset_id": DATASET_ID,
        "model_name": "GradientBoostingRegressor (100 shallow trees; 1-hour lag, station, hour/day seasonality)",
        "target": "Next source-recorded manual rainfall value exactly one hour after the previous station record (mm)",
        "test_fraction_of_unique_timestamps": test_fraction,
        "embargo_days": embargo_days,
        "train_end_exclusive": train_end.isoformat(sep=" "),
        "test_start": test_start.isoformat(sep=" "),
        "train_pairs": int(len(train_pairs)),
        "test_pairs": int(len(predictions)),
        "test_stations": int(predictions["station"].nunique()),
        "all_stations": int(frame["station"].nunique()),
        "test_period_start": predictions["timestamp"].min().isoformat(sep=" "),
        "test_period_end": predictions["timestamp"].max().isoformat(sep=" "),
        "excluded_test_pairs_without_training_history": excluded_without_history,
        "source_rows": int(len(frame)),
        "source_start": frame["timestamp"].min().isoformat(sep=" "),
        "source_end": frame["timestamp"].max().isoformat(sep=" "),
        "zero_value_rows": zero_count,
        "all_values_positive": zero_count == 0,
        "metrics": metrics,
    }
    return {
        "summary": summary,
        "metrics": metrics,
        "predictions": predictions.reset_index(drop=True),
        "per_station": pd.DataFrame(per_station_rows),
        "warnings": [
            "The local series contains no exact zero-rain values; dry-hour representation is unknown, so scores apply only to represented readings.",
            "Station-time event identifiers are absent. The chronological split and 7-day embargo prevent random time mixing, but cannot prove independent meteorological events.",
            "The source timezone is not documented. The 1-hour interval is measured from its stored timestamps without timezone conversion.",
            "The local series ends in 2014. This is a retrospective benchmark, not a current forecast, operational guidance, or flood forecast.",
            "No observed flood outcome labels are linked to these rainfall values; no flood risk, probability, or impact is estimated.",
        ],
    }


def run_manual_rainfall_backtest(root: str | Path = PROJECT_ROOT) -> dict[str, Any]:
    """Load the unmodified manual rainfall source and run its historical benchmark."""
    try:
        observations, qa = load_observations(DATASET_ID, root)
    except (HydrologyDataError, OSError) as exc:
        raise RainfallForecastError(str(exc)) from exc
    if qa["invalid_timestamp_rows"] or qa["invalid_measurement_rows"] or qa["missing_station_rows"]:
        raise RainfallForecastError("The source has invalid required fields; review them before modeling.")
    if qa["duplicate_station_time_groups"] or qa["conflicting_station_time_groups"]:
        raise RainfallForecastError(
            "The manual rainfall source contains duplicate station-time groups; the benchmark will not deduplicate them."
        )
    result = evaluate_hourly_rainfall(observations)
    result["source_qa"] = qa
    result["source_path"] = str(Path(root) / "data" / "raw" / "rainfall_manual_hr_kerala-sw_kl_1991_2020.csv")
    return result

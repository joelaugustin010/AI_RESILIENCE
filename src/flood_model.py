"""Fail-closed readiness checks and evaluation tools for flood classification.

The bundled five-row example is not eligible for training. This module only fits
a model after documented observations, labels, feature timing and event groups
pass the readiness checks. Test fixtures must opt into the explicit test-only
mode and must never be presented as real-world model evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "disaster_probability_data.csv"
METADATA_PATH = PROJECT_ROOT / "data" / "reference" / "disaster_probability_data.metadata.json"

TARGET = "target_flood_event_next_24h"
TIME_COLUMN = "observation_date"
EVENT_COLUMN = "event_group_id"
FEATURE_COLUMNS = (
    "antecedent_rainfall_3day_mm",
    "forecast_rainfall_24h_mm",
    "insat3d_ipwv_mm",
    "soil_moisture_percent",
    "slope_angle_deg",
    "river_gauge_height_m",
    "danger_level_m",
    "cwc_flood_warning_level",
)
NUMERIC_FEATURES = FEATURE_COLUMNS[:-1]
MIN_ROWS = 100
MIN_CLASS_ROWS = 20
MIN_CLASS_EVENTS = 10

LEAKAGE_REVIEW_COLUMNS = (
    "cwc_flood_warning_level",
    "river_gauge_height_m",
    "danger_level_m",
)
REQUIRED_METADATA = (
    "publisher",
    "source_url",
    "retrieved_on",
    "license",
    "geographic_coverage",
    "label_definition",
    "label_source",
    "label_review_status",
    "feature_availability_cutoff",
    "time_zone",
    "prediction_horizon_hours",
    "feature_source_map",
    "independent_source_families",
    "source_crosswalk_status",
    "observation_alignment_window_hours",
)


class FloodModelNotReady(ValueError):
    """Raised when an input dataset has not met the pre-training checks."""


def load_flood_data() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load the candidate CSV and optional provenance sidecar without fitting."""
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Flood dataset not found: {DATA_PATH}")
    frame = pd.read_csv(DATA_PATH, low_memory=False)
    if METADATA_PATH.is_file():
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
        expected_hash = metadata.get("raw_sha256")
        metadata["raw_hash_matches"] = (
            hashlib.sha256(DATA_PATH.read_bytes()).hexdigest() == expected_hash
            if expected_hash else None
        )
    else:
        metadata = {}
    return frame, metadata


def _chronological_event_split(
    frame: pd.DataFrame,
    time_column: str,
    event_column: str,
    test_fraction: float = 0.2,
) -> tuple[pd.Index, pd.Index, pd.Timestamp] | None:
    """Hold out the latest dates and remove all overlapping event groups from train."""
    times = pd.to_datetime(frame[time_column], errors="coerce", utc=True)
    if times.isna().any():
        return None
    unique_times = sorted(times.unique())
    if len(unique_times) < 5:
        return None
    cut_index = max(1, min(len(unique_times) - 1, int(len(unique_times) * (1 - test_fraction))))
    test_start = pd.Timestamp(unique_times[cut_index])
    test_mask = times >= test_start
    test_events = set(frame.loc[test_mask, event_column].astype(str))
    train_mask = (times < test_start) & ~frame[event_column].astype(str).isin(test_events)
    train_index = frame.index[train_mask]
    test_index = frame.index[test_mask]
    if train_index.empty or test_index.empty:
        return None
    return train_index, test_index, test_start


def audit_flood_dataset(
    frame: pd.DataFrame,
    metadata: dict[str, Any] | None = None,
    *,
    allow_synthetic_test_fixture: bool = False,
) -> dict[str, Any]:
    """Summarize data quality and report whether evaluation is allowed.

    Prototype screening floors (100 rows, 20/class, 10 event groups/class) are
    engineering gates, not a claim that meeting them establishes scientific
    validity or production readiness.
    """
    metadata = metadata or {}
    required = set(FEATURE_COLUMNS) | {TARGET, TIME_COLUMN}
    event_column = str(metadata.get("event_group_column") or EVENT_COLUMN)
    missing_columns = sorted(required - set(frame.columns))
    blockers: list[str] = []
    warnings: list[str] = []

    if missing_columns:
        blockers.append("Missing required columns: " + ", ".join(missing_columns))

    target_counts: dict[str, int] = {}
    class_event_counts: dict[str, int] = {}
    date_min = date_max = None
    distinct_dates = 0
    invalid_timestamps = None
    missing_values: dict[str, int] = {}
    exact_duplicates = int(frame.duplicated().sum()) if not frame.empty else 0
    rows = int(len(frame))

    if not frame.empty:
        missing_values = {str(k): int(v) for k, v in frame.isna().sum().items() if v}
    if TARGET in frame:
        target = frame[TARGET]
        target_counts = {str(key): int(value) for key, value in target.value_counts(dropna=False).items()}
        valid_labels = set(target.dropna().unique()).issubset({0, 1, False, True})
        if target.isna().any():
            blockers.append("The outcome label contains missing values.")
        if not valid_labels:
            blockers.append("The outcome must use only binary labels 0 and 1.")
        if target.nunique(dropna=True) < 2:
            blockers.append("Both flood and no-flood labels are required.")
        for label in (0, 1):
            class_count = int(target.eq(label).sum())
            if class_count < MIN_CLASS_ROWS:
                blockers.append(f"Class {label} has {class_count} rows; at least {MIN_CLASS_ROWS} are required for the prototype screen.")
    else:
        blockers.append(f"Missing target column: {TARGET}.")

    if rows < MIN_ROWS:
        blockers.append(f"Only {rows} rows are available; at least {MIN_ROWS} are required for the prototype screen.")
    if exact_duplicates:
        blockers.append(f"Found {exact_duplicates} exact duplicate row(s); review them before evaluation.")
    if metadata.get("raw_hash_matches") is False:
        blockers.append("The CSV hash does not match its reviewed metadata sidecar.")

    if TIME_COLUMN in frame:
        parsed = pd.to_datetime(frame[TIME_COLUMN], errors="coerce", utc=True)
        invalid_timestamps = int(parsed.isna().sum())
        if invalid_timestamps:
            blockers.append(f"{invalid_timestamps} timestamp(s) are invalid or missing.")
        valid_times = parsed.dropna()
        if not valid_times.empty:
            date_min = valid_times.min().date().isoformat()
            date_max = valid_times.max().date().isoformat()
            distinct_dates = int(valid_times.nunique())
        if distinct_dates < 5:
            blockers.append(f"Only {distinct_dates} distinct observation date(s); at least 5 are required for chronological evaluation.")

    if event_column not in frame:
        blockers.append(f"Missing event-group column '{event_column}'; related observations cannot be kept together across the evaluation split.")
    elif frame[event_column].isna().any():
        blockers.append("Event-group identifiers contain missing values.")
    elif TARGET in frame:
        class_event_counts = {
            str(label): int(frame.loc[frame[TARGET].eq(label), event_column].nunique())
            for label in (0, 1)
        }
        for label in (0, 1):
            count = class_event_counts[str(label)]
            if count < MIN_CLASS_EVENTS:
                blockers.append(f"Class {label} has only {count} distinct event group(s); at least {MIN_CLASS_EVENTS} are required.")

    if not missing_columns:
        for column in NUMERIC_FEATURES:
            values = pd.to_numeric(frame[column], errors="coerce")
            bad = int((frame[column].notna() & values.isna()).sum())
            nonfinite = int((values.notna() & ~np.isfinite(values)).sum())
            if bad or nonfinite:
                blockers.append(f"Feature '{column}' contains {bad} non-numeric and {nonfinite} non-finite value(s).")
        for column, low, high in (
            ("antecedent_rainfall_3day_mm", 0, None),
            ("forecast_rainfall_24h_mm", 0, None),
            ("insat3d_ipwv_mm", 0, None),
            ("soil_moisture_percent", 0, 100),
            ("slope_angle_deg", 0, 90),
        ):
            values = pd.to_numeric(frame[column], errors="coerce")
            outside = values.notna() & ((values < low) | ((values > high) if high is not None else False))
            if outside.any():
                blockers.append(f"Feature '{column}' has {int(outside.sum())} value(s) outside its documented basic range.")

    data_kind = metadata.get("data_kind")
    test_fixture = data_kind == "synthetic_test_fixture"
    if test_fixture:
        if not allow_synthetic_test_fixture:
            blockers.append("Synthetic test fixtures are never eligible for user-facing model evaluation.")
        else:
            warnings.append("Synthetic fixture mode: any fitted model and metrics are test plumbing only, not real-world evidence.")
    else:
        for key in REQUIRED_METADATA:
            value = metadata.get(key)
            if value is None or not str(value).strip() or str(value).strip().casefold() in {
                "unknown", "not documented", "not stated", "n/a", "none"
            }:
                blockers.append(f"Missing provenance/label metadata: {key}.")
        if data_kind != "verified_observations":
            blockers.append("Dataset is not documented as verified real observations.")
        if metadata.get("label_review_status") != "independently_verified":
            blockers.append("Target labels have not been independently verified.")
        if metadata.get("prediction_horizon_hours") != 24:
            blockers.append("The target must be documented as a 24-hour prediction horizon.")

        # Multi-source condition: each predictor must have traceable provenance,
        # and a single dataset/source family must not masquerade as an ensemble.
        source_map = metadata.get("feature_source_map")
        if not isinstance(source_map, dict):
            blockers.append("Feature provenance must map every model feature to a source ID.")
        else:
            unmapped_features = sorted(set(FEATURE_COLUMNS) - set(source_map))
            if unmapped_features:
                blockers.append("Feature provenance is missing: " + ", ".join(unmapped_features) + ".")
            unmapped_sources = [
                feature for feature in FEATURE_COLUMNS
                if feature in source_map and not str(source_map[feature]).strip()
            ]
            if unmapped_sources:
                blockers.append("Feature provenance contains blank source IDs for: " + ", ".join(unmapped_sources) + ".")

        source_families = metadata.get("independent_source_families")
        if not isinstance(source_families, list):
            blockers.append("Independent source families must be documented as a list.")
        else:
            normalized_families = {
                str(family).strip().casefold() for family in source_families if str(family).strip()
            }
            if len(normalized_families) < 3:
                blockers.append(
                    f"Only {len(normalized_families)} independent source families are documented; at least 3 are required."
                )
        if metadata.get("source_crosswalk_status") != "independently_verified":
            blockers.append("The crosswalk linking model features to independent source records is not independently verified.")
        try:
            alignment_window = float(metadata.get("observation_alignment_window_hours"))
        except (TypeError, ValueError):
            alignment_window = 0.0
        if not np.isfinite(alignment_window) or alignment_window <= 0 or alignment_window > 24:
            blockers.append("Observation alignment window must be documented, positive, and no greater than 24 hours.")

    for column in LEAKAGE_REVIEW_COLUMNS:
        if column in frame and not metadata.get("feature_availability_cutoff"):
            blockers.append(f"Potential leakage: timing for '{column}' relative to prediction issue time is undocumented.")

    if not missing_columns and event_column in frame and TIME_COLUMN in frame and not frame.empty:
        split = _chronological_event_split(frame, TIME_COLUMN, event_column)
        if split is None:
            blockers.append("A chronological, event-separated train/test split cannot be formed.")
        elif TARGET in frame:
            train_index, test_index, _ = split
            for subset_name, indices in (("training", train_index), ("test", test_index)):
                labels = set(frame.loc[indices, TARGET].dropna().astype(int))
                if labels != {0, 1}:
                    blockers.append(f"The chronological {subset_name} subset does not contain both outcome classes.")
    elif distinct_dates and distinct_dates < 5:
        # A single date cannot establish a time-held-out evaluation.
        pass

    if missing_values:
        warnings.append("Some values are missing; the candidate pipeline can impute feature values, but missing labels or event IDs block evaluation.")
    if exact_duplicates:
        warnings.append("Exact duplicate rows were found and have not been removed.")
    if any(column in frame for column in LEAKAGE_REVIEW_COLUMNS):
        warnings.append("Warning/gauge features require documented availability times to rule out target leakage.")

    return {
        "ready": not blockers,
        "rows": rows,
        "feature_count": sum(column in frame for column in FEATURE_COLUMNS),
        "target_counts": target_counts,
        "class_event_counts": class_event_counts,
        "missing_values": missing_values,
        "exact_duplicates": exact_duplicates,
        "date_min": date_min,
        "date_max": date_max,
        "distinct_dates": distinct_dates,
        "invalid_timestamps": invalid_timestamps,
        "event_group_column": event_column,
        "blockers": blockers,
        "warnings": warnings,
        "screening_floors": {
            "rows": MIN_ROWS,
            "rows_per_class": MIN_CLASS_ROWS,
            "event_groups_per_class": MIN_CLASS_EVENTS,
        },
    }


def build_flood_pipeline(frame: pd.DataFrame, classifier: Any | None = None) -> Pipeline:
    """Create a leakage-conscious logistic-regression classifier pipeline."""
    numeric = [column for column in NUMERIC_FEATURES if column in frame]
    categorical = ["cwc_flood_warning_level"] if "cwc_flood_warning_level" in frame else []
    preprocessing = ColumnTransformer(
        [
            ("numeric", Pipeline([
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]), numeric),
            ("categorical", Pipeline([
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore")),
            ]), categorical),
        ],
        remainder="drop",
    )
    return Pipeline([
        ("preprocessing", preprocessing),
        ("classifier", classifier or LogisticRegression(max_iter=1000, class_weight="balanced", random_state=0)),
    ])


def evaluate_flood_model(
    frame: pd.DataFrame,
    metadata: dict[str, Any] | None = None,
    *,
    allow_synthetic_test_fixture: bool = False,
) -> dict[str, Any]:
    """Fit logistic and prior baselines only after the fail-closed readiness gate."""
    readiness = audit_flood_dataset(frame, metadata, allow_synthetic_test_fixture=allow_synthetic_test_fixture)
    if not readiness["ready"]:
        raise FloodModelNotReady("Flood model evaluation blocked: " + " ".join(readiness["blockers"]))

    event_column = readiness["event_group_column"]
    train_index, test_index, test_start = _chronological_event_split(frame, TIME_COLUMN, event_column)
    features = list(FEATURE_COLUMNS)
    train_x, test_x = frame.loc[train_index, features], frame.loc[test_index, features]
    train_y, test_y = frame.loc[train_index, TARGET].astype(int), frame.loc[test_index, TARGET].astype(int)

    model = build_flood_pipeline(train_x)
    baseline = build_flood_pipeline(train_x, classifier=DummyClassifier(strategy="prior"))
    model.fit(train_x, train_y)
    baseline.fit(train_x, train_y)

    def metrics(fitted: Pipeline) -> dict[str, Any]:
        predictions = fitted.predict(test_x)
        return {
            "precision": float(precision_score(test_y, predictions, zero_division=0)),
            "recall": float(recall_score(test_y, predictions, zero_division=0)),
            "f1": float(f1_score(test_y, predictions, zero_division=0)),
            "confusion_matrix_labels_0_1": confusion_matrix(test_y, predictions, labels=[0, 1]).tolist(),
            "test_rows": int(len(test_y)),
            "test_class_counts": {str(k): int(v) for k, v in test_y.value_counts().sort_index().items()},
        }

    return {
        "model": model,
        "baseline_model": baseline,
        "model_metrics": metrics(model),
        "baseline_metrics": metrics(baseline),
        "split": {
            "method": "chronological holdout; all event groups present in the future test window are excluded from training",
            "test_start": test_start.date().isoformat(),
            "train_rows": int(len(train_y)),
            "test_rows": int(len(test_y)),
            "event_groups_overlap": sorted(set(frame.loc[train_index, event_column]) & set(frame.loc[test_index, event_column])),
        },
        "readiness": readiness,
    }


def predict_flood_probability(model: Pipeline, values: dict[str, Any]) -> float:
    """Validate one complete feature record and return its positive-class score."""
    missing = [column for column in FEATURE_COLUMNS if column not in values]
    if missing:
        raise ValueError("Missing required prediction inputs: " + ", ".join(missing))
    if not isinstance(values["cwc_flood_warning_level"], str) or not values["cwc_flood_warning_level"].strip():
        raise ValueError("cwc_flood_warning_level must be a non-empty string.")
    sample = {}
    for column in NUMERIC_FEATURES:
        try:
            value = float(values[column])
        except (TypeError, ValueError) as error:
            raise ValueError(f"{column} must be numeric.") from error
        if not np.isfinite(value):
            raise ValueError(f"{column} must be finite.")
        if column in {"antecedent_rainfall_3day_mm", "forecast_rainfall_24h_mm", "insat3d_ipwv_mm"} and value < 0:
            raise ValueError(f"{column} must not be negative.")
        if column == "soil_moisture_percent" and not 0 <= value <= 100:
            raise ValueError("soil_moisture_percent must be between 0 and 100.")
        if column == "slope_angle_deg" and not 0 <= value <= 90:
            raise ValueError("slope_angle_deg must be between 0 and 90.")
        sample[column] = value
    sample["cwc_flood_warning_level"] = values["cwc_flood_warning_level"].strip()
    probabilities = model.predict_proba(pd.DataFrame([sample], columns=FEATURE_COLUMNS))[0]
    classes = list(model.named_steps["classifier"].classes_)
    return float(probabilities[classes.index(1)])

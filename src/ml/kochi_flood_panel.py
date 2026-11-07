"""Evidence-gated event-panel pipeline for Kochi flood research."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = ("rainfall_24h_mm", "rainfall_72h_mm", "river_level_m", "tide_level_m")
REQUIRED_COLUMNS = ("event_id", "site_id", "issue_time", "feature_time", "outcome_time", "inundation_observed", "negative_observation_verified", "observation_source_id", "observation_coverage", *FEATURE_COLUMNS)
MIN_TRAIN_EVENTS, MIN_TEST_EVENTS, MIN_SITES = 10, 5, 3

class FloodPanelError(ValueError):
    """Raised when the evidence panel is not fit for analysis."""

@dataclass(frozen=True)
class FloodPanelAudit:
    frame: pd.DataFrame
    report: dict[str, Any]

def validate_flood_event_panel(frame: pd.DataFrame) -> FloodPanelAudit:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        raise FloodPanelError("Panel must be a non-empty pandas DataFrame.")
    missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
    if missing:
        raise FloodPanelError("Missing required columns: " + ", ".join(missing))
    data = frame.copy()
    for c in ("event_id", "site_id", "observation_source_id", "observation_coverage"):
        data[c] = data[c].astype("string").str.strip()
        if data[c].isna().any() or data[c].eq("").any():
            raise FloodPanelError(c + " must contain non-empty values.")
    if data.duplicated(["event_id", "site_id", "issue_time"]).any():
        raise FloodPanelError("Duplicate event/site/issue-time rows are not allowed.")
    for c in ("issue_time", "feature_time", "outcome_time"):
        data[c] = pd.to_datetime(data[c], utc=True, errors="coerce")
        if data[c].isna().any():
            raise FloodPanelError(c + " must contain valid timezone-aware timestamps.")
    if (data.feature_time > data.issue_time).any():
        raise FloodPanelError("Feature data must be available no later than issue_time; future leakage detected.")
    if (data.outcome_time <= data.issue_time).any():
        raise FloodPanelError("Every outcome_time must be later than issue_time.")
    for c in ("inundation_observed", "negative_observation_verified"):
        if not data[c].isin([True, False]).all():
            raise FloodPanelError(c + " must contain explicit boolean values.")
        data[c] = data[c].astype(bool)
    if (~data.inundation_observed & ~data.negative_observation_verified).any():
        raise FloodPanelError("A dry/negative label requires verified observation coverage; missing imagery is not a non-event.")
    for c in FEATURE_COLUMNS:
        data[c] = pd.to_numeric(data[c], errors="coerce")
        if not np.isfinite(data[c].to_numpy(dtype=float)).all():
            raise FloodPanelError(c + " must be finite and complete; missing sensor records are not imputed.")
        if (data[c] < 0).any():
            raise FloodPanelError(c + " must be non-negative.")
    data["target"] = data.inundation_observed.astype(int)
    data["event_date"] = data.groupby("event_id").issue_time.transform("min")
    if (data.groupby("event_id").event_date.nunique() != 1).any():
        raise FloodPanelError("Each event_id must map to one event date.")
    report = {
        "status": "PANEL_SCHEMA_VALIDATED_NOT_MODEL_VALIDATED",
        "rows": int(len(data)), "unique_events": int(data.event_id.nunique()),
        "unique_sites": int(data.site_id.nunique()),
        "positive_rows": int(data.target.sum()),
        "verified_negative_rows": int((data.target == 0).sum()),
        "feature_columns": list(FEATURE_COLUMNS),
        "negative_labels_require_verified_observation": True,
        "feature_time_cutoff_enforced": True,
        "event_grouped_temporal_holdout": True,
        "operational_prediction_allowed": False,
    }
    return FloodPanelAudit(data, report)

def evaluate_flood_event_panel(frame: pd.DataFrame) -> dict[str, Any]:
    audit = validate_flood_event_panel(frame)
    data = audit.frame
    events = data[["event_id", "event_date"]].drop_duplicates().sort_values(["event_date", "event_id"])
    n = len(events)
    if data.site_id.nunique() < MIN_SITES or n < MIN_TRAIN_EVENTS + MIN_TEST_EVENTS:
        return {**audit.report, "status": "BLOCKED_INSUFFICIENT_EVENTS_OR_SITES",
                "minimum_train_events": MIN_TRAIN_EVENTS, "minimum_test_events": MIN_TEST_EVENTS,
                "minimum_sites": MIN_SITES, "model_metrics": None}
    n_test = max(MIN_TEST_EVENTS, int(np.ceil(n * 0.2)))
    n_test = min(n_test, n - MIN_TRAIN_EVENTS)
    test_ids = set(events.tail(n_test).event_id)
    train, test = data[~data.event_id.isin(test_ids)], data[data.event_id.isin(test_ids)]
    if train.target.nunique() < 2 or test.target.nunique() < 2:
        return {**audit.report, "status": "BLOCKED_SINGLE_CLASS_TEMPORAL_SPLIT",
                "train_events": int(train.event_id.nunique()), "test_events": int(test.event_id.nunique()),
                "test_event_ids": sorted(test_ids), "model_metrics": None}
    model = make_pipeline(StandardScaler(), LogisticRegression(class_weight="balanced", max_iter=2000, random_state=17))
    model.fit(train[list(FEATURE_COLUMNS)], train.target)
    prob = model.predict_proba(test[list(FEATURE_COLUMNS)])[:, 1]
    pred = (prob >= 0.5).astype(int)
    baseline = np.full(len(test), float(train.target.mean()))
    metrics = {
        "test_rows": int(len(test)), "train_events": int(train.event_id.nunique()),
        "test_events": int(test.event_id.nunique()), "test_sites": int(test.site_id.nunique()),
        "test_event_ids": sorted(test_ids),
        "precision": float(precision_score(test.target, pred, zero_division=0)),
        "recall": float(recall_score(test.target, pred, zero_division=0)),
        "f1": float(f1_score(test.target, pred, zero_division=0)),
        "accuracy": float(accuracy_score(test.target, pred)),
        "roc_auc": float(roc_auc_score(test.target, prob)),
        "brier_score": float(brier_score_loss(test.target, prob)),
        "training_prevalence_baseline_brier": float(brier_score_loss(test.target, baseline)),
        "confusion_matrix_labels_0_1": confusion_matrix(test.target, pred, labels=[0, 1]).tolist(),
        "threshold": 0.5,
        "interpretation": "Research-only future-event holdout; not independently validated or operational."
    }
    return {**audit.report, "status": "RESEARCH_BASELINE_EVALUATED_NOT_OPERATIONAL",
            "model_metrics": metrics, "operational_prediction_allowed": False,
            "promotion_requirements": ["Independent source review and observation coverage audit",
              "Geographically held-out sites and more independent events",
              "Calibration and uncertainty intervals",
              "Persistence and official rainfall/gauge baseline comparisons",
              "Independent replication and local authority review"]}

__all__ = ["FEATURE_COLUMNS", "FloodPanelError", "FloodPanelAudit", "validate_flood_event_panel", "evaluate_flood_event_panel"]

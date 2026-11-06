"""Pure presentation helpers for the shared ML evidence blocks.

These functions return plain rows so the Streamlit pages stay thin and the
formatting can be tested without importing Streamlit.
"""

from __future__ import annotations

from typing import Any


def model_rows(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for model in evidence.get("models", []):
        context = model.get("context", {})
        missing = context.get("missing_features") or []
        rows.append(
            {
                "Model": model.get("model_id", "Unknown"),
                "Status": model.get("status", "Unknown"),
                "Evidence tier": model.get("evidence_tier") or "Not recorded",
                "Context complete": "Yes" if context.get("complete") else "No",
                "Missing features": len(missing),
                "Note": model.get("note") or "",
            }
        )
    return rows


def application_rows(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for application in evidence.get("applications", []):
        calibration = application.get("calibration", {})
        baselines = application.get("baselines", {})
        persistence = baselines.get("persistence_baseline") or {}
        majority = baselines.get("majority_baseline") or {}
        rows.append(
            {
                "Model": application.get("model_id", "Unknown"),
                "Research event": application.get("target_definition", "Not documented"),
                "Model probability estimate": round(
                    float(application.get("probability_estimate", 0.0)), 4
                ),
                "Selected threshold": application.get("selected_probability_threshold"),
                "Above threshold": "Yes" if application.get("event_flag_at_threshold") else "No",
                "Brier score": calibration.get("brier_score"),
                "Calibration error": calibration.get("expected_calibration_error"),
                "Majority F1": majority.get("f1"),
                "Persistence F1": persistence.get("f1"),
                "Interpretation": application.get("score_interpretation", ""),
            }
        )
    return rows


def coverage_rows(coverage: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in coverage.get("entries", []):
        statuses = entry.get("model_statuses", {})
        rows.append(
            {
                "Hazard": entry.get("hazard", "Unknown"),
                "ML support": entry.get("support_level", "Unknown"),
                "Models": ", ".join(entry.get("model_ids", [])) or "None",
                "Model status": "; ".join(
                    f"{model_id}: {status}" for model_id, status in statuses.items()
                )
                or "No model",
                "Deterministic model retained": (
                    "Yes" if entry.get("deterministic_model_retained") else "No"
                ),
                "Interpretation": entry.get("interpretation", ""),
            }
        )
    return rows


def card_rows(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for card in cards:
        metrics = card.get("metrics", {})
        rows.append(
            {
                "Model": card.get("model_id", "Unknown"),
                "Hazard": card.get("hazard", "Unknown"),
                "Status": card.get("status", "Unknown"),
                "Tier": card.get("evidence_tier", "Unknown"),
                "Estimator": card.get("selected_model_type", "Unknown"),
                "Test events": card.get("test_events"),
                "Test rows": card.get("test_rows"),
                "ROC-AUC": metrics.get("roc_auc"),
                "PR-AUC": metrics.get("average_precision"),
                "F1": metrics.get("f1"),
                "Brier": metrics.get("brier_score"),
                "Validation": card.get("validation_status", "Unknown"),
            }
        )
    return rows


__all__ = ["application_rows", "card_rows", "coverage_rows", "model_rows"]

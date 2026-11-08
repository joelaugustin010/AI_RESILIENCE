"""Transparent dashboard for hazard-specific model training status."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.dataframe_display import display_dataframe
from src.ml.coverage import build_coverage_matrix
from src.ml.presentation import card_rows, coverage_rows
from src.ml.registry import list_model_cards
from src.ml.service import ml_registry_summary
from src.ml.validation_gates import model_card_validation_gate

from src.hazard_manifest import build_hazard_manifest_frame
from src.ui_theme import page_header

ROOT = Path(__file__).resolve().parents[1]
TRAINING_REPORT = ROOT / "reports" / "weather_hazard_training.json"
FLOOD_REPORT = ROOT / "reports" / "flood_event_severity_baseline.json"
ACQUISITION_REPORT = ROOT / "reports" / "hazard_data_acquisition_manifest.json"
READINESS_REPORT = ROOT / "reports" / "hazard_dataset_readiness.json"


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


page_header(
    "AI RESILIENCE · MODEL TRANSPARENCY",
    "Hazard Model Lab",
    "Research and training status for the multi-hazard project. A downloaded dataset is "
    "not automatically a training dataset, and a trained baseline is not an operational warning.",
    meta=("Research baselines", "Validation status", "Explicit blockers"),
    accent="violet",
    key="hazard-model-lab",
)

st.warning(
    "Research prototype only — these models are not official forecasts, emergency alerts, "
    "or scientifically validated predictions for Kochi. Use official IMD, KSDMA and other "
    "authorities for real safety decisions."
)

training = read_json(TRAINING_REPORT)
acquisition = read_json(ACQUISITION_REPORT)
models = training.get("models", [])
trained = training.get("trained", [])
blocked = training.get("blocked", {})

c1, c2, c3 = st.columns(3)
c1.metric("Research baselines trained", len(trained))
c2.metric("Additional hazards not trained", len(training.get("not_trained", [])))
c3.metric("Acquisition manifest entries", len(acquisition.get("downloads", [])))

st.subheader("Trained research baselines")
if not models:
    st.info("No saved weather training report was found in this deployment.")
else:
    for model in models:
        label = {
            "high_temperature": "Next-day high temperature",
            "extreme_rainfall": "Next-day extreme rainfall",
        }.get(model.get("hazard"), model.get("hazard", "Unknown hazard"))
        with st.expander(label, expanded=True):
            st.caption(model.get("status", "Status not recorded"))
            st.write(f"**Research target:** {model.get('target_definition', 'Not documented')}")
            st.write(f"**Selected estimator:** {model.get('selected_model_type', 'Not recorded')}")
            st.write(
                f"**Threshold:** {model.get('threshold', 'N/A')} "
                f"{model.get('threshold_units', '')}"
            )
            st.write(
                f"**Temporal evaluation:** model-selection training target dates before "
                f"{model.get('model_selection_train_target_dates_before', 'N/A')}; "
                f"threshold validation: {model.get('threshold_validation_target_dates', 'not recorded')}; "
                f"final training target dates before {model.get('final_train_target_dates_before', model.get('train_target_dates_before', 'N/A'))}; "
                f"test target dates from {model.get('test_target_dates_from', 'N/A')}."
            )
            if model.get("selected_probability_threshold") is not None:
                st.write(
                    f"**Selected probability threshold:** {model['selected_probability_threshold']:.2f} "
                    f"(chosen using validation-period {model.get('threshold_selection_metric', 'metric not recorded')})."
                )
            st.write("**Locations:** " + ", ".join(model.get("locations", [])))
            selection_results = model.get("model_selection_results", [])
            if selection_results:
                st.write("**Validation-only estimator comparison**")
                display_dataframe(pd.DataFrame(selection_results), hide_index=True, width="stretch")
            metrics = model.get("metrics", {})
            metric_rows = [
                {"Metric": "Accuracy", "Value": metrics.get("accuracy")},
                {"Metric": "Balanced accuracy", "Value": metrics.get("balanced_accuracy")},
                {"Metric": "Precision", "Value": metrics.get("precision")},
                {"Metric": "Recall", "Value": metrics.get("recall")},
                {"Metric": "F1 score", "Value": metrics.get("f1")},
                {"Metric": "ROC-AUC", "Value": metrics.get("roc_auc")},
                {"Metric": "Average precision (rare-event ranking)", "Value": metrics.get("average_precision")},
                {"Metric": "Brier score (probability error; lower is better)", "Value": metrics.get("brier_score")},
                {"Metric": "Majority baseline accuracy", "Value": metrics.get("majority_baseline_accuracy")},
                {"Metric": "Majority baseline balanced accuracy", "Value": metrics.get("majority_baseline_balanced_accuracy")},
                {"Metric": "Majority baseline F1", "Value": metrics.get("majority_baseline_f1")},
                {"Metric": "Persistence baseline balanced accuracy", "Value": metrics.get("persistence_baseline_balanced_accuracy")},
                {"Metric": "Persistence baseline F1", "Value": metrics.get("persistence_baseline_f1")},
            ]
            display_dataframe(pd.DataFrame(metric_rows), hide_index=True, width="stretch")
            if metrics.get("confusion_matrix_tn_fp_fn_tp") is not None:
                tn, fp, fn, tp = metrics["confusion_matrix_tn_fp_fn_tp"]
                st.caption(
                    f"Untouched test-set confusion matrix — true negatives: {tn}; false positives: {fp}; "
                    f"false negatives: {fn}; true positives: {tp}."
                )
            if model.get("hazard") == "extreme_rainfall":
                if metrics.get("accuracy") is not None and metrics.get("majority_baseline_accuracy") is not None and metrics["accuracy"] < metrics["majority_baseline_accuracy"]:
                    st.error(
                        "Accuracy at the validation-selected probability threshold remains below the "
                        "majority-class baseline. Review precision, recall and F1 together; do not "
                        "present this baseline as a reliable rainfall warning."
                    )
                else:
                    st.warning(
                        "The threshold was selected on a separate historical validation period. "
                        "This is still a research baseline, not a validated rainfall warning model; "
                        "review event recall, false alarms, calibration and independent observations."
                    )
                validation_scores = model.get("validation_threshold_scores", [])
                if validation_scores:
                    st.write("**Validation-only threshold comparison**")
                    display_dataframe(pd.DataFrame(validation_scores), hide_index=True, width="stretch")
            for limitation in model.get("limitations", []):
                st.write(f"- {limitation}")

if blocked:
    st.subheader("Training blockers")
    for hazard, reason in blocked.items():
        st.error(f"{hazard}: {reason}")

flood_report = read_json(FLOOD_REPORT)
st.subheader("Flood research baseline")
if not flood_report:
    st.info("No flood research evaluation report is available in this deployment.")
else:
    st.warning(
        "Exploratory event-severity research only. This is not a flood-occurrence model, "
        "Kochi forecast, inundation model or public warning."
    )
    dataset = flood_report.get("dataset", {})
    metrics = flood_report.get("test_metrics", {})
    fc1, fc2, fc3 = st.columns(3)
    fc1.metric("Recorded event rows", dataset.get("event_rows", "—"))
    fc2.metric("Explicitly Open gauges", dataset.get("explicitly_open_gauges", "—"))
    fc3.metric("Held-out gauges", dataset.get("held_out_gauges", "—"))
    st.write("**Research target:**", flood_report.get("target", "Not documented"))
    metric_rows = [
        {"Metric": "Accuracy", "Value": metrics.get("accuracy")},
        {"Metric": "Majority baseline accuracy", "Value": metrics.get("majority_baseline_accuracy")},
        {"Metric": "Balanced accuracy", "Value": metrics.get("balanced_accuracy")},
        {"Metric": "Precision", "Value": metrics.get("precision")},
        {"Metric": "Recall", "Value": metrics.get("recall")},
        {"Metric": "F1", "Value": metrics.get("f1")},
        {"Metric": "ROC-AUC", "Value": metrics.get("roc_auc")},
        {"Metric": "Grouped CV balanced accuracy (mean ± SD)", "Value": f"{metrics.get('grouped_cv_balanced_accuracy_mean', '—')} ± {metrics.get('grouped_cv_balanced_accuracy_std', '—')}"},
    ]
    display_dataframe(pd.DataFrame(metric_rows), hide_index=True, width="stretch")
    st.error(f"**Decision:** {flood_report.get('decision', 'Integration decision not recorded')}")
    for limitation in flood_report.get("limitations", []):
        st.write(f"- {limitation}")
    st.caption("The source and full evaluation are documented in the milestone report.")

st.subheader("Shared ML engine")
try:
    shared_cards = list_model_cards()
    coverage = build_coverage_matrix(write=False)
    shared_summary = ml_registry_summary()
except Exception as exc:
    st.info(f"Shared ML registry is unavailable: {type(exc).__name__}: {exc}")
else:
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Registered shared models", shared_summary["n_models"])
    sc2.metric("Workflow hazards represented", coverage["n_hazards"])
    sc3.metric("Hazards without released ML", coverage["n_hazards_without_ml"])
    gate_results = [model_card_validation_gate(card) for card in shared_cards]
    operational_count = sum(bool(item["operational_eligible"]) for item in gate_results)
    st.metric("Models passing independent validation gate", operational_count)
    st.caption(
        "The independent gate requires separate temporal and spatial validation, "
        "calibration, baseline skill, complete provenance and domain-transfer evidence. "
        "It cannot be passed by a single holdout or synthetic records."
    )
    st.caption(
        "The registry can contain both event classifiers and continuous regressors. Regression MAE/RMSE are not probabilities. Coverage records evidence roles, not predictive validity. No shared model is "
        "independently validated; missing models remain explicit rather than fabricated."
    )
    shared_rows = card_rows(shared_cards)
    if shared_rows:
        display_dataframe(
            pd.DataFrame(shared_rows),
            hide_index=True,
            width="stretch",
            alt="Shared ML model cards with classification and regression holdout metrics and validation boundary",
        )
    else:
        st.info("No shared ML model cards are present in this deployment.")

    st.markdown("**Coverage of the ten workflow hazards**")
    display_dataframe(
        pd.DataFrame(coverage_rows(coverage)),
        hide_index=True,
        width="stretch",
        alt="Shared ML evidence coverage and explicit no-model hazards",
    )

    for card in shared_cards:
        label = (
            f"{card.get('model_id', 'Model')} — {card.get('hazard', 'Unknown hazard')} "
            f"({card.get('status', 'Unknown status')})"
        )
        with st.expander(label, expanded=False):
            gate = model_card_validation_gate(card)
            st.caption("Operational validation gate: " + gate["readiness"])
            if gate["blocking_reasons"]:
                st.write("**Independent validation still required:**")
                for reason in gate["blocking_reasons"]:
                    st.write(f"- {reason}")
            st.write("**Status reason:**", card.get("status_reason", "Not recorded"))
            st.write("**Target:**", card.get("target_definition", "Not documented"))
            st.write("**Intended use:**", card.get("intended_use", "Not documented"))
            st.write("**Prohibited use:**", card.get("prohibited_use", "Not documented"))
            metrics = card.get("metrics", {})
            majority = metrics.get("majority_baseline") or {}
            persistence = metrics.get("persistence_baseline") or {}
            if card.get("task_type") == "regression":
                baseline = metrics.get("persistence_baseline") or {}
                median_baseline = baseline.get("training_median") or {}
                metric_rows = [
                    {"Metric": "Task", "Value": "Continuous regression"},
                    {"Metric": "Selected estimator", "Value": card.get("selected_model_type")},
                    {"Metric": "Held-out rows", "Value": metrics.get("n")},
                    {"Metric": "Prediction unit", "Value": card.get("prediction_unit")},
                    {"Metric": "Test MAE", "Value": metrics.get("mae")},
                    {"Metric": "Test RMSE", "Value": metrics.get("rmse")},
                    {"Metric": "Test R²", "Value": metrics.get("r2")},
                    {"Metric": "Baseline MAE", "Value": baseline.get("mae")},
                    {"Metric": "Training-median baseline MAE", "Value": median_baseline.get("mae")},
                    {"Metric": "MAE skill over baseline", "Value": metrics.get("mae_skill_over_persistence")},
                    {"Metric": "Paired bootstrap 95% CI for MAE improvement", "Value": metrics.get("paired_mae_improvement_bootstrap_95ci")},
                ]
            else:
                metric_rows = [
                    {"Metric": "Held-out events", "Value": card.get("test_events")},
                    {"Metric": "Held-out rows", "Value": card.get("test_rows")},
                    {"Metric": "ROC-AUC", "Value": metrics.get("roc_auc")},
                    {"Metric": "Average precision (PR-AUC)", "Value": metrics.get("average_precision")},
                    {"Metric": "Precision", "Value": metrics.get("precision")},
                    {"Metric": "Recall", "Value": metrics.get("recall")},
                    {"Metric": "F1", "Value": metrics.get("f1")},
                    {"Metric": "Brier score", "Value": metrics.get("brier_score")},
                    {"Metric": "Base-rate Brier reference", "Value": metrics.get("base_rate_brier_score")},
                    {"Metric": "Expected calibration error", "Value": metrics.get("expected_calibration_error")},
                    {"Metric": "Majority baseline F1", "Value": majority.get("f1")},
                    {
                        "Metric": "Persistence baseline F1",
                        "Value": persistence.get("f1") if persistence.get("available") else None,
                    },
                    {
                        "Metric": "Persistence baseline balanced accuracy",
                        "Value": persistence.get("balanced_accuracy") if persistence.get("available") else None,
                    },
                ]
            display_dataframe(
                pd.DataFrame(metric_rows),
                hide_index=True,
                width="stretch",
                alt=f"Holdout metrics for shared model {card.get('model_id', '')}",
            )
            ablation = metrics.get("ablation")
            if isinstance(ablation, dict) and ablation.get("available"):
                st.write("**Ablation**")
                display_dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Model": "Full",
                                "Test ROC-AUC": ablation.get("full_test_roc_auc"),
                                "Test PR-AUC": ablation.get("full_test_average_precision"),
                            },
                            {
                                "Model": "Reduced",
                                "Test ROC-AUC": ablation.get("reduced_test_roc_auc"),
                                "Test PR-AUC": ablation.get("reduced_test_average_precision"),
                            },
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                )
                st.caption(ablation.get("interpretation", ""))
            for limitation in card.get("limitations", []):
                st.write(f"- {limitation}")

st.subheader("Scientific data readiness by hazard")
readiness = read_json(READINESS_REPORT)
readiness_hazards = readiness.get("hazards", [])
if not readiness_hazards:
    st.warning(
        "The local source-readiness audit is missing or unreadable. Re-run "
        "`python scripts/audit_hazard_datasets.py` to regenerate it."
    )
else:
    readiness_rows = []
    for item in readiness_hazards:
        raw_sources = item.get("raw_sources", [])
        present_sources = [
            source for source in raw_sources
            if source.get("exists") and source.get("status") != "PRESENT_BUT_UNREADABLE"
        ]
        curated = item.get("curated_training_table", {})
        baseline = item.get("research_baseline") or {}
        readiness_rows.append({
            "Hazard": item.get("label", item.get("hazard_id", "Unknown")),
            "Raw source files": f"{len(present_sources)} / {len(raw_sources)}",
            "Curated training table": curated.get("status", "Not audited"),
            "Research baseline": baseline.get("status", "None recorded"),
            "Model readiness": item.get("model_status", "Not established"),
        })
    display_dataframe(pd.DataFrame(readiness_rows), hide_index=True, width="stretch")
    for item in readiness_hazards:
        with st.expander(f"{item.get('label', item.get('hazard_id', 'Hazard'))}: evidence and blockers"):
            for source in item.get("raw_sources", []):
                st.markdown(
                    f"**{source.get('file', 'Source file')}** — "
                    f"{source.get('status', 'Not audited')}"
                )
                if source.get("sha256"):
                    st.caption(f"SHA-256: {source['sha256']}")
                if source.get("error"):
                    st.error(source["error"])
            curated = item.get("curated_training_table", {})
            st.markdown(f"**Training table:** {curated.get('status', 'Not audited')}")
            for issue in curated.get("issues", []):
                st.write(f"- {issue}")
            baseline = item.get("research_baseline") or {}
            if baseline:
                st.info(f"Separate research baseline: {baseline.get('status', 'Status not recorded')}")
                if baseline.get("test_target_dates_from"):
                    st.caption(f"Historical test period begins: {baseline['test_target_dates_from']}")
                if baseline.get("locations"):
                    st.caption("Training/evaluation locations: " + ", ".join(baseline["locations"]))
                if baseline.get("metrics"):
                    display_dataframe(
                        pd.DataFrame([baseline["metrics"]]),
                        hide_index=True,
                        width="stretch",
                    )
            st.write(f"**Scientific limitation:** {item.get('scientific_limitation', 'Not documented')}")
    st.caption(readiness.get("warning", ""))

with st.expander("Source acquisition manifest"):
    entries = acquisition.get("downloads", [])
    if entries:
        display_dataframe(
            build_hazard_manifest_frame(entries),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("No acquisition manifest entries are available.")

st.caption(
    "All metrics are for a single chronological holdout and historical gridded weather inputs. "
    "They do not establish local operational forecast skill. Independent station validation, "
    "calibration, drift checks and appropriate official thresholds remain necessary."
)

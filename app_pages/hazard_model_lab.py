"""Transparent dashboard for hazard-specific model training status."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
TRAINING_REPORT = ROOT / "reports" / "weather_hazard_training.json"
ACQUISITION_REPORT = ROOT / "reports" / "hazard_data_acquisition_manifest.json"
READINESS_REPORT = ROOT / "reports" / "hazard_dataset_readiness.json"


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


st.title("Hazard Model Lab")
st.caption(
    "Research and training status for the multi-hazard project. "
    "A downloaded dataset is not automatically a training dataset."
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
            metrics = model.get("metrics", {})
            metric_rows = [
                {"Metric": "Accuracy", "Value": metrics.get("accuracy")},
                {"Metric": "Balanced accuracy", "Value": metrics.get("balanced_accuracy")},
                {"Metric": "Precision", "Value": metrics.get("precision")},
                {"Metric": "Recall", "Value": metrics.get("recall")},
                {"Metric": "F1 score", "Value": metrics.get("f1")},
                {"Metric": "ROC-AUC", "Value": metrics.get("roc_auc")},
                {"Metric": "Majority baseline accuracy", "Value": metrics.get("majority_baseline_accuracy")},
            ]
            st.dataframe(pd.DataFrame(metric_rows), hide_index=True, width="stretch")
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
                    st.dataframe(pd.DataFrame(validation_scores), hide_index=True, width="stretch")
            for limitation in model.get("limitations", []):
                st.write(f"- {limitation}")

if blocked:
    st.subheader("Training blockers")
    for hazard, reason in blocked.items():
        st.error(f"{hazard}: {reason}")

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
        readiness_rows.append({
            "Hazard": item.get("label", item.get("hazard_id", "Unknown")),
            "Raw source files": f"{len(present_sources)} / {len(raw_sources)}",
            "Curated training table": curated.get("status", "Not audited"),
            "Model readiness": item.get("model_status", "Not established"),
        })
    st.dataframe(pd.DataFrame(readiness_rows), hide_index=True, width="stretch")
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
            st.write(f"**Scientific limitation:** {item.get('scientific_limitation', 'Not documented')}")
    st.caption(readiness.get("warning", ""))

with st.expander("Source acquisition manifest"):
    entries = acquisition.get("downloads", [])
    if entries:
        rows = []
        for item in entries:
            rows.append({
                "File": item.get("file", ""),
                "Status": item.get("status", "Not recorded"),
                "Rows": item.get("data_rows", ""),
                "Bytes": item.get("bytes", ""),
                "Retrieved": item.get("retrieved_at", ""),
                "SHA-256": item.get("sha256", ""),
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    else:
        st.info("No acquisition manifest entries are available.")

st.caption(
    "All metrics are for a single chronological holdout and historical gridded weather inputs. "
    "They do not establish local operational forecast skill. Independent station validation, "
    "calibration, drift checks and appropriate official thresholds remain necessary."
)

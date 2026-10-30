"""Transparent dashboard for hazard-specific model training status."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
TRAINING_REPORT = ROOT / "reports" / "weather_hazard_training.json"
ACQUISITION_REPORT = ROOT / "reports" / "hazard_data_acquisition_manifest.json"


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
                f"**Historical split:** training target dates before "
                f"{model.get('train_target_dates_before', 'N/A')}; test target dates from "
                f"{model.get('test_target_dates_from', 'N/A')}."
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
                st.error(
                    "The current 0.5-classification-threshold accuracy is below the majority-class "
                    "baseline. ROC-AUC is not a substitute for useful event recall. This model "
                    "needs threshold tuning on training-only validation data and further evaluation "
                    "before any user-facing prediction."
                )
            for limitation in model.get("limitations", []):
                st.write(f"- {limitation}")

if blocked:
    st.subheader("Training blockers")
    for hazard, reason in blocked.items():
        st.error(f"{hazard}: {reason}")

st.subheader("Other hazard tracks")
remaining = [
    ("Earthquake", "Event catalogue acquired; suitable impact labels and exposure/shaking predictors are still needed."),
    ("Cyclone", "North Indian Ocean track data acquired; a storm-held-out forecast dataset is still needed."),
    ("Landslide", "Global event catalogue acquired; defensible background samples and spatial-bias checks are still needed."),
    ("Drought", "India drought-monitor files acquired; definitions, structure and aligned predictors need validation."),
    ("Wildfire", "Satellite access and defensible non-fire/background examples are still needed."),
    ("Tsunami", "Historical event records cannot alone support short-term occurrence prediction; coastal impact modelling needs suitable data."),
    ("Air pollution", "Validated CPCB/OpenAQ station time series and time-aligned predictors are still needed."),
]
for hazard, status in remaining:
    st.markdown(f"**{hazard}:** {status}")

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

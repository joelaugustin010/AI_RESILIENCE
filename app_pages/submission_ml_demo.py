"""Competition demonstration dashboard for the existing research ML evidence.

This page is deliberately evidence-led: it displays persisted model cards and
validation boundaries, never invents a live forecast or turns a research score
into a disaster probability.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.ml.coverage import build_coverage_matrix
from src.ml.presentation import card_rows
from src.ml.registry import list_model_cards
from src.ml.submission_summary import rank_classifier_cards, rank_regression_cards
from src.ml.validation_gates import model_card_validation_gate
from src.ui_theme import page_header


page_header(
    "AI RESILIENCE · SUBMISSION DEMONSTRATION",
    "ML Evidence & Demonstration",
    "A clear, evaluator-facing view of what has been trained, what the tests show, "
    "where the models may help research, and what still needs independent validation.",
    meta=("Persisted research models", "Baseline comparisons", "Transparent limits"),
    accent="violet",
    key="submission-ml-demo",
)

st.warning(
    "Research demonstration only. These historical research models are not live "
    "Kochi forecasts, calibrated public warnings, or substitutes for IMD/KSDMA "
    "instructions. No model currently passes the independent operational gate."
)

try:
    cards = list_model_cards()
    coverage = build_coverage_matrix(write=False)
except Exception as exc:
    st.error(f"Model evidence could not be loaded: {type(exc).__name__}: {exc}")
    st.stop()

gates = [model_card_validation_gate(card) for card in cards]
regressors = rank_regression_cards(cards)
operational = sum(bool(gate["operational_eligible"]) for gate in gates)
hazards_with_models = sum(bool(entry.get("trained_model_ids")) for entry in coverage["entries"])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Persisted research models", len(cards))
m2.metric("Hazards with trained evidence", hazards_with_models, "of 10")
m3.metric("Regression tasks", sum(card.get("task_type") == "regression" for card in cards))
m4.metric("Operationally validated", operational)

st.subheader("What the current evidence supports")
st.markdown(
    """
    - **Continuous research estimates:** next-day precipitation, next-day maximum
      temperature, and cyclone wind change. These are numeric estimates, not disaster probabilities.
    - **Exploratory event screening:** rainfall, high temperature, drought, cyclone
      rapid intensification, earthquake aftershock, and cyclone–rainfall association.
    - **Not yet supported by defensible supervised models:** landslides, industrial
      incidents, and infrastructure failure, because representative verified event
      and non-event training panels are missing.
    """
)

if regressors:
    best = regressors[0]
    metrics = best["metrics"]
    skill = float(metrics["mae_skill_over_persistence"])
    st.markdown("#### Strongest regression result against its recorded baseline")
    st.metric(
        best.get("hazard", best.get("model_id", "Regression model")),
        f"{skill * 100:.1f}% lower MAE than persistence",
        help="Computed from the persisted model card's held-out MAE skill metric.",
    )
    baseline = metrics.get("persistence_baseline") or {}
    baseline_label = (
        "No-change baseline MAE"
        if baseline.get("type") == "constant_no_change"
        else "Persistence baseline MAE"
    )
    st.caption(
        f"Model: {best.get('model_id')} · Held-out MAE: {metrics.get('mae')} "
        f"{best.get('prediction_unit', '')} · {baseline_label}: "
        f"{baseline.get('mae', 'not recorded')}."
    )
    st.info(
        "A better next-day weather estimate can support research and scenario inputs. "
        "It does not establish flood occurrence, inundation, casualties, or a local warning."
    )
else:
    st.info("No regression model card with a recorded persistence-skill metric is available.")

classifiers = rank_classifier_cards(cards)
if classifiers:
    best_classifier = classifiers[0]
    classifier_metrics = best_classifier["metrics"]
    baseline_f1 = float(classifier_metrics["persistence_baseline"]["f1"])
    model_f1 = float(classifier_metrics["f1"])
    st.markdown("#### Strongest classifier F1 comparison")
    c1, c2, c3 = st.columns(3)
    c1.metric("Research task", best_classifier.get("hazard", best_classifier.get("model_id", "Classifier")))
    c2.metric("Model F1", f"{model_f1:.3f}")
    c3.metric("Persistence F1", f"{baseline_f1:.3f}", f"{(model_f1 - baseline_f1):+.3f} absolute")
    st.caption(
        f"{best_classifier.get('model_id')} · ROC-AUC "
        f"{classifier_metrics.get('roc_auc', 'not recorded')} · "
        f"average precision {classifier_metrics.get('average_precision', 'not recorded')}."
    )
    st.warning(
        "This is a single-holdout research comparison. It does not establish "
        "independent validation or calibrated probabilities; inspect the model "
        "card and limitations before interpreting the score."
    )

st.subheader("Complete registered model-card inventory")
st.dataframe(
    pd.DataFrame(card_rows(cards)),
    hide_index=True,
    use_container_width=True,
)
st.caption(
    "This inventory reports every registered research card, including weak or "
    "non-operational results. A row means a model artifact/card exists; it does "
    "not mean the model is independently validated or suitable for warnings."
)

st.subheader("Explore a hazard")
hazard_names = [entry["hazard"] for entry in coverage["entries"]]
selected_hazard = st.selectbox("Select a hazard or compound scenario", hazard_names)
entry = next(item for item in coverage["entries"] if item["hazard"] == selected_hazard)
st.markdown(f"**Evidence role:** {entry.get('support_level', 'Not recorded').replace('_', ' ').title()}")
st.write(entry.get("interpretation", "No interpretation recorded."))
if entry.get("trained_model_ids"):
    selected_cards = [
        card for card in cards if card.get("model_id") in entry["trained_model_ids"]
    ]
    if not selected_cards:
        st.info("The coverage registry references model IDs, but matching model cards are unavailable.")
    for card in selected_cards:
        metrics = card.get("metrics", {})
        gate = model_card_validation_gate(card)
        with st.expander(f"{card.get('model_id')} · {card.get('status')}", expanded=True):
            st.caption(f"Independent validation gate: {gate['readiness']}")
            if card.get("task_type") == "regression":
                st.dataframe(
                    pd.DataFrame([
                        {"Metric": "Held-out MAE", "Value": metrics.get("mae")},
                        {"Metric": "Persistence baseline MAE", "Value": (metrics.get("persistence_baseline") or {}).get("mae")},
                        {"Metric": "MAE skill over persistence", "Value": metrics.get("mae_skill_over_persistence")},
                        {"Metric": "Held-out RMSE", "Value": metrics.get("rmse")},
                        {"Metric": "Held-out R²", "Value": metrics.get("r2")},
                        {"Metric": "Held-out cases", "Value": metrics.get("n")},
                    ]),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                st.dataframe(
                    pd.DataFrame([
                        {"Metric": "ROC-AUC", "Value": metrics.get("roc_auc")},
                        {"Metric": "Average precision", "Value": metrics.get("average_precision")},
                        {"Metric": "F1", "Value": metrics.get("f1")},
                        {"Metric": "Brier score", "Value": metrics.get("brier_score")},
                        {"Metric": "Base-rate Brier reference", "Value": metrics.get("base_rate_brier_score")},
                        {"Metric": "Expected calibration error", "Value": metrics.get("expected_calibration_error")},
                        {"Metric": "Held-out rows", "Value": card.get("test_rows")},
                        {"Metric": "Held-out events", "Value": card.get("test_events")},
                    ]),
                    hide_index=True,
                    use_container_width=True,
                )
                calibration_rows = metrics.get("calibration_table") or []
                if calibration_rows:
                    st.markdown("**Held-out reliability bins**")
                    st.dataframe(
                        pd.DataFrame(calibration_rows),
                        hide_index=True,
                        use_container_width=True,
                    )
                    st.caption(
                        "Reliability bins are descriptive for this historical holdout; "
                        "they do not establish future or operational calibration."
                    )
                intervals = metrics.get("bootstrap_95ci") or {}
                if intervals:
                    interval_rows = [
                        {"Metric": name, "95% bootstrap interval": str(bounds)}
                        for name, bounds in intervals.items()
                    ]
                    st.markdown("**Recorded holdout uncertainty intervals**")
                    st.dataframe(
                        pd.DataFrame(interval_rows),
                        hide_index=True,
                        use_container_width=True,
                    )
                    st.caption(
                        f"Bootstrap method: {metrics.get('bootstrap_method', 'not recorded')}. "
                        "Intervals quantify resampling uncertainty under the recorded method, "
                        "not geographic transfer or operational reliability."
                    )
            st.write("**Research target:**", card.get("target_definition", "Not documented"))
            feature_columns = card.get("feature_columns") or []
            if feature_columns:
                with st.expander("Inspect model feature set", expanded=False):
                    st.write(f"{len(feature_columns)} recorded input features")
                    st.code("\n".join(str(item) for item in feature_columns), language="text")
            st.write("**Intended use:**", card.get("intended_use", "Not documented"))
            st.write("**Not suitable for:**", card.get("prohibited_use", "Not documented"))
            if gate["blocking_reasons"]:
                st.write("**Why it is not operationally validated**")
                for reason in gate["blocking_reasons"]:
                    st.write(f"- {reason}")
            for limitation in card.get("limitations", []):
                st.write(f"- {limitation}")
else:
    st.warning("No trained supervised model is registered for this hazard. Use the scenario workflow and its evidence/precaution guidance instead.")

st.subheader("Ten-hazard coverage")
coverage_rows = []
for item in coverage["entries"]:
    coverage_rows.append({
        "Hazard": item["hazard"],
        "Research support": item["support_level"].replace("_", " ").title(),
        "Trained model cards": len(item.get("trained_model_ids", [])),
        "Deterministic workflow retained": "Yes" if item.get("deterministic_model_retained") else "No",
    })
st.dataframe(pd.DataFrame(coverage_rows), hide_index=True, use_container_width=True)

st.subheader("How to demonstrate this at the exhibition")
st.markdown(
    """
    1. Open **Decision Workflow** and select a hazard or compound scenario.
    2. Explain the evidence, assumptions, exposed services and recommended preparedness actions.
    3. Open **ML Evidence & Demonstration** and select the matching hazard.
    4. Compare the model's held-out metrics with its recorded baseline.
    5. Explain one limitation and why the platform refuses to present an unvalidated
       result as an official warning.
    """
)
st.caption(
    "The shared ML registry is the source of truth for this page. Missing cards, "
    "missing metrics, and failed validation gates remain visible rather than being guessed."
)

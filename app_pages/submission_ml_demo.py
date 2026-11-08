"""Competition demonstration dashboard for the existing research ML evidence.

This page is deliberately evidence-led: it displays persisted model cards and
validation boundaries, never invents a live forecast or turns a research score
into a disaster probability.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dataframe_display import display_dataframe

from src.dataframe_display import display_dataframe

from src.ml.coverage import build_coverage_matrix
from src.ml.presentation import application_rows, card_rows, model_rows
from src.ml.registry import list_model_cards
from src.ml.service import historical_replay_context, ml_evidence_for
from src.ml.submission_summary import rank_classifier_cards, rank_regression_cards, regression_baseline_label
from src.ml.validation_gates import model_card_validation_gate
from src.ui_theme import page_header


@st.cache_data(show_spinner=False)
def _load_historical_replay(model_id: str) -> dict:
    """Cache the deterministic historical holdout row used in the exhibition replay."""
    return historical_replay_context(model_id)


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
        f"{skill * 100:.1f}% lower MAE than the recorded baseline",
        help="Computed against the comparator recorded in this model card; the comparator may be persistence or a no-change baseline.",
    )
    baseline = metrics.get("persistence_baseline") or {}
    baseline_label = f"{regression_baseline_label(best)} MAE"
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
display_dataframe(
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
selected_cards = [
    card for card in cards if card.get("model_id") in entry.get("trained_model_ids", [])
]
# Put an actually applicable research model first for a smoother evaluator demo.
# Regression models are preferred because their outputs retain physical units;
# the model's validation status and scientific limitations remain visible below.
selected_cards.sort(
    key=lambda card: (
        card.get("status") not in {"WEAK_RESEARCH_SIGNAL", "RESEARCH_SIGNAL_NOT_VALIDATED"},
        card.get("task_type") != "regression",
        str(card.get("model_id", "")),
    )
)
if selected_cards:
    st.markdown("#### Run a transparent research inference")
    selected_model_id = st.selectbox(
        "Choose a registered model",
        options=[card["model_id"] for card in selected_cards],
        format_func=lambda value: value.replace("_", " ").title(),
    )
    selected_card = next(card for card in selected_cards if card["model_id"] == selected_model_id)
    demo_mode = st.radio(
        "Inference demonstration mode",
        ["Replay a historical test case", "Enter measured feature values"],
        horizontal=True,
    )
    if demo_mode == "Replay a historical test case":
        st.info(
            "Recommended for the exhibition: this loads a real, complete row from "
            "the model's documented historical test period and runs the persisted "
            "model on its recorded input features. It is a retrospective replay, "
            "not a current forecast."
        )
        try:
            replay = _load_historical_replay(selected_model_id)
            replay_cols = st.columns(4)
            replay_cols[0].metric("Historical case date", replay["case_date"])
            replay_cols[1].metric("Input features", len(replay["context"]))
            replay_cols[2].metric("Observed target", f"{replay['observed_target']:g}")
            observed_class = (
                "Event" if replay.get("observed_event") is True
                else "No event" if replay.get("observed_event") is False
                else "Continuous target"
            )
            replay_cols[3].metric("Observed held-out class", observed_class)
            st.caption(
                f"Target: {replay.get('target_definition') or replay['target_column']} · "
                f"Source: {replay.get('source') or 'model-card source'} · "
                f"{replay.get('source_type') or 'source type not recorded'}"
            )
            st.caption(replay["warning"])
            if st.button(
                "Run model on this historical test case",
                type="primary",
                use_container_width=True,
                key=f"run-historical-{selected_model_id}",
            ):
                inference_inputs = {"ml_context": replay["context"]}
                if replay.get("location"):
                    inference_inputs["location"] = replay["location"]
                try:
                    evidence_result = ml_evidence_for(
                        selected_hazard,
                        inference_inputs,
                        selected_model_id=selected_model_id,
                    )
                    st.session_state["submission_ml_inference_result"] = {
                        "hazard": selected_hazard,
                        "model_id": selected_model_id,
                        "evidence": evidence_result,
                        "replay": replay,
                    }
                    st.session_state.pop("submission_ml_inference_error", None)
                except Exception as exc:
                    st.session_state["submission_ml_inference_error"] = (
                        f"{type(exc).__name__}: {exc}"
                    )
        except Exception as exc:
            st.error(
                f"Historical replay is unavailable for this model: {type(exc).__name__}: {exc}"
            )
    else:
        st.info(
            "Enter independently sourced observations only. Unknown fields remain "
            "blank; the engine will refuse inference until the selected model's "
            "complete feature contract is supplied."
        )
        feature_names = [str(name) for name in selected_card.get("feature_columns", [])]
        feature_ranges = selected_card.get("feature_ranges") or {}
        provenance = selected_card.get("provenance") or {}
        location_required = str(provenance.get("location") or "").casefold() == "kochi"
        with st.form("submission_ml_inference_form", clear_on_submit=False):
            location_value = ""
            if location_required:
                location_value = st.text_input(
                    "Model location (must match its documented geography)",
                    placeholder="Enter Kochi only if these inputs are for Kochi",
                )
            st.caption(f"Required features for this model: {len(feature_names)}")
            input_columns = st.columns(2)
            supplied_values = {}
            for index, feature in enumerate(feature_names):
                with input_columns[index % 2]:
                    bounds = feature_ranges.get(feature, {})
                    if isinstance(bounds, dict) and bounds.get("min") is not None and bounds.get("max") is not None:
                        range_help = (
                            f"Recorded training range: {bounds['min']} to {bounds['max']}. "
                            "This is a domain-check reference, not a suggested or current observation."
                        )
                    else:
                        range_help = "No numeric training range is recorded for this feature."
                    supplied_values[feature] = st.text_input(
                        feature,
                        value="",
                        help=range_help,
                        placeholder="Enter a measured value; leave blank if unknown",
                        key=f"submission-ml-{selected_hazard}-{selected_model_id}-{feature}",
                    )
            run_inference = st.form_submit_button(
                "Check inputs and run model",
                type="primary",
                use_container_width=True,
            )
        if run_inference:
            explicit_context = {
                name: value.strip()
                for name, value in supplied_values.items()
                if value.strip() != ""
            }
            inference_inputs = {"ml_context": explicit_context}
            if location_required:
                inference_inputs["location"] = location_value.strip()
            try:
                evidence_result = ml_evidence_for(
                    selected_hazard,
                    inference_inputs,
                    selected_model_id=selected_model_id,
                )
                st.session_state["submission_ml_inference_result"] = {
                    "hazard": selected_hazard,
                    "model_id": selected_model_id,
                    "evidence": evidence_result,
                    "replay": None,
                }
                st.session_state.pop("submission_ml_inference_error", None)
            except Exception as exc:
                st.session_state["submission_ml_inference_error"] = (
                    f"{type(exc).__name__}: {exc}"
                )
    inference_error = st.session_state.get("submission_ml_inference_error")
    if inference_error:
        st.error(f"Inference could not be completed: {inference_error}")
    saved_result = st.session_state.get("submission_ml_inference_result")
    if (
        isinstance(saved_result, dict)
        and saved_result.get("hazard") == selected_hazard
        and saved_result.get("model_id") == selected_model_id
    ):
        evidence_result = saved_result["evidence"]
        st.markdown("**Input and model readiness**")
        model_result_rows = model_rows(evidence_result)
        if model_result_rows:
            display_dataframe(
                pd.DataFrame(model_result_rows),
                hide_index=True,
                use_container_width=True,
            )
        st.markdown(
            f"**Engine status:** "
            f"{evidence_result.get('status', 'unknown').replace('_', ' ').title()}"
        )
        if evidence_result.get("applications"):
            st.markdown("**Model output(s)**")
            display_dataframe(
                pd.DataFrame(application_rows(evidence_result)),
                hide_index=True,
                use_container_width=True,
            )
            for application in evidence_result["applications"]:
                for warning in application.get("warnings", []):
                    st.warning(warning)
                for limitation in application.get("limitations", []):
                    st.caption(f"Limitation: {limitation}")
        else:
            st.warning(
                evidence_result.get("note")
                or "No output was produced. Review missing features, model status, "
                   "geographic scope, and training-range checks above."
            )
        if saved_result.get("replay"):
            replay = saved_result["replay"]
            st.caption(
                f"Retrospective check: {replay['target_column']} observed value was "
                f"{replay['observed_target']:g} on the held-out case. "
                f"Observed class: {replay.get('observed_event')}. The target was "
                "not supplied as a model input."
            )
        st.caption(
            "Research output only. It is not a calibrated disaster probability, "
            "live forecast, official warning, or independently validated prediction."
        )
else:
    st.info(
        "No supervised model is registered for this hazard. The deterministic "
        "scenario assessment remains the available decision path."
    )
st.write(entry.get("interpretation", "No interpretation recorded."))
if entry.get("trained_model_ids"):
    if not selected_cards:
        st.info("The coverage registry references model IDs, but matching model cards are unavailable.")
    for card in selected_cards:
        metrics = card.get("metrics", {})
        gate = model_card_validation_gate(card)
        with st.expander(f"{card.get('model_id')} · {card.get('status')}", expanded=True):
            st.caption(f"Independent validation gate: {gate['readiness']}")
            if card.get("task_type") == "regression":
                display_dataframe(
                    pd.DataFrame([
                        {"Metric": "Held-out MAE", "Value": metrics.get("mae")},
                        {"Metric": "Recorded baseline MAE", "Value": (metrics.get("persistence_baseline") or {}).get("mae")},
                        {"Metric": "MAE skill over recorded baseline", "Value": metrics.get("mae_skill_over_persistence")},
                        {"Metric": "Held-out RMSE", "Value": metrics.get("rmse")},
                        {"Metric": "Held-out R²", "Value": metrics.get("r2")},
                        {"Metric": "Held-out cases", "Value": metrics.get("n")},
                    ]),
                    hide_index=True,
                    use_container_width=True,
                )
            else:
                display_dataframe(
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
                    display_dataframe(
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
                    display_dataframe(
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
            if card.get("status_reason"):
                st.caption(f"Model-card status rationale: {card['status_reason']}")
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
display_dataframe(pd.DataFrame(coverage_rows), hide_index=True, use_container_width=True)

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

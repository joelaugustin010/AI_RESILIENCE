"""Input-based Ernakulam disaster-risk assessment page."""

from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from src.ui_theme import page_header

from src.ernakulam_disaster_dashboard import load_location_registry, location_options
from src.ernakulam_input_predictions import (
    HAZARD_GUIDANCE,
    HAZARD_MODELS,
    INPUTS,
    SIMPLE_INPUTS,
    InputValidationError,
    data_readiness_summary,
    prediction_ready_hazards,
    prediction_unavailable_reasons,
    predict_hazard,
    validated_probability,
)


st.markdown(
    """
    <style>
    /* Ernakulam risk module: measured blue accent, calm analytical surfaces. */
    .probability-panel {
      border: 1px solid rgba(23, 78, 85, .16);
      border-radius: 16px;
      padding: .95rem 1.05rem .8rem;
      margin: .55rem 0 .8rem;
      background:
        radial-gradient(ellipse at 100% 0%, rgba(127, 184, 255, .10), transparent 16rem),
        linear-gradient(145deg, rgba(15, 42, 62, .96), rgba(9, 28, 43, .96));
      box-shadow: var(--ar-shadow-soft);
    }
    .probability-label {
      color: #9db9d4;
      font-size: .72rem;
      font-weight: 750;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .probability-value {
      color: #cfe4ff;
      font-size: 2.05rem;
      font-weight: 800;
      line-height: 1.1;
      margin: .18rem 0 .35rem;
      font-variant-numeric: tabular-nums;
    }
    .probability-unavailable {
      color: #f0c56a;
      font-size: 1.12rem;
      font-weight: 750;
      margin: .18rem 0 .35rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

page_header(
    "AI RESILIENCE · ERNAKULAM RISK ASSESSMENT",
    "AI Disaster Risk Assessment",
    "Understand local environmental conditions and assess potential disaster risks in "
    "Ernakulam, one hazard at a time.",
    meta=("Ernakulam district", "Preliminary screening", "Not a forecast"),
    accent="blue",
    key="disaster-probability",
)
st.caption(
    "One independent hazard assessment at a time. Preliminary categories describe submitted "
    "conditions; they are not probabilities, official warnings, or forecasts."
)

try:
    locations = location_options(load_location_registry())
except (OSError, ValueError) as error:
    st.error(f"The verified Ernakulam location list could not be loaded: {error}")
    st.stop()

st.markdown("### Location and data")
location_column, observation_column = st.columns((1.2, 1))
with location_column:
    selected_location = st.selectbox("Location in Ernakulam district", locations)
    st.caption(
        "Local-body names are verified for Ernakulam. A district or local-body "
        "selection does not imply a location-specific model or sensor feed."
    )
with observation_column:
    current_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    observation_date = st.date_input(
        "Observation date",
        value=current_ist.date(),
        format="DD/MM/YYYY",
    )
    observation_clock = st.time_input(
        "Observation time (India Standard Time)",
        value=current_ist.time().replace(tzinfo=None, second=0, microsecond=0),
        step=60,
    )
observation_time = datetime.combine(observation_date, observation_clock)

status_column, source_column = st.columns(2)
with status_column:
    st.markdown("**Data retrieval status**")
    st.caption(
        "Live weather and warning feeds are not connected; no live data are used."
    )
    st.caption(
        "The unauthenticated IMD API check returned HTTP 401. No API token is "
        "configured, so current observations and forecasts are not fetched."
    )
with source_column:
    st.markdown("**Available reference data**")
    st.write(
        "KSDMA's published Ernakulam flood scenarios are shown as district-level "
        "historical context only. The local CWC/NWIC station file is excluded from "
        "live assessment because station, time, and source quality are unresolved."
    )
    st.caption(
        "Reference snapshot: KSDMA report retrieved 31 Oct 2026. "
        "No automatic data refresh."
    )
st.caption(
    "Sources: "
    "[IMD API documentation](https://api.imd.gov.in/public/api_reference.html) · "
    "[IMD weather](https://mausam.imd.gov.in/) · "
    "[CWC/NWIC portal](https://nwdp.nwic.gov.in/) · "
    "[KSDMA hazard maps](https://sdma.kerala.gov.in/hazard-maps/). "
    "Links are references, not integrated feeds."
)

st.markdown("### Choose your mode")
available_hazards = prediction_ready_hazards(selected_location)
if not available_hazards:
    st.warning(
        "No hazard currently passes the verified data and model-readiness gates "
        "for this location. Probability prediction is unavailable; no fabricated "
        "probabilities are shown."
    )
    with st.expander("Why hazards are unavailable"):
        for label, reason in prediction_unavailable_reasons(selected_location).items():
            st.markdown(f"**{label}** — {reason}")
    st.stop()

hazard_options = list(available_hazards)
selected_hazard = st.selectbox(
    "Disaster to assess",
    hazard_options,
    format_func=lambda hazard_id: available_hazards[hazard_id]["label"],
    key="selected_disaster_hazard",
)
mode_label = st.radio(
    "Input mode",
    ("SIMPLE MODE", "ADVANCED MODE"),
    horizontal=True,
    label_visibility="collapsed",
    key="disaster_input_mode",
)
input_mode = "simple" if mode_label == "SIMPLE MODE" else "advanced"
mode_cards = st.columns(2)
with mode_cards[0]:
    with st.container(border=True):
        st.markdown("#### SIMPLE MODE")
        st.write(
            "For everyday observations. Choose answers about what you notice; "
            "no instruments or scientific terms are needed."
        )
        if input_mode == "simple":
            st.caption("Selected")
with mode_cards[1]:
    with st.container(border=True):
        st.markdown("#### ADVANCED MODE")
        st.write(
            "For measured readings. Enter scientific values, units, and a "
            "monitoring reference where relevant."
        )
        if input_mode == "advanced":
            st.caption("Selected")

hazard_simple_fields = {
    "flood": ("rain", "water_rising", "water_collecting", "duration"),
    "cyclone": ("wind", "weather", "storm_warning"),
    "landslide": ("ground", "slope_signs", "unusual_changes"),
    "drought": ("recent_rainfall", "water_shortage"),
}
selected_simple_fields = hazard_simple_fields[selected_hazard]

with st.form("environmental_conditions"):
    submitted_values = {}
    simple_observations = {}
    assessment_observations = {}
    water_level_reference = ""
    if input_mode == "simple":
        st.markdown("### What are conditions like near you?")
        st.caption(
            "Answer what you know. These qualitative answers remain descriptions "
            "and are never converted into scientific measurements."
        )
        st.markdown(f"#### {HAZARD_MODELS[selected_hazard]['label']}")
        columns = st.columns(2)
        for index, field in enumerate(selected_simple_fields):
            specification = SIMPLE_INPUTS[field]
            with columns[index % 2]:
                simple_observations[field] = st.selectbox(
                    specification["label"],
                    specification["options"],
                    index=None,
                    placeholder="Choose an answer",
                    help=specification["help"],
                    key=f"simple_{field}",
                )
    else:
        st.markdown("### Scientific measurements")
        st.caption(
            "Enter only readings you have. Leave unavailable values blank; "
            "they are not guessed or treated as normal."
        )
        field_hazards = {
            field: [
                HAZARD_MODELS[hazard_id]["label"]
                for hazard_id, model in HAZARD_MODELS.items()
                if field in model["advanced_fields"]
            ]
            for field in INPUTS
        }
        model = HAZARD_MODELS[selected_hazard]
        fields = [(field, INPUTS[field]) for field in model["advanced_fields"]]
        columns = st.columns(2)
        for index, (field, specification) in enumerate(fields):
            hazards = ", ".join(field_hazards[field])
            with columns[index % 2]:
                submitted_values[field] = st.number_input(
                    f"{specification['label']} ({specification['unit']})",
                    min_value=specification["minimum"],
                    max_value=specification["maximum"],
                    value=None,
                    step=specification["step"],
                    format=specification["format"],
                    help=f"{specification['help']} Used for: {hazards}.",
                    key=f"advanced_{field}",
                )
        st.text_input(
            "Monitoring station and measurement reference",
            placeholder="Required if entering a water-level measurement",
            help=(
                "Name the gauge/sensor and its measurement datum for water level, "
                "rate of rise, or coastal level."
            ),
            key="water_level_reference",
        )
        water_level_reference = st.session_state.get("water_level_reference", "")
        st.text_input(
            "Measurement source (optional)",
            placeholder="Station, sensor, or official bulletin",
            help="Record where manually entered measurements came from.",
            key="measurement_source",
        )
        st.caption(
            "Location coordinates are not requested: user-supplied coordinates "
            "cannot currently be checked against a verified district boundary."
        )
        with st.expander("Local signs you have observed (optional)"):
            st.caption(
                "A reported warning is not checked against a live IMD or KSDMA feed."
            )
            for field in selected_simple_fields:
                specification = SIMPLE_INPUTS[field]
                assessment_observations[field] = st.selectbox(
                    specification["label"],
                    specification["options"],
                    index=None,
                    placeholder="No answer",
                    help=specification["help"],
                    key=f"advanced_observation_{field}",
                )
            assessment_observations = {
                field: value
                for field, value in assessment_observations.items()
                if value is not None
            }

    submitted = st.form_submit_button(
        "Assess local risks",
        type="primary",
        use_container_width=True,
    )

measurement_source = (
    st.session_state.get("measurement_source", "").strip()
    if input_mode == "advanced"
    else "User-reported local observations"
)
submission_signature = (
    selected_location,
    selected_hazard,
    input_mode,
    observation_time.isoformat(),
    tuple(sorted(submitted_values.items())),
    tuple(sorted(simple_observations.items())),
    tuple(sorted(assessment_observations.items())),
    water_level_reference,
    measurement_source,
)

if submitted:
    for key in (
        "input_prediction_results",
        "input_prediction_signature",
    ):
        st.session_state.pop(key, None)
    try:
        with st.spinner("Assessing the entered conditions…"):
            result = predict_hazard(
                selected_hazard,
                selected_location,
                submitted_values,
                water_level_reference=water_level_reference,
                input_mode=input_mode,
                simple_observations=simple_observations,
                assessment_observations=assessment_observations,
                observation_time=observation_time,
            )
    except InputValidationError as error:
        st.error("Please correct the environmental inputs before continuing.")
        for message in error.errors.values():
            st.write(f"- {message}")
    except (OSError, ValueError, TypeError) as error:
        st.error(f"The assessment could not be completed: {error}")
    else:
        st.session_state["input_prediction_results"] = [result]
        st.session_state["input_prediction_signature"] = submission_signature

results = st.session_state.get("input_prediction_results")
current_results = results if results else []


def _render_reference_evidence(result):
    evidence = result["reference_evidence"]
    st.markdown(f"**Historical/source status:** {evidence['status']}")
    st.markdown(f"**Observation period:** {evidence['observation_period']}")
    st.markdown(f"**Geographic coverage:** {evidence['spatial_coverage']}")
    st.markdown(f"**Record coverage:** {evidence['record_coverage']}")
    st.markdown("**What the available evidence says**")
    for finding in evidence["key_findings"]:
        st.markdown(f"- {finding}")
    if evidence["seasonal_pattern"] is None:
        st.markdown(
            f"**Seasonal evidence:** {evidence['seasonal_pattern_gap']}"
        )
    st.markdown(f"**Evidence uncertainty:** {evidence['uncertainty']}")
    for source in evidence["sources"]:
        source_name = source.get("title", source.get("name", "Source"))
        st.markdown(f"**Source:** [{source_name}]({source['url']})")
        if source.get("reuse_note"):
            st.caption(source["reuse_note"])

    scenarios = evidence.get("historical_scenario")
    if scenarios:
        st.markdown("**KSDMA district-wide historical flood scenario**")
        st.caption(
            "Modeled affected area by return period. This is historical scenario "
            "context for all of Ernakulam—not a current prediction or a result for "
            "the selected municipality/local body."
        )
        chart_data = {
            "Return period": [
                f"{item['return_period_years']}-year" for item in scenarios
            ],
            "Affected area (sq km)": [
                item["area_affected_sq_km"] for item in scenarios
            ],
        }
        st.bar_chart(
            chart_data,
            x="Return period",
            y="Affected area (sq km)",
            height=230,
        )
        st.caption(
            f"Source snapshot retrieved {evidence['source_retrieved_on']}. "
            "KSDMA's published scenario outputs do not describe the selected "
            "locality or current conditions."
        )


def _render_probability_indicator(result):
    """Render a consistent percentage indicator without converting risk tiers."""
    probability = validated_probability(result)
    if probability is None:
        st.markdown(
            '<div class="probability-panel">'
            '<div class="probability-label">Modelled event probability</div>'
            '<div class="probability-unavailable">Insufficient validated data</div>'
            '<div>No calibrated, location-matched model output is available for these inputs.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.caption(
            "The displayed risk category is a preliminary evidence assessment, "
            "not a percentage or forecast."
        )
        return

    percentage = probability * 100
    st.markdown(
        '<div class="probability-panel">'
        '<div class="probability-label">Validated model probability</div>'
        f'<div class="probability-value">{percentage:.1f}%</div>'
        '<div>Estimated chance of the model-defined event within its forecast horizon.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.progress(
        probability,
        text=f"{percentage:.1f}% · {result['forecast_horizon']}",
    )
    st.caption(
        "This percentage is a calibrated model output for the selected location and inputs; "
        "it is not a historical frequency or official warning."
    )


if current_results:
    st.markdown("### Assessment results")
    st.caption(
        f"{selected_location} · {observation_time:%d %b %Y, %H:%M} IST · "
        f"Input mode: {mode_label.title()} · "
        f"Source: {measurement_source or 'manually entered measurements (not specified)'}"
    )
    st.info(
        "Percentage cards are shown only for validated, calibrated model outputs. "
        "When that evidence is unavailable, the page shows Insufficient validated data "
        "rather than converting a category or score into a probability. No live conditions "
        "were retrieved."
    )
    result_columns = st.columns(2)
    for index, result in enumerate(current_results):
        with result_columns[index % 2]:
            with st.container(border=True):
                st.markdown(f"#### {result['icon']} {result['hazard_name']}")
                _render_probability_indicator(result)
                st.metric("Risk category", result["risk_label"])
                st.caption(
                    f"{result['assessment_method']} · {result['forecast_horizon']}"
                )
                st.write(result["explanation"])
                with st.expander("Evidence, uncertainty, and precautions"):
                    st.markdown("**Conditions used**")
                    for condition in result["contributing_conditions"]:
                        st.markdown(f"- {condition}")
                    st.markdown("**Important missing information**")
                    for item in result["missing_information"]:
                        st.markdown(f"- {item}")
                    st.markdown(f"**Precautions:** {result['precautions']}")
                    st.markdown(f"**Assessment limits:** {result['assessment_basis']}")
                    for limitation in result["limitations"]:
                        st.markdown(f"- {limitation}")
                    if result["sources"]:
                        st.markdown("**Measurement thresholds/reference**")
                        for source in result["sources"]:
                            st.markdown(f"- [{source['name']}]({source['url']})")
                    guidance = HAZARD_GUIDANCE[result["hazard_id"]]
                    st.markdown(
                        f"**What would improve this assessment:** "
                        f"{guidance['next_step']}"
                    )
                    st.markdown("**Ernakulam evidence context**")
                    _render_reference_evidence(result)
                st.caption(f"Data quality: {result['data_quality']}")
else:
    st.caption(
        "Submit the selected hazard's observations to see its assessment. "
        "A missing reading will remain unknown, not be treated as zero."
    )

with st.expander("Technical details and model readiness"):
    st.markdown(
        "Each hazard has an independent prediction target and model-artifact path. "
        "A model is used only when its Ernakulam coverage, genuine positive and "
        "negative labels, chronological validation, calibration, baseline "
        "comparison, and input schema pass the release checks."
    )
    st.markdown(
        "When a model is absent or not suitable, the shared engine returns a "
        "hazard-specific preliminary assessment. These concern categories are "
        "not probabilities, and no numerical score is shown because no locally "
        "validated scoring scale exists."
    )
    try:
        readiness = data_readiness_summary()
    except (OSError, ValueError) as error:
        st.error(f"Model readiness details could not be loaded: {error}")
    else:
        st.write(
            "Genuine Ernakulam records used by input-prediction models: "
            + ", ".join(
                f"{HAZARD_MODELS[hazard_id]['label']}: {count}"
                for hazard_id, count in readiness["input_model_records_used"].items()
            )
        )
        st.write(
            "Trained hazard-specific artifacts present: "
            + (
                ", ".join(
                    HAZARD_MODELS[hazard_id]["label"]
                    for hazard_id, exists in readiness["registered_artifacts"].items()
                    if exists
                )
                or "none"
            )
        )
        evaluated_results = [
            result
            for result in current_results
            if result["status"] == "validated_prediction"
        ]
        if evaluated_results:
            st.markdown("**Evaluation of models used for this submission**")
            for result in evaluated_results:
                metrics = result["metrics"]
                st.write(
                    f"{result['hazard_name']}: "
                    f"precision {metrics['precision']:.3f}, "
                    f"recall {metrics['recall']:.3f}, "
                    f"F1 {metrics['f1']:.3f}, "
                    f"ROC-AUC {metrics['roc_auc']:.3f}, "
                    f"PR-AUC {metrics['pr_auc']:.3f}, "
                    f"Brier score {metrics['brier_score']:.3f}."
                )
        else:
            st.write(
                "No validated Ernakulam model metrics are available because no "
                "qualifying input-prediction model artifact is registered."
            )

    st.markdown(
        "**Hazard-specific inputs:** Flood needs accumulated and forecast rainfall, "
        "rainfall duration, datum-referenced water-level trends, and drainage/tide "
        "context. Cyclone impacts need official track/intensity and coastal exposure. "
        "Landslides need antecedent rainfall, slope, soil and geology. Drought needs "
        "multi-week rainfall deficits and water availability. The common weather "
        "measurements alone are insufficient for validated predictions."
    )
    st.markdown(
        "**Existing research artifacts are excluded:** the flood baseline estimates "
        "severity after gauge events, not local flood occurrence. Regional weather "
        "baselines are not validated for the Ernakulam input workflow. Cyclone and "
        "landslide catalogues lack representative local non-event labels, and a "
        "verified district drought outcome series is not available."
    )
    st.markdown(
        "**Location coverage:** the selector contains Ernakulam district, 13 "
        "municipalities, 82 grama panchayats, and Kochi Corporation from verified "
        "administrative registers. No current model is validated for the district "
        "or any selected local body."
    )

st.caption(
    "This prototype is not an official forecast or emergency warning. Follow "
    "[IMD](https://mausam.imd.gov.in/) and "
    "[KSDMA](https://sdma.kerala.gov.in/) alerts."
)

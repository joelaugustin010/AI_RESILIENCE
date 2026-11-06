"""Integrated Kochi cyclone, flood and compound-impact planning workspace."""
from __future__ import annotations

import json
from datetime import date

import pandas as pd
import streamlit as st

from src.compound_hazard_assessment import assess_compound_scenario
from src.hazard_registry import WORKFLOW_HAZARDS
from src.dataframe_display import display_dataframe
from src.ui_theme import page_header


def _render_shared_ml_evidence(selected_hazards: list[str]) -> None:
    """Show the exploratory compound-association card, never a joint forecast."""
    st.markdown("#### Shared ML association evidence (exploratory)")
    try:
        from src.ml.registry import load_model_card
        from src.ml.service import ml_evidence_for
    except Exception as exc:  # deployment may omit optional ML artifacts
        st.info(f"Shared ML evidence is unavailable: {type(exc).__name__}: {exc}")
        return
    try:
        for selected_hazard in selected_hazards:
            if selected_hazard == "Compound: cyclone + flood":
                continue
            item = ml_evidence_for(selected_hazard, {})
            st.write("**" + selected_hazard + ":** " + str(item.get("status", "unknown")).replace("_", " ").capitalize())
            st.caption(item.get("interpretation", ""))
        evidence = ml_evidence_for("Compound: cyclone + flood", {})
    except Exception as exc:
        st.info(f"Shared ML evidence could not be loaded: {type(exc).__name__}: {exc}")
        return
    st.write(
        "**ML status:**",
        str(evidence.get("status", "unknown")).replace("_", " ").capitalize(),
    )
    st.caption(evidence.get("interpretation", ""))
    card = load_model_card("compound_cyclone_rainfall_interaction")
    if not card:
        st.info(
            "No shared compound-association model is present in this deployment. "
            "The scenario review remains a separate evidence exercise."
        )
        return
    st.write("**Model status:**", card.get("status", "Unknown"))
    st.write("**Evidence tier:**", card.get("evidence_tier", "Unknown"))
    st.write("**Research target:**", card.get("target_definition", "Not documented"))
    st.caption(card.get("status_reason", ""))

    metrics = card.get("metrics", {})
    ablation = metrics.get("ablation")
    if isinstance(ablation, dict) and ablation.get("available"):
        st.markdown("**Ablation: does cyclone proximity add incremental skill?**")
        display_dataframe(
            pd.DataFrame(
                [
                    {
                        "Model": "Full association model",
                        "Test ROC-AUC": ablation.get("full_test_roc_auc"),
                        "Test PR-AUC": ablation.get("full_test_average_precision"),
                    },
                    {
                        "Model": "Reduced seasonal + prior-rainfall model",
                        "Test ROC-AUC": ablation.get("reduced_test_roc_auc"),
                        "Test PR-AUC": ablation.get("reduced_test_average_precision"),
                    },
                ]
            ),
            hide_index=True,
            width="stretch",
            alt="Ablation comparing the full compound association model with a reduced model that removes cyclone features",
        )
        delta = ablation.get("delta_average_precision")
        if isinstance(delta, (int, float)) and delta <= 0.02:
            st.warning(
                "Removing every cyclone feature changes test PR-AUC by "
                f"{delta:+.3f}. On this holdout, cyclone proximity has no demonstrated "
                "incremental ranking skill beyond season and prior rainfall. The "
                "unadjusted association below must not be read as a compound effect."
            )
        else:
            st.info(
                f"The full model's test PR-AUC is {delta:+.3f} higher than the reduced "
                "seasonal/prior-rainfall model. This is an exploratory difference on one "
                "holdout, not evidence of a causal or forecastable compound effect."
            )

    association = metrics.get("association_analysis")
    if isinstance(association, dict):
        st.markdown("**Unadjusted cyclone-near / extreme-rain association**")
        rows = []
        for split, label in (("final_train", "Training era"), ("test", "Test era")):
            item = association.get(split, {})
            table = item.get("table", {})
            rows.append(
                {
                    "Period": label,
                    "Exposed + event": table.get("exposed_event"),
                    "Exposed + no event": table.get("exposed_no_event"),
                    "Unexposed + event": table.get("unexposed_event"),
                    "Unexposed + no event": table.get("unexposed_no_event"),
                    "Odds ratio (Haldane)": item.get("odds_ratio_haldane_corrected"),
                    "Fisher exact p": item.get("fisher_exact_p_value"),
                }
            )
        display_dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            width="stretch",
            alt="Unadjusted two-by-two association between cyclone proximity and extreme rainfall",
        )
        st.caption(
            "Concurrent exposure and outcome; season and prior rainfall are unresolved "
            "confounders. The test-era interval is wide and compatible with no association."
        )
    st.warning(
        "No compound probability, joint return period, flood depth, or impact estimate "
        "is produced from these inputs. The association model is exploratory and has no "
        "forecast lead time."
    )


page_header(
    "AI RESILIENCE · COMPOUND HAZARD WORKSPACE",
    "Kochi Cyclone + Flood Resilience Workspace",
    "One integrated workspace for rainfall, river flooding, cyclone exposure, compound "
    "pathways and service continuity.",
    meta=("Kochi · Ernakulam", "Cyclone + flood", "Research prototype"),
    accent="violet",
    key="compound-scenario",
)

st.warning(
    "Research and planning prototype only. It does not issue warnings or calculate validated "
    "hazard probabilities, inundation depths, damage or casualties. Follow official IMD, CWC, "
    "KSDMA and local-authority instructions for real safety decisions."
)

st.markdown(
    """
    **How this workspace works:** record whether the case is hypothetical, historical or based on
    current observations; add source and timing; review flood and cyclone pathways together;
    then inspect consequences and preparedness actions for critical services. Blank or unknown
    inputs remain explicit data gaps.
    """
)

with st.form("compound_scenario_form"):
    st.subheader("1. Define the event")
    area = st.text_input("Study area", value="Kochi / Ernakulam")
    hazards = st.multiselect("Hazards in this scenario", list(WORKFLOW_HAZARDS), default=["Flood", "Cyclone"], help="Select any of the ten registered hazards, including multiple hazards and registered compound scenarios.")
    custom_disaster = st.text_input("Custom disaster (optional)", placeholder="Describe an unregistered disaster; it receives a qualitative review only.")
    evidence_type = st.selectbox(
        "Evidence type",
        ["Hypothetical scenario", "Historical event", "Current sourced observations", "Official forecast product"],
    )
    col1, col2 = st.columns(2)
    with col1:
        period_start = st.date_input("Scenario period — start", value=date.today())
    with col2:
        period_end = st.date_input("Scenario period — end", value=date.today())
    observation_time = st.text_input(
        "Observation / bulletin issue time and timezone",
        placeholder="Example: 2026-11-02 10:00 IST",
    )
    evidence_source = st.text_input(
        "Source URL or document reference",
        placeholder="Official IMD / CWC / KSDMA source or project dataset record",
    )
    forecast_issue_time = st.text_input("Forecast bulletin issue time (if applicable)", placeholder="Preserve exact source timezone")
    forecast_valid_time = st.text_input("Forecast valid time (if applicable)", placeholder="When the forecast conditions apply")


    st.divider()
    st.subheader("2. Flood and rainfall evidence")
    st.caption("Leave unknown values blank. Do not enter an estimated value as an observation.")
    c1, c2 = st.columns(2)
    with c1:
        rainfall_mm = st.text_input("Rainfall (mm)", placeholder="Observed accumulation")
        rainfall_period = st.text_input("Rainfall accumulation period", placeholder="Example: 24 h")
        rainfall_station_id = st.text_input("Rainfall station ID")
        rainfall_reference_mm = st.text_input("Documented rainfall reference (mm)", placeholder="Optional; same station and period")
        rainfall_reference_station_id = st.text_input("Reference rainfall station ID")
        rainfall_reference_period = st.text_input("Reference accumulation period", placeholder="Must match the observation period exactly")
    with c2:
        river_level_m = st.text_input("River level (m)", placeholder="Gauge observation")
        river_gauge_id = st.text_input("River gauge ID")
        river_gauge_datum = st.text_input("River gauge datum / reference")
        river_reference_level_m = st.text_input("Official gauge reference / danger level (m)", placeholder="Optional; same gauge and datum")

    st.divider()
    st.subheader("3. Cyclone and coastal evidence")
    c1, c2 = st.columns(2)
    with c1:
        cyclone_distance_km = st.text_input("Cyclone track distance from study area (km)", placeholder="Source-derived; specify track time")
        cyclone_fix_time = st.text_input("Cyclone track-fix timestamp")
        cyclone_storm_id = st.text_input("Cyclone storm ID / name")
        cyclone_wind_knots = st.text_input("Recorded / forecast wind speed (knots)", placeholder="Preserve source definition and time")
    with c2:
        coastal_water_notes = st.text_area(
            "Coastal water, tide, surge or outfall evidence",
            placeholder="Record source, timestamp, location and whether observed or forecast.",
        )

    st.divider()
    st.subheader("4. Services and infrastructure to review")
    services = st.multiselect(
        "Select exposed services",
        ["Hospitals", "Roads and bridges", "Electricity", "Drinking water", "Communications",
         "Shelters", "Schools", "Drainage", "Industrial facilities"],
        default=["Hospitals", "Roads and bridges", "Electricity", "Drainage"],
    )
    submitted = st.form_submit_button("Generate integrated scenario review", type="primary")

if submitted:
    try:
        result = assess_compound_scenario({
            "area": area,
            "hazards": hazards,
            "custom_disaster": custom_disaster,
            "evidence_type": evidence_type,
            "period_start": period_start,
            "period_end": period_end,
            "observation_time": observation_time,
            "evidence_source": evidence_source,
            "forecast_issue_time": forecast_issue_time,
            "forecast_valid_time": forecast_valid_time,
            "rainfall_mm": rainfall_mm,
            "rainfall_period": rainfall_period,
            "rainfall_station_id": rainfall_station_id,
            "rainfall_reference_mm": rainfall_reference_mm,
            "rainfall_reference_station_id": rainfall_reference_station_id,
            "rainfall_reference_period": rainfall_reference_period,
            "river_level_m": river_level_m,
            "river_gauge_id": river_gauge_id,
            "river_gauge_datum": river_gauge_datum,
            "river_reference_level_m": river_reference_level_m,
            "cyclone_distance_km": cyclone_distance_km,
            "cyclone_fix_time": cyclone_fix_time,
            "cyclone_storm_id": cyclone_storm_id,
            "cyclone_wind_knots": cyclone_wind_knots,
            "coastal_water_notes": coastal_water_notes,
            "services": services,
        })
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.divider()
        st.subheader("Integrated assessment")
        st.info("Status: scenario review only — not a validated forecast.")
        if result["compound"]:
            st.success("Both hazards are selected. Compound interaction pathways are included in this review.")
        else:
            st.info("Only one hazard is selected; compound interaction analysis is not applicable.")

        st.markdown("#### Hazard pathways")
        for item in result["pathways"]:
            with st.expander(item["hazard"], expanded=True):
                st.write(item["pathway"])

        st.markdown("#### Supplied evidence and reference comparisons")
        st.json(result["reported_inputs"])
        if result["reference_comparisons"]:
            for item in result["reference_comparisons"]:
                st.write(
                    f"**{item['measure']}:** {item['result']} "
                    f"({item['observed']} compared with supplied reference {item['reference']})."
                )
                st.caption(item["warning"])
        else:
            st.caption("No threshold comparison was made. A reference level is never assumed or invented.")

        _render_shared_ml_evidence(hazards)

        st.markdown("#### Possible consequences to investigate")
        for item in result["service_reviews"]:
            with st.expander(item["service"], expanded=True):
                for point in item["review_points"]:
                    st.write(f"- {point}")

        st.markdown("#### Action framework")
        before, during, after = st.columns(3)
        with before:
            st.markdown("**Before**")
            for action in result["actions"]["before"]:
                st.write(f"- {action}")
        with during:
            st.markdown("**During**")
            for action in result["actions"]["during"]:
                st.write(f"- {action}")
        with after:
            st.markdown("**After**")
            for action in result["actions"]["after"]:
                st.write(f"- {action}")

        st.markdown("#### Evidence still required")
        for gap in result["data_gaps"]:
            st.write(f"- {gap}")
        st.warning(result["interpretation"])
        st.download_button(
            "Download scenario review (JSON)",
            data=json.dumps(result, indent=2, ensure_ascii=False),
            file_name="ai_resilience_compound_cyclone_flood_review.json",
            mime="application/json",
        )

st.divider()
st.caption(
    "Scientific boundary: historical cyclone tracks, event-only flood records, rainfall observations "
    "and river gauges are not interchangeable. Prediction requires aligned issue times, valid times, "
    "verified locations, independent outcomes and held-out event evaluation. The workspace keeps "
    "these requirements visible rather than manufacturing a risk score."
)

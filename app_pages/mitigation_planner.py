"""Budget arithmetic for user-supplied intervention estimates."""

from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
from src.dataframe_display import display_dataframe

def format_inr(amount):
    amount = int(round(amount))
    number = str(abs(amount))

    if len(number) > 3:
        last_three = number[-3:]
        remaining = number[:-3]
        groups = []

        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]

        if remaining:
            groups.insert(0, remaining)

        number = ",".join(groups) + "," + last_three

    sign = "-" if amount < 0 else ""
    return f"₹{sign}{number}"

from src.decision_workflow import budget_summary
from src.mitigation_optimizer import optimize_portfolio
from src.mitigation_investment import score_investment_priority
from src.mitigation_intelligence import (
    design_recommendations,
    review_project_register,
)





from src.ui_theme import page_header, section_intro

page_header(
    "AI RESILIENCE · KOCHI · PLANNING WORKSPACE",
    "AI Mitigation Decision & Investment Platform",
    "An evidence-aware planning workspace combining historical-project ML estimates, "
    "budget-constrained portfolio scenarios, and transparent implementation tracking "
    "for flood-resilience investments across Kochi, Kerala.",
    meta=("Kochi · Kerala · India", "ML estimates when validated", "Human-reviewed scenarios"),
    accent="amber",
    key="mitigation-budget",
)




st.caption(
    "Planning worksheet • User-supplied estimates • "
    "Budget comparison only; no automatic effectiveness ranking"
)

# Compact AI-first intake styling
st.markdown(
    """
    <style>
    div[data-testid="stExpander"] details summary p {
        font-weight: 650;
        color: #174E55;
        font-size: 0.94rem;
    }
    div[data-testid="stMetric"] {
        background: rgba(220, 231, 232, 0.38);
        border: 1px solid rgba(23, 78, 85, 0.10);
        border-radius: 12px;
        padding: 10px 12px;
    }
    div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
        min-height: 2.8rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

budget = st.number_input("Available budget (INR)", min_value=0, value=0, step=100000)
st.caption("Enter estimates only when you have a source, date, scope, and unit basis. Blank cost means unknown.")


# ============================================================
# AI-FIRST PROJECT INTAKE AND PORTFOLIO
# ============================================================
columns = [
    "Intervention",
    "Location",
    "Project Status",
    "Priority",
    "Cost INR",
    "Source / estimate date",
    "Scope and unit",
    "Potential beneficiaries",
    "Evidence for risk reduction",
    "ML duration estimate",
    "Estimation method",
    "site_risk_severity",
    "urgency",
    "evidence_strength",
    "implementation_readiness",
]

if "mitigation_project_records" not in st.session_state:
    st.session_state["mitigation_project_records"] = []

cost_model = st.session_state.get("mitigation_cost_ml_model")
duration_model = st.session_state.get("mitigation_duration_ml_model")
cost_ready = bool(cost_model and cost_model.get("metrics", {}).get("beats_baseline"))
duration_ready = bool(duration_model and duration_model.get("metrics", {}).get("beats_baseline"))

section_intro(
    "AI project intake",
    "Build a mitigation project profile",
    "Create a project record once. Validated historical models may estimate cost and delivery; otherwise the record remains an unpredicted draft.",
)

status_cols = st.columns(3)
status_cols[0].metric("Historical cost model", "Ready" if cost_ready else "Awaiting evidence")
status_cols[1].metric("Delivery model", "Ready" if duration_ready else "Awaiting evidence")
status_cols[2].metric("Projects in portfolio", len(st.session_state["mitigation_project_records"]))

if not cost_ready:
    st.info(
        "AI cost estimates are currently locked. Upload at least 40 complete, traceable "
        "completed-project records in the ML workspace below, train the model, and pass "
        "the holdout baseline check. Until then, projects can be saved as drafts without "
        "invented AI estimates."
    )

cost_categories = cost_model.get("categories", {}) if cost_ready else {}
duration_categories = duration_model.get("categories", {}) if duration_ready else {}
intervention_options = sorted(set(
    (cost_categories.get("intervention", []) or [])
    + (duration_categories.get("intervention", []) or [])
    + ["Drainage maintenance / upgrade", "Hospital resilience", "Evacuation infrastructure", "Building retrofit"]
))
area_options = sorted(set(
    (cost_categories.get("area_type", []) or [])
    + (duration_categories.get("area_type", []) or [])
    + ["Low-lying flood-prone area", "Urban road", "Residential neighbourhood", "Commercial area"]
))
unit_options = sorted(set(
    (cost_categories.get("scope_unit", []) or [])
    + (duration_categories.get("scope_unit", []) or [])
    + ["metres", "square metres", "units", "sites"]
))

with st.container(border=True):
    st.markdown("#### 01 · Define the intervention")
    with st.form("mitigation_ai_project_intake", clear_on_submit=True):
        form_cols = st.columns(2)
        project_name = form_cols[0].selectbox("Intervention type", intervention_options)
        project_location = form_cols[1].text_input(
            "Kochi project location",
            placeholder="e.g. ward, road, neighbourhood or facility",
        )
        area_type = form_cols[0].selectbox("Area context", area_options)
        scope_unit = form_cols[1].selectbox("Scope measurement unit", unit_options)
        scope_quantity = st.number_input(
            "Scope quantity", min_value=0.0, value=100.0, step=10.0
        )
        st.markdown("##### Investment assessment · human-reviewed inputs")
        score_cols = st.columns(2)
        assessment_options = ["Not assessed", 1, 2, 3, 4, 5]
        site_risk_severity = score_cols[0].selectbox(
            "Site risk severity (1–5)", options=assessment_options, index=0,
            help="Use a documented local risk assessment. 1 = lower assessed severity; 5 = highest assessed severity."
        )
        urgency = score_cols[1].selectbox(
            "Urgency (1–5)", options=assessment_options, index=0,
            help="1 = can be scheduled later; 5 = time-critical based on documented conditions."
        )
        evidence_strength = score_cols[0].selectbox(
            "Evidence strength (1–5)", options=assessment_options, index=0,
            help="1 = preliminary / anecdotal; 5 = strong, traceable site-specific evidence."
        )
        implementation_readiness = score_cols[1].selectbox(
            "Implementation readiness (1–5)", options=assessment_options, index=0,
            help="Consider design, permissions, land, responsible owner and delivery arrangements."
        )
        with st.expander("Optional details · quotation and evidence", expanded=False):
            manual_cost = st.number_input(
                "Known quotation / manual cost (₹)", min_value=0.0, value=0.0, step=10000.0,
                help="Optional fallback for a draft. Leave at zero when unknown."
            )
            source_reference = st.text_input(
                "Quotation / survey / source reference",
                placeholder="Add a traceable reference, if available",
            )
            risk_evidence = st.text_area(
                "Supporting site or risk evidence",
                placeholder="Describe the site issue or cite a survey, report or assessment.",
                height=90,
            )

        submit_project = st.form_submit_button(
            "Create project profile",
            type="primary",
            use_container_width=True,
        )

    if submit_project:
        if not project_location.strip():
            st.warning("Add the project location before creating the profile.")
        elif scope_quantity <= 0:
            st.warning("Scope quantity must be greater than zero.")
        else:
            estimated_cost = float(manual_cost) if manual_cost > 0 else None
            estimated_duration = None
            method_parts = []

            if cost_ready:
                try:
                    cost_result = estimate_cost(
                        cost_model,
                        intervention=project_name,
                        area_type=area_type,
                        scope_quantity=scope_quantity,
                        scope_unit=scope_unit,
                    )
                    estimated_cost = float(cost_result["estimated_cost_inr"])
                    method_parts.append("ML cost estimate")
                except CostModelDataError as exc:
                    st.warning(f"Cost model could not estimate this profile: {exc}")

            if duration_ready and estimated_cost is not None:
                try:
                    duration_result = estimate_duration(
                        duration_model,
                        intervention=project_name,
                        area_type=area_type,
                        scope_quantity=scope_quantity,
                        scope_unit=scope_unit,
                        estimated_cost_inr=estimated_cost,
                    )
                    estimated_duration = float(duration_result["estimated_duration_months"])
                    method_parts.append("ML duration estimate")
                except CostModelDataError as exc:
                    st.warning(f"Duration model could not estimate this profile: {exc}")

            if not method_parts and estimated_cost is None:
                method_parts.append("Draft · awaiting validated ML models")
            elif not method_parts:
                method_parts.append("User-entered quotation · not an ML estimate")

            record = {
                "Intervention": project_name,
                "Location": project_location.strip(),
                "Project Status": "Proposed",
                "Priority": "Not assessed",
                "Cost INR": estimated_cost,
                "Source / estimate date": (
                    ("ML estimate · validation required" if "ML cost estimate" in method_parts
                     else source_reference.strip())
                ),
                "Scope and unit": f"{scope_quantity:g} {scope_unit}",
                "Potential beneficiaries": None,
                "Evidence for risk reduction": risk_evidence.strip(),
                "ML duration estimate": estimated_duration,
                "Estimation method": " + ".join(method_parts),
                "site_risk_severity": site_risk_severity,
                "urgency": urgency,
                "evidence_strength": evidence_strength,
                "implementation_readiness": implementation_readiness,
            }
            record["Priority"] = score_investment_priority(record)["band"]
            st.session_state["mitigation_project_records"].append(record)
            st.success(
                "Project profile added. "
                + ("ML estimates were generated where eligible." if any("ML" in x for x in method_parts)
                   else "No AI prediction was fabricated; this remains a draft.")
            )
            st.rerun()

plan = pd.DataFrame(st.session_state["mitigation_project_records"], columns=columns)

section_intro(
    "Investment intelligence",
    "Evidence-aware project prioritisation",
    "Compare projects using explicit human assessments of site risk, urgency, evidence and implementation readiness. Incomplete assessments are not scored.",
)
if plan.empty:
    st.info("Add project profiles to build an investment shortlist.")
else:
    ranked_rows = []
    for _, project in plan.iterrows():
        assessment = score_investment_priority(project.to_dict())
        ranked_rows.append({
            "Project": project.get("Intervention", "Unnamed"),
            "Location": project.get("Location", "Not specified"),
            "Priority score": assessment["score"],
            "Assessment": assessment["band"],
            "Risk (1–5)": assessment["criteria"].get("site_risk_severity", "—"),
            "Urgency (1–5)": assessment["criteria"].get("urgency", "—"),
            "Evidence (1–5)": assessment["criteria"].get("evidence_strength", "—"),
            "Readiness (1–5)": assessment["criteria"].get("implementation_readiness", "—"),
            "Missing assessments": "; ".join(assessment["missing"]) or "None",
        })
    ranked_df = pd.DataFrame(ranked_rows)
    scored_df = ranked_df[ranked_df["Priority score"].notna()].sort_values(
        "Priority score", ascending=False
    )
    score_cols = st.columns(3)
    score_cols[0].metric("Projects assessed", len(scored_df))
    score_cols[1].metric("Awaiting assessment", len(ranked_df) - len(scored_df))
    score_cols[2].metric(
        "Highest assessed score",
        f"{scored_df['Priority score'].max():.1f}/100" if not scored_df.empty else "—",
    )
    if not scored_df.empty:
        st.markdown("#### Ranked investment shortlist")
        display_dataframe(scored_df, hide_index=True, use_container_width=True)
    incomplete_df = ranked_df[ranked_df["Priority score"].isna()]
    if not incomplete_df.empty:
        with st.expander(f"Projects needing assessment ({len(incomplete_df)})", expanded=False):
            display_dataframe(incomplete_df, hide_index=True, use_container_width=True)
    st.caption(
        "Method: site risk 35%, urgency 25%, evidence strength 20%, implementation readiness 20%. "
        "Each input is a human assessment on a 1–5 scale. This is a transparent prioritisation aid, "
        "not an ML prediction, measured effectiveness score, or funding approval."
    )

section_intro("Project portfolio", "Mitigation project portfolio")
st.caption(
    "Projects are shown as individual profiles rather than an editable spreadsheet. "
    "AI estimates are separated from user-entered values and require local verification."
)

if plan.empty:
    st.info("No projects have been added yet. Use the project-intake panel above to create the first profile.")
else:
    for idx, project in plan.iterrows():
        with st.container(border=True):
            top_cols = st.columns([3, 1])
            top_cols[0].markdown(f"**{project['Intervention']}**")
            top_cols[0].caption(f"{project['Location']} · {project['Project Status']}")
            top_cols[1].markdown(f"**{project['Estimation method']}**")
            priority_assessment = score_investment_priority(project.to_dict())
            metric_cols = st.columns(3)
            metric_cols[0].metric(
                "Cost estimate",
                format_inr(project["Cost INR"]) if pd.notna(project["Cost INR"]) else "Awaiting data",
            )
            metric_cols[1].metric(
                "Delivery estimate",
                f"{float(project['ML duration estimate']):.1f} months"
                if pd.notna(project["ML duration estimate"]) else "Awaiting data",
            )
            metric_cols[2].metric(
                "Investment priority",
                f"{priority_assessment['score']:.1f}/100" if priority_assessment["score"] is not None else "Needs assessment",
                help=priority_assessment["explanation"],
            )
            st.caption(
                f"Scope: {project['Scope and unit']} · "
                f"Evidence: {project['Evidence for risk reduction'] or 'Not supplied'}"
            )
            if st.button("Remove project", key=f"remove_mitigation_project_{idx}"):
                st.session_state["mitigation_project_records"].pop(idx)
                st.rerun()

# ==========================================
with st.expander("Connected Design Studio review", expanded=False):
    # SHARED DESIGN + PROJECT REGISTER INTELLIGENCE
    # ==========================================
    
    st.markdown("---")
    section_intro("Review", "Mitigation planning intelligence")
    st.caption(
        "A transparent review of the project register, with the latest concept "
        "configuration shared from the Smart Mitigation Design Studio when available."
    )
    
    design_state = st.session_state.get("mitigation_design_state")
    
    if design_state:
        st.markdown("#### Connected Design Studio configuration")
        design_cols = st.columns(4)
        design_cols[0].metric("Design area", design_state["area_type"])
        design_cols[1].metric(
            "Illustrative rainfall",
            f"{design_state['rainfall_input_mm_per_hour']:g} mm/h"
        )
        design_cols[2].metric(
            "Selected component cost",
            format_inr(design_state["illustrative_component_cost_inr"])
        )
        design_cols[3].metric("Design budget status", design_state["budget_status"])
    
        st.caption(
            f"Shared project: {design_state['project_name']} · "
            f"Model version {design_state['model_version']}"
        )
    
        st.markdown("#### Explainable planning prompts")
        for item in design_recommendations(design_state):
            with st.container(border=True):
                st.markdown(
                    f"**{item['Priority']} priority · {item['Planning recommendation']}**"
                )
                st.write(item["Why this was suggested"])
                st.caption(f"Verification step: {item['Suggested verification']}")
    else:
        st.info(
            "Open the Smart Mitigation Design Studio and configure a concept to "
            "share its current settings with this planning page. Your project "
            "register remains available independently."
        )

with st.expander("Train and evaluate the ML cost model", expanded=False):
    # ============================================================
    # EVIDENCE-GATED MACHINE-LEARNING COST ESTIMATOR
    # ============================================================
    st.markdown(
        """
        <style>
        /* Mitigation ML workspace: local contrast and hierarchy improvements */
        [data-testid="stMain"] div[data-testid="stDownloadButton"] button {
            min-height: 3.1rem !important;
            padding: .65rem 1.1rem !important;
            background: #174E55 !important;
            border: 1px solid #174E55 !important;
            border-radius: 12px !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            font-size: .96rem !important;
            letter-spacing: .01em !important;
            box-shadow: 0 5px 14px rgba(23,78,85,.16) !important;
        }
        [data-testid="stMain"] div[data-testid="stDownloadButton"] button * {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            opacity: 1 !important;
            visibility: visible !important;
        }
        [data-testid="stMain"] div[data-testid="stDownloadButton"] button:hover {
            background: #299B91 !important;
            border-color: #299B91 !important;
            color: #FFFFFF !important;
        }
        [data-testid="stMain"] .mitigation-ml-copy,
        [data-testid="stMain"] .mitigation-ml-copy p,
        [data-testid="stMain"] .mitigation-ml-copy li {
            color: #29484C !important;
            -webkit-text-fill-color: #29484C !important;
            font-size: .96rem !important;
            line-height: 1.65 !important;
        }
        [data-testid="stMain"] .mitigation-ml-kicker {
            color: #176F70 !important;
            font-size: .76rem !important;
            font-weight: 800 !important;
            letter-spacing: .11em !important;
            text-transform: uppercase !important;
        }
        [data-testid="stMain"] [data-testid="stMetricLabel"] p {
            color: #52666A !important;
            font-weight: 650 !important;
        }
        [data-testid="stMain"] [data-testid="stMetricValue"] {
            color: #174E55 !important;
            font-weight: 750 !important;
        }
        [data-testid="stMain"] div[data-testid="stFileUploader"] label,
        [data-testid="stMain"] div[data-testid="stFileUploader"] small {
            color: #29484C !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    from src.mitigation_cost_ml import CostModelDataError, estimate_cost, train_cost_model
    
    st.markdown("---")
    section_intro(
        "Cost intelligence · ML workspace",
        "Historical project cost estimator",
        "A supervised machine-learning workflow trained only on sourced, completed mitigation projects. "
        "It estimates indicative project cost—not flood-risk reduction, project effectiveness, or funding priority.",
    )
    
    with st.container(border=True):
        st.markdown('<div class="mitigation-ml-kicker">STEP 01 · DATA FOUNDATION</div>', unsafe_allow_html=True)
        st.markdown("#### Prepare the evidence")
        st.markdown(
            '<div class="mitigation-ml-copy">Upload one row per completed project. Use source-reported completed-project costs and consistent scope units; prefer final paid bills and document the cost basis in source notes. '
            'Each source reference should identify a traceable government report or project record.</div>',
            unsafe_allow_html=True,
        )
        template_columns = [
            "intervention", "area_type", "scope_quantity", "scope_unit",
            "duration_months", "actual_cost_inr", "source_reference",
        ]
        template_csv = pd.DataFrame(columns=template_columns).to_csv(index=False).encode("utf-8")
        bundled_dataset_path = (
            Path(__file__).resolve().parents[1]
            / "data" / "reference" / "kerala_soil_conservation_completed_projects.csv"
        )
        bundled_dataset_bytes = (
            bundled_dataset_path.read_bytes() if bundled_dataset_path.exists() else None
        )
        prep_cols = st.columns([1, 1, 2])
        with prep_cols[0]:
            st.download_button(
                "Download CSV template  ↓",
                data=template_csv,
                file_name="AI_RESILIENCE_historical_mitigation_costs_template.csv",
                mime="text/csv",
                key="mitigation_ml_template",
                use_container_width=True,
                type="primary",
            )
        with prep_cols[1]:
            if bundled_dataset_bytes is not None:
                st.download_button(
                    "Download Kerala source dataset",
                    data=bundled_dataset_bytes,
                    file_name="AI_RESILIENCE_Kerala_Government_Projects.csv",
                    mime="text/csv",
                    key="mitigation_ml_kerala_dataset",
                    use_container_width=True,
                )
        with prep_cols[2]:
            uploaded_cost_data = st.file_uploader(
                "Upload completed-project records",
                type=["csv"],
                help="Use source-reported completed-project costs, preferably final paid bills. Record whether each value is a final bill or a reported completion cost.",
                key="mitigation_ml_upload",
                label_visibility="visible",
            )
        st.markdown(
            '<div class="mitigation-ml-copy"><b>Required for cost ML:</b> intervention · area type · scope quantity · '
            'scope unit · source-reported completed-project cost · source reference. <b>Duration in months is optional for cost ML and required for delivery ML.</b></div>',
            unsafe_allow_html=True,
        )
    
    historical_records = None
    bundled_dataset_path = (
        Path(__file__).resolve().parents[1]
        / "data" / "reference" / "kerala_soil_conservation_completed_projects.csv"
    )
    if bundled_dataset_path.exists():
        historical_records = pd.read_csv(bundled_dataset_path)
    if uploaded_cost_data is not None or historical_records is not None:
        try:
            if uploaded_cost_data is not None:
                import hashlib
                upload_signature = hashlib.sha256(uploaded_cost_data.getvalue()).hexdigest()
                if st.session_state.get("mitigation_ml_upload_signature") != upload_signature:
                    st.session_state.pop("mitigation_cost_ml_model", None)
                    st.session_state.pop("mitigation_duration_ml_model", None)
                    st.session_state["mitigation_ml_upload_signature"] = upload_signature
                uploaded_cost_data.seek(0)
                historical_records = pd.read_csv(uploaded_cost_data)
            expected_columns = [
                "intervention", "area_type", "scope_quantity", "scope_unit",
                "actual_cost_inr", "source_reference",
            ]
            missing_columns = [name for name in expected_columns if name not in historical_records.columns]
            candidate_rows = 0
            duration_candidate_rows = 0
            if not missing_columns:
                candidate = historical_records[expected_columns].copy()
                candidate["scope_quantity"] = pd.to_numeric(candidate["scope_quantity"], errors="coerce")
                candidate["actual_cost_inr"] = pd.to_numeric(candidate["actual_cost_inr"], errors="coerce")
                cost_valid = (
                    candidate["intervention"].fillna("").astype(str).str.strip().ne("")
                    & candidate["area_type"].fillna("").astype(str).str.strip().ne("")
                    & candidate["scope_unit"].fillna("").astype(str).str.strip().ne("")
                    & candidate["source_reference"].fillna("").astype(str).str.strip().ne("")
                    & candidate["scope_quantity"].gt(0)
                    & candidate["actual_cost_inr"].gt(0)
                    & candidate["scope_quantity"].map(lambda value: pd.notna(value) and float(value) < float("inf"))
                    & candidate["actual_cost_inr"].map(lambda value: pd.notna(value) and float(value) < float("inf"))
                )
                candidate_rows = int(cost_valid.sum())
                if "duration_months" in historical_records.columns:
                    durations = pd.to_numeric(historical_records["duration_months"], errors="coerce")
                    duration_candidate_rows = int((cost_valid & durations.gt(0) & durations.map(
                        lambda value: pd.notna(value) and float(value) < float("inf")
                    )).sum())
            source_count = (
                historical_records["source_reference"].fillna("").astype(str).str.strip().ne("").sum()
                if "source_reference" in historical_records.columns else 0
            )
            with st.container(border=True):
                st.markdown('<div class="mitigation-ml-kicker">STEP 02 · QUALITY CHECK</div>', unsafe_allow_html=True)
                st.markdown("#### Dataset readiness")
                readiness_cols = st.columns(3)
                readiness_cols[0].metric("Uploaded records", f"{len(historical_records):,}")
                readiness_cols[1].metric("Valid cost records", f"{int(candidate_rows):,}")
                readiness_cols[2].metric("Valid duration records", f"{int(duration_candidate_rows):,}")
                if missing_columns:
                    st.warning("Missing columns: " + ", ".join(missing_columns))
                elif candidate_rows < 40:
                    st.warning(
                        f"{candidate_rows} complete, sourced cost records are currently usable. "
                        "At least 40 are required before cost-model evaluation. Duration training "
                        f"currently has {duration_candidate_rows} complete records and has its own 40-record gate."
                    )
                else:
                    st.info(
                        "The file has the required column names and enough rows to attempt validation. "
                        "Training will still reject incomplete, invalid, non-positive, or insufficiently varied records."
                    )
                with st.expander("Inspect uploaded records", expanded=False):
                    st.dataframe(historical_records.head(12), hide_index=True, use_container_width=True)
                    st.caption("Preview only. A non-empty source-reference field is not independently verified by this application.")
            if st.button(
                "Train and evaluate model",
                type="primary",
                key="train_mitigation_cost_model",
                use_container_width=True,
            ):
                try:
                    with st.spinner("Training the model and checking its holdout performance…"):
                        trained_cost_model = train_cost_model(historical_records)
                    st.session_state["mitigation_cost_ml_model"] = trained_cost_model
                    st.success("Training and holdout evaluation completed.")
                except CostModelDataError as exc:
                    st.session_state.pop("mitigation_cost_ml_model", None)
                    st.warning(str(exc))
        except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
            st.error(f"Could not read this CSV: {exc}")
    
    trained_cost_model = st.session_state.get("mitigation_cost_ml_model")
    if trained_cost_model:
        model_metrics = trained_cost_model["metrics"]
        st.markdown('<div class="mitigation-ml-kicker">STEP 03 · MODEL VALIDATION</div>', unsafe_allow_html=True)
        st.markdown("#### Model evaluation")
        with st.container(border=True):
            metric_cols = st.columns(4)
            metric_cols[0].metric("Training records", f"{model_metrics['training_records']:,}")
            metric_cols[1].metric("Holdout records", f"{model_metrics['validation_records']:,}")
            metric_cols[2].metric("Holdout MAE", format_inr(model_metrics["mae_inr"]))
            metric_cols[3].metric(
                "Median baseline MAE",
                format_inr(model_metrics["baseline_mae_inr"]),
            )
            st.caption(
                f"{model_metrics['validation_method']} · "
                f"R²: {model_metrics['r2']:.3f}" if pd.notna(model_metrics["r2"])
                else f"{model_metrics['validation_method']} · R² unavailable"
            )
            st.caption(
                "MAE is the average absolute cost error on held-out records. "
                "A single random holdout is an initial check, not proof of performance on every Kochi project."
            )
        if model_metrics["beats_baseline"]:
            st.success("Baseline check passed: the model had lower holdout MAE than the median-only baseline.")
            st.markdown('<div class="mitigation-ml-kicker">STEP 04 · COST SCENARIO</div>', unsafe_allow_html=True)
            st.markdown("#### Estimate a comparable project")
            st.caption(
                "Choose categories represented in the uploaded records and enter a scope comparable "
                "to the historical examples. Estimates outside that experience may be unreliable."
            )
            with st.container(border=True):
                with st.form("mitigation_ml_prediction_form"):
                    categories = trained_cost_model["categories"]
                    prediction_cols = st.columns(2)
                    chosen_intervention = prediction_cols[0].selectbox(
                        "Intervention type", categories["intervention"]
                    )
                    chosen_area = prediction_cols[1].selectbox(
                        "Area type", categories["area_type"]
                    )
                    chosen_unit = prediction_cols[0].selectbox(
                        "Scope measurement unit", categories["scope_unit"]
                    )
                    scope_quantity = prediction_cols[1].number_input(
                        "Scope quantity", min_value=0.0, value=100.0, step=10.0
                    )
                    predict_cost = st.form_submit_button(
                        "Generate cost estimate", type="primary", use_container_width=True
                    )
            if predict_cost:
                try:
                    cost_result = estimate_cost(
                        trained_cost_model,
                        intervention=chosen_intervention,
                        area_type=chosen_area,
                        scope_quantity=scope_quantity,
                        scope_unit=chosen_unit,
                    )
                    with st.container(border=True):
                        st.caption("MODEL-GENERATED INDICATIVE COST")
                        st.metric(
                            "Estimated project cost",
                            format_inr(cost_result["estimated_cost_inr"]),
                        )
                        st.write(
                            "**Indicative error range:** "
                            + format_inr(cost_result["lower_estimate_inr"])
                            + " – "
                            + format_inr(cost_result["upper_estimate_inr"])
                        )
                        st.caption(
                            "Range = estimate ± holdout MAE; it is not a statistical confidence interval."
                        )
                    st.warning(
                        "Planning aid only. Verify current local quotations, taxes, land, design, "
                        "procurement, inflation, and lifecycle maintenance costs before decisions."
                    )
                except CostModelDataError as exc:
                    st.error(str(exc))
        else:
            st.warning(
                "Model not approved for estimates: it did not beat the median-only baseline "
                "on held-out records. Add more representative, traceable completed-project data."
            )
    else:
        st.info(
            "ML is currently in data-waiting mode. No model is trained from the editable project register "
            "or illustrative starter rows. Upload sufficient historical records to begin evaluation."
        )

with st.expander("Train and evaluate the ML delivery model", expanded=False):
    # ============================================================
    # EVIDENCE-GATED PROJECT DURATION INTELLIGENCE
    # ============================================================
    from src.mitigation_duration_ml import estimate_duration, train_duration_model
    
    st.markdown("---")
    section_intro(
        "Delivery intelligence · ML workspace",
        "Historical project duration estimator",
        "Estimates indicative delivery time from comparable completed projects. "
        "This is a planning aid, not a contractor schedule or guarantee.",
    )
    
    if historical_records is None:
        st.info("Upload the same sourced completed-project dataset above to evaluate the duration model.")
    else:
        duration_train_col, duration_info_col = st.columns([1, 2])
        with duration_train_col:
            if st.button(
                "Train duration model",
                type="primary",
                key="train_mitigation_duration_model",
                use_container_width=True,
            ):
                try:
                    with st.spinner("Evaluating project-duration patterns on held-out records…"):
                        st.session_state["mitigation_duration_ml_model"] = train_duration_model(
                            historical_records
                        )
                    st.success("Duration model evaluation completed.")
                except CostModelDataError as exc:
                    st.session_state.pop("mitigation_duration_ml_model", None)
                    st.warning(str(exc))
        with duration_info_col:
            st.markdown(
                '<div class="mitigation-ml-copy">Uses intervention type, area type, '
                'scope quantity, measurement unit and estimated project cost. '
                'The model is enabled only when its holdout MAE beats a median-only baseline.</div>',
                unsafe_allow_html=True,
            )
    
    duration_model = st.session_state.get("mitigation_duration_ml_model")
    if duration_model:
        duration_metrics = duration_model["metrics"]
        with st.container(border=True):
            st.markdown("#### Delivery model evaluation")
            duration_metrics_cols = st.columns(4)
            duration_metrics_cols[0].metric("Training records", f"{duration_metrics['training_records']:,}")
            duration_metrics_cols[1].metric("Holdout records", f"{duration_metrics['validation_records']:,}")
            duration_metrics_cols[2].metric("Holdout MAE", f"{duration_metrics['mae_months']:.1f} months")
            duration_metrics_cols[3].metric("Median baseline MAE", f"{duration_metrics['baseline_mae_months']:.1f} months")
            st.caption(
                f"{duration_metrics['validation_method']} · "
                + (f"R²: {duration_metrics['r2']:.3f}" if pd.notna(duration_metrics["r2"]) else "R² unavailable")
            )
            st.caption(
                "Holdout error is an initial evaluation only. It is not a confidence interval, "
                "and performance on new locations or unusual projects may differ."
            )
        if duration_metrics["beats_baseline"]:
            st.success("Duration model passed its median-baseline comparison.")
            duration_categories = duration_model["categories"]
            with st.form("mitigation_duration_scenario"):
                duration_cols = st.columns(2)
                selected_intervention = duration_cols[0].selectbox(
                    "Intervention",
                    duration_categories["intervention"],
                    key="duration_intervention",
                )
                selected_area = duration_cols[1].selectbox(
                    "Area type",
                    duration_categories["area_type"],
                    key="duration_area",
                )
                selected_unit = duration_cols[0].selectbox(
                    "Scope unit",
                    duration_categories["scope_unit"],
                    key="duration_unit",
                )
                selected_quantity = duration_cols[1].number_input(
                    "Scope quantity",
                    min_value=0.1,
                    value=100.0,
                    step=10.0,
                    key="duration_quantity",
                )
                selected_cost = st.number_input(
                    "Estimated project cost (₹)",
                    min_value=1.0,
                    value=100000.0,
                    step=10000.0,
                    key="duration_cost",
                )
                run_duration = st.form_submit_button("Estimate delivery duration")
            if run_duration:
                try:
                    duration_result = estimate_duration(
                        duration_model,
                        intervention=selected_intervention,
                        area_type=selected_area,
                        scope_quantity=selected_quantity,
                        scope_unit=selected_unit,
                        estimated_cost_inr=selected_cost,
                    )
                    st.metric(
                        "Indicative delivery duration",
                        f"{duration_result['estimated_duration_months']:.1f} months",
                    )
                    st.caption(
                        f"Indicative historical-error range: "
                        f"{duration_result['lower_estimate_months']:.1f}–"
                        f"{duration_result['upper_estimate_months']:.1f} months "
                        f"(± holdout MAE; not a confidence interval)."
                    )
                except CostModelDataError as exc:
                    st.warning(str(exc))
        else:
            st.warning(
                "Duration predictions are disabled because the model did not beat "
                "the median-only baseline on held-out records."
            )
    else:
        st.info(
            "No duration model is trained yet. Train it only after uploading "
            "sufficient traceable completed-project records."
        )

with st.expander("Portfolio analytics, budget scenarios and exports", expanded=False):
    register_review = review_project_register(
        plan.to_dict(orient="records"),
        budget,
    )
    
    review_cols = st.columns(3)
    review_cols[0].metric("Projects reviewed", register_review["project_count"])
    review_cols[1].metric(
        "Known entered costs",
        format_inr(register_review["known_cost_total_inr"])
    )
    review_cols[2].metric(
        "Rows with unknown/invalid cost",
        register_review["unknown_cost_count"]
    )
    
    if register_review["review_rows"]:
        review_df = pd.DataFrame(register_review["review_rows"])
        st.markdown("#### Project register review")
        display_dataframe(review_df, hide_index=True, use_container_width=True)
    
    st.caption(register_review["interpretation"])
    
    if register_review["within_budget"] is True:
        st.success("Entered project costs fit within the entered budget (arithmetic check only).")
    elif register_review["within_budget"] is False:
        st.warning("Entered project costs exceed the entered budget (arithmetic check only).")
    else:
        st.info(
            "A complete budget-fit check is not available until a budget is entered "
            "and every project row has a valid cost."
        )
    
    st.info(
        "The adviser uses transparent rules and field-completeness checks. "
        "It does not rank project effectiveness, estimate avoided flood damage, "
        "or replace engineering and financial review."
    )
    
    section_intro("Expenditure", "Mitigation expenditure report")
    st.caption(
        "Estimated expenditure by proposed intervention. "
        "All amounts are based on user-entered project costs."
    )
    
    chart_data = plan[["Intervention", "Cost INR"]].copy()
    chart_data["Cost INR"] = pd.to_numeric(
        chart_data["Cost INR"], errors="coerce"
    )
    chart_data = chart_data.dropna(subset=["Cost INR"])
    chart_data = chart_data[chart_data["Cost INR"] >= 0]
    
    # Calculate the financial summary using the existing workflow
    summary = budget_summary(plan["Cost INR"], budget)
    total_known = float(summary["entered_total"])
    unknown_count = summary["unknown_or_invalid_count"]
    remaining = budget - total_known
    
    # Project cost indicators
    valid_project_count = len(chart_data)
    
    metric1, metric2, metric3 = st.columns(3)
    
    with metric1:
        st.metric("Projects with Cost Entries", f"{valid_project_count}")
    
    with metric2:
        st.metric("Total Estimated Expenditure", format_inr(total_known))
    
    with metric3:
        st.metric("Projects Requiring Cost Review", f"{unknown_count}")
    
    # Horizontal expenditure chart
    if not chart_data.empty:
        chart_data = chart_data.groupby(
            "Intervention", as_index=False
        )["Cost INR"].sum()
    
        chart_data = chart_data.sort_values(
            "Cost INR", ascending=True
        )
    
        st.markdown("#### Project-wise estimated expenditure")
        st.caption(
        "Comparison of proposed mitigation project costs in Indian Rupees (₹)."
        )
        
        
        fig = px.bar(
            chart_data,
            x="Cost INR",
            y="Intervention",
            orientation="h",
            title="Estimated Expenditure by Mitigation Project",
            labels={
                "Cost INR": "Estimated Cost (₹)",
                "Intervention": "Mitigation Project",
            },
            text="Cost INR",
            color="Cost INR",
            color_continuous_scale=["#0b4f5c", "#16a596", "#42e0c1"],
            template="plotly_white",
        )
    
        fig.update_traces(
            texttemplate="₹%{x:,.0f}",
            textposition="outside",
            cliponaxis=False,
            marker_line_width=0,
        )
    
        fig.update_layout(
            height=max(350, 75 * len(chart_data)),
            margin=dict(l=20, r=100, t=70, b=45),
            xaxis=dict(
                tickprefix="₹",
                tickformat=",.0f",
                showgrid=True,
                gridcolor="rgba(23,78,85,.12)",
                zeroline=False,
            ),
            yaxis=dict(
                title=None,
                automargin=True,
                categoryorder="total ascending",
            ),
            coloraxis_showscale=False,
            showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(
                family="Arial, sans-serif",
                size=13,
                color="#174E55",
            ),
        )
    
        st.plotly_chart(fig, use_container_width=True)
    
    
    
        st.caption(
            "Projects with the same intervention name are combined in the chart. "
            "The chart compares costs only; it does not rank effectiveness."
        )
    else:
        st.info(
            "Enter valid intervention costs in the project register "
            "to display the expenditure report."
        )
    
    
    
    section_intro(
        "Finance",
        "Financial overview",
        "Monitor arithmetic budget use while keeping unknown costs and evidence gaps visible.",
    )
    st.caption(
        "Financial monitoring summary based on the budget and "
        "project costs entered in this planning worksheet."
    )
    
    # Calculate financial indicators
    utilization = (total_known / budget * 100) if budget > 0 else 0.0
    budget_gap = max(total_known - budget, 0)
    
    # Four financial KPI cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Available Budget",
            value=format_inr(budget),
            help="Total budget entered for mitigation planning."
        )
    
    with col2:
        st.metric(
            label="Estimated Project Cost",
            value=format_inr(total_known),
            help="Sum of valid costs entered in the project register."
        )
    
    with col3:
        st.metric(
            label="Budget Balance",
            value=format_inr(remaining),
            delta=(
                f"{format_inr(budget_gap)} over budget"
                if budget_gap > 0
                else "Within entered budget"
            ),
            delta_color="inverse",
            help="Available budget minus entered project costs."
        )
    
    with col4:
        st.metric(
            label="Budget Utilization",
            value=f"{utilization:.1f}%",
            help="Entered project costs as a percentage of the available budget."
        )
    
    # Utilization indicator
    section_intro("Budget signal", "Budget utilisation monitor")
    
    if budget > 0:
        progress_value = min(max(total_known / budget, 0.0), 1.0)
        st.progress(progress_value)
    
        if total_known > budget:
            st.warning(
                f"Estimated costs exceed the available budget by "
                f"{format_inr(budget_gap)}."
            )
        else:
            st.caption(
                f"{utilization:.1f}% of the available budget is represented "
                "by entered project costs."
            )
    else:
        st.info(
            "Enter an available budget above zero to activate "
            "the budget utilization monitor."
        )
    
    # Financial data quality and budget status
    section_intro("Quality gate", "Financial review")
    
    if summary["within_budget"] is False:
        st.warning(
            "Budget review required: entered project estimates exceed "
            "the available budget. Review project scope, phasing, and "
            "funding assumptions before making decisions."
        )
    elif unknown_count:
        st.info(
            f"Cost verification pending: {unknown_count} project row(s) "
            "have no valid cost. The budget balance may be incomplete."
        )
    else:
        st.success(
            "Arithmetic check passed: all listed project rows have costs "
            "entered and the estimates fit within the available budget. "
            "This does not establish project feasibility or effectiveness."
        )
    
    
    section_intro("Register", "Project summary")
    
    total_projects = len(plan)
    
    missing_costs = (
        pd.to_numeric(plan["Cost INR"], errors="coerce")
        .isna()
        | (pd.to_numeric(plan["Cost INR"], errors="coerce") < 0)
    ).sum()
    
    summary_cols = st.columns(2)
    
    with summary_cols[0]:
        st.metric("Total Projects", total_projects)
    
    with summary_cols[1]:
        st.metric("Missing Cost Estimates", int(missing_costs))
    
    section_intro("Register", "Project status overview")
    
    status_counts = (
        plan["Project Status"]
        .fillna("Proposed")
        .value_counts()
        .reindex(
            ["Proposed", "Planned", "In Progress", "Completed", "On Hold"],
            fill_value=0,
        )
    )
    
    status_cols = st.columns(5)
    
    for col, (status, count) in zip(status_cols, status_counts.items()):
        with col:
            st.metric(status, int(count))
    
        
    section_intro("Handoff", "Export mitigation plan", "Download the current user-entered register for a separate review or funding process.")
    
    csv_data = plan.to_csv(index=False).encode("utf-8-sig")
    
    st.download_button(
        label="Download Project Register (CSV)",
        data=csv_data,
        file_name="AI_RESILIENCE_Kochi_Mitigation_Plan.csv",
        mime="text/csv",
        use_container_width=True,
    )
    
    st.caption(
        "Exports the current project table, including entered costs, "
        "status, priority, and evidence fields."
    )
    
    evidence_missing = (
        plan["Evidence for risk reduction"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
    )
    
    section_intro("Evidence", "Evidence and data quality")
    st.caption(
        f"Risk-reduction evidence is missing for "
        f"{int(evidence_missing.sum())} intervention row(s). "
        "No benefit or effectiveness score is calculated. "
        "Beneficiary estimates are user-entered and may overlap."
    )
    
    st.info(
        "Before funding decisions, document comparable engineering scope, "
        "current quotations, implementation and maintenance costs, target "
        "population, and a defensible impact evaluation."
    )
    
    section_intro(
        "Options",
        "What can you do with your budget?",
        "Explore arithmetic-only fits from the entered register. Fit does not imply effectiveness or priority.",
    )
    st.caption(
        "Find projects from your register that may fit within "
        "your available budget."
    )
    
    costs = pd.to_numeric(plan["Cost INR"], errors="coerce")
    
    feasible_projects = plan.loc[
        costs.notna()
        & (costs >= 0)
        & (costs <= budget)
    ].copy()
    
    if budget <= 0:
        st.warning(
            "Enter an available budget greater than ₹0 "
            "to explore possible projects."
        )
    
    elif feasible_projects.empty:
        st.info(
            "No projects with valid entered costs fit within this budget. "
            "Add cost estimates or review project scope."
        )
    
    else:
        section_intro("Screen", "Projects that fit individually")
    
        feasible_projects["_cost"] = pd.to_numeric(
            feasible_projects["Cost INR"], errors="coerce"
        )
    
        feasible_projects = feasible_projects.sort_values("_cost")
    
        for _, project in feasible_projects.iterrows():
            project_cost = float(project["_cost"])
            remaining_funds = budget - project_cost
    
            with st.expander(
                f"{project['Intervention']} — {format_inr(project_cost)}"
            ):
                st.write(
                    f"**Location:** {project['Location'] or 'Not specified'}"
                )
                st.write(f"**Priority:** {project['Priority']}")
                st.write(f"**Status:** {project['Project Status']}")
                st.write(
                    f"**Funds remaining if selected:** "
                    f"{format_inr(remaining_funds)}"
                )
    
                st.write(
                    "Next action: verify the quotation, project scope, "
                    "maintenance costs, and supporting evidence before "
                    "making a funding decision."
                )
    
        st.caption(
            "Projects are compared individually, not as a combined package. "
            "A project fitting the budget does not automatically mean "
            "it is the most effective choice."
        )
    
    section_intro(
        "Decision intelligence",
        "Budget-constrained investment scenarios",
        "Explore affordable project combinations using the transparent investment-priority scores above. The optimiser compares entered costs and human-assessed scores; it does not predict flood reduction or approve funding.",
    )
    
    if budget <= 0:
        st.info("Enter an available budget above ₹0 to run an investment scenario.")
    else:
        scenario_rows = []
        for _, project in plan.iterrows():
            try:
                cost_value = float(project["Cost INR"])
            except (TypeError, ValueError):
                continue
            assessment = score_investment_priority(project.to_dict())
            if pd.notna(cost_value) and cost_value > 0 and assessment["score"] is not None:
                scenario_rows.append({
                    "name": f'{project["Intervention"]} · {project["Location"]}',
                    "cost_inr": cost_value,
                    "value_points": int(round(assessment["score"])),
                })
        
        if not scenario_rows:
            st.warning("Add a valid cost estimate and complete all four investment assessments to compare projects in a budget scenario.")
        elif len(scenario_rows) > 18:
            st.warning("The transparent exact optimiser currently supports up to 18 candidate projects per scenario.")
        else:
            result = optimize_portfolio(scenario_rows, float(budget))
            if result["selected"]:
                st.success(
                    f'Best assessed-priority scenario: {result["total_value_points"]} priority points · '
                    f'{format_inr(result["total_cost_inr"])} invested · '
                    f'{format_inr(result["remaining_budget_inr"])} remaining.'
                )
                scenario_df = pd.DataFrame([
                    {"Selected project": item["name"], "Cost (INR)": item["cost_inr"],
                     "Priority points": item["value_points"]}
                    for item in result["selected"]
                ])
                display_dataframe(scenario_df, hide_index=True, use_container_width=True)
            else:
                st.info("No candidate project fits within the current budget.")
            st.caption(
                "Method: exhaustive 0/1 portfolio search over the submitted project set. "
                "The objective uses weighted human-assessed priority scores, not independently measured impact. "
                "Results are scenario comparisons—not engineering advice, risk predictions, or an automatic funding decision."
            )

            st.markdown("#### Budget sensitivity comparison · 75% / 100% / 125%")
            st.caption(
                "Compare how the selected portfolio changes when the available funding "
                "is lower or higher. These are arithmetic scenarios using the same assessed "
                "project set—not forecasts of outcomes."
            )
            sensitivity_rows = []
            for scenario_label, multiplier in (
                ("Constrained · 75%", 0.75),
                ("Current · 100%", 1.00),
                ("Expanded · 125%", 1.25),
            ):
                scenario_budget = float(budget) * multiplier
                scenario_result = optimize_portfolio(scenario_rows, scenario_budget)
                sensitivity_rows.append({
                    "Budget scenario": scenario_label,
                    "Budget cap": format_inr(scenario_budget),
                    "Selected projects": len(scenario_result["selected"]),
                    "Selected portfolio": (
                        "; ".join(item["name"] for item in scenario_result["selected"])
                        if scenario_result["selected"] else "No projects fit"
                    ),
                    "Priority points": scenario_result["total_value_points"],
                    "Allocated": format_inr(scenario_result["total_cost_inr"]),
                    "Unallocated": format_inr(scenario_result["remaining_budget_inr"]),
                })
            sensitivity_df = pd.DataFrame(sensitivity_rows)
            display_dataframe(sensitivity_df, hide_index=True, use_container_width=True)
            st.caption(
                "The comparison assumes project costs and assessments remain unchanged "
                "across scenarios. It does not model inflation, phased delivery, "
                "dependencies, maintenance, or measured risk reduction."
            )

"""Smart Mitigation Design Studio — transparent concept planning for Kochi."""
from __future__ import annotations

import io

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dataframe_display import display_dataframe
from src.mitigation_intelligence import design_recommendations
from src.smart_mitigation_studio import (
    COMPONENT_CATALOG,
    COMPONENT_DETAILS,
    build_review_items,
    build_studio_state,
    calculate_design,
    compare_designs,
)
from src.ui_theme import page_header, section_intro
from src.mitigation_project_store import get_project, save_project


page_header(
    "AI RESILIENCE · KOCHI · ENGINEERING & PLANNING",
    "Smart Mitigation Design Studio",
    "Configure, cost and review conceptual flood-resilience interventions for the Kochi pilot. "
    "Compare options and export a traceable planning brief.",
    meta=("Kochi · Kerala · India", "Concept planning", "Engineering review required"),
    accent="emerald",
    key="smart-mitigation",
)

st.info(
    "**Concept planning only.** This workspace performs transparent cost arithmetic and "
    "rule-based completeness prompts. It does not run a hydraulic model, predict flood depth, "
    "measure risk reduction, or produce construction-ready engineering drawings."
)

# Load a project handed off from Mitigation Budget before widgets are created.
_open_project_id = st.session_state.pop("mitigation_open_project_id", None)
if _open_project_id:
    _opened = get_project(st.session_state, _open_project_id)
    if _opened:
        _payload = _opened.get("studio_payload", {})
        _design_state = _payload.get("design_state", {})
        st.session_state["studio_project_name"] = _payload.get("project_name", "Untitled mitigation concept")
        st.session_state["studio_site_area"] = _payload.get("site_area", "")
        st.session_state["studio_area_type"] = _payload.get("area_type", "Low-lying flood-prone area")
        st.session_state["studio_budget"] = int(_payload.get("budget_inr", 0))
        st.session_state["studio_rainfall"] = int(_payload.get("rainfall_input_mm_per_hour", 50))
        for _key in COMPONENT_DETAILS:
            st.session_state[f"studio_include_{_key}"] = bool(_payload.get("selected", {}).get(_key, False))
            st.session_state[f"studio_qty_{_key}"] = float(_payload.get("quantities", {}).get(_key, COMPONENT_DETAILS[_key]["default_quantity"]))
            st.session_state[f"studio_rate_{_key}"] = int(_payload.get("rates_inr", {}).get(_key, COMPONENT_CATALOG[_key]["indicative_cost_inr"]))
        st.session_state["mitigation_active_project_id"] = _opened["project_id"]
        st.session_state["mitigation_active_project_revision"] = int(_opened.get("revision", 1))
        st.session_state["mitigation_design_state"] = _design_state
        st.success(f"Opened **{_payload.get('project_name', 'mitigation project')}** · revision {_opened.get('revision', 1)}")

# ---------------------------------------------------------------------
# 01 · Project context
# ---------------------------------------------------------------------
section_intro(
    "01 · Project context",
    "Define the planning case",
    "Use a specific ward, road, neighbourhood or public facility where possible. The site description is user supplied.",
)
context_left, context_right = st.columns(2)
with context_left:
    project_name = st.text_input(
        "Project / concept name",
        value="Kochi Urban Flood Resilience Pilot",
        key="studio_project_name",
    )
    site_area = st.text_input(
        "Planning area / ward / road",
        placeholder="e.g. ward, road stretch or neighbourhood",
        key="studio_site_area",
    )
    area_type = st.selectbox(
        "Area context",
        [
            "Low-lying flood-prone area",
            "Urban road",
            "Residential neighbourhood",
            "Commercial area",
        ],
        key="studio_area_type",
    )
with context_right:
    budget_inr = st.number_input(
        "Available planning budget (₹)",
        min_value=0,
        value=500000,
        step=50000,
        format="%d",
        key="studio_budget",
    )
    rainfall_input = st.slider(
        "Illustrative rainfall input (mm/hour)",
        min_value=0,
        max_value=150,
        value=50,
        step=5,
        key="studio_rainfall",
        help="A scenario input only. It is not a live observation, official warning or hydraulic model input.",
    )
    st.caption(
        "Rainfall scenario: "
        + ("Low" if rainfall_input < 30 else "Moderate" if rainfall_input < 70 else "High" if rainfall_input < 110 else "Very high")
        + " · illustrative band only"
    )

# ---------------------------------------------------------------------
# 02 · Intervention builder
# ---------------------------------------------------------------------
section_intro(
    "02 · Intervention builder",
    "Build a component-level concept",
    "Select measures and edit the planning quantity and unit allowance. Defaults are placeholders, not supplier quotations.",
)

component_rows = []
selected = {}
quantities = {}
rates = {}

for key, details in COMPONENT_DETAILS.items():
    catalog = COMPONENT_CATALOG[key]
    with st.container(border=True):
        header_col, toggle_col = st.columns([4, 1])
        header_col.markdown(f"**{details['label']}**")
        header_col.caption(
            f"{catalog['group']} · Planning unit: {details['unit']}"
        )
        selected[key] = toggle_col.checkbox(
            "Include",
            value=(key in {"drains", "inlets", "maintenance"}),
            key=f"studio_include_{key}",
        )
        if selected[key]:
            quantity_col, rate_col = st.columns(2)
            quantities[key] = quantity_col.number_input(
                f"Quantity ({details['unit']})",
                min_value=0.1,
                value=float(details["default_quantity"]),
                step=1.0,
                key=f"studio_qty_{key}",
            )
            rates[key] = rate_col.number_input(
                "Planning allowance per unit (₹)",
                min_value=0,
                value=int(catalog["indicative_cost_inr"]),
                step=5000,
                format="%d",
                key=f"studio_rate_{key}",
                help="Editable placeholder. Replace with a dated quotation or a documented estimate before investment decisions.",
            )
        else:
            quantities[key] = float(details["default_quantity"])
            rates[key] = float(catalog["indicative_cost_inr"])

try:
    design = calculate_design(
        budget_inr=budget_inr,
        selected=selected,
        quantities=quantities,
        rates_inr=rates,
    )
except ValueError as exc:
    st.error(str(exc))
    st.stop()

# ---------------------------------------------------------------------
# 03 · Cost and affordability
# ---------------------------------------------------------------------
section_intro(
    "03 · Cost and affordability",
    "Live project cost plan",
    "Costs are calculated from the quantities and unit allowances entered above.",
)

metric_cols = st.columns(4)
metric_cols[0].metric("Selected measures", f"{design['component_count']}/6")
metric_cols[1].metric("Planning estimate", f"₹{design['total_inr']:,.0f}")
metric_cols[2].metric("Available budget", f"₹{budget_inr:,.0f}")
metric_cols[3].metric("Budget balance", f"₹{design['balance_inr']:,.0f}")

if budget_inr > 0:
    st.progress(min(max(design["utilisation_pct"] / 100, 0.0), 1.0))
    st.caption(f"Estimated budget utilisation: {design['utilisation_pct']:.1f}%")
if design["status"] == "Over budget":
    st.warning(f"Over budget by ₹{abs(design['balance_inr']):,.0f}. Review scope, rates or phasing.")
else:
    st.success(f"Within the entered budget by ₹{design['balance_inr']:,.0f}.")

if design["line_items"]:
    cost_frame = pd.DataFrame(design["line_items"])
    display_costs = cost_frame[["component", "unit", "quantity", "rate_inr", "estimated_cost_inr", "basis"]].rename(
        columns={
            "component": "Intervention",
            "unit": "Unit",
            "quantity": "Quantity",
            "rate_inr": "Allowance / unit (₹)",
            "estimated_cost_inr": "Estimated line cost (₹)",
            "basis": "Cost basis",
        }
    )
    display_dataframe(display_costs, hide_index=True, use_container_width=True)
else:
    st.warning("Select at least one intervention to build a cost plan.")

# ---------------------------------------------------------------------
# 04 · Alternative package comparison
# ---------------------------------------------------------------------
section_intro(
    "04 · Scenario comparison",
    "Compare your design with a core package",
    "The comparison covers cost and component count only. It does not rank flood protection or engineering effectiveness.",
)

core_keys = {"drains", "inlets", "maintenance"}
core_selected = {key: key in core_keys for key in COMPONENT_DETAILS}
core_quantities = {key: quantities.get(key, 1.0) for key in COMPONENT_DETAILS}
core_rates = {key: rates.get(key, COMPONENT_CATALOG[key]["indicative_cost_inr"]) for key in COMPONENT_DETAILS}
core_design = calculate_design(
    budget_inr=budget_inr,
    selected=core_selected,
    quantities=core_quantities,
    rates_inr=core_rates,
)
comparison = compare_designs(design, core_design)

compare_cols = st.columns(2)
with compare_cols[0]:
    st.markdown("**Your current design**")
    st.metric("Measures", design["component_count"])
    st.metric("Estimated cost", f"₹{design['total_inr']:,.0f}")
    st.metric("Budget balance", f"₹{design['balance_inr']:,.0f}")
with compare_cols[1]:
    st.markdown("**Core package · drainage + inlets + maintenance**")
    st.metric("Measures", core_design["component_count"])
    st.metric("Estimated cost", f"₹{core_design['total_inr']:,.0f}")
    st.metric("Budget balance", f"₹{core_design['balance_inr']:,.0f}")

st.caption(
    f"Cost difference (core package minus current design): ₹{comparison['cost_difference_inr']:,.0f}. "
    f"{comparison['interpretation']}. This is a cost comparison, not a performance assessment."
)

# ---------------------------------------------------------------------
# 05 · Conceptual 3D site schematic
# ---------------------------------------------------------------------
section_intro(
    "05 · Conceptual site schematic",
    "Explore the proposed arrangement",
    "Schematic geometry only — not a surveyed Kochi map, terrain model, drainage network or hydraulic simulation.",
)

fig = go.Figure()
fig.add_trace(go.Surface(
    x=[[0, 100], [0, 100]],
    y=[[0, 0], [70, 70]],
    z=[[0, 0], [0, 0]],
    colorscale=[[0, "#dcefe2"], [1, "#dcefe2"]],
    showscale=False,
    opacity=1,
    name="Concept site",
    hoverinfo="skip",
))
fig.add_trace(go.Surface(
    x=[[5, 95], [5, 95]],
    y=[[30, 30], [43, 43]],
    z=[[0.2, 0.2], [0.2, 0.2]],
    colorscale=[[0, "#64748b"], [1, "#64748b"]],
    showscale=False,
    name="Road corridor",
    hovertemplate="Illustrative road corridor<extra></extra>",
))
# Generic blocks are intentionally not positioned from real building footprints.
for x, y, label in [(12, 8, "Block A"), (34, 8, "Block B"), (72, 8, "Block C"), (12, 52, "Block D"), (72, 52, "Block E")]:
    fig.add_trace(go.Mesh3d(
        x=[x, x + 12, x + 12, x, x, x + 12, x + 12, x],
        y=[y, y, y + 9, y + 9, y, y, y + 9, y + 9],
        z=[0.2, 0.2, 0.2, 0.2, 5, 5, 5, 5],
        i=[0, 0, 0, 1, 1, 2, 4, 4, 5, 6],
        j=[1, 2, 3, 2, 5, 3, 5, 6, 6, 7],
        k=[2, 3, 7, 5, 6, 7, 6, 7, 7, 4],
        color="#9fb7c4",
        opacity=0.92,
        name=label,
        showlegend=False,
        hovertemplate=f"{label} · illustrative block<extra></extra>",
    ))

if selected.get("drains"):
    fig.add_trace(go.Scatter3d(
        x=[8, 92], y=[25, 25], z=[0.45, 0.45],
        mode="lines", line=dict(color="#0284c7", width=8),
        name="Concept drainage corridor",
        hovertemplate="Concept corridor — alignment unverified<extra></extra>",
    ))
if selected.get("inlets"):
    fig.add_trace(go.Scatter3d(
        x=[18, 38, 58, 78], y=[29, 29, 29, 29], z=[0.5] * 4,
        mode="markers", marker=dict(color="#334155", size=6, symbol="square"),
        name="Indicative inlet markers",
    ))
if selected.get("garden"):
    fig.add_trace(go.Scatter3d(
        x=[54, 64], y=[53, 60], z=[0.35, 0.35],
        mode="markers", marker=dict(color="#16a34a", size=12, symbol="square"),
        name="Green infrastructure concept",
    ))
if selected.get("storage"):
    fig.add_trace(go.Mesh3d(
        x=[70, 86, 86, 70], y=[48, 48, 62, 62], z=[0.2, 0.2, 0.2, 0.2],
        i=[0, 0], j=[1, 2], k=[2, 3],
        color="#38bdf8", opacity=0.8, name="Indicative storage footprint",
    ))
if selected.get("sensors"):
    fig.add_trace(go.Scatter3d(
        x=[20, 50, 82], y=[24, 24, 24], z=[1.2, 1.2, 1.2],
        mode="markers", marker=dict(color="#ef4444", size=7),
        name="Indicative sensor markers",
    ))

fig.update_layout(
    height=590,
    margin=dict(l=0, r=0, t=35, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    scene=dict(
        bgcolor="#f5faf7",
        xaxis=dict(title="Schematic X", range=[0, 100], backgroundcolor="#edf5ef"),
        yaxis=dict(title="Schematic Y", range=[0, 70], backgroundcolor="#edf5ef"),
        zaxis=dict(title="Illustrative height", range=[0, 10], backgroundcolor="#edf5ef"),
        aspectmode="manual",
        aspectratio=dict(x=1.6, y=1.1, z=0.45),
        camera=dict(eye=dict(x=1.6, y=-1.7, z=1.1)),
    ),
    legend=dict(orientation="h", y=-0.08),
)
st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})

# ---------------------------------------------------------------------
# 06 · Engineering review checklist and transparent adviser
# ---------------------------------------------------------------------
section_intro(
    "06 · Engineering review",
    "Site checks before any investment decision",
    "Tick an item only when the relevant evidence has actually been reviewed. These are reminders, not automatic approvals.",
)

review_items = build_review_items(selected)
completed = 0
for index, item in enumerate(review_items):
    done = st.checkbox(
        f"{item['component']}: {item['check']}",
        key=f"studio_review_{index}_{item['component']}",
    )
    completed += int(done)

st.progress(completed / len(review_items) if review_items else 0.0)
st.caption(f"Review checklist marked complete: {completed}/{len(review_items)}. User-confirmed checklist only; no independent verification.")

shared_state = build_studio_state(
    project_name=project_name,
    area_type=area_type,
    rainfall_mm_per_hour=rainfall_input,
    budget_inr=budget_inr,
    selected=selected,
    design=design,
    site_area=site_area,
)
st.session_state["mitigation_design_state"] = shared_state

# Two-way project hand-off: save the exact editable configuration and its arithmetic.
st.markdown("#### Connected Mitigation Budget")
_active_id = st.session_state.get("mitigation_active_project_id")
_active_revision = st.session_state.get("mitigation_active_project_revision")
_save_label = "Update saved budget project" if _active_id else "Save design to Mitigation Budget"
if st.button(_save_label, type="primary", use_container_width=True, key="save_studio_to_mitigation_budget"):
    _payload = {
        "project_name": project_name,
        "site_area": site_area,
        "area_type": area_type,
        "budget_inr": float(budget_inr),
        "rainfall_input_mm_per_hour": float(rainfall_input),
        "selected": dict(selected),
        "quantities": dict(quantities),
        "rates_inr": dict(rates),
        "design_state": dict(shared_state),
        "line_items": list(design["line_items"]),
        "total_inr": float(design["total_inr"]),
        "balance_inr": float(design["balance_inr"]),
        "budget_status": design["status"],
        "engineering_review_items": list(review_items),
        "engineering_review_completed_count": int(completed),
    }
    try:
        _saved = save_project(
            st.session_state,
            _payload,
            project_id=_active_id,
            expected_revision=_active_revision if _active_id else None,
        )
        st.session_state["mitigation_active_project_id"] = _saved["project_id"]
        st.session_state["mitigation_active_project_revision"] = _saved["revision"]
        st.success(
            f"Saved to Mitigation Budget · project ID {_saved['project_id'][:8]} · "
            f"revision {_saved['revision']}"
        )
    except ValueError as exc:
        st.error(str(exc))
st.caption(
    "Projects are shared across these two pages within the current Streamlit session. "
    "They are not yet stored in a permanent database."
)

st.markdown("#### Explainable planning prompts")
st.caption("Rule-based prompts show why they appear and what evidence should be checked. They are not machine-learning predictions.")
for item in design_recommendations(shared_state):
    with st.container(border=True):
        st.markdown(f"**{item['Priority']} · {item['Planning recommendation']}**")
        st.write(item["Why this was suggested"])
        st.caption(f"Verification: {item['Suggested verification']}")

# ---------------------------------------------------------------------
# 07 · Export
# ---------------------------------------------------------------------
section_intro(
    "07 · Export project brief",
    "Download a reviewable planning record",
    "The export keeps the user-entered cost basis and engineering limitations visible.",
)

report = [
    "AI RESILIENCE — SMART MITIGATION DESIGN STUDIO",
    "Location context: Kochi, Kerala, India",
    f"Project: {project_name}",
    f"Planning area: {site_area or 'Not specified'}",
    f"Area context: {area_type}",
    f"Illustrative rainfall input: {rainfall_input} mm/hour (not a live measurement)",
    f"Available budget: INR {budget_inr:,.0f}",
    f"Estimated component cost: INR {design['total_inr']:,.0f}",
    f"Budget balance: INR {design['balance_inr']:,.0f}",
    f"Budget status: {design['status']}",
    "",
    "COMPONENT LINE ITEMS",
]
for row in design["line_items"]:
    report.append(
        f"- {row['component']}: {row['quantity']:g} {row['unit']} × "
        f"INR {row['rate_inr']:,.0f} = INR {row['estimated_cost_inr']:,.0f}"
    )
report.extend([
    "",
    "ENGINEERING LIMITATIONS",
    "- Conceptual planning only; not construction-ready.",
    "- No hydraulic simulation, flood-depth prediction or risk-reduction estimate is produced.",
    "- Cost allowances are user-editable planning placeholders, not verified quotations.",
    "- The 3D schematic is not a surveyed map or terrain/building model.",
    "- Confirm site ownership, utilities, soil, groundwater, outfalls, permits and lifecycle costs.",
    "- Qualified civil/drainage engineers must validate all design dimensions and calculations.",
])
report_text = "\n".join(report)

download_cols = st.columns(2)
with download_cols[0]:
    st.download_button(
        "Download project brief (.txt)",
        data=report_text,
        file_name="AI_RESILIENCE_Kochi_Smart_Mitigation_Brief.txt",
        mime="text/plain",
        use_container_width=True,
    )
with download_cols[1]:
    csv_buffer = io.StringIO()
    pd.DataFrame(design["line_items"]).to_csv(csv_buffer, index=False)
    st.download_button(
        "Download cost schedule (.csv)",
        data=csv_buffer.getvalue(),
        file_name="AI_RESILIENCE_Kochi_Mitigation_Cost_Schedule.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.caption(
    "Prepared for preliminary planning and discussion. A completed checklist, an affordable budget "
    "or a visual component selection does not establish technical feasibility, safety or approval."
)

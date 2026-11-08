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


# Page-scoped styling: restore the earlier light glass / mint presentation.
st.markdown(
    """
    <style>
    .concept-note {
      background: radial-gradient(ellipse at 100% 0%, rgba(240, 197, 106, .12), transparent 18rem),
                  linear-gradient(145deg, #FFFFFF, #DCE7E8);
      border: 1px solid rgba(235, 190, 91, .34);
      border-left: 4px solid #e9bd5a;
      border-radius: 15px;
      padding: 1rem 1.15rem;
      color: #465C5D;
      line-height: 1.62;
      margin: .4rem 0 1.1rem;
      box-shadow: var(--ar-shadow-soft);
    }
    .concept-note strong { color: #174E55; letter-spacing: .04em; }
    .concept-note p { color: #52666A; margin: .3rem 0 0; }
    .smart-panel {
      margin: 1.4rem 0 .9rem;
      padding: 1.05rem 1.25rem;
      background: linear-gradient(120deg, #FFFFFF, #DCE7E8);
      border: 1px solid rgba(23,78,85,.18);
      border-radius: 18px;
      box-shadow: var(--ar-shadow-soft);
    }
    .smart-panel h3 { margin: 0; color: #174E55; }
    .smart-panel p { margin: .35rem 0 0; color: #52666A; font-size: .86rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

page_header(
    "AI RESILIENCE · KOCHI · ENGINEERING & PLANNING",
    "Smart Mitigation Design Studio",
    "Configure, cost and review conceptual flood-resilience interventions for the Kochi pilot. "
    "Compare options and export a traceable planning brief.",
    meta=("Kochi · Kerala · India", "Concept planning", "Engineering review required"),
    accent="emerald",
    key="smart-mitigation",
)

st.markdown(
    """
    <div class="concept-note">
      <strong>CONCEPT ONLY</strong>
      <p>
        This visualisation is not a construction-ready engineering design. A qualified
        civil or drainage engineer must verify site conditions, hydraulic calculations,
        dimensions, costs and local requirements.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
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
# 05 · Restored earlier interactive 3D concept model
# ---------------------------------------------------------------------
# Compatibility aliases for the original 3D layout.
use_drains = bool(selected.get("drains"))
use_inlets = bool(selected.get("inlets"))
use_storage = bool(selected.get("storage"))
use_garden = bool(selected.get("garden"))
use_sensors = bool(selected.get("sensors"))
use_maintenance = bool(selected.get("maintenance"))

section_intro(
    "05 · Interactive 3D visualisation",
    "Kochi urban flood-resilience concept model",
    "Restore of the earlier detailed 3D layout. Geometry and rainfall-responsive water surfaces remain illustrative, not surveyed or hydraulically simulated.",
)
st.caption("Drag to rotate, scroll to zoom, and hover over the conceptual components.")

# ==================================================
# INTERACTIVE 3D ENGINEERING VISUALIZATION - V2
# ==================================================

st.markdown("---")
section_intro("Visualisation", "Interactive 3D flood-resilience site")
st.caption(
    "Conceptual site visualization for engineering review. "
    "Drag to rotate, scroll to zoom, and hover over components."
)
# Illustrative visual parameter only — not a predicted flood depth.
# Rainfall-responsive visual parameters.
# These are display effects, NOT hydraulic predictions.

rainfall_fraction = max(
    0.0,
    min(float(rainfall_input) / 150.0, 1.0)
)

illustrative_water_level = (
    0.42 + rainfall_fraction * 0.40
)

illustrative_pond_level = (
    0.42 + rainfall_fraction * 0.30
)
fig3d = go.Figure()

# 1. Site ground
fig3d.add_trace(go.Surface(
    x=[[0, 100], [0, 100]],
    y=[[0, 0], [70, 70]],
    z=[[0, 0], [0, 0]],
    surfacecolor=[[0, 0], [0, 0]],
    colorscale=[[0, "#b7d7a8"], [1, "#b7d7a8"]],
    showscale=False,
    hoverinfo="skip",
    name="Site ground"
))

# 2. Main road
fig3d.add_trace(go.Surface(
    x=[[5, 95], [5, 95]],
    y=[[30, 30], [43, 43]],
    z=[[0.25, 0.25], [0.25, 0.25]],
    colorscale=[[0, "#475569"], [1, "#475569"]],
    showscale=False,
    hovertemplate="Road corridor<extra></extra>",
    name="Road"
))

# Road centre line
fig3d.add_trace(go.Scatter3d(
    x=list(range(5, 96, 3)),
    y=[36.5 if i % 2 == 0 else None for i in range(len(range(5, 96, 3)))],
    z=[0.4] * len(range(5, 96, 3)),
    mode="lines",
    line=dict(color="white", width=4, dash="dash"),
    name="Road centre marking",
    hoverinfo="skip"
))

# 3. Solid building volumes
def add_plotly_building(x0, y0, length, width, height, label):
    vertices = [
        (x0, y0, 0.2),
        (x0 + length, y0, 0.2),
        (x0 + length, y0 + width, 0.2),
        (x0, y0 + width, 0.2),
        (x0, y0, height),
        (x0 + length, y0, height),
        (x0 + length, y0 + width, height),
        (x0, y0 + width, height)
    ]

    faces = [
        (0, 1, 5), (0, 5, 4),
        (1, 2, 6), (1, 6, 5),
        (2, 3, 7), (2, 7, 6),
        (3, 0, 4), (3, 4, 7),
        (4, 5, 6), (4, 6, 7)
    ]

    fig3d.add_trace(go.Mesh3d(
        x=[v[0] for v in vertices],
        y=[v[1] for v in vertices],
        z=[v[2] for v in vertices],
        i=[f[0] for f in faces],
        j=[f[1] for f in faces],
        k=[f[2] for f in faces],
        color="#9fb4c4",
        opacity=1,
        flatshading=True,
        name=label,
        hovertemplate=f"{label}<br>Concept height: {height}<extra></extra>"
    ))


# Area-specific conceptual 3D building layouts

building_layouts = {
    "Low-lying flood-prone area": [
        (12, 5, 12, 10, 3, "Low-rise Block A"),
        (31, 5, 14, 10, 3, "Low-rise Block B"),
        (55, 5, 13, 10, 4, "Low-rise Block C"),
        (76, 5, 12, 10, 3, "Low-rise Block D"),
        (12, 51, 13, 10, 3, "Low-rise Block E"),
        (34, 53, 14, 9, 4, "Low-rise Block F"),
        (76, 53, 13, 10, 3, "Low-rise Block G")
    ],

    "Urban road": [
        (12, 5, 12, 10, 5, "Roadside Building A"),
        (31, 5, 14, 10, 7, "Roadside Building B"),
        (55, 5, 13, 10, 6, "Roadside Building C"),
        (76, 5, 12, 10, 8, "Roadside Building D"),
        (12, 51, 13, 10, 5, "Roadside Building E"),
        (34, 53, 14, 9, 7, "Roadside Building F"),
        (76, 53, 13, 10, 6, "Roadside Building G")
    ],

    "Residential neighbourhood": [
        (12, 5, 12, 10, 4, "Residential Block A"),
        (31, 5, 14, 10, 6, "Residential Block B"),
        (55, 5, 13, 10, 5, "Residential Block C"),
        (76, 5, 12, 10, 7, "Residential Block D"),
        (12, 51, 13, 10, 5, "Residential Block E"),
        (34, 53, 14, 9, 7, "Residential Block F"),
        (76, 53, 13, 10, 6, "Residential Block G")
    ],

    "Commercial area": [
        (12, 5, 12, 10, 8, "Commercial Building A"),
        (31, 5, 14, 10, 9, "Commercial Building B"),
        (55, 5, 13, 10, 8, "Commercial Building C"),
        (76, 5, 12, 10, 9, "Commercial Building D"),
        (12, 51, 13, 10, 7, "Commercial Building E"),
        (34, 53, 14, 9, 9, "Commercial Building F"),
        (76, 53, 13, 10, 8, "Commercial Building G")
    ]
}

building_layout_3d = building_layouts.get(
    area_type,
    building_layouts["Residential neighbourhood"]
)


for building in building_layout_3d:
    add_plotly_building(*building)

    # ==========================================
# AREA-RESPONSIVE COMPONENT POSITIONING
# ==========================================

component_layouts = {
    "Low-lying flood-prone area": {
        "garden": (50, 61, 48, 56),
        "pond": (63, 74, 48, 64)
    },

    "Urban road": {
        "garden": (50, 61, 49, 57),
        "pond": (63, 74, 49, 65)
    },

    "Residential neighbourhood": {
        "garden": (50, 61, 50, 58),
        "pond": (63, 74, 48, 64)
    },

    "Commercial area": {
        "garden": (50, 61, 48, 56),
        "pond": (63, 74, 50, 66)
    }
}

active_layout = component_layouts[area_type]

garden_x0, garden_x1, garden_y0, garden_y1 = (
    active_layout["garden"]
)

pond_x0, pond_x1, pond_y0, pond_y1 = (
    active_layout["pond"]
)


# Drainage corridor — 3D channel with banks and flowing water
if use_drains:
    # Concrete channel bed
    fig3d.add_trace(go.Mesh3d(
        x=[8, 92, 92, 8],
        y=[24, 24, 30, 30],
        z=[0.35, 0.35, 0.35, 0.35],
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color="#94a3b8",
        opacity=1,
        name="Concrete channel bed",
        hovertemplate="Conceptual channel bed<extra></extra>"
    ))

    # Water surface
    fig3d.add_trace(go.Mesh3d(
        x=[8, 92, 92, 8],
        y=[25, 25, 29, 29],
        z=[illustrative_pond_level] * 4,
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color="#0284c7",
        opacity=0.88,
        name="Stormwater",
        hovertemplate="Conceptual stormwater surface<extra></extra>"
    ))

        # Subtle water-surface highlights
    for highlight_y in [26.0, 28.0]:
        fig3d.add_trace(go.Scatter3d(
            x=[12, 88],
            y=[highlight_y, highlight_y],
            z=[
                illustrative_water_level + 0.015,
                illustrative_water_level + 0.015
            ],
            mode="lines",
            line=dict(color="#bae6fd", width=2),
            showlegend=False,
            hoverinfo="skip"
        ))

    # Water-surface edge indicator
    fig3d.add_trace(go.Scatter3d(
        x=[8, 92],
        y=[25, 25],
        z=[
            illustrative_water_level + 0.01,
            illustrative_water_level + 0.01
        ],
        mode="lines",
        line=dict(color="#7dd3fc", width=2),
        showlegend=False,
        hoverinfo="skip"
    ))
    # Proper 3D concrete drainage channel walls
    for bank_y in [24, 30]:

        fig3d.add_trace(go.Mesh3d(
            x=[8, 92, 92, 8],
            y=[bank_y, bank_y, bank_y, bank_y],
            z=[0.35, 0.35, 0.90, 0.90],
            i=[0, 0],
            j=[1, 2],
            k=[2, 3],
            color="#94a3b8",
            opacity=1,
            flatshading=True,
            name="Concrete channel wall",
            showlegend=(bank_y == 24),
            hovertemplate=(
                "Concrete drainage channel wall"
                "<br>Conceptual height: 0.55 units"
                "<extra></extra>"
            )
        ))

        # Upper wall edge
        fig3d.add_trace(go.Scatter3d(
            x=[8, 92],
            y=[bank_y, bank_y],
            z=[0.90, 0.90],
            mode="lines",
            line=dict(
                color="#cbd5e1",
                width=5
            ),
            showlegend=False,
            hoverinfo="skip"
        ))


    
    # Compact drainage flow-direction indicators
    flow_z = illustrative_water_level + 0.10

    fig3d.add_trace(go.Scatter3d(
        x=[
            25, 27, None,
            48, 50, None,
            71, 73
        ],
        y=[
            27, 27, None,
            27, 27, None,
            27, 27
        ],
        z=[
            flow_z, flow_z, None,
            flow_z, flow_z, None,
            flow_z, flow_z
        ],
        mode="lines+markers",
        line=dict(
            color="#e0f7ff",
            width=5
        ),
        marker=dict(
            size=3,
            color="#e0f7ff",
            symbol="circle"
        ),
        name="Illustrative water-flow direction",
        hovertemplate=(
            "Conceptual flow direction"
            "<extra></extra>"
        )
    ))



# 5. Rain garden
if use_garden:
    fig3d.add_trace(go.Mesh3d(
        x=[garden_x0, garden_x1, garden_x1, garden_x0],
        y=[garden_y0, garden_y0, garden_y1, garden_y1],
        z=[0.35, 0.35, 0.35, 0.35],
        i=[0, 0], j=[1, 2], k=[2, 3],
        color="#239b68",
        opacity=0.9,
        name="Rain garden",
        hovertemplate="Green infrastructure<extra></extra>"
    ))
    
    # Rain garden — conceptual raised edging
    fig3d.add_trace(go.Scatter3d(
        x=[
            garden_x0, garden_x1, garden_x1,
            garden_x0, garden_x0
        ],
        y=[
            garden_y0, garden_y0, garden_y1,
            garden_y1, garden_y0
        ],
        z=[[0.80] * 5, 0.65, 0.65, 0.65, 0.65],
        mode="lines",
        line=dict(color="#475569", width=6),
        name="Rain-garden edging",
        hovertemplate="Conceptual garden edging<extra></extra>"
    ))
        # Rain garden — 3D vegetation clusters
    fig3d.add_trace(go.Scatter3d(
                x=[
            garden_x0 + 1, garden_x0 + 2,
            garden_x0 + 3, garden_x0 + 5,
            garden_x0 + 7, garden_x0 + 9,
            garden_x0 + 2, garden_x0 + 4,
            garden_x0 + 6, garden_x0 + 8
        ],
        y=[
            garden_y0 + 1, garden_y0 + 4,
            garden_y0 + 2, garden_y0 + 6,
            garden_y0 + 1, garden_y0 + 4,
            garden_y0 + 7, garden_y0 + 6,
            garden_y0 + 1, garden_y0 + 3
        ],
        z=[
            0.65, 0.72, 0.68, 0.75, 0.66, 0.72,
            0.68, 0.74, 0.70, 0.67
        ],
        mode="markers",
        marker=dict(
            size=11,
            color=[
                "#166534", "#15803d", "#22c55e",
                "#166534", "#15803d", "#22c55e",
                "#166534", "#15803d", "#22c55e",
                "#166534"
            ],
            symbol="circle",
            line=dict(
                color="#bbf7d0",
                width=1
            )
        ),
        name="Rain-garden vegetation",
        hovertemplate="Conceptual vegetation<extra></extra>"
    ))
    # Shallow infiltration zone
    fig3d.add_trace(go.Mesh3d(
                x=[
            garden_x0 + 2,
            garden_x1 - 2,
            garden_x1 - 2,
            garden_x0 + 2
        ],
        y=[
            garden_y0 + 2,
            garden_y0 + 2,
            garden_y1 - 2,
            garden_y1 - 2
        ],
        z=[0.42, 0.42, 0.42, 0.42],
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color="#0f766e",
        opacity=0.65,
        name="Infiltration zone concept",
        hovertemplate="Illustrative shallow infiltration zone<extra></extra>"
    ))




    # Conceptual vegetation clusters
    vegetation_positions = [
        (garden_x0 + 2, garden_y0 + 3),
        (garden_x0 + 4, garden_y0 + 6),
        (garden_x0 + 6, garden_y0 + 3),
        (garden_x0 + 8, garden_y0 + 6),
        (garden_x0 + 9, garden_y0 + 2),
        (garden_x0 + 5, garden_y0 + 8)
    ]

    for plant_index, (px, py) in enumerate(vegetation_positions):
        fig3d.add_trace(go.Scatter3d(
            x=[px, px],
            y=[py, py],
            z=[0.45, 1.15],
            mode="lines",
            line=dict(
                color="#166534",
                width=5
            ),
            showlegend=(plant_index == 0),
            name="Conceptual vegetation"
        ))

        fig3d.add_trace(go.Scatter3d(
            x=[px],
            y=[py],
            z=[1.15],
            mode="markers",
            marker=dict(
                size=8,
                color="#4ade80",
                symbol="circle",
                line=dict(color="#14532d", width=1)
            ),
            showlegend=False,
            hovertemplate="Illustrative vegetation cluster<extra></extra>"
        ))

# 6. Stormwater storage pond
if use_storage:
    pond_x = [pond_x0, pond_x1, pond_x1, pond_x0]
    pond_y = [pond_y0, pond_y0, pond_y1, pond_y1]

    fig3d.add_trace(go.Mesh3d(
        x=pond_x,
        y=pond_y,
        z=[illustrative_water_level] * 4,
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color="#38bdf8",
        opacity=0.9,
        name="Concept detention pond",
        hovertemplate="Stormwater storage concept<extra></extra>"
    ))
    
    # Conceptual pond perimeter
    fig3d.add_trace(go.Scatter3d(
        x=[pond_x0, pond_x1, pond_x1, pond_x0, pond_x0],
        y=[pond_y0, pond_y0, pond_y1, pond_y1, pond_y0], 
        z=[0.65, 0.65, 0.65, 0.65, 0.65],
        mode="lines",
        line=dict(
            color="#a16207",
            width=9
        ),
        name="Pond perimeter",
        hovertemplate="Conceptual pond boundary<extra></extra>"
    ))

    # Landscape buffer around pond
    fig3d.add_trace(go.Scatter3d(
        x=[
    pond_x0 + 2,
    pond_x1 - 2,
    pond_x1 - 2,
    pond_x0 + 2,
    pond_x0 + 2
],
        y=[
    pond_y0 - 2,
    pond_y0 - 2,
    pond_y1 + 2,
    pond_y1 + 2,
    pond_y0 - 2
],
        z=[0.40, 0.40, 0.40, 0.40, 0.40],
        mode="lines",
        line=dict(
            color="#4ade80",
            width=5,
            dash="dot"
        ),
        name="Pond landscape buffer",
        hovertemplate="Illustrative landscape buffer<extra></extra>"
    ))


# 7. Roadside inlets — conceptual 3D grates
if use_inlets:
    inlet_positions = list(range(15, 90, 15))

    for inlet_x in inlet_positions:
        # Dark rectangular grate frame
        fig3d.add_trace(go.Mesh3d(
            x=[
                inlet_x - 2, inlet_x + 2,
                inlet_x + 2, inlet_x - 2
            ],
            y=[28.5, 28.5, 29.5, 29.5],
            z=[0.72, 0.72, 0.72, 0.72],
            i=[0, 0],
            j=[1, 2],
            k=[2, 3],
            color="#1f2937",
            opacity=1,
            name="Inlet frame",
            showlegend=(inlet_x == inlet_positions[0]),
            hovertemplate="Conceptual inlet frame<extra></extra>"
        ))

        # Parallel grate bars
        for bar_y in [28.65, 28.85, 29.05, 29.25, 29.45]:
            fig3d.add_trace(go.Scatter3d(
                x=[inlet_x - 1.7, inlet_x + 1.7],
                y=[bar_y, bar_y],
                z=[0.76, 0.76],
                mode="lines",
                line=dict(color="#cbd5e1", width=3),
                showlegend=False,
                hovertemplate="Conceptual grate bar<extra></extra>"
            ))
    
# 8. Conceptual connections from road inlets to drainage
if use_inlets and use_drains:
    for inlet_x in range(15, 90, 15):
        fig3d.add_trace(go.Scatter3d(
            x=[inlet_x, inlet_x],
            y=[29, 27],
            z=[0.68, 0.58],
            mode="lines",
            line=dict(color="#38bdf8", width=5),
            showlegend=(inlet_x == 15),
            name="Inlet-to-drain connection",
            hovertemplate=(
                "Illustrative stormwater connection"
                "<extra></extra>"
            )
        ))



# 8. Water-level monitoring stations
if use_sensors:
    for sensor_index, (sx, sy) in enumerate(
        [(12, 25), (50, 25), (88, 25)]
    ):
        # Vertical monitoring pole
        fig3d.add_trace(go.Scatter3d(
            x=[sx, sx],
            y=[sy, sy],
            z=[0.3, 4.0],
            mode="lines",
            line=dict(color="#64748b", width=8),
            name="Sensor pole",
            showlegend=(sensor_index == 0),
            hovertemplate="Conceptual sensor pole<extra></extra>"
        ))

        # Sensor housing
        fig3d.add_trace(go.Scatter3d(
            x=[sx],
            y=[sy],
            z=[4.0],
            mode="markers",
            marker=dict(
                size=9,
                color="#ef4444",
                symbol="square",
                line=dict(color="#ffffff", width=1)
            ),
            name="Water-level sensor",
            showlegend=(sensor_index == 0),
            hovertemplate="Conceptual water-level sensor<extra></extra>"
        ))

        # Small warning indicator
        fig3d.add_trace(go.Scatter3d(
            x=[sx],
            y=[sy],
            z=[4.4],
            mode="markers",
            marker=dict(size=5, color="#fbbf24"),
            showlegend=False,
            hovertemplate="Illustrative warning indicator<extra></extra>"
        ))


# 9. Conceptual flood-warning indicator
if use_sensors:
    fig3d.add_trace(go.Scatter3d(
        x=[50],
        y=[26],
        z=[1.2],
        mode="markers+text",
        marker=dict(
            size=8,
            color="#f59e0b",
            symbol="diamond",
            line=dict(color="#ffffff", width=2)
        ),
        text=["FLOOD ALERT"],
        textposition="top center",
        textfont=dict(
            color="#b45309",
            size=12
        ),
        name="Conceptual flood warning",
        hovertemplate=(
            "Illustrative flood-warning marker"
            "<extra></extra>"
        )
    ))

# 9. Project labels
fig3d.add_trace(go.Scatter3d(
    x=[20, pond_x0 + 3, garden_x0 + 2],
    y=[27, pond_y0 + 3, garden_y0 + 1],
    z=[3, 3, 4],
    mode="text",
    text=[
        "01 DRAINAGE",
        "02 STORAGE",
        "03 GREEN BUFFER"
    ],
    textfont=dict(size=10, color="#083344"),
    name="Engineering labels",
    hoverinfo="skip"
))



# ==========================================
# PROFESSIONAL 3D PRESENTATION LAYOUT
# ==========================================

fig3d.update_layout(
    title=dict(
        text=(
            "KOCHI | URBAN FLOOD RESILIENCE"
            "<br><sup>INTERACTIVE 3D SITE MODEL · CONCEPT DESIGN</sup>"
        ),
        x=0.5,
        xanchor="center",
        y=0.97,
        font=dict(
            family="Arial",
            size=22,
            color="#1D3030"
        )
    ),
    height=760,
    margin=dict(l=15, r=15, t=100, b=75),

    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",

    scene=dict(
    bgcolor="#F4F8F5",

        xaxis=dict(
            title="",
            range=[0, 100],
            showbackground=True,
            backgroundcolor="#EAF3EE",
            gridcolor="rgba(44,105,82,.18)",
            zerolinecolor="rgba(44,105,82,.30)",
            showspikes=False,
            color="#587267",
            tickfont=dict(size=10),
            nticks=6
        ),

        yaxis=dict(
            title="",
            range=[0, 70],
            showbackground=True,
            backgroundcolor="#EAF3EE",
            gridcolor="rgba(44,105,82,.18)",
            zerolinecolor="rgba(44,105,82,.30)",
            showspikes=False,
            color="#587267",
            tickfont=dict(size=10),
            nticks=5
        ),

        zaxis=dict(
            title="",
            range=[0, 10],
            showbackground=True,
            backgroundcolor="#EAF3EE",
            gridcolor="rgba(44,105,82,.18)",
            zerolinecolor="rgba(44,105,82,.30)",
            showspikes=False,
            color="#587267",
            tickfont=dict(size=10),
            nticks=5
        ),

        # Reduce vertical exaggeration
        aspectmode="manual",
        aspectratio=dict(
            x=1.8,
            y=1.25,
            z=0.55
        ),

        # More balanced engineering perspective
        camera=dict(
            eye=dict(
                x=1.65,
                y=-1.85,
                z=1.25
            ),
            center=dict(
                x=0,
                y=0,
                z=0
            ),
            up=dict(
                x=0,
                y=0,
                z=1
            ),
            projection=dict(type="orthographic")
        ),

        dragmode="turntable"
    ),

    legend=dict(
        title=dict(
            text="DESIGN COMPONENTS",
            font=dict(
                color="#1D3030",
                size=11
            )
        ),
        orientation="h",
        yanchor="bottom",
        y=-0.16,
        xanchor="center",
        x=0.5,
        font=dict(
            color="#1D3030",
            size=10
        ),
        bgcolor="rgba(255,255,255,0.96)",
        bordercolor="rgba(44,105,82,0.22)",
        borderwidth=1,
        itemsizing="constant"
    ),

    font=dict(
        family="Arial",
        color="#1D3030"
    ),

    hoverlabel=dict(
        bgcolor="#ffffff",
        bordercolor="rgba(44,105,82,.25)",
        font=dict(
            color="#1D3030",
            size=12
        )
    ),

    uirevision="kochi-engineering-model"
)

# ==========================================
# RENDER PRESENTATION MODEL
# ==========================================

st.plotly_chart(
    fig3d,
    use_container_width=True,
    config={
        "displaylogo": False,
        "scrollZoom": True,
        "responsive": True,
        "displayModeBar": True,
        "modeBarButtonsToRemove": [
            "lasso3d",
            "select3d"
        ]
    },
    key="kochi_flood_resilience_3d"
)



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
            {"studio_payload": _payload},
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

import streamlit as st
from src.dataframe_display import display_dataframe
import plotly.graph_objects as go
st.set_page_config(
    page_title="Smart Mitigation Design Studio",
    page_icon="🏗️",
    layout="wide"
)


# Shared dark SDG climate-intelligence workspace styling.
st.markdown("""
<style>
.stApp{background:transparent!important;color:#e7f5f5!important}
.block-container{padding-top:1.5rem;padding-bottom:3rem;max-width:1500px}
h1,h2,h3,h4{color:#effafa!important;letter-spacing:-.02em}
h2{border-bottom:1px solid rgba(130,190,199,.24);padding-bottom:.5rem}
h3{color:#65e4ce!important}
p,li,label,.stMarkdown,.stCaption{color:#c5dadd}
.design-header{position:relative;overflow:hidden;padding:clamp(1.5rem,3vw,2.4rem);border-radius:23px;margin-bottom:1.25rem;background:radial-gradient(ellipse at 88% 12%,rgba(76,226,197,.2),transparent 22rem),linear-gradient(118deg,#071a2a 0%,#0b4054 58%,#087e78 100%);border:1px solid rgba(112,226,207,.28);box-shadow:0 22px 54px rgba(0,0,0,.28);color:#e7f5f5}
.design-header h1{color:#f1ffff!important;font-size:clamp(2rem,3.5vw,2.8rem)}
.design-header p{color:#c3e0e2!important;line-height:1.7}
.concept-note{background:rgba(64,54,28,.55)!important;border:1px solid rgba(235,190,91,.4);border-left:5px solid #e9bd5a;border-radius:12px;padding:17px;color:#f6e6b8!important;line-height:1.6}
div[data-baseweb="select"]>div,div[data-baseweb="input"]>div,div[data-baseweb="textarea"]>div,div[data-testid="stDateInput"] input,div[data-testid="stNumberInput"] input,div[data-testid="stTextInput"] input,div[data-testid="stTextArea"] textarea{background:#102b3c!important;color:#eaf7f7!important;border:1px solid rgba(130,190,199,.34)!important;border-radius:10px!important}
div[data-testid="stSlider"],div[data-testid="stMetric"],div[data-testid="stExpander"],div[data-testid="stVerticalBlockBorderWrapper"]>div{background:linear-gradient(145deg,rgba(17,48,66,.96),rgba(10,34,49,.96))!important;border:1px solid rgba(130,190,199,.24)!important;border-radius:14px;color:#e7f5f5!important}
div[data-testid="stMetric"]{padding:1rem;min-height:108px}
div[data-testid="stMetricLabel"],.stCaption{color:#a7c1c8!important}
div[data-testid="stMetricValue"]{color:#f0ffff!important}
div[data-testid="stProgress"]{background:#16384a;border-radius:20px}
div[data-testid="stProgress"]>div>div{background:linear-gradient(90deg,#42e0c1,#56c8e8);border-radius:20px}
div[data-testid="stExpander"] summary,div[data-testid="stExpander"] summary p{color:#e5f4f4!important}
.stDownloadButton button,div.stButton>button{background:linear-gradient(105deg,#126a70,#147c83)!important;color:#f4ffff!important;border:1px solid rgba(91,223,200,.42)!important;border-radius:11px;font-weight:750;min-height:2.7rem}
.stDownloadButton button:hover,div.stButton>button:hover{background:linear-gradient(105deg,#16817e,#168b91)!important;border-color:#7bf0d7!important}
hr{border-color:rgba(130,190,199,.22)!important}
[data-testid="stDataFrame"],[data-testid="stTable"]{border:1px solid rgba(130,190,199,.22);border-radius:12px}
</style>
""",unsafe_allow_html=True)

# Page header

st.markdown(
    "<div class='design-header'>",
    unsafe_allow_html=True
)

st.markdown(
    "<div style='font-size:12px; letter-spacing:2px; font-weight:700; color:#398477;'>AI RESILIENCE · ENGINEERING & PLANNING</div>"
    "<h1>🏗️ Smart Mitigation Design Studio</h1>"
    "<p>Kochi, Kerala, India<br>Urban Flood Resilience · Concept Design and Budget Planning</p>"
    "<div style='margin-top:18px; display:inline-block; padding:7px 13px; background:#102b3c; border:1px solid #c5e4dc; border-radius:20px; color:#398477; font-size:12px; font-weight:650;'>CONCEPT STAGE · ENGINEERING REVIEW REQUIRED</div>",
    unsafe_allow_html=True
)

st.markdown(
    "</div>",
    unsafe_allow_html=True
)

st.markdown("""
<div class="concept-note">
<strong>⚠️ CONCEPT ONLY</strong><br>
This visualization is not a construction-ready engineering design.
A qualified civil/drainage engineer must verify site conditions,
hydraulic calculations, dimensions, costs, and local requirements.
</div>
""", unsafe_allow_html=True)



st.markdown("""
<div style="
    margin-top: 12px;
    margin-bottom: 18px;
    padding: 15px 20px;
    background: linear-gradient(120deg, rgba(13,43,60,.98), rgba(10,61,67,.96));
    border: 1px solid rgba(130,190,199,.28);
    border-radius: 13px;
">
    <h3 style="margin: 0; color: #e7f5f5;">
        ⚙️ Project Configuration
    </h3>
    <p style="margin: 5px 0 0 0; color: #a8c2ca; font-size: 13px;">
        Define the planning area, rainfall conditions and mitigation components.
    </p>
</div>
""", unsafe_allow_html=True)

left, right = st.columns(2)

with left:
    project_name = st.text_input(
        "Project name",
        value="Kochi Urban Flood Management Concept"
    )

    area_type = st.selectbox(
        "Area type",
        [
            "Low-lying flood-prone area",
            "Urban road",
            "Residential neighbourhood",
            "Commercial area"
        ]
    )

with right:
    available_budget = st.number_input(
        "Available project budget (₹)",
        min_value=0,
        value=500000,
        step=50000,
        format="%d"
    )

# ==============================
# MITIGATION COMPONENT SELECTION
# ==============================

st.markdown("### 🏗️ Select Mitigation Components")

component_names = {
    "drains": "Underground drainage",
    "inlets": "Roadside stormwater inlets",
    "storage": "Stormwater storage pond",
    "garden": "Rain garden",
    "sensors": "Water-level sensors",
    "maintenance": "Maintenance access"
}

# Illustrative planning estimates — not verified quotations
costs = {
    "drains": 150000,
    "inlets": 50000,
    "storage": 120000,
    "garden": 60000,
    "sensors": 40000,
    "maintenance": 30000
}

selected = {}

component_col1, component_col2 = st.columns(2)

with component_col1:
    selected["drains"] = st.checkbox(
        "Underground drainage", value=True
    )
    selected["inlets"] = st.checkbox(
        "Roadside stormwater inlets", value=True
    )
    selected["storage"] = st.checkbox(
        "Stormwater storage pond", value=True
    )

with component_col2:
    selected["garden"] = st.checkbox(
        "Rain garden", value=True
    )
    selected["sensors"] = st.checkbox(
        "Water-level sensors", value=True
    )
    selected["maintenance"] = st.checkbox(
        "Maintenance access", value=True
    )

use_drains = selected["drains"]
use_inlets = selected["inlets"]
use_storage = selected["storage"]
use_garden = selected["garden"]
use_sensors = selected["sensors"]
use_maintenance = selected["maintenance"]

design_total = sum(
    costs[key] for key in costs if selected[key]
)

remaining_budget = available_budget - design_total


# ==============================
# RAINFALL SCENARIO INPUT
# ==============================

st.markdown("### 🌧️ Rainfall Scenario")

rainfall_scenario = st.slider(
    "Select illustrative rainfall intensity (mm/hour)",
    min_value=0,
    max_value=150,
    value=50,
    step=5,
    key="rainfall_scenario_slider"
)

if rainfall_scenario < 30:
    rainfall_label = "Low"
elif rainfall_scenario < 70:
    rainfall_label = "Moderate"
elif rainfall_scenario < 110:
    rainfall_label = "High"
else:
    rainfall_label = "Very high"

# ==============================
# BUDGET UTILISATION DASHBOARD
# ==============================

st.markdown("""
<div style="
    margin-top: 28px;
    margin-bottom: 18px;
    padding: 16px 20px;
    background: linear-gradient(120deg, rgba(13,43,60,.98), rgba(10,61,67,.96));
    border: 1px solid rgba(130,190,199,.28);
    border-radius: 14px;
">
    <h3 style="margin: 0; color: #e7f5f5;">
        📊 Budget Utilisation Dashboard
    </h3>
    <p style="margin: 5px 0 0 0; color: #a8c2ca; font-size: 13px;">
        Monitor estimated project costs against the available planning budget.
    </p>
</div>
""", unsafe_allow_html=True)

budget_col1, budget_col2, budget_col3 = st.columns(3)

with budget_col1:
    st.metric(
        "Available Budget",
        f"₹{available_budget:,.0f}"
    )

with budget_col2:
    st.metric(
        "Selected Components",
        f"₹{design_total:,.0f}"
    )

with budget_col3:
    st.metric(
        "Budget Remaining",
        f"₹{remaining_budget:,.0f}"
    )

if available_budget > 0:
    budget_used_ratio = design_total / available_budget
    st.progress(min(max(budget_used_ratio, 0.0), 1.0))
    st.caption(
        f"Estimated budget utilisation: "
        f"{budget_used_ratio * 100:.1f}%"
    )
else:
    st.info("Enter an available budget greater than ₹0 to view utilisation.")

if design_total > available_budget:
    st.warning(
        f"⚠️ Over budget by ₹{design_total - available_budget:,.0f}. "
        "Review component estimates or the available budget."
    )
else:
    st.info(
        f"✓ ₹{remaining_budget:,.0f} remains within the available budget."
    )


# ==============================
# PROJECT STATUS DASHBOARD
# ==============================

selected_count = sum(selected.values())

if design_total > available_budget:
    budget_status = "Over budget"
else:
    budget_status = "Within budget"

st.markdown("## 📊 Project Status Dashboard")

status1, status2, status3, status4 = st.columns(4)

status1.metric("Project Components", f"{selected_count}/6")
status2.metric("Estimated Cost", f"₹{design_total:,.0f}")
status3.metric("Available Budget", f"₹{available_budget:,.0f}")
status4.metric("Budget Status", budget_status)

st.caption(
    "Project overview · Kochi, Kerala, India · "
    "Conceptual flood mitigation planning"
)






# ==============================
# ENGINEERING PROJECT BRIEF
# ==============================

st.markdown("""
<div style="
    margin-top: 28px;
    margin-bottom: 18px;
    padding: 16px 20px;
    background: linear-gradient(120deg, rgba(13,43,60,.98), rgba(10,61,67,.96));
    border: 1px solid rgba(130,190,199,.28);
    border-radius: 14px;
">
    <h3 style="margin: 0; color: #e7f5f5;">
        📐 Engineering Concept Brief
    </h3>
    <p style="margin: 5px 0 0 0; color: #a8c2ca; font-size: 13px;">
        Project scope, selected systems and engineering review status.
    </p>
</div>
""", unsafe_allow_html=True)

brief1, brief2, brief3 = st.columns(3, gap="large")

with brief1:
    st.markdown("**PROJECT**")
    st.write("Kochi Urban Flood Resilience")
    st.caption("Integrated stormwater management")

with brief2:
    st.markdown("**DESIGN SCOPE**")
    active_systems = sum([
        use_drains,
        use_inlets,
        use_storage,
        use_garden,
        use_sensors,
        use_maintenance
    ])
    st.metric("Selected systems", active_systems, help="Count of enabled design components")

with brief3:
    st.markdown("**REVIEW STATUS**")
    st.warning("Concept stage — engineering review pending")

st.caption(
    "Design maturity: preliminary visualization. "
    "No verified hydraulic capacity, flood-depth reduction, "
    "structural adequacy or construction dimensions are implied."
)

# ==============================
# DESIGN FEATURES PANEL
# ==============================

st.markdown("### 🏙️ Proposed Flood-Resilience Features")

feature_col1, feature_col2, feature_col3 = st.columns(3)

with feature_col1:
    st.markdown("#### 💧 Water Management")
    if use_drains:
        st.write("✓ Underground drainage concept")
    if use_inlets:
        st.write("✓ Roadside stormwater collection")
    if use_storage:
        st.write("✓ Detention pond concept")

with feature_col2:
    st.markdown("#### 🌿 Green Infrastructure")
    if use_garden:
        st.write("✓ Rain garden / permeable surfaces")
    st.write("✓ Conceptual landscape planting")
    st.write("✓ Urban green-space integration")

with feature_col3:
    st.markdown("#### 📡 Monitoring & Access")
    if use_sensors:
        st.write("✓ Water-level monitoring concept")
    if use_maintenance:
        st.write("✓ Maintenance access concept")
    st.write("✓ Future inspection planning")

st.caption(
    "These features are conceptual proposals for study. "
    "Feasibility, performance, and placement require site surveys "
    "and review by qualified engineering professionals."
)

# ==============================
# 3D DESIGN LEGEND
# ==============================

st.markdown("### 🗺️ Design Legend")

legend_items = []

if use_drains:
    legend_items.append(("🔵", "Underground drainage channel"))

if use_inlets:
    legend_items.append(("⬛", "Roadside stormwater inlets"))

if use_garden:
    legend_items.append(("🟢", "Rain garden / permeable surface"))

if use_storage:
    legend_items.append(("💧", "Detention / storage pond"))

if use_sensors:
    legend_items.append(("🔴", "Water-level monitoring sensors"))

if use_maintenance:
    legend_items.append(("🟤", "Maintenance access path"))

legend_columns = st.columns(3)

for index, (symbol, label) in enumerate(legend_items):
    with legend_columns[index % 3]:
        st.markdown(f"**{symbol} {label}**")


st.info(
    "The 3D model is illustrative, not to scale. "
    "Actual drainage routes, slopes, storage capacity, "
    "soil conditions and dimensions require professional "
    "engineering assessment."
)


# ==============================
# DESIGN COMPONENT SUMMARY
# ==============================

st.markdown("---")
st.markdown("## 📋 Design Component Summary")

summary_items = []

for key, name in component_names.items():
    if selected[key]:
        summary_items.append({
            "Component": name,
            "Estimated Cost (₹)": costs[key],
            "Status": "Included"
        })

if summary_items:
    import pandas as pd

    summary_df = pd.DataFrame(summary_items)

    display_dataframe(
        summary_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Estimated Cost (₹)": st.column_config.NumberColumn(
                "Estimated Cost (₹)",
                format="₹%.0f"
            )
        }
    )
else:
    st.warning(
        "No components selected. Select at least one component "
        "to build your conceptual design."
    )

st.caption(
    "All costs are illustrative estimates entered by the user, "
    "not verified quotations or engineering cost estimates."
)

# ==================================================
# INTERACTIVE 3D ENGINEERING VISUALIZATION - V2
# ==================================================

st.markdown("---")
st.markdown("## 🏗️ Interactive 3D Flood-Resilience Site")
st.caption(
    "Conceptual site visualization for engineering review. "
    "Drag to rotate, scroll to zoom, and hover over components."
)
# Illustrative visual parameter only — not a predicted flood depth.
# Rainfall-responsive visual parameters.
# These are display effects, NOT hydraulic predictions.

rainfall_fraction = max(
    0.0,
    min(float(rainfall_scenario) / 150.0, 1.0)
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
            color="#285675"
        )
    ),
    height=760,
    margin=dict(l=15, r=15, t=100, b=75),

    paper_bgcolor="#f2f8fc",
    plot_bgcolor="#f2f8fc",

    scene=dict(
    bgcolor="#eaf4fa",

        xaxis=dict(
            title="",
            range=[0, 100],
            showbackground=True,
            backgroundcolor="#f5faff",
            gridcolor="#d5e4ed",
            zerolinecolor="#9bb8c8",
            showspikes=False,
            color="#52768b",
            tickfont=dict(size=10),
            nticks=6
        ),

        yaxis=dict(
            title="",
            range=[0, 70],
            showbackground=True,
            backgroundcolor="#f5faff",
            gridcolor="#d5e4ed",
            zerolinecolor="#9bb8c8",
            showspikes=False,
            color="#52768b",
            tickfont=dict(size=10),
            nticks=5
        ),

        zaxis=dict(
            title="",
            range=[0, 10],
            showbackground=True,
            backgroundcolor="#f5faff",
            gridcolor="#d5e4ed",
            zerolinecolor="#9bb8c8",
            showspikes=False,
            color="#52768b",
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
                color="#285675",
                size=11
            )
        ),
        orientation="h",
        yanchor="bottom",
        y=-0.16,
        xanchor="center",
        x=0.5,
        font=dict(
            color="#285675",
            size=10
        ),
        bgcolor="rgba(12,35,51,0.98)",
        bordercolor="rgba(130,190,199,0.35)",
        borderwidth=1,
        itemsizing="constant"
    ),

    font=dict(
        family="Arial",
        color="#285675"
    ),

    hoverlabel=dict(
        bgcolor="#102b3c",
        bordercolor="#9bcbdc",
        font=dict(
            color="#ffffff",
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

# ==========================================
# LIVE 3D DESIGN INTELLIGENCE PANEL
# ==========================================

st.markdown("""
<div style="
    margin-top: 30px;
    margin-bottom: 18px;
    padding: 17px 21px;
    background: linear-gradient(120deg, rgba(13,43,60,.98), rgba(10,61,67,.96));
    border: 1px solid rgba(130,190,199,.28);
    border-radius: 14px;
">
    <h3 style="margin: 0; color: #e7f5f5;">
        🧠 Live Design Intelligence
    </h3>
    <p style="margin: 5px 0 0 0; color: #a8c2ca; font-size: 13px;">
        Real-time overview of your selected design configuration.
    </p>
</div>
""", unsafe_allow_html=True)

live_col1, live_col2, live_col3, live_col4 = st.columns(4)

selected_component_count = sum([
    use_drains,
    use_inlets,
    use_garden,
    use_storage,
    use_sensors,
    use_maintenance
])

with live_col1:
    st.metric(
        "Active Components",
        f"{selected_component_count}/6"
    )

with live_col2:
    st.metric(
        "Rainfall Scenario",
        f"{rainfall_scenario} mm/h"
    )

with live_col3:
    st.metric(
        "Area Configuration",
        area_type
    )

with live_col4:
    st.metric(
        "Budget Status",
        "Over budget" if design_total > available_budget
        else "Within budget"
    )

st.caption(
    "Live values reflect user-selected design settings. "
    "They are not independently verified engineering measurements."
)



# ==========================================
# RAINFALL SCENARIO COMPARISON
# ==========================================

st.markdown("---")
st.markdown("### 🌧️ Rainfall Scenario Comparison")

st.caption(
    "Illustrative display comparison using three rainfall inputs. "
    "This is not a hydraulic flood simulation."
)

scenario_col1, scenario_col2, scenario_col3 = st.columns(3)

scenario_values = [
    ("Lower scenario", 30),
    ("Moderate scenario", 75),
    ("Higher scenario", 120)
]

for column, (scenario_name, scenario_rainfall) in zip(
    [scenario_col1, scenario_col2, scenario_col3],
    scenario_values
):
    with column:
        display_level = (
            0.42 + (scenario_rainfall / 150) * 0.40
        )

        pond_display_level = (
            0.42 + (scenario_rainfall / 150) * 0.30
        )

        st.markdown(f"**{scenario_name}**")
        st.metric(
            "Rainfall input",
            f"{scenario_rainfall} mm/hour"
        )
        st.metric(
            "Illustrative channel level",
            f"{display_level:.2f}"
        )
        st.metric(
            "Illustrative pond level",
            f"{pond_display_level:.2f}"
        )
# ==========================================
# MITIGATION CONFIGURATION COMPARISON
# ==========================================

st.markdown("---")
st.markdown("### 🏗️ Mitigation Configuration Comparison")

st.caption(
    "Compare your selected design with a fully integrated "
    "component package. Costs are estimates, not engineering quotations."
)

# Current configuration
current_components = [
    key for key in costs
    if selected.get(key, False)
]

# Fully integrated configuration
all_components = list(costs.keys())

full_package_cost = sum(costs.values())

current_component_count = len(current_components)
full_component_count = len(all_components)

compare_col1, compare_col2 = st.columns(2)

with compare_col1:
    st.markdown("#### Current Design")
    st.metric(
        "Active components",
        current_component_count
    )
    st.metric(
        "Estimated project cost",
        f"₹{design_total:,.0f}"
    )
    st.metric(
        "Remaining budget",
        f"₹{remaining_budget:,.0f}"
    )

    st.write("**Included components**")
    if current_components:
        for key in current_components:
            st.write(f"✅ {component_names.get(key, key.title())}")
    else:
        st.info("No components selected.")

with compare_col2:
    st.markdown("#### Fully Integrated Package")
    st.metric(
        "Active components",
        full_component_count
    )
    st.metric(
        "Estimated project cost",
        f"₹{full_package_cost:,.0f}"
    )

    full_package_balance = available_budget - full_package_cost

    st.metric(
        "Budget balance",
        f"₹{full_package_balance:,.0f}"
    )

    st.write("**Included components**")
    for key in all_components:
        st.write(f"📦 {component_names.get(key, key.title())}")

st.info(
    "This comparison evaluates component selection and estimated cost only. "
    "It does not predict flood-depth reduction or hydraulic performance."
)
# ==============================
# LIVE RAINFALL STATUS
# ==============================

st.markdown("### 🌧️ Live Design Scenario")

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    st.metric(
        "Selected Rainfall",
        f"{rainfall_scenario} mm/hour"
    )

with status_col2:
    st.metric(
        "Rainfall Category",
        rainfall_label
    )

with status_col3:
    st.metric(
        "Illustrative Display Level",
        f"{illustrative_water_level:.2f} units"
    )

st.caption(
    "Display level is a visualization parameter, not a measured "
    "water depth or a validated flood prediction."
)

# ==============================
# RAINFALL SCENARIO INPUT
# ==============================

st.markdown("### 🌧️ Rainfall Scenario")

rainfall_scenario = st.slider(
    "Select illustrative rainfall intensity (mm/hour)",
    min_value=0,
    max_value=150,
    value=50,
    step=5
)
# ==============================
# RAINFALL IMPACT INDICATOR
# ==============================

st.markdown("### 📊 Rainfall Scenario Indicator")

rainfall_progress = rainfall_scenario / 150

st.progress(rainfall_progress)

if rainfall_scenario < 30:
    st.success("Low illustrative rainfall scenario")
elif rainfall_scenario < 70:
    st.info("Moderate illustrative rainfall scenario")
elif rainfall_scenario < 110:
    st.warning("High illustrative rainfall scenario")
else:
    st.error("Very high illustrative rainfall scenario")

st.caption(
    "This indicator represents the selected scenario only. "
    "It does not calculate actual flood probability or safety."
)



# ==========================================
# ENGINEERING CONCEPT SUMMARY
# ==========================================

st.markdown("""
<div style="
    margin-top: 30px;
    margin-bottom: 18px;
    padding: 17px 21px;
    background: linear-gradient(120deg, rgba(13,43,60,.98), rgba(10,61,67,.96));
    border: 1px solid rgba(130,190,199,.28);
    border-radius: 14px;
">
    <h3 style="margin: 0; color: #e7f5f5;">
        🏗️ Flood-Management Design Overview
    </h3>
    <p style="margin: 5px 0 0 0; color: #a8c2ca; font-size: 13px;">
        Summary of the mitigation systems included in this concept design.
    </p>
</div>
""", unsafe_allow_html=True)

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

with summary_col1:
    st.metric(
        "Drainage",
        "Included" if use_drains else "Not selected"
    )
    st.caption("Stormwater channel")

with summary_col2:
    st.metric(
        "Storage",
        "Included" if use_storage else "Not selected"
    )
    st.caption("Retention pond")

with summary_col3:
    st.metric(
        "Green Infrastructure",
        "Included" if use_garden else "Not selected"
    )
    st.caption("Rain garden")

with summary_col4:
    st.metric(
        "Monitoring",
        "Included" if use_sensors else "Not selected"
    )
    st.caption("Water-level sensors")
st.info(
    "Engineering status: CONCEPT ONLY. "
    "No validated flood prediction, hydraulic capacity, "
    "structural safety, or construction dimensions are provided."
)

# ==========================================
# INTERACTIVE MODEL — ENGINEERING STATUS
# ==========================================

st.markdown("### 📋 Model Components & Review Status")

status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    st.markdown("**WATER MANAGEMENT**")
    st.write(
        f"{'✓' if use_drains else '—'} Drainage corridor"
    )
    st.write(
        f"{'✓' if use_inlets else '—'} Stormwater inlets"
    )
    st.write(
        f"{'✓' if use_storage else '—'} Storage pond"
    )

with status_col2:
    st.markdown("**GREEN INFRASTRUCTURE**")
    st.write(
        f"{'✓' if use_garden else '—'} Rain garden"
    )
    st.write("✓ Conceptual urban buildings")
    st.write("✓ Road corridor")

with status_col3:
    st.markdown("**MONITORING & VALIDATION**")
    st.write(
        f"{'✓' if use_sensors else '—'} Monitoring sensors"
    )
    st.write(
        f"{'✓' if use_maintenance else '—'} Maintenance access"
    )
    st.warning("Engineering validation pending")

st.caption(
    "A check mark indicates inclusion in the visualization only. "
    "It does not indicate verified performance, compliance, "
    "or engineering approval."
)

st.caption(
    "CONCEPT ONLY — Not for construction. "
    "Geometry, drainage capacity, hydraulic performance, "
    "storage volume and site suitability have not been validated."
)

# ==============================
# GENERATE DESIGN REPORT
# ==============================

st.markdown("""
<div style="
    margin-top: 32px;
    margin-bottom: 20px;
    padding: 20px 23px;
    background: linear-gradient(120deg, rgba(13,43,60,.98), rgba(10,61,67,.96));
    border: 1px solid rgba(130,190,199,.28);
    border-radius: 16px;
">
    <h2 style="margin: 0; color: #e7f5f5;">
        📄 Project Design Report
    </h2>
    <p style="margin: 6px 0 0 0; color: #a8c2ca; font-size: 13px;">
        Downloadable project configuration, component estimates and engineering limitations.
    </p>
</div>
""", unsafe_allow_html=True)

report_lines = [
    "AI RESILIENCE — SMART MITIGATION DESIGN STUDIO",
    "Kochi, Kerala, India",
    "",
    f"Project Name: {project_name}",
    f"Area Type: {area_type}",
    "Design: Conceptual 3D Urban Flood Management",
    "",
    "SELECTED COMPONENTS",
]

for key, name in component_names.items():
    if selected[key]:
        report_lines.append(
            f"- {name}: INR {costs[key]:,.0f}"
        )

report_lines.extend([
    "",
    f"Available Budget: INR {available_budget:,.0f}",
    f"Estimated Selected Cost: INR {design_total:,.0f}",
    f"Budget Remaining: INR {remaining_budget:,.0f}",
    "",
    "IMPORTANT DISCLAIMER",
    "This report contains conceptual information and user-entered",
    "cost estimates only. It is not a construction-ready design.",
    "A qualified civil/drainage engineer must validate site",
    "conditions, hydraulic calculations, dimensions, and costs.",
])
# ----------------------------------------------
# PROFESSIONAL PROJECT DESIGN REPORT
# ----------------------------------------------

report_lines.extend([
    "",
    "=" * 55,
    "PROJECT DESIGN AND BUDGET SUMMARY",
    "=" * 55,
    "",
    "PROJECT DETAILS",
    f"Project Name: {project_name}",
    "Location: Kochi, Kerala, India",
    f"Area Type: {area_type}",
    f"Illustrative Rainfall Scenario: {rainfall_scenario} mm/hour",
    "",
    "SELECTED MITIGATION COMPONENTS",
])

selected_count = 0

for key, is_selected in selected.items():
    if is_selected:
        selected_count += 1
        report_lines.append(
            f"- {component_names[key]}: ₹{costs[key]:,.0f}"
        )

if selected_count == 0:
    report_lines.append("No mitigation components selected.")

report_lines.extend([
    "",
    "BUDGET SUMMARY",
    f"Available Budget: ₹{available_budget:,.0f}",
    f"Estimated Project Cost: ₹{design_total:,.0f}",
    f"Remaining Budget: ₹{remaining_budget:,.0f}",
    f"Selected Components: {selected_count}",
])

if design_total > available_budget:
    report_lines.append(
        f"Budget Status: OVER BUDGET by ₹{design_total - available_budget:,.0f}"
    )
else:
    report_lines.append("Budget Status: WITHIN AVAILABLE BUDGET")

report_lines.extend([
    "",
    "ENGINEERING REVIEW AND LIMITATIONS",
    "- This report represents a conceptual mitigation design.",
    "- Cost figures are preliminary estimates, not verified quotations.",
    "- The 3D water level is an illustrative visual parameter.",
    "- No validated hydraulic or structural simulation is performed.",
    "- Site surveys, drainage calculations and engineering review are required.",
    "- This report must not be used as construction approval.",
    "",
    "Prepared by: AI RESILIENCE",
    "Location: Kochi, Kerala, India",
    "=" * 55,
])
report_text = "\n".join(report_lines)

st.download_button(
    label="📥 Generate & Download Design Report",
    data=report_text,
    file_name="AI_RESILIENCE_Design_Report.txt",
    mime="text/plain",
    use_container_width=True,
)



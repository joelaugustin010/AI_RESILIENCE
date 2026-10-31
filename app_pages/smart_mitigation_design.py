import streamlit as st
import plotly.graph_objects as go
import numpy as np
st.set_page_config(
    page_title="Smart Mitigation Design Studio",
    page_icon="🏗️",
    layout="wide"
)

# Page styling
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #eaf7ff 0%, #e9fff5 100%);
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}

.design-header {
    background: linear-gradient(110deg, #073763, #087eaa);
    padding: 28px;
    border-radius: 18px;
    color: white;
    margin-bottom: 18px;
    box-shadow: 0 8px 25px rgba(0, 60, 100, 0.15);
}

.design-header h1 {
    color: white;
    margin-bottom: 8px;
}

.design-header p {
    color: #e2f5ff;
    font-size: 16px;
    margin-bottom: 0;
}

.concept-note {
    background: #fff8df;
    border: 1px solid #f2d27b;
    border-radius: 12px;
    padding: 15px;
    color: #654b00;
}
</style>
""", unsafe_allow_html=True)

# Page header
st.markdown("""
<div class="design-header">
    <h1>🏗️ Smart Mitigation Design Studio</h1>
    <p>
        AI RESILIENCE · Kochi, Kerala, India<br>
        Conceptual urban drainage and flood management design
    </p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="concept-note">
<strong>⚠️ CONCEPT ONLY</strong><br>
This visualization is not a construction-ready engineering design.
A qualified civil/drainage engineer must verify site conditions,
hydraulic calculations, dimensions, costs, and local requirements.
</div>
""", unsafe_allow_html=True)



st.markdown("## 🏙️ Project Configuration")

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
# RAINFALL SCENARIO CONTROL
# ==============================

st.markdown("### 🌧️ Rainfall Scenario")

rainfall_scenario = st.slider(
    "Illustrative rainfall intensity (mm/hour)",
    min_value=0,
    max_value=150,
    value=50,
    step=10,
    help=(
        "This is a user-selected scenario for visualization only. "
        "It is not a live rainfall measurement or flood prediction."
    )
)

if rainfall_scenario < 30:
    rainfall_label = "Low scenario"
elif rainfall_scenario < 70:
    rainfall_label = "Moderate scenario"
elif rainfall_scenario < 110:
    rainfall_label = "High scenario"
else:
    rainfall_label = "Very high scenario"

st.info(
    f"Selected scenario: {rainfall_label} — "
    f"{rainfall_scenario} mm/hour"
)

st.markdown("### 🧩 Select Design Components")

c1, c2, c3 = st.columns(3)

with c1:
    use_drains = st.checkbox(
        "Underground drainage channels", value=True
    )
    use_inlets = st.checkbox(
        "Roadside stormwater inlets", value=True
    )

with c2:
    use_garden = st.checkbox(
        "Rain garden / permeable surfaces", value=True
    )
    use_storage = st.checkbox(
        "Detention / storage pond", value=True
    )

with c3:
    use_sensors = st.checkbox(
        "Water-level sensors", value=True
    )
    use_maintenance = st.checkbox(
        "Maintenance access", value=True
    )

st.markdown("### 💰 Component Cost Estimates")

st.caption(
    "Enter sourced estimates when available. These inputs do not "
    "represent verified construction prices."
)

costs = {}

with st.expander("Configure component costs", expanded=True):
    cost_col1, cost_col2 = st.columns(2)

    with cost_col1:
        costs["drains"] = st.number_input(
            "Underground drainage channels (₹)",
            min_value=0, value=200000, step=10000
        )
        costs["inlets"] = st.number_input(
            "Stormwater inlets (₹)",
            min_value=0, value=75000, step=5000
        )
        costs["garden"] = st.number_input(
            "Rain garden / permeable surfaces (₹)",
            min_value=0, value=100000, step=5000
        )

    with cost_col2:
        costs["storage"] = st.number_input(
            "Detention / storage pond (₹)",
            min_value=0, value=150000, step=10000
        )
        costs["sensors"] = st.number_input(
            "Water-level sensors (₹)",
            min_value=0, value=25000, step=1000
        )
        costs["maintenance"] = st.number_input(
            "Maintenance access (₹)",
            min_value=0, value=25000, step=1000
        )

selected = {
    "drains": use_drains,
    "inlets": use_inlets,
    "garden": use_garden,
    "storage": use_storage,
    "sensors": use_sensors,
    "maintenance": use_maintenance
}

component_names = {
    "drains": "Underground drainage channels",
    "inlets": "Roadside stormwater inlets",
    "garden": "Rain garden / permeable surfaces",
    "storage": "Detention / storage pond",
    "sensors": "Water-level sensors",
    "maintenance": "Maintenance access"
}

design_total = sum(
    costs[key] for key in costs if selected[key]
)

remaining_budget = available_budget - design_total


# ==============================
# BUDGET UTILISATION DASHBOARD
# ==============================

st.markdown("### 💰 Budget Utilisation Dashboard")

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
    st.error(
        f"Over budget by ₹{design_total - available_budget:,.0f}. "
        "Review component estimates or the available budget."
    )
else:
    st.success(
        f"₹{remaining_budget:,.0f} remains within the available budget."
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

st.markdown("---")

st.markdown("### 📊 Budget Overview")

m1, m2, m3 = st.columns(3)

m1.metric("Available Budget", f"₹{available_budget:,.0f}")
m2.metric("Estimated Total Cost", f"₹{design_total:,.0f}")
m3.metric("Budget Remaining", f"₹{remaining_budget:,.0f}")

if design_total > available_budget:
    st.error(
        f"Over budget by ₹{design_total - available_budget:,.0f}. "
        "Adjust the scope or budget estimates."
    )
else:
    st.success(
        f"Within budget — ₹{remaining_budget:,.0f} remaining."
    )




# ==============================
# ENGINEERING PROJECT BRIEF
# ==============================

st.markdown("---")
st.markdown("### 📐 Engineering Concept Brief")

brief1, brief2, brief3 = st.columns(3)

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

    st.dataframe(
        summary_df,
        use_container_width=True,
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
# Illustrative water-level response to selected rainfall
display_water_z = 0.55 + (rainfall_scenario / 150) * 1.8
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

building_layout_3d = [
    (12, 5, 12, 10, 4, "Residential Block A"),
    (31, 5, 14, 10, 6, "Residential Block B"),
    (55, 5, 13, 10, 5, "Residential Block C"),
    (76, 5, 12, 10, 7, "Residential Block D"),
    (12, 51, 13, 10, 5, "Residential Block E"),
    (34, 53, 14, 9, 7, "Residential Block F"),
    (76, 53, 13, 10, 6, "Residential Block G")
]

for building in building_layout_3d:
    add_plotly_building(*building)


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
        z=[display_water_z] * 4,
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color="#0284c7",
        opacity=0.88,
        name="Stormwater",
        hovertemplate="Conceptual stormwater surface<extra></extra>"
    ))

    # Raised channel banks
    for bank_y in [24, 30]:
        fig3d.add_trace(go.Scatter3d(
            x=[8, 92],
            y=[bank_y, bank_y],
            z=[0.9, 0.9],
            mode="lines",
            line=dict(color="#64748b", width=10),
            name="Channel bank",
            showlegend=(bank_y == 24),
            hovertemplate="Conceptual channel bank<extra></extra>"
        ))

    # Flow direction arrows
    # Small flow-direction arrows
    fig3d.add_trace(go.Cone(
        x=[25, 48, 71],
        y=[27, 27, 27],
        z=[0.8, 0.8, 0.8],
        u=[1, 1, 1],
        v=[0, 0, 0],
        w=[0, 0, 0],
        sizemode="absolute",
        sizeref=0.7,
        anchor="tail",
        colorscale=[[0, "#e0f2fe"], [1, "#0284c7"]],
        showscale=False,
        name="Illustrative flow direction",
        hovertemplate="Illustrative flow direction<extra></extra>"
    ))


# 5. Rain garden
if use_garden:
    fig3d.add_trace(go.Mesh3d(
        x=[15, 38, 38, 15],
        y=[48, 48, 62, 62],
        z=[0.35, 0.35, 0.35, 0.35],
        i=[0, 0], j=[1, 2], k=[2, 3],
        color="#239b68",
        opacity=0.9,
        name="Rain garden",
        hovertemplate="Green infrastructure<extra></extra>"
    ))
    
    # Rain garden — conceptual raised edging
    fig3d.add_trace(go.Scatter3d(
        x=[15, 38, 38, 15, 15],
        y=[48, 48, 62, 62, 48],
        z=[0.65, 0.65, 0.65, 0.65, 0.65],
        mode="lines",
        line=dict(color="#475569", width=6),
        name="Rain-garden edging",
        hovertemplate="Conceptual garden edging<extra></extra>"
    ))

    # Shallow infiltration zone
    fig3d.add_trace(go.Mesh3d(
        x=[19, 34, 34, 19],
        y=[51, 51, 59, 59],
        z=[0.42, 0.42, 0.42, 0.42],
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color="#0f766e",
        opacity=0.65,
        name="Infiltration zone concept",
        hovertemplate="Illustrative shallow infiltration zone<extra></extra>"
    ))




# 6. Stormwater storage pond
if use_storage:
    pond_x = [62, 88, 88, 62]
    pond_y = [48, 48, 62, 62]

    fig3d.add_trace(go.Mesh3d(
        x=pond_x,
        y=pond_y,
        z=[display_water_z] * 4,
        i=[0, 0],
        j=[1, 2],
        k=[2, 3],
        color="#38bdf8",
        opacity=0.9,
        name="Concept detention pond",
        hovertemplate="Stormwater storage concept<extra></extra>"
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
    x=[20, 72, 28],
    y=[27, 57, 58],
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

# 10. Professional scene layout
fig3d.update_layout(
    title=dict(
        text="KOCHI | URBAN FLOOD RESILIENCE — CONCEPT MODEL",
        x=0.5,
        xanchor="center"
    ),
    height=720,
    margin=dict(l=0, r=0, t=65, b=0),
    paper_bgcolor="#eef6f8",
    scene=dict(
        bgcolor="#eaf2f5",
        xaxis=dict(
            title="Site length (concept units)",
            range=[0, 100],
            showbackground=True,
            backgroundcolor="#e5edf0",
            gridcolor="#cbd5e1"
        ),
        yaxis=dict(
            title="Site width (concept units)",
            range=[0, 70],
            showbackground=True,
            backgroundcolor="#e5edf0",
            gridcolor="#cbd5e1"
        ),
        zaxis=dict(
            title="Concept elevation",
            range=[0, 10],
            showbackground=True,
            backgroundcolor="#e5edf0",
            gridcolor="#cbd5e1"
        ),
        
        aspectmode="manual",
        aspectratio=dict(x=1.6, y=1.15, z=0.85),
        camera=dict(
            eye=dict(x=1.8, y=-2.1, z=1.45),
            center=dict(x=0, y=0, z=-0.08),
            up=dict(x=0, y=0, z=1),
            projection=dict(type="perspective")
        )

    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.12,
        xanchor="center",
        x=0.5
    )
)

st.plotly_chart(fig3d, use_container_width=True)
# ==============================
# LIVE RAINFALL STATUS
# ==============================

st.markdown("### 🌧️ Selected Design Scenario")

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
        f"{display_water_z:.2f} units"
    )

st.caption(
    "Display level is a visualization parameter, not a measured "
    "water depth or a validated flood prediction."
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

# ==============================
# DESIGN SUMMARY
# ==============================

st.markdown("### 🏗️ Flood Management Design Summary")

summary_col1, summary_col2 = st.columns(2)

with summary_col1:
    st.markdown("#### ✅ Selected Components")

    if use_drains:
        st.write("• Stormwater drainage channel")

    if use_storage:
        st.write("• Stormwater storage pond")

    if use_garden:
        st.write("• Rain garden / infiltration zone")

    if not any([use_drains, use_storage, use_garden]):
        st.info("No mitigation components selected.")

with summary_col2:
    st.markdown("#### 🌧️ Scenario Details")
    st.write(f"**Project:** {project_name}")
    st.write(f"**Area type:** {area_type}")
    st.write(f"**Selected rainfall:** {rainfall_scenario} mm/hour")
    st.write(f"**Scenario category:** {rainfall_label}")
    st.write(f"**Available budget:** ₹{available_budget:,.0f}")

st.warning(
    "Conceptual design only. Component selection and budget do not "
    "establish flood protection performance. Professional site surveys, "
    "hydraulic calculations, and engineering review are required."
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

st.markdown("---")
st.markdown("## 📄 Project Design Report")

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

report_text = "\n".join(report_lines)

st.download_button(
    label="📥 Generate & Download Design Report",
    data=report_text,
    file_name="AI_RESILIENCE_Design_Report.txt",
    mime="text/plain",
    use_container_width=True,
)



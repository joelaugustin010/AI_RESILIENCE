"""Budget arithmetic for user-supplied intervention estimates."""

import pandas as pd
import streamlit as st
import plotly.express as px

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





st.markdown("""
<style>
.project-header {
    background: rgba(12,35,51,.92);
    padding: 28px 32px;
    border: 1px solid #d9e2ec;
    border-top: 4px solid #17365d;
    border-radius: 8px;
    margin: 8px 0 26px 0;
    box-shadow: 0 2px 8px rgba(15, 35, 60, 0.05);
}

.project-eyebrow {
    color: #52677f !important;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.8px;
    margin-bottom: 14px;
}

.project-title {
    color: #17365d !important;
    font-size: clamp(26px, 3vw, 36px);
    font-weight: 750;
    line-height: 1.25;
    margin: 0 0 12px 0;
}

.project-description {
    color: #526174 !important;
    font-size: 15px;
    line-height: 1.7;
    max-width: 850px;
    margin: 0;
}
</style>

<div class="project-header">
    <div class="project-eyebrow">
        AI RESILIENCE &nbsp; | &nbsp; KOCHI, KERALA, INDIA
    </div>

    
<h1 class="project-title">
    Urban Flood Mitigation Budget
    <br>
    &amp; Project Planning
</h1>

<p class="project-description">
    A public infrastructure planning dashboard for assessing proposed
    flood mitigation investments, monitoring project implementation,
    and supporting transparent budget allocation across Kochi, Kerala.
</p>

</div>
""", unsafe_allow_html=True)




st.caption(
    "Planning worksheet • User-supplied estimates • "
    "Budget comparison only; no automatic effectiveness ranking"
)

budget = st.number_input("Available budget (INR)", min_value=0, value=0, step=100000)
st.caption("Enter estimates only when you have a source, date, scope, and unit basis. Blank cost means unknown.")


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
]

starter = pd.DataFrame([
    [
        "Drainage maintenance / upgrade",
        "",
        "Proposed",
        "Medium",
        None,
        "",
        "",
        None,
        "",
    ],
    [
        "Hospital resilience (power / water / access)",
        "",
        "Proposed",
        "Medium",
        None,
        "",
        "",
        None,
        "",
    ],
    [
        "Evacuation infrastructure",
        "",
        "Proposed",
        "Medium",
        None,
        "",
        "",
        None,
        "",
    ],
    [
        "Building retrofit",
        "",
        "Proposed",
        "Medium",
        None,
        "",
        "",
        None,
        "",
    ],
], columns=columns)


st.markdown("### Project Register")
st.caption(
    "Record proposed mitigation works, estimated expenditure, "
    "implementation status, beneficiaries, and supporting evidence."
)

plan = st.data_editor(
    starter,
    hide_index=True,
    width="stretch",
    num_rows="dynamic",
    row_height=45,
    column_config={
        "Intervention": st.column_config.TextColumn(
            "Mitigation Project",
            help="Name of the proposed flood-mitigation intervention.",
            required=True,
        ),
        "Location": st.column_config.TextColumn(
            "Project Location",
            help="Specify the relevant area in Kochi.",
            required=True,
        ),
        "Project Status": st.column_config.SelectboxColumn(
            "Implementation Status",
            help="Update the current stage of the project.",
            options=[
                "Proposed",
                "Planned",
                "In Progress",
                "Completed",
                "On Hold",
            ],
            required=True,
        ),
        "Priority": st.column_config.SelectboxColumn(
            "Priority Level",
            help="Planning priority; confirm through an appropriate risk assessment.",
            options=["High", "Medium", "Low"],
            required=True,
        ),
        "Cost INR": st.column_config.NumberColumn(
            "Estimated Cost (₹)",
            help="Enter the estimated project cost in Indian rupees.",
            min_value=0,
            step=1000,
            format="₹%.0f",
        ),
        "Source / estimate date": st.column_config.TextColumn(
            "Cost Source / Date",
            help="Record the source, quotation date, or estimate reference.",
        ),
        "Scope and unit": st.column_config.TextColumn(
            "Scope and Measurement Unit",
            help="For example, drain cleaning in metres or pumps in units.",
        ),
        "Potential beneficiaries": st.column_config.NumberColumn(
            "Potential Beneficiaries",
            help="Enter an estimated number of people, where known.",
            min_value=0,
            step=1,
            format="%d",
        ),
        "Evidence for risk reduction": st.column_config.TextColumn(
            "Risk-Reduction Evidence",
            help="Add a report, study, survey, or other supporting reference.",
        ),
    },
)





st.markdown("## 📊 Mitigation Expenditure Report")
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

    st.markdown("### Project-wise Estimated Expenditure")
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
        color_continuous_scale=["#b9e4e8", "#117477", "#103653"],
        template="plotly_dark",
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
            gridcolor="#e4edf2",
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
            color="#193247",
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



    st.markdown("## Financial Overview")
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
st.markdown("### Budget Utilization Monitor")

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
st.markdown("### Financial Review")

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


st.markdown("## 📋 Project Summary")

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

st.markdown("## 📌 Project Status Overview")

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

    
st.markdown("## 📥 Export Mitigation Plan")

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

st.markdown("## Evidence & Data Quality")
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

st.markdown("---")
st.markdown("## 🎯 What Can You Do With Your Budget?")
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
    st.markdown("### Projects that fit individually")

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

from itertools import combinations

st.markdown("### 🧮 Affordable Project Combinations")

if budget <= 0:
    st.info("Enter a budget greater than ₹0 to compare combinations.")
else:
    combo_projects = plan.copy()
    combo_projects["_cost"] = pd.to_numeric(
        combo_projects["Cost INR"], errors="coerce"
    )

    # Exclude missing, zero, and invalid cost estimates.
    combo_projects = combo_projects[
        combo_projects["_cost"].notna()
        & (combo_projects["_cost"] > 0)
        & (combo_projects["_cost"] <= budget)
    ]

    combo_projects = combo_projects.reset_index(drop=True)

    if combo_projects.empty:
        st.info("Enter positive project cost estimates to compare combinations.")
    elif len(combo_projects) > 15:
        st.warning(
            "For this first version, the combination planner supports "
            "up to 15 projects. Reduce the list to compare combinations."
        )
    else:
        affordable_combinations = []

        for size in range(1, len(combo_projects) + 1):
            for indexes in combinations(range(len(combo_projects)), size):
                chosen = combo_projects.iloc[list(indexes)]
                total_cost = float(chosen["_cost"].sum())

                if total_cost <= budget:
                    affordable_combinations.append(
                        (total_cost, chosen["Intervention"].tolist())
                    )

        affordable_combinations.sort(
            key=lambda item: item[0], reverse=True
        )

        if affordable_combinations:
            best_total, best_names = affordable_combinations[0]

            st.success(
                f"An affordable combination totals "
                f"{format_inr(best_total)}, leaving "
                f"{format_inr(budget - best_total)}."
            )

            st.markdown("**Projects in this combination:**")
            for name in best_names:
                st.markdown(f"- {name}")

            st.caption(
                "This combination maximizes the amount of budget used "
                "among the entered projects. It does not rank safety "
                "benefits or determine the best real-world investment."
            )



"""Budget arithmetic for user-supplied intervention estimates."""

import pandas as pd
import streamlit as st

from src.decision_workflow import budget_summary

st.header("Budget-aware mitigation planning")
st.write("Organize candidate projects and compare entered costs with an available budget. This worksheet does not rank effectiveness or predict risk reduction.")
budget = st.number_input("Available budget (INR)", min_value=0, value=0, step=100000)
st.caption("Enter estimates only when you have a source, date, scope, and unit basis. Blank cost means unknown.")

columns = ["Intervention", "Location", "Cost INR", "Source / estimate date", "Scope and unit", "Potential beneficiaries", "Evidence for risk reduction"]
starter = pd.DataFrame([
    ["Drainage maintenance / upgrade", "", None, "", "", None, ""],
    ["Hospital resilience (power / water / access)", "", None, "", "", None, ""],
    ["Evacuation infrastructure", "", None, "", "", None, ""],
    ["Building retrofit", "", None, "", "", None, ""],
], columns=columns)
plan = st.data_editor(starter, hide_index=True, width="stretch", num_rows="dynamic", column_config={
    "Cost INR": st.column_config.NumberColumn(min_value=0, step=1000, format="₹%.0f"),
    "Potential beneficiaries": st.column_config.NumberColumn(min_value=0, step=1),
})

summary = budget_summary(plan["Cost INR"], budget)
total_known = float(summary["entered_total"])
unknown_count = summary["unknown_or_invalid_count"]
left, right = st.columns(2)
left.metric("Sum of entered costs", f"₹{total_known:,.0f}")
right.metric("Budget after entered costs", f"₹{budget-total_known:,.0f}")
if summary["within_budget"] is False:
    st.warning("Entered estimates exceed the available budget. This comparison excludes rows with unknown costs.")
elif unknown_count:
    st.info(f"{unknown_count} intervention row(s) have no cost. The remaining-budget figure is incomplete.")
else:
    st.success("All listed rows have costs entered; this is arithmetic only, not an optimized plan.")
evidence_missing = plan["Evidence for risk reduction"].fillna("").astype(str).str.strip().eq("")
st.caption(f"Risk-reduction evidence is blank for {int(evidence_missing.sum())} row(s). No benefit or effectiveness score is calculated. Beneficiary estimates are user-entered and may overlap.")
st.info("Before funding decisions, attach comparable engineering scope, current quotations, implementation and maintenance costs, target population, and a defensible impact evaluation.")

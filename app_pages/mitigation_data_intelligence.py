"""Evidence-first dataset intelligence dashboard for mitigation planning."""
from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import streamlit as st

from src.mitigation_data_validation import validate_records
from src.ui_theme import page_header, section_intro

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "reference"

DATASETS = [
    ("Core project records", "kerala_soil_conservation_completed_projects.csv", "project"),
    ("Supplemental source leads", "mitigation_project_supplemental_candidates.csv", "project"),
    ("AMRUT sector aggregates", "kerala_amrut_sector_aggregates.csv", "aggregate"),
]


def load_records(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


page_header(
    "AI RESILIENCE · DATA GOVERNANCE",
    "Mitigation Dataset Intelligence",
    "A transparent quality-control workspace for reviewing project evidence, "
    "data completeness and model readiness before investment estimates are used.",
    meta=("Evidence-first validation", "No automatic ML unlock", "Kochi pilot"),
    accent="cyan",
    key="mitigation-data-intelligence",
)

st.info(
    "This dashboard screens source records. It does not certify that a source is true, "
    "estimate intervention effectiveness, or train a model. Human source review remains required."
)

loaded = []
for label, filename, kind in DATASETS:
    path = DATA_DIR / filename
    if not path.exists():
        loaded.append({"label": label, "error": f"Missing file: {filename}", "kind": kind})
        continue
    records = load_records(path)
    result = validate_records(records, dataset_kind=kind)
    frame = pd.DataFrame(records)
    audit = pd.DataFrame(result["rows"])
    if not audit.empty:
        frame.insert(0, "row_number", range(1, len(frame) + 1))
        frame = frame.merge(audit, on="row_number", how="left", suffixes=("", "_audit"))
    loaded.append({"label": label, "filename": filename, "kind": kind,
                   "result": result, "frame": frame})

valid = [item for item in loaded if "result" in item]
total_records = sum(item["result"]["records_received"] for item in valid)
cost_ready = sum(item["result"]["cost_ml_eligible"] for item in valid)
duration_ready = sum(item["result"]["duration_ml_eligible"] for item in valid)
review_count = sum(item["result"]["review_required"] for item in valid)
rejected_count = sum(item["result"]["rejected"] for item in valid)

section_intro("SYSTEM SNAPSHOT", "Dataset quality overview",
              "Counts reflect the current CSVs in the repository branch, not live government feeds.")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Records scanned", f"{total_records:,}")
m2.metric("Cost-model eligible", f"{cost_ready:,}")
m3.metric("Duration-model eligible", f"{duration_ready:,}")
m4.metric("Review required", f"{review_count:,}")

st.caption(
    f"{rejected_count:,} rows are rejected by structural checks. "
    "A row can remain in the source register while being blocked from model training."
)

summary_rows = []
for item in valid:
    result = item["result"]
    summary_rows.append({
        "Dataset": item["label"],
        "Rows": result["records_received"],
        "Validated candidates": result["validated_candidates"],
        "Review required": result["review_required"],
        "Rejected": result["rejected"],
        "Cost ML eligible": result["cost_ml_eligible"],
        "Duration ML eligible": result["duration_ml_eligible"],
    })
st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

section_intro("RECORD REVIEW", "Inspect evidence and validation reasons",
              "Choose one dataset and filter its row-level findings. Use the source link to perform manual verification.")
dataset_labels = [item["label"] for item in valid]
if dataset_labels:
    selected_label = st.selectbox("Dataset", dataset_labels)
    selected = next(item for item in valid if item["label"] == selected_label)
    frame = selected["frame"].copy()
    statuses = ["All"] + sorted(frame["validation_status"].dropna().unique().tolist())
    status_filter = st.selectbox("Validation status", statuses)
    if status_filter != "All":
        frame = frame[frame["validation_status"] == status_filter]

    search = st.text_input("Find a project by name, district or record ID")
    if search.strip():
        searchable = [column for column in ("project_name", "district", "record_id", "candidate_id")
                      if column in frame.columns]
        mask = pd.Series(False, index=frame.index)
        for column in searchable:
            mask = mask | frame[column].fillna("").astype(str).str.contains(search, case=False, regex=False)
        frame = frame[mask]

    display_columns = [column for column in (
        "record_id", "candidate_id", "project_name", "district", "intervention",
        "scope_quantity", "scope_unit", "actual_cost_inr", "reported_cost_inr",
        "cost_basis", "status_reported", "completion_status", "validation_status",
        "cost_ml_eligible", "duration_ml_eligible", "issues", "review_reasons",
        "source_reference"
    ) if column in frame.columns]
    st.dataframe(frame[display_columns], use_container_width=True, hide_index=True)

    export = frame[display_columns].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download filtered audit rows",
        data=export,
        file_name="AI_RESILIENCE_mitigation_validation_rows.csv",
        mime="text/csv",
        use_container_width=False,
    )
else:
    st.warning("No dataset files were found. Check the repository data/reference folder.")

section_intro("MODEL GOVERNANCE", "What the readiness flags mean")
st.markdown(
    """
    - **Cost eligibility** requires a completed project, traceable and explicitly verified source,
      positive scope and cost, an approved final-cost basis, a price year, and an explicit
      cost-model approval flag.
    - **Duration eligibility** additionally requires exact start and completion dates, a
      positive duration consistent with those dates, and an explicit duration-model approval flag.
    - **Review required** means information is incomplete or has not been explicitly verified.
    - **Rejected** means a structural conflict or invalid value was detected.
    """
)
st.warning(
    "The current source files were not altered by this dashboard. Missing metadata must be "
    "verified from original documents; do not invent values to increase the eligible count."
)

with st.expander("Official data-quality reference"):
    st.markdown(
        "- [Kerala ODR content-quality guidelines](https://odr.ecostat.kerala.gov.in/help/content-quality)\n"
        "- [Kerala ODR metadata standards](https://odr.ecostat.kerala.gov.in/help/metadata-standards)\n"
        "- [Kerala Data Portal](https://www.datahub.kerala.gov.in/datasets)"
    )

"""Audit a Kochi flood-mitigation site/event panel before causal analysis.

This is a data-quality and design-readiness gate only. It does not estimate
intervention effects, create labels, or certify difference-in-differences
assumptions. One row must represent one site during one observed flood event.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED = {
    "observation_id", "site_id", "event_id", "event_date",
    "intervention_id", "implementation_date", "treated",
    "outcome_name", "outcome_value", "outcome_unit",
    "rainfall_mm", "source_id", "source_url",
}


def audit_panel(frame: pd.DataFrame) -> dict[str, Any]:
    problems: list[str] = []
    warnings: list[str] = []
    missing = sorted(REQUIRED - set(frame.columns))
    if missing:
        return {
            "schema_version": "kochi-intervention-panel-audit/1.0.0",
            "status": "BLOCKED_SCHEMA",
            "ready_for_causal_design_review": False,
            "row_count": int(len(frame)),
            "problems": [f"Missing required columns: {missing}"],
            "warnings": [],
        }
    if frame.empty:
        problems.append("The panel contains no observations.")
    data = frame.copy()
    for col in ("event_date", "implementation_date"):
        data[col] = pd.to_datetime(data[col], errors="coerce")
    if data["event_date"].isna().any():
        problems.append("event_date contains missing or invalid dates.")
    if data["implementation_date"].isna().all():
        problems.append("No implementation dates are documented.")
    elif data.loc[data["treated"].astype(str).isin(["1", "1.0", "True", "true"]), "implementation_date"].isna().any():
        problems.append("Treated observations require a documented implementation_date.")

    treated = pd.to_numeric(data["treated"], errors="coerce")
    if treated.isna().any() or not set(treated.dropna().unique()).issubset({0, 1}):
        problems.append("treated must contain only binary 0/1 values.")
    else:
        data["treated"] = treated.astype(int)
    numeric = pd.to_numeric(data["outcome_value"], errors="coerce")
    if numeric.isna().any() or not pd.Series(numeric).map(lambda x: pd.notna(x) and abs(float(x)) != float("inf")).all():
        problems.append("outcome_value must be finite numeric data with no missing values.")
    else:
        data["outcome_value"] = numeric
    if data["observation_id"].isna().any() or data["observation_id"].astype(str).str.strip().eq("").any():
        problems.append("observation_id cannot be blank.")
    if data["site_id"].isna().any() or data["event_id"].isna().any():
        problems.append("site_id and event_id cannot be blank.")
    if data.duplicated(["site_id", "event_id"]).any():
        problems.append("Duplicate site_id/event_id observations exist; resolve them before analysis.")
    for col in ("intervention_id", "outcome_name", "outcome_unit", "source_id", "source_url"):
        if data[col].isna().any() or data[col].astype(str).str.strip().eq("").any():
            problems.append(f"{col} must be complete for every observation.")
    if data["outcome_name"].nunique(dropna=True) > 1:
        problems.append("A panel must contain one consistently defined outcome; split different outcomes.")
    if data["outcome_unit"].nunique(dropna=True) > 1:
        problems.append("Outcome units differ within the panel; standardise or split the panel.")
    if data["intervention_id"].nunique(dropna=True) > 1:
        problems.append("Different intervention versions are mixed; audit each intervention separately.")
    if "rainfall_mm" in data and pd.to_numeric(data["rainfall_mm"], errors="coerce").isna().any():
        warnings.append("Some rainfall_mm values are missing or non-numeric; rainfall adjustment may be impossible.")
    if "tide_level_m" not in data.columns:
        warnings.append("tide_level_m is absent; coastal/tidal confounding cannot be assessed from this panel.")
    if "river_level_m" not in data.columns:
        warnings.append("river_level_m is absent; river-level confounding cannot be assessed from this panel.")

    treated_sites = int(data.loc[data.get("treated", pd.Series(dtype=int)).eq(1), "site_id"].nunique()) if "treated" in data else 0
    control_sites = int(data.loc[data.get("treated", pd.Series(dtype=int)).eq(0), "site_id"].nunique()) if "treated" in data else 0
    event_count = int(data["event_id"].nunique()) if "event_id" in data else 0
    pre_rows = post_rows = 0
    if not data["event_date"].isna().any() and not data["implementation_date"].isna().all() and "treated" in data:
        dated = data.dropna(subset=["implementation_date"]).copy()
        pre_rows = int((dated["event_date"] < dated["implementation_date"]).sum())
        post_rows = int((dated["event_date"] >= dated["implementation_date"]).sum())
        if (dated.loc[dated["treated"].eq(1), "event_date"] < dated.loc[dated["treated"].eq(1), "implementation_date"]).any():
            problems.append("A treated=1 observation occurs before its intervention implementation date.")
        if (dated.loc[dated["treated"].eq(0), "event_date"] >= dated.loc[dated["treated"].eq(0), "implementation_date"]).any():
            problems.append("A treated=0 observation occurs after its recorded implementation date.")

    if treated_sites < 2:
        problems.append("Fewer than two treated sites are represented.")
    if control_sites < 2:
        problems.append("Fewer than two comparison sites are represented.")
    if event_count < 4:
        problems.append("Fewer than four distinct flood events are represented; at least two pre- and two post-period events are needed for design review.")
    if pre_rows < 2 or post_rows < 2:
        problems.append("Insufficient pre/post observations around implementation for a basic panel design review.")
    if "source_url" in data and not data["source_url"].astype(str).str.match(r"^https?://").all():
        problems.append("Every source_url must be a resolvable http(s) source reference.")

    ready = not problems
    return {
        "schema_version": "kochi-intervention-panel-audit/1.0.0",
        "status": "READY_FOR_DESIGN_REVIEW_NOT_CAUSAL_PROOF" if ready else "BLOCKED_DATA_OR_DESIGN_GAPS",
        "ready_for_causal_design_review": ready,
        "causal_effect_estimated": False,
        "validated_effect": False,
        "row_count": int(len(data)),
        "site_count": int(data["site_id"].nunique()) if "site_id" in data else 0,
        "event_count": event_count,
        "treated_site_count": treated_sites,
        "comparison_site_count": control_sites,
        "pre_implementation_rows": pre_rows,
        "post_implementation_rows": post_rows,
        "outcome_name": str(data["outcome_name"].iloc[0]) if len(data) and "outcome_name" in data else None,
        "outcome_unit": str(data["outcome_unit"].iloc[0]) if len(data) and "outcome_unit" in data else None,
        "problems": problems,
        "warnings": warnings,
        "mandatory_review": [
            "Check parallel-trends plausibility using multiple pre-intervention events.",
            "Check intervention targeting, concurrent works, spillovers and changing exposure.",
            "Adjust for event-specific rainfall, tide, river level and antecedent conditions where observed.",
            "Verify outcome measurement comparability and missingness across sites and events.",
            "Obtain independent methodological review before any effect estimate is interpreted.",
        ],
        "interpretation": (
            "Passing this audit only means the file meets basic structural checks for human design review. "
            "It does not establish parallel trends, exchangeability, no spillovers, or causal identification."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Site-by-flood-event panel CSV.")
    parser.add_argument("--output", default="reports/kochi_intervention_panel_audit.json")
    args = parser.parse_args()
    path = Path(args.data)
    if not path.is_file():
        raise SystemExit(f"BLOCKED: panel file does not exist: {path}")
    result = audit_panel(pd.read_csv(path))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["ready_for_causal_design_review"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

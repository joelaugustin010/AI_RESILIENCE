from __future__ import annotations

import pandas as pd

from scripts.audit_kochi_intervention_panel import audit_panel


def _panel():
    rows = []
    dates = ["2018-06-01", "2019-06-01", "2020-06-01", "2021-06-01"]
    for site, implementation in [("T1", "2019-12-01"), ("T2", "2019-12-01"), ("C1", "2030-01-01"), ("C2", "2030-01-01")]:
        for index, date in enumerate(dates):
            rows.append({
                "observation_id": f"{site}-{index}",
                "site_id": site,
                "event_id": f"E{index}",
                "event_date": date,
                "intervention_id": "drainage_upgrade_v1",
                "implementation_date": implementation,
                "treated": int(site.startswith("T") and date >= implementation),
                "outcome_name": "inundation_depth",
                "outcome_value": 10 + index,
                "outcome_unit": "cm",
                "rainfall_mm": 100 + index,
                "tide_level_m": 0.5,
                "river_level_m": 1.0,
                "source_id": f"source-{site}-{index}",
                "source_url": "https://example.org/verified-record",
            })
    return pd.DataFrame(rows)


def test_panel_audit_only_grants_design_review_not_causal_proof():
    result = audit_panel(_panel())
    assert result["ready_for_causal_design_review"] is True
    assert result["causal_effect_estimated"] is False
    assert result["validated_effect"] is False
    assert result["treated_site_count"] == 2
    assert result["comparison_site_count"] == 2


def test_panel_audit_blocks_missing_comparison_sites():
    frame = _panel()
    frame = frame[frame.site_id.str.startswith("T")]
    result = audit_panel(frame)
    assert result["ready_for_causal_design_review"] is False
    assert any("comparison sites" in issue for issue in result["problems"])


def test_panel_audit_blocks_duplicate_site_event_rows():
    frame = _panel()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    result = audit_panel(frame)
    assert any("Duplicate site_id/event_id" in issue for issue in result["problems"])


def test_panel_audit_blocks_mixed_outcome_units_and_interventions():
    frame = _panel()
    frame.loc[0, "outcome_unit"] = "hours"
    frame.loc[1, "intervention_id"] = "different_intervention"
    result = audit_panel(frame)
    assert any("Outcome units differ" in issue for issue in result["problems"])
    assert any("Different intervention versions" in issue for issue in result["problems"])


def test_panel_audit_blocks_non_finite_outcomes():
    frame = _panel()
    frame.loc[0, "outcome_value"] = float("inf")
    result = audit_panel(frame)
    assert any("finite numeric" in issue for issue in result["problems"])

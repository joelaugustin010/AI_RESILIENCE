import pandas as pd
import pytest
from src.ml.kochi_flood_panel import FloodPanelError, evaluate_flood_event_panel, validate_flood_event_panel

def panel(events=20, sites=4):
    rows = []
    for event in range(events):
        for site in range(sites):
            issue = pd.Timestamp("2020-01-01", tz="UTC") + pd.Timedelta(days=event * 30)
            flooded = (event + site) % 2 == 0
            rows.append({"event_id": f"event-{event}", "site_id": f"site-{site}",
                "issue_time": issue.isoformat(), "feature_time": (issue-pd.Timedelta(hours=1)).isoformat(),
                "outcome_time": (issue+pd.Timedelta(hours=6)).isoformat(),
                "inundation_observed": flooded, "negative_observation_verified": not flooded,
                "observation_source_id": f"source-{event}-{site}",
                "observation_coverage": "complete reviewed imagery",
                "rainfall_24h_mm": float(event+site+1), "rainfall_72h_mm": float(event+site+2),
                "river_level_m": float(site+0.5), "tide_level_m": float(site+0.2)})
    return pd.DataFrame(rows)

def test_validates_panel_and_blocks_operational_use():
    result = validate_flood_event_panel(panel())
    assert result.report["status"] == "PANEL_SCHEMA_VALIDATED_NOT_MODEL_VALIDATED"
    assert result.report["unique_events"] == 20
    assert result.report["operational_prediction_allowed"] is False

def test_rejects_negative_without_verified_coverage():
    data = panel()
    row = data.index[data.inundation_observed == False][0]
    data.loc[row, "negative_observation_verified"] = False
    with pytest.raises(FloodPanelError, match="verified observation"):
        validate_flood_event_panel(data)

def test_rejects_feature_time_after_issue():
    data = panel()
    data.loc[0, "feature_time"] = (pd.Timestamp(data.loc[0, "issue_time"])+pd.Timedelta(minutes=1)).isoformat()
    with pytest.raises(FloodPanelError, match="future leakage"):
        validate_flood_event_panel(data)

def test_rejects_outcome_before_issue():
    data = panel()
    data.loc[0, "outcome_time"] = (pd.Timestamp(data.loc[0, "issue_time"])-pd.Timedelta(minutes=1)).isoformat()
    with pytest.raises(FloodPanelError, match="later than issue_time"):
        validate_flood_event_panel(data)

def test_temporal_holdout_keeps_events_separate_and_is_research_only():
    result = evaluate_flood_event_panel(panel())
    assert result["status"] == "RESEARCH_BASELINE_EVALUATED_NOT_OPERATIONAL"
    metrics = result["model_metrics"]
    assert metrics["train_events"] + metrics["test_events"] == 20
    assert result["operational_prediction_allowed"] is False

def test_blocks_small_panel():
    result = evaluate_flood_event_panel(panel(events=8))
    assert result["status"] == "BLOCKED_INSUFFICIENT_EVENTS_OR_SITES"
    assert result["model_metrics"] is None

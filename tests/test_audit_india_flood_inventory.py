"""Tests for the public India Flood Inventory source audit."""
import pandas as pd

from scripts.audit_india_flood_inventory import audit_inventory


def _frame():
    return pd.DataFrame([
        {
            "UEI": "UEI-IMD-FL-2018-0001",
            "Start Date": "15-08-2018 00:00",
            "End Date": "20-08-2018 00:00",
            "State": "Kerala",
            "Districts": "Ernakulam, Idukki",
            "Latitude": 9.98,
            "Longitude": 76.28,
            "Severity": "Severe",
            "Area Affected": 120.0,
            "Human fatality": 4,
            "Human injured": 10,
            "Human Displaced": 200,
            "Event Source": "IMD",
        },
        {
            "UEI": "UEI-IMD-FL-2019-0001",
            "Start Date": "21-10-2019 00:00",
            "End Date": "22-10-2019 00:00",
            "State": "Kerala",
            "Districts": "Ernakulam",
            "Latitude": None,
            "Longitude": None,
            "Severity": "Moderate",
            "Area Affected": None,
            "Human fatality": None,
            "Human injured": None,
            "Human Displaced": None,
            "Event Source": "IMD",
        },
    ])


def test_audit_reports_public_event_inventory_without_claiming_training_readiness():
    report = audit_inventory(_frame(), md5="verified")
    assert report["status"] == "AUDITED_EVENT_INVENTORY_NOT_LOCAL_INUNDATION_GROUND_TRUTH"
    assert report["row_count"] == 2
    assert report["kerala_or_ernakulam_text_match_count"] == 2
    assert report["complete_coordinate_pair_count"] == 1
    assert report["training_ready"] is False


def test_audit_rejects_duplicate_event_identifiers():
    frame = _frame()
    frame.loc[1, "UEI"] = frame.loc[0, "UEI"]
    report = audit_inventory(frame)
    assert report["status"] == "BLOCKED_DATA_QUALITY"
    assert any("UEI is not unique" in problem for problem in report["problems"])


def test_audit_rejects_invalid_event_dates_and_coordinates():
    frame = _frame()
    frame.loc[0, "End Date"] = "01-01-2018"
    frame.loc[0, "Latitude"] = 120
    report = audit_inventory(frame)
    assert report["status"] == "BLOCKED_DATA_QUALITY"
    assert any("End Date precedes" in problem for problem in report["problems"])
    assert any("out-of-range coordinates" in problem for problem in report["problems"])


def test_audit_blocks_missing_source_schema():
    report = audit_inventory(pd.DataFrame({"UEI": ["x"]}))
    assert report["status"] == "BLOCKED_SCHEMA"
    assert report["training_ready"] is False


def test_audit_distinguishes_successful_audit_from_training_readiness():
    from scripts.audit_india_flood_inventory import audit_inventory
    report = audit_inventory(_frame())
    assert report["status"] == "AUDITED_EVENT_INVENTORY_NOT_LOCAL_INUNDATION_GROUND_TRUTH"
    assert report["training_ready"] is False

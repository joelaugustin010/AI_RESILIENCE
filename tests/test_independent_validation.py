from __future__ import annotations

import json

import pytest

from scripts.independent_validation import (
    append_shadow_record, evaluate, validate_partitions,
)


def sample_rows():
    rows = []
    # Separate spatial groups and event identifiers for each partition.
    for split, groups in (("train", ["train-a"]), ("calibration", ["cal-a"]),
                          ("test", ["test-a", "test-b"])):
        for gi, group in enumerate(groups):
            for i in range(24):
                y = int(i % 3 == 0)
                p = 0.65 if y else 0.25
                rows.append({"split": split, "spatial_group": group,
                             "event_id": f"{split}-{group}-{i}",
                             "y_true": y, "probability": p})
    return rows


def test_spatial_holdout_and_worst_location_report():
    report = evaluate(sample_rows())
    assert report["partition_rows"]["test"] == 48
    assert len(report["worst_location"]) == 2
    assert report["clearance"]["operational"] is False


def test_rejects_spatial_group_overlap():
    rows = sample_rows()
    rows.append({"split": "test", "spatial_group": "cal-a", "event_id": "new-event",
                 "y_true": 0, "probability": 0.2})
    with pytest.raises(ValueError, match="Spatial leakage"):
        validate_partitions(rows)


def test_rejects_event_crossing_splits():
    rows = sample_rows()
    rows.append({"split": "test", "spatial_group": "test-c", "event_id": "train-train-a-0",
                 "y_true": 0, "probability": 0.2})
    with pytest.raises(ValueError, match="Event leakage"):
        validate_partitions(rows)


def test_shadow_log_is_append_only_and_explicitly_non_operational(tmp_path):
    path = tmp_path / "shadow.jsonl"
    record = {"issued_at_utc": "2026-11-07T10:00:00+00:00",
              "data_as_of_utc": "2026-11-07T09:55:00+00:00",
              "model_id": "test-model", "model_version": "abc123",
              "location_id": "ward-x", "prediction": 0.4, "input_status": "fresh"}
    append_shadow_record(path, record)
    append_shadow_record(path, record)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["mode"] == "shadow_only_no_alerts_no_automated_actions"


def test_shadow_log_rejects_naive_timestamp(tmp_path):
    record = {"issued_at_utc": "2026-11-07T10:00:00",
              "data_as_of_utc": "2026-11-07T09:55:00+00:00",
              "model_id": "test-model", "model_version": "abc123",
              "location_id": "ward-x", "prediction": 0.4, "input_status": "fresh"}
    with pytest.raises(ValueError, match="timezone"):
        append_shadow_record(tmp_path / "shadow.jsonl", record)

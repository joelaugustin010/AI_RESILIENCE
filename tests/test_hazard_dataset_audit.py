"""Tests for separating raw-source acquisition from supervised-model readiness."""
import json
from pathlib import Path

from scripts.audit_hazard_datasets import build_report


def test_nested_raw_source_is_found_without_claiming_model_readiness(tmp_path: Path):
    registry = tmp_path / "data" / "external" / "hazard_dataset_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "hazards": [{
            "id": "earthquake",
            "label": "Earthquake",
            "source": "USGS",
            "url": "https://example.org",
            "limitation": "Event catalogue only.",
        }]
    }), encoding="utf-8")

    raw = tmp_path / "data" / "external" / "hazards" / "raw" / "earthquake" / "usgs_india_events_2000_present.csv"
    raw.parent.mkdir(parents=True)
    raw.write_text("time,latitude,longitude,mag\n2020-01-01,10,76,3.1\n", encoding="utf-8")

    report = build_report(tmp_path)
    hazard = report["hazards"][0]

    assert hazard["raw_source_count"] == 1
    assert hazard["raw_sources"][0]["status"] == "PRESENT_RAW_SOURCE_NOT_VALIDATED_FOR_PREDICTION"
    assert hazard["raw_sources"][0]["has_explicit_target_column"] is False
    assert hazard["curated_training_table"]["status"] == "MISSING_CURATED_TRAINING_TABLE"
    assert hazard["model_status"] == "NO_CURATED_TRAINING_TABLE"
    assert report["research_baselines_found_in_separate_report"] == 0


def test_missing_raw_source_is_not_confused_with_curated_training_table(tmp_path: Path):
    registry = tmp_path / "data" / "external" / "hazard_dataset_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "hazards": [{
            "id": "wildfire",
            "label": "Wildfire",
            "source": "NASA",
            "url": "https://example.org",
            "limitation": "No background samples.",
        }]
    }), encoding="utf-8")

    report = build_report(tmp_path)
    hazard = report["hazards"][0]

    assert hazard["raw_source_count"] == 0
    assert hazard["curated_training_table"]["status"] == "MISSING_CURATED_TRAINING_TABLE"
    assert hazard["model_status"] == "NOT_READY"


def test_existing_weather_research_baselines_are_not_hidden_by_missing_curated_tables(tmp_path: Path):
    registry = tmp_path / "data" / "external" / "hazard_dataset_registry.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(json.dumps({
        "hazards": [
            {"id": "heatwave", "label": "Heatwave", "source": "weather", "url": "https://example.org"},
            {"id": "severe_storm", "label": "Rain", "source": "weather", "url": "https://example.org"},
        ]
    }), encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "weather_hazard_training.json").write_text(json.dumps({
        "models": [
            {"hazard": "high_temperature", "status": "RESEARCH_BASELINE_TRAINED_NOT_VALIDATED",
             "metrics": {"f1": 0.6}, "test_target_dates_from": "2020-01-01", "locations": ["kochi"]},
            {"hazard": "extreme_rainfall", "status": "RESEARCH_BASELINE_TRAINED_NOT_VALIDATED",
             "metrics": {"f1": 0.3}, "test_target_dates_from": "2020-01-01", "locations": ["kochi"]},
        ]
    }), encoding="utf-8")

    report = build_report(tmp_path)
    assert report["research_baselines_found_in_separate_report"] == 2
    assert report["hazards"][0]["model_status"] == "RESEARCH_BASELINE_EXISTS_NOT_VALIDATED"
    assert report["hazards"][0]["research_baseline"]["metrics"]["f1"] == 0.6
    assert report["hazards"][1]["model_status"] == "RESEARCH_BASELINE_EXISTS_NOT_VALIDATED"

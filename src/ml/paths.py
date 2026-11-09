"""Filesystem locations used by the shared ML engine."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "external" / "hazards" / "raw"
WEATHER_ROOT = DATA_ROOT / "weather"
CYCLONE_ROOT = DATA_ROOT / "cyclone"
EARTHQUAKE_ROOT = DATA_ROOT / "earthquake"
LANDSLIDE_ROOT = DATA_ROOT / "landslide"
MODELS_ROOT = ROOT / "models" / "ml"
REPORTS_ROOT = ROOT / "reports"
REGISTRY_PATH = REPORTS_ROOT / "ml_model_registry.json"
COVERAGE_PATH = REPORTS_ROOT / "ml_disaster_coverage.json"
VALIDATION_PATH = REPORTS_ROOT / "ml_validation_report.json"


def model_dir(model_id: str) -> Path:
    return MODELS_ROOT / model_id


def artifact_path(model_id: str) -> Path:
    return model_dir(model_id) / "model.joblib"


def card_path(model_id: str) -> Path:
    return model_dir(model_id) / "model_card.json"

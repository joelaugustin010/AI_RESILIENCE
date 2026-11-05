"""Audit raw hazard sources separately from curated model-training tables.

Raw source availability is not proof of labels, predictors, local relevance, or model
validity. The report deliberately keeps these states separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "external" / "hazard_dataset_registry.json"
GROUP_CANDIDATES = ("event_id", "storm_id", "year", "station_id", "location_id", "group_id")
TIME_CANDIDATES = ("timestamp", "time", "date", "datetime", "valid_time")

# Exact repository paths of acquired raw sources. Never treat these as training tables.
SOURCE_FILES = {
    "earthquake": ["data/external/hazards/raw/earthquake/usgs_india_events_2000_present.csv"],
    "cyclone": ["data/external/hazards/raw/cyclone/ibtracs_north_indian_ocean_v04r01.csv"],
    "landslide": ["data/external/hazards/raw/landslide/nasa_global_landslide_catalog.csv"],
    "drought": [
        "data/external/hazards/raw/drought/india_current_cdi.txt",
        "data/external/hazards/raw/drought/india_drought_area_timeseries.txt",
        "data/external/hazards/raw/weather/kochi_daily_weather_1991_2025.json",
    ],
    "heatwave": [
        "data/external/hazards/raw/weather/kochi_daily_weather_1991_2025.json",
        "data/external/hazards/raw/weather/kochi_daily_weather_2000_2025.json",
        "data/external/hazards/raw/weather/kottayam_daily_weather_2000_2025.json",
        "data/external/hazards/raw/weather/wayanad_daily_weather_2000_2025.json",
        "data/external/hazards/raw/weather/thiruvananthapuram_daily_weather_2000_2025.json",
    ],
    "severe_storm": [
        "data/external/hazards/raw/weather/kochi_daily_weather_1991_2025.json",
        "data/external/hazards/raw/weather/kochi_daily_weather_2000_2025.json",
        "data/external/hazards/raw/weather/kottayam_daily_weather_2000_2025.json",
        "data/external/hazards/raw/weather/wayanad_daily_weather_2000_2025.json",
        "data/external/hazards/raw/weather/thiruvananthapuram_daily_weather_2000_2025.json",
    ],
    "wildfire": [],
    "tsunami": [],
    "air_pollution": [
        "data/processed/air_quality/kspcb_caaqms_eloor_aqi_2026-08.csv",
        "data/processed/air_quality/kspcb_caaqms_eloor_aqi_2026-09.csv",
        "data/processed/air_quality/kspcb_caaqms_eloor_daily_2026-08.csv",
        "data/processed/air_quality/kspcb_caaqms_eloor_daily_2026-09.csv",
        "data/processed/air_quality/kspcb_daily_aqi_2026-10-16.csv",
        "data/processed/air_quality/kspcb_namp_ernakulam_2025-06.csv",
    ],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_csv(path: Path) -> dict[str, Any]:
    """Check a candidate training table; a raw source without target remains NOT_READY."""
    result: dict[str, Any] = {"file": str(path), "status": "NOT_READY", "issues": [], "rows": 0}
    try:
        frame = pd.read_csv(path, low_memory=False)
    except Exception as exc:
        result["issues"].append(f"Could not read CSV: {type(exc).__name__}: {exc}")
        return result
    result["rows"] = int(len(frame))
    result["columns"] = list(frame.columns)
    if len(frame) < 100:
        result["issues"].append("Fewer than 100 rows; justify sample size before modelling.")
    target = "target" if "target" in frame.columns else None
    if target is None:
        result["issues"].append("No explicit target label; raw observations are not a supervised training table.")
    elif frame[target].nunique(dropna=True) < 2:
        result["issues"].append("Target has fewer than two non-null classes.")
    elif frame[target].isna().any():
        result["issues"].append("Target has missing labels; resolve or explicitly exclude them.")
    group = next((column for column in GROUP_CANDIDATES if column in frame.columns), None)
    if group is None:
        result["issues"].append("No recognized event/storm/year/station grouping column for leakage-safe evaluation.")
    else:
        result["group_column"] = group
        result["groups"] = int(frame[group].nunique(dropna=True))
        if result["groups"] < 5:
            result["issues"].append("Fewer than five independent groups; group-held-out evaluation is unreliable.")
    time_col = next((column for column in TIME_CANDIDATES if column in frame.columns), None)
    if time_col is None:
        result["issues"].append("No recognized time column; temporal leakage cannot be audited.")
    else:
        result["time_column"] = time_col
    predictors = [
        column for column in frame.columns
        if column not in {target, group, time_col}
        and not column.lower().endswith(("_id", "_url"))
    ]
    result["candidate_predictors"] = predictors
    if len(predictors) < 2:
        result["issues"].append("Fewer than two candidate predictor columns.")
    if not result["issues"]:
        result["status"] = "CANDIDATE_READY_FOR_REVIEW"
        result["issues"].append(
            "Human review still required: target definition, feature availability time, units, licence, "
            "class balance, geographic relevance, and independent holdout evaluation."
        )
    return result


def inspect_raw_source(path: Path, relative: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "file": relative,
        "exists": path.is_file(),
        "status": "MISSING",
    }
    if not path.is_file():
        return result
    result.update({
        "status": "PRESENT_RAW_SOURCE_NOT_VALIDATED_FOR_PREDICTION",
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "format": path.suffix.lower().lstrip(".") or "unknown",
    })
    if path.suffix.lower() == ".csv":
        try:
            frame = pd.read_csv(path, nrows=5, low_memory=False)
            result["columns_sample"] = [str(column) for column in frame.columns]
            result["has_explicit_target_column"] = "target" in frame.columns
        except Exception as exc:
            result["status"] = "PRESENT_BUT_UNREADABLE"
            result["error"] = f"{type(exc).__name__}: {exc}"
    elif path.suffix.lower() == ".json":
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            result["json_root_type"] = type(payload).__name__
            if isinstance(payload, dict):
                result["top_level_keys"] = list(payload.keys())
                daily = payload.get("daily")
                if isinstance(daily, dict):
                    result["daily_record_count"] = max(
                        (len(values) for values in daily.values() if isinstance(values, list)),
                        default=0,
                    )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            result["status"] = "PRESENT_BUT_UNREADABLE"
            result["error"] = f"{type(exc).__name__}: {exc}"
    elif path.suffix.lower() == ".txt":
        try:
            with path.open("r", encoding="utf-8", errors="replace") as stream:
                result["line_count"] = sum(1 for _ in stream)
        except OSError as exc:
            result["status"] = "PRESENT_BUT_UNREADABLE"
            result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def build_report(root: Path = ROOT, data_dir: Path | None = None) -> dict[str, Any]:
    root = Path(root)
    registry_path = root / "data" / "external" / "hazard_dataset_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    curated_dir = Path(data_dir) if data_dir is not None else root / "data" / "external" / "hazards"
    if not curated_dir.is_absolute():
        curated_dir = root / curated_dir
    training_path = root / "reports" / "weather_hazard_training.json"
    try:
        training_report = json.loads(training_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        training_report = {}
    baseline_map = {
        "high_temperature": "heatwave",
        "extreme_rainfall": "severe_storm",
    }
    research_baselines = {
        baseline_map.get(model.get("hazard"), model.get("hazard", "unknown")): model
        for model in training_report.get("models", [])
        if isinstance(model, dict)
    }

    hazards = []
    for item in registry["hazards"]:
        hazard_id = item["id"]
        sources = [
            inspect_raw_source(root / relative, relative)
            for relative in SOURCE_FILES.get(hazard_id, [])
        ]
        curated_path = curated_dir / f"{hazard_id}.csv"
        curated = (
            audit_csv(curated_path)
            if curated_path.is_file()
            else {
                "file": str(curated_path.relative_to(root)) if curated_path.is_relative_to(root) else str(curated_path),
                "status": "MISSING_CURATED_TRAINING_TABLE",
                "issues": ["No curated, explicitly labelled training table exists at this path."],
            }
        )
        baseline = research_baselines.get(hazard_id)
        if baseline:
            model_status = "RESEARCH_BASELINE_EXISTS_NOT_VALIDATED"
        elif curated["status"] == "CANDIDATE_READY_FOR_REVIEW":
            model_status = "CURATED_TABLE_CANDIDATE_REQUIRES_INDEPENDENT_REVIEW"
        else:
            model_status = "NO_CURATED_TRAINING_TABLE"
        hazards.append({
            "hazard_id": hazard_id,
            "label": item["label"],
            "source": item["source"],
            "source_url": item["url"],
            "raw_sources": sources,
            "raw_source_count": sum(source["exists"] and source["status"] != "PRESENT_BUT_UNREADABLE" for source in sources),
            "curated_training_table": curated,
            "research_baseline": {
                "status": baseline.get("status", "Status not recorded"),
                "hazard": baseline.get("hazard"),
                "metrics": baseline.get("metrics", {}),
                "test_target_dates_from": baseline.get("test_target_dates_from"),
                "locations": baseline.get("locations", []),
            } if baseline else None,
            "model_status": model_status,
            "scientific_limitation": item.get("limitation", "Target and evaluation design require review."),
        })
    present = sum(hazard["raw_source_count"] > 0 for hazard in hazards)
    return {
        "status": "RAW_SOURCE_AUDIT_AND_TRAINING_READINESS",
        "generated_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "raw_sources_available_for_hazards": present,
        "hazard_tracks": len(hazards),
        "research_baselines_found_in_separate_report": len(research_baselines),
        "warning": (
            "Raw data availability, a curated training table, a research baseline, and a validated local "
            "prediction model are separate states. Research baselines referenced here are not certified forecasts."
        ),
        "hazards": hazards,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data/external/hazards"))
    parser.add_argument("--output", type=Path, default=Path("reports/hazard_dataset_readiness.json"))
    args = parser.parse_args()
    report = build_report(ROOT, args.data_dir)
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "hazard_tracks": report["hazard_tracks"],
        "raw_sources_available_for_hazards": report["raw_sources_available_for_hazards"],
        "research_baselines_found_in_separate_report": report["research_baselines_found_in_separate_report"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

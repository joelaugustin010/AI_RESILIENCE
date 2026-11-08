"""Verify the tracked ML release bundle without promoting research artifacts.

This check validates presence and JSON consistency only. It does not claim
predictive validity, load arbitrary model binaries, or make an operational
promotion decision.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MODEL_IDS = {
    "weather_extreme_rainfall_kochi_nextday",
    "weather_high_temperature_kochi_nextday",
    "weather_drought_onset_kochi_30day",
    "cyclone_rapid_intensification_24h",
    "earthquake_aftershock_occurrence",
    "compound_cyclone_rainfall_interaction",
    "weather_precipitation_kochi_nextday_regression",
    "weather_tmax_kochi_nextday_regression",
    "cyclone_wind_change_24h_regression",
}
REPORTS = (
    "reports/ml_model_registry.json",
    "reports/ml_validation_report.json",
    "reports/ml_disaster_coverage.json",
)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def verify_release_bundle(root: Path = ROOT) -> dict[str, Any]:
    problems: list[str] = []
    cards: dict[str, dict[str, Any]] = {}
    for model_id in sorted(EXPECTED_MODEL_IDS):
        directory = root / "models" / "ml" / model_id
        binary = directory / "model.joblib"
        card_path = directory / "model_card.json"
        if not binary.is_file() or binary.stat().st_size == 0:
            problems.append(f"{model_id}: missing or empty model.joblib")
        if not card_path.is_file():
            problems.append(f"{model_id}: missing model_card.json")
            continue
        try:
            card = _read_json(card_path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            problems.append(f"{model_id}: invalid model card ({exc})")
            continue
        if card.get("model_id") != model_id:
            problems.append(f"{model_id}: model card ID mismatch")
        if not isinstance(card.get("feature_columns"), list) or not card["feature_columns"]:
            problems.append(f"{model_id}: feature_columns missing or empty")
        if card.get("validation_status") != "SINGLE_TEMPORAL_HOLDOUT_NOT_INDEPENDENTLY_VALIDATED":
            problems.append(f"{model_id}: unexpected validation status; manual review required")
        cards[model_id] = card

    reports: dict[str, dict[str, Any]] = {}
    for relative in REPORTS:
        path = root / relative
        if not path.is_file():
            problems.append(f"missing required report: {relative}")
            continue
        try:
            reports[relative] = _read_json(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            problems.append(f"invalid report {relative}: {exc}")

    validation = reports.get("reports/ml_validation_report.json", {})
    coverage = reports.get("reports/ml_disaster_coverage.json", {})
    if validation.get("validated_models") != 0:
        problems.append("validation report must explicitly retain validated_models=0")
    if coverage.get("validated_models") != 0:
        problems.append("coverage report must explicitly retain validated_models=0")
    if coverage.get("n_hazards") != 10:
        problems.append("coverage report must enumerate all 10 workflow hazards")
    if coverage.get("predictive_model_coverage_complete") is not False:
        problems.append("coverage report must not claim complete predictive-model coverage")

    return {
        "passed": not problems,
        "expected_model_count": len(EXPECTED_MODEL_IDS),
        "cards_found": len(cards),
        "reports_found": len(reports),
        "validated_models_reported": validation.get("validated_models"),
        "problems": problems,
        "scope": "Artifact integrity only; not empirical or operational model validation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = verify_release_bundle(args.root.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

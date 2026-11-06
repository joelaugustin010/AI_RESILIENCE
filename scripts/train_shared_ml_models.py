"""Train the shared, leakage-aware ML models and publish model cards.

Run from the repository root:

    python scripts/train_shared_ml_models.py

The script uses only repository-held data and scikit-learn estimators.  It
writes artifacts under ``models/ml/<model_id>/`` and reports under ``reports/``.
A model is never labelled validated; each card records the exact temporal split,
holdout metrics, calibration diagnostics and limitations.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ml.coverage import build_coverage_matrix
from src.ml.data import (
    build_aftershock_dataset,
    build_compound_cyclone_rainfall_dataset,
    build_cyclone_intensification_dataset,
    build_landslide_readiness_dataset,
    build_weather_target_dataset,
)
from src.ml.paths import REPORTS_ROOT, VALIDATION_PATH
from src.ml.persistence import write_json
from src.ml.registry import register
from src.ml.training import TrainingConfig, train_model
from src.ml.regression import train_weather_regression_models

MODEL_SPECS: tuple[tuple[str, dict], ...] = (
    (
        "weather_extreme_rainfall_kochi_nextday",
        {
            "builder": lambda: build_weather_target_dataset(
                "kochi", lead_days=1, target="extreme_rainfall"
            ),
            "config": TrainingConfig(
                model_id="weather_extreme_rainfall_kochi_nextday",
                hazard="Flood",
                target_mode="continuous_high",
                validation_start="2015-01-01",
                test_start="2020-01-01",
                event_quantile=0.95,
                candidate_models=(
                    "random_forest",
                    "extra_trees",
                    "logistic_regression",
                    "hist_gradient_boosting",
                ),
                persistence_column="precipitation_sum",
                evidence_tier="baseline",
                intended_use=(
                    "Next-day extreme-rainfall screening at the Kochi reanalysis grid "
                    "point, used only as supplementary flood-forcing evidence."
                ),
                prohibited_use=(
                    "Not a flood-occurrence, inundation, depth, impact, or public-warning "
                    "model. Do not use for evacuation or asset decisions."
                ),
                limitations=(
                    "Kochi grid-point reanalysis is not a station observation or a local flood gauge.",
                    "The 95th-percentile event definition is a research threshold, not an IMD warning threshold.",
                ),
            ),
        },
    ),
    (
        "weather_high_temperature_kochi_nextday",
        {
            "builder": lambda: build_weather_target_dataset(
                "kochi", lead_days=1, target="high_temperature"
            ),
            "config": TrainingConfig(
                model_id="weather_high_temperature_kochi_nextday",
                hazard="Heatwave",
                target_mode="continuous_high",
                validation_start="2015-01-01",
                test_start="2020-01-01",
                event_quantile=0.95,
                candidate_models=(
                    "random_forest",
                    "extra_trees",
                    "logistic_regression",
                    "hist_gradient_boosting",
                ),
                persistence_column="temperature_2m_max",
                evidence_tier="baseline",
                intended_use=(
                    "Next-day high-temperature screening at the Kochi reanalysis grid "
                    "point, used only as supplementary heat evidence."
                ),
                prohibited_use=(
                    "Not an official heatwave declaration or heat-health warning. Not a "
                    "humidity, night-time temperature, or exposure model."
                ),
                limitations=(
                    "Reanalysis grid-point temperature is not a station observation.",
                    "The research threshold is not an IMD heatwave criterion.",
                ),
            ),
        },
    ),
    (
        "weather_drought_onset_kochi_30day",
        {
            "builder": lambda: build_weather_target_dataset(
                "kochi", lead_days=30, target="drought_onset"
            ),
            "config": TrainingConfig(
                model_id="weather_drought_onset_kochi_30day",
                hazard="Drought",
                target_mode="continuous_low",
                validation_start="2015-01-01",
                test_start="2020-01-01",
                event_quantile=0.10,
                candidate_models=(
                    "random_forest",
                    "extra_trees",
                    "logistic_regression",
                    "hist_gradient_boosting",
                ),
                persistence_column="rain_30d_sum",
                evidence_tier="baseline",
                intended_use=(
                    "30-day meteorological rainfall-deficit screening at the Kochi "
                    "reanalysis grid point, used only as supplementary drought context."
                ),
                prohibited_use=(
                    "Not a drought declaration, SPI/SPEI index, agricultural or hydrological "
                    "drought model, or water-supply forecast."
                ),
                limitations=(
                    "A 30-day rainfall deficit is not agricultural or hydrological drought.",
                    "Soil moisture, evaporative demand, storage and demand are absent.",
                ),
            ),
        },
    ),
    (
        "cyclone_rapid_intensification_24h",
        {
            "builder": build_cyclone_intensification_dataset,
            "config": TrainingConfig(
                model_id="cyclone_rapid_intensification_24h",
                hazard="Cyclone",
                target_mode="continuous_high",
                validation_start="2015-01-01",
                test_start="2020-01-01",
                fixed_threshold=30.0,
                candidate_models=(
                    "random_forest",
                    "extra_trees",
                    "logistic_regression",
                    "hist_gradient_boosting",
                ),
                group_column="storm_id",
                persistence_column="wind_chg_24h",
                min_train_rows=500,
                min_validation_rows=100,
                min_test_rows=100,
                min_train_events=10,
                evidence_tier="screening",
                intended_use=(
                    "24-hour rapid-intensification screening from IBTrACS best-track "
                    "history, used only as supplementary cyclone context."
                ),
                prohibited_use=(
                    "Not a track, landfall, intensity, surge, wind, or warning forecast. "
                    "Do not use for evacuation or shelter decisions."
                ),
                limitations=(
                    "Best-track data are post-event reanalysis, not operational forecasts.",
                    "Rapid intensification is rare; held-out event counts are small and uncertainty is wide.",
                    "Agency wind-source changes create inhomogeneity.",
                ),
            ),
        },
    ),
    (
        "earthquake_aftershock_occurrence",
        {
            "builder": build_aftershock_dataset,
            "config": TrainingConfig(
                model_id="earthquake_aftershock_occurrence",
                hazard="Earthquake",
                target_mode="binary",
                label_end_column="target_window_end",
                validation_start="2018-01-01",
                test_start="2022-01-01",
                fixed_threshold=0.5,
                persistence_column="n_m4_prev7d_50km",
                candidate_models=(
                    "random_forest",
                    "extra_trees",
                    "logistic_regression",
                    "hist_gradient_boosting",
                    "gradient_boosting",
                ),
                min_train_rows=100,
                min_validation_rows=50,
                min_test_rows=30,
                min_train_events=10,
                evidence_tier="screening",
                intended_use=(
                    "Aftershock occurrence screening for an already observed M>=5 "
                    "mainshock, used only as supplementary sequence context."
                ),
                prohibited_use=(
                    "Not earthquake prediction, mainshock timing, shaking intensity, "
                    "damage, or warning guidance."
                ),
                limitations=(
                    "The USGS catalogue is regionally clipped and capped at 20,000 events.",
                    "Aftershock labelling depends on catalogue completeness and the chosen distance/time windows.",
                ),
            ),
        },
    ),
    (
        "compound_cyclone_rainfall_interaction",
        {
            "builder": build_compound_cyclone_rainfall_dataset,
            "config": TrainingConfig(
                model_id="compound_cyclone_rainfall_interaction",
                hazard="Compound: cyclone + flood",
                target_mode="continuous_high",
                validation_start="2015-01-01",
                test_start="2020-01-01",
                event_quantile=0.95,
                candidate_models=(
                    "random_forest",
                    "extra_trees",
                    "logistic_regression",
                    "hist_gradient_boosting",
                ),
                evidence_tier="exploratory_association",
                ablation_columns=(
                    "cyclone_near_500",
                    "cyclone_near_300",
                    "cyclone_distance_capped",
                    "cyclone_max_wind_kt",
                    "cyclone_fixes",
                    "cyclone_wind_x_near",
                    "near500_x_prior7",
                    "near500_x_month_sin",
                    "near500_x_month_cos",
                ),
                association_exposure="cyclone_near_500",
                persistence_column="prior_rain_1d",
                intended_use=(
                    "Exploratory concurrent association between cyclone proximity and "
                    "extreme daily rainfall at the Kochi grid point."
                ),
                prohibited_use=(
                    "Not a joint probability, compound forecast, lead-time warning, flood "
                    "depth, or impact estimate. Do not add this output to component indicators."
                ),
                limitations=(
                    "Cyclone position and rainfall are concurrent; there is no forecast lead time.",
                    "Only 128 cyclone-near days and about 20 compound extreme-rain days are available.",
                    "Association is not causation and does not establish a compound impact pathway.",
                ),
            ),
        },
    ),
)


def main() -> int:
    results = []
    errors: dict[str, str] = {}
    skipped: dict[str, str] = {}

    for model_id, spec in MODEL_SPECS:
        print(f"[TRAIN] {model_id}")
        try:
            dataset = spec["builder"]()
            result = train_model(dataset, spec["config"])
        except Exception as exc:  # record the honest blocker and continue
            errors[model_id] = f"{type(exc).__name__}: {exc}"
            print(f"[BLOCKED] {model_id}: {errors[model_id]}")
            continue
        results.append(result)
        print(
            f"[OK] {model_id}: status={result.card['status']}, "
            f"test_events={result.card['test_events']}, "
            f"selected={result.card['selected_model_type']}"
        )

    # Landslide is documented as a readiness-only dataset, not trained.
    try:
        readiness = build_landslide_readiness_dataset()
        skipped["landslide_reported_events_kerala"] = (
            f"Readiness only: {len(readiness.frame)} reported events and no "
            "representative non-event sample; no supervised model is released."
        )
    except Exception as exc:
        skipped["landslide_reported_events_kerala"] = f"{type(exc).__name__}: {exc}"

    # Persist artifacts and cards before registering them.
    from src.ml.persistence import save_model_bundle

    saved_cards = []
    for result in results:
        paths = save_model_bundle(result.config.model_id, result.pipeline, result.card)
        result.card["artifact"].update(paths)
        saved_cards.append(result.card)

    register(
        saved_cards,
        extra={
            "training_script": "scripts/train_shared_ml_models.py",
            "validated_models": 0,
            "interpretation": (
                "All models are research-only. Single temporal holdouts are not "
                "independent validation."
            ),
        },
    )
    regression_cards = []
    regression_errors = {}
    try:
        regression_cards = train_weather_regression_models()
        print(
            "[REGRESSION] "
            + ", ".join(
                f"{card['model_id']}={card['status']}"
                for card in regression_cards
            )
        )
    except Exception as exc:
        regression_errors["weather_regression"] = f"{type(exc).__name__}: {exc}"
        print(f"[REGRESSION BLOCKED] {regression_errors['weather_regression']}")

    coverage = build_coverage_matrix(write=True)

    validation_report = {
        "schema_version": 1,
        "status": "RESEARCH_MODELS_TRAINED_NOT_INDEPENDENTLY_VALIDATED",
        "validated_models": 0,
        "n_trained": len(results),
        "n_regression_trained": len(regression_cards),
        "regression_trained": regression_cards,
        "regression_blocked": regression_errors,
        "n_blocked": len(errors) + len(regression_errors),
        "trained": [
            {
                "model_id": result.card["model_id"],
                "hazard": result.card["hazard"],
                "status": result.card["status"],
                "skill_grade": result.card.get("skill_grade"),
                "status_reason": result.card["status_reason"],
                "evidence_tier": result.card["evidence_tier"],
                "selected_model_type": result.card["selected_model_type"],
                "target_definition": result.card["target_definition"],
                "threshold_source": result.card["threshold_source"],
                "temporal_split": result.card["temporal_split"],
                "train_rows": result.card["final_train_rows"],
                "train_events": result.card["final_train_events"],
                "test_rows": result.card["test_rows"],
                "test_events": result.card["test_events"],
                "metrics": result.card["metrics"],
                "limitations": result.card["limitations"],
            }
            for result in results
        ],
        "blocked": errors,
        "documented_without_training": skipped,
        "coverage": {
            "n_hazards": coverage["n_hazards"],
            "n_hazards_with_ml_evidence": coverage["n_hazards_with_ml_evidence"],
            "n_hazards_without_ml": coverage["n_hazards_without_ml"],
            "hazards_without_ml_evidence": coverage["hazards_without_ml_evidence"],
            "coverage_complete": coverage["coverage_complete"],
        },
        "interpretation": (
            "Metrics are single temporal holdouts. No model is calibrated for "
            "decision use, independently validated, or suitable for warnings."
        ),
    }
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    write_json(VALIDATION_PATH, validation_report)

    print(json.dumps(
        {
            "trained": [result.config.model_id for result in results],
            "regression_trained": [card["model_id"] for card in regression_cards],
            "regression_blocked": regression_errors,
            "blocked": errors,
            "documented_without_training": skipped,
            "coverage": validation_report["coverage"],
        },
        indent=2,
    ))
    return 0 if results else 1


if __name__ == "__main__":
    raise SystemExit(main())

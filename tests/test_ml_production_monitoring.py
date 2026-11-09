import numpy as np
import pytest

from src.ml.production_monitoring import evaluate_production_health, population_stability_index


def args():
    ref = np.linspace(0, 1, 500)
    return dict(reference_features={"rain": ref}, current_features={"rain": ref.copy()},
                latency_ms=[20, 25, 30, 40], data_age_minutes=5,
                max_data_age_minutes=30, out_of_domain_rate=0.01,
                max_out_of_domain_rate=0.05, inference_failure_rate=0.0,
                max_inference_failure_rate=0.01, max_p95_latency_ms=500)


def test_healthy_inputs_do_not_trigger_fallback():
    assert not evaluate_production_health(**args())["fallback_required"]


def test_stale_inputs_trigger_deterministic_fallback():
    values = args()
    values["data_age_minutes"] = 60
    report = evaluate_production_health(**values)
    assert report["action"] == "DETERMINISTIC_SCREENING_ONLY"
    assert report["automated_warning_authorized"] is False


def test_feature_shift_triggers_fallback():
    values = args()
    values["current_features"] = {"rain": np.linspace(10, 20, 500)}
    assert evaluate_production_health(**values)["fallback_required"]


def test_psi_rejects_nan():
    with pytest.raises(ValueError, match="finite"):
        population_stability_index([1, 2, float("nan")], [1, 2, 3])

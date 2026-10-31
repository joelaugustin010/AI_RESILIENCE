"""Tests for independent held-out model evaluation helpers."""
import pytest
from src.independent_model_evaluation import evaluate_classifier, evaluate_regressor

def test_classifier_reports_imbalance_aware_metrics_and_confusion_matrix():
    result = evaluate_classifier([0, 0, 0, 1], [0, 0, 1, 1], labels=[0, 1])
    assert result["n_test"] == 4
    # Class 0 recall is 2/3 and class 1 recall is 1; their mean is 5/6.
    assert result["balanced_accuracy"] == pytest.approx(5 / 6)
    assert result["confusion_matrix"] == [[2, 1], [0, 1]]
    assert result["probability_metrics_available"] is False

def test_binary_classifier_can_report_brier_score():
    result = evaluate_classifier([0, 1, 1], [0, 1, 1], labels=[0, 1], y_probability=[0.1, 0.8, 0.9])
    assert result["brier_score"] == pytest.approx(0.02)
    assert result["probability_metrics_available"] is True

@pytest.mark.parametrize("actual,predicted", [([0, 1], [0]), ([], []), ([[0], [1]], [[0], [1]])])
def test_classifier_rejects_misaligned_or_invalid_arrays(actual, predicted):
    with pytest.raises(ValueError):
        evaluate_classifier(actual, predicted)

def test_classifier_rejects_invalid_probabilities():
    with pytest.raises(ValueError):
        evaluate_classifier([0, 1], [0, 1], labels=[0, 1], y_probability=[0.2, 1.2])

def test_regression_reports_mae_and_rmse():
    result = evaluate_regressor([1, 2, 3], [1, 3, 3])
    assert result["mae"] == pytest.approx(1 / 3)
    assert result["rmse"] == pytest.approx((1 / 3) ** 0.5)

def test_regression_rejects_single_row():
    with pytest.raises(ValueError):
        evaluate_regressor([1], [1])

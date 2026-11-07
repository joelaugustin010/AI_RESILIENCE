from src.ml.submission_summary import rank_classifier_cards, rank_regression_cards, regression_baseline_label


def test_regressions_rank_by_finite_mae_skill():
    cards = [
        {"model_id": "rain", "task_type": "regression", "metrics": {"mae_skill_over_persistence": 0.09}},
        {"model_id": "cyclone", "task_type": "regression", "metrics": {"mae_skill_over_persistence": 0.28}},
        {"model_id": "bad", "task_type": "regression", "metrics": {"mae_skill_over_persistence": float("nan")}},
        {"model_id": "classifier", "task_type": "classification", "metrics": {"mae_skill_over_persistence": 0.99}},
    ]
    assert [card["model_id"] for card in rank_regression_cards(cards)] == ["cyclone", "rain"]


def test_regression_ranking_ignores_missing_or_boolean_skill():
    cards = [
        {"model_id": "missing", "task_type": "regression", "metrics": {}},
        {"model_id": "boolean", "task_type": "regression", "metrics": {"mae_skill_over_persistence": True}},
    ]
    assert rank_regression_cards(cards) == []


def test_classifier_rank_uses_absolute_f1_gain_over_persistence():
    cards = [
        {"model_id": "rain", "task_type": "classification", "metrics": {"f1": 0.425, "persistence_baseline": {"f1": 0.425}}},
        {"model_id": "heat", "task_type": "classification", "metrics": {"f1": 0.743, "persistence_baseline": {"f1": 0.692}}},
        {"model_id": "cyclone", "task_type": "classification", "metrics": {"f1": 0.21, "persistence_baseline": {"f1": 0.24}}},
    ]
    ranked = rank_classifier_cards(cards)
    assert [card["model_id"] for card in ranked] == ["heat", "rain", "cyclone"]


def test_classifier_ranking_ignores_missing_and_nonfinite_metrics():
    cards = [
        {"model_id": "missing", "task_type": "classification", "metrics": {"f1": 0.5}},
        {"model_id": "nan", "task_type": "classification", "metrics": {"f1": float("nan"), "persistence_baseline": {"f1": 0.2}}},
        {"model_id": "regression", "task_type": "regression", "metrics": {"f1": 0.9, "persistence_baseline": {"f1": 0.1}}},
    ]
    assert rank_classifier_cards(cards) == []


def test_regression_baseline_label_uses_recorded_comparator():
    assert regression_baseline_label({"metrics": {"persistence_baseline": {"type": "constant_no_change"}}}) == "No-change baseline"
    assert regression_baseline_label({"metrics": {"persistence_baseline": {"type": "persistence"}}}) == "Persistence baseline"
    assert regression_baseline_label({"metrics": {}}) == "Recorded baseline"

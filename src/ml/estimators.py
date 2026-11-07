"""Deployment-compatible estimator factory.

Only scikit-learn estimators already covered by ``requirements.txt`` are used.
No optional gradient-boosting package (XGBoost/LightGBM) is imported, so a
model card produced here can be loaded by the deployed application.
"""

from __future__ import annotations

from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

SUPPORTED_MODELS: tuple[str, ...] = (
    "random_forest",
    "extra_trees",
    "hist_gradient_boosting",
    "logistic_regression",
    "gradient_boosting",
)

# A small, deliberately conservative default.  Training scripts may widen it,
# but every candidate must remain a scikit-learn estimator.
DEFAULT_CANDIDATES: tuple[str, ...] = (
    "random_forest",
    "extra_trees",
    "logistic_regression",
)


def build_estimator(
    model_type: str,
    *,
    random_state: int = 42,
    n_jobs: int = -1,
    class_weight: str | None = "balanced",
) -> Pipeline:
    """Build an imputation + classifier pipeline for a supported model type."""
    if model_type == "random_forest":
        classifier = RandomForestClassifier(
            n_estimators=300,
            min_samples_leaf=10,
            max_features="sqrt",
            class_weight=class_weight,
            random_state=random_state,
            n_jobs=n_jobs,
        )
        steps = [("imputer", SimpleImputer(strategy="median")), ("classifier", classifier)]
    elif model_type == "extra_trees":
        classifier = ExtraTreesClassifier(
            n_estimators=300,
            min_samples_leaf=8,
            max_features="sqrt",
            class_weight=class_weight,
            random_state=random_state,
            n_jobs=n_jobs,
        )
        steps = [("imputer", SimpleImputer(strategy="median")), ("classifier", classifier)]
    elif model_type == "hist_gradient_boosting":
        classifier = HistGradientBoostingClassifier(
            learning_rate=0.06,
            max_iter=250,
            max_leaf_nodes=31,
            min_samples_leaf=20,
            l2_regularization=1.0,
            random_state=random_state,
        )
        steps = [("imputer", SimpleImputer(strategy="median")), ("classifier", classifier)]
    elif model_type == "logistic_regression":
        classifier = LogisticRegression(
            max_iter=2000,
            class_weight=class_weight,
            random_state=random_state,
            solver="lbfgs",
        )
        steps = [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("classifier", classifier),
        ]
    elif model_type == "gradient_boosting":
        classifier = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=3,
            min_samples_leaf=20,
            subsample=0.8,
            random_state=random_state,
        )
        steps = [("imputer", SimpleImputer(strategy="median")), ("classifier", classifier)]
    else:
        raise ValueError(
            f"Unsupported estimator {model_type!r}; choose from {sorted(SUPPORTED_MODELS)}."
        )
    return Pipeline(steps)


def positive_class_probability(model: Pipeline, features) -> "object":
    """Return the probability of class 1, with an explicit failure if absent."""
    if not hasattr(model, "predict_proba"):
        raise TypeError("The fitted estimator does not expose predict_proba.")
    classifier = model.steps[-1][1]
    classes = list(classifier.classes_)
    if 1 not in classes:
        raise ValueError("The fitted estimator has no positive class (1).")
    return model.predict_proba(features)[:, classes.index(1)]


from sklearn.ensemble import ExtraTreesRegressor, HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge

REGRESSION_CANDIDATES = (
    "random_forest_regressor", "extra_trees_regressor",
    "hist_gradient_boosting_regressor", "ridge_regressor",
)


def build_regressor(model_type: str, *, random_state: int = 42, n_jobs: int = -1) -> Pipeline:
    """Build a shared preprocessing + continuous regression pipeline."""
    if model_type == "random_forest_regressor":
        estimator = RandomForestRegressor(n_estimators=300, min_samples_leaf=8, max_features=1.0, random_state=random_state, n_jobs=n_jobs)
        steps = [("imputer", SimpleImputer(strategy="median")), ("regressor", estimator)]
    elif model_type == "extra_trees_regressor":
        estimator = ExtraTreesRegressor(n_estimators=300, min_samples_leaf=8, max_features=1.0, random_state=random_state, n_jobs=n_jobs)
        steps = [("imputer", SimpleImputer(strategy="median")), ("regressor", estimator)]
    elif model_type == "hist_gradient_boosting_regressor":
        estimator = HistGradientBoostingRegressor(learning_rate=0.05, max_iter=250, max_leaf_nodes=31, min_samples_leaf=20, l2_regularization=1.0, random_state=random_state)
        steps = [("imputer", SimpleImputer(strategy="median")), ("regressor", estimator)]
    elif model_type == "ridge_regressor":
        estimator = Ridge(alpha=10.0)
        steps = [("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("regressor", estimator)]
    else:
        raise ValueError(f"Unsupported regression estimator {model_type!r}; choose from {sorted(REGRESSION_CANDIDATES)}.")
    return Pipeline(steps)

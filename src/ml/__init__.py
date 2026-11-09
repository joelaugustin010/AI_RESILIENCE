"""Shared, leakage-aware machine-learning infrastructure for AI RESILIENCE.

The package deliberately separates data construction, feature engineering,
training, evaluation, persistence and inference.  A model is only reported as
usable when an untouched temporal holdout supports that statement; otherwise
the model card records the weaker status explicitly.
"""

from __future__ import annotations

from src.ml.coverage import build_coverage_matrix
from src.ml.registry import list_model_cards, load_model_card
from src.ml.service import ml_evidence_for

__all__ = [
    "build_coverage_matrix",
    "list_model_cards",
    "load_model_card",
    "ml_evidence_for",
]

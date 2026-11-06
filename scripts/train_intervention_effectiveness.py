"""Train action-effect models from a verified observational intervention dataset.

No built-in or synthetic data is generated. Supply a real episode-level CSV and
a provenance JSON sidecar. Each action is evaluated against contemporaneous
no-action episodes for the same hazard.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from src.intervention_effectiveness import train_intervention_model


PROVENANCE_FIELDS = (
    "source_title", "source_owner", "source_url_or_archive_id",
    "collection_period", "outcome_definition", "outcome_unit", "outcome_direction",
    "treatment_definition", "geographic_scope", "known_biases", "permission_or_access_basis",
    "pre_treatment_features",
)


def validate_training_provenance(provenance):
    """Validate provenance metadata before reading or fitting supplied data."""
    if not isinstance(provenance, dict):
        raise ValueError("Provenance sidecar must contain a JSON object.")
    missing = [
        key for key in PROVENANCE_FIELDS
        if key != "pre_treatment_features"
        and (not isinstance(provenance.get(key), str) or not provenance[key].strip())
    ]
    if missing:
        raise ValueError(f"Provenance sidecar is missing non-empty text fields: {missing}.")
    if provenance.get("outcome_direction") != "lower_is_better":
        raise ValueError("outcome_direction must be lower_is_better; transform and document higher-is-better outcomes before training.")
    if provenance.get("synthetic") is True:
        raise ValueError("Synthetic data cannot train or validate intervention-effect models.")
    features = provenance.get("pre_treatment_features")
    if (
        not isinstance(features, list)
        or not features
        or any(not isinstance(item, str) or not item.strip() for item in features)
        or len(set(features)) != len(features)
    ):
        raise ValueError("pre_treatment_features must be a non-empty list of unique, non-empty column names.")
    return provenance

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="Real intervention-episode CSV.")
    parser.add_argument("--provenance", required=True, help="JSON provenance sidecar.")
    parser.add_argument("--output", default="reports/intervention_effectiveness_registry.json")
    parser.add_argument("--artifacts", default="models/intervention_effectiveness")
    parser.add_argument("--test-start", default="2022-01-01")
    args = parser.parse_args()

    data_path, provenance_path = Path(args.data), Path(args.provenance)
    if not data_path.is_file() or not provenance_path.is_file():
        raise SystemExit("BLOCKED: dataset and provenance sidecar must both exist.")
    provenance = validate_training_provenance(
        json.loads(provenance_path.read_text(encoding="utf-8"))
    )

    frame = pd.read_csv(data_path)
    from src.intervention_effectiveness import validate_intervention_frame
    validate_intervention_frame(frame, feature_columns=provenance["pre_treatment_features"])
    cards, trained = [], []
    output_dir = Path(args.artifacts)
    output_dir.mkdir(parents=True, exist_ok=True)
    for hazard, action_id in sorted(
        {(str(h), str(a)) for h, a in zip(frame["hazard"], frame["action_id"])}
    ):
        try:
            model = train_intervention_model(
                frame, action_id=action_id, hazard=hazard,
                feature_columns=provenance["pre_treatment_features"],
                test_start=args.test_start,
                outcome_unit=str(provenance["outcome_unit"]),
            )
            card = {**model.card, "data_provenance": provenance}
            if model.card.get("eligible_for_ranking"):
                safe_hazard = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in hazard.lower())
                safe_action = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in action_id)
                artifact_path = output_dir / f"{safe_hazard}__{safe_action}.joblib"
                joblib.dump({
                    "preprocessor": model.preprocessor,
                    "effect_model": model.effect_model,
                    "support_profile": model.support_profile,
                }, artifact_path)
                card["artifact_path"] = str(artifact_path)
                trained.append(str(artifact_path))
            cards.append(card)
        except Exception as exc:
            cards.append({
                "hazard": hazard,
                "action_id": action_id,
                "status": "TRAINING_BLOCKED",
                "eligible_for_ranking": False,
                "status_reason": f"{type(exc).__name__}: {exc}",
                "data_provenance": provenance,
            })

    registry = {
        "schema_version": "intervention-effectiveness-registry/1.0.0",
        "status": "OBSERVATIONAL_RESEARCH_ONLY",
        "validated_models": 0,
        "data_path": str(data_path),
        "data_provenance": provenance,
        "models": cards,
        "interpretation": (
            "Eligible cards are preliminary doubly-robust observational estimates. "
            "No model is independently validated or approved for operational decisions."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(registry, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({
        "registry": str(output),
        "action_models": len(cards),
        "eligible_artifacts": len(trained),
        "blocked_or_no_signal": len(cards) - len(trained),
        "validated_models": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

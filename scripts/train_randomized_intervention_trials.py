"""Train pairwise ITT/CATE models from an authorized cluster-randomized trial.

This command accepts only a real, documented, authorized dataset. It never
creates sample data. The CSV must already be prepared at one row per
household/episode, with the assignment cluster and randomized arm verified
against the study protocol.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import pandas as pd

from src.randomized_intervention_trials import (
    fit_randomized_contrast, validate_trial_frame,
)


PROVENANCE_REQUIRED = (
    "source_title", "source_owner", "source_url_or_archive_id",
    "study_protocol_reference", "collection_period", "geographic_scope",
    "randomization_unit", "assignment_definition", "outcome_definition",
    "outcome_unit", "known_biases", "permission_or_access_basis",
    "pre_randomization_features", "assignment_probabilities",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, help="Authorized household/episode CSV.")
    parser.add_argument("--provenance", required=True, help="Study and data provenance JSON.")
    parser.add_argument("--output", default="reports/randomized_intervention_trial_registry.json")
    parser.add_argument("--artifacts", default="models/randomized_intervention_trials")
    parser.add_argument("--reference-arm", required=True)
    parser.add_argument("--treatment-arms", required=True,
                        help="Comma-separated randomized arm names to compare with reference.")
    parser.add_argument("--min-clusters-per-arm", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    data_path, provenance_path = Path(args.data), Path(args.provenance)
    if not data_path.is_file() or not provenance_path.is_file():
        raise SystemExit("BLOCKED: authorized dataset and provenance sidecar are both required.")
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    missing = [key for key in PROVENANCE_REQUIRED if not provenance.get(key)]
    if missing:
        raise SystemExit(f"BLOCKED: provenance is missing {missing}.")
    if provenance.get("synthetic") is True:
        raise SystemExit("BLOCKED: synthetic data cannot train this model.")
    if provenance.get("permission_or_access_basis", "").strip().lower() in {
        "unknown", "none", "not obtained", "pending"
    }:
        raise SystemExit("BLOCKED: documented permission/access basis is required.")
    features = provenance["pre_randomization_features"]
    probabilities = provenance["assignment_probabilities"]
    if not isinstance(features, list) or not features:
        raise SystemExit("BLOCKED: pre_randomization_features must be a non-empty list.")
    if not isinstance(probabilities, dict) or not probabilities:
        raise SystemExit("BLOCKED: assignment_probabilities must be a complete arm-to-probability map.")

    frame = pd.read_csv(data_path)
    validate_trial_frame(frame, features)
    observed_arms = set(frame["assigned_arm"].astype(str))
    if observed_arms != set(probabilities):
        raise SystemExit(
            "BLOCKED: observed arm labels must exactly match the documented "
            f"assignment-probability keys; observed={sorted(observed_arms)}, "
            f"documented={sorted(probabilities)}."
        )
    if args.reference_arm not in observed_arms:
        raise SystemExit("BLOCKED: reference arm is not present in the dataset.")
    treatment_arms = [x.strip() for x in args.treatment_arms.split(",") if x.strip()]
    if not treatment_arms or args.reference_arm in treatment_arms:
        raise SystemExit("BLOCKED: provide one or more treatment arms distinct from the reference.")
    unknown = sorted(set(treatment_arms) - observed_arms)
    if unknown:
        raise SystemExit(f"BLOCKED: unknown treatment arms: {unknown}.")

    artifact_dir = Path(args.artifacts)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    cards = []
    for index, arm in enumerate(treatment_arms):
        model = fit_randomized_contrast(
            frame,
            treatment_arm=arm,
            reference_arm=args.reference_arm,
            assignment_probabilities=probabilities,
            feature_columns=features,
            outcome_unit=str(provenance["outcome_unit"]),
            min_clusters_per_arm=args.min_clusters_per_arm,
            seed=args.seed + index,
        )
        card = {**model.report, "data_provenance": provenance}
        if model.report.get("eligible_for_research_ranking"):
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in arm)
            path = artifact_dir / f"{safe_name}__vs__reference.joblib"
            joblib.dump({
                "preprocessor": model.preprocessor,
                "cate_model": model.cate_model,
                "feature_columns": model.feature_columns,
                "treatment_arm": arm,
                "reference_arm": args.reference_arm,
            }, path)
            card["artifact_path"] = str(path)
        cards.append(card)

    registry = {
        "schema_version": "randomized-intervention-trial-registry/1.0.0",
        "status": "RANDOMIZED_TRIAL_RESEARCH_ONLY",
        "validated_models": 0,
        "data_provenance": provenance,
        "models": cards,
        "warning": (
            "These are preliminary pairwise ITT research estimates. They are not "
            "effects of treatment receipt, do not generalize to unrelated actions, "
            "and are not validated for operational decisions."
        ),
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(registry, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({
        "registry": str(output),
        "pairwise_contrasts": len(cards),
        "eligible_research_models": sum(bool(c.get("eligible_for_research_ranking")) for c in cards),
        "validated_models": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

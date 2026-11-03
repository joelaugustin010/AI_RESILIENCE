"""Explicit uncertainty categories and downstream guardrails for assessments."""

from __future__ import annotations

from typing import Any

import pandas as pd


UNCERTAINTY_TYPES = (
    "Measurement uncertainty",
    "Data-quality uncertainty",
    "Spatial uncertainty",
    "Temporal uncertainty",
    "Model uncertainty",
    "Scenario uncertainty",
)


def build_uncertainty_register(
    inputs: dict[str, Any],
    evidence: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Describe uncertainty and its consequence without inventing confidence values."""
    measurements = [
        label
        for field, label in (
            ("rainfall_mm", "rainfall"),
            ("river_level_m", "river level"),
            ("wind_speed_kmh", "wind speed"),
            ("temperature_c", "temperature"),
        )
        if inputs.get(field) is not None
    ]
    measurement_status = "Unresolved" if measurements else "Not assessed"
    measurement_evidence = (
        f"User-entered {', '.join(measurements)} value(s); instruments, calibration, units, and source quality are not checked."
        if measurements
        else "No physical measurements supplied."
    )

    data_status = "Unresolved"
    data_evidence = "No evidence register supplied."
    if evidence is not None and "Evidence state" in evidence.columns:
        states = evidence["Evidence state"].astype(str)
        concerns = states.loc[~states.eq("Verified")].value_counts().to_dict()
        data_evidence = (
            f"{sum(concerns.values())} evidence item(s) are not in the Verified state: {concerns}."
            if concerns
            else "All listed items are marked Verified; fitness for this specific assessment still requires review."
        )
        if states.eq("Conflicting").any():
            data_evidence += " Conflicting records remain unresolved and are not averaged or silently selected."

    raw_assets = inputs.get("assets", [])
    nominated_assets = (
        [asset for asset in raw_assets if isinstance(asset, str)]
        if isinstance(raw_assets, (list, tuple))
        else []
    )
    spatial_status = "Unresolved" if nominated_assets else "Not assessed"
    spatial_evidence = (
        f"Nominated assets/services: {', '.join(nominated_assets)}; no validated asset coordinates, compatible hazard footprint, or spatial join is available."
        if nominated_assets
        else "No assets were nominated and no exposure geometry was supplied."
    )

    source_notes = str(inputs.get("source_and_time", "")).strip()
    temporal_status = "Unresolved"
    temporal_evidence = (
        f"User source/time notes supplied but not parsed or verified: {source_notes}"
        if source_notes
        else "Observation/forecast timestamp, timezone, averaging period, and synchronization are not established."
    )

    scenario_class = str(inputs.get("input_classification", "Unknown / unverified"))
    scenario_status = "Unresolved"
    scenario_evidence = (
        f"Input classification: {scenario_class}; the workflow cannot authenticate the event, forecast, sequence, or assumed service condition."
    )

    rows = [
        {
            "Uncertainty type": "Measurement uncertainty",
            "Status": measurement_status,
            "Evidence / source of uncertainty": measurement_evidence,
            "Downstream consequence": "Do not interpret the entered value as verified intensity or compare it with a warning threshold.",
            "Required resolution": "Record source, instrument/method, units, location, calibration/quality flags, and measurement interval.",
        },
        {
            "Uncertainty type": "Data-quality uncertainty",
            "Status": data_status,
            "Evidence / source of uncertainty": data_evidence,
            "Downstream consequence": "Conflicts and missing records remain explicit; they are not converted to zero hazard or averaged away.",
            "Required resolution": "Review source provenance, duplicates, missingness, quality controls, and source-version hashes.",
        },
        {
            "Uncertainty type": "Spatial uncertainty",
            "Status": spatial_status,
            "Evidence / source of uncertainty": spatial_evidence,
            "Downstream consequence": "No statement that an asset is inside or outside a hazard area is supported.",
            "Required resolution": "Verify asset and hazard geometries, CRS, resolution, positional accuracy, and boundary coverage.",
        },
        {
            "Uncertainty type": "Temporal uncertainty",
            "Status": temporal_status,
            "Evidence / source of uncertainty": temporal_evidence,
            "Downstream consequence": "Simultaneity, event order, duration, and observation-to-hazard alignment are unknown.",
            "Required resolution": "Use a common documented time basis, timezone, sampling interval, and event window.",
        },
        {
            "Uncertainty type": "Model uncertainty",
            "Status": "Not assessed",
            "Evidence / source of uncertainty": "No numerical disaster-risk model is applied in this workflow.",
            "Downstream consequence": "No model output, probability, confidence interval, or risk class is available.",
            "Required resolution": "Specify a validated target, baseline, model assumptions, calibration, and out-of-sample evaluation before prediction.",
        },
        {
            "Uncertainty type": "Scenario uncertainty",
            "Status": scenario_status,
            "Evidence / source of uncertainty": scenario_evidence,
            "Downstream consequence": "Hypothetical combinations remain planning cases; they do not establish that hazards occurred or interact.",
            "Required resolution": "Confirm the event definition, sequence, dependency evidence, and official scenario inputs.",
        },
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "Uncertainty type",
            "Status",
            "Evidence / source of uncertainty",
            "Downstream consequence",
            "Required resolution",
        ],
    )

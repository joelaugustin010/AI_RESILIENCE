"""Discover matched Geul baseline/intervention raster slices in the ZIP archive.

This is a schema and sample-size audit only. It does not extract the archive,
fit a model, or establish independent event coverage.
"""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

SCENARIOS = {
    "baseline": "baseline_blokbui",
    "retention_ponds": "waterbuffers_blokbui",
    "reforestation": "reforestation_blokbui",
    "grassland_conversion": "grassland_conversion_blokbui",
    "dryproofing": "dry_proofing_blokbui",
    "wetproofing": "wet_proofing_blokbui",
}
RASTER_NAME = re.compile(r"^hmax\s*RP\s*([0-9]+(?:\.[0-9]+)?)\.tif$", re.I)


def discover_slices(archive_path: str | Path) -> dict[str, Any]:
    archive = Path(archive_path)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    scenario_slices: dict[str, set[tuple[str, str, str]]] = {
        label: set() for label in SCENARIOS
    }
    with zipfile.ZipFile(archive) as zf:
        for member in zf.namelist():
            if member.endswith("/"):
                continue
            parts = member.split("/")
            for label, folder in SCENARIOS.items():
                marker = f"final_results/{folder}/SFINCS/"
                try:
                    marker_index = member.index(marker) + len(marker)
                except ValueError:
                    continue
                suffix = member[marker_index:]
                suffix_parts = suffix.split("/")
                if len(suffix_parts) < 4:
                    continue
                model_id = suffix_parts[0]
                if suffix_parts[1] != "simulations":
                    continue
                event_id = suffix_parts[2]
                match = RASTER_NAME.match(suffix_parts[-1])
                if match:
                    scenario_slices[label].add(
                        (model_id, event_id, match.group(1))
                    )
                break

    baseline = scenario_slices["baseline"]
    comparisons = {}
    for label, slices in scenario_slices.items():
        matched = sorted(baseline & slices) if label != "baseline" else sorted(baseline)
        comparisons[label] = {
            "available_slices": len(slices),
            "matched_with_baseline": len(matched),
            "matched_model_ids": sorted({item[0] for item in matched}),
            "matched_event_ids": sorted({item[1] for item in matched}),
            "matched_return_periods": sorted({item[2] for item in matched}),
            "matched_slices": [
                {"model_id": model, "event_id": event, "return_period": rp}
                for model, event, rp in matched
            ],
        }

    all_matched_events = sorted({
        item[1]
        for label, slices in scenario_slices.items()
        if label != "baseline"
        for item in (baseline & slices)
    })
    return {
        "schema_version": "geul-simulation-slice-discovery/1.0.0",
        "archive": archive.name,
        "scenario_outputs": comparisons,
        "baseline_slice_count": len(baseline),
        "independent_event_ids_with_any_matched_intervention": all_matched_events,
        "independent_event_count": len(all_matched_events),
        "model_training_performed": False,
        "validation_readiness": (
            "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_EVENT_HOLDOUT"
            if len(all_matched_events) < 3
            else "CANDIDATE_FOR_SPATIAL_AND_EVENT_HOLDOUT_DESIGN_REVIEW"
        ),
        "warning": (
            "A matched raster slice is not necessarily an independent storm. "
            "Distinct return periods or forcing labels for one event must not "
            "be counted as independent events."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--archive",
        default="data/external/geul_intervention/final_results.zip",
    )
    parser.add_argument(
        "--output",
        default="reports/geul_simulation_slice_discovery.json",
    )
    args = parser.parse_args()
    report = discover_slices(args.archive)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({
        "report": str(output),
        "baseline_slices": report["baseline_slice_count"],
        "independent_event_count": report["independent_event_count"],
        "validation_readiness": report["validation_readiness"],
        "model_training_performed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

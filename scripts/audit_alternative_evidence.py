"""Prepare carefully labelled alternative-evidence research inputs.

Examples:
  python scripts/audit_alternative_evidence.py flood-geojson --input map.geojson --output-report reports/flood_map_audit.json
  python scripts/audit_alternative_evidence.py landslide-pseudo-absence --positives events.csv --background eligible_background.csv --output-csv research/landslide_candidates.csv --output-report reports/landslide_sampling_audit.json

This script never downloads datasets or converts pseudo-absence into verified
non-event labels. Input provenance and licence must be checked by the operator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.evidence_alternatives import (
    assign_spatial_block_splits,
    audit_satellite_flood_geojson,
    generate_pseudo_absence_samples,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def audit_flood(args: argparse.Namespace) -> int:
    source = Path(args.input)
    payload = json.loads(source.read_text(encoding="utf-8"))
    result = audit_satellite_flood_geojson(payload)
    result.update({
        "input_file": str(source),
        "input_sha256": sha256(source),
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    write_json(Path(args.output_report), result)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "OBSERVED_SATELLITE_EXTENT_ONLY_NOT_DEPTH_OR_FLOOD_FORECAST" else 2


def prepare_landslide(args: argparse.Namespace) -> int:
    positives_path = Path(args.positives)
    background_path = Path(args.background)
    positives = pd.read_csv(positives_path)
    background = pd.read_csv(background_path)
    pseudo = generate_pseudo_absence_samples(
        positives,
        background,
        min_distance_km=args.min_distance_km,
        sample_size=args.sample_size,
        random_state=args.seed,
    )
    positive_rows = positives.copy()
    positive_rows["label"] = 1
    positive_rows["label_type"] = "MAPPED_INVENTORY_EVENT"
    positive_rows["nearest_mapped_positive_km"] = 0.0
    positive_rows["pseudo_absence_buffer_km"] = args.min_distance_km
    positive_rows["sampling_seed"] = args.seed
    combined = pd.concat([positive_rows, pseudo], ignore_index=True, sort=False)
    combined = assign_spatial_block_splits(
        combined,
        block_size_km=args.block_size_km,
        random_state=args.seed,
    )
    output = Path(args.output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)
    report = {
        "schema_version": "landslide-pseudo-absence-preparation/1.0.0",
        "status": "RESEARCH_CANDIDATES_ONLY_NOT_OPERATIONAL_MODEL_DATA",
        "positive_rows": int(len(positive_rows)),
        "pseudo_absence_rows": int(len(pseudo)),
        "rows_by_split": combined["spatial_split"].value_counts().to_dict(),
        "blocks_by_split": combined.groupby("spatial_split")["spatial_block_id"].nunique().to_dict(),
        "label_types": combined["label_type"].value_counts().to_dict(),
        "min_distance_km": args.min_distance_km,
        "block_size_km": args.block_size_km,
        "random_seed": args.seed,
        "positive_file": str(positives_path),
        "positive_sha256": sha256(positives_path),
        "background_file": str(background_path),
        "background_sha256": sha256(background_path),
        "output_file": str(output),
        "output_sha256": sha256(output),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "Pseudo-absence rows are not verified true negatives.",
            "Background candidates must come from a documented eligible/surveyed study domain.",
            "Inventory reporting bias, positional uncertainty and mapping effort remain.",
            "Spatial blocks reduce spatial leakage but do not replace independent event and region validation.",
            "No model is trained and no operational landslide probability is produced.",
        ],
    }
    report_path = Path(args.output_report)
    write_json(report_path, report)
    print(json.dumps(report, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    flood = sub.add_parser("flood-geojson", help="Audit a satellite flood-extent GeoJSON file.")
    flood.add_argument("--input", required=True)
    flood.add_argument("--output-report", required=True)
    flood.set_defaults(run=audit_flood)

    landslide = sub.add_parser("landslide-pseudo-absence", help="Build spatially blocked research candidates.")
    landslide.add_argument("--positives", required=True, help="CSV of mapped landslide inventory points.")
    landslide.add_argument("--background", required=True, help="CSV of eligible background candidate points.")
    landslide.add_argument("--output-csv", required=True)
    landslide.add_argument("--output-report", required=True)
    landslide.add_argument("--min-distance-km", type=float, default=1.0)
    landslide.add_argument("--sample-size", type=int, default=None)
    landslide.add_argument("--block-size-km", type=float, default=10.0)
    landslide.add_argument("--seed", type=int, default=42)
    landslide.set_defaults(run=prepare_landslide)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.run(args)


if __name__ == "__main__":
    raise SystemExit(main())

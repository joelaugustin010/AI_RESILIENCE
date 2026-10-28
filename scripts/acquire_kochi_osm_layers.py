"""Acquire bounded, community-mapped OSM context layers for Kochi."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.kochi_osm import OVERPASS_ENDPOINTS, acquire_layers


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Acquire OpenStreetMap road, transit, waterway, healthcare, emergency, "
            "industrial, and air-monitoring context for the Kochi map. All output is "
            "marked PROVISIONAL and uses ODbL attribution/share-alike terms."
        )
    )
    parser.add_argument(
        "--endpoint",
        action="append",
        help="Overpass API endpoint; repeat to provide ordered fallback endpoints.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data" / "raw" / "openstreetmap",
        help="Directory for timestamped raw Overpass JSON and provenance sidecars.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=ROOT / "data" / "processed",
        help="Directory where validated GeoJSON layers are written.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=2,
        help="Retries per endpoint for temporary capacity or network failures.",
    )
    args = parser.parse_args()
    if args.retries < 1:
        parser.error("--retries must be at least 1.")

    result = acquire_layers(
        args.raw_dir,
        args.processed_dir,
        endpoints=tuple(args.endpoint) if args.endpoint else OVERPASS_ENDPOINTS,
        retries_per_endpoint=args.retries,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())

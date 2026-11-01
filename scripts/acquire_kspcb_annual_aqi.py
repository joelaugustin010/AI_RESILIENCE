"""Acquire public KSPCB year-labeled annual AQI summaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.air_quality_sources import acquire_kspcb_annual_aqi, rebuild_kspcb_annual_aqi_from_raw


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("years", nargs="*", type=int, default=[2023, 2024, 2025, 2026])
    parser.add_argument("--rebuild-only", action="store_true", help="Reprocess preserved raw downloads without network access.")
    arguments = parser.parse_args()
    register = json.loads(
        (ROOT / "data" / "reference" / "air_quality_acquisition.json").read_text(encoding="utf-8")
    )
    raw_directory = ROOT / "data" / "raw" / "air_quality"
    processed_directory = ROOT / "data" / "processed" / "air_quality"
    if arguments.rebuild_only:
        rows, path = rebuild_kspcb_annual_aqi_from_raw(
            raw_directory, processed_directory, register["kspcb_namp_ernakulam_stations"]
        )
    else:
        rows, path = acquire_kspcb_annual_aqi(
            arguments.years,
            register["kspcb_namp_ernakulam_stations"],
            raw_directory,
            processed_directory,
        )
    print(f"Saved {len(rows)} validated statewide annual AQI rows to {path}")
    print(f"Exact reference station matches: {rows['reference_station'].notna().sum()}")


if __name__ == "__main__":
    main()

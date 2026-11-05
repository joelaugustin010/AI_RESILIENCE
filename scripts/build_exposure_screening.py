"""Build the JRC RP100 modelled flood-depth screening report.

Usage:
    python scripts/build_exposure_screening.py

The script reads the pinned JRC depth tiles and the provisional OpenStreetMap
asset layers, writes ``reports/jrc_rp100_osm_exposure_screening.json``, and
prints a short summary. It does not modify source data and does not produce an
operational exposure count.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "jrc_rp100_osm_exposure_screening.json"
METADATA_PATH = (
    ROOT / "data" / "processed" / "spatial_layers" / "jrc_glofas_rp100_kochi_preview.metadata.json"
)
TILE_PATHS = (
    ROOT / "data" / "raw" / "jrc_glofas_rp100_ID185_N20_E70_depth.tif",
    ROOT / "data" / "raw" / "jrc_glofas_rp100_ID186_N10_E70_depth.tif",
)
WATER_TILE_PATHS = (
    ROOT / "data" / "raw" / "ID185_N20_E70_permanent_water.tif",
    ROOT / "data" / "raw" / "ID186_N10_E70_permanent_water.tif",
)
ASSETS_ROOT = ROOT / "data" / "processed" / "spatial_layers"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from src.exposure_assessment import build_report

    metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    bounds = metadata["processing"]["bounds_epsg4326"]
    missing = [str(path) for path in TILE_PATHS if not path.is_file()]
    if missing:
        print("Missing JRC source tiles:", *missing, sep="\n  ")
        return 1
    missing_water = [str(path) for path in WATER_TILE_PATHS if not path.is_file()]
    if missing_water:
        print("Missing JRC permanent-water tiles:", *missing_water, sep="\n  ")
        return 1
    report = build_report(ASSETS_ROOT, TILE_PATHS, bounds, WATER_TILE_PATHS)
    report["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    report["metadata_file"] = str(METADATA_PATH.relative_to(ROOT)).replace("\\", "/")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    aggregate = report["aggregate"]
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    print(
        f"Assets screened: {aggregate['features_total']:,}; "
        f"in coverage: {aggregate['features_sampled_in_coverage']:,}; "
        f"positive modelled depth: {aggregate['positive_modelled_depth']:,}"
    )
    extent = report["extent"]
    print(
        "Extent: "
        f"{extent['positive_depth_cells']:,} positive cells "
        f"({extent['positive_depth_area_km2']} km²) within the display rectangle"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

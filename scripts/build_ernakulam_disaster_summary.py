"""Regenerate the four-hazard Ernakulam evidence summary."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    sys.path.insert(0, str(ROOT))
    from src.ernakulam_disaster_dashboard import (
        build_assessment_cards,
        load_assessment_data,
        location_options,
        load_location_registry,
    )

    registry = load_location_registry()
    options = location_options(registry)
    assessment_data = load_assessment_data()
    assessments = build_assessment_cards(options[0], options, assessment_data)
    summary = {
        "schema_version": 3,
        "district": "Ernakulam",
        "state": "Kerala",
        "location_count": len(options),
        "local_body_counts": {
            "municipalities": len(registry["municipalities"]),
            "corporations": len(registry["corporations"]),
            "grama_panchayats": len(registry["grama_panchayats"]),
        },
        "location_register_vintages": registry["register_vintages"],
        "data_coverage": {
            "cwc_rainfall": assessment_data["rainfall"],
            "cyclone_tracks": assessment_data["cyclone_tracks"],
            "landslide_catalog_entries": len(
                assessment_data["landslide_reports"]
            ),
        },
        "hazards": assessments,
    }
    output = ROOT / "data" / "processed" / "ernakulam_disaster_summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

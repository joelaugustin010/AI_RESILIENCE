"""Audit and optionally evaluate a verified Kochi flood event-panel CSV."""
import argparse
import json
from pathlib import Path
import pandas as pd
from src.ml.kochi_flood_panel import FloodPanelError, evaluate_flood_event_panel, validate_flood_event_panel

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/kochi_flood_panel_audit.json"))
    parser.add_argument("--evaluate", action="store_true")
    args = parser.parse_args()
    try:
        frame = pd.read_csv(args.csv)
        report = evaluate_flood_event_panel(frame) if args.evaluate else validate_flood_event_panel(frame).report
        code = 3 if report["status"].startswith("BLOCKED_") else 0
    except (OSError, pd.errors.ParserError, FloodPanelError, ValueError) as exc:
        report, code = {"status": "PANEL_AUDIT_FAILED", "error": str(exc)}, 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return code

if __name__ == "__main__":
    raise SystemExit(main())

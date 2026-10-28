"""Print a read-only machine-readable or human-readable local data audit."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingestion_audit import build_ingestion_report, markdown_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit local source snapshots and existing catalogs without downloading or writing data."
    )
    parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown",
        help="Output format; JSON is suitable for other tools.",
    )
    args = parser.parse_args()
    report = build_ingestion_report(ROOT)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(markdown_report(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

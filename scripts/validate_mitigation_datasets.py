"""Run the mitigation dataset audit locally: python scripts/validate_mitigation_datasets.py."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.mitigation_data_validation import validate_records
DATA = ROOT / "data" / "reference"
OUTPUT = ROOT / "reports"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    datasets = [
        ("core_project_records", DATA / "kerala_soil_conservation_completed_projects.csv", "project"),
        ("supplemental_source_leads", DATA / "mitigation_project_supplemental_candidates.csv", "project"),
        ("amrut_sector_aggregates", DATA / "kerala_amrut_sector_aggregates.csv", "aggregate"),
    ]
    reports = []
    for name, path, kind in datasets:
        if not path.exists():
            reports.append({"dataset": name, "error": f"File not found: {path.relative_to(ROOT)}"})
            continue
        result = validate_records(read_csv(path), dataset_kind=kind)
        result["dataset"] = name
        result["source_file"] = str(path.relative_to(ROOT))
        reports.append(result)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    json_path = OUTPUT / "mitigation_data_validation_report.json"
    csv_path = OUTPUT / "mitigation_data_validation_rows.csv"
    json_path.write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding="utf-8")

    flat = []
    for report in reports:
        for row in report.get("rows", []):
            flat.append({"dataset": report["dataset"], **row})
    fields = ["dataset", "row_number", "record_id", "project_name", "validation_status",
              "cost_ml_eligible", "duration_ml_eligible", "issues", "review_reasons"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in flat:
            writer.writerow({**row, "issues": "; ".join(row["issues"]),
                             "review_reasons": "; ".join(row["review_reasons"])})
    print(f"Validation report written: {json_path.relative_to(ROOT)}")
    print(f"Row-level audit written: {csv_path.relative_to(ROOT)}")
    for report in reports:
        if "error" in report:
            print(f"{report['dataset']}: {report['error']}")
        else:
            print(f"{report['dataset']}: {report['records_received']} rows | "
                  f"{report['cost_ml_eligible']} cost eligible | "
                  f"{report['duration_ml_eligible']} duration eligible")


if __name__ == "__main__":
    main()

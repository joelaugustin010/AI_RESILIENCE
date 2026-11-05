"""Build the descriptive Kochi climate-benchmark report.

Usage:
    python scripts/build_climate_benchmarks.py

The script reads the 1991-2025 Open-Meteo archived reanalysis record, compares
it with the existing 2000-2025 record over their overlap, cross-checks the
pooled ML training threshold, and writes ``reports/kochi_climate_benchmarks.json``.
It does not modify source data and does not produce a forecast or warning.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEATHER_PATH = (
    ROOT
    / "data"
    / "external"
    / "hazards"
    / "raw"
    / "weather"
    / "kochi_daily_weather_1991_2025.json"
)
COMPARISON_PATH = (
    ROOT
    / "data"
    / "external"
    / "hazards"
    / "raw"
    / "weather"
    / "kochi_daily_weather_2000_2025.json"
)
TRAINING_REPORT = ROOT / "reports" / "weather_hazard_training.json"
REPORT_PATH = ROOT / "reports" / "kochi_climate_benchmarks.json"
METADATA_PATH = WEATHER_PATH.with_name(
    "kochi_daily_weather_1991_2025.metadata.json"
)


def main() -> int:
    sys.path.insert(0, str(ROOT))
    from src.climate_benchmarks import build_benchmark_report

    if not WEATHER_PATH.is_file():
        print(f"Missing weather record: {WEATHER_PATH}")
        return 1
    report = build_benchmark_report(
        WEATHER_PATH,
        location_name="Kochi",
        comparison_path=COMPARISON_PATH,
        training_report_path=TRAINING_REPORT,
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    heat = report["heat"]["thresholds"]
    rain = report["rainfall"]["annual_total_mm"]
    spi = report["spi_readiness"]
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)}")
    print(
        "Record: "
        f"{report['record']['first_date']} to {report['record']['last_date']} "
        f"({report['record']['complete_year_count']} complete years)"
    )
    print(
        "Heat: "
        f"baseline p95 {heat['baseline_p95_c']:.2f} C; "
        f"full-record max {heat['full_record_max_c']:.2f} C"
    )
    print(
        "Rainfall: "
        f"annual mean {rain['mean']:.1f} mm; "
        f"wettest day {report['rainfall']['wettest_day']['precipitation_mm']:.1f} mm "
        f"on {report['rainfall']['wettest_day']['date']}"
    )
    print(
        "SPI readiness: "
        f"{'READY' if spi['meets_30_year_spi_reference_rule'] else 'NOT READY'} "
        f"({spi['reference_years']} years)"
    )
    if "training_threshold_cross_check" in report["validation"]:
        check = report["validation"]["training_threshold_cross_check"]
        print(
            "Training-threshold cross-check: pooled "
            f"{check['training_threshold_c']} C vs Kochi baseline p95 "
            f"{check['kochi_baseline_p95_c']:.2f} C; not directly comparable."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

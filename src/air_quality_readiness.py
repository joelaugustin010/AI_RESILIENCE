"""Read-only readiness audit for the project's processed air-quality datasets.

This audit checks local file integrity and basic structure while preserving
source limitations. It does not acquire data, repair files, calculate AQI,
infer pollution sources, or approve forecasting/model training.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from src.air_quality_monthly_reports import MonthlyReportError, load_eloor_monthly_report


AIR_DIR = Path("data/processed/air_quality")
REPORT_METADATA = "kspcb_air_reports.metadata.json"
ANNUAL_FILE = "kspcb_annual_aqi.csv"
ANNUAL_METADATA = "kspcb_annual_aqi.metadata.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object.")
    return value


def _audit_csv(
    root: Path,
    *,
    dataset_id: str,
    name: str,
    relative_path: str,
    expected: dict[str, Any] | None,
    required_columns: tuple[str, ...],
    status_if_valid: str,
    permitted_use: str,
    limitations: list[str],
    date_column: str | None = "observed_at",
    numeric_range: tuple[str, float, float] | None = None,
    identity_columns: tuple[str, ...] = (),
) -> dict[str, Any]:
    path = root / relative_path
    result: dict[str, Any] = {
        "dataset_id": dataset_id,
        "name": name,
        "path": relative_path,
        "status": "unavailable",
        "integrity_check": "not checked",
        "schema_check": "not checked",
        "row_count": None,
        "expected_row_count": expected.get("rows") if isinstance(expected, dict) else None,
        "date_start": None,
        "date_end": None,
        "permitted_use": permitted_use,
        "descriptive_analysis_eligible": False,
        "forecast_training_eligible": False,
        "limitations": list(limitations),
        "errors": [],
    }
    if not path.is_file():
        result["errors"].append(f"Processed file is missing: {relative_path}.")
        return result
    if not isinstance(expected, dict):
        result["status"] = "unsuitable"
        result["errors"].append("Expected row count and SHA-256 are missing from provenance metadata.")
        return result

    expected_hash = expected.get("sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        result["integrity_check"] = "failed"
        result["errors"].append("A valid expected SHA-256 is not recorded.")
    else:
        result["integrity_check"] = (
            "passed" if _sha256(path).casefold() == expected_hash.casefold() else "failed"
        )
        if result["integrity_check"] == "failed":
            result["errors"].append("Processed CSV SHA-256 does not match its provenance metadata.")

    try:
        frame = pd.read_csv(path)
    except (OSError, UnicodeDecodeError, pd.errors.ParserError, ValueError) as error:
        result["status"] = "unsuitable"
        result["errors"].append(f"CSV could not be parsed: {type(error).__name__}: {error}")
        return result

    result["row_count"] = int(len(frame))
    if not isinstance(expected.get("rows"), int) or isinstance(expected.get("rows"), bool):
        result["errors"].append("Expected row count is missing or invalid.")
    elif len(frame) != expected["rows"]:
        result["errors"].append(
            f"Row count mismatch: expected {expected['rows']}, found {len(frame)}."
        )

    missing_columns = [column for column in required_columns if column not in frame.columns]
    if missing_columns:
        result["schema_check"] = "failed"
        result["errors"].append("Required column(s) missing: " + ", ".join(missing_columns))
    else:
        result["schema_check"] = "passed"

    if date_column and date_column in frame.columns and not frame.empty:
        parsed = pd.to_datetime(frame[date_column], errors="coerce")
        if parsed.isna().any():
            result["errors"].append(f"{date_column} contains missing or invalid dates.")
        else:
            result["date_start"] = parsed.min().date().isoformat()
            result["date_end"] = parsed.max().date().isoformat()

    if numeric_range and numeric_range[0] in frame.columns:
        column, lower, upper = numeric_range
        values = pd.to_numeric(frame[column], errors="coerce")
        valid = values.notna() & values.map(math.isfinite) & values.between(lower, upper)
        if not bool(valid.all()):
            result["errors"].append(
                f"{column} contains missing, non-numeric, non-finite, or out-of-range values."
            )

    if identity_columns and all(column in frame.columns for column in identity_columns):
        if frame.duplicated(list(identity_columns)).any():
            result["errors"].append(
                "Duplicate row identities found for: " + ", ".join(identity_columns) + "."
            )

    if result["errors"]:
        result["status"] = "unsuitable"
    else:
        result["status"] = status_if_valid
        result["descriptive_analysis_eligible"] = True
    return result


def _monthly_result(root: Path, month: str) -> dict[str, Any]:
    dataset_id = f"kspcb_eloor_caaqms_{month.replace('-', '_')}"
    result: dict[str, Any] = {
        "dataset_id": dataset_id,
        "name": f"KSPCB Eloor CAAQMS daily report extract ({month})",
        "path": str(AIR_DIR / f"kspcb_caaqms_eloor_daily_{month}.csv").replace("\\", "/"),
        "status": "unavailable",
        "integrity_check": "not checked",
        "schema_check": "not checked",
        "row_count": None,
        "expected_row_count": None,
        "date_start": None,
        "date_end": None,
        "permitted_use": "Descriptive historical ambient-air summaries only; not live monitoring or factory-emissions evidence.",
        "descriptive_analysis_eligible": False,
        "forecast_training_eligible": False,
        "limitations": [
            "The report provides daily summaries but does not state exact pollutant averaging intervals.",
            "Row-level quality/completeness flags and verified station coordinates are absent.",
            "All extracted observations are marked unassessed; descriptive eligibility is not a quality certification.",
        ],
        "errors": [],
    }
    try:
        report = load_eloor_monthly_report(root / AIR_DIR, month)
    except MonthlyReportError as error:
        source_path = root / AIR_DIR / f"kspcb_caaqms_eloor_daily_{month}.csv"
        result["status"] = "unsuitable" if source_path.is_file() else "unavailable"
        result["errors"].append(str(error))
        return result

    observations = report["observations"]
    dates = pd.to_datetime(observations["observed_at"], errors="coerce")
    result.update(
        status="provisional",
        integrity_check="passed",
        schema_check="passed",
        row_count=int(len(observations)),
        expected_row_count=int(report["expected_days"] * observations["pollutant"].nunique()),
        date_start=dates.min().date().isoformat(),
        date_end=dates.max().date().isoformat(),
        descriptive_analysis_eligible=True,
    )
    result["limitations"].append(
        f"Coverage: {report['expected_days']} calendar days; "
        f"{int(observations['observed_at'].nunique())} dated report days."
    )
    result["limitations"].append(
        "Extracted quality flags: "
        + ", ".join(sorted(observations["quality_flag"].dropna().astype(str).unique()))
        + "."
    )
    return result


def audit_air_quality_datasets(root: Path) -> dict[str, Any]:
    """Audit tracked air-quality extracts and known missing feeds without side effects."""
    root = Path(root)
    air_dir = root / AIR_DIR
    catalog_errors: list[str] = []
    report_metadata: dict[str, Any] = {}
    annual_metadata: dict[str, Any] = {}

    try:
        report_metadata = _read_json(air_dir / REPORT_METADATA).get("sources", {})
        if not isinstance(report_metadata, dict):
            raise ValueError("The report metadata sources field must be an object.")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        catalog_errors.append(f"Could not read {REPORT_METADATA}: {error}")

    try:
        annual_metadata = _read_json(air_dir / ANNUAL_METADATA)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        catalog_errors.append(f"Could not read {ANNUAL_METADATA}: {error}")

    datasets: list[dict[str, Any]] = []

    annual_expected = {
        "sha256": annual_metadata.get("processed_sha256"),
        "rows": annual_metadata.get("rows"),
    }
    datasets.append(
        _audit_csv(
            root,
            dataset_id="kspcb_annual_aqi",
            name="KSPCB statewide year-labelled annual AQI summary",
            relative_path=str(AIR_DIR / ANNUAL_FILE).replace("\\", "/"),
            expected=annual_expected,
            required_columns=("year", "source_station", "monitoring_mode", "average_aqi"),
            status_if_valid="provisional",
            permitted_use="Descriptive year-labelled AQI summaries only; not timestamped pollutant observations.",
            limitations=[
                "The source does not state the exact annual aggregation cutoff; the 2026 label may be partial-year.",
                "The source is statewide and does not provide station coordinates.",
                "Annual AQI values are not pollutant concentrations and are not live readings.",
            ],
            date_column=None,
            numeric_range=("average_aqi", 0, 500),
            identity_columns=("year", "source_station", "monitoring_mode"),
        )
    )

    daily_source = report_metadata.get("daily_aqi", {})
    daily_outputs = daily_source.get("outputs", {}) if isinstance(daily_source, dict) else {}
    datasets.append(
        _audit_csv(
            root,
            dataset_id="kspcb_daily_aqi_2026_10_16",
            name="KSPCB daily AQI and pollutant report (16 October 2026)",
            relative_path=str(AIR_DIR / "kspcb_daily_aqi_2026-10-16.csv").replace("\\", "/"),
            expected=daily_outputs.get("kspcb_daily_aqi_2026-10-16.csv"),
            required_columns=("observed_at", "station", "source_aqi", "source_url", "PM2.5_value", "PM10_value"),
            status_if_valid="provisional",
            permitted_use="Descriptive historical station AQI and pollutant context only.",
            limitations=[
                "This is a single historical report date, not a live feed.",
                "Exact per-pollutant averaging intervals, completeness flags, station identifiers and coordinates are absent.",
            ],
            numeric_range=("source_aqi", 0, 500),
            identity_columns=("observed_at", "station"),
        )
    )

    datasets.append(
        _audit_csv(
            root,
            dataset_id="kspcb_daily_aqi_station_status_2026_10_16",
            name="KSPCB daily AQI station availability/status report (16 October 2026)",
            relative_path=str(AIR_DIR / "kspcb_daily_aqi_status_2026-10-16.csv").replace("\\", "/"),
            expected=daily_outputs.get("kspcb_daily_aqi_status_2026-10-16.csv"),
            required_columns=("observed_at", "station", "source_status", "source_url"),
            status_if_valid="provisional",
            permitted_use="Monitoring availability and missing-station context only; not pollutant concentration analysis.",
            limitations=[
                "Four stations are listed as insufficient data or power failure; missing station readings must not be treated as zero.",
            ],
            identity_columns=("observed_at", "station"),
        )
    )

    for month in ("2026-08", "2026-09"):
        datasets.append(_monthly_result(root, month))

    namp_source = report_metadata.get("namp", {})
    namp_outputs = namp_source.get("outputs", {}) if isinstance(namp_source, dict) else {}
    namp_result = _audit_csv(
        root,
        dataset_id="kspcb_namp_ernakulam_2025_06",
        name="KSPCB NAMP Ernakulam report extract (report pages state June 2025)",
        relative_path=str(AIR_DIR / "kspcb_namp_ernakulam_2025-06.csv").replace("\\", "/"),
        expected=namp_outputs.get("kspcb_namp_ernakulam_2025-06.csv"),
        required_columns=("station_code", "observed_at", "station", "unit_status", "coordinate_reference_system"),
        status_if_valid="unsuitable",
        permitted_use="Archive and source-table review only; not eligible for concentration trends, AQI calculation or spatial analysis.",
        limitations=[
            "Pollutant concentration units are not stated in the source report.",
            "Coordinate reference system is not stated; row-level coordinates are not approved for mapping.",
            "The directory filename says August 2025 while the Ernakulam report pages state June 2025.",
        ],
        identity_columns=("station_code", "observed_at"),
    )
    if namp_result["status"] == "unsuitable" and not namp_result["errors"]:
        namp_result["descriptive_analysis_eligible"] = False
    datasets.append(namp_result)

    datasets.append(
        {
            "dataset_id": "cpcb_realtime_aqi",
            "name": "CPCB real-time AQI observation feed for Kochi",
            "path": None,
            "status": "unavailable",
            "integrity_check": "not applicable",
            "schema_check": "not available",
            "row_count": None,
            "expected_row_count": None,
            "date_start": None,
            "date_end": None,
            "permitted_use": "No live data are currently available in this project checkout.",
            "descriptive_analysis_eligible": False,
            "forecast_training_eligible": False,
            "limitations": [
                "The official catalogue is documented, but an API credential and Kochi observation payload are not available in the project.",
                "Do not display cached historical readings as current AQI.",
            ],
            "errors": ["No live CPCB AQI feed is connected."],
        }
    )

    status_counts = {
        status: sum(item["status"] == status for item in datasets)
        for status in ("verified", "provisional", "unavailable", "unsuitable")
    }
    return {
        "schema_version": 1,
        "overall_status": "provisional" if any(item["status"] == "provisional" for item in datasets) else "unavailable",
        "forecasting_ready": False,
        "conclusion": (
            "Existing KSPCB extracts support limited historical descriptive analysis. "
            "Live monitoring, validated concentration coverage and forecasting are not ready."
        ),
        "dataset_count": len(datasets),
        "status_counts": status_counts,
        "descriptive_dataset_count": sum(item["descriptive_analysis_eligible"] for item in datasets),
        "forecast_training_dataset_count": sum(item["forecast_training_eligible"] for item in datasets),
        "catalog_errors": catalog_errors,
        "datasets": datasets,
    }

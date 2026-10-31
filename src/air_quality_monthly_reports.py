"""Load and compare preserved KSPCB Eloor monthly report extracts.

The source CSVs remain the authority for values, units, and report dates. This
module verifies their recorded provenance and returns a validated copy for the
existing descriptive air-quality helpers; it performs no unit conversion.
"""

from __future__ import annotations

import calendar
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from urllib.parse import urlsplit

from src.air_quality import AirQualityDataError, SUPPORTED_POLLUTANTS, validate_observations


KSPCB_PUBLISHER = "Kerala State Pollution Control Board"
MONTHLY_POLLUTANTS = ("PM10", "PM2.5", "SO2", "CO", "NO", "NO2", "NOx", "NH3", "O3")
WEATHER_VALUE_COLUMNS = ("wind_speed", "wind_direction", "temperature", "relative_humidity")
REPORT_FILES = {
    "2026-08": {
        "metadata_file": "kspcb_air_reports.metadata.json",
        "source_path": ("sources", "monthly_caaqms"),
        "outputs": {
            "observations": "kspcb_caaqms_eloor_daily_2026-08.csv",
            "aqi": "kspcb_caaqms_eloor_aqi_2026-08.csv",
            "weather": "kspcb_caaqms_eloor_weather_2026-08.csv",
        },
    },
    "2026-09": {
        "metadata_file": "kspcb_caaqms_eloor_2026-09.metadata.json",
        "source_path": ("sources", "kspcb_caaqms_eloor_2026_09"),
        "outputs": {
            "observations": "kspcb_caaqms_eloor_daily_2026-09.csv",
            "aqi": "kspcb_caaqms_eloor_aqi_2026-09.csv",
            "weather": "kspcb_caaqms_eloor_weather_2026-09.csv",
        },
    },
}


class MonthlyReportError(ValueError):
    """Raised when a monthly report extract fails provenance or data checks."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_metadata(reports_dir: Path, month: str) -> tuple[dict[str, Any], dict[str, Any]]:
    config = REPORT_FILES.get(month)
    if config is None:
        raise MonthlyReportError(f"Unsupported Eloor report month: {month!r}.")
    metadata_path = reports_dir / config["metadata_file"]
    try:
        document = json.loads(metadata_path.read_text(encoding="utf-8"))
        source: Any = document
        for key in config["source_path"]:
            source = source[key]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        raise MonthlyReportError(f"Could not read provenance metadata for {month}: {error}") from error

    if not isinstance(source, dict):
        raise MonthlyReportError(f"Provenance entry for {month} is not an object.")
    if source.get("publisher") != KSPCB_PUBLISHER:
        raise MonthlyReportError(f"Unexpected publisher for {month} Eloor report.")
    source_url = str(source.get("source_url", "")).strip()
    try:
        parsed_source_url = urlsplit(source_url)
        valid_source_url = (
            parsed_source_url.scheme == "https"
            and bool(parsed_source_url.hostname)
            and parsed_source_url.username is None
            and parsed_source_url.password is None
        )
    except ValueError:
        valid_source_url = False

    if not valid_source_url or not source.get("retrieved_on"):
        raise MonthlyReportError(
            f"Source URL is not a valid HTTPS web address or retrieval date is missing for {month}."
        )
    return config, source


def _load_verified_csv(
    reports_dir: Path,
    filename: str,
    output_metadata: dict[str, Any],
    source_url: str,
    *,
    source_columns: Iterable[str],
) -> pd.DataFrame:
    path = reports_dir / filename
    try:
        data = path.read_bytes()
    except OSError as error:
        raise MonthlyReportError(f"Could not read {filename}: {error}") from error
    if _sha256(data) != output_metadata.get("sha256"):
        raise MonthlyReportError(f"SHA-256 does not match provenance metadata for {filename}.")
    try:
        frame = pd.read_csv(path, dtype={column: "string" for column in source_columns})
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as error:
        raise MonthlyReportError(f"Could not parse {filename}: {error}") from error
    if len(frame) != output_metadata.get("rows"):
        raise MonthlyReportError(f"Row count does not match provenance metadata for {filename}.")
    if frame.empty:
        raise MonthlyReportError(f"The {filename} extract is empty.")
    if "source_url" not in frame or not frame["source_url"].astype("string").eq(source_url).all():
        raise MonthlyReportError(f"Source URL is missing or inconsistent in {filename}.")
    return frame


def _validate_report_dates(frame: pd.DataFrame, month: str, filename: str) -> pd.Series:
    if "observed_at" not in frame or frame["observed_at"].isna().any():
        raise MonthlyReportError(f"Missing report dates in {filename}.")
    original = frame["observed_at"].astype("string")
    parsed = pd.to_datetime(original, format="%Y-%m-%d", errors="coerce")
    if parsed.isna().any() or parsed.dt.strftime("%Y-%m-%d").astype("string").ne(original).any():
        raise MonthlyReportError(f"Invalid or non-day-precision dates in {filename}.")
    if parsed.dt.strftime("%Y-%m").ne(month).any():
        raise MonthlyReportError(f"Dates fall outside the declared {month} period in {filename}.")
    return parsed


def load_eloor_monthly_report(
    reports_dir: Path,
    month: str,
) -> dict[str, Any]:
    """Load one preserved monthly extract after source-hash and schema checks.

    Returns original CSV values and a separately validated observation copy.
    Day-only dates remain day-only; no clock time or averaging interval is added.
    """
    reports_dir = Path(reports_dir)
    config, source = _source_metadata(reports_dir, month)
    expected_days = calendar.monthrange(int(month[:4]), int(month[5:7]))[1]
    outputs = config["outputs"]
    output_metadata = source.get("outputs", {})
    try:
        observations = _load_verified_csv(
            reports_dir,
            outputs["observations"],
            output_metadata[outputs["observations"]],
            source["source_url"],
            source_columns=("observed_at", "station", "pollutant", "unit", "averaging_period", "quality_flag"),
        )
        aqi = _load_verified_csv(
            reports_dir,
            outputs["aqi"],
            output_metadata[outputs["aqi"]],
            source["source_url"],
            source_columns=("observed_at", "station", "source_aqi_category"),
        )
        weather = _load_verified_csv(
            reports_dir,
            outputs["weather"],
            output_metadata[outputs["weather"]],
            source["source_url"],
            source_columns=("observed_at", "station", "wind_speed_unit", "wind_direction_unit", "temperature_unit", "relative_humidity_unit", "averaging_period"),
        )
    except (KeyError, TypeError) as error:
        raise MonthlyReportError(f"Incomplete output metadata for {month}: {error}") from error

    required = {
        "observations": {"observed_at", "station", "pollutant", "value", "unit", "averaging_period", "quality_flag", "source_url"},
        "aqi": {"observed_at", "station", "source_aqi", "source_url"},
        "weather": {"observed_at", "station", *WEATHER_VALUE_COLUMNS, "source_url"},
    }
    for name, frame in (("observations", observations), ("aqi", aqi), ("weather", weather)):
        missing = sorted(required[name] - set(frame.columns))
        if missing:
            raise MonthlyReportError(f"Missing required columns in {month} {name}: {', '.join(missing)}.")
        _validate_report_dates(frame, month, outputs[name])
        if frame["station"].astype("string").str.casefold().ne("eloor").any():
            raise MonthlyReportError(f"Unexpected station label in {outputs[name]}.")

    _validate_report_dates(observations, month, outputs["observations"])
    if observations.duplicated(["observed_at", "station", "pollutant", "averaging_period"]).any():
        raise MonthlyReportError(f"Duplicate date/pollutant rows in {outputs['observations']}.")
    unknown_pollutants = sorted(set(observations["pollutant"].dropna()) - set(MONTHLY_POLLUTANTS))
    if unknown_pollutants:
        raise MonthlyReportError(f"Unexpected pollutant(s) in {month}: {', '.join(unknown_pollutants)}.")
    missing_periods = sorted(set(MONTHLY_POLLUTANTS) - set(observations["pollutant"].dropna()))
    # An absent pollutant is retained as a coverage gap instead of being filled.
    for pollutant in set(observations["pollutant"].dropna()):
        units = observations.loc[observations["pollutant"].eq(pollutant), "unit"].dropna().unique()
        if len(units) != 1:
            raise MonthlyReportError(f"Inconsistent source units for {pollutant} in {month}.")

    if aqi.duplicated(["observed_at", "station"]).any() or weather.duplicated(["observed_at", "station"]).any():
        raise MonthlyReportError(f"Duplicate daily AQI or weather rows in {month}.")
    for value_column in ("source_aqi",):
        numeric = pd.to_numeric(aqi[value_column], errors="coerce")
        nonblank = aqi[value_column].notna() & aqi[value_column].astype("string").str.strip().ne("")
        invalid = nonblank & numeric.isna()
        out_of_range = numeric.dropna().map(
            lambda value: not float(value).is_integer() or not 0 <= value <= 500
        )
        if invalid.any() or out_of_range.any():
            raise MonthlyReportError(f"Invalid source-reported AQI values in {month}.")
        aqi[value_column] = numeric
    for value_column in WEATHER_VALUE_COLUMNS:
        numeric = pd.to_numeric(weather[value_column], errors="coerce")
        nonblank = weather[value_column].notna() & weather[value_column].astype("string").str.strip().ne("")
        if (nonblank & numeric.isna()).any():
            raise MonthlyReportError(f"Non-numeric source weather values in {month}: {value_column}.")
        weather[value_column] = numeric

    numeric_values = pd.to_numeric(observations["value"], errors="coerce")
    nonblank_values = observations["value"].notna() & observations["value"].astype("string").str.strip().ne("")
    if (nonblank_values & numeric_values.isna()).any():
        raise MonthlyReportError(f"Non-numeric pollutant values in {month}.")
    observations["value"] = numeric_values
    observed_values = observations.loc[observations["value"].notna()].copy()
    try:
        validated = validate_observations(observed_values, ["Eloor"], verified=True)
    except AirQualityDataError as error:
        raise MonthlyReportError(f"Air-quality validation failed for {month}: {error}") from error

    report = {
        "month": month,
        "label": pd.Period(month, freq="M").strftime("%B %Y"),
        "expected_days": expected_days,
        "expected_dates": pd.date_range(f"{month}-01", periods=expected_days, freq="D").strftime("%Y-%m-%d").tolist(),
        "source": source,
        "source_url": source["source_url"],
        "observations": observations,
        "validated_observations": validated,
        "aqi": aqi,
        "weather": weather,
        "missing_pollutants": missing_periods,
    }
    return report


def monthly_report_coverage(report: dict[str, Any]) -> pd.DataFrame:
    """Count dated and complete entries without filling missing source records."""
    expected = set(report["expected_dates"])
    rows: list[dict[str, Any]] = []

    for pollutant in MONTHLY_POLLUTANTS:
        group = report["observations"].loc[report["observations"]["pollutant"].eq(pollutant)]
        present_dates = set(group["observed_at"].dropna().astype(str))
        value_dates = set(group.loc[group["value"].notna(), "observed_at"].astype(str))
        rows.append(
            {
                "Report month": report["label"],
                "Series": pollutant,
                "Expected dates": len(expected),
                "Dates with records": len(present_dates & expected),
                "Dates with values": len(value_dates & expected),
                "Missing dates": len(expected - present_dates),
                "Missing value cells": int(group["value"].isna().sum()),
                "Unit": ", ".join(sorted(group["unit"].dropna().astype(str).unique())),
            }
        )

    for series_name, frame, value_columns in (
        ("Source AQI", report["aqi"], ("source_aqi",)),
        ("Daily weather summary", report["weather"], WEATHER_VALUE_COLUMNS),
    ):
        present_dates = set(frame["observed_at"].dropna().astype(str))
        complete = frame[list(value_columns)].notna().all(axis=1)
        value_dates = set(frame.loc[complete, "observed_at"].astype(str))
        missing_cells = int(frame[list(value_columns)].isna().sum().sum())
        rows.append(
            {
                "Report month": report["label"],
                "Series": series_name,
                "Expected dates": len(expected),
                "Dates with records": len(present_dates & expected),
                "Dates with values": len(value_dates & expected),
                "Missing dates": len(expected - present_dates),
                "Missing value cells": missing_cells,
                "Unit": "source units retained; see daily weather table" if series_name == "Daily weather summary" else "AQI index (source-reported)",
            }
        )
    return pd.DataFrame(rows)


def compare_monthly_report_values(reports: Iterable[dict[str, Any]]) -> pd.DataFrame:
    """Compare derived monthly means only for exact shared station/field metadata.

    Means are arithmetic means of source-reported daily rows, not official
    monthly averages. Matching requires the same station, pollutant, source unit,
    and source averaging-period label; values are never converted.
    """
    ordered = sorted(list(reports), key=lambda report: report["month"])
    columns = [
        "Station",
        "Pollutant",
        "Unit",
        "Source averaging-period label",
        f"{ordered[0]['label']} dated values" if ordered else "First month dated values",
        f"{ordered[0]['label']} mean of daily report values" if ordered else "First month mean",
        f"{ordered[1]['label']} dated values" if len(ordered) > 1 else "Second month dated values",
        f"{ordered[1]['label']} mean of daily report values" if len(ordered) > 1 else "Second month mean",
    ]
    if len(ordered) != 2:
        return pd.DataFrame(columns=columns)

    summaries: list[dict[tuple[str, str, str, str], dict[str, Any]]] = []
    for report in ordered:
        frame = report["observations"].copy()
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        grouped = frame.groupby(["station", "pollutant", "unit", "averaging_period"], dropna=False)
        summaries.append(
            {
                key: {
                    "count": int(group["value"].notna().sum()),
                    "mean": float(group["value"].mean()),
                }
                for key, group in grouped
                if group["value"].notna().any()
            }
        )

    shared = sorted(set(summaries[0]) & set(summaries[1]))
    result = []
    for station, pollutant, unit, period_label in shared:
        if station.casefold() != "eloor" or pollutant not in SUPPORTED_POLLUTANTS:
            continue
        if SUPPORTED_POLLUTANTS[pollutant] != unit:
            continue
        result.append(
            {
                "Station": station,
                "Pollutant": pollutant,
                "Unit": unit,
                "Source averaging-period label": period_label,
                f"{ordered[0]['label']} dated values": summaries[0][(station, pollutant, unit, period_label)]["count"],
                f"{ordered[0]['label']} mean of daily report values": summaries[0][(station, pollutant, unit, period_label)]["mean"],
                f"{ordered[1]['label']} dated values": summaries[1][(station, pollutant, unit, period_label)]["count"],
                f"{ordered[1]['label']} mean of daily report values": summaries[1][(station, pollutant, unit, period_label)]["mean"],
            }
        )
    return pd.DataFrame(result, columns=columns)

"""Validation and descriptive summaries for verified air-quality observations.

The caller must attest that observations have verified provenance. This module
does not retrieve data or decide whether a source is authoritative; it prevents
unreviewed rows from entering the analysis helpers by accident.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable, Mapping

import pandas as pd


REQUIRED_COLUMNS = (
    "observed_at",
    "station",
    "pollutant",
    "value",
    "unit",
    "averaging_period",
    "quality_flag",
)
SUPPORTED_POLLUTANTS = {
    "PM2.5": "ug/m3",
    "PM10": "ug/m3",
    "SO2": "ug/m3",
    "CO": "mg/m3",
    "NO": "ug/m3",
    "NO2": "ug/m3",
    "NOx": "ug/m3",
    "NH3": "ug/m3",
    "O3": "ug/m3",
    "Pb": "ug/m3",
}
QUALITY_FLAGS = {"valid", "suspect", "invalid", "unassessed"}
_VALIDATED_ATTR = "ai_resilience_verified_air_quality"
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CPCB_AQI_CATEGORIES = (
    (0, 50, "Good", "Minimal impact"),
    (51, 100, "Satisfactory", "Minor breathing discomfort to sensitive people"),
    (101, 200, "Moderately polluted", "Breathing discomfort to people with lung, asthma, or heart disease"),
    (201, 300, "Poor", "Breathing discomfort to most people on prolonged exposure"),
    (301, 400, "Very Poor", "Respiratory illness on prolonged exposure"),
    (401, 500, "Severe", "Respiratory effects even on healthy people; serious impacts for people with existing disease"),
)


class AirQualityDataError(ValueError):
    """Raised when observations are unverified or fail the analysis schema."""


def cpcb_aqi_category(value: object) -> tuple[str, str]:
    """Return the official CPCB category and health meaning for an AQI value.

    This classifies an AQI index only; it does not convert concentrations to AQI
    or make an annual mean into a valid daily/rolling AQI.
    """
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise AirQualityDataError("AQI must be an integer between 0 and 500.") from error
    if not math.isfinite(number) or not number.is_integer() or not 0 <= number <= 500:
        raise AirQualityDataError("AQI must be an integer between 0 and 500.")
    for low, high, category, meaning in CPCB_AQI_CATEGORIES:
        if low <= number <= high:
            return category, meaning
    raise AirQualityDataError("AQI falls outside the CPCB category bands.")


def _station_names(
    station_inventory: Iterable[str | Mapping[str, str]],
) -> dict[str, str]:
    names: dict[str, str] = {}
    for item in station_inventory:
        name = item.get("station") if isinstance(item, Mapping) else item
        if not isinstance(name, str) or not name.strip():
            raise AirQualityDataError(
                "Station inventory entries must have a non-empty station name."
            )
        label = name.strip()
        key = label.casefold()
        if key in names and names[key] != label:
            raise AirQualityDataError(f"Station inventory contains ambiguous names for {label!r}.")
        names[key] = label
    if not names:
        raise AirQualityDataError("A documented station inventory is required.")
    return names


def _canonical_pollutant(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AirQualityDataError("Pollutant names must be non-empty strings.")
    key = unicodedata.normalize("NFKC", value).casefold()
    key = re.sub(r"\s+", "", key).replace("₂", "2").replace("₃", "3")
    aliases = {
        "pm25": "PM2.5",
        "pm2.5": "PM2.5",
        "pm10": "PM10",
        "so2": "SO2",
        "co": "CO",
        "no": "NO",
        "no2": "NO2",
        "nox": "NOx",
        "nh3": "NH3",
        "o3": "O3",
        "pb": "Pb",
    }
    pollutant = aliases.get(key)
    if pollutant is None:
        raise AirQualityDataError(f"Unsupported pollutant: {value!r}.")
    return pollutant


def _canonical_unit(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AirQualityDataError("Measurement units must be non-empty strings.")
    key = unicodedata.normalize("NFKC", value).casefold().strip()
    key = key.replace("μ", "u").replace("µ", "u").replace("³", "3")
    key = re.sub(r"\s+", "", key)
    aliases = {
        "ug/m3": "ug/m3",
        "μg/m3": "ug/m3",
        "microgram/m3": "ug/m3",
        "micrograms/m3": "ug/m3",
        "mg/m3": "mg/m3",
        "milligram/m3": "mg/m3",
        "milligrams/m3": "mg/m3",
    }
    unit = aliases.get(key)
    if unit is None:
        raise AirQualityDataError(f"Unsupported concentration unit: {value!r}.")
    return unit


def _parse_timestamp(value: object) -> pd.Timestamp | str:
    if isinstance(value, str) and _DATE_ONLY.fullmatch(value.strip()):
        try:
            return pd.Timestamp(value.strip()).date().isoformat()
        except (TypeError, ValueError, OverflowError) as error:
            raise AirQualityDataError(f"Invalid observation date: {value!r}.") from error
    try:
        timestamp = pd.Timestamp(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise AirQualityDataError(f"Invalid observation timestamp: {value!r}.") from error
    if pd.isna(timestamp):
        raise AirQualityDataError("Observation timestamps cannot be missing or invalid.")
    if timestamp.tzinfo is None:
        raise AirQualityDataError("Observation timestamps must include a timezone.")
    return timestamp.tz_convert("UTC")


def validate_observations(
    observations: pd.DataFrame,
    station_inventory: Iterable[str | Mapping[str, str]],
    *,
    verified: bool,
) -> pd.DataFrame:
    """Validate and normalize a long-form verified observation table.

    ``verified=True`` is an explicit caller attestation that source provenance,
    reuse terms, and the source-to-station mapping have been reviewed. It does
    not replace those reviews. Timestamp observations must include a timezone;
    source date-only observations retain day precision without an invented time.
    Missing values are rejected; pollutant/unit pairs follow the common
    concentration units used by the documented monitoring parameters.
    """
    if verified is not True:
        raise AirQualityDataError("Unverified observations are not eligible for analysis.")
    if not isinstance(observations, pd.DataFrame):
        raise AirQualityDataError("Observations must be provided as a pandas DataFrame.")
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in observations.columns]
    if missing_columns:
        raise AirQualityDataError("Missing required column(s): " + ", ".join(missing_columns))
    if observations.empty:
        raise AirQualityDataError("No air-quality observation rows were supplied.")

    frame = observations.copy()
    empty_columns = []
    for column in ("station", "pollutant", "unit", "averaging_period", "quality_flag"):
        values = frame[column].astype("string").str.strip()
        if values.isna().any() or values.eq("").any():
            empty_columns.append(column)
        frame[column] = values
    if frame["observed_at"].isna().any():
        empty_columns.append("observed_at")
    if frame["value"].isna().any():
        empty_columns.append("value")
    if empty_columns:
        raise AirQualityDataError("Missing values in required field(s): " + ", ".join(empty_columns))

    station_lookup = _station_names(station_inventory)
    normalized_stations = []
    for station in frame["station"]:
        label = str(station).strip()
        canonical = station_lookup.get(label.casefold())
        if canonical is None:
            raise AirQualityDataError(f"Unknown monitoring station: {label!r}.")
        normalized_stations.append(canonical)
    frame["station"] = normalized_stations

    frame["pollutant"] = [_canonical_pollutant(value) for value in frame["pollutant"]]
    frame["unit"] = [_canonical_unit(value) for value in frame["unit"]]
    for pollutant, unit in zip(frame["pollutant"], frame["unit"]):
        if SUPPORTED_POLLUTANTS[pollutant] != unit:
            raise AirQualityDataError(
                f"Unit {unit!r} is not supported for pollutant {pollutant}."
            )

    parsed_times = [_parse_timestamp(value) for value in frame["observed_at"]]
    precision = ["day" if isinstance(value, str) else "instant" for value in parsed_times]
    if len(set(precision)) != 1:
        raise AirQualityDataError(
            "Date-only observations and timestamp observations cannot be mixed in one table."
        )
    supplied_precision = frame.get("timestamp_precision")
    if supplied_precision is not None:
        normalized_precision = supplied_precision.astype("string").str.strip().str.casefold()
        if normalized_precision.isna().any() or normalized_precision.tolist() != precision:
            raise AirQualityDataError(
                "timestamp_precision must match the source precision (day or instant)."
            )
    frame["timestamp_precision"] = precision
    if precision[0] == "day":
        frame["observed_at"] = pd.Series(parsed_times, index=frame.index, dtype="string")
    else:
        frame["observed_at"] = pd.to_datetime(parsed_times, utc=True)
    numeric_values = pd.to_numeric(frame["value"], errors="coerce")
    if numeric_values.isna().any() or not all(
        math.isfinite(float(value)) for value in numeric_values
    ):
        raise AirQualityDataError("Measurement values must be finite numbers.")
    if (numeric_values < 0).any():
        raise AirQualityDataError(
            "Negative pollutant concentrations must be reviewed, not analyzed."
        )
    frame["value"] = numeric_values.astype(float)

    frame["quality_flag"] = frame["quality_flag"].str.casefold()
    unknown_flags = sorted(set(frame["quality_flag"]) - QUALITY_FLAGS)
    if unknown_flags:
        raise AirQualityDataError(
            "Quality flags must be mapped to valid, suspect, or invalid; unknown: "
            + ", ".join(unknown_flags)
        )

    identity = ["observed_at", "station", "pollutant", "averaging_period"]
    if frame.duplicated(identity).any():
        raise AirQualityDataError(
            "Duplicate station, time, pollutant, and averaging-period rows were found."
        )

    frame.attrs[_VALIDATED_ATTR] = True
    return frame


def _analysis_rows(
    observations: pd.DataFrame, pollutant: str, *, include_unassessed: bool = False
) -> pd.DataFrame:
    if (
        not isinstance(observations, pd.DataFrame)
        or observations.attrs.get(_VALIDATED_ATTR) is not True
    ):
        raise AirQualityDataError("Run validate_observations on verified data before analysis.")
    selected_pollutant = _canonical_pollutant(pollutant)
    accepted_flags = {"valid", "unassessed"} if include_unassessed else {"valid"}
    rows = observations.loc[
        observations["quality_flag"].isin(accepted_flags)
        & observations["pollutant"].eq(selected_pollutant)
    ].copy()
    if rows.empty:
        raise AirQualityDataError(
            f"No eligible {selected_pollutant} observations are available."
        )
    return rows


def station_comparison(
    observations: pd.DataFrame, pollutant: str, *, include_unassessed: bool = False
) -> pd.DataFrame:
    """Return descriptive station summaries, optionally including unassessed rows."""
    rows = _analysis_rows(observations, pollutant, include_unassessed=include_unassessed)
    return (
        rows.groupby(["station", "pollutant", "unit"], as_index=False)
        .agg(
            observation_count=("value", "size"),
            mean_value=("value", "mean"),
            median_value=("value", "median"),
            maximum_value=("value", "max"),
        )
        .sort_values("station", kind="stable")
        .reset_index(drop=True)
    )


def time_series_summary(
    observations: pd.DataFrame, pollutant: str, *, include_unassessed: bool = False
) -> pd.DataFrame:
    """Return readings by source time precision and station without resampling."""
    rows = _analysis_rows(observations, pollutant, include_unassessed=include_unassessed)
    return (
        rows.groupby(["observed_at", "station", "pollutant", "unit"], as_index=False)
        .agg(
            observation_count=("value", "size"),
            mean_value=("value", "mean"),
            minimum_value=("value", "min"),
            maximum_value=("value", "max"),
        )
        .sort_values(["station", "observed_at"], kind="stable")
        .reset_index(drop=True)
    )

"""Strict, descriptive readers for the Phase 2 external data snapshots."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


NASA_FILE = "nasa_power_kochi_center_daily_20200101_20250101.json"
IMD_FILE_PATTERN = "imd_daily_gridded_rainfall_{year}_025deg.nc"
OSM_FILE = "openstreetmap_roads_provisional_kochi_bounds.json"
USGS_FILE = "usgs_earthquakes_kerala_bbox_1900_present_m0.geojson"
NASA_PARAMETERS = (
    "PRECTOTCORR",
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "WS10M",
)
REFERENCE_LATITUDE = 9.93
REFERENCE_LONGITUDE = 76.27


class Phase2DataError(ValueError):
    """Raised when an external snapshot is malformed or fails integrity checks."""


class Phase2DataUnavailable(FileNotFoundError):
    """Raised when an optional Phase 2 data snapshot is not in this checkout."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise Phase2DataUnavailable(f"Optional dataset metadata is not available: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise Phase2DataError(f"Could not read dataset metadata {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise Phase2DataError(f"Expected a JSON object in {path}.")
    return value


def read_optional_metadata(path: str | Path) -> dict[str, Any] | None:
    """Return parsed metadata, distinguish absent files from malformed metadata."""
    metadata_path = Path(path)
    if not metadata_path.is_file():
        return None
    return _read_json(metadata_path)


def _read_verified_json_snapshot(
    root: str | Path,
    filename: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(root) / "data" / "raw" / "experimental" / filename
    if not path.is_file():
        raise Phase2DataUnavailable(f"Optional dataset snapshot is not available: {path}")
    metadata = _read_json(path.with_name(path.name + ".metadata.json"))
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != metadata.get("sha256"):
        raise Phase2DataError(f"Dataset snapshot SHA-256 mismatch: {path}")
    try:
        response = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Phase2DataError(f"Dataset snapshot is not valid JSON: {path}: {exc}") from exc
    if not isinstance(response, dict):
        raise Phase2DataError(f"Expected a JSON object in dataset snapshot: {path}")
    return response, metadata


def load_osm_road_snapshot(
    root: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return OSM road counts and metadata without inferring access or exposure."""
    response, metadata = _read_verified_json_snapshot(root, OSM_FILE)
    elements = response.get("elements")
    if not isinstance(elements, list):
        raise Phase2DataError("OSM road snapshot does not contain an elements array.")
    roads = [
        item
        for item in elements
        if isinstance(item, dict)
        and item.get("type") == "way"
        and isinstance(item.get("tags"), dict)
        and item["tags"].get("highway")
    ]
    osm_metadata = response.get("osm3s")
    return metadata, {
        "road_way_count": len(roads),
        "snapshot_timestamp": (
            osm_metadata.get("timestamp_osm_base")
            if isinstance(osm_metadata, dict)
            else None
        ),
        "inference": (
            "Mapped ways are not verified for completeness, condition, passability, "
            "hospital access, or flood exposure."
        ),
    }


def load_usgs_earthquake_query(
    root: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return catalog query counts without interpreting an empty result as no hazard."""
    response, metadata = _read_verified_json_snapshot(root, USGS_FILE)
    features = response.get("features")
    if response.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise Phase2DataError("USGS response is not a GeoJSON FeatureCollection.")
    time_range = metadata.get("time_range")
    if not isinstance(time_range, dict) or not {"start", "end"} <= set(time_range):
        raise Phase2DataError("USGS query metadata is missing its time range.")
    return metadata, {
        "catalogue_event_count": len(features),
        "query_bounds": metadata.get("query_bounds"),
        "time_range": time_range,
        "minimum_magnitude": metadata.get("minimum_magnitude"),
        "response_status": metadata.get("response_status"),
        "inference": (
            "A zero-result query does not establish zero earthquake hazard or a complete "
            "local seismicity catalogue."
        ),
    }


def load_nasa_power(
    root: str | Path,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    """Load NASA POWER point estimates after verifying the stored snapshot hash."""
    raw_path = Path(root) / "data" / "raw" / "experimental" / NASA_FILE
    metadata_path = raw_path.with_name(raw_path.name + ".metadata.json")
    if not raw_path.is_file():
        raise Phase2DataUnavailable(f"NASA POWER snapshot is not available: {raw_path}")
    metadata = _read_json(metadata_path)
    payload = raw_path.read_bytes()
    expected_hash = metadata.get("sha256")
    actual_hash = hashlib.sha256(payload).hexdigest()
    if not isinstance(expected_hash, str) or expected_hash != actual_hash:
        raise Phase2DataError(f"NASA POWER snapshot SHA-256 mismatch: {raw_path}")
    try:
        response = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Phase2DataError(f"NASA POWER snapshot is not valid JSON: {exc}") from exc
    header = response.get("header", {})
    if header.get("time_standard") != "UTC":
        raise Phase2DataError("NASA POWER data must declare UTC time standard.")
    parameter_values = response.get("properties", {}).get("parameter", {})
    parameter_metadata = response.get("parameters", {})
    missing = sorted(set(NASA_PARAMETERS) - set(parameter_values))
    if missing:
        raise Phase2DataError("NASA POWER data is missing variable(s): " + ", ".join(missing))
    if sorted(set(NASA_PARAMETERS) - set(parameter_metadata)):
        raise Phase2DataError("NASA POWER data is missing units or definitions for requested variables.")

    date_sets = [set(parameter_values[name]) for name in NASA_PARAMETERS]
    if any(dates != date_sets[0] for dates in date_sets[1:]):
        raise Phase2DataError("NASA POWER variables do not share the same daily timestamps.")
    dates = sorted(date_sets[0])
    if not dates:
        raise Phase2DataError("NASA POWER response contains no dated values.")
    rows: dict[str, Any] = {
        "date": [datetime.strptime(day, "%Y%m%d") for day in dates]
    }
    fill_value = header.get("fill_value")
    missing_counts: dict[str, int] = {}
    for name in NASA_PARAMETERS:
        values: list[float] = []
        missing_count = 0
        for day in dates:
            value = parameter_values[name][day]
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError) as exc:
                raise Phase2DataError(f"NASA POWER value {name}/{day} is not numeric.") from exc
            if not math.isfinite(number):
                raise Phase2DataError(f"NASA POWER value {name}/{day} is not finite.")
            if fill_value is not None and number == float(fill_value):
                values.append(float("nan"))
                missing_count += 1
            else:
                values.append(number)
        rows[name] = values
        missing_counts[name] = missing_count
    frame = pd.DataFrame(rows)
    summary = {
        "row_count": int(len(frame)),
        "start": frame["date"].min().date().isoformat(),
        "end": frame["date"].max().date().isoformat(),
        "missing_values_by_parameter": missing_counts,
        "valid_values_by_parameter": {
            name: int(frame[name].notna().sum()) for name in NASA_PARAMETERS
        },
        "parameter_metadata": parameter_metadata,
        "fill_value": fill_value,
        "coordinate": response.get("geometry", {}).get("coordinates"),
        "time_standard": header.get("time_standard"),
    }
    return frame, metadata, summary


def _netcdf_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("ascii", errors="replace")
    return str(value)


def load_imd_rainfall_cell(
    root: str | Path,
    year: int,
    latitude: float = REFERENCE_LATITUDE,
    longitude: float = REFERENCE_LONGITUDE,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    """Extract one nearest IMD 0.25-degree cell as a clearly derived time series."""
    path = (
        Path(root)
        / "data"
        / "raw"
        / "experimental"
        / IMD_FILE_PATTERN.format(year=year)
    )
    if not path.is_file():
        raise Phase2DataUnavailable(f"IMD annual rainfall snapshot is not available: {path}")
    metadata = _read_json(path.with_name(path.name + ".metadata.json"))
    payload_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    if payload_hash != metadata.get("sha256"):
        raise Phase2DataError(f"IMD rainfall snapshot SHA-256 mismatch: {path}")
    try:
        from scipy.io import netcdf_file

        dataset = netcdf_file(path, mode="r", mmap=False)
    except (ImportError, OSError, ValueError) as exc:
        raise Phase2DataError(f"Could not open IMD NetCDF snapshot {path}: {exc}") from exc

    try:
        variables = dataset.variables
        required = {"LONGITUDE", "LATITUDE", "TIME", "RAINFALL"}
        missing_variables = sorted(required - set(variables))
        if missing_variables:
            raise Phase2DataError(
                "IMD rainfall NetCDF is missing variable(s): "
                + ", ".join(missing_variables)
            )
        longitudes = np.asarray(variables["LONGITUDE"][:], dtype=float)
        latitudes = np.asarray(variables["LATITUDE"][:], dtype=float)
        if (
            longitudes.size == 0
            or latitudes.size == 0
            or not np.isfinite(longitudes).all()
            or not np.isfinite(latitudes).all()
        ):
            raise Phase2DataError("IMD coordinate axes are empty or contain non-finite values.")
        longitude_index = int(np.abs(longitudes - longitude).argmin())
        latitude_index = int(np.abs(latitudes - latitude).argmin())
        cell_longitude = float(longitudes[longitude_index])
        cell_latitude = float(latitudes[latitude_index])

        rainfall_variable = variables["RAINFALL"]
        dimension_names = tuple(name.upper() for name in rainfall_variable.dimensions)
        if set(dimension_names) != {"TIME", "LATITUDE", "LONGITUDE"}:
            raise Phase2DataError(
                "IMD RAINFALL dimensions differ from TIME, LATITUDE, LONGITUDE."
            )
        rainfall_data = np.asarray(rainfall_variable[:])
        dimension_order = [dimension_names.index(name) for name in ("TIME", "LATITUDE", "LONGITUDE")]
        rainfall_data = np.transpose(rainfall_data, axes=dimension_order)
        if (
            rainfall_data.shape[1] != len(latitudes)
            or rainfall_data.shape[2] != len(longitudes)
        ):
            raise Phase2DataError("IMD rainfall array shape does not match its coordinate axes.")
        series = rainfall_data[:, latitude_index, longitude_index].astype(float)

        fill_value = getattr(
            rainfall_variable,
            "missing_value",
            getattr(rainfall_variable, "_FillValue", -999.0),
        )
        fill_value = float(np.asarray(fill_value).reshape(-1)[0])
        time_variable = variables["TIME"]
        time_units = _netcdf_text(getattr(time_variable, "units", ""))
        match = re.fullmatch(
            r"(days|hours) since (\d{4}-\d{2}-\d{2})(?:[ T]\d{2}:\d{2}:\d{2})?",
            time_units.strip(),
        )
        if not match:
            raise Phase2DataError(f"Unsupported IMD time units: {time_units!r}.")
        origin_text = re.search(r"\d{4}-\d{2}-\d{2}", time_units)
        if origin_text is None:
            raise Phase2DataError(f"Unsupported IMD time origin: {time_units!r}.")
        origin = datetime.strptime(origin_text.group(0), "%Y-%m-%d")
        unit = match.group(1)
        multiplier = 86400 if unit == "days" else 3600
        time_values = np.asarray(time_variable[:], dtype=float)
        if time_values.size != len(series) or not np.isfinite(time_values).all():
            raise Phase2DataError("IMD time coordinates do not match the rainfall array.")
        dates = [
            origin + timedelta(seconds=float(value) * multiplier)
            for value in time_values
        ]
    finally:
        dataset.close()

    missing_mask = ~np.isfinite(series) | (series == fill_value)
    values = series.copy()
    values[missing_mask] = np.nan
    frame = pd.DataFrame({"date": pd.to_datetime(dates), "rainfall_mm": values})
    if frame.empty or frame["date"].dt.year.ne(year).any():
        raise Phase2DataError(f"IMD rainfall timestamps do not match requested year {year}.")
    if frame["date"].duplicated().any() or frame["date"].diff().dropna().ne(
        pd.Timedelta(days=1)
    ).any():
        raise Phase2DataError("IMD rainfall timestamps are not unique consecutive daily values.")
    if frame["rainfall_mm"].dropna().lt(0).any():
        raise Phase2DataError("IMD rainfall contains negative values outside its fill value.")
    valid = frame["rainfall_mm"].dropna()
    summary = {
        "row_count": int(len(frame)),
        "valid_days": int(valid.size),
        "missing_days": int(frame["rainfall_mm"].isna().sum()),
        "start": frame["date"].min().date().isoformat(),
        "end": frame["date"].max().date().isoformat(),
        "minimum_mm_day": float(valid.min()) if not valid.empty else None,
        "maximum_mm_day": float(valid.max()) if not valid.empty else None,
        "mean_mm_day": float(valid.mean()) if not valid.empty else None,
        "fill_value": fill_value,
        "grid_cell_center": {
            "latitude": cell_latitude,
            "longitude": cell_longitude,
        },
        "reference_coordinate": {"latitude": latitude, "longitude": longitude},
        "nearest_cell_offset_degrees": {
            "latitude": cell_latitude - latitude,
            "longitude": cell_longitude - longitude,
        },
        "crs": "Longitude/latitude in degrees; source datum and authority CRS are not stated.",
        "units": "mm/day",
        "time_units": time_units,
    }
    return frame, metadata, summary

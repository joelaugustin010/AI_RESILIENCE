"""Acquire and inventory public datasets for the Phase 2 data foundation."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "experimental"
REGISTER_PATH = ROOT / "data" / "reference" / "DATA_PROVENANCE_REGISTER.json"
USER_AGENT = "AI_RESILIENCE data foundation research (read-only public dataset retrieval)"
NWDP_RESOURCES = (
    {
        "dataset_id": "nwdp_cwc_rainfall_2021_2025",
        "resource_id": "654dd5af-ec2c-4439-a8a5-f9bf5d61ab74",
        "source_publisher": "Central Water Commission (CWC), served by NWIC/NWDP",
        "local_comparison": "data/raw/kerala.csv",
    },
    {
        "dataset_id": "nwdp_manual_rainfall_1991_2020",
        "resource_id": "ceb9ffcf-927b-4b34-8ab5-6c3098dd95a9",
        "source_publisher": "Kerala Surface Water Department, served by NWIC/NWDP",
        "local_comparison": "data/raw/rainfall_manual_hr_kerala-sw_kl_1991_2020.csv",
    },
    {
        "dataset_id": "nwdp_manual_river_level_2021_2025",
        "resource_id": "fe95a85e-142d-4acf-83fc-24499afc546b",
        "source_publisher": "Kerala Surface Water Department, served by NWIC/NWDP",
        "local_comparison": "data/raw/rwl_manual_hr_kerala_sw_031_2021_2025.csv",
    },
    {
        "dataset_id": "nwdp_telemetry_river_level_2021_2025",
        "resource_id": "a6de190e-40b6-484b-ad4c-a9f811f061ba",
        "source_publisher": "Kerala Surface Water Department, served by NWIC/NWDP",
        "local_comparison": "data/raw/rwl_tel_hr_kerala_sw_031_2021_2025.csv",
    },
)
NASA_PARAMETERS = ("PRECTOTCORR", "T2M", "T2M_MAX", "T2M_MIN", "WS10M")
IMD_YEARS = (2018, 2021, 2024)
OSM_BOUNDS = (9.8934161, 76.2373589, 10.0497693, 76.3400293)
INVENTORY_EXTENSIONS = {
    ".csv",
    ".dly",
    ".dwg",
    ".geojson",
    ".json",
    ".nc",
    ".pdf",
    ".png",
    ".tif",
    ".txt",
    ".xlsx",
    ".zip",
}
BROWSER_PROFILE_DIRECTORY_NAMES = {
    "browser_profile",
    "browser_cache",
    "chrome_profile",
    "chromium_profile",
    "edge_pdf_profile",
    "firefox_profile",
}
LOCAL_MACHINE_SUFFIX_PATTERN = re.compile(
    r"-(?:LAPTOP|DESKTOP|WORKSTATION)-[A-Z0-9]{6,}(?=\.|$)",
    re.IGNORECASE,
)
EXAMPLE_INPUT_NAMES = {
    "air_pollution_data.csv",
    "compound_disaster_data.csv",
    "disaster_probability_data.csv",
    "hospital_vulnerability_data.csv",
}


class AcquisitionError(RuntimeError):
    """Raised when a source cannot be retrieved or structurally validated."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    """Hash a file incrementally so large local rasters do not load into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _request_bytes(url: str, *, data: bytes | None = None, timeout: int = 120) -> tuple[bytes, dict[str, str]]:
    headers = {"User-Agent": USER_AGENT}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    for attempt in range(3):
        request = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read(), {
                    key.lower(): value for key, value in response.headers.items()
                }
        except OSError as exc:
            if attempt == 2:
                raise AcquisitionError(
                    f"Public source request failed after three attempts: {url}: {exc}"
                ) from exc
            time.sleep(2**attempt)
    raise AcquisitionError(f"Public source request failed: {url}")


def _save_snapshot(basename: str, content: bytes) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    path = RAW / basename
    if path.exists():
        if _sha256(path.read_bytes()) == _sha256(content):
            return path
        suffix = _utc_now().strftime("%Y%m%dT%H%M%SZ")
        path = path.with_name(f"{path.stem}_{suffix}{path.suffix}")
    path.write_bytes(content)
    return path


def _write_sidecar(path: Path, metadata: dict[str, Any]) -> Path:
    sidecar = path.with_name(path.name + ".metadata.json")
    sidecar.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return sidecar


def _tabular_quality(payload: bytes) -> dict[str, Any]:
    frame = pd.read_csv(io.BytesIO(payload), low_memory=False)
    result: dict[str, Any] = {
        "rows": int(len(frame)),
        "columns": [str(column) for column in frame.columns],
        "missing_values_by_column": {
            str(column): int(count)
            for column, count in frame.isna().sum().items()
            if count
        },
    }
    station_column = next(
        (column for column in frame.columns if str(column).strip().casefold() == "station"),
        None,
    )
    timestamp_column = next(
        (
            column
            for column in frame.columns
            if str(column).strip().casefold() == "data acquisition time"
        ),
        None,
    )
    measurement_column = next(
        (
            column
            for column in frame.columns
            if any(
                marker in str(column).casefold()
                for marker in ("rainfall (mm)", "water level", "river water level")
            )
        ),
        None,
    )
    if station_column is not None:
        result["station_count"] = int(frame[station_column].nunique(dropna=True))
    if timestamp_column is not None:
        times = pd.to_datetime(frame[timestamp_column], errors="coerce", dayfirst=True)
        valid_times = times.dropna()
        result["invalid_timestamp_rows"] = int(times.isna().sum())
        result["observed_start"] = valid_times.min().isoformat() if not valid_times.empty else None
        result["observed_end"] = valid_times.max().isoformat() if not valid_times.empty else None
        if station_column is not None and measurement_column is not None:
            values = pd.to_numeric(frame[measurement_column], errors="coerce")
            keys = pd.DataFrame(
                {
                    "station": frame[station_column].astype("string").str.strip(),
                    "timestamp": times,
                    "value": values,
                }
            ).dropna(subset=["station", "timestamp", "value"])
            sizes = keys.groupby(["station", "timestamp"], dropna=False).size()
            distinct = keys.groupby(["station", "timestamp"], dropna=False)["value"].nunique()
            duplicate = sizes.gt(1)
            result["invalid_measurement_rows"] = int(values.isna().sum())
            result["duplicate_station_time_groups"] = int(duplicate.sum())
            result["conflicting_station_time_groups"] = int(
                (duplicate & distinct.gt(1)).sum()
            )
    return result


def _local_comparison(path: Path, downloaded: bytes, downloaded_metadata: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return {"path": path.as_posix(), "available": False}
    local_bytes = path.read_bytes()
    comparison: dict[str, Any] = {
        "path": path.as_posix(),
        "available": True,
        "same_sha256": _sha256(local_bytes) == _sha256(downloaded),
        "local_bytes": len(local_bytes),
        "downloaded_bytes": len(downloaded),
        "local_sha256": _sha256(local_bytes),
        "same_sha256_after_crlf_to_lf_normalization": (
            local_bytes.replace(b"\r\n", b"\n") == downloaded.replace(b"\r\n", b"\n")
        ),
    }
    try:
        local_qa = _tabular_quality(local_bytes)
        comparison["local_rows"] = local_qa["rows"]
        comparison["local_observed_start"] = local_qa.get("observed_start")
        comparison["local_observed_end"] = local_qa.get("observed_end")
        comparison["local_duplicate_station_time_groups"] = local_qa.get(
            "duplicate_station_time_groups"
        )
        comparison["local_conflicting_station_time_groups"] = local_qa.get(
            "conflicting_station_time_groups"
        )
    except (ValueError, pd.errors.ParserError, UnicodeError) as exc:
        comparison["local_parse_error"] = str(exc)
    comparison["downloaded_rows"] = downloaded_metadata.get("rows")
    comparison["downloaded_observed_start"] = downloaded_metadata.get("observed_start")
    comparison["downloaded_observed_end"] = downloaded_metadata.get("observed_end")
    comparison["downloaded_conflicting_station_time_groups"] = downloaded_metadata.get(
        "conflicting_station_time_groups"
    )
    return comparison


def _nwdp_acquisition(resource_config: dict[str, str]) -> dict[str, Any]:
    resource_id = resource_config["resource_id"]
    api_url = "https://nwdp.nwic.gov.in/api/3/action/resource_show?" + urllib.parse.urlencode(
        {"id": resource_id}
    )
    api_payload, _ = _request_bytes(api_url)
    resource_response = json.loads(api_payload)
    if resource_response.get("success") is not True:
        raise AcquisitionError(f"NWDP resource metadata lookup failed for {resource_id}.")
    resource = resource_response["result"]
    package_url = (
        "https://nwdp.nwic.gov.in/api/3/action/package_show?"
        + urllib.parse.urlencode({"id": resource["package_id"]})
    )
    package_payload, _ = _request_bytes(package_url)
    package_response = json.loads(package_payload)
    if package_response.get("success") is not True:
        raise AcquisitionError(f"NWDP package metadata lookup failed for {resource_id}.")
    package = package_response["result"]
    source_url = resource.get("url")
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise AcquisitionError(f"NWDP returned no HTTPS source URL for {resource_id}.")
    payload, response_headers = _request_bytes(source_url, timeout=180)
    quality = _tabular_quality(payload)
    source_md5 = hashlib.md5(payload).hexdigest()  # NWDP publishes an MD5 resource hash.
    reported_md5 = resource.get("hash")
    status = "source_md5_match" if source_md5 == reported_md5 else "source_md5_mismatch"
    acquired_at = _utc_now()
    stem = re.sub(r"[^a-z0-9]+", "_", resource_config["dataset_id"].casefold()).strip("_")
    path = _save_snapshot(f"{stem}.csv", payload)
    metadata: dict[str, Any] = {
        "dataset_id": resource_config["dataset_id"],
        "publisher": resource_config["source_publisher"],
        "resource_title": resource.get("name"),
        "source_url": source_url,
        "catalog_url": f"https://nwdp.nwic.gov.in/dataset/{package['name']}/resource/{resource_id}",
        "retrieved_at_utc": acquired_at.isoformat(),
        "resource_created": resource.get("created"),
        "resource_last_modified": resource.get("last_modified"),
        "package_metadata_modified": package.get("metadata_modified"),
        "format": resource.get("format"),
        "license": package.get("license_title") or resource.get("license_title") or "Not stated in API fields",
        "license_id": package.get("license_id") or resource.get("license_id"),
        "source_md5": source_md5,
        "portal_md5": reported_md5,
        "source_hash_status": status,
        "portal_size_bytes": resource.get("size"),
        "download_size_bytes": len(payload),
        "portal_datastore_active": resource.get("datastore_active"),
        "portal_datastore_contains_all_records_of_source_file": resource.get(
            "datastore_contains_all_records_of_source_file"
        ),
        "content_type": response_headers.get("content-type"),
        "local_snapshot": path.relative_to(ROOT).as_posix(),
        "sha256": _sha256(payload),
        "temporal_coverage": quality.get("observed_start"),
        "temporal_coverage_end": quality.get("observed_end"),
        "crs": "Not supplied in the CSV/resource API; station coordinates are not promoted to validated geometries.",
        "quality": quality,
    }
    comparison_path = ROOT / resource_config["local_comparison"]
    metadata["comparison_with_existing_project_file"] = _local_comparison(
        comparison_path,
        payload,
        quality,
    )
    sidecar = _write_sidecar(path, metadata)
    metadata["metadata_sidecar"] = sidecar.relative_to(ROOT).as_posix()
    return metadata


def _nasa_acquisition() -> dict[str, Any]:
    params = {
        "parameters": ",".join(NASA_PARAMETERS),
        "community": "SB",
        "longitude": "76.27",
        "latitude": "9.93",
        "start": "20200101",
        "end": "20250101",
        "format": "JSON",
        "time-standard": "UTC",
    }
    url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urllib.parse.urlencode(params)
    payload, headers = _request_bytes(url)
    response = json.loads(payload)
    header = response.get("header", {})
    if header.get("time_standard") != "UTC":
        raise AcquisitionError("NASA POWER response did not confirm the requested UTC time standard.")
    parameters = response.get("parameters", {})
    missing_parameters = sorted(set(NASA_PARAMETERS) - set(parameters))
    if missing_parameters:
        raise AcquisitionError("NASA POWER response omitted parameter metadata: " + ", ".join(missing_parameters))
    path = _save_snapshot("nasa_power_kochi_center_daily_20200101_20250101.json", payload)
    acquired_at = _utc_now()
    rows_by_parameter = {
        name: len(values)
        for name, values in response.get("properties", {}).get("parameter", {}).items()
    }
    dates = sorted(
        response.get("properties", {}).get("parameter", {}).get(NASA_PARAMETERS[0], {}).keys()
    )
    metadata = {
        "dataset_id": "nasa_power_kochi_center_daily_2020_2025",
        "publisher": "NASA Langley Research Center POWER Project",
        "source_url": url,
        "retrieved_at_utc": acquired_at.isoformat(),
        "product": header.get("title"),
        "api_version": header.get("api", {}).get("version"),
        "source_systems": header.get("sources"),
        "community": "SB",
        "requested_point_longitude_latitude": [76.27, 9.93],
        "returned_point_and_elevation": response.get("geometry", {}).get("coordinates"),
        "coordinate_interpretation": "Fixed contextual request point, not a verified station or geocoded user scenario.",
        "start": header.get("start"),
        "end_inclusive": header.get("end"),
        "time_standard": header.get("time_standard"),
        "parameters": parameters,
        "rows_by_parameter": rows_by_parameter,
        "date_count": len(dates),
        "first_date": dates[0] if dates else None,
        "last_date": dates[-1] if dates else None,
        "fill_value": header.get("fill_value"),
        "content_type": headers.get("content-type"),
        "local_snapshot": path.relative_to(ROOT).as_posix(),
        "sha256": _sha256(payload),
        "license": "NASA POWER public API; retain NASA POWER attribution and citation; confirm current NASA data-use terms before redistribution.",
        "resolution": "Daily point service using source-native resolution; this is gridded/model-derived information, not an in-situ station record.",
        "limitation": "No station validation, local flood threshold, or event-impact linkage. The fixed point is not joined to the invalid provisional Kochi polygon.",
    }
    sidecar = _write_sidecar(path, metadata)
    metadata["metadata_sidecar"] = sidecar.relative_to(ROOT).as_posix()
    return metadata


def _imd_rainfall_acquisition(year: int) -> dict[str, Any]:
    endpoint = "https://www.imdpune.gov.in/cmpg/Griddata/RF25.php"
    payload, headers = _request_bytes(
        endpoint,
        data=urllib.parse.urlencode({"RF25": str(year)}).encode("ascii"),
        timeout=240,
    )
    if not payload.startswith((b"CDF\x01", b"CDF\x02", b"CDF\x05")):
        raise AcquisitionError("IMD annual rainfall response was not a NetCDF file.")
    path = _save_snapshot(f"imd_daily_gridded_rainfall_{year}_025deg.nc", payload)
    metadata: dict[str, Any] = {
        "dataset_id": f"imd_daily_gridded_rainfall_{year}",
        "publisher": "India Meteorological Department, Climate Research and Services, Pune",
        "source_url": "https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html",
        "download_endpoint": endpoint,
        "retrieval_method": f"Public year-selection form POST (RF25={year}); no authentication or access-control workaround used.",
        "retrieved_at_utc": _utc_now().isoformat(),
        "publication_date": f"Annual file for {year}; the source page describes the 0.25 degree product as available through 2024.",
        "format": "NetCDF classic",
        "signature": payload[:4].decode("ascii", errors="replace"),
        "download_content_type": headers.get("content-type"),
        "download_content_disposition": headers.get("content-disposition"),
        "year": year,
        "license": "No explicit dataset reuse licence found on the product page; page requests citation of Pai et al. (2014). Retained as a source snapshot; redistribution/reuse terms need confirmation.",
        "page_declared_coverage": "India, 1901–2024; 0.25 x 0.25 degree daily grid; rainfall in mm.",
        "crs": "Longitude/latitude grid; no projected CRS stated on the product page.",
        "sha256": _sha256(payload),
        "download_size_bytes": len(payload),
        "local_snapshot": path.relative_to(ROOT).as_posix(),
        "quality_status": "Downloaded and format signature checked; variable, dimensions, and values are inspected by the validation command.",
    }
    try:
        from scipy.io import netcdf_file

        with netcdf_file(io.BytesIO(payload), mode="r", mmap=False) as dataset:
            observed_dimensions: dict[str, int] = {}
            for variable in dataset.variables.values():
                for axis, name in enumerate(variable.dimensions):
                    observed_dimensions[name] = max(
                        observed_dimensions.get(name, 0),
                        int(variable.shape[axis]),
                    )
            metadata["dimensions"] = {
                name: {
                    "declared_length": None if size is None else int(size),
                    "observed_length": observed_dimensions.get(name, 0),
                }
                for name, size in dataset.dimensions.items()
            }
            variable_info: dict[str, dict[str, Any]] = {}
            for name, variable in dataset.variables.items():
                item: dict[str, Any] = {
                    "dimensions": list(variable.dimensions),
                    "shape": list(variable.shape),
                    "dtype": str(variable.data.dtype),
                }
                for attr in ("units", "long_name", "missing_value", "_FillValue"):
                    if hasattr(variable, attr):
                        value = getattr(variable, attr)
                        item[attr] = value.item() if hasattr(value, "item") else str(value)
                variable_info[name] = item
            metadata["variables"] = variable_info
            for candidate in ("LONGITUDE", "LATITUDE", "longitude", "latitude"):
                variable = dataset.variables.get(candidate)
                if variable is not None:
                    values = variable[:]
                    metadata.setdefault("coordinate_axes", {})[candidate] = {
                        "count": int(values.size),
                        "minimum": float(values.min()),
                        "maximum": float(values.max()),
                    }
            rainfall = dataset.variables.get("RAINFALL")
            if rainfall is not None:
                values = rainfall[:]
                fill_value = getattr(rainfall, "missing_value", None)
                if fill_value is None:
                    fill_value = getattr(rainfall, "_FillValue", -999.0)
                valid = values != fill_value
                valid_values = values[valid]
                metadata["rainfall_value_quality"] = {
                    "cells_total": int(values.size),
                    "fill_value": float(fill_value),
                    "missing_cell_days": int((~valid).sum()),
                    "valid_cell_days": int(valid.sum()),
                    "valid_min_mm": float(valid_values.min()) if valid_values.size else None,
                    "valid_max_mm": float(valid_values.max()) if valid_values.size else None,
                    "negative_nonmissing_cell_days": int((valid_values < 0).sum()),
                    "zero_nonmissing_cell_days": int((valid_values == 0).sum()),
                }
            time_axis = dataset.variables.get("TIME")
            if time_axis is not None and hasattr(time_axis, "units"):
                time_units = getattr(time_axis, "units")
                if isinstance(time_units, bytes):
                    time_units = time_units.decode("ascii", errors="replace")
                match = re.match(r"days since (\d{4}-\d{2}-\d{2})", str(time_units))
                if match:
                    origin = datetime.strptime(match.group(1), "%Y-%m-%d")
                    time_values = time_axis[:]
                    metadata["observed_date_range"] = {
                        "start": (origin + pd.to_timedelta(float(time_values.min()), unit="D")).date().isoformat(),
                        "end": (origin + pd.to_timedelta(float(time_values.max()), unit="D")).date().isoformat(),
                        "time_units": str(time_units),
                    }
    except (ImportError, OSError, ValueError, TypeError) as exc:
        metadata["netcdf_inspection_error"] = str(exc)
    sidecar = _write_sidecar(path, metadata)
    metadata["metadata_sidecar"] = sidecar.relative_to(ROOT).as_posix()
    return metadata


def _usgs_acquisition() -> dict[str, Any]:
    params = {
        "format": "geojson",
        "starttime": "1900-01-01",
        "endtime": _utc_now().date().isoformat(),
        "minlatitude": "8",
        "maxlatitude": "12",
        "minlongitude": "74",
        "maxlongitude": "79",
        "minmagnitude": "0",
        "orderby": "time-asc",
    }
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + urllib.parse.urlencode(params)
    payload, headers = _request_bytes(url)
    response = json.loads(payload)
    features = response.get("features")
    if response.get("type") != "FeatureCollection" or not isinstance(features, list):
        raise AcquisitionError("USGS response is not a valid GeoJSON FeatureCollection.")
    path = _save_snapshot("usgs_earthquakes_kerala_bbox_1900_present_m0.geojson", payload)
    metadata = {
        "dataset_id": "usgs_earthquake_catalog_kerala_query",
        "publisher": "U.S. Geological Survey Earthquake Hazards Program",
        "source_url": url,
        "retrieved_at_utc": _utc_now().isoformat(),
        "query_bounds": {"min_lat": 8, "max_lat": 12, "min_lon": 74, "max_lon": 79},
        "time_range": {"start": "1900-01-01", "end": params["endtime"]},
        "minimum_magnitude": 0,
        "crs": "GeoJSON longitude/latitude (WGS 84)",
        "feature_count": len(features),
        "response_generated_epoch_ms": response.get("metadata", {}).get("generated"),
        "response_status": response.get("metadata", {}).get("status"),
        "content_type": headers.get("content-type"),
        "local_snapshot": path.relative_to(ROOT).as_posix(),
        "sha256": _sha256(payload),
        "license": "USGS public data; retain source attribution and verify dataset-specific terms for redistribution.",
        "interpretation": "The current query returned no catalog events at magnitude >= 0 in the stated box and period. This is not evidence of zero earthquake hazard or a complete local seismicity catalogue.",
    }
    sidecar = _write_sidecar(path, metadata)
    metadata["metadata_sidecar"] = sidecar.relative_to(ROOT).as_posix()
    return metadata


def _osm_acquisition() -> dict[str, Any]:
    south, west, north, east = OSM_BOUNDS
    query = (
        '[out:json][timeout:60];way["highway"]'
        f"({south},{west},{north},{east});out geom;"
    )
    url = "https://overpass-api.de/api/interpreter?" + urllib.parse.urlencode(
        {"data": query}
    )
    payload, headers = _request_bytes(url, timeout=180)
    response = json.loads(payload)
    elements = response.get("elements")
    if not isinstance(elements, list):
        raise AcquisitionError("Overpass response does not contain an elements array.")
    class_counts: Counter[str] = Counter()
    invalid_coordinates = 0
    for element in elements:
        tags = element.get("tags", {})
        if isinstance(tags.get("highway"), str):
            class_counts[tags["highway"]] += 1
        geometry = element.get("geometry", [])
        if len(geometry) < 2:
            invalid_coordinates += 1
        for point in geometry:
            lat, lon = point.get("lat"), point.get("lon")
            if (
                not isinstance(lat, (int, float))
                or not isinstance(lon, (int, float))
                or not math.isfinite(lat)
                or not math.isfinite(lon)
                or not (-90 <= lat <= 90 and -180 <= lon <= 180)
            ):
                invalid_coordinates += 1
    path = _save_snapshot("openstreetmap_roads_provisional_kochi_bounds.json", payload)
    metadata = {
        "dataset_id": "openstreetmap_roads_kochi_bbox",
        "publisher": "OpenStreetMap contributors",
        "source_url": url,
        "retrieved_at_utc": _utc_now().isoformat(),
        "osm_base_timestamp": response.get("osm3s", {}).get("timestamp_osm_base"),
        "query_bounds": {"south": south, "west": west, "north": north, "east": east},
        "bounds_basis": "Observed extent of the existing 2022 DataMeet ward snapshot; not an authoritative Kochi Corporation boundary.",
        "geometry_type": "OSM ways with highway tag, returned as JSON node geometries",
        "crs": "WGS 84 latitude/longitude per OSM API convention",
        "feature_count": len(elements),
        "highway_feature_counts": dict(sorted(class_counts.items())),
        "ways_with_less_than_two_points": sum(
            1
            for element in elements
            if len(element.get("geometry", [])) < 2
        ),
        "invalid_coordinate_count": invalid_coordinates,
        "content_type": headers.get("content-type"),
        "local_snapshot": path.relative_to(ROOT).as_posix(),
        "sha256": _sha256(payload),
        "license": "Open Database License (ODbL) 1.0; attribution to OpenStreetMap contributors required; share-alike obligations may apply to derived databases.",
        "limitation": "Completeness, positional accuracy, road access/condition, and temporal currency are not independently validated. Not used for routing, exposure, or hospital access claims.",
    }
    sidecar = _write_sidecar(path, metadata)
    metadata["metadata_sidecar"] = sidecar.relative_to(ROOT).as_posix()
    return metadata


def acquire_all() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for resource in NWDP_RESOURCES:
        results.append(_nwdp_acquisition(resource))
    results.extend(_imd_rainfall_acquisition(year) for year in IMD_YEARS)
    results.extend([_nasa_acquisition(), _usgs_acquisition(), _osm_acquisition()])
    return results


def _is_browser_profile_path(path: Path) -> bool:
    parts = {part.casefold() for part in path.parts}
    return bool(parts.intersection(BROWSER_PROFILE_DIRECTORY_NAMES))


def _is_local_machine_artifact(path: Path) -> bool:
    return bool(LOCAL_MACHINE_SUFFIX_PATTERN.search(path.name))


def _asset_status(
    path: Path,
    sidecar: Path | None,
    metadata: dict[str, Any] | None = None,
    observed_sha256: str | None = None,
) -> str:
    if path.name in EXAMPLE_INPUT_NAMES:
        return "unverified_example_input_not_for_assessment"

    parts = {part.casefold() for part in path.parts}
    metadata_unreadable = sidecar is not None and metadata is None
    metadata = metadata or {}
    dataset_id = str(metadata.get("dataset_id", "")).casefold()
    reuse_status = str(metadata.get("reuse_status", "")).upper()
    metadata_hash_matches = bool(
        observed_sha256
        and str(metadata.get("sha256", "")).casefold() == observed_sha256.casefold()
    )
    acquired_record = metadata_hash_matches and reuse_status.startswith("ACQUIRED")
    structurally_validated = (
        acquired_record
        and "STRUCTURALLY_VALIDATED" in reuse_status
        and isinstance(metadata.get("validation"), dict)
        and bool(metadata["validation"])
    )

    is_ibtracs = "ibtracs" in parts or "ibtracs" in path.name.casefold() or "ibtracs" in dataset_id
    if is_ibtracs:
        rights_text = " ".join(
            str(metadata.get(field, ""))
            for field in ("license", "licence", "rights", "license_status", "rights_status", "reuse_status")
        ).casefold()
        unresolved_terms = ("unresolved", "unknown", "no dataset-level", "not found", "not stated", "unclear")
        rights_unresolved = not rights_text.strip() or any(term in rights_text for term in unresolved_terms)
        if rights_unresolved:
            if structurally_validated:
                return "acquired_validated_not_integrated_rights_unresolved"
            if acquired_record:
                return "acquired_not_integrated_rights_unresolved"
            return "present_not_integrated_rights_unresolved"

    is_ghcn = (
        "ghcn" in parts
        or path.name.casefold() == "ghcnd-stations.txt"
        or (path.suffix.casefold() == ".dly" and path.parent.name.casefold() in {"ghcn", "ghcnd"})
    )
    if is_ghcn:
        rights_text = " ".join(
            str(metadata.get(field, ""))
            for field in ("license", "licence", "rights", "license_status", "rights_status", "reuse_status")
        ).casefold()
        rights_review_required = any(
            term in rights_text
            for term in ("review", "no explicit", "not found", "unknown", "unresolved")
        )
        if structurally_validated and rights_review_required:
            return "acquired_structurally_validated_rights_review_required_not_integrated"
        if acquired_record and rights_review_required:
            return "acquired_rights_review_required_not_integrated"
        if acquired_record:
            return "acquired_not_integrated"
        return "present_inventory_only_not_integrated_provenance_unverified"

    if "experimental" in parts:
        return "experimental_or_research_snapshot"
    if sidecar is None:
        return "provenance_sidecar_not_found"
    if metadata_unreadable:
        return "provenance_sidecar_unreadable"
    return "sidecar_available_requires_dataset_specific_suitability_review"


def build_register(root: Path = ROOT) -> dict[str, Any]:
    """Inventory data assets without treating missing metadata as verified."""
    assets: list[dict[str, Any]] = []
    for base in (root / "data" / "raw", root / "data" / "processed", root / "data" / "reference"):
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if (
                not path.is_file()
                or _is_browser_profile_path(path)
                or _is_local_machine_artifact(path)
            ):
                continue
            if path.suffix.casefold() == ".png" and "spatial_layers" not in {
                part.casefold() for part in path.parts
            }:
                continue
            if path.name.endswith(".metadata.json") or path.suffix.lower() not in INVENTORY_EXTENSIONS:
                continue
            if path.name in {"DATA_PROVENANCE_REGISTER.json"}:
                continue
            if path.suffix.lower() == ".json" and "historical_flood_events" not in path.name and "data" not in path.parts:
                continue
            relative = path.relative_to(root).as_posix()
            sidecar = path.with_name(path.name + ".metadata.json")
            if not sidecar.is_file() and path.suffix.casefold() in {".png", ".jpg", ".jpeg", ".webp"}:
                stem_sidecar = path.with_suffix(".metadata.json")
                if stem_sidecar.is_file():
                    sidecar = stem_sidecar
            if not sidecar.is_file():
                sidecar = None
                metadata = None
            else:
                try:
                    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    metadata = None
            sidecar_relative = sidecar.relative_to(root).as_posix() if sidecar is not None else None
            observed_sha256 = _sha256_file(path)
            assets.append(
                {
                    "path": relative,
                    "bytes": path.stat().st_size,
                    "sha256": observed_sha256,
                    "format": path.suffix.lower().lstrip("."),
                    "role": "raw" if "raw" in path.parts else "processed" if "processed" in path.parts else "reference",
                    "provenance_sidecar": sidecar_relative,
                    "provenance_status": _asset_status(path, sidecar, metadata, observed_sha256),
                }
            )
    return {
        "register_version": 1,
        "generated_at_utc": _utc_now().isoformat(),
        "repository": "joelaugustin010/AI_RESILIENCE",
        "assets": assets,
        "asset_count": len(assets),
        "assets_without_sidecars": sum(not asset["provenance_sidecar"] for asset in assets),
        "policy": "Checksums establish byte identity only, not source identity, licence, accuracy, completeness, or suitability.",
    }


def write_register(root: Path = ROOT) -> Path:
    register = build_register(root)
    path = root / "data" / "reference" / "DATA_PROVENANCE_REGISTER.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(register, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(        "acquire",
        "acquire-imd", "inventory"),
        help="Retrieve public snapshots, or rebuild the local checksum inventory.",
    )
    parser.add_argument("--imd-year", type=int, choices=IMD_YEARS)
    args = parser.parse_args()
    if args.action == "acquire":
        for result in acquire_all():
            print(
                json.dumps(
                    {
                        "dataset_id": result["dataset_id"],
                        "local_snapshot": result["local_snapshot"],
                        "sha256": result["sha256"],
                        "status": result.get("source_hash_status", result.get("quality_status", "retrieved")),
                    },
                    ensure_ascii=False,
                )
            )
    elif args.action == "acquire-imd":
        years = (args.imd_year,) if args.imd_year is not None else IMD_YEARS
        for result in (_imd_rainfall_acquisition(year) for year in years):
            print(
                json.dumps(
                    {
                        "dataset_id": result["dataset_id"],
                        "local_snapshot": result["local_snapshot"],
                        "sha256": result["sha256"],
                        "quality": result.get("rainfall_value_quality"),
                    },
                    ensure_ascii=False,
                )
            )
    register_path = write_register()
    print(f"Inventory: {register_path.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()

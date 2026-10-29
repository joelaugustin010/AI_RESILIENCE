"""Acquire a bounded USGS ComCat earthquake catalogue around Kochi and audit it descriptively.

This is a regional seismicity inventory, not a local ground-motion, building-damage,
or earthquake-probability model. Raw GeoJSON responses and the normalized CSV are
kept in a short-lived private workflow artifact rather than committed to Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


API_ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"
KOCHI_REFERENCE = {"latitude": 9.9312, "longitude": 76.2673, "label": "approximate Kochi city-centre screening point"}
START_YEAR = 1970
WINDOW_YEARS = 5
MIN_MAGNITUDE = 2.5
RADIUS_KM = 1000
MAX_EVENTS_PER_WINDOW = 20000
MAX_RESPONSE_BYTES = 50 * 1024 * 1024
ALLOWED_HOST = "earthquake.usgs.gov"


def iter_windows(start_year: int = START_YEAR, end_date: date | None = None, window_years: int = WINDOW_YEARS):
    """Yield non-overlapping inclusive UTC date windows."""
    end_date = end_date or datetime.now(timezone.utc).date()
    year = start_year
    while year <= end_date.year:
        window_start = date(year, 1, 1)
        window_end_year = min(year + window_years - 1, end_date.year)
        window_end = end_date if window_end_year == end_date.year else date(window_end_year, 12, 31)
        yield {
            "starttime": f"{window_start.isoformat()}T00:00:00",
            "endtime": f"{window_end.isoformat()}T23:59:59",
        }
        year = window_end_year + 1


def haversine_km(latitudes, longitudes, target_lat: float = KOCHI_REFERENCE["latitude"], target_lon: float = KOCHI_REFERENCE["longitude"]):
    """Great-circle distance in km, used only for regional proximity screening."""
    lat = np.radians(np.asarray(latitudes, dtype=float))
    lon = np.radians(np.asarray(longitudes, dtype=float))
    tlat = np.radians(target_lat)
    tlon = np.radians(target_lon)
    dlat = lat - tlat
    dlon = lon - tlon
    a = np.sin(dlat / 2) ** 2 + np.cos(tlat) * np.cos(lat) * np.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def normalize_feature(feature: dict, window: dict) -> dict:
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    lon = coordinates[0] if len(coordinates) >= 2 else None
    lat = coordinates[1] if len(coordinates) >= 2 else None
    depth = coordinates[2] if len(coordinates) >= 3 else None
    timestamp = properties.get("time")
    if isinstance(timestamp, (int, float)):
        time_utc = datetime.fromtimestamp(timestamp / 1000.0, timezone.utc).isoformat()
    else:
        time_utc = None
    return {
        "event_id": feature.get("id") or properties.get("code"),
        "time_utc": time_utc,
        "latitude": lat,
        "longitude": lon,
        "depth_km": depth,
        "magnitude": properties.get("mag"),
        "magnitude_type": properties.get("magType"),
        "place": properties.get("place"),
        "event_url": properties.get("url"),
        "status": properties.get("status"),
        "tsunami_flag": properties.get("tsunami"),
        "significance": properties.get("sig"),
        "network": properties.get("net"),
        "event_type": properties.get("type"),
        "query_window_start": window["starttime"],
        "query_window_end": window["endtime"],
    }


def fetch_window(window: dict, output_path: Path) -> dict:
    params = {
        "format": "geojson",
        "starttime": window["starttime"],
        "endtime": window["endtime"],
        "latitude": KOCHI_REFERENCE["latitude"],
        "longitude": KOCHI_REFERENCE["longitude"],
        "maxradiuskm": RADIUS_KM,
        "minmagnitude": MIN_MAGNITUDE,
        "eventtype": "earthquake",
        "orderby": "time-asc",
        "limit": MAX_EVENTS_PER_WINDOW,
    }
    url = API_ENDPOINT + "?" + urlencode(params)
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST or parsed.path != "/fdsnws/event/1/query":
        raise ValueError("Earthquake query URL is outside the allowlisted USGS endpoint")
    request = Request(url, headers={"User-Agent": "AI-RESILIENCE-Research-Data-Acquisition/1.0", "Accept": "application/geo+json,application/json"})
    with urlopen(request, timeout=90) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != ALLOWED_HOST or final.path != "/fdsnws/event/1/query":
            raise ValueError("USGS request redirected outside the allowlisted endpoint")
        content_type = response.headers.get("Content-Type", "unknown")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeError(f"USGS response exceeded {MAX_RESPONSE_BYTES} bytes for {window}")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"USGS returned non-JSON content for {window}: {exc}") from exc
    metadata = payload.get("metadata") or {}
    if int(metadata.get("status", 200)) != 200:
        raise RuntimeError(f"USGS API status was not 200 for {window}")
    features = payload.get("features")
    if not isinstance(features, list):
        raise RuntimeError(f"USGS response has no GeoJSON features list for {window}")
    declared_count = int(metadata.get("count", len(features)))
    if declared_count != len(features):
        raise RuntimeError(f"USGS declared count {declared_count} does not match {len(features)} features for {window}")
    if declared_count >= MAX_EVENTS_PER_WINDOW:
        raise RuntimeError(f"USGS window reached the {MAX_EVENTS_PER_WINDOW}-event cap; split this window before using it")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(raw)
    return {
        "query_url": url,
        "window": window,
        "http_content_type": content_type,
        "api_count": declared_count,
        "file": str(output_path),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
    }, [normalize_feature(feature, window) for feature in features]


def build_audit_report(events: pd.DataFrame, windows: list[dict], query_config: dict) -> dict:
    required = {"event_id", "time_utc", "latitude", "longitude", "magnitude"}
    missing = sorted(required - set(events.columns))
    if missing:
        raise ValueError("Normalized earthquake table missing required field(s): " + ", ".join(missing))
    frame = events.copy()
    frame["time_parsed"] = pd.to_datetime(frame["time_utc"], errors="coerce", utc=True)
    frame["lat_num"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["lon_num"] = pd.to_numeric(frame["longitude"], errors="coerce")
    frame["mag_num"] = pd.to_numeric(frame["magnitude"], errors="coerce")
    frame["depth_num"] = pd.to_numeric(frame["depth_km"], errors="coerce") if "depth_km" in frame else np.nan
    coords_present = frame["lat_num"].notna() & frame["lon_num"].notna()
    coords_valid = coords_present & frame["lat_num"].between(-90, 90) & frame["lon_num"].between(-180, 180)
    frame["distance_to_kochi_km"] = np.nan
    if coords_valid.any():
        frame.loc[coords_valid, "distance_to_kochi_km"] = haversine_km(frame.loc[coords_valid, "lat_num"], frame.loc[coords_valid, "lon_num"])
    duplicate_ids = frame.duplicated(subset=["event_id"], keep=False) & frame["event_id"].notna()
    valid_times = frame["time_parsed"].dropna()
    valid_magnitudes = frame["mag_num"].dropna()
    valid_distances = frame.loc[coords_valid, "distance_to_kochi_km"].dropna()
    decade_counts = {}
    if not valid_times.empty:
        years = frame.loc[frame["time_parsed"].notna(), "time_parsed"].dt.year
        decades = (years // 10) * 10
        decade_counts = {str(int(k)) + "s": int(v) for k, v in decades.value_counts().sort_index().items()}
    magnitude_bins = {
        "<3.0": int((frame["mag_num"] < 3).sum()),
        "3.0-3.9": int(((frame["mag_num"] >= 3) & (frame["mag_num"] < 4)).sum()),
        "4.0-4.9": int(((frame["mag_num"] >= 4) & (frame["mag_num"] < 5)).sum()),
        "5.0-5.9": int(((frame["mag_num"] >= 5) & (frame["mag_num"] < 6)).sum()),
        ">=6.0": int((frame["mag_num"] >= 6).sum()),
        "missing": int(frame["mag_num"].isna().sum()),
    }
    distances = frame.loc[coords_valid].sort_values("distance_to_kochi_km")
    nearest_events = []
    for _, row in distances.head(25).iterrows():
        nearest_events.append({
            "event_id": str(row["event_id"]) if pd.notna(row["event_id"]) else None,
            "time_utc": row["time_parsed"].isoformat() if pd.notna(row["time_parsed"]) else None,
            "magnitude": float(row["mag_num"]) if pd.notna(row["mag_num"]) else None,
            "depth_km": float(row["depth_num"]) if pd.notna(row["depth_num"]) else None,
            "distance_km": float(row["distance_to_kochi_km"]),
            "place": str(row["place"]) if "place" in row and pd.notna(row["place"]) else None,
            "event_url": str(row["event_url"]) if "event_url" in row and pd.notna(row["event_url"]) else None,
        })
    return {
        "audit_version": 1,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "DESCRIPTIVE_REGIONAL_SEISMICITY_ONLY_NOT_VALIDATED_FOR_LOCAL_GROUND_SHAKING",
        "source": {
            "publisher": "USGS Earthquake Hazards Program, ComCat",
            "api_documentation": "https://earthquake.usgs.gov/fdsnws/event/1/",
            "query_config": query_config,
            "query_windows": windows,
            "event_count": int(len(frame)),
        },
        "data_quality": {
            "invalid_time_rows": int(frame["time_parsed"].isna().sum()),
            "missing_coordinate_rows": int((~coords_present).sum()),
            "out_of_range_coordinate_rows": int((coords_present & ~coords_valid).sum()),
            "missing_magnitude_rows": int(frame["mag_num"].isna().sum()),
            "duplicate_event_id_rows": int(duplicate_ids.sum()),
            "unique_event_ids": int(frame["event_id"].nunique(dropna=True)),
            "valid_time_range_utc": [valid_times.min().isoformat(), valid_times.max().isoformat()] if not valid_times.empty else None,
            "magnitude_range": [float(valid_magnitudes.min()), float(valid_magnitudes.max())] if not valid_magnitudes.empty else None,
            "events_by_decade": decade_counts,
            "magnitude_bins": magnitude_bins,
        },
        "kochi_proximity_screening": {
            "reference_point": KOCHI_REFERENCE,
            "query_radius_km": RADIUS_KM,
            "events_within_100_km": int((valid_distances <= 100).sum()),
            "events_within_300_km": int((valid_distances <= 300).sum()),
            "events_within_500_km": int((valid_distances <= 500).sum()),
            "events_within_1000_km": int((valid_distances <= 1000).sum()),
            "nearest_events": nearest_events,
            "interpretation": "Regional event proximity is not local ground-motion intensity, site amplification, building damage, or earthquake probability.",
        },
        "limitations": [
            "USGS ComCat is a multi-network global catalogue; completeness and location uncertainty vary by time, magnitude and contributing network.",
            "The 1,000 km query radius is a regional screening choice, not a municipal hazard boundary.",
            "Magnitude, depth and epicentre distance do not alone predict shaking or damage in Kochi.",
            "Site geology, local ground-motion models, building inventory, fragility and independent NCS/GSI evidence are required for consequence analysis.",
            "No events were deleted or deduplicated; duplicate event IDs are reported for review.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/external/earthquake_catalog"))
    parser.add_argument("--start-year", type=int, default=START_YEAR)
    args = parser.parse_args(argv)
    end_date = datetime.now(timezone.utc).date()
    windows = list(iter_windows(args.start_year, end_date))
    output_dir = args.output_dir
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    all_events = []
    window_manifests = []
    for index, window in enumerate(windows):
        raw_path = raw_dir / f"usgs_{window['starttime'][:4]}_{window['endtime'][:4]}.geojson"
        manifest, events = fetch_window(window, raw_path)
        window_manifests.append(manifest)
        all_events.extend(events)
        time.sleep(0.15)
    columns = ["event_id", "time_utc", "latitude", "longitude", "depth_km", "magnitude", "magnitude_type", "place", "event_url", "status", "tsunami_flag", "significance", "network", "event_type", "query_window_start", "query_window_end"]
    frame = pd.DataFrame(all_events, columns=columns)
    query_config = {
        "start_year": args.start_year,
        "end_date_utc": end_date.isoformat(),
        "min_magnitude": MIN_MAGNITUDE,
        "radius_km": RADIUS_KM,
        "reference_point": KOCHI_REFERENCE,
        "window_years": WINDOW_YEARS,
        "event_type": "earthquake",
        "raw_source_rows_preserved": True,
    }
    audit = build_audit_report(frame, window_manifests, query_config)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "earthquake_catalog.csv"
    frame.to_csv(csv_path, index=False)
    acquisition_manifest = {
        "acquisition_status": "DOWNLOADED_RAW_UNVALIDATED",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "api_endpoint": API_ENDPOINT,
        "query_config": query_config,
        "window_requests": window_manifests,
        "normalized_csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "normalized_csv_bytes": csv_path.stat().st_size,
        "source_terms_note": "USGS ComCat source attribution retained; verify applicable terms before redistribution or operational use.",
    }
    (output_dir / "earthquake_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    (output_dir / "acquisition_manifest.json").write_text(json.dumps(acquisition_manifest, indent=2) + "\n", encoding="utf-8")
    print(f"USGS regional earthquake catalogue: {len(frame)} event rows from {len(windows)} non-overlapping windows")
    print("Events within 100/300/500/1000 km:", audit["kochi_proximity_screening"]["events_within_100_km"], audit["kochi_proximity_screening"]["events_within_300_km"], audit["kochi_proximity_screening"]["events_within_500_km"], audit["kochi_proximity_screening"]["events_within_1000_km"])
    print("This is regional seismicity context, not a local shaking/damage prediction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

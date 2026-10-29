"""Acquire public, reproducible source datasets for the nine non-flood hazards.

Downloads source observations only; it does not fabricate labels or claim model training.
Run: python scripts/acquire_hazard_data.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path("data/external/hazards/raw")
MANIFEST = Path("reports/hazard_data_acquisition_manifest.json")
TODAY = date.today().isoformat()
USER_AGENT = "AI_RESILIENCE-student-research/1.0 (public dataset acquisition; attribution retained)"
TIMEOUT = 90


def fetch(name: str, url: str, *, headers: dict[str, str] | None = None) -> dict:
    """Download a public file and record provenance, checksum, and basic validation."""
    target = ROOT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    request_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    entry = {"file": str(target), "url": url, "retrieved_at": TODAY, "status": "FAILED"}
    try:
        req = Request(url, headers=request_headers)
        with urlopen(req, timeout=TIMEOUT) as response:
            data = response.read()
            content_type = response.headers.get("Content-Type", "")
            final_url = response.geturl()
        if len(data) < 100:
            raise ValueError(f"Response suspiciously small ({len(data)} bytes)")
        # Avoid saving an HTML error/login page under a data-file extension.
        prefix = data[:500].lstrip().lower()
        if ("text/html" in content_type.lower() or prefix.startswith(b"<!doctype html")
                or prefix.startswith(b"<html")):
            raise ValueError(f"Received HTML instead of data (Content-Type: {content_type})")
        target.write_bytes(data)
        entry.update({
            "status": "DOWNLOADED",
            "final_url": final_url,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "content_type": content_type,
        })
        if target.suffix.lower() == ".csv":
            with target.open("r", encoding="utf-8-sig", errors="replace", newline="") as stream:
                reader = csv.reader(stream)
                entry["header"] = next(reader, [])
                entry["approx_data_rows"] = max(sum(1 for _ in reader), 0)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        entry["error"] = f"{type(exc).__name__}: {exc}"
        print(f"[FAILED] {name}: {entry['error']}", file=sys.stderr)
    else:
        print(f"[OK] {name}: {entry['bytes']:,} bytes")
    return entry


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []

    # India-focused earthquake event observations; these are not a future-earthquake forecast.
    earthquake_url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + urlencode({
        "format": "csv", "starttime": "2000-01-01", "endtime": TODAY,
        "minlatitude": 5.0, "maxlatitude": 38.0, "minlongitude": 65.0,
        "maxlongitude": 100.0, "minmagnitude": 2.5, "orderby": "time-asc",
        "limit": 20000,
    })
    entries.append(fetch("earthquake/usgs_india_events.csv", earthquake_url))

    # NOAA's WMO-endorsed global tropical-cyclone best-track archive.
    entries.append(fetch(
        "cyclone/ibtracs_all_v04r01.csv",
        "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.ALL.list.v04r01.csv",
    ))

    # NASA Global Landslide Catalog: event inventory only (no implicit negative examples).
    entries.append(fetch(
        "landslide/nasa_global_landslide_catalog.csv",
        "https://data.nasa.gov/docs/legacy/Global_Landslide_Catalog_Export/Global_Landslide_Catalog_Export_rows.csv",
    ))

    # India Drought Monitor: current 0.25-degree CDI grid and national weekly area series.
    entries.append(fetch(
        "drought/india_current_cdi.txt",
        "https://indiadroughtmonitor.in/data/Current_CDI.txt",
    ))
    entries.append(fetch(
        "drought/india_drought_area_timeseries.txt",
        "https://indiadroughtmonitor.in/data/India_Drought_Area_Timeseries.txt",
    ))

    # Public daily reanalysis-derived weather for four Kerala locations. Useful predictors
    # for heat/rainfall studies, but not itself a labelled disaster-occurrence dataset.
    weather_params = {
        "latitude": "9.9312,11.6854,9.8494,10.7867",
        "longitude": "76.2673,76.1320,76.9552,76.6548",
        "start_date": "2000-01-01",
        "end_date": "2025-12-31",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max",
        "timezone": "Asia/Kolkata",
        "format": "json",
    }
    weather_url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(weather_params)
    entries.append(fetch("weather/kerala_daily_weather_2000_2025.json", weather_url))

    # These sources are deliberately marked as requiring additional access/label work,
    # instead of downloading guessed endpoints or silently treating event-only data as ML rows.
    access_notes = [
        {
            "hazard_id": "wildfire",
            "status": "ACCESS_KEY_REQUIRED_FOR_ARCHIVE",
            "source": "NASA FIRMS",
            "url": "https://firms.modaps.eosdis.nasa.gov/download/",
            "needed": "A NASA FIRMS MAP_KEY/Earthdata-authorized archive request; pair detections with defensible non-fire samples and weather predictors.",
        },
        {
            "hazard_id": "air_pollution",
            "status": "API_KEY_OR_CPCB_EXPORT_NEEDED",
            "source": "OpenAQ / CPCB",
            "url": "https://docs.openaq.org/about/about",
            "needed": "OpenAQ v3 API key or a documented CPCB export, station metadata, timestamps, units, and sufficient historical labels.",
        },
        {
            "hazard_id": "tsunami",
            "status": "CATALOGUE_ACCESS_AND_LABEL_REVIEW_NEEDED",
            "source": "NOAA NCEI Global Historical Tsunami Database",
            "url": "https://www.ncei.noaa.gov/products/natural-hazards/tsunamis-earthquakes-volcanoes/tsunamis/global-historical-data",
            "needed": "Retrieve the catalogue via NCEI HazEL and define a defensible impact target; rare event records alone cannot train an occurrence forecast.",
        },
    ]

    report = {
        "status": "SOURCE_ACQUISITION_ATTEMPTED",
        "retrieved_at": TODAY,
        "purpose": "Download public source data and document provenance; not a claim of nine trained models.",
        "downloads": entries,
        "access_notes": access_notes,
        "summary": {
            "attempted_public_downloads": len(entries),
            "downloaded": sum(e["status"] == "DOWNLOADED" for e in entries),
            "failed": sum(e["status"] != "DOWNLOADED" for e in entries),
            "trained_models": 0,
        },
        "scientific_limitations": [
            "Earthquake, cyclone, and landslide catalogues are observed-event records, not automatically labelled forecasts.",
            "Drought index and weather reanalysis are useful targets/predictors only after time alignment and leakage-safe validation.",
            "Wildfire and air-pollution archives need additional access and carefully constructed labels/background samples.",
            "Tsunami is a rare-event hazard; this acquisition does not justify a short-term probability model.",
            "No source download is treated as proof of scientific validation or Kochi-specific accuracy.",
        ],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    # A source outage should still leave an artifact with precise failure reasons.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

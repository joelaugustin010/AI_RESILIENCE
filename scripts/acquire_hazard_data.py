"""Acquire public, reproducible source observations for the nine non-flood hazards.

The downloaded files are source observations, not automatically supervised training tables.
Run: python scripts/acquire_hazard_data.py
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
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
USER_AGENT = "AI_RESILIENCE-student-research/1.0 (public dataset acquisition; source attribution retained)"
TIMEOUT = 120


def download_bytes(url: str, attempts: int = 5) -> tuple[bytes, str, str]:
    """Retry transient source throttling and server errors with backoff."""
    last_error = None
    for attempt in range(attempts):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            with urlopen(req, timeout=TIMEOUT) as response:
                return response.read(), response.headers.get("Content-Type", ""), response.geturl()
        except HTTPError as exc:
            last_error = exc
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            delay = min(5 * (2 ** attempt), 60)
            print(f"[RETRY] HTTP {exc.code}; waiting {delay}s before retry", file=sys.stderr)
            time.sleep(delay)
        except URLError as exc:
            last_error = exc
            if attempt == attempts - 1:
                raise
            delay = min(3 * (2 ** attempt), 30)
            print(f"[RETRY] {exc}; waiting {delay}s before retry", file=sys.stderr)
            time.sleep(delay)
    raise RuntimeError(f"Download failed after retries: {last_error}")


def save_data(name: str, url: str, data: bytes, content_type: str, final_url: str,
              *, rows: int | None = None, header: list[str] | None = None) -> dict:
    target = ROOT / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if len(data) < 100:
        raise ValueError(f"Response suspiciously small ({len(data)} bytes)")
    prefix = data[:500].lstrip().lower()
    if "text/html" in content_type.lower() or prefix.startswith((b"<!doctype html", b"<html")):
        raise ValueError(f"Received HTML instead of data (Content-Type: {content_type})")
    target.write_bytes(data)
    entry = {
        "file": str(target), "source_url": url, "final_url": final_url,
        "retrieved_at": TODAY, "status": "DOWNLOADED", "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(), "content_type": content_type,
    }
    if rows is not None:
        entry["data_rows"] = rows
    if header is not None:
        entry["header"] = header
    print(f"[OK] {name}: {len(data):,} bytes")
    return entry


def fetch(name: str, url: str) -> dict:
    try:
        data, content_type, final_url = download_bytes(url)
        rows = None
        header = None
        if name.lower().endswith(".csv"):
            reader = csv.reader(io.StringIO(data.decode("utf-8-sig", errors="replace")))
            header = next(reader, [])
            rows = sum(1 for _ in reader)
        return save_data(name, url, data, content_type, final_url, rows=rows, header=header)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        result = {"file": str(ROOT / name), "source_url": url, "retrieved_at": TODAY,
                  "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
        print(f"[FAILED] {name}: {result['error']}", file=sys.stderr)
        return result


def fetch_ibtracs_north_indian_ocean() -> dict:
    """Fetch NOAA's archive, retain only North Indian Ocean (NI) rows for repo-size control."""
    url = ("https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-"
           "ibtracs/v04r01/access/csv/ibtracs.ALL.list.v04r01.csv")
    name = "cyclone/ibtracs_north_indian_ocean_v04r01.csv"
    try:
        data, content_type, final_url = download_bytes(url)
        text = data.decode("utf-8-sig", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or "BASIN" not in reader.fieldnames:
            raise ValueError("IBTrACS response did not contain expected BASIN field")
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
        writer.writeheader()
        kept = 0
        for row in reader:
            # NI is the North Indian Ocean basin; retain this region to support India-focused analysis.
            if (row.get("BASIN") or "").strip().upper() == "NI":
                writer.writerow(row)
                kept += 1
        if kept < 20:
            raise ValueError(f"Only {kept} North Indian Ocean rows found; refusing suspicious result")
        filtered = output.getvalue().encode("utf-8")
        return save_data(name, url, filtered, "text/csv", final_url, rows=kept,
                         header=list(reader.fieldnames))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        result = {"file": str(ROOT / name), "source_url": url, "retrieved_at": TODAY,
                  "status": "FAILED", "error": f"{type(exc).__name__}: {exc}"}
        print(f"[FAILED] {name}: {result['error']}", file=sys.stderr)
        return result


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    entries: list[dict] = []

    earthquake_url = "https://earthquake.usgs.gov/fdsnws/event/1/query?" + urlencode({
        "format": "csv", "starttime": "2000-01-01", "endtime": TODAY,
        "minlatitude": 5.0, "maxlatitude": 38.0, "minlongitude": 65.0,
        "maxlongitude": 100.0, "minmagnitude": 2.5, "orderby": "time-asc",
        "limit": 20000,
    })
    entries.append(fetch("earthquake/usgs_india_events_2000_present.csv", earthquake_url))
    entries.append(fetch_ibtracs_north_indian_ocean())

    entries.append(fetch(
        "landslide/nasa_global_landslide_catalog.csv",
        "https://data.nasa.gov/docs/legacy/Global_Landslide_Catalog_Export/Global_Landslide_Catalog_Export_rows.csv",
    ))
    entries.append(fetch(
        "drought/india_current_cdi.txt",
        "https://indiadroughtmonitor.in/data/Current_CDI.txt",
    ))
    entries.append(fetch(
        "drought/india_drought_area_timeseries.txt",
        "https://indiadroughtmonitor.in/data/India_Drought_Area_Timeseries.txt",
    ))

    # Open-Meteo's archive endpoint takes one coordinate pair per request.
    locations = {
        "kochi": (9.9312, 76.2673),
        "kottayam": (9.5916, 76.5222),
        "wayanad": (11.6854, 76.1320),
        "thiruvananthapuram": (8.5241, 76.9366),
    }
    for location, (lat, lon) in locations.items():
        weather_url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode({
            "latitude": lat, "longitude": lon, "start_date": "2000-01-01",
            "end_date": "2025-12-31",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max",
            "timezone": "Asia/Kolkata",
        })
        entries.append(fetch(f"weather/{location}_daily_weather_2000_2025.json", weather_url))
        # Respect public API rate limits between location requests.
        import time as _time
        _time.sleep(3)

    # Extended Kochi reference record (1991-2025) so the SPI-1 model can use a
    # 30-year reference period. It is stored separately and never spliced with
    # the 2000-2025 file; descriptive benchmarks use one consistent record.
    extended_kochi_url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode({
        "latitude": 9.947276, "longitude": 76.29921,
        "start_date": "1991-01-01", "end_date": "2025-12-31",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max",
        "timezone": "Asia/Kolkata",
    })
    entries.append(fetch("weather/kochi_daily_weather_1991_2025.json", extended_kochi_url))

    access_notes = [
        {"hazard_id": "wildfire", "status": "ACCESS_KEY_REQUIRED_FOR_ARCHIVE",
         "source": "NASA FIRMS", "url": "https://firms.modaps.eosdis.nasa.gov/download/",
         "needed": "FIRMS MAP_KEY/authenticated request; pair fire detections with defensible non-fire samples and weather."},
        {"hazard_id": "air_pollution", "status": "API_KEY_OR_CPCB_EXPORT_NEEDED",
         "source": "OpenAQ / CPCB", "url": "https://docs.openaq.org/about/about",
         "needed": "OpenAQ v3 API key or documented CPCB export, station metadata, pollutant units and timestamps."},
        {"hazard_id": "tsunami", "status": "CATALOGUE_RETRIEVAL_AND_LABEL_REVIEW_NEEDED",
         "source": "NOAA NCEI Global Historical Tsunami Database",
         "url": "https://www.ncei.noaa.gov/products/natural-hazards/tsunamis-earthquakes-volcanoes/tsunamis/global-historical-data",
         "needed": "Download the public catalogue and define an impact/scenario target; rare event records cannot justify short-term probability forecasts."},
    ]
    report = {
        "status": "SOURCE_ACQUISITION_ATTEMPTED",
        "retrieved_at": TODAY,
        "purpose": "Download source observations with provenance. Not a claim that nine models are trained.",
        "downloads": entries,
        "access_notes": access_notes,
        "summary": {
            "attempted_downloads": len(entries),
            "downloaded": sum(e["status"] == "DOWNLOADED" for e in entries),
            "failed": sum(e["status"] != "DOWNLOADED" for e in entries),
            "trained_models": 0,
        },
        "source_notes": {
            "IBTrACS": "North Indian Ocean basin rows only; original NOAA/NCEI archive URL and checksum retained.",
            "Open-Meteo": "Daily historical reanalysis data; cite Open-Meteo and its data providers when using these files.",
            "USGS": "Observed earthquake catalogue, not a future earthquake prediction dataset.",
            "NASA landslides": "Event inventory only; no non-landslide samples are inferred.",
        },
        "scientific_limitations": [
            "Raw event catalogues are not automatically labelled prediction tables.",
            "Drought/weather data need explicit targets and time-safe feature construction.",
            "Wildfire and air pollution require additional access and carefully defined labels.",
            "Tsunami rarity means an event catalogue alone is not a short-term probability model.",
            "Data presence does not prove local Kochi validity or scientific approval.",
        ],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

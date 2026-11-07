"""Acquire the exact Open-Meteo weather inputs required by the Kerala transfer experiment.

The files are downloaded at workflow runtime, validated, and accompanied by a
SHA-256 manifest. They remain untracked research inputs; no labels are created.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "external" / "hazards" / "raw" / "weather"
REPORT = ROOT / "reports" / "kerala_weather_transfer_acquisition.json"
FIELDS = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
)
LOCATIONS = {
    "kochi": {
        "latitude": 9.947276, "longitude": 76.29921,
        "start_date": "1991-01-01",
        "filename": "kochi_daily_weather_1991_2025.json",
    },
    "kottayam": {
        "latitude": 9.5916, "longitude": 76.5222,
        "start_date": "2000-01-01",
        "filename": "kottayam_daily_weather_2000_2025.json",
    },
    "wayanad": {
        "latitude": 11.6854, "longitude": 76.1320,
        "start_date": "2000-01-01",
        "filename": "wayanad_daily_weather_2000_2025.json",
    },
    "thiruvananthapuram": {
        "latitude": 8.5241, "longitude": 76.9366,
        "start_date": "2000-01-01",
        "filename": "thiruvananthapuram_daily_weather_2000_2025.json",
    },
}
END_DATE = "2025-12-31"
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"


def validate_payload(payload: dict, *, start_date: str, end_date: str) -> dict:
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("Open-Meteo response has no daily object.")
    required = {"time", *FIELDS}
    missing = sorted(required - set(daily))
    if missing:
        raise ValueError(f"Weather response missing fields: {missing}")
    dates = daily["time"]
    if not isinstance(dates, list) or len(dates) < 300:
        raise ValueError("Weather response has too few daily dates.")
    if dates != sorted(set(dates)):
        raise ValueError("Weather dates must be unique and strictly increasing.")
    parsed = [date.fromisoformat(value) for value in dates]
    if any((current - previous).days != 1 for previous, current in zip(parsed, parsed[1:])):
        raise ValueError(
            "Weather dates must be continuous daily dates; missing calendar dates "
            "would misalign lag features and next-day targets."
        )
    if parsed[0] > date.fromisoformat(start_date) or parsed[-1] < date.fromisoformat(end_date):
        raise ValueError("Weather response does not cover the complete requested date range.")
    for field in FIELDS:
        values = daily[field]
        if not isinstance(values, list) or len(values) != len(dates):
            raise ValueError(f"{field} does not align with the daily date index.")
        for value in values:
            if value is not None and not isinstance(value, (int, float)):
                raise ValueError(f"{field} contains a non-numeric value.")
            if isinstance(value, (int, float)) and not __import__("math").isfinite(value):
                raise ValueError(f"{field} contains a non-finite value.")
    for value in daily["precipitation_sum"]:
        if value is not None and value < 0:
            raise ValueError("Precipitation cannot be negative.")
    return {
        "rows": len(dates),
        "first_date": dates[0],
        "last_date": dates[-1],
        "timezone": payload.get("timezone"),
        "units": daily.get("units", {}),
    }


def download(url: str, attempts: int = 5) -> bytes:
    last_error = None
    for attempt in range(attempts):
        try:
            request = Request(
                url,
                headers={"User-Agent": "AI_RESILIENCE-research/1.0", "Accept": "application/json"},
            )
            with urlopen(request, timeout=90) as response:
                data = response.read()
            if len(data) < 100:
                raise ValueError("Weather response is unexpectedly small.")
            return data
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            time.sleep(min(3 * (2 ** attempt), 30))
    raise RuntimeError(f"Open-Meteo download failed after {attempts} attempts: {last_error}")


def acquire(output_root: Path = DATA_ROOT, end_date: str = END_DATE) -> dict:
    if date.fromisoformat(end_date) > date.today():
        raise ValueError("end_date cannot be in the future.")
    output_root.mkdir(parents=True, exist_ok=True)
    entries = []
    for location, config in LOCATIONS.items():
        params = {
            "latitude": config["latitude"],
            "longitude": config["longitude"],
            "start_date": config["start_date"],
            "end_date": end_date,
            "daily": ",".join(FIELDS),
            "timezone": "Asia/Kolkata",
        }
        url = BASE_URL + "?" + urlencode(params)
        raw = download(url)
        payload = json.loads(raw)
        validation = validate_payload(
            payload, start_date=config["start_date"], end_date=end_date
        )
        target = output_root / config["filename"]
        target.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        metadata = {
            "source": "Open-Meteo Historical Weather API",
            "source_url": url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "location": location,
            "coordinates": {
                "latitude": config["latitude"],
                "longitude": config["longitude"],
            },
            "requested_start_date": config["start_date"],
            "requested_end_date": end_date,
            "source_type": "MODELLED_REANALYSIS_GRID_POINT_NOT_STATION_OBSERVATION",
            "sha256": digest,
            **validation,
        }
        target.with_suffix(".metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        entries.append({"location": location, "file": str(target.relative_to(ROOT)),
                        "sha256": digest, **validation})
        time.sleep(2)
    return {
        "status": "ACQUIRED_AND_SCHEMA_VALIDATED",
        "source": "Open-Meteo Historical Weather API",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "records": entries,
        "scope": "Input acquisition and schema validation only; not station validation or model validation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DATA_ROOT)
    parser.add_argument("--end-date", default=END_DATE)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    report = acquire(args.output_root, args.end_date)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "locations": len(report["records"]),
                      "rows": {x["location"]: x["rows"] for x in report["records"]}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

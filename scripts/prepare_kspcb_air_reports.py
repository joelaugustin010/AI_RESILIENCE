"""Prepare local, source-preserving extracts from reviewed KSPCB PDFs.

Install the optional parser with ``python -m pip install -r requirements-data.txt``.
This script only reads the preserved PDFs and writes derived CSVs plus hashes;
it does not retrieve or infer source observations.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "air_quality_reports"
OUTPUT = ROOT / "data" / "processed" / "air_quality"

MONTHLY_FILE = RAW / "KSPCB_CAAQMS_monthly_report_2026-08.pdf"
DAILY_AQI_FILE = RAW / "KSPCB_AQI_daily_average_2026-10-16.pdf"
NAMP_FILE = RAW / "KSPCB_NAMP_report_2025-08.pdf"

MONTHLY_PDF_URL = (
    "https://kspcb.kerala.gov.in/fileViewer/"
    "UHIwKzVlZkpwTnVzaVAxY2lHZlRZTzNUQ0dBczBoYktqTmN3dFVHb2xUMm1rTktMUldZTjR4"
    "UHgyZGYwWFE1NTdYckNpc0ZweUhZc1pXaXlhK1V5UEE9PQ%2A%2A/0?raw=1"
)
DAILY_AQI_PDF_URL = (
    "https://kspcb.kerala.gov.in/fileViewer/"
    "azN0VDUxTVp6VmpieWlJZmc1UnoyZmF0ckErZWlCNWltVzlEaFlYM3BEeC9kT1hvQkdEek1V"
    "Q2pxbUVnZk1nOE81MTYzcXJyUFlLYzZQL2NISDRDVXc9PQ%2A%2A/0?raw=1"
)
NAMP_PDF_URL = (
    "https://kspcb.kerala.gov.in/fileViewer/"
    "NXNVM0NVdTVKeUVBdWtZTVdTWXgyUnNDVW4zQ1Y2TlVtWG14SWpFZmdzVT0%2A/0?raw=1"
)
DIRECTORY_URL = "https://kspcb.kerala.gov.in/water-and-air-quality-directory"

POLLUTANT_COLUMNS = {
    "PM10": "ug/m3",
    "PM2.5": "ug/m3",
    "SO2": "ug/m3",
    "CO": "mg/m3",
    "NO": "ug/m3",
    "NO2": "ug/m3",
    "NOX": "ug/m3",
    "NH3": "ug/m3",
    "O3": "ug/m3",
}
MONTHLY_PARAMETERS = list(POLLUTANT_COLUMNS)
DAILY_PARAMETERS = ["SO2", "CO", "PM2.5", "O3", "PM10", "NH3", "NOx", "NO", "NO2"]

NAMP_MEASUREMENT_COLUMNS = [
    "SO2_06_10_4h_source_value",
    "SO2_10_14_4h_source_value",
    "SO2_14_18_4h_source_value",
    "SO2_18_22_4h_source_value",
    "SO2_22_02_4h_source_value",
    "SO2_02_06_4h_source_value",
    "SO2_24h_average_source_value",
    "NO2_06_10_4h_source_value",
    "NO2_10_14_4h_source_value",
    "NO2_14_18_4h_source_value",
    "NO2_18_22_4h_source_value",
    "NO2_22_02_4h_source_value",
    "NO2_02_06_4h_source_value",
    "NO2_24h_average_source_value",
    "RSPM_06_14_8h_source_value",
    "RSPM_14_22_8h_source_value",
    "RSPM_22_06_8h_source_value",
    "RSPM_24h_average_source_value",
    "PM2.5_source_value",
    "temperature_source_value",
    "weather_source_value",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        raise ValueError("Refusing to serialize an empty extract.")
    from io import StringIO

    output = StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _preserve_or_write(path: Path, content: bytes, *, write: bool) -> dict[str, str]:
    digest = hashlib.sha256(content).hexdigest()
    if path.exists():
        existing_digest = sha256_file(path)
        if existing_digest != digest:
            raise FileExistsError(
                f"Refusing to replace different existing output {path}: "
                f"expected {digest}, found {existing_digest}."
            )
        return {"path": path.name, "sha256": digest, "state": "already matches"}
    if not write:
        return {"path": path.name, "sha256": digest, "state": "validated; not written"}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as output:
        output.write(content)
    return {"path": path.name, "sha256": digest, "state": "created"}


def _validate_pinned_pdf(path: Path, source_key: str) -> None:
    manifest_path = OUTPUT / "kspcb_air_reports.metadata.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing reviewed source manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("sources", {}).get(source_key, {}).get("sha256")
    if not isinstance(expected, str) or sha256_file(path) != expected:
        raise ValueError(f"{path.name} does not match the SHA-256 pinned in {manifest_path.name}.")
    with path.open("rb") as source:
        if not source.read(8).startswith(b"%PDF-"):
            raise ValueError(f"{path.name} does not have a PDF signature.")


def extract_monthly_caaqms(
    path: Path = MONTHLY_FILE,
    source_url: str = MONTHLY_PDF_URL,
    station: str = "Eloor",
    expected_days: int = 31,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    reader = PdfReader(path)
    page = reader.pages[2]
    page_text = page.extract_text(extraction_mode="layout") or ""
    if station.casefold() not in page_text.casefold():
        raise ValueError(f"Expected {station} station heading on page 3 of {path.name}")
    lines = page_text.splitlines()
    pollutant_rows: list[dict[str, Any]] = []
    aqi_rows: list[dict[str, Any]] = []
    weather_rows: list[dict[str, Any]] = []

    for line in lines:
        fields = line.split()
        if len(fields) != 16 or not re.fullmatch(r"\d{2}-\d{2}-\d{4}", fields[0]):
            continue
        date = datetime.strptime(fields[0], "%d-%m-%Y").date().isoformat()
        values = [float(value) for value in fields[1:]]
        pollutant_values = values[: len(MONTHLY_PARAMETERS)]
        wind_speed, wind_direction, temperature, humidity = values[9:13]
        source_aqi = int(values[15 - 1])

        for pollutant, value in zip(MONTHLY_PARAMETERS, pollutant_values):
            pollutant_rows.append(
                {
                    "observed_at": date,
                    "station": station,
                    "pollutant": "NOx" if pollutant == "NOX" else pollutant,
                    "value": value,
                    "unit": POLLUTANT_COLUMNS[pollutant],
                    "averaging_period": "daily report value; exact interval not stated",
                    "quality_flag": "unassessed",
                    "quality_note": "No row-level quality or completeness flag is printed in this report.",
                    "source_aqi": source_aqi,
                    "source_url": source_url,
                }
            )

        aqi_rows.append(
            {
                "observed_at": date,
                "station": station,
                "source_aqi": source_aqi,
                "source_aqi_category": "not supplied in this report",
                "source_url": source_url,
            }
        )
        weather_rows.append(
            {
                "observed_at": date,
                "station": station,
                "wind_speed": wind_speed,
                "wind_speed_unit": "m/s",
                "wind_direction": wind_direction,
                "wind_direction_unit": "degrees",
                "temperature": temperature,
                "temperature_unit": "°C",
                "relative_humidity": humidity,
                "relative_humidity_unit": "%",
                "averaging_period": "daily report value; exact interval not stated",
                "source_url": source_url,
            }
        )

    if len(aqi_rows) != expected_days:
        raise ValueError(f"Expected {expected_days} dated {station} rows, found {len(aqi_rows)}")
    return pollutant_rows, aqi_rows, weather_rows


def extract_daily_aqi(path: Path = DAILY_AQI_FILE) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    reader = PdfReader(path)
    page_text = reader.pages[0].extract_text(extraction_mode="layout") or ""
    measurement_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    observed_at = "2026-10-16"

    for line in page_text.splitlines():
        fields = line.split()
        if not fields:
            continue
        remark = fields[-1].casefold()
        numeric_start = next(
            (i for i, token in enumerate(fields) if _is_number(token)), None
        )
        if numeric_start is not None and len(fields) - numeric_start == 11:
            station = " ".join(fields[:numeric_start])
            values = [float(value) for value in fields[numeric_start:-1]]
            if len(values) != 10 or remark not in {"good", "satisfactory"}:
                continue
            source_aqi = int(values[-1])
            measurement_rows.append(
                {
                    "observed_at": observed_at,
                    "station": station,
                    "source_aqi": source_aqi,
                    "source_remark": fields[-1],
                    "source_url": DAILY_AQI_PDF_URL,
                    **{
                        f"{pollutant}_value": value
                        for pollutant, value in zip(DAILY_PARAMETERS, values[:-1])
                    },
                    "unit_SO2": "ug/m3",
                    "unit_CO": "mg/m3",
                    "unit_PM2.5": "ug/m3",
                    "unit_O3": "ug/m3",
                    "unit_PM10": "ug/m3",
                    "unit_NH3": "ug/m3",
                    "unit_NOx": "ug/m3",
                    "unit_NO": "ug/m3",
                    "unit_NO2": "ug/m3",
                    "averaging_period": "daily report value; exact interval not stated",
                    "quality_flag": "unassessed",
                }
            )
        else:
            status_match = re.match(
                r"^\s*(.*?)\s+(INSUFFICIENT DATA|POWER FAILURE)\s*$",
                line,
                flags=re.IGNORECASE,
            )
            if status_match is None:
                continue
            status_rows.append(
                {
                    "observed_at": observed_at,
                    "station": status_match.group(1).strip(),
                    "source_status": status_match.group(2),
                    "source_url": DAILY_AQI_PDF_URL,
                }
            )

    if len(measurement_rows) != 5 or len(status_rows) != 4:
        raise ValueError(
            f"Expected five AQI rows and four unavailable-station rows, got "
            f"{len(measurement_rows)} and {len(status_rows)}"
        )
    return measurement_rows, status_rows


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _number_or_source_marker(value: str) -> str:
    if value == "*":
        return value
    return str(float(value))


def extract_ernakulam_namp(path: Path = NAMP_FILE) -> list[dict[str, Any]]:
    reader = PdfReader(path)
    records: list[dict[str, Any]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text(extraction_mode="layout") or ""
        normalized_text = " ".join(text.upper().split())
        if "ERNAKULAM" not in normalized_text or "NAMP DATA FOR THE MONTH OF JUNE 2025" not in normalized_text:
            continue
        title = next(
            (line.strip() for line in text.splitlines() if "NAMP DATA FOR THE MONTH" in line.upper()),
            "",
        )
        station_match = re.search(r"-\s*(.*?)\s*\(ERNAKULAM\)", title, flags=re.IGNORECASE)
        if not station_match:
            raise ValueError(f"Cannot read NAMP station title on page {page_number}")
        station = station_match.group(1).strip()
        lines = text.splitlines()
        top_rows: list[dict[str, Any]] = []
        bottom_rows: list[list[str]] = []
        for line in lines:
            fields = line.split()
            if len(fields) >= 12 and fields[0].isdigit() and re.fullmatch(r"\d{2}[./]\d{2}[./]\d{4}", fields[1]):
                coordinate_index = next(
                    (
                        i
                        for i in range(2, len(fields) - 1)
                        if _is_number(fields[i])
                        and _is_number(fields[i + 1])
                        and 8 <= float(fields[i]) <= 12
                        and 74 <= float(fields[i + 1]) <= 79
                    ),
                    None,
                )
                if coordinate_index is None:
                    raise ValueError(f"Missing source coordinates on NAMP page {page_number}")
                trailing = fields[-7:]
                if not all(value == "*" or _is_number(value) for value in trailing):
                    raise ValueError(f"Malformed SO2 data row on NAMP page {page_number}")
                source_date = datetime.strptime(fields[1].replace(".", "/"), "%d/%m/%Y").date().isoformat()
                top_rows.append(
                    {
                        "station_code": fields[0],
                        "observed_at": source_date,
                        "station": station,
                        "latitude": float(fields[coordinate_index]),
                        "longitude": float(fields[coordinate_index + 1]),
                        "location_attributes_source": " ".join(fields[coordinate_index + 2 : -7]),
                        "SO2_06_10_4h_source_value": _number_or_source_marker(trailing[0]),
                        "SO2_10_14_4h_source_value": _number_or_source_marker(trailing[1]),
                        "SO2_14_18_4h_source_value": _number_or_source_marker(trailing[2]),
                        "SO2_18_22_4h_source_value": _number_or_source_marker(trailing[3]),
                        "SO2_22_02_4h_source_value": _number_or_source_marker(trailing[4]),
                        "SO2_02_06_4h_source_value": _number_or_source_marker(trailing[5]),
                        "SO2_24h_average_source_value": _number_or_source_marker(trailing[6]),
                        "source_page": page_number,
                    }
                )
                continue

            if len(fields) >= 14 and all(value == "*" or _is_number(value) for value in fields[:13]):
                bottom_rows.append(fields[:13] + [fields[13]])

        if len(top_rows) != len(bottom_rows):
            raise ValueError(
                f"NAMP page {page_number} has {len(top_rows)} source identity rows and "
                f"{len(bottom_rows)} pollutant rows"
            )
        for top, values in zip(top_rows, bottom_rows):
            for column, value in zip(NAMP_MEASUREMENT_COLUMNS[7:], values):
                top[column] = (
                    value
                    if column == "weather_source_value"
                    else _number_or_source_marker(value)
                )
            top["unit_status"] = "Concentration units are not stated in the PDF; not eligible for concentration analysis."
            top["coordinate_reference_system"] = "not stated by source"
            records.append(top)

    if len(records) != 62:
        raise ValueError(f"Expected 62 dated Ernakulam NAMP rows, found {len(records)}")
    return records


def _file_metadata(path: Path, source_url: str, source_publisher: str, limitations: list[str]) -> dict[str, Any]:
    return {
        "publisher": source_publisher,
        "source_url": source_url,
        "directory_url": DIRECTORY_URL if "kspcb" in source_url.lower() else None,
        "retrieved_on": "2026-10-23",
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "reuse_terms": "No dataset-specific reuse licence was found. Attribute the public source; confirm permission before redistribution beyond this project.",
        "limitations": limitations,
    }


def main(*, write: bool = False) -> None:
    for path, key in (
        (MONTHLY_FILE, "monthly_caaqms"),
        (DAILY_AQI_FILE, "daily_aqi"),
        (NAMP_FILE, "namp"),
    ):
        if not path.is_file():
            raise FileNotFoundError(f"Missing reviewed input: {path}")
        _validate_pinned_pdf(path, key)
    monthly_pollutants, monthly_aqi, monthly_weather = extract_monthly_caaqms()
    daily_measurements, daily_status = extract_daily_aqi()
    namp_rows = extract_ernakulam_namp()

    outputs = {
        "kspcb_caaqms_eloor_daily_2026-08.csv": monthly_pollutants,
        "kspcb_caaqms_eloor_aqi_2026-08.csv": monthly_aqi,
        "kspcb_caaqms_eloor_weather_2026-08.csv": monthly_weather,
        "kspcb_daily_aqi_2026-10-16.csv": daily_measurements,
        "kspcb_daily_aqi_status_2026-10-16.csv": daily_status,
        "kspcb_namp_ernakulam_2025-06.csv": namp_rows,
    }
    output_bytes = {filename: _csv_bytes(rows) for filename, rows in outputs.items()}

    source_files = {
        "monthly_caaqms": _file_metadata(
            MONTHLY_FILE,
            MONTHLY_PDF_URL,
            "Kerala State Pollution Control Board",
            [
                "Directory label and report title say August 2026; the Eloor page is daily by date.",
                "The PDF gives pollutant units but not exact averaging intervals, row-level QA flags, completeness/capture, a station code, or coordinates for Eloor.",
                "A numeric value means the report published a value; it is not an independent quality certification.",
            ],
        ),
        "daily_aqi": _file_metadata(
            DAILY_AQI_FILE,
            DAILY_AQI_PDF_URL,
            "Kerala State Pollution Control Board",
            [
                "Report date is 16 October 2026; the values are historical and are not a live feed.",
                "The directory identifies the document as a daily-average AQI report; exact per-pollutant averaging intervals and completeness flags are not printed.",
                "Station identifiers and coordinates are not included; three stations report insufficient data and one reports power failure.",
            ],
        ),
        "namp": _file_metadata(
            NAMP_FILE,
            NAMP_PDF_URL,
            "Kerala State Pollution Control Board",
            [
                "The directory filename says August 2025, but the report pages for Ernakulam state June 2025.",
                "The report prints station codes, dates, decimal latitude/longitude, pollutant values, 4-hour/8-hour samples and 24-hour averages, and some missing-sample notes.",
                "Pollutant concentration units and coordinate reference system are not stated in the reviewed pages; rows are preserved but excluded from concentration analysis.",
                "Some coordinates vary within the Kuttippadam page; retain row-level values and do not promote that coordinate to a station point.",
                "pypdf emitted four unresolved indirect-object warnings while parsing this PDF; the 62 extracted rows passed structural checks, but source-table review remains appropriate.",
            ],
        ),
    }
    for key, source in source_files.items():
        source["outputs"] = {
            filename: {
                "sha256": hashlib.sha256(output_bytes[filename]).hexdigest(),
                "rows": len(rows),
            }
            for filename, rows in outputs.items()
            if (key == "monthly_caaqms" and filename.startswith("kspcb_caaqms_eloor_"))
            or (key == "daily_aqi" and filename.startswith("kspcb_daily_aqi_"))
            or (key == "namp" and filename.startswith("kspcb_namp_"))
        }
    metadata = {
        "generated_on": max(source["retrieved_on"] for source in source_files.values()),
        "extractor": "scripts/prepare_kspcb_air_reports.py",
        "extractor_version": "pypdf 6.21.2, local review run",
        "sources": source_files,
        "analysis_boundary": "Only the August 2026 Eloor CAAQMS daily concentration series has both dated values and source-stated units. NAMP observations with unstated units are archived separately and not passed to the analysis pipeline.",
    }
    metadata_bytes = (json.dumps(metadata, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    states = [
        _preserve_or_write(OUTPUT / filename, content, write=write)
        for filename, content in output_bytes.items()
    ]
    states.append(_preserve_or_write(
        OUTPUT / "kspcb_air_reports.metadata.json", metadata_bytes, write=write
    ))
    print(json.dumps({
        "outputs": states,
        "raw_inputs_preserved": True,
        "write_requested": write,
        "note": "No processed output was written." if not write else "Only missing, hash-checked outputs were created.",
    }, indent=2))


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser(
        description="Rebuild KSPCB report extracts. Default is read-only; --write creates missing outputs only."
    )
    argument_parser.add_argument(
        "--write", action="store_true",
        help="Write missing derived outputs after input and output hash checks; mismatched existing outputs are never replaced.",
    )
    main(write=argument_parser.parse_args().write)

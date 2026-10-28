"""Create validated, source-linked extracts from the newly acquired official PDFs."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from prepare_kspcb_air_reports import extract_monthly_caaqms


ROOT = Path(__file__).resolve().parents[1]
RAW_AIR = ROOT / "data" / "raw" / "air_quality_reports" / "KSPCB_CAAQMS_monthly_report_2026-09.pdf"
RAW_DIC = ROOT / "data" / "raw" / "industrial" / "DIC_DA_Edayar_allotment_details_2022.pdf"
OUTPUT_AIR = ROOT / "data" / "processed" / "air_quality"
OUTPUT_INDUSTRIAL = ROOT / "data" / "processed" / "industrial"
KSPCB_URL = "https://kspcb.kerala.gov.in/fileViewer/UHIwKzVlZkpwTnVzaVAxY2lHZlRZS0swN04rRWJuOHBlVVNZeUNRdkZ5c0pkUlVxeDY5aDduT1AwUnR5TWt6cjRKdnp6R25UZS9ubC9oeEh3TmFUbFE9PQ%2A%2A/0?raw=1"
DIC_URL = "https://industry.kerala.gov.in/images/DA-DP/Ernakulam/DA_Edayar.pdf"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_preserved_pdf(path: Path, source_url: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing preserved input: {path}")
    content = path.read_bytes()
    if not content.startswith(b"%PDF-"):
        raise ValueError(f"Input has a .pdf name but no PDF signature: {path.name}")
    metadata_path = Path(str(path) + ".metadata.json")
    if not metadata_path.is_file():
        raise FileNotFoundError(f"Missing provenance sidecar: {metadata_path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("source_url") != source_url:
        raise ValueError(f"Source URL mismatch in {metadata_path.name}")
    if metadata.get("sha256") != _sha256(content):
        raise ValueError(f"SHA-256 mismatch in {metadata_path.name}")
    if metadata.get("bytes") != len(content):
        raise ValueError(f"Byte count mismatch in {metadata_path.name}")
    return metadata


def _csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        raise ValueError("Refusing to serialize an empty dataset")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def _preserve_or_write(path: Path, content: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_bytes()
        existing_hash = _sha256(existing)
        if existing_hash == _sha256(content):
            return existing_hash
        raise FileExistsError(f"Refusing to replace a different existing output: {path}")
    with path.open("xb") as output:
        output.write(content)
    return _sha256(content)


def _dic_crosswalk() -> list[dict[str, Any]]:
    reader = PdfReader(RAW_DIC, strict=True)
    # The PDF identifies itself as the Edayar DA/DP allotment register. These
    # two rows were located and manually checked against their printed serials.
    records = [
        {
            "facility_id": "EDAYAR-002",
            "facility_name_as_published": "SUD CHEMIE INDIA PVT LTD",
            "source_page": 26,
            "source_serial_number": 322,
            "plot_number_as_published": "",
            "plot_area": 2152.00,
            "plot_area_unit": "cents",
            "activity_as_published": "Catalyst, Chemical",
            "working_status_as_published": "Working",
            "status_reference_date": "2022-02-15",
            "source_url": DIC_URL,
            "interpretation_limit": "Historical allotment-register entry only; plot number is blank in the source, and this is not current occupancy, coordinates, or emissions evidence.",
        },
        {
            "facility_id": "EDAYAR-004",
            "facility_name_as_published": "TMS LEATHERS",
            "source_page": 27,
            "source_serial_number": 338,
            "plot_number_as_published": "28",
            "plot_area": 352.00,
            "plot_area_unit": "cents",
            "activity_as_published": "N.e.c",
            "working_status_as_published": "Working",
            "status_reference_date": "2022-02-15",
            "source_url": DIC_URL,
            "interpretation_limit": "Historical allotment-register entry only; plot number is not a coordinate, and this is not current occupancy or emissions evidence.",
        },
    ]
    for record in records:
        lines = (reader.pages[record["source_page"] - 1].extract_text(extraction_mode="layout") or "").splitlines()
        row_start = next((i for i, line in enumerate(lines) if line.strip().startswith(f"{record['source_serial_number']} ")), None)
        if row_start is None:
            raise ValueError(f"DIC serial validation failed for {record['facility_id']}")
        excerpt_lines = []
        for line in lines[row_start:row_start + 4]:
            if excerpt_lines and line.strip()[:1].isdigit() and len(line.split()) > 1:
                break
            excerpt_lines.append(line)
        excerpt = " ".join(" ".join(excerpt_lines).casefold().split())
        expected_name_tokens = str(record["facility_name_as_published"]).casefold().split()
        if not all(token in excerpt for token in expected_name_tokens) or f"{record['plot_area']:.2f}" not in excerpt:
            raise ValueError(f"DIC row validation failed for {record['facility_id']}")
        if record["plot_number_as_published"] and f" {record['plot_number_as_published']} " not in f" {excerpt} ":
            raise ValueError(f"DIC plot-number validation failed for {record['facility_id']}")
    return records


def main() -> None:
    if not RAW_AIR.is_file() or not RAW_DIC.is_file():
        raise FileNotFoundError("Run scripts/acquire_new_official_air_evidence.py first")

    air_source_metadata = _validate_preserved_pdf(RAW_AIR, KSPCB_URL)
    dic_source_metadata = _validate_preserved_pdf(RAW_DIC, DIC_URL)
    air_raw_hash = _sha256(RAW_AIR.read_bytes())
    dic_raw_hash = _sha256(RAW_DIC.read_bytes())
    pollutants, aqi, weather = extract_monthly_caaqms(
        RAW_AIR,
        source_url=KSPCB_URL,
        station="Eloor",
        expected_days=30,
    )
    if len(pollutants) != 270 or len(aqi) != 30 or len(weather) != 30:
        raise ValueError(f"Unexpected September extract sizes: {len(pollutants)}, {len(aqi)}, {len(weather)}")
    dates = sorted({str(row["observed_at"]) for row in aqi})
    if dates[0] != "2026-09-01" or dates[-1] != "2026-09-30" or len(dates) != 30:
        raise ValueError("September Eloor extract does not contain one row for each date")
    for row in pollutants:
        value = float(row["value"])
        if value < 0 or row["unit"] not in {"ug/m3", "mg/m3"} or row["quality_flag"] != "unassessed":
            raise ValueError(f"Invalid or unexpected source concentration row: {row}")

    air_outputs = {
        "kspcb_caaqms_eloor_daily_2026-09.csv": pollutants,
        "kspcb_caaqms_eloor_aqi_2026-09.csv": aqi,
        "kspcb_caaqms_eloor_weather_2026-09.csv": weather,
    }
    air_hashes = {
        name: {"sha256": _preserve_or_write(OUTPUT_AIR / name, _csv_bytes(rows)), "rows": len(rows)}
        for name, rows in air_outputs.items()
    }

    dic_rows = _dic_crosswalk()
    dic_name = "edayar_dic_allotment_crosswalk_2022.csv"
    dic_bytes = _csv_bytes(dic_rows)
    dic_output_hash = _preserve_or_write(OUTPUT_INDUSTRIAL / dic_name, dic_bytes)

    metadata = {
        "generated_on": max(
            str(air_source_metadata["retrieved_on"]),
            str(dic_source_metadata["retrieved_on"]),
        ),
        "extractor": "scripts/prepare_new_official_air_evidence.py plus shared parser scripts/prepare_kspcb_air_reports.py",
        "sources": {
            "kspcb_caaqms_eloor_2026_09": {
                "publisher": "Kerala State Pollution Control Board",
                "source_url": KSPCB_URL,
                "listing_url": "https://kspcb.kerala.gov.in/water-and-air-quality-directory",
                "retrieved_on": str(air_source_metadata["retrieved_on"]),
                "publication_date": "2026-09-30 (directory report date)",
                "licence": "No dataset-specific reuse licence found; preserve publisher attribution and confirm terms before redistribution.",
                "raw_file": str(RAW_AIR.relative_to(ROOT)).replace("\\", "/"),
                "raw_sha256": air_raw_hash,
                "time_coverage": {"start": dates[0], "end": dates[-1], "station": "Eloor CAAQMS", "dated_records": 30},
                "units": {"PM10": "ug/m3", "PM2.5": "ug/m3", "SO2": "ug/m3", "CO": "mg/m3", "NO": "ug/m3", "NO2": "ug/m3", "NOx": "ug/m3", "NH3": "ug/m3", "O3": "ug/m3", "wind_speed": "m/s", "wind_direction": "degrees", "temperature": "degree C", "relative_humidity": "%", "rainfall": "mm"},
                "validation": "PDF signature and structure passed; Eloor September 2026 table and units were present; 30 daily rows from 2026-09-01 through 2026-09-30 parsed; nine pollutant values per date retained without changing units.",
                "outputs": air_hashes,
                "limitations": [
                    "Report values are daily summary values; exact averaging intervals and row-level QA/completeness are not stated.",
                    "Station coordinates and station code are absent; the Eloor station location cannot be verified from this report.",
                    "Daily summary weather fields share dates with pollution rows but cannot provide subdaily time alignment or a dispersion model input series.",
                    "This is ambient monitoring, not facility stack testing; AQI is not an emissions measurement and the series alone cannot identify an industrial source.",
                ],
            },
            "dic_edayar_allotment_2022": {
                "publisher": "Directorate of Industries and Commerce, Government of Kerala",
                "source_url": DIC_URL,
                "listing_url": "https://industry.kerala.gov.in/index.php/pages/infrastructure-support/industrial-development-areas-plots1",
                "retrieved_on": str(dic_source_metadata["retrieved_on"]),
                "publication_date": "2022-02-15 (date in official listing label)",
                "licence": "No dataset-specific open licence identified; preserve attribution and confirm terms before redistribution.",
                "raw_file": str(RAW_DIC.relative_to(ROOT)).replace("\\", "/"),
                "raw_sha256": dic_raw_hash,
                "time_coverage": "Dated Edayar DA/DP allotment register; date basis from official listing label.",
                "units": "Plot area in cents; plot number is a categorical identifier, not a coordinate.",
                "validation": "PDF signature and structure passed; the source names D.A. Edayar; candidate names and serials 322 (page 26) and 338 (page 27) matched extracted source text.",
                "outputs": {dic_name: {"sha256": dic_output_hash, "rows": len(dic_rows)}},
                "limitations": [
                    "Only two candidate-name matches were located in the register; absence of other name matches is not evidence that those facilities are absent.",
                    "Sud Chemie row has no plot number printed; retain the plot field blank.",
                    "TMS plot 28 is not geographically georeferenced here. No candidate latitude/longitude was derived or verified.",
                    "The source's Working status is historical to the register date and does not establish current operations, consent, or emissions.",
                ],
            },
        },
        "analysis_boundary": "The Eloor series is eligible for descriptive ambient-air summaries with the stated caveats. Neither source provides facility-level stack emissions or candidate coordinates; source attribution remains unsupported.",
    }
    metadata_path = OUTPUT_AIR / "kspcb_caaqms_eloor_2026-09.metadata.json"
    metadata_bytes = (json.dumps(metadata, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    metadata_hash = _preserve_or_write(metadata_path, metadata_bytes)
    print(json.dumps({"air_outputs": air_hashes, "dic_output": {"file": dic_name, "sha256": dic_output_hash, "rows": len(dic_rows)}, "metadata": {"file": str(metadata_path.relative_to(ROOT)), "sha256": metadata_hash}}, indent=2))


if __name__ == "__main__":
    main()

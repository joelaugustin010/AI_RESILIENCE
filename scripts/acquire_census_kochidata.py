"""Acquire and inspect official 2011 Census of India Ernakulam handbook files."""

from __future__ import annotations

import hashlib
import json
import urllib.request
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "raw" / "experimental" / "kochidata_2026-11-02"
USER_AGENT = "AI_RESILIENCE public data foundation research"

DATASETS: tuple[dict[str, Any], ...] = (
    {
        "id": "census_2011_ernakulam_dchb_part_a",
        "filename": "census_2011_ernakulam_dchb_part_a.pdf",
        "url": "https://censusindia.gov.in/nada/index.php/catalog/644/download/2224/DH_2011_3208_PART_A_DCHB_ERNAKULAM.pdf",
        "catalog_url": "https://censusindia.gov.in/nada/index.php/catalog/644",
        "publication_date": "2014",
        "coverage": "Ernakulam district; Census 2011 village and town directory, including facility/amenity tables.",
        "license": "No explicit reuse licence was found on the catalog record; preserve for research and confirm terms before redistribution.",
        "format": "pdf",
    },
    {
        "id": "census_2011_ernakulam_dchb_part_b",
        "filename": "census_2011_ernakulam_dchb_part_b.pdf",
        "url": "https://censusindia.gov.in/nada/index.php/catalog/645/download/2228/DH_2011_3208_PART_B_DCHB_ERNAKULAM.pdf",
        "catalog_url": "https://censusindia.gov.in/nada/index.php/catalog/645",
        "publication_date": "2014",
        "coverage": "Ernakulam district; Census 2011 village and town Primary Census Abstract, population and household tables.",
        "license": "No explicit reuse licence was found on the catalog record; preserve for research and confirm terms before redistribution.",
        "format": "pdf",
    },
    {
        "id": "census_2011_kerala_town_directory_tables",
        "filename": "census_2011_kerala_town_directory.xlsx",
        "url": "https://censusindia.gov.in/nada/index.php/catalog/644/download/2227/DH_2011_DCHB_Town_Release_3200.xlsx",
        "catalog_url": "https://censusindia.gov.in/nada/index.php/catalog/644",
        "publication_date": "2011 census; release date not stated in the file.",
        "coverage": "Kerala-wide town directory workbook; Ernakulam/Kochi rows require sheet-level filtering.",
        "license": "No explicit reuse licence was found on the catalog record; preserve for research and confirm terms before redistribution.",
        "format": "xlsx",
    },
    {
        "id": "census_2011_kerala_village_directory_tables",
        "filename": "census_2011_kerala_village_directory.xlsx",
        "url": "https://censusindia.gov.in/nada/index.php/catalog/644/download/2226/DH_2011_DCHB_Village_Release_3200.xlsx",
        "catalog_url": "https://censusindia.gov.in/nada/index.php/catalog/644",
        "publication_date": "2011 census; release date not stated in the file.",
        "coverage": "Kerala-wide village directory workbook; Ernakulam rows require sheet-level filtering.",
        "license": "No explicit reuse licence was found on the catalog record; preserve for research and confirm terms before redistribution.",
        "format": "xlsx",
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(dataset: dict[str, Any]) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / dataset["filename"]
    if path.exists():
        return path
    partial = path.with_suffix(path.suffix + ".part")
    request = urllib.request.Request(
        dataset["url"], headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Unexpected HTTP status {response.status} for {dataset['id']}."
                )
            with partial.open("xb") as target:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
            expected = response.headers.get("Content-Length")
            content_type = response.headers.get("Content-Type")
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    if not partial.is_file() or partial.stat().st_size == 0:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Empty download for {dataset['id']}.")
    if expected and partial.stat().st_size != int(expected):
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Length mismatch for {dataset['id']}.")
    partial.replace(path)
    dataset["_content_type"] = content_type
    return path


def _validate_pdf(path: Path) -> dict[str, Any]:
    reader = PdfReader(str(path), strict=True)
    if reader.is_encrypted:
        raise RuntimeError(f"Encrypted PDF: {path.name}.")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return {
        "pages": len(reader.pages),
        "metadata": {
            str(key): str(value) for key, value in (reader.metadata or {}).items()
        },
        "contains_ernakulam_text": "ernakulam" in text.casefold(),
        "text_characters_extracted": len(text),
    }


def _validate_xlsx(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"XLSX ZIP CRC failed for {bad_member}.")
        if "xl/workbook.xml" not in archive.namelist():
            raise RuntimeError(f"Not an XLSX workbook: {path.name}.")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        workbook = load_workbook(path, read_only=True, data_only=True)
        sheets: list[dict[str, Any]] = []
        ernakulam_matches: list[dict[str, Any]] = []
        for worksheet in workbook.worksheets:
            row_count = 0
            first_rows: list[list[str | int | float | None]] = []
            for row in worksheet.iter_rows(values_only=True):
                row_count += 1
                values = [value for value in row]
                if row_count <= 5:
                    first_rows.append(values[:12])
                if any(
                    isinstance(value, str) and "ernakulam" in value.casefold()
                    for value in values
                ):
                    ernakulam_matches.append(
                        {
                            "sheet": worksheet.title,
                            "row": row_count,
                            "values": [str(value)[:160] if value is not None else None for value in values[:12]],
                        }
                    )
            sheets.append(
                {
                    "name": worksheet.title,
                    "rows_iterated": row_count,
                    "dimensions": worksheet.calculate_dimension(),
                    "first_rows": first_rows,
                }
            )
        parser_warnings = sorted({str(item.message) for item in caught})
    workbook.close()
    return {
        "zip_crc": "passed",
        "sheet_count": len(sheets),
        "sheets": sheets,
        "ernakulam_text_match_count": len(ernakulam_matches),
        "ernakulam_matches_sample": ernakulam_matches[:20],
        "crs": "Not applicable; tabular administrative statistics, no spatial geometry.",
        "parser_warnings": parser_warnings,
    }


def validate(path: Path, dataset: dict[str, Any]) -> dict[str, Any]:
    if dataset["format"] == "pdf":
        return _validate_pdf(path)
    if dataset["format"] == "xlsx":
        return _validate_xlsx(path)
    raise ValueError(f"Unsupported format: {dataset['format']}")


def acquire() -> list[dict[str, Any]]:
    results = []
    for dataset in DATASETS:
        path = _download(dataset)
        checksum = _sha256(path)
        qa = validate(path, dataset)
        metadata = {
            key: value
            for key, value in dataset.items()
            if not key.startswith("_")
        }
        metadata.update(
            {
                "publisher": "Office of the Registrar General & Census Commissioner, India; Directorate of Census Operations, Kerala",
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "local_file": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": checksum,
                "http_content_type": dataset.get("_content_type"),
                "verification_status": "official_catalog_downloaded_structurally_inspected_research_only",
                "units": "Census counts/administrative directory attributes; variable-specific definitions are in the source workbook/publication.",
                "crs": "Not applicable to handbook tables; no GIS geometry acquired.",
                "quality_validation": qa,
                "not_integrated_reason": "Census 2011 is historical and not a current geospatial layer; reuse terms and local applicability require confirmation.",
            }
        )
        sidecar = path.with_name(path.name + ".metadata.json")
        if sidecar.exists():
            existing = json.loads(sidecar.read_text(encoding="utf-8"))
            if existing.get("sha256") != checksum:
                raise RuntimeError(f"Refusing to overwrite conflicting sidecar: {sidecar}.")
            existing["quality_validation"] = qa
            existing["validation_updated_at_utc"] = datetime.now(timezone.utc).isoformat()
            metadata = existing
            sidecar.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        else:
            sidecar.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        results.append(
            {
                "dataset_id": dataset["id"],
                "local_file": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": checksum,
                "validation_summary": (
                    {
                        "pages": qa["pages"],
                        "contains_ernakulam_text": qa["contains_ernakulam_text"],
                    }
                    if dataset["format"] == "pdf"
                    else {
                        "sheet_count": qa["sheet_count"],
                        "ernakulam_text_match_count": qa["ernakulam_text_match_count"],
                        "sheet_rows": {
                            sheet["name"]: sheet["rows_iterated"]
                            for sheet in qa["sheets"]
                        },
                    }
                ),
            }
        )
    return results


if __name__ == "__main__":
    for result in acquire():
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))

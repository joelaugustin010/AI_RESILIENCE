"""Read-only provenance audit for recovered research and source catalogs."""
from __future__ import annotations

import hashlib
import html.parser
import importlib.util
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DATA_STATUS_DEFINITIONS = {
    "verified": "Source identity, integrity, schema, dates/coverage, units and spatial meaning support the stated limited use.",
    "provisional": "Source identity or integrity is supported, but a material metadata, coverage, quality, reuse or interpretation gap remains.",
    "unavailable": "The source or a required input was not obtained or is missing from this checkout.",
    "unsuitable": "The file or evidence is invalid, or it cannot support the proposed analysis without unsupported assumptions.",
}


def _pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-standard JSON constant is not allowed: {value}")


def read_json_strict(path: Path) -> Any:
    """Read UTF-8 JSON and reject duplicate keys and NaN/Infinity."""
    return json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=_pairs_without_duplicates,
        parse_constant=_reject_constant,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_retrieval_date(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        if "T" in value or " " in value:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            return parsed.tzinfo is not None and parsed.utcoffset() is not None
        date.fromisoformat(value.strip())
        return True
    except ValueError:
        return False


def _metadata_checks(path: Path, metadata: dict[str, Any]) -> tuple[dict[str, str], list[str], list[str]]:
    checks: dict[str, str] = {}
    errors: list[str] = []
    warnings: list[str] = []
    expected = metadata.get("raw_sha256", metadata.get("sha256"))
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        checks["sha256"] = "missing"
        errors.append("No valid SHA-256 is recorded in source metadata.")
    else:
        checks["sha256"] = "passed" if sha256_file(path).casefold() == expected.casefold() else "failed"
        if checks["sha256"] == "failed":
            errors.append("Source SHA-256 does not match provenance metadata.")

    size = metadata.get("raw_bytes", metadata.get("bytes"))
    if isinstance(size, int) and not isinstance(size, bool):
        checks["byte_count"] = "passed" if path.stat().st_size == size else "failed"
        if checks["byte_count"] == "failed":
            errors.append("Source byte count does not match provenance metadata.")
    else:
        checks["byte_count"] = "not recorded"
        warnings.append("Source byte count is not recorded.")

    if isinstance(metadata.get("publisher"), str) and metadata["publisher"].strip():
        checks["publisher"] = "passed"
    else:
        checks["publisher"] = "missing"
        errors.append("Publisher is missing from provenance metadata.")

    source_url = metadata.get("source_url", metadata.get("url"))
    parsed = urlparse(source_url) if isinstance(source_url, str) else None
    if parsed and parsed.scheme == "https" and parsed.hostname:
        checks["source_url"] = "passed"
    else:
        checks["source_url"] = "missing or non-HTTPS"
        warnings.append("An HTTPS source URL is not recorded.")

    retrieved = metadata.get("retrieved_at_utc", metadata.get("retrieved_on"))
    checks["retrieval_date"] = "passed" if _valid_retrieval_date(retrieved) else "missing or invalid"
    if retrieved and checks["retrieval_date"] != "passed":
        errors.append("Retrieval date is invalid.")
    elif checks["retrieval_date"] != "passed":
        warnings.append("A valid retrieval date is not recorded.")

    terms = metadata.get("reuse_terms", metadata.get("license", metadata.get("licence")))
    known_terms = isinstance(terms, str) and terms.strip() and not any(
        marker in terms.casefold()
        for marker in ("not identified", "not located", "no dataset-specific")
    )
    checks["reuse_terms"] = "recorded" if known_terms else "unresolved"
    if not known_terms:
        warnings.append("Dataset-specific reuse terms are not established.")
    return checks, errors, warnings


def validate_annual_aqi_file(raw_path: Path, metadata_path: Path) -> dict[str, Any]:
    """Validate one annual AQI summary without inventing dates or locations."""
    raw_path, metadata_path = Path(raw_path), Path(metadata_path)
    result: dict[str, Any] = {
        "status": "unavailable",
        "checks": {"raw_file": "missing"},
        "errors": [],
        "warnings": [],
        "row_count": None,
        "year_label": None,
        "station_names": [],
        "measurement_kind": "source-reported annual average AQI index",
    }
    if not raw_path.is_file():
        result["warnings"].append(f"Raw source is unavailable: {raw_path.name}")
        return result
    result["checks"]["raw_file"] = "present"
    if not metadata_path.is_file():
        result["status"] = "unsuitable"
        result["errors"].append("Provenance sidecar is missing.")
        return result
    try:
        metadata = read_json_strict(metadata_path)
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a JSON object.")
        checks, errors, warnings = _metadata_checks(raw_path, metadata)
        result["checks"].update(checks)
        result["errors"].extend(errors)
        result["warnings"].extend(warnings)

        year = metadata.get("year_label")
        result["year_label"] = year
        match = re.search(r"kspcb_annual_aqi_(\d{4})_", raw_path.name)
        result["checks"]["year_label"] = (
            "passed" if isinstance(year, int) and match and int(match.group(1)) == year else "failed"
        )
        if result["checks"]["year_label"] == "failed":
            result["errors"].append("Year label does not match the filename.")

        payload = json.loads(
            raw_path.read_bytes().decode("utf-8"),
            object_pairs_hook=_pairs_without_duplicates,
            parse_constant=_reject_constant,
        )
        if not isinstance(payload, dict):
            raise ValueError("Payload root must be a JSON object.")
        if payload.get("aqi_data") is not None and not isinstance(payload.get("aqi_data"), dict):
            raise ValueError("aqi_data must be an object or null.")
        rows = payload.get("station_data")
        if not isinstance(rows, list) or not rows:
            raise ValueError("Payload must contain a non-empty station_data list.")

        seen: set[tuple[str, str]] = set()
        stations: set[str] = set()
        missing_codes = 0
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(f"Station row {index} is not an object.")
            station, mode = row.get("station_name"), row.get("mode")
            if not isinstance(station, str) or not station.strip():
                raise ValueError(f"Station row {index} has no station_name.")
            if not isinstance(mode, str) or not mode.strip():
                raise ValueError(f"Station row {index} has no monitoring mode.")
            identity = (re.sub(r"[^A-Z0-9]", "", station.upper()), mode.strip().upper())
            if identity in seen:
                raise ValueError(f"Duplicate station summary: {station!r} / {mode!r}.")
            seen.add(identity)
            stations.add(station.strip())
            value = row.get("average_aqi")
            try:
                number = float(value)
            except (TypeError, ValueError, OverflowError) as error:
                raise ValueError(f"Station row {index} has an invalid average_aqi.") from error
            if isinstance(value, bool) or not math.isfinite(number) or not 0 <= number <= 500:
                raise ValueError(f"Station row {index} average_aqi is outside 0-500 or nonfinite.")
            code = row.get("stn_code")
            if code is None or not str(code).strip() or str(code).strip().casefold() == "nil":
                missing_codes += 1

        if metadata.get("validated_station_rows") not in (None, len(rows)):
            raise ValueError("validated_station_rows does not match the payload.")
        result["checks"]["strict_json"] = "passed"
        result["checks"]["schema_and_values"] = "passed"
        result["row_count"] = len(rows)
        result["station_names"] = sorted(stations)
        result["rows_missing_station_code"] = missing_codes
        result["geographic_coverage"] = metadata.get(
            "geographic_coverage", "KSPCB statewide rows; exact locations are not provided."
        )
        result["units"] = metadata.get("units", "AQI index (dimensionless)")
        result["reporting_period"] = f"Year label {year}; exact aggregation cutoff not supplied."
        result["warnings"].append("Annual AQI summaries are not pollutant concentrations or timestamped observations.")
        result["warnings"].append("Station names do not establish station coordinates or a Kochi-only spatial subset.")
        if "not supplied" in str(metadata.get("period_cutoff", "")).casefold():
            result["warnings"].append("The annual aggregation cutoff is not stated; 2026 may be partial-year.")
        if missing_codes:
            result["warnings"].append(f"{missing_codes} row(s) do not provide a usable station code.")
        result["status"] = "provisional" if not result["errors"] else "unsuitable"
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as error:
        result["status"] = "unsuitable"
        result["errors"].append(str(error))
        result["checks"].setdefault("strict_json", "failed")
    return result


class _HtmlSummary(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables = self.rows = self.forms = self.controls = self.scripts = 0
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        attributes = dict(attrs)
        if tag == "table":
            self.tables += 1
        elif tag == "tr":
            self.rows += 1
        elif tag == "form":
            self.forms += 1
        elif tag in {"input", "textarea", "select"}:
            self.controls += 1
        elif tag == "script":
            self.scripts += 1
        elif tag == "a" and attributes.get("href"):
            self.links.append(str(attributes["href"]))


def validate_pdf_file(path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    path = Path(path)
    result: dict[str, Any] = {
        "status": "provisional", "checks": {}, "errors": [], "warnings": [],
        "page_count": None, "text_characters": None,
    }
    if not path.is_file():
        result["status"] = "unavailable"
        result["warnings"].append("PDF source is missing.")
        return result
    if not path.read_bytes()[:8].startswith(b"%PDF-"):
        result.update(status="unsuitable", checks={"pdf_signature": "failed"})
        result["errors"].append("The .pdf file does not begin with a PDF signature.")
        return result
    result["checks"]["pdf_signature"] = "passed"
    checks, errors, warnings = _metadata_checks(path, metadata)
    result["checks"].update(checks)
    result["errors"].extend(errors)
    result["warnings"].extend(warnings)
    if importlib.util.find_spec("pypdf") is not None:
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path), strict=True)
            result["page_count"] = len(reader.pages)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            result["text_characters"] = len(text)
            result["checks"]["pdf_structure"] = "passed" if reader.pages else "failed"
            if not reader.pages:
                result["errors"].append("PDF parser found no pages.")
            markers = (metadata.get("source_text_validation") or {}).get("expected_markers", [])
            normalized = " ".join(text.casefold().split())
            missing = [str(marker) for marker in markers if str(marker).casefold() not in normalized]
            if markers:
                result["checks"]["text_markers"] = "passed" if not missing else "failed"
                if missing:
                    result["errors"].append("Expected source text markers are absent: " + ", ".join(missing))
        except Exception as error:
            result["checks"]["pdf_structure"] = "failed"
            result["errors"].append(f"PDF parsing failed: {type(error).__name__}: {error}")
    else:
        prior = metadata.get("source_text_validation") or {}
        result["page_count"] = metadata.get("pages")
        if isinstance(prior, dict) and prior.get("passed") is True:
            result["text_characters"] = prior.get("characters")
            result["checks"]["prior_text_validation"] = "recorded but not rerun locally"
        else:
            result["checks"]["pdf_structure"] = "not checked"
        result["warnings"].append("Optional pypdf is not installed; current PDF structure/text extraction was not rerun.")
    if result["errors"]:
        result["status"] = "unsuitable"
    return result


def validate_dwg_file(path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    path = Path(path)
    result: dict[str, Any] = {"status": "provisional", "checks": {}, "errors": [], "warnings": []}
    if not path.is_file():
        result["status"] = "unavailable"
        result["warnings"].append("DWG source is missing.")
        return result
    signature = path.read_bytes()[:6].decode("ascii", "replace")
    expected = str(metadata.get("drawing_format_signature", "AC1018"))
    expected_code = re.search(r"AC\d{4}", expected)
    expected_code = expected_code.group(0) if expected_code else expected
    result["checks"]["dwg_signature"] = "passed" if signature == expected_code else "failed"
    if signature != expected_code:
        result["errors"].append("DWG signature does not match provenance metadata.")
    checks, errors, warnings = _metadata_checks(path, metadata)
    result["checks"].update(checks)
    result["errors"].extend(errors)
    result["warnings"].extend(warnings)
    result["warnings"].append("No compatible DWG/GIS parser is available; CRS, extent, layers and plot geometry remain unverified.")
    if result["errors"]:
        result["status"] = "unsuitable"
    return result


def validate_html_file(path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
    path = Path(path)
    result: dict[str, Any] = {"status": "provisional", "checks": {}, "errors": [], "warnings": [], "html_summary": {}}
    if not path.is_file():
        result["status"] = "unavailable"
        result["warnings"].append("HTML source is missing.")
        return result
    checks, errors, warnings = _metadata_checks(path, metadata)
    result["checks"].update(checks)
    result["errors"].extend(errors)
    result["warnings"].extend(warnings)
    try:
        parser = _HtmlSummary()
        parser.feed(path.read_text(encoding="utf-8"))
        hosts = sorted({
            urlparse(link).hostname for link in parser.links
            if urlparse(link).scheme in {"http", "https"} and urlparse(link).hostname
        })
        result["checks"]["html_parse"] = "passed"
        result["html_summary"] = {
            "table_count": parser.tables, "row_count": parser.rows,
            "form_count": parser.forms, "input_control_count": parser.controls,
            "script_count": parser.scripts, "external_link_hosts": hosts,
        }
        result["warnings"].append("Historical application listing only; it is not a current consent certificate.")
        result["warnings"].append("Raw HTML is not rendered; only source metadata and aggregate QA are exposed.")
    except (OSError, UnicodeDecodeError, ValueError) as error:
        result["checks"]["html_parse"] = "failed"
        result["errors"].append(f"HTML parsing failed: {error}")
    if result["errors"]:
        result["status"] = "unsuitable"
    return result


def _source_specs(root: Path) -> list[dict[str, Any]]:
    annual_path = root / "data/processed/air_quality/kspcb_annual_aqi.metadata.json"
    try:
        annual_manifest = read_json_strict(annual_path) if annual_path.is_file() else {}
    except (OSError, ValueError, json.JSONDecodeError):
        annual_manifest = {}
    annual_outputs = {}
    if annual_manifest.get("processed_file") and annual_manifest.get("processed_sha256"):
        annual_outputs[f"data/processed/air_quality/{annual_manifest['processed_file']}"] = {
            "sha256": annual_manifest["processed_sha256"],
            "rows": annual_manifest.get("rows"),
        }
    specs: list[dict[str, Any]] = []
    for item in annual_manifest.get("raw_files", []):
        rel = (Path("data/raw/air_quality") / str(item.get("path", ""))).as_posix()
        specs.append({
            "dataset_id": f"kspcb_annual_aqi_{item.get('year', 'unknown')}",
            "name": f"KSPCB annual average AQI summary ({item.get('year', 'year unknown')} label)",
            "kind": "annual_aqi", "path": rel,
            "metadata_path": str(Path(rel).with_suffix(".metadata.json")).replace("\\", "/"),
            "expected_metadata": None, "default_status": "provisional",
            "processing": "src.air_quality_sources.prepare_kspcb_annual_aqi; exact station/program name match; no interpolation.",
            "derived_outputs": annual_outputs,
            "intended_use": "Descriptive statewide source-reported annual AQI summary.",
            "limitations": ["No timestamps, exact cutoff, pollutant concentrations or station coordinates.", "Dataset-specific reuse terms were not located."],
        })

    report_path = root / "data/processed/air_quality/kspcb_air_reports.metadata.json"
    try:
        reports = read_json_strict(report_path).get("sources", {}) if report_path.is_file() else {}
    except (OSError, ValueError, json.JSONDecodeError, AttributeError):
        reports = {}
    report_specs = [
        ("daily_aqi", "kspcb_daily_aqi_2026-10-16", "KSPCB daily AQI report (16 Oct 2026)", "data/raw/air_quality_reports/KSPCB_AQI_daily_average_2026-10-16.pdf", "provisional", "Single historical day; exact averaging/completeness metadata and station coordinates are absent."),
        ("monthly_caaqms", "kspcb_eloor_caaqms_2026_08", "KSPCB Eloor CAAQMS report (Aug 2026)", "data/raw/air_quality_reports/KSPCB_CAAQMS_monthly_report_2026-08.pdf", "provisional", "Exact averaging intervals, row-level QA and station coordinates are absent."),
        ("namp", "kspcb_namp_ernakulam_2025_06", "KSPCB NAMP Ernakulam report (pages state June 2025)", "data/raw/air_quality_reports/KSPCB_NAMP_report_2025-08.pdf", "unsuitable", "Directory says August 2025 while report pages say June; units and CRS are absent, so values are excluded."),
    ]
    for meta_key, dataset_id, name, path, status, limitation in report_specs:
        meta = reports.get(meta_key, {})
        specs.append({
            "dataset_id": dataset_id, "name": name, "kind": "pdf", "path": path,
            "metadata_path": None, "expected_metadata": meta,
            "default_status": status,
            "processing": "scripts/prepare_kspcb_air_reports.py; pypdf extraction into source-linked CSVs.",
            "intended_use": "Historical source-report context only.", "limitations": [limitation],
            "reporting_period": {
                "daily_aqi": "2026-10-16",
                "monthly_caaqms": "2026-08-01 through 2026-08-31",
                "namp": "Directory label August 2025; report pages state June 2025",
            }.get(meta_key),
            "geographic_coverage": {
                "daily_aqi": "Five source-reported station rows statewide; Eloor is in Ernakulam.",
                "monthly_caaqms": "KSPCB report pages include five stations; the extracted Ernakulam series is Eloor.",
                "namp": "Eight Ernakulam stations; 62 dated rows stated in the existing extract metadata.",
            }.get(meta_key),
            "units": {
                "daily_aqi": "AQI index and pollutant units as printed in the report/extract.",
                "monthly_caaqms": "Pollutant units as printed; exact averaging windows are unstated.",
                "namp": "Not stated in the report metadata; excluded from concentration analysis.",
            }.get(meta_key),
        })

    prepared_path = root / "data/processed/air_quality/kspcb_caaqms_eloor_2026-09.metadata.json"
    try:
        prepared_sources = read_json_strict(prepared_path).get("sources", {}) if prepared_path.is_file() else {}
    except (OSError, ValueError, json.JSONDecodeError, AttributeError):
        prepared_sources = {}
    direct = [
        ("kspcb_eloor_caaqms_2026_09", "KSPCB Eloor CAAQMS report (Sep 2026)", "data/raw/air_quality_reports/KSPCB_CAAQMS_monthly_report_2026-09.pdf", "pdf", "provisional", "Daily summary only; averaging intervals, row QA and verified station coordinates are absent.", prepared_sources.get("kspcb_caaqms_eloor_2026_09", {}), "data/processed/air_quality"),
        ("dic_edayar_allotment_2022", "DIC Edayar allotment register (2022)", "data/raw/industrial/DIC_DA_Edayar_allotment_details_2022.pdf", "pdf", "provisional", "Historical name/plot context only; not current occupancy, coordinates or emissions evidence.", prepared_sources.get("dic_edayar_allotment_2022", {}), "data/processed/industrial"),
        ("kwa_edayar_cetp_2022", "KWA Edayar CETP report (2021/2022)", "data/raw/industrial/KWA_Edayar_CETP_DER_2022.pdf", "pdf", "provisional", "Effluent planning context is not air-emissions evidence and gives no firm-level coordinates.", {}, "data/processed/industrial"),
        ("dic_edayar_site_plan", "DIC Edayar AutoCAD plan", "data/raw/industrial/DIC_DA_EDAYAR.dwg", "dwg", "provisional", "No parser/CRS/extent or company-to-plot relation has been validated.", {}, "data/processed/industrial"),
        ("kspcb_ocmms_historical_cto_listing", "KSPCB legacy CTO application listing (2015-2019)", "data/raw/industrial/KSPCB_OCMMS_CTO_red_page2_2015-2019.html", "html", "provisional", "Historical application decisions do not establish current consent validity or emissions.", {}, "data/processed/industrial"),
    ]
    for dataset_id, name, path, kind, status, limitation, processed_metadata, output_directory in direct:
        raw_metadata_path = root / f"{path}.metadata.json"
        try:
            raw_metadata = read_json_strict(raw_metadata_path) if raw_metadata_path.is_file() else {}
        except (OSError, ValueError, json.JSONDecodeError):
            raw_metadata = {}
        combined_metadata = {**raw_metadata, **processed_metadata}
        specs.append({
            "dataset_id": dataset_id, "name": name, "kind": kind, "path": path,
            "metadata_path": path + ".metadata.json", "expected_metadata": combined_metadata,
            "default_status": status,
            "processing": {
                "kspcb_eloor_caaqms_2026_09": "scripts/prepare_new_official_air_evidence.py; validated Eloor daily extracts.",
                "dic_edayar_allotment_2022": "scripts/prepare_new_official_air_evidence.py; two manually checked historical rows.",
                "kwa_edayar_cetp_2022": "No operational extract; retained for historical effluent context.",
                "dic_edayar_site_plan": "No conversion performed; no CRS or plot geometry asserted.",
                "kspcb_ocmms_historical_cto_listing": "Read-only HTML structural audit; source rows are not used for current status.",
            }.get(dataset_id),
            "output_directory": output_directory,
            "reporting_period": {
                "kwa_edayar_cetp_2022": "Prepared August 2021; approved 2022-06-01",
                "dic_edayar_site_plan": "Drawing metadata date 2021-05-25",
                "kspcb_ocmms_historical_cto_listing": "2015-04-01 through 2019-10-20 query window",
            }.get(dataset_id),
            "geographic_coverage": {
                "kspcb_eloor_caaqms_2026_09": "Eloor CAAQMS, Ernakulam; 30 dated daily records.",
                "dic_edayar_allotment_2022": "Edayar DA/DP historical plot allotment register.",
                "kwa_edayar_cetp_2022": "Edayar industrial estate / Eloor-Edayar belt; no firm-level coordinates.",
                "dic_edayar_site_plan": "Edayar DA; drawing extent and CRS not verified.",
                "kspcb_ocmms_historical_cto_listing": "Kerala red-category CTO applications; selected historical Edayar records.",
            }.get(dataset_id),
            "units": {
                "dic_edayar_site_plan": "CAD drawing units/scale not established.",
                "kspcb_ocmms_historical_cto_listing": "Not applicable; application dates/status fields.",
            }.get(dataset_id),
            "intended_use": "Historical or contextual evidence only.", "limitations": [limitation],
        })
    return specs


def _normal_status(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if text in DATA_STATUS_DEFINITIONS:
        return text
    if "unsuitable" in text:
        return "unsuitable"
    if any(token in text for token in ("unavailable", "not obtained", "not acquired", "blocked", "not ingested")):
        return "unavailable"
    if "verified" in text and "unverified" not in text:
        return "verified"
    return "provisional"


def _audit_derived_outputs(root: Path, spec: dict[str, Any], metadata: dict[str, Any]) -> list[dict[str, Any]]:
    outputs = spec.get("derived_outputs") or metadata.get("outputs") or {}
    if not isinstance(outputs, dict):
        return []
    checked = []
    for name, details in outputs.items():
        details = details if isinstance(details, dict) else {}
        relative = Path(str(name))
        if relative.is_absolute() or ".." in relative.parts:
            checked.append({"path": str(name), "status": "invalid path"})
            continue
        if not str(name).startswith("data/"):
            relative = Path(spec.get("output_directory", "data/processed/air_quality")) / relative
        output_path = root / relative
        expected = details.get("sha256")
        if not output_path.is_file():
            actual = None
            status = "missing"
        else:
            actual = sha256_file(output_path)
            status = "passed" if isinstance(expected, str) and actual.casefold() == expected.casefold() else "failed"
        checked.append({
            "path": relative.as_posix(),
            "expected_sha256": expected,
            "actual_sha256": actual,
            "rows": details.get("rows"),
            "status": status,
        })
    return checked


def _catalog_records(root: Path, relative: str, key: str, id_key: str, kind: str) -> tuple[list[dict[str, Any]], list[str]]:
    path = root / relative
    if not path.is_file():
        return [], [f"Missing source catalog: {relative}"]
    try:
        catalog = read_json_strict(path)
        entries = catalog.get(key)
        if not isinstance(entries, list):
            raise ValueError(f"Expected {key} list.")
        records = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise ValueError(f"{key}[{index}] must be an object.")
            status = entry.get("evidence_status", entry.get("validation_status", entry.get("status")))
            records.append({
                "dataset_id": entry.get("dataset_id", entry.get(id_key, f"{kind}_{index + 1}")),
                "name": entry.get("title", entry.get("publisher", f"{kind} source {index + 1}")),
                "publisher": entry.get("publisher"), "source_url": entry.get("source_url", entry.get("url")),
                "status": _normal_status(status), "reported_status": status,
                "reporting_period": entry.get("publication_date"),
                "geographic_coverage": entry.get("geographic_coverage"),
                "units": entry.get("units"), "crs": entry.get("crs"),
                "license": entry.get("license", entry.get("reuse_terms", entry.get("licence"))),
                "local_file": entry.get("local_file", entry.get("raw_file", entry.get("processed_file"))),
                "blocker": entry.get("blocker"), "limitations": entry.get("limitations", []),
            })
        return records, []
    except (OSError, ValueError, json.JSONDecodeError, AttributeError) as error:
        return [], [f"Could not validate {relative}: {error}"]


def build_ingestion_report(root: Path, *, validated_at_utc: str | None = None) -> dict[str, Any]:
    """Build a live machine-readable report; never downloads or writes data."""
    root = Path(root)
    timestamp = validated_at_utc or datetime.now(timezone.utc).isoformat(timespec="seconds")
    recovered: list[dict[str, Any]] = []
    for spec in _source_specs(root):
        path = root / spec["path"]
        metadata = spec.get("expected_metadata")
        metadata_path = root / spec["metadata_path"] if spec.get("metadata_path") else None
        metadata_error = None
        if metadata is None:
            if metadata_path and metadata_path.is_file():
                try:
                    metadata = read_json_strict(metadata_path)
                except (OSError, ValueError, json.JSONDecodeError) as error:
                    metadata, metadata_error = {}, str(error)
            else:
                metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        if spec["kind"] == "annual_aqi":
            validation = validate_annual_aqi_file(path, metadata_path) if metadata_path else {"status": "unavailable", "checks": {}, "errors": [], "warnings": []}
        elif spec["kind"] == "pdf":
            validation = validate_pdf_file(path, metadata)
        elif spec["kind"] == "dwg":
            validation = validate_dwg_file(path, metadata)
        else:
            validation = validate_html_file(path, metadata)
        if metadata_error:
            validation["status"] = "unsuitable"
            validation["errors"].append(f"Invalid provenance JSON: {metadata_error}")
        elif (
            not validation.get("errors")
            and validation["status"] != "unavailable"
            and spec.get("default_status") == "unsuitable"
        ):
            validation["status"] = "unsuitable"

        license_terms = metadata.get("reuse_terms", metadata.get("license", metadata.get("licence")))
        limits = list(spec["limitations"])
        if isinstance(metadata.get("limitations"), list):
            limits.extend(metadata["limitations"])
        recovered.append({
            "dataset_id": spec["dataset_id"], "name": spec["name"],
            "publisher": metadata.get("publisher"),
            "source_url": metadata.get("source_url", metadata.get("url")),
            "retrieved_at": metadata.get("retrieved_at_utc", metadata.get("retrieved_on")),
            "publication_date": metadata.get("publication_date"),
            "reporting_period": (
                f"{metadata['time_coverage'].get('start')} through {metadata['time_coverage'].get('end')}"
                if isinstance(metadata.get("time_coverage"), dict)
                and metadata["time_coverage"].get("start")
                and metadata["time_coverage"].get("end")
                else metadata.get("publication_date", metadata.get("report_date", metadata.get("year_label", spec.get("reporting_period"))))
            ) or spec.get("reporting_period"),
            "geographic_coverage": (
                f"{metadata['time_coverage'].get('station')} station, {metadata['time_coverage'].get('dated_records')} dated records"
                if isinstance(metadata.get("time_coverage"), dict) and metadata["time_coverage"].get("station")
                else metadata.get("geographic_coverage", metadata.get("coverage")) or spec.get("geographic_coverage")
            ),
            "units": metadata.get("units") or spec.get("units"),
            "crs": metadata.get("crs", metadata.get("coordinate_reference_system")) or "Not stated / not applicable",
            "license": license_terms or "Dataset-specific reuse terms not identified.",
            "original_filename": Path(spec["path"]).name, "storage_location": spec["path"],
            "processing_steps": spec["processing"], "intended_use": spec["intended_use"],
            "documented_derived_outputs": _audit_derived_outputs(root, spec, metadata),
            "status": validation["status"], "validation_checks": validation.get("checks", {}),
            "validation_errors": validation.get("errors", []), "validation_warnings": validation.get("warnings", []),
            "last_successful_validation_utc": timestamp if not validation.get("errors") and validation["status"] != "unavailable" else None,
            "known_limitations": list(dict.fromkeys(limits)), "row_count": validation.get("row_count"),
            "station_names": validation.get("station_names", []), "html_summary": validation.get("html_summary", {}),
            "page_count": validation.get("page_count"), "text_characters": validation.get("text_characters"),
        })

    spatial, spatial_errors = _catalog_records(root, "data/reference/spatial_sources.json", "datasets", "layer_id", "spatial")
    air, air_errors = _catalog_records(root, "data/reference/air_quality_acquisition.json", "sources", "dataset_id", "air")
    return {
        "schema_version": 1, "validated_at_utc": timestamp,
        "status_definitions": DATA_STATUS_DEFINITIONS,
        "recovered_sources": recovered, "spatial_catalog": spatial, "air_quality_catalog": air,
        "catalog_errors": spatial_errors + air_errors,
        "flood_analysis": {
            "status": "unavailable", "operational": False,
            "conclusion": "No real asset-to-flood exposure count is currently supported.",
            "available_hazard_context": "The local JRC GloFAS RP100 tiles are modeled river-flood scenario data at about 90 m. Their map preview is withheld because the dataset README specifies ODbL 1.0 while the linked copyright notice specifies CC BY 4.0; no clarification has been obtained. KSDMA historical return-period rasters remain review-only. CWC station metadata and NWIC telemetry listings are hydrology leads only; neither supplies a validated local asset layer or reviewed flood-event labels.",
            "blockers": [
                "KSDMA's historical 10-, 25-, and 50-year archive passes ZIP and GeoTIFF structural checks and declares EPSG:4326 plus a NoData sentinel, but dataset reuse terms and valid pixel-value meaning/units remain undocumented; the rasters are not interpreted, rendered, or overlaid.",
                "The JRC README lists ODbL 1.0 and its linked copyright notice lists CC BY 4.0. The applicable or dual-licence terms have not been clarified; the preview is suppressed and must not be redistributed or publicly deployed until clarified.",
                "CWC's official meteorological-station register (as of 2012-06-01) lists Kalampur, Ramamangalam, and Neeleeswaram in Ernakulam, but does not document a CRS/datum or positional accuracy and is not a current station-status or water-level series.",
                "NWIC's Kerala Surface Water Department portal lists an hourly telemetry CSV resource for 2026–2030, but the resource page could not be retrieved for file integrity, station semantics, CRS/datum, threshold, or reuse validation; it was not acquired or joined.",
                "NIHFW hospital coordinate order, CRS/datum and positional accuracy are undocumented; no hospital points are eligible.",
                "KITE's Sametham school directory exposes school identifiers, local-body fields, and individual Google Maps links, but the reviewed listing has no downloadable GIS export or published CRS/coordinate accuracy; some listings have no map link.",
                "Ernakulam district administration hospital and school directories provide names and addresses, but no reusable coordinates or GIS export with CRS and positional accuracy; addresses were not geocoded.",
                "KSDMA's 2022 flood-probability report is linked as a large PDF and its indexed contents describe school/hospital statistics by local government; the PDF could not be retrieved by the web tool (21,992,376 bytes), and no point geometry or inspected local copy is available.",
                "OSM healthcare, road, and waterway features pass structural and WGS 84 range checks, but remain provisional community-mapped context rather than complete operational asset or drainage inventories.",
                "No directly downloadable Kochi road/drainage layer with dataset-specific schema, CRS, accuracy, date, and reuse terms was verified; the LRIS catalogue lists road, drainage-line, and canal-network themes only.",
                "The available Kochi Corporation outline is provisional and self-intersecting, so it cannot establish the study boundary or complete coverage.",
                "There is no locally validated flood-event extent/depth dataset and authoritative dated hospital/school point inventory eligible for the same spatial analysis.",
            ],
            "next_evidence": [
                "Written KSDMA pixel definitions, units, intended NoData interpretation, and dataset-specific reuse terms for each historical and RCP 8.5 raster product.",
                "Written JRC clarification explaining how the README's ODbL 1.0 statement and linked CC BY 4.0 copyright notice apply to the raster and derived products.",
                "A dated authoritative asset register with stable identifiers, coordinates, coordinate order, CRS/datum, positional accuracy, current status, and reuse terms for hospitals and schools.",
                "A validated study boundary and coverage statement, plus a dated locally relevant hazard dataset covering river, pluvial, and coastal mechanisms as needed.",
                "A directly downloadable municipal road/drainage inventory with schema, condition/capacity fields, CRS, positional accuracy, update date, and reuse terms.",
            ],
        },
        "air_attribution": {
            "status": "unavailable", "operational": False,
            "conclusion": "Historical AQI and ambient reports support descriptive summaries only; industrial source attribution and facility ranking are unsupported.",
            "blockers": [
                "CAAQMS averaging intervals and row-level completeness/QA are not printed in the available reports.",
                "Current facility-specific air consent, measured stack emissions, source signatures and verified facility coordinates are unavailable.",
                "Time-aligned meteorology, background observations and competing-source data are insufficient for source apportionment.",
                "Historical wastewater permissions and CTO application rows are not current air-emissions evidence.",
            ],
        },
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Local data ingestion audit", "", f"Last checked: {report['validated_at_utc']}", "",
        "## Recovered local sources", "",
        "| Dataset | Status | Period | Coverage | SHA / signature | Limitations |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in report["recovered_sources"]:
        checks = item["validation_checks"]
        integrity = checks.get("sha256", checks.get("pdf_signature", checks.get("dwg_signature", "not checked")))
        lines.append(
            f"| {item['name']} | {item['status']} | {item.get('reporting_period') or 'Not established'} "
            f"| {item.get('geographic_coverage') or 'Not established'} | {integrity} "
            f"| {'; '.join(item['known_limitations'])} |"
        )
    lines.extend(["", "## Flood analysis", "", report["flood_analysis"]["conclusion"], ""])
    lines.extend(f"- {item}" for item in report["flood_analysis"]["blockers"])
    lines.extend(["", "## Air-quality attribution", "", report["air_attribution"]["conclusion"], ""])
    lines.extend(f"- {item}" for item in report["air_attribution"]["blockers"])
    return "\n".join(lines) + "\n"

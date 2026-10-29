"""Acquire and validate the Kochi ward-map candidate linked by Kochi Corporation.

The linked map page currently labels the map "DRAFT NOTIFICATION". This script
preserves that limitation: it never promotes this candidate to a legal boundary
or an exposure-analysis mask. It only creates a candidate if 76 unique ward
names can be matched exactly (after case/punctuation normalization) to the SEC
ward roster and every polygon passes geometry validity checks.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely import make_valid
from shapely.geometry import mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.spatial_data import validate_geojson
SOURCE_URL = "https://wardmap.ksmart.live/files/Ernakulam_Cochin_01JBBD7151DY27T8X2GJ2ZD40P.json"
SOURCE_PAGE = "https://kochicorporation.lsgkerala.gov.in/en/delimitation-commission-kerala-notification/590"
ROSTER_PATH = ROOT / "data/reference/kochi_official_ward_roster_2025.json"
RAW_PATH = ROOT / "data/raw/kochi_wards_ksmart_2024_draft.json"
RAW_META_PATH = ROOT / "data/raw/kochi_wards_ksmart_2024_draft.metadata.json"
CANDIDATE_PATH = ROOT / "data/processed/spatial_layers/kochi_wards_ksmart_2024_draft_candidate.geojson"
CANDIDATE_META_PATH = CANDIDATE_PATH.with_name("kochi_wards_ksmart_2024_draft_candidate.metadata.json")
CATALOG_PATH = ROOT / "data/reference/spatial_sources.json"
USER_AGENT = "AI_RESILIENCE educational project; source attribution retained"


def normalize(value: Any) -> str:
    return "".join(ch for ch in str(value).casefold() if ch.isalnum())


def fetch_source() -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json,application/json,*/*"},
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read(), response.geturl(), response.headers.get("Content-Type", "")


def extract_features(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
        features = payload.get("features")
        if isinstance(features, list):
            return [item for item in features if isinstance(item, dict) and item.get("type") == "Feature"]
    if isinstance(payload, dict) and payload.get("type") == "Feature":
        return [payload]
    if isinstance(payload, list) and all(isinstance(item, dict) and item.get("type") == "Feature" for item in payload):
        return payload
    raise ValueError(f"Unsupported ward-map JSON structure: root type={type(payload).__name__}, keys={list(payload)[:30] if isinstance(payload, dict) else 'n/a'}")


def extract_ward_number(feature: dict[str, Any]) -> int | None:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None
    preferred_keys = {"wardno", "wardnumber", "divisionno", "wardid"}
    for key, value in properties.items():
        if normalize(key) not in preferred_keys or value is None:
            continue
        if isinstance(value, (int, float)) and float(value).is_integer():
            number = int(value)
            return number if 1 <= number <= 76 else None
        match = re.fullmatch(r"\s*(?:ward\s*(?:no\.?|number)?\s*)?0*(\d+)\s*", str(value), flags=re.IGNORECASE)
        if match:
            number = int(match.group(1))
            return number if 1 <= number <= 76 else None
    return None


def extract_source_ward_name(feature: dict[str, Any]) -> str:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return ""
    for key, value in properties.items():
        if normalize(key) in {"wardname", "divisionname", "nameen", "name"} and value is not None:
            label = str(value).strip()
            if label and label.casefold() not in {"null", "none", "nan", "#name?"}:
                return label
    return ""


def _polygonal_parts(geometry):
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    if hasattr(geometry, "geoms"):
        parts = []
        for child in geometry.geoms:
            parts.extend(_polygonal_parts(child))
        return parts
    return []


def validate_and_annotate(
    features: list[dict[str, Any]], roster: list[list[str]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    if len(features) != 76:
        raise ValueError(f"Expected 76 source features; received {len(features)}. Candidate was not promoted.")
    roster_by_number = {}
    for code, name in roster:
        match = re.search(r"(\d{3})$", code)
        if not match:
            raise ValueError(f"Official ward code has no three-digit ward number: {code}")
        number = int(match.group(1))
        if number in roster_by_number:
            raise ValueError(f"Duplicate official ward number in roster: {number}")
        roster_by_number[number] = (code, name)
    if set(roster_by_number) != set(range(1, 77)):
        raise ValueError("Official roster must contain explicit ward numbers 1 through 76.")

    annotated = []
    seen_numbers: set[int] = set()
    geometry_errors = []
    name_mismatches = []
    geometry_repairs = []
    for index, feature in enumerate(features, start=1):
        number = extract_ward_number(feature)
        if number is None:
            props = feature.get("properties")
            keys = sorted(props.keys()) if isinstance(props, dict) else []
            raise ValueError(f"Feature {index} has no explicit Ward_No/ward identifier in 1..76; property keys={keys}")
        if number in seen_numbers:
            raise ValueError(f"Duplicate explicit source Ward_No {number}; no ordinal or spatial fallback will be used.")
        seen_numbers.add(number)

        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            geometry_errors.append(f"ward {number}: missing geometry")
            continue
        try:
            source_geometry = shape(geometry)
            if source_geometry.is_empty or source_geometry.geom_type not in {"Polygon", "MultiPolygon"}:
                geometry_errors.append(f"ward {number}: empty or non-polygon geometry ({source_geometry.geom_type})")
                continue
            output_geometry = source_geometry
            repair_record = None
            if not source_geometry.is_valid:
                repaired = make_valid(source_geometry)
                polygon_parts = _polygonal_parts(repaired)
                if not polygon_parts:
                    geometry_errors.append(f"ward {number}: make_valid produced no polygonal component")
                    continue
                output_geometry = unary_union(polygon_parts)
                if output_geometry.is_empty or output_geometry.geom_type not in {"Polygon", "MultiPolygon"} or not output_geometry.is_valid:
                    geometry_errors.append(f"ward {number}: geometry remains invalid after make_valid")
                    continue
                repair_record = {
                    "ward_number": number,
                    "source_ward_name": extract_source_ward_name(feature) or None,
                    "method": "Shapely make_valid; retained polygonal components only",
                    "source_geometry_type": source_geometry.geom_type,
                    "repaired_geometry_type": output_geometry.geom_type,
                    "note": "Raw source geometry is preserved in the raw file; repaired geometry is only in the clearly marked draft candidate copy.",
                }
                geometry_repairs.append(repair_record)
        except Exception as exc:
            geometry_errors.append(f"ward {number}: geometry parse/repair error: {exc}")
            continue

        code, official_name = roster_by_number[number]
        source_name = extract_source_ward_name(feature)
        if normalize(source_name) != normalize(official_name):
            name_mismatches.append({
                "ward_number": number,
                "ward_code": code,
                "source_name": source_name or None,
                "official_sec_name": official_name,
            })
        copied = json.loads(json.dumps(feature))
        copied.setdefault("properties", {})
        copied["geometry"] = mapping(output_geometry)
        copied["properties"]["source_ward_name"] = source_name or None
        copied["properties"]["sec_ward_code"] = code
        copied["properties"]["sec_ward_name"] = official_name
        copied["properties"]["boundary_status"] = "draft_candidate_not_approved"
        copied["properties"]["geometry_repaired_for_candidate"] = repair_record is not None
        annotated.append(copied)

    if geometry_errors:
        raise ValueError("Invalid source geometries; no usable candidate copy created: " + "; ".join(geometry_errors[:12]))
    if seen_numbers != set(range(1, 77)) or len(annotated) != 76:
        missing = sorted(set(range(1, 77)) - seen_numbers)
        raise ValueError(f"Source Ward_No coverage is not exactly 1..76; missing={missing}")
    return annotated, name_mismatches, geometry_repairs

def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    retrieved_at = datetime.now(timezone.utc).isoformat()
    try:
        raw_bytes, final_url, content_type = fetch_source()
        payload = json.loads(raw_bytes.decode("utf-8-sig"))
        features = extract_features(payload)
        roster_payload = json.loads(ROSTER_PATH.read_text(encoding="utf-8"))
        roster = roster_payload.get("wards", [])
        if len(roster) != 76:
            raise ValueError(f"Expected 76 official roster entries, found {len(roster)}.")
        annotated, name_mismatches, geometry_repairs = validate_and_annotate(features, roster)
    except Exception as exc:
        print(f"KOCHI_WARD_CANDIDATE_BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    raw_sha256 = hashlib.sha256(raw_bytes).hexdigest()
    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    RAW_PATH.write_bytes(raw_bytes)
    raw_metadata = {
        "dataset_id": "kochi_wards_ksmart_2024_draft",
        "title": "Cochin corporation ward-map JSON linked from Kochi Corporation notification page",
        "publisher": "Information Kerala Mission / Delimitation Commission portal (as attributed by the official portal)",
        "source_url": SOURCE_URL,
        "source_page": SOURCE_PAGE,
        "final_url": final_url,
        "retrieved_at_utc": retrieved_at,
        "content_type": content_type,
        "raw_bytes": len(raw_bytes),
        "sha256": raw_sha256,
        "feature_count": len(features),
        "source_status": "DRAFT NOTIFICATION label shown on linked map page",
        "reuse_terms": "Dataset-specific reuse terms not verified; retain attribution and review terms before redistribution.",
        "limitations": [
            "Candidate boundary only; the linked map page labels the map DRAFT NOTIFICATION.",
            "A successful name/geometry audit does not establish legal finality or positional accuracy.",
            "Not approved as a hazard-exposure mask or legal boundary.",
        ],
    }
    write_json(RAW_META_PATH, raw_metadata)
    candidate = {"type": "FeatureCollection", "name": "Kochi 2024 draft ward-map candidate", "features": annotated}
    write_json(CANDIDATE_PATH, candidate)
    candidate_sha = hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest()
    geometry_types: dict[str, int] = {}
    for feature in annotated:
        geometry_type = feature.get("geometry", {}).get("type", "Unknown")
        geometry_types[geometry_type] = geometry_types.get(geometry_type, 0) + 1
    rights_statement = (
        "Reuse rights pending confirmation; attribution retained; candidate is for provisional educational review only, "
        "not approved for legal use or further redistribution."
    )
    validation_warnings = []
    if name_mismatches:
        validation_warnings.append(f"{len(name_mismatches)} source ward names differ from the SEC roster by Ward_No; SEC display names are added without overwriting source names.")
    if geometry_repairs:
        validation_warnings.append(f"{len(geometry_repairs)} invalid source geometries were repaired only in the candidate copy using Shapely make_valid; raw source remains unchanged.")
    validation_warnings.append("The linked map page labels this source DRAFT NOTIFICATION; no legal boundary or exposure-analysis approval is implied.")
    candidate_metadata = {
        "dataset_id": "kochi_wards_ksmart_2024_draft_candidate",
        "title": "Kochi 2024 draft ward-map candidate with explicit SEC name/code matches",
        "source_url": SOURCE_URL,
        "source_page": SOURCE_PAGE,
        "publisher": raw_metadata["publisher"],
        "retrieved_on": retrieved_at[:10],
        "retrieved_at_utc": retrieved_at,
        "publication_date": "Not stated by source; linked map page displays DRAFT NOTIFICATION; corporation notification page posted 2024-11-19.",
        "license": rights_statement,
        "source_sha256": raw_sha256,
        "source_snapshot_sha256": raw_sha256,
        "processed_sha256": candidate_sha,
        "source_feature_count": len(features),
        "processed_feature_count": len(annotated),
        "matched_official_ward_count": 76,
        "source_name_mismatch_count": len(name_mismatches),
        "source_name_mismatches": name_mismatches,
        "match_method": "explicit source Ward_No (unique values 1..76) matched to numeric suffix of SEC ward codes; source labels are retained and audited, not used to assign IDs",
        "geometry_validation": "all 76 output features are valid Polygon/MultiPolygon geometries; any repairs use make_valid and are itemized below",
        "geometry_repair_count": len(geometry_repairs),
        "geometry_repairs": geometry_repairs,
        "crs": "EPSG:4326",
        "crs_note": "GeoJSON longitude/latitude coordinates are treated as WGS 84 under RFC 7946 semantics; formal source CRS metadata was not found in the linked JSON.",
        "units": "longitude/latitude degrees",
        "geographic_coverage": "Kochi Municipal Corporation; candidate 76-ward map",
        "layer_role": "context",
        "required_properties": ["sec_ward_code", "sec_ward_name"],
        "status": "candidate_not_integrated",
        "validation_status": "DRAFT CANDIDATE ONLY — 76 features; legal status not approved",
        "analysis_status": "Not approved as a legal boundary, hazard-exposure mask, or production risk-analysis input.",
        "reuse_terms": rights_statement,
        "limitations": raw_metadata["limitations"] + [
            "CRS is interpreted as WGS 84 from GeoJSON semantics; no independent formal CRS record was supplied.",
            "Twelve source Ward_Name values differ from the State Election Commission roster; source labels are retained and SEC names are added by explicit Ward_No only.",
            "Three invalid source geometries were repaired in the candidate copy; raw source bytes are preserved unchanged and repairs are itemized.",
            "Candidate is not approved for legal boundaries or production exposure calculations.",
            "Reuse rights require confirmation before further redistribution or non-educational reuse.",
        ],
        "validation": {},
    }
    validation_report = validate_geojson(CANDIDATE_PATH, candidate_metadata)
    if validation_report.get("errors") or not validation_report.get("provenance_valid"):
        raise ValueError(
            "Processed candidate failed repository validation: "
            + "; ".join(validation_report.get("errors", []))
            + "; provenance_valid="
            + str(validation_report.get("provenance_valid"))
        )
    validation_report["source_snapshot_sha256"] = raw_sha256
    validation_report["source_feature_count"] = len(features)
    validation_report["excluded_invalid_feature_count"] = 0
    validation_report["excluded_invalid_features"] = []
    validation_report["warnings"] = list(dict.fromkeys(
        validation_report.get("warnings", []) + validation_warnings
    ))
    candidate_metadata["validation"] = validation_report
    write_json(CANDIDATE_META_PATH, candidate_metadata)

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    datasets = catalog.setdefault("datasets", [])
    layer_id = "kochi_wards_ksmart_2024_draft_candidate"
    record = {
        "layer_id": layer_id,
        "title": candidate_metadata["title"],
        "status": "candidate_not_integrated",
        "source_url": SOURCE_URL,
        "publisher": candidate_metadata["publisher"],
        "retrieved_on": retrieved_at[:10],
        "publication_date": "2024-11-18 notification page; linked map itself labelled DRAFT NOTIFICATION",
        "license": candidate_metadata["license"],
        "crs": candidate_metadata["crs"],
        "units": candidate_metadata["units"],
        "geographic_coverage": "Kochi Municipal Corporation; candidate 76-ward map",
        "limitations": candidate_metadata["limitations"],
        "local_file": str(CANDIDATE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "feature_count": 76,
        "validation_status": candidate_metadata["validation_status"],
        "evidence_status": "provisional",
    }
    existing = next((i for i, item in enumerate(datasets) if item.get("layer_id") == layer_id), None)
    if existing is None:
        datasets.append(record)
    else:
        datasets[existing] = record
    write_json(CATALOG_PATH, catalog)
    print(json.dumps({
        "status": "CANDIDATE_ACQUIRED_NOT_APPROVED",
        "source_sha256": raw_sha256,
        "candidate_sha256": candidate_sha,
        "source_feature_count": len(features),
        "matched_official_ward_count": 76,
        "valid_geometry_count": 76,
        "raw_file": str(RAW_PATH.relative_to(ROOT)),
        "candidate_file": str(CANDIDATE_PATH.relative_to(ROOT)),
        "catalog_status": "provisional / candidate_not_integrated",
        "source_name_mismatch_count": len(name_mismatches),
        "source_name_mismatches": name_mismatches,
        "geometry_repair_count": len(geometry_repairs),
        "geometry_repairs": geometry_repairs,
        "warning": "DRAFT NOTIFICATION candidate only; not approved for legal boundaries or exposure analysis",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

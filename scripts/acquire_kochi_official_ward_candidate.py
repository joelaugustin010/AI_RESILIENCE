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

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[1]
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


def feature_name_matches(feature: dict[str, Any], roster_by_normalized_name: dict[str, tuple[str, str]]) -> tuple[str, str] | None:
    properties = feature.get("properties")
    if not isinstance(properties, dict):
        return None
    matches = set()
    for value in properties.values():
        if not isinstance(value, (str, int, float)):
            continue
        normalized = normalize(value)
        if normalized in roster_by_normalized_name:
            matches.add(normalized)
    if len(matches) == 1:
        return roster_by_normalized_name[next(iter(matches))]
    return None


def validate_and_annotate(features: list[dict[str, Any]], roster: list[list[str]]) -> list[dict[str, Any]]:
    if len(features) != 76:
        raise ValueError(f"Expected 76 source features; received {len(features)}. Candidate was not promoted.")
    roster_by_name = {normalize(name): (code, name) for code, name in roster}
    if len(roster_by_name) != 76:
        raise ValueError("Official roster does not contain 76 unique normalized names.")

    annotated = []
    matched_codes: list[str] = []
    geometry_errors = []
    for index, feature in enumerate(features, start=1):
        geometry = feature.get("geometry")
        if not isinstance(geometry, dict):
            geometry_errors.append(f"feature {index}: missing geometry")
            continue
        try:
            polygon = shape(geometry)
            if polygon.is_empty or polygon.geom_type not in {"Polygon", "MultiPolygon"} or not polygon.is_valid:
                geometry_errors.append(f"feature {index}: empty, non-polygon, or invalid geometry ({polygon.geom_type})")
                continue
        except Exception as exc:
            geometry_errors.append(f"feature {index}: geometry parse error: {exc}")
            continue

        matched = feature_name_matches(feature, roster_by_name)
        if matched is None:
            props = feature.get("properties")
            keys = sorted(props.keys()) if isinstance(props, dict) else []
            raise ValueError(f"Feature {index} has no unique exact match to the SEC roster; property keys={keys}")
        code, official_name = matched
        matched_codes.append(code)
        copied = json.loads(json.dumps(feature))
        copied.setdefault("properties", {})
        copied["properties"]["sec_ward_code"] = code
        copied["properties"]["sec_ward_name"] = official_name
        copied["properties"]["boundary_status"] = "draft_candidate_not_approved"
        annotated.append(copied)

    if geometry_errors:
        raise ValueError("Invalid source geometries; no automatic repair performed: " + "; ".join(geometry_errors[:12]))
    if len(annotated) != 76 or len(set(matched_codes)) != 76:
        raise ValueError(f"SEC-name match is not one-to-one: features={len(annotated)}, unique_codes={len(set(matched_codes))}")
    missing = sorted(set(code for code, _ in roster) - set(matched_codes))
    if missing:
        raise ValueError(f"Source is missing official ward codes: {missing}")
    return annotated


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
        annotated = validate_and_annotate(features, roster)
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
    candidate_metadata = {
        "dataset_id": "kochi_wards_ksmart_2024_draft_candidate",
        "title": "Kochi 2024 draft ward-map candidate with explicit SEC name/code matches",
        "source_url": SOURCE_URL,
        "source_page": SOURCE_PAGE,
        "publisher": raw_metadata["publisher"],
        "retrieved_at_utc": retrieved_at,
        "source_sha256": raw_sha256,
        "processed_sha256": candidate_sha,
        "source_feature_count": len(features),
        "processed_feature_count": len(annotated),
        "matched_official_ward_count": 76,
        "match_method": "exact normalized official name match across source property values; no spatial/ordinal guessing",
        "geometry_validation": "all 76 features parsed as valid Polygon/MultiPolygon by Shapely; no automatic repair",
        "crs": "EPSG:4326 assumed from source coordinates; confirm source CRS metadata before metric calculations",
        "units": "longitude/latitude degrees",
        "layer_role": "context",
        "evidence_status": "provisional",
        "status": "candidate_not_integrated",
        "reuse_terms": raw_metadata["reuse_terms"],
        "limitations": raw_metadata["limitations"] + [
            "CRS assumption is not independently confirmed from a formal metadata record.",
            "Candidate is not used for production exposure calculations.",
        ],
    }
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
        "license": raw_metadata["reuse_terms"],
        "crs": candidate_metadata["crs"],
        "units": candidate_metadata["units"],
        "geographic_coverage": "Kochi Municipal Corporation; candidate 76-ward map",
        "limitations": candidate_metadata["limitations"],
        "local_file": str(CANDIDATE_PATH.relative_to(ROOT)).replace("\\", "/"),
        "feature_count": 76,
        "validation_status": "STRUCTURE AND GEOMETRY CHECKED; LEGAL STATUS NOT APPROVED",
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
        "warning": "DRAFT NOTIFICATION candidate only; not approved for legal boundaries or exposure analysis",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

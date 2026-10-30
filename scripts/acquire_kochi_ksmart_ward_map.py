"""Acquire and audit the official KSMART-linked Kochi ward map JSON as a candidate.

The Kochi Corporation page links the map page, but that page currently labels
itself "DRAFT NOTIFICATION". This script preserves the source response and
audits its structure; it never promotes the geometry to the production map.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE_HTML = "https://wardmap.ksmart.live/files/Ernakulam_Cochin_01JBBD7151DY27T8X2GJ2ZD40P.html"
SOURCE_JSON = "https://wardmap.ksmart.live/files/Ernakulam_Cochin_01JBBD7151DY27T8X2GJ2ZD40P.json"
CORPORATION_NOTICE = "https://kochicorporation.lsgkerala.gov.in/en/delimitation-commission-kerala-notification/590"
SEC_WARD_REGISTER = "https://sec.kerala.gov.in/public/cnstncy/lb/da39a3ee5e6b4b0d3255bfef95601890afd8/U/C"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external" / "map_reference"
RAW_PATH = OUT / "kochi_wards_ksmart_portal_candidate.json"
REPORT_PATH = OUT / "kochi_wards_ksmart_portal_candidate.metadata.json"
USER_AGENT = "AI_RESILIENCE educational research; retain source attribution"


def fetch(url: str) -> tuple[bytes, str, str]:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json,*/*"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read(), response.geturl(), response.headers.get("Content-Type", "")


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def walk_features(payload: Any):
    """Yield feature-like records from common GeoJSON or wrapped GIS JSON shapes."""
    if isinstance(payload, dict):
        if payload.get("type") == "Feature" and isinstance(payload.get("geometry"), dict):
            yield payload
            return
        features = payload.get("features")
        if isinstance(features, list):
            for feature in features:
                if isinstance(feature, dict):
                    yield from walk_features(feature)
            return
        for key in ("data", "result", "layers", "wards", "records", "items"):
            child = payload.get(key)
            if isinstance(child, (dict, list)):
                yield from walk_features(child)
    elif isinstance(payload, list):
        for item in payload:
            yield from walk_features(item)


def collect_geometry_stats(features: list[dict[str, Any]]) -> dict[str, Any]:
    geometry_types: dict[str, int] = {}
    valid_count = 0
    invalid_count = 0
    empty_count = 0
    geometry_errors: list[str] = []
    try:
        from shapely.geometry import shape
    except ImportError:
        shape = None
    for index, feature in enumerate(features, start=1):
        geometry = feature.get("geometry")
        kind = str((geometry or {}).get("type", "missing"))
        geometry_types[kind] = geometry_types.get(kind, 0) + 1
        if not geometry:
            empty_count += 1
            continue
        if shape is None:
            continue
        try:
            geom = shape(geometry)
            if geom.is_empty:
                empty_count += 1
            elif geom.is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                if len(geometry_errors) < 10:
                    geometry_errors.append(f"feature {index}: invalid geometry")
        except Exception as error:
            invalid_count += 1
            if len(geometry_errors) < 10:
                geometry_errors.append(f"feature {index}: {type(error).__name__}: {error}")
    names = []
    numbers = []
    property_key_counts: dict[str, int] = {}
    for feature in features:
        properties = feature.get("properties") or {}
        if not isinstance(properties, dict):
            continue
        for key in properties:
            property_key_counts[str(key)] = property_key_counts.get(str(key), 0) + 1
        norm = {''.join(ch for ch in str(key).casefold() if ch.isalnum()): value for key, value in properties.items()}
        for key in ("wardname", "wardnameen", "ward_name", "name", "nameen", "divisionname"):
            value = norm.get(''.join(ch for ch in key if ch.isalnum()))
            if value is not None and str(value).strip() and str(value).strip().casefold() not in {"null", "none", "nan"}:
                names.append(str(value).strip())
                break
        for key in ("wardno", "wardnumber", "wardid", "divisionno", "wardcode", "code"):
            value = norm.get(''.join(ch for ch in key if ch.isalnum()))
            if value is not None and str(value).strip() and str(value).strip().casefold() not in {"null", "none", "nan"}:
                numbers.append(str(value).strip())
                break
    return {
        "feature_count": len(features),
        "geometry_types": geometry_types,
        "valid_geometry_count": valid_count if shape else None,
        "invalid_geometry_count": invalid_count if shape else None,
        "empty_geometry_count": empty_count,
        "named_feature_count": len(names),
        "unique_name_count": len(set(names)),
        "sample_names": names[:100],
        "numbered_feature_count": len(numbers),
        "unique_number_count": len(set(numbers)),
        "sample_numbers": numbers[:100],
        "property_keys": sorted(property_key_counts),
        "geometry_errors_sample": geometry_errors,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "dataset_id": "kochi_ksmart_portal_ward_geometry_candidate",
        "publisher": "Information Kerala Mission / Kerala local-government map portal",
        "source_json_url": SOURCE_JSON,
        "source_html_url": SOURCE_HTML,
        "corporation_notice_url": CORPORATION_NOTICE,
        "sec_ward_register_url": SEC_WARD_REGISTER,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACQUISITION_FAILED",
        "approval": "NOT_APPROVED_FOR_PRODUCTION",
        "source_caution": (
            "The linked Kochi Corporation page calls the map a DRAFT NOTIFICATION. "
            "Treat this as a candidate until the final Gazette/order and current SEC register are "
            "shown to correspond to this exact geometry."
        ),
    }
    try:
        raw, final_url, content_type = fetch(SOURCE_JSON)
        payload = json.loads(raw.decode("utf-8-sig"))
        features = list(walk_features(payload))
        if not isinstance(payload, (dict, list)):
            raise ValueError("Top-level GIS response is not an object or array.")
        if not raw:
            raise ValueError("Empty response.")
        atomic_write(RAW_PATH, raw)
        stats = collect_geometry_stats(features)
        report.update({
            "final_url": final_url,
            "content_type": content_type,
            "size_bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "raw_file": str(RAW_PATH.relative_to(ROOT)),
            "top_level_type": type(payload).__name__,
            "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
            "audit": stats,
            "status": "DOWNLOADED_STRUCTURALLY_AUDITED_CANDIDATE",
            "current_sec_count_alignment": {
                "official_sec_ward_count": 76,
                "portal_feature_count": stats["feature_count"],
                "feature_count_matches_sec_register": stats["feature_count"] == 76,
                "unique_names_match_feature_count": stats["unique_name_count"] == stats["feature_count"],
                "unique_numbers_match_feature_count": stats["unique_number_count"] == stats["feature_count"],
            },
            "production_promotion": "BLOCKED_PENDING_FINAL_ORDER_CONFIRMATION_AND_MANUAL_SPATIAL_AUDIT",
        })
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        report["status"] = "ACQUISITION_FAILED"
        atomic_write(REPORT_PATH, json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8"))
        raise
    atomic_write(REPORT_PATH, json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8"))
    print(json.dumps({
        "status": report["status"],
        "feature_count": report["audit"]["feature_count"],
        "unique_names": report["audit"]["unique_name_count"],
        "unique_numbers": report["audit"]["unique_number_count"],
        "geometry_types": report["audit"]["geometry_types"],
        "production_promotion": report["production_promotion"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

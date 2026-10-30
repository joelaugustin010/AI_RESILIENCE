"""Compare the KSMART-linked ward-map candidate with the current SEC ward register.

The map page is labelled DRAFT NOTIFICATION. This audit is diagnostic only:
it never repairs source polygons, changes the production map, or treats a
candidate match as proof of legal currency.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PORTAL_META = ROOT / "data/external/map_reference/kochi_wards_ksmart_portal_candidate.metadata.json"
PORTAL_RAW = ROOT / "data/external/map_reference/kochi_wards_ksmart_portal_candidate.json"
SEC_REGISTER = ROOT / "data/reference/kochi_official_ward_register_2026.json"
OUTPUT = ROOT / "reports/kochi_portal_candidate_vs_sec_register.json"


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def first(properties: dict[str, Any], aliases: tuple[str, ...]) -> Any:
    normalized = {norm(key): value for key, value in properties.items()}
    for alias in aliases:
        value = normalized.get(norm(alias))
        if value is not None and str(value).strip().casefold() not in {"", "null", "none", "nan", "<null>"}:
            return value
    return None


def features_from(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if payload.get("type") == "Feature" and isinstance(payload.get("geometry"), dict):
            return [payload]
        if isinstance(payload.get("features"), list):
            return [f for f in payload["features"] if isinstance(f, dict)]
        for key in ("data", "result", "layers", "wards", "records", "items"):
            if isinstance(payload.get(key), (dict, list)):
                found = features_from(payload[key])
                if found:
                    return found
    if isinstance(payload, list):
        out = []
        for item in payload:
            out.extend(features_from(item))
        return out
    return []


def main() -> int:
    portal_meta = json.loads(PORTAL_META.read_text(encoding="utf-8"))
    payload_bytes = PORTAL_RAW.read_bytes()
    payload = json.loads(payload_bytes.decode("utf-8-sig"))
    register_bytes = SEC_REGISTER.read_bytes()
    register = json.loads(register_bytes.decode("utf-8-sig"))
    official = register.get("wards", [])
    official_by_number = {int(row["ward_number"]): row for row in official}
    features = features_from(payload)

    comparisons = []
    portal_numbers = []
    portal_names = []
    for index, feature in enumerate(features, start=1):
        props = feature.get("properties") or {}
        if not isinstance(props, dict):
            props = {}
        raw_number = first(props, ("Ward_No", "WardNo", "Ward_Number", "WardNumber", "Ward_ID", "WardId"))
        raw_name = first(props, ("Ward_Name", "WardName", "Ward_Name_1", "name", "name_en"))
        try:
            number = int(str(raw_number).strip())
        except (TypeError, ValueError):
            number = None
        name = str(raw_name).strip() if raw_name is not None else None
        if number is not None:
            portal_numbers.append(number)
        if name:
            portal_names.append(name)
        official_row = official_by_number.get(number) if number is not None else None
        official_name = official_row.get("ward_name") if official_row else None
        name_match = bool(name and official_name and norm(name) == norm(official_name))
        comparisons.append({
            "feature_index": index,
            "portal_ward_number": number,
            "portal_ward_name": name,
            "sec_ward_name_for_number": official_name,
            "number_found_in_sec_register": official_row is not None,
            "normalized_name_match": name_match,
            "name_mismatch": bool(official_row and name and not name_match),
            "ward_number_missing": number is None,
            "ward_name_missing": not bool(name),
        })

    try:
        from shapely.geometry import shape
        valid = invalid = empty = missing_geometry = 0
        invalid_indices = []
        for index, feature in enumerate(features, start=1):
            geometry = feature.get("geometry")
            if not geometry:
                missing_geometry += 1
                continue
            try:
                geom = shape(geometry)
                if geom.is_empty:
                    empty += 1
                elif geom.is_valid:
                    valid += 1
                else:
                    invalid += 1
                    invalid_indices.append(index)
            except Exception:
                invalid += 1
                invalid_indices.append(index)
        geometry_audit = {
            "validator": "Shapely",
            "valid_geometry_count": valid,
            "invalid_geometry_count": invalid,
            "empty_geometry_count": empty,
            "missing_geometry_count": missing_geometry,
            "invalid_feature_indices": invalid_indices,
        }
    except ImportError:
        geometry_audit = {"validator": None, "status": "Shapely unavailable"}

    expected_numbers = set(official_by_number)
    found_numbers = set(portal_numbers)
    duplicate_numbers = sorted(n for n in found_numbers if portal_numbers.count(n) > 1)
    report = {
        "status": "CANDIDATE_AUDITED_NOT_APPROVED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "portal_candidate_file": str(PORTAL_RAW.relative_to(ROOT)),
        "portal_candidate_sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "portal_metadata_file": str(PORTAL_META.relative_to(ROOT)),
        "portal_source_url": portal_meta.get("source_json_url"),
        "portal_source_caution": portal_meta.get("source_caution"),
        "official_sec_register_file": str(SEC_REGISTER.relative_to(ROOT)),
        "official_sec_register_sha256": hashlib.sha256(register_bytes).hexdigest(),
        "official_sec_register_source_url": register.get("source_url"),
        "official_sec_register_retrieved_on": register.get("retrieved_on"),
        "official_sec_ward_count": len(official),
        "portal_feature_count": len(features),
        "unique_portal_numbers": len(found_numbers),
        "unique_portal_names": len({norm(name) for name in portal_names}),
        "missing_sec_numbers_in_portal": sorted(expected_numbers - found_numbers),
        "numbers_not_in_sec_register": sorted(found_numbers - expected_numbers),
        "duplicate_portal_numbers": duplicate_numbers,
        "ward_name_mismatch_count": sum(row["name_mismatch"] for row in comparisons),
        "ward_name_missing_count": sum(row["ward_name_missing"] for row in comparisons),
        "ward_number_missing_count": sum(row["ward_number_missing"] for row in comparisons),
        "geometry_audit": geometry_audit,
        "ward_comparisons": comparisons,
        "promotion_decision": "BLOCKED: source page is labelled DRAFT NOTIFICATION; compare final Gazette geometry and resolve all invalid polygons and SEC name/number mismatches before production use.",
        "limitations": [
            "A matching count of 76 does not prove the polygons are the final legally notified boundaries.",
            "Names are compared by ward number after normalization; spelling and boundary changes may require source-document review.",
            "Invalid geometries are reported, not repaired.",
            "No production data or map source was changed by this audit.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "portal_features": report["portal_feature_count"],
        "official_sec_wards": report["official_sec_ward_count"],
        "name_mismatches": report["ward_name_mismatch_count"],
        "invalid_geometries": geometry_audit.get("invalid_geometry_count"),
        "promotion_decision": report["promotion_decision"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

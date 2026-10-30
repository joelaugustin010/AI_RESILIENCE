"""Read-only audit of a public ArcGIS India ward-boundary service for Kochi.

The script queries public REST endpoints only, does not authenticate or bypass
access controls, does not save raw geometries, and never promotes a candidate
into the production map. It records counts, schema, geometry validity, and
name-only comparison with the official SEC register.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import shape
from shapely.ops import transform as shapely_transform, unary_union
from pyproj import Transformer

BASE = "https://livingatlas.esri.in/server1/rest/services/Wards/India_Ward_Boundaries/MapServer"
LAYER_URL = BASE + "/0"
ITEM_URL = "https://livingatlas.esri.in/sharing/rest/content/items/9ff2ac026dbb48ff85a0f4573b9987f1?f=json"
REGISTER = Path("data/reference/kochi_official_ward_register_2026.json")
BOUNDARY_PATH = Path("data/reference/kochi_corporation_boundary.geojson")
FINAL_MAP_REPORT = Path("reports/kochi_final_map_source_discovery.json")
OUT = Path("reports/kochi_esri_ward_candidate_audit.json")
UA = "AI_RESILIENCE educational GIS source audit; contact project maintainer via repository"
TIMEOUT = 40
MAX_PAGES = 10
PAGE_SIZE = 1000


def normalize(value) -> str:
    return "".join(ch for ch in str(value or "").casefold() if ch.isalnum())


def get_json(url: str, params: dict | None = None) -> tuple[dict, str, bytes]:
    if params:
        separator = "&" if "?" in url else "?"
        url = url + separator + urllib.parse.urlencode(params)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"livingatlas.esri.in"}:
        raise ValueError(f"Refusing non-HTTPS or unapproved source URL: {url}")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json, application/geo+json, */*",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        raw = response.read(35_000_001)
        if len(raw) > 35_000_000:
            raise ValueError("Response exceeds 35 MB safety limit")
        final_url = response.geturl()
    data = json.loads(raw.decode("utf-8-sig"))
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"ArcGIS REST error: {data['error']}")
    return data, final_url, raw


def query_count(where: str) -> dict:
    data, final_url, raw = get_json(
        LAYER_URL + "/query",
        {"where": where, "returnCountOnly": "true", "f": "json"},
    )
    return {
        "where": where,
        "count": data.get("count"),
        "url": final_url,
        "response_sha256": hashlib.sha256(raw).hexdigest(),
    }


def query_ernakulam_towns() -> tuple[list[dict], list[dict]]:
    where = "state='Kerala' AND district='Ernakulam'"
    rows: list[dict] = []
    pages = []
    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        data, final_url, raw = get_json(
            LAYER_URL + "/query",
            {
                "where": where,
                "outFields": "objectid,town,district,state",
                "returnGeometry": "false",
                "orderByFields": "objectid",
                "resultOffset": str(offset),
                "resultRecordCount": str(PAGE_SIZE),
                "f": "json",
            },
        )
        features = data.get("features", [])
        rows.extend(
            feature.get("attributes", {})
            for feature in features
            if isinstance(feature, dict)
        )
        pages.append({
            "offset": offset,
            "rows": len(features),
            "exceeded_transfer_limit": bool(data.get("exceededTransferLimit", False)),
            "url": final_url,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
        })
        if not data.get("exceededTransferLimit") and len(features) < PAGE_SIZE:
            break
        if not features:
            break
    return rows, pages


def query_town_geometry(
    town: str,
    sec_wards: list[dict],
    final_pdf_labels_by_number: dict[int, list[str]],
) -> dict:
    safe_town = town.replace("'", "''")
    where = f"state='Kerala' AND district='Ernakulam' AND town='{safe_town}'"
    count = query_count(where)
    count_value = count.get("count")
    result = {
        "town_value": town,
        "where": where,
        "count_audit": count,
        "geometry_query": None,
        "candidate_status": "NOT_FETCHED",
    }
    if not isinstance(count_value, int) or count_value <= 0:
        result["candidate_status"] = "NO_MATCHING_FEATURES"
        return result
    if count_value > 1000:
        result["candidate_status"] = "TOO_MANY_FEATURES_FOR_BOUNDED_AUDIT"
        return result

    data, final_url, raw = get_json(
        LAYER_URL + "/query",
        {
            "where": where,
            "outFields": "objectid,id,name,code,town,district,state,link",
            "returnGeometry": "true",
            "outSR": "4326",
            "resultRecordCount": "1000",
            "f": "geojson",
        },
    )
    features = data.get("features", [])
    labels = []
    invalid = []
    missing_geometry = []
    duplicate_names = []
    seen_names = set()
    all_geometries = []
    sec_by_number = {int(row["ward_number"]): row["ward_name"] for row in sec_wards}
    for index, feature in enumerate(features, start=1):
        props = feature.get("properties", {}) if isinstance(feature, dict) else {}
        name = str(props.get("name") or "").strip()
        raw_code = props.get("code")
        try:
            code_number = int(str(raw_code).strip())
        except (TypeError, ValueError):
            code_number = None
        labels.append({
            "name": name or None,
            "code": raw_code,
            "id": props.get("id"),
            "town": props.get("town"),
            "link": props.get("link"),
            "parsed_code_number": code_number,
        })
        norm_name = normalize(name)
        if norm_name in seen_names:
            duplicate_names.append(name)
        if norm_name:
            seen_names.add(norm_name)
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if not geometry:
            missing_geometry.append(index)
            all_geometries.append(None)
            continue
        try:
            geom = shape(geometry)
            all_geometries.append(geom)
            if geom.is_empty or geom.geom_type not in {"Polygon", "MultiPolygon"} or not geom.is_valid:
                invalid.append({
                    "feature_index": index,
                    "name": name,
                    "geometry_type": geom.geom_type,
                    "is_valid": geom.is_valid,
                })
        except Exception as exc:
            all_geometries.append(None)
            invalid.append({"feature_index": index, "name": name, "error": f"{type(exc).__name__}: {exc}"})

    source_names = [item["name"] for item in labels if item["name"]]
    official_norm = {normalize(row["ward_name"]) for row in sec_wards}
    exact_unique_names = sorted({name for name in source_names if normalize(name) in official_norm})
    differences = [
        {"source_name": name, "exact_SEC_name_match": normalize(name) in official_norm}
        for name in sorted(set(source_names), key=str.casefold)
        if normalize(name) not in official_norm
    ]

    code_numbers = [row["parsed_code_number"] for row in labels]
    code_range_valid = (
        len(code_numbers) == 76
        and all(number is not None for number in code_numbers)
        and sorted(code_numbers) == list(range(1, 77))
    )
    crosswalk = []
    for row in labels:
        number = row["parsed_code_number"]
        sec_name = sec_by_number.get(number) if number is not None else None
        pdf_labels = final_pdf_labels_by_number.get(number, []) if number is not None else []
        source_name = row["name"] or ""
        crosswalk.append({
            "source_code": row["code"],
            "parsed_ward_number": number,
            "source_name": source_name or None,
            "SEC_name_for_same_number": sec_name,
            "exact_SEC_name_match_for_same_number": bool(sec_name and normalize(source_name) == normalize(sec_name)),
            "final_PDF_label_for_same_number": pdf_labels,
            "exact_final_PDF_label_match_for_same_number": any(
                normalize(source_name) == normalize(pdf_label) for pdf_label in pdf_labels
            ),
            "note": "Diagnostic comparison only; no SEC identity is assigned to the source polygon.",
        })

    geometry_audit = {
        "valid_polygon_count": len(all_geometries) - len(invalid) - len(missing_geometry),
        "invalid_geometry_count": len(invalid),
        "invalid_geometry_examples": invalid[:20],
        "missing_geometry_indices": missing_geometry[:20],
        "source_name_count": len(set(source_names)),
        "unique_source_code_count": len({str(row["code"]) for row in labels if row.get("code") not in (None, "")}),
        "source_code_numbers_exactly_1_to_76": code_range_valid,
        "exact_SEC_name_match_count_any_number": len(exact_unique_names),
        "exact_SEC_name_match_count_by_source_code_number": sum(row["exact_SEC_name_match_for_same_number"] for row in crosswalk),
        "exact_final_PDF_label_match_count_by_source_code_number": sum(row["exact_final_PDF_label_match_for_same_number"] for row in crosswalk),
        "source_names_not_exactly_in_SEC_register": differences,
        "source_code_name_crosswalk": crosswalk,
    }

    comparison = {"status": "NOT_COMPUTED"}
    valid_geometries = [
        geom for geom in all_geometries
        if geom is not None and not geom.is_empty and geom.is_valid
        and geom.geom_type in {"Polygon", "MultiPolygon"}
    ]
    if valid_geometries:
        transformer = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)
        projected = [shapely_transform(transformer.transform, geom) for geom in valid_geometries]
        ward_union = unary_union(projected)
        area_sum = sum(geom.area for geom in projected)
        overlap_pairs = []
        for i, first in enumerate(projected):
            for j in range(i + 1, len(projected)):
                second = projected[j]
                if not first.bounds[2] < second.bounds[0] and not second.bounds[2] < first.bounds[0] and not first.bounds[3] < second.bounds[1] and not second.bounds[3] < first.bounds[1]:
                    intersection_area = first.intersection(second).area
                    if intersection_area > 1.0:
                        overlap_pairs.append({
                            "feature_indices": [i + 1, j + 1],
                            "intersection_area_m2": round(intersection_area, 3),
                        })
        comparison = {
            "comparison_crs": "EPSG:32643",
            "valid_geometry_count_used": len(projected),
            "ward_union_is_valid": ward_union.is_valid,
            "ward_union_geometry_type": ward_union.geom_type,
            "sum_of_individual_ward_areas_km2": round(area_sum / 1_000_000, 4),
            "ward_union_area_km2": round(ward_union.area / 1_000_000, 4),
            "sum_minus_union_area_km2_overlap_indicator": round((area_sum - ward_union.area) / 1_000_000, 6),
            "pairwise_interior_overlap_pairs_over_1m2": len(overlap_pairs),
            "largest_pairwise_overlap_examples": sorted(overlap_pairs, key=lambda item: item["intersection_area_m2"], reverse=True)[:20],
            "ward_union_bounds_lonlat": list(shape({
                "type": "Polygon",
                "coordinates": [[
                    [float(x), float(y)] for x, y in [
                        # bounds are reported below from source coordinates instead;
                    ]
                ]]
            }).bounds) if False else None,
        }
        try:
            boundary_data = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
            boundary_geom = shape(boundary_data["geometry"] if boundary_data.get("type") == "Feature" else boundary_data)
            boundary_projected = shapely_transform(transformer.transform, boundary_geom)
            intersection = ward_union.intersection(boundary_projected)
            union_area = ward_union.union(boundary_projected).area
            comparison["configured_boundary_comparison"] = {
                "boundary_path": str(BOUNDARY_PATH),
                "boundary_is_valid": boundary_projected.is_valid,
                "boundary_area_km2": round(boundary_projected.area / 1_000_000, 4),
                "intersection_area_km2": round(intersection.area / 1_000_000, 4),
                "symmetric_difference_area_km2": round(ward_union.symmetric_difference(boundary_projected).area / 1_000_000, 4),
                "intersection_over_union": round(intersection.area / union_area, 6) if union_area else None,
                "candidate_outside_boundary_km2": round(ward_union.difference(boundary_projected).area / 1_000_000, 4),
                "boundary_uncovered_by_candidate_km2": round(boundary_projected.difference(ward_union).area / 1_000_000, 4),
                "status": "DIAGNOSTIC_ONLY_CONFIGURED_BOUNDARY_NOT_LEGAL_APPROVAL",
            }
        except Exception as exc:
            comparison["configured_boundary_comparison"] = {
                "status": "BOUNDARY_COMPARISON_FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            }
    geometry_audit["topology_and_coverage"] = comparison

    result.update({
        "geometry_query": {
            "url": final_url,
            "http_success": True,
            "response_bytes": len(raw),
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "feature_count": len(features),
            "returned_geojson_type": data.get("type"),
            "geometry_type_counts": {
                kind: sum(1 for f in features if (f.get("geometry") or {}).get("type") == kind)
                for kind in sorted({(f.get("geometry") or {}).get("type", "missing") for f in features})
            },
            **geometry_audit,
            "source_feature_label_sample": labels[:100],
            "spatial_reference_requested": "EPSG:4326 via outSR=4326",
        },
        "candidate_status": "AUDITED_CANDIDATE_ONLY_NOT_PROMOTED",
    })
    return result


def main() -> int:
    report = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "service_url": LAYER_URL,
        "item_url": ITEM_URL,
        "status": "READ_ONLY_SOURCE_AUDIT_ONLY",
        "limitations": [
            "A public ArcGIS service is a candidate source, not proof that its boundaries match the final Gazette geometry.",
            "Names are compared by exact normalized text only; no SEC identity is assigned to a polygon by ordinal number or fuzzy matching.",
            "Geometry validity is not positional accuracy, topology between neighboring wards, legal status, or flood-model validation.",
            "Reuse terms and source lineage must be confirmed before redistribution or production integration.",
            "Raw geometry is not persisted by this audit script.",
        ],
    }
    try:
        metadata, metadata_url, metadata_raw = get_json(LAYER_URL, {"f": "pjson"})
        report["service_metadata"] = {
            "url": metadata_url,
            "sha256": hashlib.sha256(metadata_raw).hexdigest(),
            "layer_name": metadata.get("name"),
            "geometry_type": metadata.get("geometryType"),
            "spatial_reference": metadata.get("sourceSpatialReference"),
            "fields": [
                {"name": field.get("name"), "alias": field.get("alias"), "type": field.get("type")}
                for field in metadata.get("fields", [])
            ],
            "max_record_count": metadata.get("maxRecordCount"),
            "supported_query_formats": metadata.get("supportedQueryFormats"),
            "capabilities": metadata.get("capabilities"),
            "service_item_id": metadata.get("serviceItemId"),
            "copyright_text": metadata.get("copyrightText"),
        }
        try:
            item, item_url, item_raw = get_json(ITEM_URL)
            report["service_item_metadata"] = {
                "url": item_url,
                "sha256": hashlib.sha256(item_raw).hexdigest(),
                "title": item.get("title"),
                "snippet": item.get("snippet"),
                "description": item.get("description"),
                "license_info": item.get("licenseInfo"),
                "access_information": item.get("accessInformation"),
                "access": item.get("access"),
                "modified": item.get("modified"),
                "created": item.get("created"),
            }
        except Exception as exc:
            report["service_item_metadata"] = {"error": f"{type(exc).__name__}: {exc}"}

        register = json.loads(REGISTER.read_text(encoding="utf-8"))
        sec_wards = register.get("wards", [])
        sec_names = [row["ward_name"] for row in sec_wards]
        if len(sec_names) != 76:
            raise ValueError(f"Expected 76 official SEC ward names, got {len(sec_names)}")
        final_pdf_labels_by_number = {}
        if FINAL_MAP_REPORT.exists():
            final_map_report = json.loads(FINAL_MAP_REPORT.read_text(encoding="utf-8"))
            for row in final_map_report.get("final_map_pdf_audit", {}).get("numbered_comparison", []):
                final_pdf_labels_by_number[int(row["ward_number"])] = row.get("final_map_labels", [])
        report["official_sec_register"] = {
            "source_url": register.get("source_url"),
            "retrieved_on": register.get("retrieved_on"),
            "ward_count": len(sec_names),
        }

        rows, pages = query_ernakulam_towns()
        town_counts: dict[str, int] = {}
        for row in rows:
            town = str(row.get("town") or "").strip()
            if town:
                town_counts[town] = town_counts.get(town, 0) + 1
        candidates = [
            {"town": town, "count_in_Ernakulam_query": count}
            for town, count in sorted(town_counts.items(), key=lambda item: item[0].casefold())
            if "cochin" in normalize(town) or "kochi" in normalize(town)
        ]
        report["district_query"] = {
            "where": "state='Kerala' AND district='Ernakulam'",
            "rows_scanned": len(rows),
            "pages": pages,
            "unique_town_count": len(town_counts),
            "matching_town_values": candidates,
        }
        if not candidates:
            report["candidate_towns"] = []
            report["status"] = "SERVICE_REACHABLE_BUT_NO_KOCHI_TOWN_VALUE_FOUND"
        else:
            town_results = []
            for candidate in candidates:
                town_results.append(query_town_geometry(candidate["town"], sec_wards, final_pdf_labels_by_number))
            report["candidate_towns"] = town_results
            report["status"] = "CANDIDATE_AUDITED_NOT_PROMOTED"
        report["summary"] = {
            "official_sec_wards": len(sec_names),
            "district_records_scanned": len(rows),
            "candidate_town_values": [row["town"] for row in candidates],
            "candidate_feature_counts": [
                row.get("geometry_query", {}).get("feature_count")
                for row in report.get("candidate_towns", [])
            ],
            "production_geometry_promoted": False,
        }
    except Exception as exc:
        report["status"] = "AUDIT_BLOCKED"
        report["error"] = f"{type(exc).__name__}: {exc}"
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 2

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

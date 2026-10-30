"""Create a conservative geometric crosswalk for missing labels in Kochi ward data.

This script reports candidate name matches only. It never modifies source GeoJSON,
fills ward IDs, or treats the OpenCity candidate as legally authoritative.
"""
from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/processed/spatial_layers/kochi_wards_datameet_2022.geojson"
CANDIDATE = ROOT / "data/external/map_reference/kochi_wards_2024_candidate.kml"
OUTPUT = ROOT / "reports/kochi_ward_label_reconciliation.json"
TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:32643", always_xy=True)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def coordinates(node: ET.Element) -> list[tuple[float, float]]:
    item = next((child for child in node.iter() if local_name(child.tag) == "coordinates"), None)
    if item is None:
        return []
    points = []
    for token in (item.text or "").split():
        parts = token.split(",")
        if len(parts) < 2:
            continue
        points.append((float(parts[0]), float(parts[1])))
    return points


def read_candidate_wards(path: Path) -> list[dict[str, Any]]:
    root = ET.parse(path).getroot()
    wards = []
    for index, placemark in enumerate((e for e in root.iter() if local_name(e.tag) == "Placemark"), 1):
        name = ""
        for child in placemark.iter():
            if local_name(child.tag) == "SimpleData" and child.attrib.get("name", "").casefold() in {
                "ward_lgd_name", "ward_name", "wardname", "sourcewardname", "name"
            } and child.text and child.text.strip():
                name = child.text.strip()
                break
        if not name:
            name = next((e.text.strip() for e in placemark.iter()
                         if local_name(e.tag) == "name" and e.text and e.text.strip()), "")
        polygons = []
        for node in (e for e in placemark.iter() if local_name(e.tag) == "Polygon"):
            outer = next((e for e in node.iter() if local_name(e.tag) == "outerBoundaryIs"), None)
            shell = coordinates(outer) if outer is not None else []
            holes = []
            for inner in (e for e in node.iter() if local_name(e.tag) == "innerBoundaryIs"):
                ring = coordinates(inner)
                if len(ring) >= 4 and ring[0] == ring[-1]:
                    holes.append(ring)
            if len(shell) >= 4 and shell[0] == shell[-1]:
                polygon = Polygon(shell, holes)
                if polygon.is_valid and not polygon.is_empty:
                    polygons.append(transform(TRANSFORMER.transform, polygon))
        if name and polygons:
            geometry = unary_union(polygons)
            if geometry.is_valid and not geometry.is_empty:
                wards.append({"name": name, "geometry": geometry, "placemark_index": index})
    return wards


def has_value(value: Any) -> bool:
    return value is not None and str(value).strip().casefold() not in {"", "none", "null", "nan", "<null>", "n/a"}


def main() -> None:
    source_bytes = SOURCE.read_bytes()
    candidate_bytes = CANDIDATE.read_bytes()
    source = json.loads(source_bytes)
    candidate_wards = read_candidate_wards(CANDIDATE)
    source_features = source.get("features", [])
    source_records = []
    for index, feature in enumerate(source_features, 1):
        properties = feature.get("properties") or {}
        geom = shape(feature["geometry"])
        geom = transform(TRANSFORMER.transform, geom)
        ward_name = next((properties.get(k) for k in ("Ward_Name", "WardName", "ward_name", "name") if has_value(properties.get(k))), None)
        ward_no = next((properties.get(k) for k in ("Ward_No", "WardNo", "ward_no", "ward_number") if has_value(properties.get(k))), None)
        source_records.append({"index": index, "ward_name_present": has_value(ward_name), "ward_no_present": has_value(ward_no), "geometry": geom})

    matches = []
    for source_record in source_records:
        if source_record["ward_name_present"] and source_record["ward_no_present"]:
            continue
        source_geom = source_record["geometry"]
        ranked = []
        for candidate in candidate_wards:
            union_area = source_geom.union(candidate["geometry"]).area
            iou = source_geom.intersection(candidate["geometry"]).area / union_area if union_area else 0.0
            ranked.append({"candidate_name": candidate["name"], "placemark_index": candidate["placemark_index"], "intersection_over_union": round(iou, 6)})
        ranked.sort(key=lambda row: row["intersection_over_union"], reverse=True)
        best = ranked[0] if ranked else None
        second = ranked[1] if len(ranked) > 1 else None
        margin = (best["intersection_over_union"] - second["intersection_over_union"]) if best and second else None
        matches.append({
            "source_feature_index": source_record["index"],
            "source_ward_name_missing": not source_record["ward_name_present"],
            "source_ward_number_missing": not source_record["ward_no_present"],
            "best_candidate": best,
            "second_best_candidate": second,
            "best_minus_second_iou": round(margin, 6) if margin is not None else None,
            "suggested_for_manual_review": bool(best and best["intersection_over_union"] >= 0.75 and margin is not None and margin >= 0.15),
            "automatic_assignment": False,
        })

    report = {
        "status": "GEOMETRIC_CROSSWALK_CANDIDATES_ONLY",
        "source_file": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "candidate_file": str(CANDIDATE.relative_to(ROOT)),
        "candidate_sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "source_feature_count": len(source_features),
        "candidate_named_ward_count": len(candidate_wards),
        "source_features_with_missing_ward_attributes": len(matches),
        "matches": matches,
        "method": "Projected each geometry to UTM zone 43N (EPSG:32643), ranked candidate polygons by intersection-over-union, and reported top two candidates.",
        "limitations": [
            "OpenCity 2024 map is a candidate source, not independently confirmed as the final legally authoritative ward boundary.",
            "Geometry similarity is not proof that a ward name or number is legally/currently correct.",
            "No source geometry or attribute was changed; no ward number was inferred.",
            "Suggested matches require manual inspection against official ward register and boundary notification before display as verified labels.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "source_features": len(source_features),
                      "candidate_wards": len(candidate_wards), "missing_records": len(matches),
                      "suggested_for_manual_review": sum(m["suggested_for_manual_review"] for m in matches)}, indent=2))


if __name__ == "__main__":
    main()

"""Acquire candidate spatial reference data for the Kochi map.

Downloads are kept as raw evidence and are NOT automatically promoted to map
layers. Every output receives a SHA-256 manifest entry and explicit caveats.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "external" / "map_reference"
USER_AGENT = "AI_RESILIENCE educational research; preserve source attribution"
HOSPITAL_QUERY = "https://livingatlas.esri.in/server/rest/services/LivingAtlas/IND_Health/MapServer/0/query"
PREVIOUS_HOSPITAL_QUERY = "https://livingatlas.esri.in/server/rest/services/LivingAtlas/IND_Hospital_Directory/MapServer/0/query"
FLOOD_ZIP = "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/1.-Flood-Return-Probability-Historical-10-25-50-years.zip"
SOURCES = {
    "health_facilities_ernakulam.geojson": {
        "url": HOSPITAL_QUERY,
        "publisher": "Esri India Living Atlas, Health Centers in India (underlying data provenance requires review)",
        "source_page": "https://livingatlas.esri.in/server/rest/services/LivingAtlas/IND_Health/MapServer/0",
        "previous_source_attempt": {
            "url": PREVIOUS_HOSPITAL_QUERY,
            "status": "FAILED_ZERO_FEATURES_AFTER_TWO_OBJECT_IDS",
            "reason": "The Hospital Directory layer returned an empty FeatureCollection when the retrieved object IDs were queried; retained as a failed source attempt rather than silently accepted."
        },
        "reuse": "Service page did not state a dataset-specific licence; review terms before redistribution.",
        "purpose": "Candidate public health-facility locations (PHCs, CHCs, sub-centres and hospitals) for independent identity and coordinate review.",
        "independent_verification_sources": [
            {
                "publisher": "Kerala Health Department",
                "title": "Institutions List (live search)",
                "url": "https://health.kerala.gov.in/index.php/institutionSearch",
                "role": "Independent reference for facility names, district, address, category and reported bed counts; does not itself provide a verified GIS export.",
                "status": "REFERENCE_IDENTIFIED_MATCHING_NOT_YET_PERFORMED"
            },
            {
                "publisher": "Kerala Health Department",
                "title": "List of Modern Medicine Institutions 2024-25",
                "url": "https://health.kerala.gov.in/assets/backend/uploads/Galleryitem/17506790021511401637.pdf",
                "role": "Downloadable official name/address cross-check; older snapshot, not a source of coordinates or current operating status.",
                "status": "REFERENCE_TO_BE_DOWNLOADED_AND_MATCHED"
            }
        ],
        "limitations": [
            "Not an official Kerala Health Department GIS export; source provenance, currency and licence require review.",
            "Ernakulam district is broader than Kochi Corporation.",
            "Coordinates are converted to EPSG:4326 by the service; positional accuracy is not stated.",
            "Do not use for hospital vulnerability scoring until facility identity, location and operating status are checked."
        ],
    },
    "ksdma_flood_return_probability_historical_10_25_50.zip": {
        "url": FLOOD_ZIP,
        "publisher": "Kerala State Disaster Management Authority (KSDMA)",
        "source_page": "https://sdma.kerala.gov.in/hazard-maps/",
        "reuse": "Dataset-specific licence and pixel semantics must be verified before reuse.",
        "purpose": "Candidate statewide flood return-probability raster archive for metadata and spatial QA.",
        "limitations": [
            "Statewide raster is not automatically a Kochi-specific flood-depth layer.",
            "CRS, units, NoData values, band meanings, resolution, and spatial alignment must be audited.",
            "Return-period hazard is not a forecast for a specific date and is not an observed flood label.",
            "Do not display as validated exposure until raster metadata, licence, and Kochi coverage are confirmed."
        ],
    },
    "kerala_health_department_institutions_2024_25.pdf": {
        "url": "https://health.kerala.gov.in/assets/backend/uploads/Galleryitem/17506790021511401637.pdf",
        "publisher": "Kerala Health Department, Government of Kerala",
        "source_page": "https://health.kerala.gov.in/index.php/institutionSearch",
        "reuse": "No explicit licence for redistribution verified; retain attribution and verify terms before republishing.",
        "purpose": "Independent name/address reference for cross-checking candidate health-facility features; not a coordinate source.",
        "limitations": [
            "This is a 2024-25 snapshot and may not reflect current facility status.",
            "Facility names and addresses must be matched carefully; spelling variants are not proof of identity.",
            "This PDF does not independently verify the coordinates of the Esri features.",
            "Do not treat a successful PDF download as completion of facility verification."
        ],
    },
    "kochi_corporation_boundary_candidate.geojson": {
        "url": "https://raw.githubusercontent.com/yashveeeeeeer/india-geodata/main/data/urban/municipal-boundaries/kochi/KCH_Corporation_Boundary.geojson",
        "publisher": "DataMeet Trust; curated mirror in India Geodata, sourced from Kerala OpenSDI",
        "source_page": "https://opensdi.kerala.gov.in/layers/opensdi_data:geonode:KSUDP_KCH_Corporation_Boundary",
        "reuse": "CC BY-SA 2.5 India, as stated in the source repository README; preserve attribution and share-alike terms.",
        "purpose": "Candidate Kochi Corporation polygon for preliminary point-in-polygon screening of Ernakulam health-facility coordinates.",
        "limitations": [
            "The source README does not establish that this polygon reflects the current 2024 delimitation; date/currentness remain unverified.",
            "Kochi Corporation published a 2024 delimitation notification; compare this candidate with the current official ward map before treating it as the authoritative city boundary.",
            "Spatial inclusion is preliminary screening only and does not verify facility identity, positional accuracy, or current operating status.",
            "Do not use this boundary or filtered points for final exposure analysis until the boundary version is confirmed."
        ],
    },
}


def fetch(url: str, timeout: int = 120) -> tuple[bytes, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json,application/json,application/zip,*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
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


def point_in_ring(point: tuple[float, float], ring: list) -> bool:
    """Ray-casting point-in-ring test for longitude/latitude coordinates."""
    x, y = point
    inside = False
    if len(ring) < 4:
        return False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][:2]
        xj, yj = ring[j][:2]
        # Treat points on a segment as inside within a small numerical tolerance.
        cross = (x - xi) * (yj - yi) - (y - yi) * (xj - xi)
        if abs(cross) < 1e-10 and min(xi, xj) - 1e-10 <= x <= max(xi, xj) + 1e-10 and min(yi, yj) - 1e-10 <= y <= max(yi, yj) + 1e-10:
            return True
        if (yi > y) != (yj > y):
            intersection_x = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < intersection_x:
                inside = not inside
        j = i
    return inside


def point_in_polygon(point: tuple[float, float], polygon: list) -> bool:
    if not polygon or not point_in_ring(point, polygon[0]):
        return False
    return not any(point_in_ring(point, hole) for hole in polygon[1:])


def point_in_geometry(point: tuple[float, float], geometry: dict) -> bool:
    kind = geometry.get("type")
    coordinates = geometry.get("coordinates") or []
    if kind == "Polygon":
        return point_in_polygon(point, coordinates)
    if kind == "MultiPolygon":
        return any(point_in_polygon(point, polygon) for polygon in coordinates)
    return False


def add_boundary_screening(output: Path, manifest: dict) -> None:
    """Record preliminary health-facility overlap with the candidate 2022-era city boundary."""
    facility_file = output / "health_facilities_ernakulam.geojson"
    boundary_file = output / "kochi_corporation_boundary_candidate.geojson"
    if not facility_file.exists() or not boundary_file.exists():
        return
    facilities = json.loads(facility_file.read_text(encoding="utf-8"))
    boundary_payload = json.loads(boundary_file.read_text(encoding="utf-8-sig"))
    boundary_feature = boundary_payload if boundary_payload.get("type") == "Feature" else None
    if boundary_feature is None:
        return
    geometry = boundary_feature.get("geometry") or {}
    inside = outside = invalid = 0
    for feature in facilities.get("features", []):
        point_geometry = feature.get("geometry") or {}
        coords = point_geometry.get("coordinates") or []
        if point_geometry.get("type") != "Point" or len(coords) < 2:
            invalid += 1
            continue
        try:
            point = (float(coords[0]), float(coords[1]))
        except (TypeError, ValueError):
            invalid += 1
            continue
        if not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
            invalid += 1
        elif point_in_geometry(point, geometry):
            inside += 1
        else:
            outside += 1
    for item in manifest["files"]:
        if item.get("filename") == "health_facilities_ernakulam.geojson":
            item["city_boundary_screening"] = {
                "boundary_file": boundary_file.name,
                "boundary_source": "DataMeet Trust / Kerala OpenSDI via India Geodata mirror",
                "boundary_date": "not established by source metadata; ward reference is 2022 and current 2024 delimitation must be checked",
                "candidate_facility_points": len(facilities.get("features", [])),
                "points_inside_candidate_boundary": inside,
                "points_outside_candidate_boundary": outside,
                "invalid_points_for_boundary_test": invalid,
                "status": "PRELIMINARY_SCREENING_ONLY_NOT_APPROVED",
                "limitation": "A point outside the 2022-era candidate boundary may be a valid Ernakulam district facility; the boundary is not yet confirmed as the current Kochi Corporation polygon."
            }
            break


def acquire(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / "map_reference_manifest.json"
    manifest = {
        "manifest_version": 1,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": "ACQUISITION_IN_PROGRESS",
        "files": [],
    }
    failures = []
    # Persist the manifest after every source, including failures, so partial runs
    # never leave successfully downloaded bytes without a provenance record.
    atomic_write(manifest_path, json.dumps(manifest, indent=2).encode("utf-8"))

    for filename, source in SOURCES.items():
        url = source["url"]
        record = dict(source)
        record.update({
            "filename": filename,
            "request_url": url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ACQUISITION_FAILED",
            "validation_status": "NOT_VALIDATED",
        })
        try:
            source_feature_count = None
            payload = None
            if filename == "health_facilities_ernakulam.geojson":
                # Query a bounded Ernakulam-area envelope first so the service does not
                # need to scan/download the national directory. If the spatial query returns
                # no IDs, try the Kerala state attribute as a secondary route.
                ernakulam_envelope = json.dumps({
                    "xmin": 75.9, "ymin": 9.5, "xmax": 77.0, "ymax": 10.6,
                    "spatialReference": {"wkid": 4326},
                }, separators=(",", ":"))
                spatial_ids_url = url + "?" + urllib.parse.urlencode({
                    "where": "1=1",
                    "geometry": ernakulam_envelope,
                    "geometryType": "esriGeometryEnvelope",
                    "inSR": "4326",
                    "spatialRel": "esriSpatialRelIntersects",
                    "returnIdsOnly": "true",
                    "f": "json",
                })
                ids_data, final_url, content_type = fetch(spatial_ids_url)
                ids_payload = json.loads(ids_data.decode("utf-8-sig"))
                object_ids = ids_payload.get("objectIds")
                if not isinstance(object_ids, list) or not object_ids:
                    ids_url = url + "?" + urllib.parse.urlencode({
                        "where": "statename='Kerala'",
                        "returnIdsOnly": "true",
                        "f": "json",
                    })
                    ids_data, final_url, content_type = fetch(ids_url)
                    ids_payload = json.loads(ids_data.decode("utf-8-sig"))
                    object_ids = ids_payload.get("objectIds")
                if not isinstance(object_ids, list) or not object_ids:
                    raise RuntimeError(
                        "Hospital service returned no object IDs for the Kerala filter or "
                        "Ernakulam-area spatial fallback; refusing to treat an empty response as valid GIS data."
                    )
                all_features = []
                for batch_start in range(0, len(object_ids), 500):
                    batch_url = url + "?" + urllib.parse.urlencode({
                        "objectIds": ",".join(str(value) for value in object_ids[batch_start:batch_start + 500]),
                        "outFields": "*",
                        "returnGeometry": "true",
                        "outSR": "4326",
                        "f": "geojson",
                    })
                    batch_data, final_url, content_type = fetch(batch_url)
                    batch_payload = json.loads(batch_data.decode("utf-8-sig"))
                    if batch_payload.get("type") != "FeatureCollection" or not isinstance(batch_payload.get("features"), list):
                        raise RuntimeError("Hospital service batch did not return a GeoJSON FeatureCollection.")
                    all_features.extend(batch_payload["features"])
                source_feature_count = len(all_features)
                filtered = []
                for feature in all_features:
                    props = feature.get("properties") or {}
                    state_value = props.get("state_name", props.get("statename", ""))
                    district_value = props.get("district_name", props.get("districtname", ""))
                    state = str(state_value).strip().casefold()
                    district = " ".join(str(district_value).strip().casefold().replace("-", " ").split())
                    if state == "kerala" and district in {"ernakulam", "ernakulam district", "ernakulam (kochi)"}:
                        # Normalize alternate layer fields while preserving all original properties.
                        props["state_name"] = str(state_value).strip()
                        props["district_name"] = str(district_value).strip()
                        props["health_facility_name"] = props.get("health_facility_name") or props.get("facilityname", "")
                        props["address"] = props.get("address") or props.get("facilityaddress", "")
                        props["facility_type"] = props.get("facility_type") or props.get("facilitytype", "")
                        feature["properties"] = props
                        filtered.append(feature)
                payload = {"type": "FeatureCollection", "features": filtered}
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            else:
                data, final_url, content_type = fetch(url)
            if not data:
                raise RuntimeError(f"Empty response from {source['publisher']}")
            record.update({
                "final_url": final_url,
                "content_type": content_type,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            })
            if filename == "health_facilities_ernakulam.geojson":
                # Health-facility features were assembled from all object-ID batches above.
                if payload.get("type") != "FeatureCollection" or not isinstance(payload.get("features"), list):
                    raise RuntimeError("Hospital service did not return a GeoJSON FeatureCollection.")
                features = payload["features"]
                record["source_feature_count"] = source_feature_count
                record["feature_count"] = len(features)
                if not features:
                    raise RuntimeError("Hospital query returned zero features; refusing to treat an empty GeoJSON response as a successful data download. Check the source query and field values.")
                record["geometry_type_counts"] = {}
                invalid_coordinates = 0
                district_mismatches = 0
                outside_kerala_screening_box = 0
                coordinate_pairs = []
                missing_facility_names = 0
                for feature in features:
                    geometry = feature.get("geometry") or {}
                    kind = geometry.get("type", "missing")
                    record["geometry_type_counts"][kind] = record["geometry_type_counts"].get(kind, 0) + 1
                    coordinates = geometry.get("coordinates")
                    if kind != "Point" or not isinstance(coordinates, list) or len(coordinates) < 2:
                        invalid_coordinates += 1
                    else:
                        lon, lat = coordinates[:2]
                        if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
                            invalid_coordinates += 1
                        else:
                            coordinate_pairs.append((round(float(lon), 6), round(float(lat), 6)))
                            # Broad state screening box only; never a substitute for a district polygon.
                            if not (74.0 <= float(lon) <= 78.0 and 8.0 <= float(lat) <= 13.0):
                                outside_kerala_screening_box += 1
                    props = feature.get("properties") or {}
                    if not str(props.get("health_facility_name", props.get("facilityname", props.get("name", "")))).strip():
                        missing_facility_names += 1
                    normalized_state = str(props.get("state_name", props.get("statename", ""))).strip().casefold()
                    normalized_district = " ".join(str(props.get("district_name", props.get("districtname", ""))).strip().casefold().replace("-", " ").split())
                    if normalized_state != "kerala" or normalized_district not in {"ernakulam", "ernakulam district", "ernakulam (kochi)"}:
                        district_mismatches += 1
                from collections import Counter
                coordinate_counts = Counter(coordinate_pairs)
                duplicate_groups = sum(1 for count in coordinate_counts.values() if count > 1)
                rows_in_duplicate_groups = sum(count for count in coordinate_counts.values() if count > 1)
                record["invalid_point_count"] = invalid_coordinates
                record["district_filter_mismatch_count"] = district_mismatches
                record["outside_kerala_screening_box_count"] = outside_kerala_screening_box
                record["missing_facility_name_count"] = missing_facility_names
                record["duplicate_coordinate_pair_group_count"] = duplicate_groups
                record["rows_in_duplicate_coordinate_pair_groups"] = rows_in_duplicate_groups
                record["validation_status"] = (
                    "STRUCTURE_CHECKED_WITH_SPATIAL_QA_FLAGS"
                    if invalid_coordinates or district_mismatches or outside_kerala_screening_box or missing_facility_names or duplicate_groups
                    else "STRUCTURE_CHECKED_SPATIAL_ACCURACY_AND_LICENCE_UNVERIFIED"
                )
                atomic_write(output / filename, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
            elif filename.endswith(".pdf"):
                if not data.startswith(b"%PDF-"):
                    raise RuntimeError("Kerala Health Department response is not a PDF; refusing to save an error page as reference data.")
                atomic_write(output / filename, data)
                record["validation_status"] = "PDF_SIGNATURE_CHECKED_FACILITY_MATCHING_REQUIRED"
            elif filename.endswith(".geojson"):
                try:
                    boundary_payload = json.loads(data.decode("utf-8-sig"))
                except (UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise RuntimeError(f"Boundary response is not valid GeoJSON: {error}") from error
                boundary_feature = boundary_payload if boundary_payload.get("type") == "Feature" else None
                boundary_geometry = (boundary_feature or {}).get("geometry") or {}
                if boundary_geometry.get("type") not in {"Polygon", "MultiPolygon"}:
                    raise RuntimeError("Kochi boundary GeoJSON does not contain a Polygon or MultiPolygon feature.")
                record["geometry_type"] = boundary_geometry.get("type")
                record["boundary_properties"] = boundary_feature.get("properties") or {}
                record["validation_status"] = "BOUNDARY_GEOJSON_STRUCTURE_CHECKED_CURRENTNESS_UNVERIFIED"
                atomic_write(output / filename, data)
            else:
                import io
                if not zipfile.is_zipfile(io.BytesIO(data)):
                    raise RuntimeError("KSDMA response is not a ZIP archive; refusing to save an error page as data.")
                with zipfile.ZipFile(io.BytesIO(data)) as archive:
                    bad_member = archive.testzip()
                    if bad_member is not None:
                        raise RuntimeError(f"KSDMA ZIP failed CRC check at member: {bad_member}")
                    members = [item for item in archive.infolist() if not item.is_dir()]
                    record["archive_member_count"] = len(members)
                    record["raster_candidates"] = [item.filename for item in members if item.filename.lower().endswith((".tif", ".tiff", ".vrt"))]
                    if not record["raster_candidates"]:
                        raise RuntimeError("KSDMA ZIP contains no TIFF/VRT raster candidates.")
                atomic_write(output / filename, data)
                record["validation_status"] = "ZIP_INTEGRITY_CHECKED_RASTER_SEMANTICS_UNVERIFIED"
            record["status"] = "DOWNLOADED_RAW_CANDIDATE"
        except Exception as error:
            record["status"] = "ACQUISITION_FAILED"
            record["error"] = f"{type(error).__name__}: {error}"
            failures.append(filename)
        manifest["files"].append(record)
        manifest["overall_status"] = (
            "RAW_CANDIDATES_NOT_APPROVED_FOR_MAP"
            if not failures and len(manifest["files"]) == len(SOURCES)
            else "PARTIAL_ACQUISITION_FAILED" if failures
            else "ACQUISITION_IN_PROGRESS"
        )
        manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_write(manifest_path, json.dumps(manifest, indent=2).encode("utf-8"))

    if not failures:
        add_boundary_screening(output, manifest)
        manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
        atomic_write(manifest_path, json.dumps(manifest, indent=2).encode("utf-8"))
    if failures:
        raise RuntimeError(
            "One or more map reference downloads failed: " + ", ".join(failures)
            + f". Partial provenance manifest saved to {manifest_path}."
        )
    return manifest

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = acquire(args.output_dir)
    for item in report["files"]:
        print(f"{item['filename']}: {item['validation_status']} ({item['size_bytes']} bytes)")
        if "feature_count" in item:
            print(f"  Features: {item['feature_count']}; invalid points: {item['invalid_point_count']}; filter mismatches: {item['district_filter_mismatch_count']}")
        if "raster_candidates" in item:
            print(f"  Raster candidates: {len(item['raster_candidates'])}; archive members: {item['archive_member_count']}")
    print("These files are raw candidates only; no layer was automatically approved for display or analysis.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

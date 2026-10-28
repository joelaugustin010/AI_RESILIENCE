"""Reproducible, cautious OpenStreetMap acquisition for the Kochi map."""

from __future__ import annotations

import hashlib
import gzip
import json
import math
import os
import shutil
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.spatial_data import geometry_errors, validate_geojson

OSM_COPYRIGHT_URL = "https://www.openstreetmap.org/copyright"
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
)
USER_AGENT = "AI_RESILIENCE geospatial data acquisition/1.0"
MAX_RESPONSE_BYTES = 100_000_000

# The Kochi boundary is provisional and self-intersects. Its numeric extent is
# used only as a query window; it is never used as a validated clipping mask.
KOCHI_BBOX = {
    "south": 9.889718280722308,
    "west": 76.23735890065669,
    "north": 10.049769312385111,
    "east": 76.34002933184016,
}
ERNAKULAM_URBAN_BBOX = {
    "south": 9.85,
    "west": 76.15,
    "north": 10.20,
    "east": 76.45,
}

ROAD_CLASSES = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "unclassified", "residential", "living_street",
}
RAIL_CLASSES = {"rail", "light_rail", "tram", "subway"}
WATERWAY_CLASSES = {"river", "canal", "stream", "drain", "ditch"}
HEALTH_AMENITIES = {"hospital", "clinic", "doctors"}
HEALTHCARE_VALUES = {"hospital", "clinic", "doctor"}
EMERGENCY_AMENITIES = {"fire_station", "police"}
EMERGENCY_VALUES = {"fire_service", "ambulance_station", "rescue_station"}
AIR_MONITOR_TAGS = {"monitoring:air_quality", "air_quality", "measurement:air_quality"}

LAYER_DEFINITIONS = {
    "roads": {
        "title": "OpenStreetMap mapped roads (Kochi map extent)",
        "feature_type": "mapped road",
        "bbox": KOCHI_BBOX,
        "limitations": [
            "Community-mapped coverage is incomplete and positional accuracy is not stated by the source.",
            "The query includes selected routable highway classes and omits footways, paths, cycleways, and service roads.",
            "The selected rectangle is derived from the provisional boundary extent; features are not clipped to a validated municipal boundary.",
            "This display does not provide route travel times, road condition, accessibility, or emergency response access.",
        ],
    },
    "transit": {
        "title": "OpenStreetMap mapped rail and transit ways (Ernakulam urban extent)",
        "feature_type": "mapped rail or transit way",
        "bbox": ERNAKULAM_URBAN_BBOX,
        "limitations": [
            "Community-mapped coverage is incomplete and positional accuracy is not stated by the source.",
            "Only selected rail and urban transit way types are queried; this is not a complete public-transport network or timetable.",
            "The query rectangle is an urban study extent, not an administrative boundary.",
        ],
    },
    "waterways": {
        "title": "OpenStreetMap mapped waterways and drainage-like ways (Ernakulam urban extent)",
        "feature_type": "mapped waterway",
        "bbox": ERNAKULAM_URBAN_BBOX,
        "limitations": [
            "Community-mapped coverage is incomplete and positional accuracy is not stated by the source.",
            "Mapped waterway=drain or ditch features are not a municipal storm-drain asset register and do not describe capacity, ownership, or flow direction.",
            "The query rectangle is an urban study extent, not an administrative boundary.",
        ],
    },
    "healthcare": {
        "title": "OpenStreetMap community-mapped healthcare facilities (Ernakulam urban extent)",
        "feature_type": "community-mapped healthcare facility",
        "bbox": ERNAKULAM_URBAN_BBOX,
        "limitations": [
            "Community-mapped locations are not an authoritative or complete facility register; opening status and services are not verified.",
            "A mapped way polygon is an OSM footprint; any fallback way center is approximate and is explicitly identified in feature properties.",
            "NIHFW source coordinates remain review-only because the source does not define coordinate order, CRS/datum, or positional accuracy.",
            "These locations are not used for flood-exposure or emergency-access conclusions.",
        ],
    },
    "emergency": {
        "title": "OpenStreetMap community-mapped emergency facilities (Ernakulam urban extent)",
        "feature_type": "community-mapped emergency facility",
        "bbox": ERNAKULAM_URBAN_BBOX,
        "limitations": [
            "Community-mapped locations are not an authoritative or complete facility register; operating status and response capability are not verified.",
            "A mapped way polygon is an OSM footprint; any fallback way center is approximate and is explicitly identified in feature properties.",
            "No response-time or service-area analysis is supported by this layer.",
        ],
    },
    "industry": {
        "title": "OpenStreetMap mapped industrial features (Ernakulam urban extent)",
        "feature_type": "community-mapped industrial feature",
        "bbox": ERNAKULAM_URBAN_BBOX,
        "limitations": [
            "Mapped industrial land use or works tags are not a verified factory register, current consent record, or emissions inventory.",
            "Community-mapped coverage is incomplete and positional accuracy is not stated by the source.",
            "A mapped industrial feature is a candidate location only; proximity does not establish pollution causation or exposure.",
            "A mapped way polygon is retained only when it passes structural geometry checks; fallback way centers are marked approximate.",
        ],
    },
    "air_monitors": {
        "title": "OpenStreetMap community-mapped air-quality monitoring sites (Ernakulam urban extent)",
        "feature_type": "community-mapped air-monitoring site",
        "bbox": ERNAKULAM_URBAN_BBOX,
        "limitations": [
            "This layer includes only OSM features explicitly tagged for air-quality monitoring; it is not a KSPCB/CPCB station inventory.",
            "Community-mapped station identity, operation, instruments, and coordinates are not verified.",
            "No observations are attached to these features unless a separate observation source supplies matching station identifiers and coordinates.",
        ],
    },
}

TAG_FIELDS = (
    "name", "name:en", "ref", "operator", "brand",
    "highway", "railway", "waterway", "amenity", "healthcare",
    "emergency", "industrial", "landuse", "man_made", "building",
    "surface", "bridge", "tunnel", "oneway", "access", "service",
    "public_transport", "monitoring", "monitoring:air_quality", "air_quality",
    "measurement:air_quality",
)


class OSMAcquisitionError(RuntimeError):
    """Raised when an Overpass response cannot be safely used."""


def _bbox_text(bounds: dict[str, float]) -> str:
    return ",".join(f"{bounds[key]:.8f}" for key in ("south", "west", "north", "east"))


def overpass_queries() -> dict[str, str]:
    """Return bounded thematic queries; no invalid city polygon is used."""
    kochi = _bbox_text(KOCHI_BBOX)
    urban = _bbox_text(ERNAKULAM_URBAN_BBOX)
    network = f"""[out:json][timeout:120];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|living_street)$"]({kochi});
  way["railway"~"^(rail|light_rail|tram|subway)$"]({urban});
  way["waterway"~"^(river|canal|stream|drain|ditch)$"]({urban});
);
out geom;"""
    facilities = f"""[out:json][timeout:120];
(
  node["amenity"~"^(hospital|clinic|doctors|fire_station|police)$"]({urban});
  way["amenity"~"^(hospital|clinic|doctors|fire_station|police)$"]({urban});
  node["healthcare"~"^(hospital|clinic|doctor)$"]({urban});
  way["healthcare"~"^(hospital|clinic|doctor)$"]({urban});
  node["emergency"~"^(fire_service|ambulance_station|rescue_station)$"]({urban});
  way["emergency"~"^(fire_service|ambulance_station|rescue_station)$"]({urban});
  node["man_made"="works"]({urban});
  way["man_made"="works"]({urban});
  node["industrial"]({urban});
  way["industrial"]({urban});
  way["landuse"="industrial"]({urban});
  node["man_made"="monitoring_station"]({urban});
  way["man_made"="monitoring_station"]({urban});
  node["monitoring:air_quality"]({urban});
  way["monitoring:air_quality"]({urban});
  node["monitoring"~"air"]({urban});
  way["monitoring"~"air"]({urban});
  node["air_quality"]({urban});
  way["air_quality"]({urban});
  node["measurement:air_quality"]({urban});
  way["measurement:air_quality"]({urban});
);
out center geom;"""
    return {"network": network, "facilities": facilities}


def request_overpass(
    query: str,
    endpoints: tuple[str, ...] = OVERPASS_ENDPOINTS,
    retries_per_endpoint: int = 2,
    timeout: int = 150,
) -> tuple[bytes, dict[str, Any], str]:
    """Fetch and validate one Overpass JSON response with bounded retries."""
    failures: list[str] = []
    for endpoint in endpoints:
        for attempt in range(retries_per_endpoint):
            request = urllib.request.Request(
                endpoint,
                data=urllib.parse.urlencode({"data": query}).encode("utf-8"),
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    raw = response.read(MAX_RESPONSE_BYTES + 1)
                    if len(raw) > MAX_RESPONSE_BYTES:
                        raise OSMAcquisitionError(
                            f"Overpass response exceeded the {MAX_RESPONSE_BYTES // 1_000_000} MB safety limit."
                        )
                    content_type = response.headers.get("Content-Type", "")
                    if "json" not in content_type.casefold():
                        raise OSMAcquisitionError(
                            f"Overpass returned unexpected content type {content_type!r}; no file was written."
                        )
                    payload = json.loads(raw.decode("utf-8"))
                    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
                        raise OSMAcquisitionError("Overpass JSON does not contain an elements list.")
                    if not isinstance(payload.get("osm3s"), dict):
                        raise OSMAcquisitionError("Overpass response is missing its database timestamp metadata.")
                    return raw, payload, endpoint
            except urllib.error.HTTPError as error:
                body = error.read(1000).decode("utf-8", "replace")
                failures.append(f"{endpoint}: HTTP {error.code}: {body[:250]}")
                if error.code not in {429, 502, 503, 504}:
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSMAcquisitionError) as error:
                failures.append(f"{endpoint}: {error}")
                if isinstance(error, OSMAcquisitionError) and "safety limit" in str(error):
                    raise
            if attempt + 1 < retries_per_endpoint:
                time.sleep(min(2 ** attempt, 4))
    details = "; ".join(failures[-6:])
    raise OSMAcquisitionError(f"No Overpass endpoint returned a usable response. {details}")


def _valid_lonlat(longitude: Any, latitude: Any) -> tuple[float, float] | None:
    try:
        lon, lat = float(longitude), float(latitude)
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    return lon, lat


def _way_positions(element: dict[str, Any]) -> list[list[float]]:
    geometry = element.get("geometry")
    if not isinstance(geometry, list):
        return []
    positions = []
    for point in geometry:
        if not isinstance(point, dict):
            return []
        position = _valid_lonlat(point.get("lon"), point.get("lat"))
        if position is None:
            return []
        positions.append([position[0], position[1]])
    return positions


def _is_area_way(tags: dict[str, str], positions: list[list[float]]) -> bool:
    if len(positions) < 4 or positions[0] != positions[-1]:
        return False
    return tags.get("area") == "yes" or any(
        key in tags for key in ("amenity", "healthcare", "emergency", "landuse", "industrial", "man_made", "building")
    )


def _element_geometry(
    element: dict[str, Any],
    tags: dict[str, str],
    layer_key: str,
) -> tuple[dict[str, Any] | None, str | None]:
    element_type = element.get("type")
    if element_type == "node":
        position = _valid_lonlat(element.get("lon"), element.get("lat"))
        if position is None:
            return None, None
        return {"type": "Point", "coordinates": [position[0], position[1]]}, "OSM node coordinates"

    if element_type != "way":
        return None, None
    positions = _way_positions(element)
    if len(positions) < 2:
        return None, None

    is_candidate_area = layer_key in {"healthcare", "emergency", "industry"} and _is_area_way(tags, positions)
    if is_candidate_area:
        polygon = {"type": "Polygon", "coordinates": [positions]}
        if not geometry_errors(polygon):
            return polygon, "OSM closed-way polygon"
        center = element.get("center") or {}
        position = _valid_lonlat(center.get("lon"), center.get("lat"))
        if position is not None:
            return (
                {"type": "Point", "coordinates": [position[0], position[1]]},
                "Overpass way bounding-box center; source polygon failed structural QA",
            )
        return None, None
    return {"type": "LineString", "coordinates": positions}, "OSM way geometry"


def _categories(tags: dict[str, str]) -> list[str]:
    categories: list[str] = []
    if tags.get("highway") in ROAD_CLASSES:
        categories.append("roads")
    if tags.get("railway") in RAIL_CLASSES:
        categories.append("transit")
    if tags.get("waterway") in WATERWAY_CLASSES:
        categories.append("waterways")

    is_emergency = tags.get("amenity") in EMERGENCY_AMENITIES or tags.get("emergency") in EMERGENCY_VALUES
    if is_emergency:
        categories.append("emergency")
    elif tags.get("amenity") in HEALTH_AMENITIES or tags.get("healthcare") in HEALTHCARE_VALUES:
        categories.append("healthcare")

    if tags.get("man_made") == "works" or "industrial" in tags or tags.get("landuse") == "industrial":
        categories.append("industry")

    air_tag = any(
        key in tags and str(tags[key]).casefold() not in {"", "no", "false", "0"}
        for key in AIR_MONITOR_TAGS
    )
    if air_tag or (
        tags.get("man_made") == "monitoring_station"
        and "air" in tags.get("monitoring", "").casefold()
    ):
        categories.append("air_monitors")
    return categories


def parse_osm_layers(payload: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Convert selected Overpass nodes/ways into validated GeoJSON features."""
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise OSMAcquisitionError("Payload must be Overpass JSON with an elements list.")
    osm_timestamp = str((payload.get("osm3s") or {}).get("timestamp_osm_base") or "")
    if not osm_timestamp:
        raise OSMAcquisitionError("Payload is missing osm3s.timestamp_osm_base.")

    layers = {key: [] for key in LAYER_DEFINITIONS}
    seen: dict[str, set[str]] = {key: set() for key in layers}
    invalid: dict[str, list[dict[str, str]]] = {key: [] for key in layers}
    source_counts = {key: 0 for key in layers}
    duplicate_counts = {key: 0 for key in layers}

    for element in payload["elements"]:
        if not isinstance(element, dict):
            continue
        osm_type = str(element.get("type") or "")
        osm_id = element.get("id")
        if osm_type not in {"node", "way"} or osm_id is None:
            continue
        raw_tags = element.get("tags")
        if not isinstance(raw_tags, dict):
            continue
        tags = {str(key): str(value) for key, value in raw_tags.items()}
        for layer_key in _categories(tags):
            source_counts[layer_key] += 1
            identity = f"{osm_type}/{osm_id}"
            if identity in seen[layer_key]:
                duplicate_counts[layer_key] += 1
                continue
            seen[layer_key].add(identity)
            geometry, placement = _element_geometry(element, tags, layer_key)
            if geometry is None:
                invalid[layer_key].append({"osm_id": identity, "reason": "Missing or invalid source coordinates."})
                continue
            errors = geometry_errors(geometry)
            if errors:
                invalid[layer_key].append({"osm_id": identity, "reason": " ".join(errors)})
                continue

            subtype_key = next(
                (key for key in ("highway", "railway", "waterway", "amenity", "healthcare", "emergency", "industrial", "landuse", "man_made") if tags.get(key)),
                "type",
            )
            name = tags.get("name") or tags.get("name:en") or f"OSM {osm_type} {osm_id}"
            properties: dict[str, Any] = {
                key: tags[key] for key in TAG_FIELDS if key in tags
            }
            properties.update({
                "osm_type": osm_type,
                "osm_id": str(osm_id),
                "osm_url": f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                "feature_type": LAYER_DEFINITIONS[layer_key]["feature_type"],
                "feature_name": name,
                "feature_subtype": f"{subtype_key}: {tags[subtype_key]}" if subtype_key != "type" else "mapped feature",
                "placement_method": placement,
                "source": "OpenStreetMap contributors",
                "data_status": "PROVISIONAL",
                "osm_timestamp": osm_timestamp,
            })
            layers[layer_key].append({
                "type": "Feature",
                "id": identity,
                "geometry": geometry,
                "properties": properties,
            })

    qa = {
        "osm_timestamp": osm_timestamp,
        "source_element_count": len(payload["elements"]),
        "source_counts_by_layer": source_counts,
        "processed_counts_by_layer": {key: len(value) for key, value in layers.items()},
        "duplicate_counts_by_layer": duplicate_counts,
        "excluded_by_layer": invalid,
    }
    return layers, qa


def _write_exclusive(path: Path, data: bytes) -> None:
    """Write a new file without replacing an existing path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    handle, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise FileExistsError(f"Refusing to overwrite existing file: {path}")
        except OSError:
            created = False
            try:
                with path.open("xb") as target:
                    created = True
                    with temporary.open("rb") as source:
                        shutil.copyfileobj(source, target)
                    target.flush()
                    os.fsync(target.fileno())
            except Exception:
                if created:
                    path.unlink(missing_ok=True)
                raise
    finally:
        temporary.unlink(missing_ok=True)


def write_raw_snapshot(
    raw_dir: Path,
    query_name: str,
    raw: bytes,
    payload: dict[str, Any],
    query: str,
    endpoint: str,
    retrieved_at: datetime,
) -> tuple[Path, dict[str, Any]]:
    """Preserve one timestamped OSM response and a provenance sidecar."""
    stamp = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
    snapshot_id = f"kochi_{query_name}_{stamp}"
    path = Path(raw_dir) / f"{snapshot_id}.json.gz"
    digest = hashlib.sha256(raw).hexdigest()
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    compressed_digest = hashlib.sha256(compressed).hexdigest()
    metadata = {
        "dataset_id": f"osm_kochi_{query_name}_{stamp}",
        "title": f"OpenStreetMap {query_name} query response for Kochi/Ernakulam",
        "publisher": "OpenStreetMap contributors",
        "source_url": "https://www.openstreetmap.org/",
        "copyright_url": OSM_COPYRIGHT_URL,
        "query_service_url": endpoint,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "retrieved_on": retrieved_at.date().isoformat(),
        "osm_timestamp": (payload.get("osm3s") or {}).get("timestamp_osm_base"),
        "license": "Open Database License 1.0 (ODbL); attribution and share-alike apply to this extracted database.",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "attribution": "© OpenStreetMap contributors",
        "query": query,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "response_sha256": digest,
        "response_bytes": len(raw),
        "snapshot_file": path.name,
        "snapshot_compression": "gzip (lossless)",
        "snapshot_file_sha256": compressed_digest,
        "snapshot_file_bytes": len(compressed),
        "source_element_count": len(payload.get("elements", [])),
        "geographic_coverage": "See query bounding boxes; bounding boxes are acquisition windows, not administrative boundaries.",
        "crs": "WGS 84 longitude/latitude (EPSG:4326)",
        "limitations": [
            "OpenStreetMap is community-mapped and is not an authoritative completeness or positional-accuracy statement.",
            "The Overpass response is a dated database extract, not a live feed.",
            "The query uses bounding boxes and is not clipped to an administrative boundary.",
        ],
    }
    _write_exclusive(path, compressed)
    metadata_path = path.with_name(snapshot_id + ".metadata.json")
    _write_exclusive(metadata_path, json.dumps(metadata, indent=2, ensure_ascii=False).encode("utf-8"))
    return path, metadata


def _metadata_for_layer(
    layer_key: str,
    dataset_id: str,
    features: list[dict[str, Any]],
    query_metadata: dict[str, Any],
    query: str,
    raw_path: Path,
    raw_sha256: str,
    retrieved_at: datetime,
    qa: dict[str, Any],
) -> dict[str, Any]:
    definition = LAYER_DEFINITIONS[layer_key]
    bounds = definition["bbox"]
    return {
        "dataset_id": dataset_id,
        "logical_layer_id": f"osm_kochi_{layer_key}",
        "title": definition["title"],
        "publisher": "OpenStreetMap contributors",
        "source_url": "https://www.openstreetmap.org/",
        "copyright_url": OSM_COPYRIGHT_URL,
        "query_service_url": query_metadata["query_service_url"],
        "retrieved_on": retrieved_at.date().isoformat(),
        "retrieved_at_utc": retrieved_at.isoformat(),
        "publication_date": f"Not stated by source; OSM database state as of {query_metadata['osm_timestamp']}",
        "license": "Open Database License 1.0 (ODbL); attribution and share-alike apply to the extracted database.",
        "license_url": "https://opendatacommons.org/licenses/odbl/1-0/",
        "attribution": "© OpenStreetMap contributors",
        "crs": "EPSG:4326",
        "units": "Decimal degrees (longitude, latitude); source-specific tags have no common measurement units.",
        "geographic_coverage": (
            f"Bounding box south={bounds['south']}, west={bounds['west']}, "
            f"north={bounds['north']}, east={bounds['east']}; query selection only, not a legal boundary."
        ),
        "coverage_bbox_south_west_north_east": [
            bounds["south"], bounds["west"], bounds["north"], bounds["east"]
        ],
        "layer_role": "context",
        "validation_status": "PROVISIONAL",
        "analysis_status": "Context display only; not used for exposure, safety, source-attribution, or emergency-access conclusions.",
        "required_properties": ["osm_type", "osm_id", "feature_type", "feature_name", "source", "osm_url"],
        "source_query": query,
        "source_query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "source_database_timestamp": query_metadata["osm_timestamp"],
        "source_snapshot_file": raw_path.name,
        "source_snapshot_sha256": raw_sha256,
        "source_snapshot_stored_sha256": query_metadata.get("snapshot_file_sha256", "Not separately recorded"),
        "source_feature_count": qa["source_counts_by_layer"][layer_key],
        "processed_feature_count": len(features),
        "excluded_invalid_features": qa["excluded_by_layer"][layer_key],
        "duplicate_count": qa["duplicate_counts_by_layer"][layer_key],
        "limitations": list(definition["limitations"]),
        "quality_notes": [
            "Coordinates and tags are taken from a community-maintained OSM database snapshot.",
            "Feature locations were checked for GeoJSON structure and WGS 84 coordinate ranges; source completeness and ground truth were not authenticated.",
        ],
        "field_definitions": {
            "osm_type": "OpenStreetMap object type (node or way).",
            "osm_id": "OpenStreetMap object ID, preserved as text.",
            "feature_name": "OSM name/name:en value, or an explicit object ID label if unnamed.",
            "feature_subtype": "Selected OSM tag used for map categorization.",
            "placement_method": "Source node coordinates, way geometry, or explicitly marked Overpass bounding-box center fallback.",
        },
    }


def _publish_processed_layer(
    processed_dir: Path,
    layer_key: str,
    features: list[dict[str, Any]],
    query_metadata: dict[str, Any],
    query: str,
    raw_path: Path,
    raw_sha256: str,
    retrieved_at: datetime,
    qa: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:
    """Validate then publish a timestamped GeoJSON and matching sidecar."""
    if not features:
        raise OSMAcquisitionError(f"No valid {layer_key} features were returned; no empty layer was written.")
    stamp = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
    dataset_id = f"osm_kochi_{layer_key}_{stamp}"
    output_dir = Path(processed_dir) / "spatial_layers"
    geojson_path = output_dir / f"{dataset_id}.geojson"
    metadata_path = output_dir / f"{dataset_id}.metadata.json"
    if geojson_path.exists() or metadata_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing processed layer {dataset_id}.")

    output_dir.mkdir(parents=True, exist_ok=True)
    geojson_bytes = json.dumps(
        {"type": "FeatureCollection", "features": features},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    temporary_geojson = output_dir / f".{dataset_id}.validation.tmp.geojson"
    try:
        with temporary_geojson.open("xb") as stream:
            stream.write(geojson_bytes)
        metadata = _metadata_for_layer(
            layer_key, dataset_id, features, query_metadata, query, raw_path, raw_sha256, retrieved_at, qa
        )
        report = validate_geojson(
            temporary_geojson,
            metadata,
            required_properties=metadata["required_properties"],
        )
        if report["errors"] or not report["provenance_valid"]:
            raise OSMAcquisitionError(
                f"{layer_key} GeoJSON failed validation: {' '.join(report['errors'])}"
            )
        report["source_file"] = geojson_path.name
        metadata["validation"] = report
        metadata["processed_file"] = geojson_path.name
        metadata["processed_sha256"] = report["source_sha256"]
        metadata_bytes = json.dumps(metadata, indent=2, ensure_ascii=False).encode("utf-8")

        geojson_temp_fd, geojson_temp_name = tempfile.mkstemp(prefix=f".{dataset_id}.", suffix=".tmp", dir=output_dir)
        metadata_temp_fd, metadata_temp_name = tempfile.mkstemp(prefix=f".{dataset_id}.metadata.", suffix=".tmp", dir=output_dir)
        geojson_temp = Path(geojson_temp_name)
        metadata_temp = Path(metadata_temp_name)
        created: list[Path] = []
        try:
            with os.fdopen(geojson_temp_fd, "wb") as stream:
                stream.write(geojson_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            with os.fdopen(metadata_temp_fd, "wb") as stream:
                stream.write(metadata_bytes)
                stream.flush()
                os.fsync(stream.fileno())
            for temporary, destination in ((geojson_temp, geojson_path), (metadata_temp, metadata_path)):
                try:
                    os.link(temporary, destination)
                except FileExistsError:
                    raise FileExistsError(f"Refusing to overwrite existing processed layer file {destination}.")
                except OSError:
                    with destination.open("xb") as target:
                        created.append(destination)
                        with temporary.open("rb") as source:
                            shutil.copyfileobj(source, target)
                        target.flush()
                        os.fsync(target.fileno())
                else:
                    created.append(destination)
        except Exception:
            for path in created:
                path.unlink(missing_ok=True)
            raise
        finally:
            geojson_temp.unlink(missing_ok=True)
            metadata_temp.unlink(missing_ok=True)
        return geojson_path, metadata
    finally:
        temporary_geojson.unlink(missing_ok=True)


def acquire_layers(
    raw_dir: Path,
    processed_dir: Path,
    endpoints: tuple[str, ...] = OVERPASS_ENDPOINTS,
    retries_per_endpoint: int = 2,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Acquire thematic extracts independently; retain successes if another query fails."""
    retrieved_at = now or datetime.now(timezone.utc)
    queries = overpass_queries()
    results: dict[str, Any] = {"started_at_utc": retrieved_at.isoformat(), "layers": {}, "errors": []}
    query_layers = {
        "network": ("roads", "transit", "waterways"),
        "facilities": ("healthcare", "emergency", "industry", "air_monitors"),
    }

    for query_name, layer_keys in query_layers.items():
        query = queries[query_name]
        try:
            raw, payload, endpoint = request_overpass(
                query, endpoints=endpoints, retries_per_endpoint=retries_per_endpoint
            )
        except OSMAcquisitionError as error:
            message = f"{query_name} query failed: {error}"
            results["errors"].append(message)
            for layer_key in layer_keys:
                results["layers"][layer_key] = {"status": "UNAVAILABLE", "reason": message, "feature_count": 0}
            continue

        query_time = datetime.now(timezone.utc)
        raw_path, query_metadata = write_raw_snapshot(
            raw_dir, query_name, raw, payload, query, endpoint, query_time
        )
        raw_sha256 = hashlib.sha256(raw).hexdigest()
        layer_features, qa = parse_osm_layers(payload)
        for layer_key in layer_keys:
            features = layer_features[layer_key]
            if not features:
                results["layers"][layer_key] = {
                    "status": "UNAVAILABLE",
                    "reason": "The bounded OSM query returned no structurally valid tagged features for this category.",
                    "feature_count": 0,
                    "osm_timestamp": qa["osm_timestamp"],
                    "raw_snapshot": raw_path.name,
                }
                continue
            try:
                geojson_path, metadata = _publish_processed_layer(
                    processed_dir, layer_key, features, query_metadata, query,
                    raw_path, raw_sha256, query_time, qa
                )
            except (OSError, ValueError, OSMAcquisitionError) as error:
                message = f"{layer_key} processing failed: {error}"
                results["errors"].append(message)
                results["layers"][layer_key] = {"status": "UNAVAILABLE", "reason": message, "feature_count": 0}
                continue
            results["layers"][layer_key] = {
                "status": "PROVISIONAL",
                "feature_count": len(features),
                "path": str(geojson_path),
                "metadata_path": str(geojson_path.with_name(geojson_path.stem + ".metadata.json")),
                "osm_timestamp": qa["osm_timestamp"],
                "raw_snapshot": raw_path.name,
                "excluded_invalid_count": len(qa["excluded_by_layer"][layer_key]),
                "duplicate_count": qa["duplicate_counts_by_layer"][layer_key],
                "validation": metadata["validation"],
            }
    results["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    return results

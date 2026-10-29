"""Kochi map showing licensed reference geometry and user-reviewed points."""

import json
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.spatial_data import classify_exposure, processed_layer_issues, read_processed_layers, validate_geojson

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "data" / "reference" / "kochi_corporation_boundary.geojson"
SOURCE_CATALOG_PATH = ROOT / "data" / "reference" / "spatial_sources.json"
FLOOD_ACQUISITION_METADATA = ROOT / "data" / "raw" / "ksdma_flood_return_probability_historical_10_25_50.metadata.json"
HOSPITAL_REVIEW_METADATA = ROOT / "data" / "processed" / "nihfw_ernakulam_hospitals_coordinate_review.metadata.json"
HOSPITAL_REVIEW_CSV = ROOT / "data" / "processed" / "nihfw_ernakulam_hospitals_coordinate_review.csv"


def _first_property(properties: dict, candidates: tuple[str, ...], fallback: str) -> str:
    """Return the first populated source property without assuming every dataset uses the same schema."""
    def normalize_key(value: object) -> str:
        # GeoJSON publishers commonly vary between Bound_Name, Bound Name,
        # bound-name, and camel-case spellings.
        return "".join(character for character in str(value).casefold() if character.isalnum())

    normalized = {normalize_key(key): value for key, value in properties.items()}
    for candidate in candidates:
        value = normalized.get(normalize_key(candidate))
        if value is not None and str(value).strip() and str(value).strip().casefold() not in {"nan", "none", "null"}:
            return str(value).strip()
    return fallback


def normalize_geojson_for_tooltip(geojson: dict) -> dict:
    """Add display-only aliases while preserving every original property and geometry."""
    display = json.loads(json.dumps(geojson))

    def normalize_feature(feature: dict) -> None:
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            properties = {}
            feature["properties"] = properties
        properties["display_bound"] = _first_property(
            properties,
            ("Bound_Name", "Bound Name", "bound_name", "boundname", "boundary_name", "name"),
            "Not available in source data",
        )
        properties["display_ward"] = _first_property(
            properties,
            ("Ward_Name", "Ward Name", "ward_name", "wardname", "Ward_No", "ward_no", "ward", "ward_number"),
            "Not available in source data",
        )
        properties["display_name"] = _first_property(
            properties,
            ("feature_name", "name", "name_en", "Bound_Name", "Ward_Name", "amenity", "highway", "landuse"),
            "Unnamed feature",
        )
        properties["display_type"] = _first_property(
            properties,
            ("feature_subtype", "feature_type", "type", "amenity", "highway", "landuse", "building"),
            "Not recorded",
        )
        properties["display_source"] = _first_property(
            properties, ("source", "source_name", "publisher", "provider"), "Not recorded"
        )
        properties["display_timestamp"] = _first_property(
            properties, ("osm_timestamp", "timestamp", "last_edited", "updated_at"), "Not recorded"
        )
        properties["display_url"] = _first_property(
            properties, ("osm_url", "url", "source_url"), "Not recorded"
        )

    if display.get("type") == "FeatureCollection":
        for feature in display.get("features", []):
            if isinstance(feature, dict):
                normalize_feature(feature)
    elif display.get("type") == "Feature":
        normalize_feature(display)
    return display


@st.cache_data
def load_boundary() -> dict:
    """Load the downloaded GeoJSON; fail clearly if it is missing or malformed."""
    with BOUNDARY_PATH.open(encoding="utf-8") as source:
        feature = json.load(source)
    if feature.get("type") != "Feature" or feature.get("geometry", {}).get("type") != "Polygon":
        raise ValueError("Expected a single GeoJSON Polygon Feature.")
    ring = feature["geometry"].get("coordinates", [[]])[0]
    if len(ring) < 4 or ring[0] != ring[-1]:
        raise ValueError("Boundary polygon ring is missing or not closed.")
    return feature


@st.cache_data
def load_source_catalog() -> dict:
    """Load reviewed data-source records; candidates remain visibly unavailable."""
    with SOURCE_CATALOG_PATH.open(encoding="utf-8") as source:
        return json.load(source)


@st.cache_data
def load_acquisition_metadata(path: Path) -> dict | None:
    """Read acquisition sidecars for datasets that are not eligible map layers."""
    try:
        with path.open(encoding="utf-8") as source:
            return json.load(source)
    except (OSError, json.JSONDecodeError):
        return None


@st.cache_data
def load_hospital_review() -> pd.DataFrame:
    """Read the preserved review-only records; this does not create points."""
    return pd.read_csv(HOSPITAL_REVIEW_CSV, dtype={"Sr_No": "string"})


@st.cache_data
def validate_boundary() -> dict:
    """Check the bundled provisional polygon without repairing its source file."""
    metadata_path = ROOT / "data" / "reference" / "kochi_corporation_boundary.metadata.json"
    with metadata_path.open(encoding="utf-8") as source:
        metadata = json.load(source)
    return validate_geojson(BOUNDARY_PATH, metadata)


@st.cache_data
def load_processed_layers(boundary_geometry: dict | None) -> list[dict]:
    """Read only processed layers that pass the local provenance/geometry checks."""
    return read_processed_layers(ROOT / "data" / "processed", boundary_geometry)


@st.cache_data
def load_processed_layer_issues(boundary_geometry: dict | None) -> list[str]:
    """Report files excluded from the map because their provenance or QA failed."""
    return processed_layer_issues(ROOT / "data" / "processed", boundary_geometry)


st.header("Kochi GIS and infrastructure map")
st.caption("Layer status and source records are explicit. The corporation boundary is an administrative outline, not a hazard or vulnerability layer.")

catalog = load_source_catalog()
catalog_rows = [{
    "Layer": item["title"],
    "Spatial status": item.get("validation_status", ""),
    "Source record status": item["status"],
    "Features": item.get("feature_count", "Not ingested"),
    "Publisher": item["publisher"],
    "Coverage": item["geographic_coverage"],
    "CRS": item["crs"],
    "Licence / reuse": item["license"],
} for item in catalog["datasets"]]
st.subheader("Source and layer catalog")
st.dataframe(pd.DataFrame(catalog_rows), hide_index=True, width="stretch", alt="Reviewed Kochi spatial source inventory with availability, coverage, CRS, and reuse status")
ward_candidate = next(
    (item for item in catalog["datasets"] if item.get("layer_id") == "kochi_wards_opencity_2024_candidate"),
    None,
)
if ward_candidate:
    geometry_comparison = ward_candidate.get("geometry_comparison", {})
    if geometry_comparison.get("status") == "COMPLETED_SHAPE_COMPARISON_NOT_LEGAL_APPROVAL":
        st.warning(
            "The OpenCity 2024 ward candidate and the configured provisional Kochi Corporation boundary disagree substantially: "
            f"intersection-over-union {geometry_comparison.get('intersection_over_union', 'unknown')}, "
            f"symmetric difference {geometry_comparison.get('symmetric_difference_area_km2', 'unknown')} km². "
            "Neither geometry is promoted by this comparison. The candidate remains excluded from exposure masking until its source and final official notification alignment are resolved.",
            title="2024 ward boundary candidate is not approved",
        )
    else:
        st.info(
            "The OpenCity 2024 ward map is recorded as a candidate only. It is not used as the production boundary or exposure mask.",
            title="2024 ward boundary candidate",
        )
air_observation_status = next(
    (item for item in catalog["datasets"] if item.get("layer_id") == "air_observations_spatial_locations"),
    None,
)
if air_observation_status:
    st.warning(
        f"Spatial air-observation layer: {air_observation_status['validation_status']}. "
        f"{air_observation_status['blocker']} Dated source reports remain available on the air-pollution page.",
        title="Air observations are not mapped to validated stations",
    )
for item in catalog["datasets"]:
    with st.expander(item["title"]):
        source_ref = item["source_url"]
        source_display = f"[{source_ref}]({source_ref})" if source_ref.startswith(("https://", "http://")) else source_ref
        st.markdown(f"**Publisher:** {item['publisher']}  \n**Source:** {source_display}  \n**Retrieved:** {item['retrieved_on']}  \n**Publication date:** {item['publication_date']}  \n**CRS:** {item['crs']}  \n**Units:** {item['units']}  \n**Reuse terms:** {item['license']}")
        if item.get("download_urls"):
            st.markdown("**Linked source files:** " + " | ".join(f"[file {index}]({url})" for index, url in enumerate(item["download_urls"], start=1)))
        st.write("**Limitations:**", " ".join(item["limitations"]))
        if item.get("blocker"):
            st.warning(item["blocker"])

flood_metadata = load_acquisition_metadata(FLOOD_ACQUISITION_METADATA)
hospital_metadata = load_acquisition_metadata(HOSPITAL_REVIEW_METADATA)
if flood_metadata or hospital_metadata:
    st.subheader("Recent real-data acquisition status")
    if flood_metadata:
        st.warning(
            "KSDMA historical flood archive obtained and checksum-verified. Its GeoTIFFs identify EPSG:4326 and "
            "declare a NoData sentinel (-3.402823e38), but the valid pixel meaning/units and dataset reuse terms "
            "remain undocumented. The raw archive is not rendered or used for exposure; unknown exposure is not a safe result.",
            title="Flood hazard layer unavailable for analysis",
        )
        st.caption(
            f"Raw archive SHA-256: {flood_metadata.get('sha256', 'not recorded')}. "
            f"Publisher: {flood_metadata.get('publisher', 'not recorded')}. "
            f"[KSDMA hazard catalogue]({flood_metadata.get('source_url', 'https://sdma.kerala.gov.in/hazard-maps/')})"
        )
    if hospital_metadata:
        validation = hospital_metadata.get("validation", {})
        st.info(
            f"NIHFW hospital directory obtained under GODL-India and reviewed for Ernakulam: "
            f"{validation.get('selected_record_count', 'unknown')} records; "
            f"{validation.get('coordinate_pair_unparseable_count', 'unknown')} missing/nonnumeric coordinate pairs; "
            f"{validation.get('duplicate_coordinate_pair_group_count', 'unknown')} repeated coordinate-pair groups. "
            "The source does not specify coordinate order or CRS, so these remain a CSV QA review and are not plotted as hospital points."
        )
        st.caption(
            "[NIHFW directory record](https://www.data.gov.in/resource/national-hospital-directory-geo-code-and-additional-parameters-updated-till-last-month) "
            "| [GODL-India terms](https://www.data.gov.in/Godl)"
        )
        with st.expander("Review NIHFW Ernakulam records; none are currently eligible for sampling"):
            st.write(
                "All 180 source rows are retained below with their source serial number. "
                "No rows are eligible for raster sampling because the directory does not establish coordinate order, CRS/datum, "
                "or per-record geocoding accuracy. Thirty-one coordinate strings are missing or nonnumeric. "
                "Eighteen repeated coordinate-pair groups cover 63 rows; repeated coordinates are flagged, not deleted, "
                "because they may represent shared locations or source duplication."
            )
            st.caption(
                "Alternative official identity reference: the [Kerala Health institution directory]"
                "(https://health.kerala.gov.in/index.php/institutionSearch) lists facility names, addresses, service details, "
                "and View Map controls. Its accessible page does not provide a downloadable GIS layer or a published CRS, "
                "positional-accuracy statement, or spatial-data reuse terms, so it is not used to assign coordinates."
            )
            try:
                review = load_hospital_review().copy()
                review["Flood sampling eligibility"] = "Not eligible: coordinate order / CRS / location accuracy unverified"
                missing_pair = review["coordinate_pair_parse_status"].ne("two finite numeric values")
                review.loc[missing_pair, "Flood sampling eligibility"] = "Not eligible: missing or nonnumeric coordinate pair"
                display_columns = [
                    "Sr_No", "Hospital_Name", "Hospital_Category", "Location_Coordinates", "Location",
                    "Pincode", "coordinate_pair_parse_status", "duplicate_coordinate_pair_count_in_subset",
                    "Flood sampling eligibility",
                ]
                st.dataframe(
                    review[display_columns], hide_index=True, width="stretch",
                    alt="Source-preserving audit of 180 NIHFW Ernakulam hospital records; every row is marked ineligible for flood sampling until its coordinates are verified",
                )
            except (OSError, KeyError, pd.errors.ParserError) as error:
                st.warning(f"The hospital coordinate review table could not be loaded: {error}")

try:
    boundary = load_boundary()
    boundary_report = validate_boundary()
except (OSError, json.JSONDecodeError, ValueError) as error:
    st.error(f"The Kochi boundary could not be loaded: {error}")
    st.stop()

if boundary_report["errors"]:
    geometry_details = [
        detail
        for issue in boundary_report["invalid_features"]
        for detail in issue["errors"]
    ]
    st.warning(
        "The provisional boundary file is displayed unchanged for orientation, but its geometry QA found issues. "
        "It is not used as a verified coverage boundary for spatial validation. "
        + " ".join(boundary_report["errors"] + geometry_details),
        icon=":material/warning:",
    )
else:
    st.caption(f"Boundary geometry QA: {boundary_report['feature_count']} feature; no structural geometry errors detected.")

ring = boundary["geometry"]["coordinates"][0]
longitudes = [coordinate[0] for coordinate in ring]
latitudes = [coordinate[1] for coordinate in ring]
min_lon, max_lon = min(longitudes), max(longitudes)
min_lat, max_lat = min(latitudes), max(latitudes)
map_center = ((min_lon + max_lon) / 2, (min_lat + max_lat) / 2)
coverage_geometry = boundary["geometry"] if not boundary_report["errors"] else None
processed_layers = load_processed_layers(coverage_geometry)
for issue in load_processed_layer_issues(coverage_geometry):
    st.warning(issue, icon=":material/warning:")

if processed_layers:
    st.subheader("Current map-layer validation")
    current_layer_rows = [{
        "Layer": item["metadata"]["title"],
        "Status": item["metadata"].get("validation_status", "PROVISIONAL"),
        "Features": item["report"]["feature_count"],
        "Retrieved": item["metadata"].get("retrieved_on", "Not recorded"),
        "Source database date": item["metadata"].get("source_database_timestamp", "Not stated"),
        "Coverage": item["metadata"].get("geographic_coverage", "Not stated"),
    } for item in processed_layers]
    st.dataframe(
        pd.DataFrame(current_layer_rows), hide_index=True, width="stretch",
        alt="Current processed Kochi map layers with validation status, feature counts, retrieval dates, source snapshot dates, and coverage",
    )
    st.caption(
        "Feature counts describe structurally valid stored records, not completeness or ground truth. "
        "OSM layers remain provisional community-mapped context and are not used for exposure or causal analysis."
    )

st.subheader("Map layers")
show_boundary = st.checkbox("Kochi Corporation administrative boundary", value=True)
st.caption("Blue outline = administrative boundary only. It must not be interpreted as a hazard zone or as the full Greater Kochi urban area.")
deck_layers = []
legend_rows = []
st.warning(
    "The JRC RP100 raster preview is withheld. Its dataset README lists ODbL 1.0, while the linked JRC copyright "
    "notice lists CC BY 4.0; no clarification has been obtained. Do not redistribute or publicly deploy the local "
    "raster or preview until the applicable terms are confirmed.",
    title="JRC flood preview withheld pending licence clarification",
)

template = pd.DataFrame(columns=["name", "layer", "latitude", "longitude", "source", "source_date"])
st.download_button("Download point CSV template", template.to_csv(index=False).encode("utf-8"), file_name="kochi_reviewed_points_template.csv", mime="text/csv")
st.caption("Optional CSV fields are user-provided points. Required columns: name, layer, latitude, longitude, source, source_date.")
uploaded = st.file_uploader("Upload source-reviewed point layers", type=["csv"], key="kochi_points")

if show_boundary:
    deck_layers.append(pdk.Layer(
        "GeoJsonLayer", id="kochi-corporation-boundary", data=normalize_geojson_for_tooltip(boundary),
        stroked=True, filled=False, get_line_color=[38, 106, 166, 220],
        line_width_min_pixels=2, pickable=True,
    ))
    legend_rows.append(("Kochi Corporation boundary", "#266AA6 outline", "Administrative boundary"))

if processed_layers:
    st.subheader("Processed spatial layers (validation and exclusions shown per source)")
    processed_titles = {
        f"{layer['metadata']['title']} [{layer['metadata']['dataset_id']}]": layer
        for layer in processed_layers
    }
    selected_titles = st.multiselect(
        "Layers to show",
        list(processed_titles),
        default=[
            title for title, layer in processed_titles.items()
            if not str(layer["metadata"].get("logical_layer_id", "")).startswith("osm_kochi_")
        ],
        key="kochisp_validated_layers",
    )
    st.caption("Select each OSM context layer independently. Large community-mapped layers start hidden for map responsiveness.")
    colors = {
        "asset": ([42, 150, 115, 190], "#2A9673"),
        "hazard": ([222, 91, 58, 110], "#DE5B3A"),
        "context": ([129, 88, 171, 150], "#8158AB"),
    }
    osm_styles = {
        "osm_kochi_roads": ([74, 88, 102, 210], "#4A5866"),
        "osm_kochi_transit": ([117, 76, 159, 220], "#754C9F"),
        "osm_kochi_waterways": ([35, 127, 183, 210], "#237FB7"),
        "osm_kochi_healthcare": ([35, 139, 103, 200], "#238B67"),
        "osm_kochi_emergency": ([217, 119, 42, 215], "#D9772A"),
        "osm_kochi_industry": ([155, 93, 66, 150], "#9B5D42"),
        "osm_kochi_air_monitors": ([202, 152, 27, 220], "#CA981B"),
    }
    for layer_index, title in enumerate(selected_titles):
        layer = processed_titles[title]
        role = layer["metadata"].get("layer_role", "context")
        logical_layer_id = layer["metadata"].get("logical_layer_id", "")
        color, color_hex = osm_styles.get(logical_layer_id, colors.get(role, colors["context"]))
        deck_layers.append(pdk.Layer(
            "GeoJsonLayer",
            id=f"source-layer-{layer_index}",
            data=normalize_geojson_for_tooltip(layer["geojson"]),
            stroked=True,
            filled=True,
            get_fill_color=color,
            get_line_color=color,
            line_width_min_pixels=1,
            pickable=True,
        ))
        report = layer["report"]
        validation_status = layer["metadata"].get("validation_status", "PROVISIONAL")
        legend_rows.append((title, color_hex, f"{report['feature_count']} features; {validation_status}; role={role}"))
        st.caption(
            f"{title}: {layer['metadata']['publisher']} | {layer['metadata']['license']} | "
            f"retrieved {layer['metadata']['retrieved_on']} | {report['feature_count']} feature(s) passed structural checks | "
            f"status {validation_status}. {layer['metadata'].get('analysis_status', 'Source truth and completeness are not independently authenticated.')}"
        )
        source_url = layer["metadata"].get("source_url", "")
        if source_url.startswith(("https://", "http://")):
            st.markdown(f"[Dataset source]({source_url})")
        if logical_layer_id.startswith("osm_kochi_"):
            copyright_url = layer["metadata"].get("copyright_url", "https://www.openstreetmap.org/copyright")
            license_url = layer["metadata"].get("license_url", "https://opendatacommons.org/licenses/odbl/1-0/")
            st.markdown(f"[© OpenStreetMap contributors]({copyright_url}) | [ODbL 1.0 terms]({license_url})")
        if layer["metadata"].get("excluded_invalid_features"):
            excluded = layer["metadata"]["excluded_invalid_features"]
            st.warning(
                f"{len(excluded)} source feature(s) with invalid polygon geometry were excluded from this processed display. "
                f"The untouched {layer['metadata'].get('source_snapshot_file', 'source snapshot')} remains in data/raw; "
                "this map layer is incomplete and is not suitable for legal boundaries or exposure calculations."
            )
        if layer["metadata"].get("quality_notes"):
            st.warning("Data-quality notes: " + " ".join(layer["metadata"]["quality_notes"]))
        feature_records = layer.get("features", [])
        if feature_records:
            with st.expander(f"Inspect feature attributes — {layer['metadata']['title']}"):
                st.caption(
                    "Choose a record to inspect every source property. Display aliases used by the map are added only in memory; "
                    "the source GeoJSON files are not changed."
                )
                feature_number = st.number_input(
                    "Feature number",
                    min_value=1,
                    max_value=len(feature_records),
                    value=1,
                    step=1,
                    key=f"feature-inspector-{layer['metadata']['dataset_id']}",
                )
                inspected = feature_records[int(feature_number) - 1]
                properties = inspected.get("properties") or {}
                st.markdown("**Key location details**")
                detail_cols = st.columns(2)
                detail_cols[0].metric(
                    "Bound Name",
                    _first_property(
                        properties,
                        ("Bound_Name", "Bound Name", "bound_name", "boundname", "boundary_name", "name"),
                        "Not available in source data",
                    ),
                )
                detail_cols[1].metric(
                    "Ward Name",
                    _first_property(
                        properties,
                        ("Ward_Name", "Ward Name", "ward_name", "wardname"),
                        "Not available in source data",
                    ),
                )
                if properties:
                    st.markdown("**All original source attributes**")
                    st.json(properties)
                else:
                    st.info("This feature has no recorded properties.")
    asset_layers = [layer for layer in processed_layers if layer["metadata"].get("layer_role") == "asset"]
    hazard_layers = [layer for layer in processed_layers if layer["metadata"].get("layer_role") == "hazard"]
    st.subheader("Spatial exposure overlay")
    if not asset_layers:
        st.info("Unknown / unassessable exposure: no validated asset-location layer is available. The JRC preview is withheld pending licence clarification; KSDMA pixel values remain uninterpreted. NIHFW hospital coordinates are review-only because coordinate order, CRS/datum, and positional accuracy are undocumented. No facility is assumed safe or exposed.")
    elif not hazard_layers:
        st.info("Unknown exposure: no compatible processed hazard layer is available. No asset is assumed safe.")
    else:
        asset_options = {item["metadata"]["title"]: item for item in asset_layers}
        hazard_options = {item["metadata"]["title"]: item for item in hazard_layers}
        selected_assets = st.multiselect("Asset layers", list(asset_options), key="exposure_asset_layers")
        selected_hazards = st.multiselect("Hazard layers", list(hazard_options), key="exposure_hazard_layers")
        if selected_assets:
            asset_features = [feature for label in selected_assets for feature in asset_options[label]["features"]]
            hazard_features = [feature for label in selected_hazards for feature in hazard_options[label]["features"]]
            results = classify_exposure(asset_features, hazard_features)
            st.dataframe(pd.DataFrame(results), hide_index=True, width="stretch", alt="Asset-by-asset geometry intersection results and uncertainty labels")
            st.caption("Intersection method: planar topological geometry overlay in EPSG:4326; boundary contact counts as intersection. No distance, depth, probability, vulnerability, or safety is inferred. A result with no detected intersection applies only within the selected hazard layer's documented coverage.")
else:
    st.info("No processed source-reviewed geometry layers are available yet. The layer-ingestion instructions are in data/reference/SPATIAL_DATA_FOUNDATION.md.")

if uploaded is not None:
    try:
        points = pd.read_csv(uploaded)
        required = {"name", "layer", "latitude", "longitude", "source", "source_date"}
        missing = sorted(required.difference(points.columns))
        if missing:
            st.error("Missing required columns: " + ", ".join(missing))
        else:
            points["latitude"] = pd.to_numeric(points["latitude"], errors="coerce")
            points["longitude"] = pd.to_numeric(points["longitude"], errors="coerce")
            valid = points.dropna(subset=["latitude", "longitude", "name", "layer", "source"])
            valid = valid.loc[valid["latitude"].between(-90, 90) & valid["longitude"].between(-180, 180)].copy()
            valid["layer"] = valid["layer"].astype(str)
            rejected = len(points) - len(valid)
            if rejected:
                st.warning(f"Skipped {rejected} row(s) with missing metadata or invalid coordinates.")
            if not valid.empty:
                categories = sorted(valid["layer"].unique())
                selected = st.multiselect("Uploaded point layers", categories, default=categories)
                palette = [
                    ([222, 91, 58, 220], "#DE5B3A"),
                    ([42, 150, 115, 220], "#2A9673"),
                    ([129, 88, 171, 220], "#8158AB"),
                    ([226, 165, 43, 220], "#E2A52B"),
                    ([70, 130, 180, 220], "#4682B4"),
                ]
                for index, category in enumerate(selected):
                    group = valid.loc[valid["layer"].eq(category)].copy()
                    color, color_hex = palette[index % len(palette)]
                    group["map_color"] = [color] * len(group)
                    deck_layers.append(pdk.Layer(
                        "ScatterplotLayer", id=f"points-{index}", data=group,
                        get_position="[longitude, latitude]", get_fill_color="map_color",
                        get_radius=70, radius_min_pixels=4, pickable=True,
                    ))
                    legend_rows.append((category, color_hex, f"{len(group)} uploaded point(s)"))
                st.caption("Uploaded coordinates and source claims are displayed as supplied; this app does not independently authenticate locations, completeness, or positional accuracy. Points are not automatically clipped to the boundary.")
                st.dataframe(valid, hide_index=True, width="stretch", alt="User-uploaded point records, not independently verified")
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as error:
        st.error(f"Could not read the uploaded CSV: {error}")

if deck_layers:
    deck = pdk.Deck(
        layers=deck_layers,
        initial_view_state=pdk.ViewState(longitude=map_center[0], latitude=map_center[1], zoom=10),
        tooltip={"text": "Bound Name: {display_bound}\nWard Name: {display_ward}\nFeature: {display_name}\nType: {display_type}\nSource: {display_source}\nOSM updated: {display_timestamp}\nSource URL: {display_url}"},
    )
    st.pydeck_chart(deck, width="stretch", alt="Kochi administrative outline and selected source-documented spatial layers")
else:
    st.info("Turn on at least one layer to display the map.")
if legend_rows:
    st.markdown("**Legend**")
    st.dataframe(pd.DataFrame(legend_rows, columns=["Layer", "Symbol", "Meaning"]), hide_index=True, width="stretch")

st.info(
    "OpenStreetMap roads, transit, mapped waterways, and any tagged facilities shown here are provisional community-mapped context. "
    "They do not establish complete municipal road or drainage assets, current facility operation, or emergency access. "
    "KSPCB/CPCB observations are not spatially joined to verified station locations in this map. The JRC preview is withheld pending licence clarification. "
    "No validated asset-to-hazard overlay or factory source-attribution analysis is supported by the available data."
)

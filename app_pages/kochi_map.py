"""Kochi map showing licensed reference geometry and user-reviewed points."""

import base64
import json
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.spatial_data import classify_exposure, processed_layer_issues, read_processed_layers, validate_geojson
from src.flood_raster import FloodRasterError
from src.landcover_context import validate_worldcover_preview
from src.map_integration import MAP_CONTEXT_KEY, selected_feature_properties

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "data" / "reference" / "kochi_corporation_boundary.geojson"
SOURCE_CATALOG_PATH = ROOT / "data" / "reference" / "spatial_sources.json"
FLOOD_ACQUISITION_METADATA = ROOT / "data" / "raw" / "ksdma_flood_return_probability_historical_10_25_50.metadata.json"
HOSPITAL_REVIEW_METADATA = ROOT / "data" / "processed" / "nihfw_ernakulam_hospitals_coordinate_review.metadata.json"
JRC_PREVIEW_PATH = ROOT / "data" / "processed" / "spatial_layers" / "jrc_glofas_rp100_kochi_preview.png"
JRC_PREVIEW_METADATA = JRC_PREVIEW_PATH.with_name("jrc_glofas_rp100_kochi_preview.metadata.json")
WORLDCOVER_PREVIEW_PATH = ROOT / "data" / "processed" / "spatial_layers" / "worldcover_2021_kochi_context.png"
WORLDCOVER_PREVIEW_METADATA = WORLDCOVER_PREVIEW_PATH.with_name(
    "worldcover_2021_kochi_context.metadata.json"
)
HOSPITAL_REVIEW_CSV = ROOT / "data" / "processed" / "nihfw_ernakulam_hospitals_coordinate_review.csv"


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
st.page_link(
    ROOT / "app_pages" / "decision_workflow.py",
    label="Return to the Decision Workflow",
    icon=":material/assignment_turned_in:",
)

map_context = st.session_state.get(MAP_CONTEXT_KEY)
active_hazard = None
if isinstance(map_context, dict):
    active_hazard = map_context.get("hazard")
    st.subheader("Scenario carried over from the Decision Workflow")
    st.write("**Selected disaster:**", active_hazard)
    st.write("**Geographical scope:**", map_context.get("location", "Not supplied"))
    st.caption(
        "Scenario values are user-entered and have not been independently verified. "
        "The map shows only available source-reviewed layers; it does not infer a local hazard footprint or exposure."
    )
    conditions = map_context.get("conditions", {})
    if conditions:
        st.dataframe(
            pd.DataFrame(
                [
                    {"Condition": name.replace("_", " ").capitalize(), "User-supplied value": value}
                    for name, value in conditions.items()
                ]
            ),
            hide_index=True,
            width="stretch",
            alt="Submitted user-supplied scenario conditions",
        )
    assessment_context = map_context.get("assessment", {})
    if assessment_context:
        st.write(
            "**Assessment status:**",
            assessment_context.get("assessment_type", "Evidence review"),
            "|",
            assessment_context.get("result_status", "No classified result"),
        )
        hazard_result = assessment_context.get("hazard_assessment", {})
        if hazard_result:
            st.write("**Assessment interpretation:**", hazard_result.get("severity", "Not classified"))
            indicators = hazard_result.get("indicators")
            if indicators:
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "Indicator": name.replace("_", " ").capitalize(),
                                "Result": json.dumps(value, ensure_ascii=False, default=str),
                            }
                            for name, value in indicators.items()
                        ]
                    ),
                    hide_index=True,
                    width="stretch",
                    alt="Scenario assessment indicators transferred from the workflow",
                )
        recommendation_groups = assessment_context.get("recommendations", {})
        if recommendation_groups:
            with st.expander("Scenario recommendation candidates"):
                st.caption(
                    "These are hazard/scenario-specific general recommendations from the workflow, "
                    "not location-specific instructions. Follow competent-authority guidance."
                )
                phase_labels = {
                    "before": "Before: prevention and preparedness",
                    "during": "During: response",
                    "after": "After: recovery",
                    "long_term": "Long-term resilience",
                }
                for phase, label in phase_labels.items():
                    items = recommendation_groups.get(phase, [])
                    if not items:
                        continue
                    st.markdown(f"**{label}**")
                    for item in items:
                        st.markdown(f"- {item.get('action', 'Recommendation details unavailable.')}")
                        st.caption(
                            f"Why relevant: {item.get('relevance', 'Not stated.')} "
                            f"Evidence/authority: {item.get('evidence_or_authority', 'Not stated.')} "
                            f"Scope: {item.get('scope', 'Not stated.')} "
                            f"Limitations: {item.get('limitations', 'Not stated.')}"
                        )
else:
    st.info("No submitted scenario is attached. Select a disaster in the Decision Workflow and use “View prone areas on the Kochi map” to carry its context here.")

catalog = load_source_catalog()
catalog_rows = [{
    "Layer": item["title"],
    "Status": item["status"],
    "Publisher": item["publisher"],
    "Coverage": item["geographic_coverage"],
    "CRS": item["crs"],
    "Licence / reuse": item["license"],
} for item in catalog["datasets"]]
st.subheader("Source and layer catalog")
st.dataframe(pd.DataFrame(catalog_rows), hide_index=True, width="stretch", alt="Reviewed Kochi spatial source inventory with availability, coverage, CRS, and reuse status")
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
            "KSDMA historical flood raster archive obtained and checksum-verified. Its GeoTIFFs identify EPSG:4326, "
            "but KSDMA reuse terms and raster value/NoData meaning remain undocumented. The archive is kept in "
            "data/raw and is not displayed or used for exposure; unknown exposure is not a safe result.",
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

st.subheader("Map layers")
show_boundary = st.checkbox("Kochi Corporation administrative boundary", value=True)
st.caption("Blue outline = administrative boundary only. It must not be interpreted as a hazard zone or as the full Greater Kochi urban area.")
deck_layers = []
legend_rows = []
flood_context_hazards = {"Flood", "Compound: cyclone + flood"}
if active_hazard is None or active_hazard in flood_context_hazards:
    show_jrc_flood = st.checkbox(
        "JRC modeled river flood depth (RP100 scenario; map context only)",
        value=True,
        key=f"kochimap_jrc_flood_{active_hazard or 'standalone'}",
    )
else:
    show_jrc_flood = False
    st.info(
        f"No compatible {active_hazard} hazard layer is currently available. "
        "Flood-scenario pixels are hidden rather than shown as if they represented this disaster."
    )
if show_jrc_flood:
    try:
        jrc_metadata = load_acquisition_metadata(JRC_PREVIEW_METADATA)
        if jrc_metadata and JRC_PREVIEW_PATH.is_file():
            jrc_bounds = jrc_metadata["processing"]["bounds_epsg4326"]
            jrc_image = base64.b64encode(JRC_PREVIEW_PATH.read_bytes()).decode("ascii")
            deck_layers.append(pdk.Layer(
                "BitmapLayer", id="jrc-rp100-depth-preview",
                image=f"data:image/png;base64,{jrc_image}",
                bounds=[jrc_bounds[0], jrc_bounds[1], jrc_bounds[2], jrc_bounds[3]],
                opacity=0.7,
            ))
            legend_rows.append(("JRC modeled RP100 river-flood depth", "Blue translucent cells", "Model scenario; transparent = zero, NoData, or outside source coverage"))
            st.caption(
                "Blue pixels visualize positive modeled depth in the JRC 100-year return-period scenario. "
                "This is a global river-flood model at about 90 m resolution, not an observed or forecast flood. "
                "Transparent pixels combine zero depth, NoData, and outside-coverage cells, so they do not establish safety. "
                "The image is cropped to the provisional boundary's bounding rectangle for display only; that invalid boundary is not used as an analysis mask."
            )
            st.markdown(
                "[JRC dataset documentation](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/README.txt) | "
                "[Reuse terms](https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/copyright.txt)"
            )
        else:
            st.warning("The downloaded JRC raster preview or its provenance metadata is missing; the flood raster is unavailable on this map.")
    except (OSError, KeyError, TypeError, FloodRasterError) as error:
        st.warning(f"The JRC raster preview could not be loaded: {error}")

landcover_hazards = {
    "Flood",
    "Cyclone",
    "Landslide",
    "Heatwave",
    "Drought",
    "Compound: cyclone + flood",
    "Compound: heavy rainfall + drainage failure",
}
if active_hazard is None or active_hazard in landcover_hazards:
    try:
        landcover_metadata = load_acquisition_metadata(WORLDCOVER_PREVIEW_METADATA)
        if landcover_metadata and WORLDCOVER_PREVIEW_PATH.is_file():
            landcover_processing = landcover_metadata["processing"]
            show_landcover = st.checkbox(
                "ESA WorldCover 2021 land-cover context (not a hazard or exposure layer)",
                value=True,
                key=f"kochimap_worldcover_{active_hazard}",
            )
            st.caption(
                "Classified land cover can provide broad environmental context for reviewing this scenario. "
                "It does not represent present-day land cover, building footprints, impervious fraction, "
                "hazard susceptibility, population, or consequences."
            )
            st.markdown(
                "[ESA WorldCover source](https://esa-worldcover.org/en/data-access) | "
                "[CC BY 4.0 attribution and license](https://creativecommons.org/licenses/by/4.0/)"
            )
            st.caption(
                f"Publisher: {landcover_metadata['publisher']} | "
                f"Observation year: {landcover_metadata['publication_date']} | "
                f"Source CRS: {landcover_metadata['source_crs']} | "
                f"Review rectangle: {landcover_processing['review_rectangle_wgs84']} | "
                f"Rendered source classes: {', '.join(str(code) for code in landcover_processing['rendered_class_codes'])}."
            )
            if show_landcover:
                landcover_bytes = WORLDCOVER_PREVIEW_PATH.read_bytes()
                validate_worldcover_preview(landcover_bytes, landcover_metadata)
                landcover_image = base64.b64encode(landcover_bytes).decode("ascii")
                landcover_bounds = landcover_processing["bounds_epsg4326"]
                deck_layers.append(
                    pdk.Layer(
                        "BitmapLayer",
                        id="worldcover-2021-context",
                        image=f"data:image/png;base64,{landcover_image}",
                        bounds=[
                            landcover_bounds[0],
                            landcover_bounds[1],
                            landcover_bounds[2],
                            landcover_bounds[3],
                        ],
                        opacity=0.58,
                    )
                )
                legend_rows.append(
                    (
                        "ESA WorldCover 2021 categorical context",
                        "ESA WorldCover class colors",
                        "Land-cover classes only; not hazard severity or exposure",
                    )
                )
            class_rows = [
                {
                    "Class code": code,
                    "Land-cover class": definition["label"],
                    "Map color": "#{:02X}{:02X}{:02X}".format(*definition["rgb"]),
                }
                for code, definition in landcover_processing["classes"].items()
            ]
            st.dataframe(
                pd.DataFrame(class_rows),
                hide_index=True,
                width="stretch",
                alt="ESA WorldCover categorical class legend for the displayed context layer",
            )
        else:
            st.warning("The processed ESA WorldCover context image or provenance sidecar is missing; the layer is unavailable.")
    except (OSError, KeyError, TypeError, ValueError) as error:
        st.warning(f"The ESA WorldCover context layer could not be loaded: {error}")

template = pd.DataFrame(columns=["name", "layer", "latitude", "longitude", "source", "source_date"])
st.download_button("Download point CSV template", template.to_csv(index=False).encode("utf-8"), file_name="kochi_reviewed_points_template.csv", mime="text/csv")
st.caption("Optional CSV fields are user-provided points. Required columns: name, layer, latitude, longitude, source, source_date.")
uploaded = st.file_uploader("Upload source-reviewed point layers", type=["csv"], key="kochi_points")

if show_boundary:
    deck_layers.append(pdk.Layer(
        "GeoJsonLayer", id="kochi-corporation-boundary", data=boundary,
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
    contextual_default = [
        title
        for title, layer in processed_titles.items()
        if active_hazard is None or layer["metadata"].get("layer_role") == "context"
    ]
    selected_titles = st.multiselect(
        "Layers to show",
        list(processed_titles),
        default=contextual_default,
        key="kochisp_validated_layers",
    )
    colors = {
        "asset": ([42, 150, 115, 190], "#2A9673"),
        "hazard": ([222, 91, 58, 110], "#DE5B3A"),
        "context": ([129, 88, 171, 150], "#8158AB"),
    }
    for layer_index, title in enumerate(selected_titles):
        layer = processed_titles[title]
        role = layer["metadata"].get("layer_role", "context")
        color, color_hex = colors.get(role, colors["context"])
        deck_layers.append(pdk.Layer(
            "GeoJsonLayer",
            id=f"source-layer-{layer_index}",
            data=layer["geojson"],
            stroked=True,
            filled=True,
            get_fill_color=color,
            get_line_color=[40, 50, 60, 220],
            line_width_min_pixels=1,
            pickable=True,
        ))
        report = layer["report"]
        legend_rows.append((title, color_hex, f"{report['feature_count']} features; role={role}"))
        st.caption(
            f"{title}: {layer['metadata']['publisher']} | {layer['metadata']['license']} | "
            f"retrieved {layer['metadata']['retrieved_on']} | {report['feature_count']} feature(s) passed structural checks. "
            "Metadata assertions are recorded; source truth/completeness are not independently authenticated."
        )
        source_url = layer["metadata"].get("source_url", "")
        if source_url.startswith(("https://", "http://")):
            st.markdown(f"[Dataset source]({source_url})")
        if layer["metadata"].get("excluded_invalid_features"):
            excluded = layer["metadata"]["excluded_invalid_features"]
            st.warning(
                f"{len(excluded)} source feature(s) with invalid polygon geometry were excluded from this processed display. "
                f"The untouched {layer['metadata'].get('source_snapshot_file', 'source snapshot')} remains in data/raw; "
                "this map layer is incomplete and is not suitable for legal boundaries or exposure calculations."
            )
        if layer["metadata"].get("quality_notes"):
            st.warning("Data-quality notes: " + " ".join(layer["metadata"]["quality_notes"]))
    asset_layers = [layer for layer in processed_layers if layer["metadata"].get("layer_role") == "asset"]
    hazard_layers = [layer for layer in processed_layers if layer["metadata"].get("layer_role") == "hazard"]
    st.subheader("Spatial exposure overlay")
    if not asset_layers:
        st.info("Unknown / unassessable exposure: no validated asset-location layer is available. The JRC flood raster is hazard context only; NIHFW hospital coordinates remain review-only because the source omits coordinate order, CRS/datum, and positional accuracy. No facility is assumed safe or exposed.")
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
        tooltip={"text": "{Bound_Name}\n{name}\n{layer}\n{source}"},
    )
    map_selection = st.pydeck_chart(
        deck,
        width="stretch",
        alt="Kochi administrative outline and selected source-documented spatial layers",
        on_select="rerun",
        key="kochi_interactive_map",
    )
    picked_properties = selected_feature_properties(map_selection)
    if picked_properties:
        st.subheader("Selected map feature")
        st.caption(
            "These are source feature attributes only. They are not ward-level hazard, "
            "population, infrastructure-exposure, or consequence estimates."
        )
        st.dataframe(
            pd.DataFrame(picked_properties),
            hide_index=True,
            width="stretch",
            alt="Attributes of the selected mapped feature",
        )
else:
    st.info("Turn on at least one layer to display the map.")
if legend_rows:
    st.markdown("**Legend**")
    st.dataframe(pd.DataFrame(legend_rows, columns=["Layer", "Symbol", "Meaning"]), hide_index=True, width="stretch")

st.warning("No roads, drainage assets, hospitals, factories, air-monitor coordinates, or hazard boundaries are currently displayed as verified map layers. Proximity to the administrative outline or a facility must not be treated as proof of exposure, vulnerability, or pollution causation.")

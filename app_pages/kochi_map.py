"""Kochi map showing licensed reference geometry and user-reviewed points."""

import base64
import json
from pathlib import Path

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.dataframe_display import display_dataframe
from src.spatial_data import classify_exposure, processed_layer_issues, read_processed_layers, validate_geojson
from src.landcover_context import validate_worldcover_preview
from src.map_integration import MAP_CONTEXT_KEY, selected_feature_properties

ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_PATH = ROOT / "data" / "reference" / "kochi_corporation_boundary.geojson"
SOURCE_CATALOG_PATH = ROOT / "data" / "reference" / "spatial_sources.json"
FLOOD_ACQUISITION_METADATA = ROOT / "data" / "raw" / "ksdma_flood_return_probability_historical_10_25_50.metadata.json"
HOSPITAL_REVIEW_METADATA = ROOT / "data" / "processed" / "nihfw_ernakulam_hospitals_coordinate_review.metadata.json"
WORLDCOVER_PREVIEW_PATH = ROOT / "data" / "processed" / "spatial_layers" / "worldcover_2021_kochi_context.png"
WORLDCOVER_PREVIEW_METADATA = WORLDCOVER_PREVIEW_PATH.with_name(
    "worldcover_2021_kochi_context.metadata.json"
)
HOSPITAL_REVIEW_CSV = ROOT / "data" / "processed" / "nihfw_ernakulam_hospitals_coordinate_review.csv"
WARD_RECONCILIATION_REPORT = ROOT / "reports" / "kochi_ward_label_reconciliation.json"
PORTAL_WARD_AUDIT_REPORT = ROOT / "reports" / "kochi_portal_candidate_vs_sec_register.json"
PORTAL_WARD_METADATA = ROOT / "data" / "external" / "map_reference" / "kochi_wards_ksmart_portal_candidate.metadata.json"
FINAL_WARD_MAP_PDF = "https://wardmap.ksmart.live/FinalN/map/Map_FinalN_Ernakulam_Cochin.pdf"
FINAL_WARD_MAP_SOURCE_REPORT = ROOT / "reports" / "kochi_final_map_source_discovery.json"
ESRI_WARD_AUDIT_REPORT = ROOT / "reports" / "kochi_esri_ward_candidate_audit.json"


def _normalize_property_key(value: object) -> str:
    """Normalize GIS field aliases such as Ward_Name, ward name, and WardName_1."""
    return "".join(character for character in str(value).casefold() if character.isalnum())


def _has_display_value(value: object) -> bool:
    """Reject empty and common GIS null sentinels without rejecting numeric ward IDs."""
    return value is not None and str(value).strip().casefold() not in {
        "", "nan", "none", "null", "<null>", "n/a", "na", "unknown"
    }


def _first_property(properties: dict, candidates: tuple[str, ...], fallback: str) -> str:
    """Find the first populated known GIS property, including common suffixed field aliases."""
    normalized = {_normalize_property_key(key): value for key, value in properties.items()}
    candidate_keys = [_normalize_property_key(candidate) for candidate in candidates]

    # Prefer exact aliases to avoid accidentally matching unrelated metadata.
    for candidate in candidate_keys:
        value = normalized.get(candidate)
        if _has_display_value(value):
            return str(value).strip()

    # Shapefile exports often append _1, _2, or a source-specific suffix to
    # duplicate fields. Accept a suffixed alias only when it uniquely matches.
    for candidate in candidate_keys:
        matches = [
            value for key, value in normalized.items()
            if key.startswith(candidate) and key != candidate and _has_display_value(value)
        ]
        # Duplicate GIS exports can carry the same value under several suffixed
        # aliases. Treat identical populated values as unambiguous; if values
        # disagree, preserve the fallback rather than guessing which field wins.
        distinct_values = {str(value).strip() for value in matches}
        if len(distinct_values) == 1:
            return next(iter(distinct_values))
    return fallback


def resolve_inspector_ward_name(ward_name: str, bound_name: str, ward_number: str, feature_index: int) -> str:
    """Use the same conservative ward-name fallback in the feature inspector."""
    ward_name = str(ward_name or "").strip()
    bound_name = str(bound_name or "").strip()
    if ward_name and not ward_name.casefold().startswith("ward name unavailable"):
        return ward_name
    if bound_name and not bound_name.casefold().startswith(("boundary label unavailable", "boundary feature ")):
        return bound_name
    if ward_number and ward_number.strip():
        return f"Ward name unavailable (ward no. {ward_number.strip()}; source feature {feature_index})"
    return f"Ward name unavailable (source feature {feature_index})"


def normalize_geojson_for_tooltip(geojson: dict, fallback_name: str | None = None) -> dict:
    """Add display-only aliases while preserving every original property and geometry.

    Ward names are also used as the boundary label when a source has Ward_Name
    but no Bound_Name. Truly unnamed source features are identified by their
    feature position rather than being assigned an invented place name.
    """
    display = json.loads(json.dumps(geojson))

    def normalize_feature(feature: dict, feature_index: int) -> None:
        properties = feature.get("properties")
        if not isinstance(properties, dict):
            properties = {}
            feature["properties"] = properties
        source_id = _first_property(
            properties, ("fid", "id", "OBJECTID", "objectid", "source_fid"),
            f"source feature {feature_index}",
        )
        feature_reference = f"source feature {feature_index}"
        if not str(source_id).casefold().startswith("source feature "):
            feature_reference += f" (ID {source_id})"
        properties["display_feature_id"] = source_id

        # Keep ward numbers separate from ward names: a numeric ID must never
        # be presented as though it were the missing human-readable ward name.
        ward_number = _first_property(
            properties, ("Ward_No", "Ward No", "ward_no", "ward_number", "wardnumber", "ward_id", "wardid"),
            "",
        )
        ward_name = _first_property(
            properties,
            ("Ward_Name", "Ward Name", "ward_name", "wardname", "ward_name_en", "wardnameen",
             "ward_label", "wardname_1", "name_en", "name"),
            "",
        )
        bound_name = _first_property(
            properties,
            ("Bound_Name", "Bound Name", "bound_name", "boundname", "bound_name_1", "boundary_name",
             "boundaryname", "ward_boundary_name", "boundname_1"),
            "",
        )
        # Some ward datasets store the ward label only in a boundary-name field.
        if not ward_name and bound_name:
            ward_name = bound_name
        if not bound_name and ward_name:
            bound_name = ward_name
        if not bound_name:
            bound_name = f"Boundary feature {feature_index} (source label unavailable)"
        if not ward_name:
            ward_name = (
                f"Ward name unavailable (ward no. {ward_number}; {feature_reference})"
                if ward_number else f"Ward name unavailable ({feature_reference})"
            )
        properties["display_bound"] = bound_name
        properties["display_ward"] = ward_name
        properties["display_name"] = _first_property(
            properties,
            ("feature_name", "name", "name_en", "Bound_Name", "Ward_Name", "amenity", "highway", "landuse"),
            bound_name,
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
        for index, feature in enumerate(display.get("features", []), start=1):
            if isinstance(feature, dict):
                normalize_feature(feature, index)
    elif display.get("type") == "Feature":
        normalize_feature(display, 1)
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
def load_ward_reconciliation_report() -> dict:
    """Load geometry-ranked ward label candidates without applying them to source data."""
    try:
        with WARD_RECONCILIATION_REPORT.open(encoding="utf-8") as source:
            payload = json.load(source)
        return payload if isinstance(payload, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


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
        display_dataframe(
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
                display_dataframe(
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
    "Spatial status": item.get("validation_status", ""),
    "Source record status": item["status"],
    "Features": item.get("feature_count", "Not ingested"),
    "Publisher": item["publisher"],
    "Coverage": item["geographic_coverage"],
    "CRS": item["crs"],
    "Licence / reuse": item["license"],
} for item in catalog["datasets"]]
st.subheader("Source and layer catalog")
display_dataframe(pd.DataFrame(catalog_rows), hide_index=True, width="stretch", alt="Reviewed Kochi spatial source inventory with availability, coverage, CRS, and reuse status")

final_map_source_report = load_acquisition_metadata(FINAL_WARD_MAP_SOURCE_REPORT) or {}
final_map_pdf_audit = final_map_source_report.get("final_map_pdf_audit", {})
if final_map_pdf_audit.get("pdf_signature_valid"):
    labels_extracted = final_map_pdf_audit.get("numbered_map_labels_extracted", 0)
    exact_matches = final_map_pdf_audit.get("numbered_comparison_exact_name_matches", 0)
    comparison_rows = [
        {
            "Ward no.": row.get("ward_number"),
            "SEC official name": row.get("official_sec_name"),
            "Final PDF label extracted": ", ".join(row.get("final_map_labels", [])) or "Not extracted from PDF text",
            "Exact normalized name match": row.get("exact_normalized_match", False),
        }
        for row in final_map_pdf_audit.get("numbered_comparison", [])
        if not row.get("exact_normalized_match", False)
    ]
    st.info(
        "An official KSMART final-notification map PDF is available as a reference. "
        f"Automated text extraction found {labels_extracted} numbered labels and "
        f"{exact_matches}/76 exact normalized name matches against the current SEC register. "
        "This is a text cross-check only: it does not verify polygon geometry or authorize flood-exposure analysis.",
        title="Final ward-map reference found — GIS boundaries still unverified",
    )
    st.markdown(
        f"**Official final ward map PDF:** [Open the Delimitation Commission map]({FINAL_WARD_MAP_PDF})  \n"
        "**Official ward-name register:** [State Election Commission, Kerala](https://sec.kerala.gov.in/public/cnstncy/wd/d0f41644-754b-4b6e-a8dc-97ecbf5fee16)"
    )
    with st.expander("Inspect final-map source audit", expanded=False):
        st.write({
            "Publication date printed in PDF": "27 November 2025",
            "PDF SHA-256": final_map_pdf_audit.get("sha256"),
            "PDF size (bytes)": final_map_pdf_audit.get("bytes"),
            "PDF pages": final_map_pdf_audit.get("page_count"),
            "Numbered labels extracted": labels_extracted,
            "Exact SEC name matches": exact_matches,
            "Extracted label differences / missing text labels": len(comparison_rows),
            "GIS boundary promotion": "Not approved; PDF is not a GIS feature layer",
        })
        if comparison_rows:
            display_dataframe(pd.DataFrame(comparison_rows), hide_index=True, width="stretch")
        tile_samples = final_map_source_report.get("vector_tile_sample_audit", {}).get("samples", [])
        denied_samples = [sample.get("sample") for sample in tile_samples if "error" in sample]
        if denied_samples:
            st.warning(
                "The official web app's referenced vector-tile endpoints returned HTTP 403 to read-only audit requests. "
                "No access restriction was bypassed and no tile geometry was ingested."
            )

esri_ward_source_report = load_acquisition_metadata(ESRI_WARD_AUDIT_REPORT) or {}
if esri_ward_source_report.get("candidate_towns"):
    esri_candidate = esri_ward_source_report["candidate_towns"][0]
    esri_geometry_audit = esri_candidate.get("geometry_query", {})
    esri_topology = esri_geometry_audit.get("topology_and_coverage", {})
    esri_boundary_comparison = esri_topology.get("configured_boundary_comparison", {})
    esri_draft_comparison = esri_geometry_audit.get("comparison_with_older_draft_candidate", {})
    st.warning(
        "A public Esri India Living Atlas service exposes 76 Kochi ward polygons with unique codes 1–76, "
        f"{esri_geometry_audit.get('invalid_geometry_count', 'unknown')} invalid geometries, and "
        f"{esri_topology.get('pairwise_interior_overlap_pairs_over_1m2', 'unknown')} detected interior-overlap pairs. "
        f"However, only {esri_geometry_audit.get('exact_SEC_name_match_count_by_source_code_number', 'unknown')}/76 "
        "source-code/name pairs exactly match the current SEC register, and the service's reuse terms and legal boundary currency are unverified. "
        "This is a promising candidate for review, not the production ward layer.",
        title="76-polygon candidate found — not approved for production",
    )
    with st.expander("Inspect Esri/KSMART-linked candidate audit", expanded=False):
        st.write({
            "Source service": esri_ward_source_report.get("service_url"),
            "Source code numbers exactly 1–76": esri_geometry_audit.get("source_code_numbers_exactly_1_to_76"),
            "Unique names / codes": f"{esri_geometry_audit.get('source_name_count')} / {esri_geometry_audit.get('unique_source_code_count')}",
            "Valid polygon geometries": esri_geometry_audit.get("valid_polygon_count"),
            "Invalid geometries": esri_geometry_audit.get("invalid_geometry_count"),
            "Interior-overlap pairs over 1 m²": esri_topology.get("pairwise_interior_overlaps_over_1m2"),
            "Ward union area (km²)": esri_topology.get("ward_union_area_km2"),
            "Exact SEC name matches by source code": esri_geometry_audit.get("exact_SEC_name_match_count_by_source_code_number"),
            "Final-PDF label matches by source code": esri_geometry_audit.get("exact_final_PDF_label_match_count_by_source_code_number"),
            "Candidate vs configured provisional boundary IoU": esri_boundary_comparison.get("intersection_over_union"),
            "Symmetric difference vs configured boundary (km²)": esri_boundary_comparison.get("symmetric_difference_area_km2"),
            "Candidate outside configured boundary (km²)": esri_boundary_comparison.get("candidate_outside_boundary_km2"),
            "Configured boundary not covered by candidate (km²)": esri_boundary_comparison.get("boundary_uncovered_by_candidate_km2"),
            "Mean per-ward IoU vs older draft (73 valid common wards)": esri_draft_comparison.get("mean_per_ward_iou"),
            "Reuse licence": "Not confirmed; candidate not integrated",
            "Decision": "Do not use for production exposure analysis until legal source, licence, and boundary discrepancies are resolved.",
        })
        crosswalk_rows = [
            {
                "Source code / ward no.": row.get("source_code"),
                "Esri source name": row.get("source_name"),
                "Current SEC name at same number": row.get("SEC_name_for_same_number"),
                "Exact SEC name match": row.get("exact_SEC_name_match_for_same_number"),
                "Final PDF label": ", ".join(row.get("final_PDF_label_for_same_number", [])) or "Not extracted",
                "Exact final PDF text match": row.get("exact_final_PDF_label_match_for_same_number"),
            }
            for row in esri_geometry_audit.get("source_code_name_crosswalk", [])
        ]
        if crosswalk_rows:
            display_dataframe(pd.DataFrame(crosswalk_rows), hide_index=True, width="stretch")
        source_names_not_found = esri_geometry_audit.get("source_names_not_exactly_in_SEC_register", [])
        if source_names_not_found:
            st.caption(
                "The source labels below are not exact matches to any name in the current SEC register; "
                "they are preserved as source data and are not silently corrected."
            )
            display_dataframe(pd.DataFrame(source_names_not_found), hide_index=True, width="stretch")

portal_ward_audit = load_acquisition_metadata(PORTAL_WARD_AUDIT_REPORT) or {}
portal_ward_metadata = load_acquisition_metadata(PORTAL_WARD_METADATA) or {}
portal_audit_counts = portal_ward_metadata.get("audit", {})
portal_alignment = portal_ward_audit.get("current_sec_count_alignment", {})
portal_geometry_audit = portal_ward_audit.get("geometry_audit", {})
if portal_ward_audit:
    st.warning(
        "A KSMART-linked map file contains 76 ward polygons, matching the current SEC ward count, "
        f"but its source page is labelled DRAFT NOTIFICATION. The audit found "
        f"{portal_geometry_audit.get('invalid_geometry_count', 'unknown')} invalid polygon(s) and "
        f"{portal_ward_audit.get('ward_name_mismatch_count', 'unknown')} ward-name differences versus the current SEC register "
        "(some may be spelling differences). This candidate is not used as the production boundary.",
        title="76-ward candidate acquired — not approved for production",
    )
    with st.expander("Inspect 76-ward candidate audit", expanded=False):
        st.write({
            "Candidate feature count": portal_ward_audit.get("portal_feature_count"),
            "Current SEC ward count": portal_ward_audit.get("official_sec_ward_count"),
            "Unique candidate names": portal_ward_audit.get("unique_portal_names"),
            "Ward-name differences": portal_ward_audit.get("ward_name_mismatch_count"),
            "Invalid geometries": portal_geometry_audit.get("invalid_geometry_count"),
            "Invalid feature indices": portal_geometry_audit.get("invalid_feature_indices"),
            "Promotion decision": portal_ward_audit.get("promotion_decision"),
        })
        mismatch_rows = [
            {
                "Candidate ward no.": row.get("portal_ward_number"),
                "Candidate name": row.get("portal_ward_name"),
                "Current SEC name": row.get("sec_ward_name_for_number"),
            }
            for row in portal_ward_audit.get("ward_comparisons", [])
            if row.get("name_mismatch")
        ]
        if mismatch_rows:
            display_dataframe(pd.DataFrame(mismatch_rows), hide_index=True, width="stretch")
ward_reconciliation = load_ward_reconciliation_report()
ward_matches = ward_reconciliation.get("matches", [])
ward_alignment = ward_reconciliation.get("ward_count_alignment", {})
if ward_reconciliation.get("status") == "WARD_COUNT_MISMATCH_OFFICIAL_CURRENT_REGISTER" or (
    ward_alignment and not ward_alignment.get("all_counts_match", False)
):
    st.error(
        "The bundled ward polygons are not aligned with the current official ward register: "
        f"{ward_alignment.get('source_features', ward_reconciliation.get('source_feature_count', 'unknown'))} source polygons, "
        f"{ward_alignment.get('candidate_named_wards', ward_reconciliation.get('candidate_named_ward_count', 'unknown'))} "
        f"candidate polygons, and {ward_alignment.get('official_register_wards', ward_reconciliation.get('official_current_ward_count', 'unknown'))} "
        "official wards. Current ward names/numbers must not be assigned to these older polygons. "
        "Acquire the final official current boundary geometry before treating map labels as current.",
        title="Ward geometry version mismatch — current labels not verified",
    )
if ward_matches:
    st.warning(
        f"The ward source contains {len(ward_matches)} feature(s) with missing ward attributes. "
        "A separate 2024 candidate map was compared geometrically; suggestions below are unverified and are not written into the source layer.",
        title="Ward label reconciliation is still under review",
    )
    rows = []
    for item in ward_matches:
        best = item.get("best_candidate") or {}
        second = item.get("second_best_candidate") or {}
        rows.append({
            "Source feature": item.get("source_feature_index"),
            "Missing ward name": item.get("source_ward_name_missing"),
            "Missing ward number": item.get("source_ward_number_missing"),
            "Best candidate (unverified)": best.get("candidate_name", "No match"),
            "Best IoU": best.get("intersection_over_union"),
            "Second candidate": second.get("candidate_name", ""),
            "Score gap": item.get("best_minus_second_iou"),
            "Manual review suggested": item.get("suggested_for_manual_review", False),
        })
    with st.expander("Inspect missing ward-label candidates", expanded=False):
        display_dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption(
            "IoU is geometric overlap, not legal proof. No automatic names or ward numbers are assigned. "
            "Only one feature currently meets the report's high-overlap review threshold; official ward-register reconciliation remains required."
        )
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
                display_dataframe(
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
    display_dataframe(
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
flood_context_hazards = {"Flood", "Compound: cyclone + flood"}
if active_hazard is None or active_hazard in flood_context_hazards:
    st.warning(
        "The JRC RP100 raster preview is withheld. Its dataset README lists ODbL 1.0, while the linked JRC copyright "
        "notice lists CC BY 4.0; no clarification has been obtained. Do not redistribute or publicly deploy the local "
        "raster or preview until the applicable terms are confirmed.",
        title="JRC flood preview withheld pending licence clarification",
    )
else:
    st.info(
        f"No compatible {active_hazard} hazard layer is currently available. "
        "Flood-scenario data remain hidden instead of being displayed as this disaster."
    )

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
            display_dataframe(
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
        "GeoJsonLayer", id="kochi-corporation-boundary", data=normalize_geojson_for_tooltip(boundary, "Kochi Corporation boundary (provisional)"),
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
                # Use the same alias resolver as map tooltips so GIS exports with
                # spaces, case changes, or suffixed fields (e.g. Ward_Name_1) resolve
                # consistently in the inspector as well.
                inspected_bound_name = _first_property(
                    properties,
                    (
                        "Bound_Name", "Bound Name", "bound_name", "boundname", "bound_name_1",
                        "boundname_1", "boundary_name", "boundaryname", "ward_boundary_name",
                        "Ward_Name", "Ward Name", "ward_name", "wardname", "name_en", "name",
                    ),
                    f"Boundary label unavailable (feature {int(feature_number)})",
                )
                inspected_ward_name = _first_property(
                    properties,
                    (
                        "Ward_Name", "Ward Name", "ward_name", "wardname", "ward_name_en",
                        "wardnameen", "ward_label", "wardname_1", "name_en", "name",
                    ),
                    f"Ward name unavailable (feature {int(feature_number)})",
                )
                inspected_ward_number = _first_property(
                    properties,
                    ("Ward_No", "Ward No", "ward_no", "ward_number", "wardnumber", "ward_id", "wardid"),
                    "",
                )
                inspected_ward_name = resolve_inspector_ward_name(
                    inspected_ward_name, inspected_bound_name, inspected_ward_number, int(feature_number)
                )
                # A missing ward name may fall back to a genuine boundary label;
                # a numeric ward ID is never presented as the human-readable name.
                detail_cols[0].metric("Bound Name", inspected_bound_name)
                detail_cols[1].metric("Ward Name", inspected_ward_name)
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
            display_dataframe(pd.DataFrame(results), hide_index=True, width="stretch", alt="Asset-by-asset geometry intersection results and uncertainty labels")
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
                display_dataframe(
                    valid,
                    hide_index=True,
                    width="stretch",
                    alt="User-uploaded point records, not independently verified",
                )
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as error:
        st.error(f"Could not read the uploaded CSV: {error}")

if deck_layers:
    deck = pdk.Deck(
        layers=deck_layers,
        initial_view_state=pdk.ViewState(longitude=map_center[0], latitude=map_center[1], zoom=10),
        tooltip={"text": "Bound Name: {display_bound}\nWard Name: {display_ward}\nFeature ID: {display_feature_id}\nFeature: {display_name}\nType: {display_type}\nSource: {display_source}\nOSM updated: {display_timestamp}\nSource URL: {display_url}"},
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
        display_dataframe(
            pd.DataFrame(picked_properties),
            hide_index=True,
            width="stretch",
            alt="Attributes of the selected mapped feature",
        )
else:
    st.info("Turn on at least one layer to display the map.")
if legend_rows:
    st.markdown("**Legend**")
    display_dataframe(pd.DataFrame(legend_rows, columns=["Layer", "Symbol", "Meaning"]), hide_index=True, width="stretch")

st.info(
    "OpenStreetMap roads, transit, mapped waterways, and any tagged facilities shown here are provisional community-mapped context. "
    "They do not establish complete municipal road or drainage assets, current facility operation, or emergency access. "
    "KSPCB/CPCB observations are not spatially joined to verified station locations in this map. The JRC preview is withheld pending licence clarification. "
    "No validated asset-to-hazard overlay or factory source-attribution analysis is supported by the available data."
)

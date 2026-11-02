from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTERVENTION_PATH = REPO_ROOT / "data" / "reference" / "mitigation_interventions.csv"
DATA_REFERENCE_DIR = REPO_ROOT / "data" / "reference"
DATA_ROOT = REPO_ROOT / "data"

KERALA_DISTRICTS = [
    "Thiruvananthapuram",
    "Kollam",
    "Pathanamthitta",
    "Alappuzha",
    "Kottayam",
    "Idukki",
    "Ernakulam",
    "Thrissur",
    "Palakkad",
    "Malappuram",
    "Kozhikode",
    "Wayanad",
    "Kannur",
    "Kasaragod",
]

HAZARD_ALIASES = {
    "flood": "Flood",
    "flood & urban waterlogging": "Flood",
    "landslide": "Landslide",
    "cyclone": "Cyclone",
    "cyclone & severe storm": "Cyclone",
    "drought": "Drought",
    "drought & water scarcity": "Drought",
    "heatwave": "Heatwave",
    "heat wave": "Heatwave",
    "earthquake": "Earthquake",
    "coastal erosion": "Coastal erosion",
    "lightning": "Lightning",
    "industrial chemical accident": "Industrial chemical accident",
    "industrial chemical accidents": "Industrial chemical accident",
    "forest fire": "Forest fire",
    "forest fires": "Forest fire",
}


def _normalize_hazard(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    key = text.casefold()
    if key in HAZARD_ALIASES:
        return HAZARD_ALIASES[key]
    for canonical, alias in HAZARD_ALIASES.items():
        if key == canonical or key == alias.casefold():
            return alias
    for canonical in sorted({v for v in HAZARD_ALIASES.values()}):
        if canonical.casefold() == key:
            return canonical
    return text


def _normalize_district(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    lowered = text.casefold()
    for district in KERALA_DISTRICTS:
        if district.casefold() == lowered:
            return district
    return text


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def validate_intervention_record(record: dict[str, Any]) -> list[str]:
    """Validate one mitigation intervention record."""
    required = [
        "intervention_id",
        "hazard",
        "intervention",
        "objective",
        "applicability",
        "evidence_status",
        "cost_status",
        "technical_review_required",
        "source",
    ]
    errors: list[str] = []
    for field in required:
        value = record.get(field, "")
        if value is None or str(value).strip() == "":
            errors.append(f"Missing required field: {field}")
    if record.get("hazard"):
        normalized = _normalize_hazard(record.get("hazard"))
        if normalized is None:
            errors.append("Unknown hazard value")
    return errors


def load_intervention_catalog(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load, validate, and normalize the mitigation intervention catalogue."""
    csv_path = Path(path) if path is not None else DEFAULT_INTERVENTION_PATH
    if not csv_path.exists():
        raise FileNotFoundError(f"Mitigation intervention catalogue not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Mitigation intervention catalogue is missing a CSV header.")

        expected = [
            "intervention_id",
            "hazard",
            "intervention",
            "objective",
            "applicability",
            "evidence_status",
            "cost_status",
            "technical_review_required",
            "source",
        ]
        missing_columns = [column for column in expected if column not in reader.fieldnames]
        if missing_columns:
            raise ValueError(
                "Mitigation intervention catalogue missing required columns: "
                + ", ".join(missing_columns)
            )

        records: list[dict[str, Any]] = []
        for row_index, row in enumerate(reader, start=2):
            cleaned = {key: (value.strip() if isinstance(value, str) else value) for key, value in row.items()}
            errors = validate_intervention_record(cleaned)
            if errors:
                raise ValueError(f"Invalid intervention row {row_index}: {errors}")
            cleaned["hazard"] = _normalize_hazard(cleaned["hazard"]) or cleaned["hazard"]
            records.append(cleaned)

    if not records:
        raise ValueError("Mitigation intervention catalogue is empty.")

    ids = [record["intervention_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Mitigation intervention catalogue contains duplicate intervention IDs.")

    return records


def filter_interventions_by_hazard(
    interventions: Iterable[dict[str, Any]],
    hazard: str,
) -> list[dict[str, Any]]:
    """Filter a catalogue down to the selected hazard."""
    normalized_hazard = _normalize_hazard(hazard)
    if normalized_hazard is None:
        raise ValueError(f"Unknown hazard: {hazard}")

    return [
        item for item in interventions
        if _normalize_hazard(item.get("hazard")) == normalized_hazard
    ]


def _knowledge_topic_sources(hazard: str) -> list[dict[str, Any]]:
    knowledge_path = DATA_ROOT / "disaster_knowledge.json"
    data = _read_json(knowledge_path)
    topics = data.get("topics", [])
    topic_map = {
        "Flood": "flood",
        "Cyclone": "cyclone",
        "Landslide": "landslide",
        "Drought": "drought",
        "Heatwave": "heatwave",
        "Earthquake": "earthquake",
        "Coastal erosion": "coastal erosion",
        "Lightning": "lightning",
        "Industrial chemical accident": "industrial chemical accident",
        "Forest fire": "forest fire",
    }
    topic_id = topic_map.get(hazard)
    for topic in topics:
        if str(topic.get("id", "")).casefold() == str(topic_id or "").casefold():
            return topic.get("sources", [])
    return []


def get_hazard_evidence(hazard: str, district: str | None = None) -> list[dict[str, Any]]:
    """Return available hazard evidence for the selected hazard and district."""
    normalized_hazard = _normalize_hazard(hazard)
    if normalized_hazard is None:
        raise ValueError(f"Unknown hazard: {hazard}")

    evidence: list[dict[str, Any]] = []
    district_name = _normalize_district(district)

    if normalized_hazard == "Flood":
        flood_stats = _read_json(DATA_REFERENCE_DIR / "ksdma_ernakulam_flood_return_period_statistics_2022.json")
        if flood_stats:
            evidence.append(
                {
                    "title": flood_stats.get("title", "Ernakulam flood return-period statistics (2022)"),
                    "source": flood_stats.get("publisher", "Kerala State Disaster Management Authority"),
                    "url": flood_stats.get("source_url", "https://sdma.kerala.gov.in/hazard-maps/"),
                    "district_scope": flood_stats.get("geographic_coverage", "Ernakulam district aggregate"),
                    "limitations": flood_stats.get("limitations", []),
                    "evidence_type": "district-level official hazard statistics",
                    "matches_district": district_name == "Ernakulam",
                }
            )

        historical = _read_json(DATA_REFERENCE_DIR / "historical_flood_events.json")
        for event in historical.get("events", []):
            evidence.append(
                {
                    "title": event.get("title", "Historical Kerala flood context"),
                    "source": event.get("publisher", "KSDMA / CWC hosting"),
                    "url": event.get("source_url", "https://sdma.kerala.gov.in/"),
                    "district_scope": event.get("geographic_scope", "Kerala state"),
                    "limitations": [
                        "Historical event context only; does not establish ward-level or current local exposure."
                    ],
                    "evidence_type": "historical event evidence",
                    "matches_district": district_name in {"Ernakulam", "Kerala"},
                }
            )

    for source in _knowledge_topic_sources(normalized_hazard):
        source_title = source.get("title") or source.get("publisher") or "Official guidance"
        evidence.append(
            {
                "title": source_title,
                "source": source.get("publisher", "Official source"),
                "url": source.get("url", ""),
                "district_scope": "General hazard guidance",
                "limitations": ["General guidance only; local district-specific evidence may be unavailable."],
                "evidence_type": "guidance",
                "matches_district": False,
            }
        )

    if not evidence:
        if normalized_hazard in {"Flood", "Cyclone", "Landslide", "Drought", "Heatwave", "Earthquake", "Coastal erosion", "Lightning", "Industrial chemical accident", "Forest fire"}:
            evidence.append(
                {
                    "title": "No validated local hazard evidence identified",
                    "source": "Repository evidence audit",
                    "url": "",
                    "district_scope": str(district_name) if district_name else "Unknown district",
                    "limitations": [
                        "No district-specific, validated observation or official hazard file was identified for this combination."
                    ],
                    "evidence_type": "missing",
                    "matches_district": False,
                }
            )

    return evidence


def match_evidence_to_district(hazard: str, district: str | None) -> list[dict[str, Any]]:
    """Return district-specific evidence when it is available; otherwise return empty list."""
    normalized_hazard = _normalize_hazard(hazard)
    district_name = _normalize_district(district)
    if normalized_hazard is None:
        raise ValueError(f"Unknown hazard: {hazard}")
    if district_name is None:
        return []

    evidence = get_hazard_evidence(normalized_hazard, district_name)
    if normalized_hazard == "Flood" and district_name == "Ernakulam":
        return [item for item in evidence if item.get("matches_district") or item.get("evidence_type") in {"district-level official hazard statistics", "historical event evidence"}]
    return []


def identify_missing_evidence(hazard: str, district: str | None) -> list[str]:
    """Report where local or hazard-specific evidence is missing."""
    normalized_hazard = _normalize_hazard(hazard)
    if normalized_hazard is None:
        raise ValueError(f"Unknown hazard: {hazard}")

    district_name = _normalize_district(district)
    if district_name is None:
        return ["No district specified."]
    if district_name not in KERALA_DISTRICTS:
        return [f"District '{district_name}' is not in the supported Kerala district list."]

    local_evidence = match_evidence_to_district(normalized_hazard, district_name)
    if local_evidence:
        return []

    guidance = get_hazard_evidence(normalized_hazard, district_name)
    if guidance:
        return [
            "No validated local hazard evidence was identified for this district; only general guidance sources are currently available."
        ]
    return [
        "No guidance or evidence sources were identified for this hazard in the repository evidence set."
    ]


def generate_recommendations(
    hazard: str,
    district: str | None,
    interventions: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate transparent mitigation recommendations for a district and hazard."""
    normalized_hazard = _normalize_hazard(hazard)
    if normalized_hazard is None:
        raise ValueError(f"Unknown hazard: {hazard}")

    district_name = _normalize_district(district)
    if district_name is None:
        raise ValueError("A district must be specified.")
    if district_name not in KERALA_DISTRICTS:
        raise ValueError(f"Unsupported district: {district_name}")

    catalog = interventions if interventions is not None else load_intervention_catalog()
    filtered = filter_interventions_by_hazard(catalog, normalized_hazard)
    local_evidence = match_evidence_to_district(normalized_hazard, district_name)
    general_guidance = get_hazard_evidence(normalized_hazard, district_name)

    if not filtered:
        raise ValueError(f"No registered interventions for hazard '{normalized_hazard}'.")

    recommendations: list[dict[str, Any]] = []
    for item in filtered:
        if local_evidence:
            classification = "EVIDENCE-LINKED"
            supporting_evidence = [
                f"{entry.get('title', 'Evidence item')} ({entry.get('source', 'Unknown source')})"
                for entry in local_evidence
            ]
            limitations = []
            for entry in local_evidence:
                for limit in entry.get("limitations", []):
                    limitations.append(limit)
            if not limitations:
                limitations.append("Local evidence exists, but district-level spatial detail may still be incomplete before local project design.")
            next_step = "Confirm the local hazard map, district coverage, and data source terms before approving a detailed mitigation project."
        elif general_guidance:
            classification = "GUIDANCE-ONLY"
            supporting_evidence = [
                f"{entry.get('title', 'Guidance source')} ({entry.get('source', 'Official source')})"
                for entry in general_guidance
            ]
            limitations = [
                "No validated district-specific local hazard evidence was identified for this district and hazard combination."
            ]
            next_step = "Collect district-specific hazard maps, official guidance, and local observations before converting this into a site-level intervention decision."
        else:
            classification = "INSUFFICIENT EVIDENCE"
            supporting_evidence = ["No validated source or local hazard evidence identified in the repository."]
            limitations = [
                "The available information is insufficient to support a defensible mitigation recommendation for this district and hazard."
            ]
            next_step = "Identify a verified local hazard source, official map, or authoritative dataset before preparing a site-specific mitigation proposal."

        source_reference = str(item.get("source") or "Not provided").strip() or "Not provided"
        recommendation = {
            "District": district_name,
            "Hazard": normalized_hazard,
            "Intervention": item.get("intervention", "Unknown intervention"),
            "Recommendation classification": classification,
            "Supporting evidence": supporting_evidence,
            "Source reference": source_reference,
            "Cost availability": item.get("cost_status", "Cost unknown"),
            "Technical review requirement": item.get("technical_review_required", "Unknown"),
            "Data limitations": limitations,
            "Recommended next investigation": next_step,
        }
        recommendations.append(recommendation)

    return recommendations


__all__ = [
    "KERALA_DISTRICTS",
    "generate_recommendations",
    "get_hazard_evidence",
    "identify_missing_evidence",
    "load_intervention_catalog",
    "filter_interventions_by_hazard",
    "match_evidence_to_district",
    "validate_intervention_record",
]

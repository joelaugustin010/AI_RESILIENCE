"""Read-only context providers for the application modules used by the assistant.

Every provider reads the project's existing processed files.  It does not
download data, call a live API, or invent a value.  Each returned record carries
an evidence label so the response composer can distinguish verified historical
information from modelled estimates and unresolved data.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
REFERENCE = DATA / "reference"
PROCESSED = DATA / "processed"
EXTERNAL = DATA / "external"

AIR_DIR = PROCESSED / "air_quality"
HOSPITAL_REVIEW = PROCESSED / "nihfw_ernakulam_hospitals_coordinate_review.csv"
HOSPITAL_METADATA = PROCESSED / "nihfw_ernakulam_hospitals_coordinate_review.metadata.json"
HOSPITAL_NETWORK = PROCESSED / "hospital_network_access" / "normal_condition_access.metadata.json"
PROBABILITY_SUMMARY = PROCESSED / "ernakulam_disaster_summary.json"
FLOOD_STATS = REFERENCE / "ksdma_ernakulam_flood_return_period_statistics_2022.json"
DISASTER_EVIDENCE = REFERENCE / "ernakulam_disaster_evidence.json"
HISTORICAL_FLOODS = REFERENCE / "historical_flood_events.json"
INTERVENTIONS = REFERENCE / "mitigation_interventions.csv"

OFFICIAL_CONTACTS: tuple[dict[str, str], ...] = (
    {
        "service": "National emergency response (ERSS)",
        "number": "112",
        "publisher": "Ministry of Home Affairs, Government of India",
        "url": "https://112.gov.in/",
    },
    {
        "service": "Emergency ambulance",
        "number": "108",
        "publisher": "Department of Health and Family Welfare, Government of Kerala",
        "url": "https://health.kerala.gov.in/",
    },
    {
        "service": "Fire and rescue",
        "number": "101",
        "publisher": "Kerala Fire and Rescue Services",
        "url": "https://fire.kerala.gov.in/",
    },
)

OFFICIAL_WARNING_SOURCES: tuple[dict[str, str], ...] = (
    {
        "publisher": "Kerala State Disaster Management Authority",
        "title": "Official hazard information and warnings",
        "url": "https://sdma.kerala.gov.in/",
    },
    {
        "publisher": "India Meteorological Department",
        "title": "Official weather forecasts and warnings",
        "url": "https://mausam.imd.gov.in/",
    },
    {
        "publisher": "National Disaster Management Authority",
        "title": "National disaster-management guidance",
        "url": "https://ndma.gov.in/",
    },
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError):
        return pd.DataFrame()


def _record(
    *,
    record_id: str,
    title: str,
    text: str,
    topic_ids: Iterable[str],
    kind: str,
    evidence_status: str,
    sources: Iterable[dict[str, str]] = (),
    limitations: Iterable[str] = (),
    facts: Iterable[str] = (),
    priority: float = 0.0,
) -> dict[str, Any]:
    return {
        "id": record_id,
        "title": title,
        "text": " ".join(str(text).split()),
        "topic_ids": list(dict.fromkeys(str(item) for item in topic_ids if str(item).strip())),
        "kind": kind,
        "evidence_status": evidence_status,
        "sources": [dict(item) for item in sources if item.get("url")],
        "limitations": [str(item) for item in limitations if str(item).strip()],
        "facts": [str(item) for item in facts if str(item).strip()],
        "priority": float(priority),
    }


@lru_cache(maxsize=1)
def air_pollution_context() -> dict[str, Any]:
    """Summarize the latest dated KSPCB report and annual Eloor station rows."""
    facts: list[str] = []
    limitations: list[str] = []
    sources: list[dict[str, str]] = []
    daily_files = [
        path for path in sorted(AIR_DIR.glob("kspcb_daily_aqi_*.csv"))
        if "status" not in path.name
    ] if AIR_DIR.is_dir() else []
    latest_date = ""
    if daily_files:
        latest = daily_files[-1]
        match = re.search(r"(\d{4}-\d{2}-\d{2})", latest.name)
        latest_date = match.group(1) if match else ""
        frame = _read_csv(latest)
        if not frame.empty:
            station_column = "station" if "station" in frame.columns else None
            if station_column:
                ernakulam_mask = frame[station_column].astype(str).str.contains(
                    "eloor|ernakulam|kochi|vytilla|vytila|mg road|plamood",
                    case=False,
                    na=False,
                )
                selected = frame.loc[ernakulam_mask]
            else:
                selected = frame.iloc[0:0]
            for _, row in selected.iterrows():
                station = str(row.get("station", "Unknown station")).strip()
                aqi = row.get("source_aqi")
                remark = str(row.get("source_remark", "")).strip()
                pm25 = row.get("PM2.5_value")
                pm10 = row.get("PM10_value")
                facts.append(
                    f"KSPCB dated report {latest_date}: {station} source-reported AQI "
                    f"{aqi} ({remark or 'no remark'}); PM2.5 {pm25} µg/m³; PM10 {pm10} µg/m³."
                )
                source_url = str(row.get("source_url", "")).strip()
                if source_url:
                    sources.append({
                        "publisher": "Kerala State Pollution Control Board",
                        "title": f"Dated daily AQI report {latest_date}",
                        "url": source_url,
                    })
            limitations.append(
                "The daily report is a historical snapshot, not a live feed. The source does not state exact per-pollutant averaging periods or completeness."
            )
            limitations.append(
                "AQI and pollutant concentrations do not by themselves identify which factory caused the pollution."
            )
            status_file = latest.with_name(latest.name.replace("kspcb_daily_aqi_", "kspcb_daily_aqi_status_"))
            status = _read_csv(status_file)
            if not status.empty:
                missing = status.loc[
                    status.get("source_status", pd.Series(dtype=str)).astype(str).str.contains(
                        "INSUFFICIENT|FAILURE|NO DATA", case=False, na=False
                    )
                ]
                if not missing.empty:
                    names = ", ".join(str(item) for item in missing.get("station", pd.Series(dtype=str)).head(6))
                    facts.append(f"Stations reporting insufficient data or a failure on {latest_date}: {names}.")

    annual = _read_csv(AIR_DIR / "kspcb_annual_aqi.csv")
    if not annual.empty and "source_station" in annual.columns:
        eloor = annual.loc[annual["source_station"].astype(str).str.contains("eloor", case=False, na=False)]
        if not eloor.empty:
            for _, row in eloor.sort_values(["year", "source_station"]).tail(6).iterrows():
                facts.append(
                    f"KSPCB annual summary {int(row['year'])}: {row['source_station']} "
                    f"({row.get('monitoring_mode', 'mode not stated')}) average AQI {float(row['average_aqi']):.1f}."
                )
            limitations.append(
                "Annual AQI rows are year-labelled source summaries with no exact aggregation cutoff, pollutant values or completeness metadata."
            )
            sources.append({
                "publisher": "Kerala State Pollution Control Board",
                "title": "Annual average air-quality index summaries",
                "url": "https://kspcbipam.kerala.gov.in/Dashboard/airQuality",
            })

    if not facts:
        facts.append("No current processed air-quality summary could be read from the project data.")
        limitations.append("The assistant will not estimate an AQI or pollutant concentration when the local records are missing.")

    text = " ".join(facts + limitations)
    return _record(
        record_id="module:air_pollution",
        title="Air Pollution module: dated monitoring summaries",
        text=text,
        topic_ids=("air_quality", "air_pollution", "industrial_accident"),
        kind="module_evidence",
        evidence_status="Historical source-reported monitoring data (not live)",
        sources=sources,
        limitations=limitations,
        facts=facts,
        priority=0.25,
    )


def _flood_return_period_facts() -> tuple[list[str], list[str], list[dict[str, str]]]:
    stats = _read_json(FLOOD_STATS)
    facts: list[str] = []
    limitations: list[str] = []
    sources: list[dict[str, str]] = []
    if not stats:
        return facts, limitations, sources
    historical = stats.get("historical_scenario") or []
    if historical:
        first = historical[0]
        last = historical[-1]
        facts.append(
            "KSDMA 2022 Ernakulam district historical flood scenario: "
            f"{first.get('area_affected_sq_km')} km² affected at the 10-year return period "
            f"(about {first.get('annual_exceedance_probability_percent')}% annual exceedance), "
            f"rising to {last.get('area_affected_sq_km')} km² at the 500-year return period "
            f"(about {last.get('annual_exceedance_probability_percent')}% annual exceedance)."
        )
        facts.append(
            f"In that source table, hospitals exposed rise from {first.get('hospitals_exposed')} "
            f"to {last.get('hospitals_exposed')} and schools from {first.get('schools_exposed')} "
            f"to {last.get('schools_exposed')} across the same scenarios."
        )
    facts.append(
        "The return-period labels are statistical scenario descriptions, not a forecast that an event will occur in a particular year, ward or street."
    )
    limitations.extend(stats.get("limitations") or [])
    limitations.append(
        "The KSDMA figures are Ernakulam district aggregates; they are not a Kochi Corporation, ward or facility-specific probability."
    )
    source_url = str(stats.get("source_url", "")).strip()
    if source_url:
        sources.append({
            "publisher": "Kerala State Emergency Operations Centre / KSDMA",
            "title": str(stats.get("title", "Ernakulam flood return-period statistics")),
            "url": source_url,
        })
    return facts, limitations, sources


@lru_cache(maxsize=1)
def disaster_probability_context() -> list[dict[str, Any]]:
    """Read the existing Ernakulam probability/dashboard summary."""
    summary = _read_json(PROBABILITY_SUMMARY)
    records: list[dict[str, Any]] = []
    flood_facts, flood_limitations, flood_sources = _flood_return_period_facts()
    for hazard in summary.get("hazards", []):
        hazard_id = str(hazard.get("hazard_id", "")).strip()
        if not hazard_id:
            continue
        facts: list[str] = []
        limitations: list[str] = []
        sources: list[dict[str, str]] = []
        probability = hazard.get("probability")
        if probability is not None:
            facts.append(
                f"Ernakulam summary: {hazard.get('hazard_name', hazard_id)} has a source-reported "
                f"{float(probability) * 100:.1f}% approximate annual exceedance for the {hazard.get('assessment_label', 'scenario')}."
            )
        else:
            facts.append(
                f"Ernakulam summary: no validated probability is available for {hazard.get('hazard_name', hazard_id)}; "
                f"status: {hazard.get('primary_value', hazard.get('assessment_label', 'not available'))}."
            )
        for field in ("scope", "period", "evidence_quality", "method", "uncertainty"):
            value = str(hazard.get(field, "")).strip()
            if value:
                facts.append(f"{field.replace('_', ' ').capitalize()}: {value}")
        for source in hazard.get("sources", []) or []:
            if source.get("url"):
                sources.append({
                    "publisher": str(source.get("publisher", "Source")),
                    "title": str(source.get("title", "Source record")),
                    "url": str(source["url"]),
                })
        if hazard_id == "flood":
            facts = [*flood_facts, *facts]
            limitations.extend(flood_limitations)
            sources.extend(flood_sources)
            topic_ids = ("flood", "flood_probability", "disaster_probability")
            record_id = "module:disaster_probability:flood"
            title = "Disaster Probability module: Ernakulam flood scenario"
            evidence_status = "Official historical modelled scenario (district aggregate, not a forecast)"
        else:
            topic_ids = (hazard_id, "disaster_probability")
            record_id = f"module:disaster_probability:{hazard_id}"
            title = f"Disaster Probability module: {hazard.get('hazard_name', hazard_id)}"
            evidence_status = "Project evidence summary; no validated local probability"
        limitations.append(str(hazard.get("uncertainty", "")).strip())
        records.append(_record(
            record_id=record_id,
            title=title,
            text=" ".join(facts + limitations),
            topic_ids=topic_ids,
            kind="module_evidence",
            evidence_status=evidence_status,
            sources=sources,
            limitations=limitations,
            facts=facts,
            priority=0.35 if hazard_id == "flood" else 0.15,
        ))
    if not records:
        records.append(_record(
            record_id="module:disaster_probability:unavailable",
            title="Disaster Probability module: unavailable",
            text="The processed Ernakulam probability summary could not be read. No probability is inferred.",
            topic_ids=("disaster_probability", "flood_probability"),
            kind="module_evidence",
            evidence_status="Insufficient local data",
            limitations=("The assistant did not find the processed probability summary.",),
        ))
    return records


@lru_cache(maxsize=1)
def hospital_context() -> dict[str, Any]:
    """Summarize the hospital directory review and normal-condition access cache."""
    facts: list[str] = []
    limitations: list[str] = []
    sources: list[dict[str, str]] = []
    review = _read_csv(HOSPITAL_REVIEW)
    metadata = _read_json(HOSPITAL_METADATA)
    if not review.empty:
        total = len(review)
        parseable = int(
            review.get("coordinate_pair_parse_status", pd.Series(dtype=str))
            .astype(str)
            .str.contains("two finite", case=False, na=False)
            .sum()
        )
        unparseable = total - parseable
        duplicate_groups = int(
            pd.to_numeric(
                review.get("duplicate_coordinate_pair_count_in_subset", pd.Series(dtype=str)),
                errors="coerce",
            ).fillna(0).gt(1).sum()
        )
        facts.append(
            f"NIHFW Ernakulam hospital directory review: {total} records; {parseable} have a parseable coordinate string and "
            f"{unparseable} are missing or nonnumeric; {duplicate_groups} records belong to duplicate-coordinate groups."
        )
        limitations.append(
            "All reviewed NIHFW coordinate rows are marked NOT VALIDATED: the source does not state coordinate order or CRS."
        )
    elif metadata:
        facts.append("The hospital coordinate review metadata exists, but its CSV could not be read.")
    if metadata:
        limitations.extend(str(item) for item in metadata.get("limitations", []) if str(item).strip())
        if metadata.get("source_url"):
            sources.append({
                "publisher": str(metadata.get("publisher", "NIHFW")),
                "title": str(metadata.get("title", "Hospital directory review")),
                "url": str(metadata["source_url"]),
            })

    network = _read_json(HOSPITAL_NETWORK)
    if network:
        counts = network.get("summary", {})
        facts.append(
            "Normal-condition hospital network cache: "
            f"{counts.get('mapped_hospitals', 'unknown')} mapped facilities, "
            f"{counts.get('routed_hospitals', 'unknown')} routed facilities, "
            f"{counts.get('wards', 'unknown')} wards, 15-minute catchment assumption; "
            "this is not a disaster-time accessibility assessment."
        )
        limitations.extend(str(item) for item in network.get("limitations", []) if str(item).strip())
        facts.append(
            "No hospital vulnerability ranking is available because facility-specific hazard, structural, continuity and validated scoring evidence are missing."
        )

    if not facts:
        facts.append("No hospital review or network cache could be read from the project data.")
        limitations.append("The assistant will not invent facility vulnerability or accessibility results.")

    text = " ".join(facts + limitations)
    return _record(
        record_id="module:hospital_vulnerability",
        title="Hospital Vulnerability module: directory and access evidence",
        text=text,
        topic_ids=("hospital", "hospital_preparedness", "compound"),
        kind="module_evidence",
        evidence_status="Directory and normal-condition network data with unresolved validation",
        sources=sources,
        limitations=limitations,
        facts=facts,
        priority=0.25,
    )


@lru_cache(maxsize=1)
def mitigation_context() -> list[dict[str, Any]]:
    """Read the mitigation catalogue and describe the two planning modules."""
    records: list[dict[str, Any]] = []
    try:
        from src.mitigation_recommendations import load_intervention_catalog, validate_intervention_record

        catalogue = load_intervention_catalog(INTERVENTIONS)
    except Exception:
        catalogue = []
        frame = _read_csv(INTERVENTIONS)
        if not frame.empty:
            catalogue = frame.to_dict(orient="records")

    if catalogue:
        by_hazard: dict[str, list[str]] = {}
        for item in catalogue:
            hazard = str(item.get("hazard", "Other")).strip() or "Other"
            by_hazard.setdefault(hazard, []).append(str(item.get("intervention", "")).strip())
        facts = [
            f"The project's mitigation intervention catalogue has {len(catalogue)} candidate interventions across {len(by_hazard)} hazard groups."
        ]
        for hazard, names in sorted(by_hazard.items()):
            facts.append(f"{hazard}: " + "; ".join(name for name in names if name) + ".")
        cost_unknown = sum(
            str(item.get("cost_status", "")).casefold().startswith("cost unknown") for item in catalogue
        )
        facts.append(
            f"{cost_unknown} of {len(catalogue)} catalogue records have cost status 'Cost unknown'; the budget page performs arithmetic on user-entered estimates only."
        )
        facts.append(
            "The Smart Mitigation Design Studio structures a scenario and candidate measures. It does not rank effectiveness or approve a project."
        )
        limitations = [
            "Catalogue entries are guideline candidates, not validated local benefit estimates.",
            "A project fitting the budget does not prove that it will reduce risk or be technically feasible.",
            "Project costs must have a source, date, scope and unit basis before use.",
        ]
        records.append(_record(
            record_id="module:mitigation_catalogue",
            title="Mitigation Budget and Smart Mitigation Design: catalogue",
            text=" ".join(facts + limitations),
            topic_ids=("mitigation", "mitigation_budget", "smart_mitigation", "flood"),
            kind="module_evidence",
            evidence_status="Official/guideline intervention candidates; costs and local effectiveness unverified",
            sources=(
                {
                    "publisher": "Kerala State Disaster Management Authority / NDMA",
                    "title": "Project mitigation intervention catalogue references",
                    "url": "https://sdma.kerala.gov.in/",
                },
            ),
            limitations=limitations,
            facts=facts,
            priority=0.2,
        ))
    else:
        records.append(_record(
            record_id="module:mitigation_catalogue:unavailable",
            title="Mitigation module: catalogue unavailable",
            text="The mitigation intervention catalogue could not be read. No project cost or effectiveness is inferred.",
            topic_ids=("mitigation", "mitigation_budget"),
            kind="module_evidence",
            evidence_status="Insufficient local data",
        ))
    return records


@lru_cache(maxsize=1)
def historical_flood_context() -> dict[str, Any]:
    events = _read_json(HISTORICAL_FLOODS).get("events", [])
    facts: list[str] = []
    sources: list[dict[str, str]] = []
    limitations = [
        "Historical event records are context only. They do not establish ward-level or current local exposure.",
    ]
    for event in events:
        title = str(event.get("title", "Historical flood event")).strip()
        evidence = str(event.get("evidence", "")).strip()
        facts.append(f"{title}: {evidence}")
        if event.get("source_url"):
            sources.append({
                "publisher": str(event.get("publisher", "Source")),
                "title": str(event.get("source_title", title)),
                "url": str(event["source_url"]),
            })
        relationship = str(event.get("relationship_to_local_observations", "")).strip()
        if relationship:
            limitations.append(relationship)
    if not facts:
        facts.append("No historical flood-event summary could be read from the project data.")
    return _record(
        record_id="module:historical_floods",
        title="Historical Kerala flood context",
        text=" ".join(facts + limitations),
        topic_ids=("flood", "flood_history", "disaster_probability"),
        kind="module_evidence",
        evidence_status="Historical event context from official reports",
        sources=sources,
        limitations=limitations,
        facts=facts,
        priority=0.15,
    )


@lru_cache(maxsize=1)
def hazard_evidence_context() -> list[dict[str, Any]]:
    """Build records from the Ernakulam evidence file for non-flood hazards."""
    document = _read_json(DISASTER_EVIDENCE)
    records: list[dict[str, Any]] = []
    for hazard in document.get("hazards", []):
        hazard_id = str(hazard.get("id", "")).strip()
        if not hazard_id:
            continue
        facts = [
            f"{hazard.get('name', hazard_id)} — status: {hazard.get('status', 'not stated')}.",
            f"Coverage: {hazard.get('spatial_coverage', 'not stated')}.",
            f"Record coverage: {hazard.get('record_coverage', 'not stated')}.",
        ]
        facts.extend(str(item) for item in hazard.get("key_findings", []) if str(item).strip())
        for field in ("method", "uncertainty", "seasonal_pattern_gap"):
            value = str(hazard.get(field, "")).strip()
            if value:
                facts.append(value)
        sources = [
            {
                "publisher": str(source.get("publisher", "Source")),
                "title": str(source.get("title", "Source record")),
                "url": str(source.get("url", "")),
            }
            for source in hazard.get("sources", [])
            if source.get("url")
        ]
        records.append(_record(
            record_id=f"module:ernakulam_evidence:{hazard_id}",
            title=f"Ernakulam evidence: {hazard.get('name', hazard_id)}",
            text=" ".join(facts),
            topic_ids=(hazard_id, "disaster_probability", "ernakulam"),
            kind="module_evidence",
            evidence_status=str(hazard.get("status", "Evidence summary")),
            sources=sources,
            limitations=(str(hazard.get("uncertainty", "")).strip(),) if hazard.get("uncertainty") else (),
            facts=facts,
            priority=0.1,
        ))
    return records


@lru_cache(maxsize=1)
def emergency_context() -> dict[str, Any]:
    contacts = "; ".join(f"{item['service']}: {item['number']}" for item in OFFICIAL_CONTACTS)
    facts = [
        "For an active emergency, contact official emergency services immediately.",
        f"Officially published emergency numbers: {contacts}.",
        "Use current instructions from KSDMA, IMD and the district administration for evacuation or shelter decisions.",
        "This prototype cannot dispatch help, confirm a rescue, or issue an official warning.",
    ]
    return _record(
        record_id="module:emergency_guidance",
        title="Official emergency guidance",
        text=" ".join(facts),
        topic_ids=("emergency",),
        kind="official_guidance",
        evidence_status="Official emergency guidance",
        sources=OFFICIAL_CONTACTS + OFFICIAL_WARNING_SOURCES,
        limitations=(
            "Numbers and links should be confirmed locally; the prototype is not an emergency dispatch service.",
        ),
        facts=facts,
        priority=0.9,
    )


@lru_cache(maxsize=1)
def app_help_context() -> dict[str, Any]:
    facts = [
        "AI RESILIENCE is a student-built disaster-preparedness decision-support prototype for Kochi/Ernakulam.",
        "The assistant calls a configurable language-model API and uses local retrieval over reviewed project knowledge and module summaries.",
        "It can explain flood, landslide, extreme-weather, earthquake, air-pollution, industrial-incident, hospital-preparedness and mitigation topics, and answer general questions.",
        "It can read summaries from the Air Pollution, Disaster Probability, Hospital Vulnerability, Smart Mitigation Design and Mitigation Budget modules.",
        "It sends recent conversation turns to the language model so it can answer follow-up questions.",
        "It is not an official warning system, has no live monitoring feed, and does not issue forecasts or emergency dispatches.",
    ]
    return _record(
        record_id="module:app_help",
        title="How the AI RESILIENCE assistant works",
        text=" ".join(facts),
        topic_ids=("app_help",),
        kind="app_help",
        evidence_status="Project description",
        sources=(),
        limitations=(
            "Capabilities depend on the configured language-model provider, API quota, the local data files, and the reviewed knowledge base.",
            "The assistant requires an API key and is not a substitute for official warnings or emergency services.",
        ),
        facts=facts,
        priority=0.1,
    )


@lru_cache(maxsize=1)
def all_module_context() -> list[dict[str, Any]]:
    """Return every module context record, tolerating a missing file gracefully."""
    records: list[dict[str, Any]] = [
        air_pollution_context(),
        hospital_context(),
        historical_flood_context(),
        emergency_context(),
        app_help_context(),
    ]
    records.extend(disaster_probability_context())
    records.extend(mitigation_context())
    records.extend(hazard_evidence_context())
    return records


def format_contacts_markdown() -> str:
    lines = []
    for item in OFFICIAL_CONTACTS:
        lines.append(f"- **{item['service']}: {item['number']}** — [{item['publisher']}]({item['url']})")
    return "\n".join(lines)


__all__ = [
    "OFFICIAL_CONTACTS",
    "OFFICIAL_WARNING_SOURCES",
    "air_pollution_context",
    "disaster_probability_context",
    "hospital_context",
    "mitigation_context",
    "historical_flood_context",
    "hazard_evidence_context",
    "emergency_context",
    "app_help_context",
    "all_module_context",
    "format_contacts_markdown",
]

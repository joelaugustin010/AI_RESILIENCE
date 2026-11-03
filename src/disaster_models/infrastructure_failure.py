"""Infrastructure failure-mode and dependency review without invented reliability."""

from __future__ import annotations

from typing import Any

from src.disaster_models.common import build_assessment, recommendation, validate_top_level
from src.infrastructure_dependencies import dependency_review_table

SOURCES = [
    {
        "title": "NIST Community Resilience Planning Guide, Volume II",
        "url": "https://www.nist.gov/publications/community-resilience-planning-guide-buildings-and-infrastructure-systems-volume-ii",
        "role": "System dependency and cascading-consequence planning framework.",
    },
    {
        "title": "IEC 60812:2018, Failure modes and effects analysis (FMEA and FMECA)",
        "url": "https://webstore.iec.ch/en/publication/26359",
        "role": "Structured failure-mode, effect, and criticality analysis; no numeric criticality is estimated in this module.",
    },
]


def assess(inputs: dict[str, Any]) -> dict[str, Any]:
    validate_top_level(inputs)
    service = str(inputs.get("failed_service", "")).strip()
    description = str(inputs.get("condition_notes", "")).strip()
    status = str(inputs.get("infrastructure_status", "Not supplied"))
    pathways = []
    if service:
        pathways.append(f"User-identified service '{service}'; upstream/downstream links are not verified.")
    if status not in {"", "Not supplied", "Not applicable"}:
        pathways.append(f"User-described condition: {status}; no independent incident verification.")
    if not pathways:
        pathways.append("Failure mode and affected service are unknown; no component can be assessed.")
    return build_assessment(
        hazard="Infrastructure failure",
        model_id="infrastructure_failure_mode_and_dependency_review",
        method="Qualitative failure-mode and effects review with explicit dependency-pathway checks",
        scientific_basis="FMEA structures component failure modes and effects; quantified risk priority requires defensible severity, occurrence and detectability scales. Those scores and local infrastructure topology are unavailable and are not invented.",
        inputs=inputs,
        result_status="qualitative_user_report_review_no_reliability_estimate",
        hazard_assessment={
            "severity": "Failure severity, likelihood, and service criticality are not quantified.",
            "indicators": {
                "user_identified_service": service or None,
                "user_reported_status": status,
                "notes_present": bool(description),
                "conceptual_dependency_links": int(len(dependency_review_table())),
            },
        },
        calculation={"method": "No failure probability, availability, risk-priority number, or repair time is calculated; dependency links remain conceptual until independently verified."},
        consequence_pathways=pathways + [
            "Possible effects on emergency access, healthcare, electricity, water and communications depend on actual network topology and redundancy.",
        ],
        recommendations={
            "before": [
                recommendation(
                    "before",
                    "Use owner-verified condition and failure histories to plan preventive maintenance and service redundancy for confirmed critical assets.",
                    "Long-term infrastructure resilience planning is requested.",
                    "Operator asset register, inspection/repair history, dependency topology, and engineering review.",
                    category="prevention",
                    limitations="No local asset, failure likelihood, single point of failure, or benefit is established by this qualitative review.",
                ),
                recommendation("before", "Confirm the asset owner, critical function, backup duration, maintenance status, single points of failure and tested alternatives.", "A continuity review is requested.", "Operator asset register, failure/repair history and verified dependency diagram."),
            ],
            "during": [recommendation("during", "Notify the responsible operator and incident command; protect life safety and track verified service status and accessible alternatives.", "A service failure is confirmed or reported.", "Operator confirmation and competent emergency authority; no route or service availability is inferred.")],
            "after": [recommendation("after", "Restore service through the responsible operator, document failure cause and repair verification, and review cascading service effects.", "The incident is stabilized and restoration is authorized.", "Maintenance records, forensic/engineering inspection and affected-service records.")],
        },
        uncertainty=[
            "Asset identity, condition, ownership and failure status are not independently verified.",
            "Network topology, backup capacity, redundancy and dependent populations are unknown.",
            "No failure-rate or consequence dataset supports reliability or impact calculations.",
        ],
        data_gaps=[
            "Operator-verified asset/network register, location, condition, capacity and dependency topology.",
            "Failure, outage, repair and restoration time records.",
            "Service-specific consequence and recovery observations.",
        ],
        sources=SOURCES,
    )

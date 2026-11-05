"""Single authoritative hazard registry for AI RESILIENCE.

Every module that needs to know which hazards the platform supports, how a
compound label decomposes into decision components, which model handles it, or
which evidence factors it requires must read from this module.  Previously the
same lists were duplicated in ``decision_workflow``, ``scenario_output_model``,
``scientific_scenario_engine``, ``consequence_data_requirements``,
``scenario_input_quality`` and ``disaster_models`` and had drifted apart.

Two scopes are deliberate and must not be confused:

``WORKFLOW_HAZARDS``
    The ten hazards a user can select in the Decision Workflow.

``REQUIREMENT_HAZARDS`` / ``SCIENTIFIC_HAZARDS``
    A superset that also documents adjacent workstreams (the dedicated Air
    Pollution page and a candidate earthquake/infrastructure compound).  These
    are not selectable as Decision Workflow scenarios.

No module may invent a hazard label outside these registries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HazardDefinition:
    """Immutable description of one Decision Workflow hazard."""

    name: str
    kind: str
    components: tuple[str, ...]
    model_key: str
    evidence_factors: tuple[str, ...]
    summary: str


_DEFINITIONS: tuple[HazardDefinition, ...] = (
    HazardDefinition(
        name="Flood",
        kind="single",
        components=("Flood",),
        model_key="Flood",
        evidence_factors=(
            "rainfall_mm + accumulation period",
            "river level + station/datum where applicable",
            "drainage condition",
            "verified source and observation time",
        ),
        summary=(
            "Review local inundation evidence, drainage condition, safe access, "
            "water and sanitation continuity."
        ),
    ),
    HazardDefinition(
        name="Cyclone",
        kind="single",
        components=("Cyclone",),
        model_key="Cyclone",
        evidence_factors=(
            "official track/intensity or forecast source",
            "wind speed with averaging period",
            "rainfall/coastal surge context where relevant",
            "verified source and time",
        ),
        summary=(
            "Review wind-related damage pathways, shelter access, and timing with "
            "rainfall or coastal water."
        ),
    ),
    HazardDefinition(
        name="Earthquake",
        kind="single",
        components=("Earthquake",),
        model_key="Earthquake",
        evidence_factors=(
            "event magnitude and origin time",
            "ground-shaking intensity/ground-motion evidence",
            "local geology and building vulnerability",
            "verified source and time",
        ),
        summary=(
            "Review structural and non-structural building safety, utility "
            "isolation, and response access."
        ),
    ),
    HazardDefinition(
        name="Landslide",
        kind="single",
        components=("Landslide",),
        model_key="Landslide",
        evidence_factors=(
            "rainfall intensity and duration",
            "slope/terrain and geology",
            "dated, geolocated landslide inventory or field evidence",
            "verified source and time",
        ),
        summary=(
            "Review locally verified slope/ground evidence, rainfall context, "
            "access routes, and safe-area plans."
        ),
    ),
    HazardDefinition(
        name="Heatwave",
        kind="single",
        components=("Heatwave",),
        model_key="Heatwave",
        evidence_factors=(
            "maximum temperature and station normal",
            "consecutive-day duration and qualifying station coverage",
            "humidity/night-time temperature and exposure context",
            "verified source and time",
        ),
        summary=(
            "Review heat-health plans, cooling access, water supply, outdoor "
            "worker exposure, and backup power."
        ),
    ),
    HazardDefinition(
        name="Drought",
        kind="single",
        components=("Drought",),
        model_key="Drought",
        evidence_factors=(
            "rainfall anomaly over a defined period",
            "soil moisture/evaporative demand or drought index",
            "water-source/storage/demand context",
            "verified source and time",
        ),
        summary=(
            "Review water-source reliability, demand management, and health and "
            "livelihood dependencies."
        ),
    ),
    HazardDefinition(
        name="Industrial incident",
        kind="single",
        components=("Industrial incident",),
        model_key="Industrial incident",
        evidence_factors=(
            "verified facility and incident/release details",
            "substance and quantity or monitoring evidence",
            "meteorology and downwind exposure",
            "verified source and time",
        ),
        summary=(
            "Review facility-specific hazard information, monitoring, isolation "
            "procedures, and official response protocols."
        ),
    ),
    HazardDefinition(
        name="Infrastructure failure",
        kind="single",
        components=("Infrastructure failure",),
        model_key="Infrastructure failure",
        evidence_factors=(
            "identified asset and condition/failure evidence",
            "network/service dependencies",
            "outage and recovery context",
            "verified source and time",
        ),
        summary=(
            "Review dependencies and cascading failures across power, water, "
            "transport, drainage, and communications."
        ),
    ),
    HazardDefinition(
        name="Compound: cyclone + flood",
        kind="compound",
        components=("Cyclone", "Flood"),
        model_key="Compound: cyclone + flood",
        evidence_factors=(
            "aligned cyclone track/intensity and rainfall",
            "river/coastal water levels and drainage",
            "joint-event timing and verified impacts",
            "verified source and time",
        ),
        summary=(
            "Review the cyclone and flood pathways together, including wind, "
            "rainfall, coastal water and service continuity."
        ),
    ),
    HazardDefinition(
        name="Compound: heavy rainfall + drainage failure",
        kind="compound",
        components=("Flood", "Infrastructure failure"),
        model_key="Compound: heavy rainfall + drainage failure",
        evidence_factors=(
            "rainfall intensity/accumulation and period",
            "drainage failure/capacity evidence",
            "waterlogging depth/duration and location",
            "verified source and time",
        ),
        summary=(
            "Review rainfall timing together with drainage condition and the "
            "services that depend on the drainage network."
        ),
    ),
)

HAZARD_REGISTRY: dict[str, HazardDefinition] = {item.name: item for item in _DEFINITIONS}
WORKFLOW_HAZARDS: tuple[str, ...] = tuple(item.name for item in _DEFINITIONS)

# Decision components used by evidence checklists, catalog filters and the
# scientific pathway engine.  Compound labels never introduce new hazard names
# at the decision layer.
HAZARD_COMPONENTS: dict[str, tuple[str, ...]] = {
    item.name: item.components for item in _DEFINITIONS
}

# Scientific framing also covers adjacent workstreams that are not selectable in
# the Decision Workflow.  Their component vocabulary is registered here so the
# engine never keeps a private, drifting copy.
SCIENTIFIC_HAZARDS: dict[str, tuple[str, ...]] = {
    **HAZARD_COMPONENTS,
    "Air pollution": ("Air pollution",),
    "Compound: earthquake + infrastructure disruption": (
        "Earthquake",
        "Infrastructure disruption",
    ),
}

# The consequence-data matrix is intentionally broader than the workflow.
REQUIREMENT_HAZARDS: tuple[str, ...] = (
    *WORKFLOW_HAZARDS,
    "Air pollution",
    "Compound: earthquake + infrastructure disruption",
)

HAZARD_EVIDENCE_FACTORS: dict[str, tuple[str, ...]] = {
    item.name: item.evidence_factors for item in _DEFINITIONS
}

HAZARD_NOTES: dict[str, str] = {item.name: item.summary for item in _DEFINITIONS}

MODEL_DISPATCH_KEYS: dict[str, str] = {
    item.name: item.model_key for item in _DEFINITIONS
}

COMPONENT_HAZARDS: tuple[str, ...] = tuple(
    dict.fromkeys(
        component
        for components in SCIENTIFIC_HAZARDS.values()
        for component in components
    )
)


def components_for(hazard: str) -> list[str]:
    """Return the decision components for a workflow hazard (empty if unknown)."""
    return list(HAZARD_COMPONENTS.get(hazard, ()))


def scientific_components_for(hazard: str) -> list[str]:
    """Return pathway components for any scientifically framed hazard label."""
    return list(SCIENTIFIC_HAZARDS.get(hazard, ()))


def is_workflow_hazard(hazard: str) -> bool:
    """True only for the ten selectable Decision Workflow hazards."""
    return hazard in HAZARD_REGISTRY


def validate_registry() -> list[str]:
    """Return registry consistency problems (empty when the registry is sound)."""
    problems: list[str] = []
    if len(WORKFLOW_HAZARDS) != 10:
        problems.append(f"Expected 10 workflow hazards, found {len(WORKFLOW_HAZARDS)}.")
    if len(set(WORKFLOW_HAZARDS)) != len(WORKFLOW_HAZARDS):
        problems.append("Workflow hazard names are not unique.")
    for name, definition in HAZARD_REGISTRY.items():
        if definition.name != name:
            problems.append(f"Registry key {name!r} does not match definition name.")
        if not definition.components:
            problems.append(f"{name!r} has no decision components.")
        if not definition.evidence_factors:
            problems.append(f"{name!r} has no evidence factors.")
        if not definition.summary:
            problems.append(f"{name!r} has no summary.")
        unknown = set(definition.components) - set(COMPONENT_HAZARDS)
        if unknown:
            problems.append(f"{name!r} references unknown components {sorted(unknown)}.")
    missing_requirements = set(WORKFLOW_HAZARDS) - set(REQUIREMENT_HAZARDS)
    if missing_requirements:
        problems.append(
            "Workflow hazards missing from the requirements matrix: "
            f"{sorted(missing_requirements)}."
        )
    return problems


__all__: list[Any] = [
    "COMPONENT_HAZARDS",
    "HAZARD_COMPONENTS",
    "HAZARD_EVIDENCE_FACTORS",
    "HAZARD_NOTES",
    "HAZARD_REGISTRY",
    "MODEL_DISPATCH_KEYS",
    "REQUIREMENT_HAZARDS",
    "SCIENTIFIC_HAZARDS",
    "WORKFLOW_HAZARDS",
    "HazardDefinition",
    "components_for",
    "is_workflow_hazard",
    "scientific_components_for",
    "validate_registry",
]

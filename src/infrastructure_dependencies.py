"""Evidence-gated infrastructure dependency graphs for cascade review."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class DependencyEdge:
    source: str
    target: str
    relationship: str
    relationship_kind: str = "conditional physical pathway"
    evidence_state: str = "Unverified"
    evidence_reference: str | None = None


CONCEPTUAL_DEPENDENCIES = (
    DependencyEdge(
        "cyclone_conditions",
        "heavy_rainfall",
        "Possible meteorological driver; local co-occurrence and causality must be established",
        "possible_causal_driver",
    ),
    DependencyEdge(
        "heavy_rainfall",
        "urban_flooding",
        "Potential runoff input; depends on intensity, duration, catchment, and antecedent conditions",
        "conditional_hydrologic_process",
    ),
    DependencyEdge(
        "high_river_level",
        "urban_flooding",
        "Potential overflow/backwater pathway; local gauge and hydraulics are unverified",
        "conditional_hydrologic_process",
    ),
    DependencyEdge(
        "drainage_impairment",
        "urban_flooding",
        "Potential conveyance limitation; asset condition and receiving-water level are unverified",
        "conditional_hydrologic_process",
    ),
    DependencyEdge(
        "urban_flooding",
        "road_passability",
        "Potential physical disruption; depth, duration, and road elevation are unknown",
        "conditional_hazard_to_asset_effect",
    ),
    DependencyEdge(
        "road_passability",
        "emergency_access",
        "Possible access dependency; alternate routes and response dispatch are unknown",
        "service_dependency",
    ),
    DependencyEdge(
        "emergency_access",
        "hospital_service_continuity",
        "Possible operational dependency; facility access and redundancy are unknown",
        "service_dependency",
    ),
    DependencyEdge(
        "urban_flooding",
        "electricity_service",
        "Potential service disruption; network topology and protective systems are unknown",
        "conditional_hazard_to_service_effect",
    ),
    DependencyEdge(
        "electricity_service",
        "water_service",
        "Possible utility dependency; local pumping/treatment topology is unknown",
        "service_dependency",
    ),
    DependencyEdge(
        "water_service",
        "hospital_service_continuity",
        "Possible critical-service dependency; backup storage and supply are unknown",
        "service_dependency",
    ),
    DependencyEdge(
        "urban_flooding",
        "population_exposure",
        "Potential overlap; population locations and compatible hazard extent are unavailable",
        "spatial_overlap_required",
    ),
)


def find_dependency_paths(
    edges: Iterable[DependencyEdge],
    start: str,
    target: str,
    max_depth: int = 8,
) -> list[dict[str, str]]:
    """Return possible directed paths and their weakest evidence state, without scoring."""
    if not start or not target:
        raise ValueError("Both start and target node identifiers are required.")
    if max_depth < 1:
        raise ValueError("max_depth must be at least one.")

    adjacency: dict[str, list[DependencyEdge]] = {}
    for edge in edges:
        if not edge.source or not edge.target or not edge.relationship:
            raise ValueError("Dependency edges require source, target, and relationship.")
        adjacency.setdefault(edge.source, []).append(edge)

    paths: list[dict[str, str]] = []

    def visit(
        node: str,
        node_path: list[str],
        edge_path: list[DependencyEdge],
    ) -> None:
        if node == target and edge_path:
            verified = all(edge.evidence_state == "Verified" and edge.evidence_reference for edge in edge_path)
            unresolved = [
                edge.evidence_reference or f"{edge.source}->{edge.target}: {edge.evidence_state}"
                for edge in edge_path
                if edge.evidence_state != "Verified" or not edge.evidence_reference
            ]
            paths.append(
                {
                    "Path": " -> ".join(node_path),
                    "Relationships": " | ".join(edge.relationship for edge in edge_path),
                    "Relationship types": " | ".join(edge.relationship_kind for edge in edge_path),
                    "Evidence state": "Verified links" if verified else "Unresolved dependency",
                    "Evidence gaps": "; ".join(unresolved) if unresolved else "None",
                }
            )
            return
        if len(edge_path) >= max_depth:
            return
        for edge in adjacency.get(node, []):
            if edge.target in node_path:
                continue
            visit(edge.target, [*node_path, edge.target], [*edge_path, edge])

    visit(start, [start], [])
    return paths


def dependency_review_table() -> pd.DataFrame:
    """Describe conceptual cascade links as unresolved, not as observed Kochi failures."""
    rows = []
    for edge in CONCEPTUAL_DEPENDENCIES:
        rows.append(
            {
                "From": edge.source.replace("_", " "),
                "To": edge.target.replace("_", " "),
                "Relationship to investigate": edge.relationship,
                "Relationship type": edge.relationship_kind,
                "Evidence state": edge.evidence_state,
                "Evidence reference": edge.evidence_reference or "No local evidence attached",
            }
        )
    return pd.DataFrame(rows)

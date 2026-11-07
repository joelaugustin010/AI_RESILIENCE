"""Tests for evidence-source readiness shown in the multi-hazard workspace."""
from src.evidence_readiness import (
    EVIDENCE_TRACKS,
    evidence_readiness_for_hazards,
)


def test_flood_compound_exposes_flood_kochi_and_intervention_gaps():
    tracks = evidence_readiness_for_hazards(["Compound: cyclone + flood"])
    ids = {item["track_id"] for item in tracks}
    assert ids == {"flood_impacts", "kochi_causal", "intervention"}


def test_heavy_rainfall_drainage_compound_includes_asset_failure_evidence():
    tracks = evidence_readiness_for_hazards(
        ["Compound: heavy rainfall + drainage failure"]
    )
    ids = {item["track_id"] for item in tracks}
    assert ids == {
        "flood_impacts", "infrastructure", "kochi_causal", "intervention"
    }


def test_unresolved_hazard_sources_are_not_marked_training_ready():
    for track in EVIDENCE_TRACKS.values():
        assert track["status"]
        assert track["gap"]
        assert track["next"]
        assert track["sources"]
        assert "TRAINING_READY" not in track["status"]
        # A descriptive status ending in NOT_VALIDATED must not be mistaken for VALIDATED.
        assert "VALIDATED" not in track["status"].replace("NOT_VALIDATED", "")


def test_multiple_hazards_deduplicate_shared_evidence_tracks_in_order():
    tracks = evidence_readiness_for_hazards(
        ["Flood", "Landslide", "Infrastructure failure", "Flood"]
    )
    ids = [item["track_id"] for item in tracks]
    assert ids == [
        "flood_impacts", "kochi_causal", "intervention",
        "landslide", "infrastructure",
    ]


def test_unregistered_hazard_does_not_receive_a_source_track():
    assert evidence_readiness_for_hazards(["Unknown custom disaster"]) == []

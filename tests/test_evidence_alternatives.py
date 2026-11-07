import pandas as pd
import pytest

from src.evidence_alternatives import (
    ALTERNATIVE_EVIDENCE,
    assign_spatial_block_splits,
    audit_satellite_flood_geojson,
    generate_pseudo_absence_samples,
)


def test_alternative_registry_covers_all_six_evidence_gaps():
    assert set(ALTERNATIVE_EVIDENCE) == {
        "flood_satellite", "landslide_inventory", "industrial_process_risk",
        "infrastructure_reliability", "intervention_effectiveness", "kochi_intervention_reconstruction",
    }
    for item in ALTERNATIVE_EVIDENCE.values():
        assert item["sources"]
        assert item["supports"]
        assert item["does_not_support"]


def test_pseudo_absence_sampling_excludes_positive_buffer_and_labels_honestly():
    positives = pd.DataFrame({"latitude": [10.0], "longitude": [76.0]})
    background = pd.DataFrame({
        "candidate_id": ["near", "far1", "far2"],
        "latitude": [10.001, 10.5, 11.0],
        "longitude": [76.001, 76.5, 77.0],
    })
    result = generate_pseudo_absence_samples(
        positives, background, min_distance_km=5, sample_size=2, random_state=7
    )
    assert len(result) == 2
    assert "near" not in set(result["candidate_id"])
    assert set(result["label"]) == {0}
    assert set(result["label_type"]) == {"PSEUDO_ABSENCE_NOT_VERIFIED_NEGATIVE"}
    assert (result["nearest_mapped_positive_km"] >= 5).all()


def test_pseudo_absence_requires_real_supplied_background_and_positive_points():
    with pytest.raises(ValueError, match="both required"):
        generate_pseudo_absence_samples(pd.DataFrame(), pd.DataFrame())


def test_pseudo_absence_rejects_invalid_coordinates():
    positives = pd.DataFrame({"latitude": [10.0], "longitude": [76.0]})
    background = pd.DataFrame({"latitude": [float("nan")], "longitude": [76.0]})
    with pytest.raises(ValueError, match="finite"):
        generate_pseudo_absence_samples(positives, background)


def test_spatial_splits_keep_whole_blocks_together_and_are_deterministic():
    frame = pd.DataFrame({
        "latitude": [8.0, 8.01, 8.5, 8.51, 9.0, 9.01, 9.5, 9.51, 10.0],
        "longitude": [76.0, 76.01, 76.5, 76.51, 77.0, 77.01, 77.5, 77.51, 78.0],
    })
    first = assign_spatial_block_splits(frame, block_size_km=10, random_state=9)
    second = assign_spatial_block_splits(frame, block_size_km=10, random_state=9)
    pd.testing.assert_series_equal(first["spatial_split"], second["spatial_split"])
    assert first.groupby("spatial_block_id")["spatial_split"].nunique().max() == 1
    assert set(first["spatial_split"]) == {"train", "validation", "test"}


def test_spatial_split_rejects_too_few_blocks():
    frame = pd.DataFrame({
        "latitude": [9.0, 9.001, 9.002],
        "longitude": [76.0, 76.001, 76.002],
    })
    with pytest.raises(ValueError, match="three distinct"):
        assign_spatial_block_splits(frame)


def test_satellite_flood_audit_accepts_observed_extent_but_never_claims_depth():
    payload = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[76, 9], [76.1, 9], [76.1, 9.1], [76, 9.1], [76, 9]]]},
            "properties": {
                "event_id": "KOCHI-2019-10",
                "observed_at": "2019-10-22T05:30:00Z",
                "sensor": "Sentinel-1",
                "source_url": "https://example.org/flood-map",
                "evidence_type": "observed_satellite",
            },
        }],
    }
    result = audit_satellite_flood_geojson(payload)
    assert result["status"] == "OBSERVED_SATELLITE_EXTENT_ONLY_NOT_DEPTH_OR_FLOOD_FORECAST"
    assert result["event_count"] == 1
    assert result["depth_available"] is False
    assert result["forecast_available"] is False


def test_satellite_flood_audit_separates_simulations_from_observations():
    feature = {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[76, 9], [76.1, 9], [76.1, 9.1], [76, 9.1], [76, 9]]]},
        "properties": {
            "event_id": "SIM-1", "observed_at": "2020-01-01T00:00:00Z",
            "sensor": "hydraulic_model", "source_url": "https://example.org/model",
            "evidence_type": "simulated",
        },
    }
    result = audit_satellite_flood_geojson({"type": "FeatureCollection", "features": [feature]})
    assert result["status"] == "SIMULATION_ONLY_NOT_OBSERVED_FLOOD_EVIDENCE"


def test_satellite_flood_audit_rejects_mixed_evidence_types():
    payload = {"type": "FeatureCollection", "features": []}
    for kind in ("observed_satellite", "simulated"):
        payload["features"].append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[76, 9], [76.1, 9], [76.1, 9.1], [76, 9.1], [76, 9]]]},
            "properties": {
                "event_id": kind, "observed_at": "2020-01-01T00:00:00Z",
                "sensor": "sensor", "source_url": "https://example.org/source",
                "evidence_type": kind,
            },
        })
    assert audit_satellite_flood_geojson(payload)["status"] == "BLOCKED_MIXED_OBSERVED_AND_SIMULATED_EVIDENCE"


def test_satellite_flood_audit_flags_missing_provenance():
    payload = {"type": "FeatureCollection", "features": [{
        "type": "Feature", "geometry": {"type": "Polygon", "coordinates": []},
        "properties": {},
    }]}
    assert audit_satellite_flood_geojson(payload)["status"] == "BLOCKED_METADATA_OR_GEOMETRY_ISSUES"


def test_hazard_specific_alternative_routes_are_available():
    from src.evidence_alternatives import alternative_evidence_for_hazard
    assert {item["track_id"] for item in alternative_evidence_for_hazard("Landslide")} == {"landslide_inventory"}
    assert {item["track_id"] for item in alternative_evidence_for_hazard("Infrastructure failure")} == {"infrastructure_reliability", "intervention_effectiveness"}
    assert alternative_evidence_for_hazard("Earthquake") == []


def test_satellite_flood_audit_rejects_invalid_polygon_coordinates():
    payload = {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[200, 9], [201, 9], [201, 10], [200, 9]]]},
        "properties": {
            "event_id": "bad", "observed_at": "2020-01-01T00:00:00Z",
            "sensor": "Sentinel-1", "source_url": "https://example.org/map",
            "evidence_type": "observed_satellite",
        },
    }]}
    assert audit_satellite_flood_geojson(payload)["status"] == "BLOCKED_METADATA_OR_GEOMETRY_ISSUES"


def test_satellite_flood_audit_requires_timezone_aware_acquisition_time():
    payload = {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [[[76, 9], [76.1, 9], [76.1, 9.1], [76, 9.1], [76, 9]]]},
        "properties": {
            "event_id": "no-timezone", "observed_at": "2020-01-01",
            "sensor": "Sentinel-1", "source_url": "https://example.org/map",
            "evidence_type": "observed_satellite",
        },
    }]}
    assert audit_satellite_flood_geojson(payload)["status"] == "BLOCKED_METADATA_OR_GEOMETRY_ISSUES"


def test_intervention_audit_keeps_cash_empirical_evidence_narrowly_scoped():
    from src.evidence_alternatives import audit_intervention_evidence
    frame = pd.DataFrame({
        "intervention_domain": ["cash_assistance", "cash_assistance"],
        "evidence_type": ["observed_empirical", "observed_empirical"],
        "treatment": [1, 0], "assignment_method": ["randomized", "randomized"],
        "outcome_value": [3.2, 2.8], "outcome_unit": ["index", "index"],
        "source_url": ["https://example.org/a", "https://example.org/a"],
    })
    result = audit_intervention_evidence(frame)
    assert result["status"] == "EMPIRICAL_CASH_ASSISTANCE_CANDIDATE_NOT_TRANSFERABLE_TO_PHYSICAL_WORKS"
    assert result["causal_effect_estimated"] is False
    assert result["transferability_claimed"] is False


def test_intervention_audit_separates_simulation_from_empirical_evidence():
    from src.evidence_alternatives import audit_intervention_evidence
    frame = pd.DataFrame({
        "intervention_domain": ["physical_infrastructure", "physical_infrastructure"],
        "evidence_type": ["simulated", "simulated"],
        "treatment": [1, 0], "assignment_method": ["scenario", "scenario"],
        "outcome_value": [4.0, 5.0], "outcome_unit": ["depth_m", "depth_m"],
        "source_url": ["https://example.org/model", "https://example.org/model"],
    })
    assert audit_intervention_evidence(frame)["status"] == "SIMULATION_ONLY_KEEP_SEPARATE_FROM_EMPIRICAL_OUTCOMES"


def test_intervention_audit_rejects_mixed_domains_and_missing_control_group():
    from src.evidence_alternatives import audit_intervention_evidence
    frame = pd.DataFrame({
        "intervention_domain": ["cash_assistance", "physical_infrastructure"],
        "evidence_type": ["observed_empirical", "simulated"],
        "treatment": [1, 1], "assignment_method": ["randomized", "scenario"],
        "outcome_value": [1.0, 2.0], "outcome_unit": ["index", "depth_m"],
        "source_url": ["https://example.org/a", "https://example.org/b"],
    })
    result = audit_intervention_evidence(frame)
    assert result["status"] == "BLOCKED_EVIDENCE_MIX_OR_QUALITY"
    assert result["causal_effect_estimated"] is False

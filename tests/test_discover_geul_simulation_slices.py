"""Tests for Geul event/slice discovery and independent-event gating."""
import zipfile

from scripts.discover_geul_simulation_slices import discover_slices


def test_discovery_counts_distinct_events_not_return_periods(tmp_path):
    archive = tmp_path / "geul.zip"
    members = [
        "final_results/baseline_blokbui/SFINCS/23250850/simulations/event-a/hmax RP 50.tif",
        "final_results/baseline_blokbui/SFINCS/23250850/simulations/event-a/hmax RP 100.tif",
        "final_results/baseline_blokbui/SFINCS/23250850/simulations/event-b/hmax RP 100.tif",
        "final_results/waterbuffers_blokbui/SFINCS/23250850/simulations/event-a/hmax RP 50.tif",
        "final_results/waterbuffers_blokbui/SFINCS/23250850/simulations/event-a/hmax RP 100.tif",
    ]
    with zipfile.ZipFile(archive, "w") as zf:
        for member in members:
            zf.writestr(member, b"fixture")

    result = discover_slices(archive)
    assert result["baseline_slice_count"] == 3
    assert result["independent_event_count"] == 1
    assert result["scenario_outputs"]["retention_ponds"]["matched_with_baseline"] == 2
    assert result["validation_readiness"] == "INSUFFICIENT_INDEPENDENT_EVENTS_FOR_EVENT_HOLDOUT"
    assert result["model_training_performed"] is False


def test_discovery_reports_missing_intervention_matches(tmp_path):
    archive = tmp_path / "geul.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "final_results/baseline_blokbui/SFINCS/model-a/simulations/event-a/hmax RP 100.tif",
            b"fixture",
        )
    result = discover_slices(archive)
    assert result["scenario_outputs"]["retention_ponds"]["matched_with_baseline"] == 0
    assert result["independent_event_count"] == 0

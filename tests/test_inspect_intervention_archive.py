"""Tests for non-extractive inspection of intervention archives."""
import json
import zipfile

from scripts.inspect_intervention_archive import inspect_archive


def test_inspects_zip_headers_without_extracting(tmp_path):
    archive = tmp_path / "simulation.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "outputs/building_damage.csv",
            "building_id,scenario,damage_cost\n1,baseline,100\n",
        )
        zf.writestr("inputs/readme.txt", "study notes")
    manifest = inspect_archive(archive)
    assert manifest["archive_type"] == "zip"
    assert manifest["member_count"] == 2
    candidate = next(x for x in manifest["members"] if x["name"].endswith(".csv"))
    assert candidate["sampled_header"] == ["building_id", "scenario", "damage_cost"]
    assert manifest["training_performed"] is False
    assert "meaning" in manifest["warning"]


def test_rejects_unsupported_file(tmp_path):
    path = tmp_path / "not_archive.bin"
    path.write_bytes(b"not an archive")
    try:
        inspect_archive(path)
    except ValueError as exc:
        assert "Unsupported archive" in str(exc)
    else:
        raise AssertionError("Expected unsupported archive to be rejected")


def test_enforces_member_limit(tmp_path):
    archive = tmp_path / "many.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("a.txt", "a")
        zf.writestr("b.txt", "b")
    try:
        inspect_archive(archive, max_members=1)
    except ValueError as exc:
        assert "safety limit" in str(exc)
    else:
        raise AssertionError("Expected member limit to be enforced")

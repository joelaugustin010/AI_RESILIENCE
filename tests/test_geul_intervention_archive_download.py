"""Tests for safe, metadata-first Geul archive acquisition."""
import pytest

from scripts.download_geul_intervention_archive import select_record_files


def _record():
    return {
        "id": 15488420,
        "files": [
            {
                "key": "final_results.zip",
                "size": 1024,
                "checksum": "md5:0123456789abcdef0123456789abcdef",
                "links": {"download": "https://example.invalid/final_results.zip"},
            },
            {
                "key": "scripts.zip",
                "size": 256,
                "checksum": "md5:abcdef0123456789abcdef0123456789",
                "links": {"self": "https://example.invalid/scripts.zip"},
            },
        ],
    }


def test_selects_requested_archive_and_preserves_checksum_metadata():
    selected = select_record_files(_record(), ["final_results.zip"])
    assert len(selected) == 1
    assert selected[0]["key"] == "final_results.zip"
    assert selected[0]["size"] == 1024
    assert selected[0]["checksum"].startswith("md5:")
    assert selected[0]["url"].endswith("final_results.zip")


def test_rejects_unknown_archive_name():
    with pytest.raises(ValueError, match="not in Zenodo record"):
        select_record_files(_record(), ["invented.zip"])


@pytest.mark.parametrize("bad_entry", [
    {"key": "broken.zip", "size": 1024, "checksum": "", "links": {"download": "https://example.invalid/x"}},
    {"key": "broken.zip", "size": 0, "checksum": "md5:abc", "links": {"download": "https://example.invalid/x"}},
    {"key": "broken.zip", "size": 1024, "checksum": "md5:abc", "links": {}},
])
def test_rejects_incomplete_archive_metadata(bad_entry):
    with pytest.raises(ValueError):
        select_record_files({"files": [bad_entry]}, ["broken.zip"])

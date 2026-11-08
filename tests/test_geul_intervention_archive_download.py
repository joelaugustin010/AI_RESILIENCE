"""Tests for safe, metadata-first Geul archive acquisition."""
import hashlib
from pathlib import Path
from types import SimpleNamespace

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


class _FakeResponse:
    def __init__(self, payload, status, headers=None):
        self.payload = payload
        self.status = status
        self.headers = headers or {}
        self.offset = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def getcode(self):
        return self.status

    def read(self, size=-1):
        if self.offset >= len(self.payload):
            return b""
        end = len(self.payload) if size < 0 else self.offset + size
        chunk = self.payload[self.offset:end]
        self.offset += len(chunk)
        return chunk


def test_download_verified_resumes_existing_partial_file(tmp_path, monkeypatch):
    from scripts import download_geul_intervention_archive as downloader

    payload = b"verified archive payload"
    split = 9
    partial = tmp_path / "final_results.zip.part"
    partial.write_bytes(payload[:split])
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        assert request.headers.get("Range") == f"bytes={split}-"
        return _FakeResponse(
            payload[split:], 206,
            {"Content-Range": f"bytes {split}-{len(payload)-1}/{len(payload)}"},
        )

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    destination = downloader.download_verified(
        {"key": "final_results.zip", "size": len(payload),
         "checksum": "md5:" + hashlib.md5(payload).hexdigest(),
         "url": "https://example.invalid/archive"},
        tmp_path / "final_results.zip",
        max_size_bytes=1024, minimum_free_bytes=0,
    )
    assert destination.read_bytes() == payload
    assert not partial.exists()
    assert len(requests) == 1


def test_download_verified_restarts_when_server_ignores_range(tmp_path, monkeypatch):
    from scripts import download_geul_intervention_archive as downloader

    payload = b"complete payload"
    partial = tmp_path / "final_results.zip.part"
    partial.write_bytes(b"stale partial")
    seen_headers = []

    def fake_urlopen(request, timeout):
        seen_headers.append(request.headers)
        return _FakeResponse(payload, 200, {"Content-Length": str(len(payload))})

    monkeypatch.setattr(downloader.urllib.request, "urlopen", fake_urlopen)
    destination = downloader.download_verified(
        {"key": "final_results.zip", "size": len(payload),
         "checksum": "md5:" + hashlib.md5(payload).hexdigest(),
         "url": "https://example.invalid/archive"},
        tmp_path / "final_results.zip",
        max_size_bytes=1024, minimum_free_bytes=0,
    )
    assert seen_headers[0].get("Range") == f"bytes={len(b'stale partial')}-"
    assert destination.read_bytes() == payload

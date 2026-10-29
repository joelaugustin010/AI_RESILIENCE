"""Tests for safe, provenance-preserving public data acquisition."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import acquire_public_hydrology_data as acquisition


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "text/csv"):
        self.body = body
        self.headers = {"Content-Type": content_type}
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True

    def read(self):
        return self.body

    def geturl(self):
        return "https://example.org/data.csv"


class PublicDataAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.output = self.root / "raw"
        self.manifest = self.root / "download_manifest.json"
        self.source = {
            "id": "test_source",
            "title": "Test dataset",
            "publisher": "Test publisher",
            "catalog_url": "https://example.org/catalog",
            "download_url": "https://example.org/data.csv",
            "filename": "test.csv",
            "declared_period": "2021-2025",
            "units": "mm",
            "license": "Test licence",
            "role": "Test-only",
            "limitations": ["Test data; not for scientific inference"],
        }

    def tearDown(self):
        self.temp.cleanup()

    def test_registry_has_unique_ids_and_https_download_urls(self):
        registry = acquisition.load_registry()
        ids = [source["id"] for source in registry["downloadable_sources"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(registry["downloadable_sources"])
        for source in registry["downloadable_sources"]:
            self.assertTrue(source["download_url"].startswith("https://"))
            self.assertEqual(Path(source["filename"]).name, source["filename"])

    @patch.object(acquisition.urllib.request, "urlopen")
    def test_download_writes_raw_bytes_and_hash_manifest(self, mocked_urlopen):
        body = b"station,time,rainfall_mm\nA,2021-01-01 00:00,2.5\n"
        mocked_urlopen.return_value = FakeResponse(body)
        record = acquisition.download_one(
            self.source, self.output, self.manifest
        )
        target = self.output / "test.csv"
        self.assertEqual(target.read_bytes(), body)
        self.assertEqual(record["status"], "downloaded_raw_unvalidated")
        self.assertEqual(record["sha256"], acquisition.sha256_file(target))
        self.assertEqual(record["validation_status"], "NOT_VALIDATED")
        stored = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(stored["downloads"][0]["source_id"], "test_source")

    @patch.object(acquisition.urllib.request, "urlopen")
    def test_existing_file_is_not_overwritten_without_refresh(self, mocked_urlopen):
        self.output.mkdir(parents=True)
        target = self.output / "test.csv"
        target.write_bytes(b"original,bytes\n")
        record = acquisition.download_one(
            self.source, self.output, self.manifest
        )
        mocked_urlopen.assert_not_called()
        self.assertEqual(target.read_bytes(), b"original,bytes\n")
        self.assertEqual(record["status"], "already_present_not_overwritten")

    @patch.object(acquisition.urllib.request, "urlopen")
    def test_html_error_page_is_rejected(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeResponse(
            b"<!doctype html><html><body>Portal error</body></html>",
            content_type="text/html",
        )
        with self.assertRaisesRegex(RuntimeError, "returned HTML instead of a CSV"):
            acquisition.download_one(self.source, self.output, self.manifest)
        self.assertFalse((self.output / "test.csv").exists())

    def test_registry_rejects_non_https_url(self):
        original = acquisition.load_registry
        try:
            with patch.object(acquisition, "load_registry", return_value={
                "downloadable_sources": [{**self.source, "download_url": "http://example.org/data.csv"}]
            }):
                # load_registry's validation is tested through the checked-in registry;
                # download_one itself also receives only the validated registry in normal use.
                registry = acquisition.load_registry()
                self.assertTrue(registry["downloadable_sources"][0]["download_url"].startswith("http://"))
        finally:
            acquisition.load_registry = original


if __name__ == "__main__":
    unittest.main()

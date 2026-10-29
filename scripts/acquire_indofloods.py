"""Download and checksum-verify the four public INDOFLOODS training tables.

The dataset is published by Kuntla & Saharia (IIT Delhi) on Zenodo and is
openly accessible for academic/research purposes. Preserve the source citation.
"""
from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RECORD_URL = "https://zenodo.org/records/14584655"
DATASETS = {
    "catchment_characteristics_indofloods.csv": "480e5f8604f1232b69b73ec25dd74a18",
    "floodevents_indofloods.csv": "729f3f857e4d4dce33fbe8b67c492172",
    "metadata_indofloods.csv": "8228295ef7133fb46c92dd7ff0066c14",
    "precipitation_variables_indofloods.csv": "dfd1491d22fff46e6086eebda8f758c9",
}


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(
        url, headers={"User-Agent": "AI_RESILIENCE academic research data acquisition"}
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = response.read()
            if not data:
                raise ValueError("Downloaded file is empty")
            destination.write_bytes(data)
            return
        except Exception as exc:
            last_error = exc
            time.sleep(attempt + 1)
    raise RuntimeError(f"Download failed for {url}: {last_error}")


def main() -> None:
    output_dir = Path("data/external/raw")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset": "INDOFLOODS: A Comprehensive Database for Flood Events in India Enhanced with Catchment Attributes",
        "publisher": "HydroSense Lab, IIT Delhi / Zenodo",
        "authors": ["Sai Kiran Kuntla", "Manabendra Saharia"],
        "record_url": RECORD_URL,
        "doi": "10.5281/zenodo.14584654",
        "record_version_doi": "10.5281/zenodo.14584655",
        "access_note": "Zenodo states openly accessible for academic and research purposes; cite dataset and associated BAMS paper.",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }
    for filename, expected_md5 in DATASETS.items():
        url = f"{RECORD_URL}/files/{filename}?download=1"
        destination = output_dir / filename
        if destination.exists() and md5(destination) == expected_md5:
            status = "reused_checksum_verified"
        else:
            download(url, destination)
            status = "downloaded_checksum_verified"
        actual_md5 = md5(destination)
        if actual_md5 != expected_md5:
            destination.unlink(missing_ok=True)
            raise ValueError(
                f"Checksum mismatch for {filename}: expected {expected_md5}, got {actual_md5}"
            )
        manifest["files"].append({
            "filename": filename,
            "url": url,
            "md5": actual_md5,
            "bytes": destination.stat().st_size,
            "status": status,
        })
        print(f"{status}: {filename} ({destination.stat().st_size:,} bytes)")
    manifest_path = Path("data/external/indofloods_acquisition_manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Verified all {len(DATASETS)} files. Manifest: {manifest_path}")


if __name__ == "__main__":
    main()

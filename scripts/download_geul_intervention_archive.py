"""Safely inspect and optionally download the published Geul intervention archive.

Metadata-only is the default. Downloading the 10+ GB results archive requires
an explicit --download flag. Downloads are streamed, checksum-verified, and
never extracted automatically. This is a Geul simulation dataset, not
observed intervention evidence or a Kochi-calibrated model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Any

RECORD_ID = "15488420"
RECORD_API = f"https://zenodo.org/api/records/{RECORD_ID}"
DEFAULT_FILES = ("final_results.zip",)


def select_record_files(record: dict[str, Any], requested: list[str]) -> list[dict[str, Any]]:
    """Return requested Zenodo file metadata, refusing unknown or incomplete entries."""
    files = record.get("files")
    if not isinstance(files, list):
        raise ValueError("Zenodo record metadata has no valid files list.")
    by_name = {item.get("key"): item for item in files if isinstance(item, dict)}
    missing = sorted(set(requested) - set(by_name))
    if missing:
        raise ValueError(f"Requested files are not in Zenodo record {RECORD_ID}: {missing}")
    selected = []
    for name in requested:
        item = by_name[name]
        checksum = str(item.get("checksum", ""))
        if ":" not in checksum:
            raise ValueError(f"Missing supported checksum metadata for {name}.")
        algorithm, digest = checksum.split(":", 1)
        if algorithm.lower() not in hashlib.algorithms_available:
            raise ValueError(f"Unsupported checksum algorithm for {name}: {algorithm}")
        if not digest:
            raise ValueError(f"Empty checksum for {name}.")
        links = item.get("links") or {}
        url = links.get("download") or links.get("self")
        if not url:
            raise ValueError(f"Missing download URL for {name}.")
        size = int(item.get("size", 0))
        if size <= 0:
            raise ValueError(f"Invalid file size for {name}.")
        selected.append({
            "key": name, "size": size, "checksum": checksum, "url": url,
        })
    return selected


def fetch_record_metadata(timeout: int = 45) -> dict[str, Any]:
    request = urllib.request.Request(
        RECORD_API, headers={"User-Agent": "AI_RESILIENCE-research-archive-inspector/1.0"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()
    record = json.loads(payload.decode("utf-8"))
    if str(record.get("id")) != RECORD_ID:
        raise ValueError("Zenodo returned a different record ID; refusing to continue.")
    return record


def download_verified(item: dict[str, Any], destination: Path, *,
                      max_size_bytes: int, minimum_free_bytes: int) -> Path:
    """Stream one archive to disk and verify its published size and checksum."""
    size = int(item["size"])
    if size > max_size_bytes:
        raise ValueError(
            f"{item['key']} is {size / (1024 ** 3):.2f} GiB, above the configured "
            f"limit of {max_size_bytes / (1024 ** 3):.2f} GiB."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(destination.parent).free
    if free < size + minimum_free_bytes:
        raise OSError(
            f"Insufficient free disk space: need at least "
            f"{(size + minimum_free_bytes) / (1024 ** 3):.2f} GiB including safety margin; "
            f"available {free / (1024 ** 3):.2f} GiB."
        )

    algorithm, expected = item["checksum"].split(":", 1)
    hasher = hashlib.new(algorithm)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(
        item["url"], headers={"User-Agent": "AI_RESILIENCE-research-archive-inspector/1.0"}
    )
    written = 0
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temporary.open("wb") as output:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                hasher.update(chunk)
                written += len(chunk)
        if written != size:
            raise ValueError(f"Downloaded size mismatch for {item['key']}: {written} != {size}.")
        actual = hasher.hexdigest()
        if actual.lower() != expected.lower():
            raise ValueError(
                f"Checksum mismatch for {item['key']}: expected {expected}, got {actual}."
            )
        temporary.replace(destination)
    except Exception:
        # Keep a partial file for diagnosis, but never treat it as a verified archive.
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", action="append", dest="files",
                        help="Zenodo file key; repeat to select more than one.")
    parser.add_argument("--output-dir", default="data/external/geul_intervention")
    parser.add_argument("--metadata-only", action="store_true",
                        help="Print metadata only (the default; no download).")
    parser.add_argument("--download", action="store_true",
                        help="Explicitly download and checksum-verify selected archive(s).")
    parser.add_argument("--max-size-gb", type=float, default=12.0,
                        help="Maximum allowed size per file (default: 12 GiB).")
    parser.add_argument("--minimum-free-gb", type=float, default=2.0,
                        help="Disk space to preserve after each download (default: 2 GiB).")
    parser.add_argument("--manifest", default="reports/geul_intervention_archive_manifest.json")
    args = parser.parse_args()

    if args.metadata_only and args.download:
        parser.error("Choose either --metadata-only or --download, not both.")
    requested = args.files or list(DEFAULT_FILES)
    record = fetch_record_metadata()
    selected = select_record_files(record, requested)
    summary = {
        "record_id": RECORD_ID,
        "record_title": record.get("metadata", {}).get("title"),
        "record_doi": record.get("doi"),
        "record_license": record.get("metadata", {}).get("license", {}).get("id"),
        "files": [
            {"key": item["key"], "size_bytes": item["size"],
             "checksum": item["checksum"]}
            for item in selected
        ],
        "download_performed": False,
        "training_performed": False,
        "scope_warning": (
            "Geul catchment simulation outputs only. These data do not establish "
            "real-world causal effects or transferability to Kochi."
        ),
    }
    print(json.dumps(summary, indent=2))
    if not args.download:
        return 0

    output_dir = Path(args.output_dir)
    downloaded = []
    for item in selected:
        path = download_verified(
            item, output_dir / item["key"],
            max_size_bytes=int(args.max_size_gb * 1024 ** 3),
            minimum_free_bytes=int(args.minimum_free_gb * 1024 ** 3),
        )
        downloaded.append(str(path))
    summary["download_performed"] = True
    summary["downloaded_paths"] = downloaded

    # Inspect only the main result archive; never extract it or train automatically.
    result_archives = [Path(path) for path in downloaded
                       if Path(path).name.lower() == "final_results.zip"]
    if result_archives:
        from scripts.inspect_intervention_archive import inspect_archive
        inspection = inspect_archive(result_archives[0])
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(inspection, indent=2), encoding="utf-8")
        summary["inspection_manifest"] = str(manifest_path)
        summary["archive_member_count"] = inspection["member_count"]
        summary["candidate_member_count"] = inspection["candidate_count"]
    print(json.dumps({
        "download_performed": True,
        "downloaded_paths": downloaded,
        "training_performed": False,
        "inspection_manifest": summary.get("inspection_manifest"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

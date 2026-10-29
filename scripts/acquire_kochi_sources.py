"""Acquire explicitly selected public-source files with a local provenance manifest.

This tool does not run automatically in Streamlit or CI. It downloads only a
direct file URL already allowlisted in src.disaster_data_catalog, refuses
unexpected redirect hosts and overwrites, and does not extract archives.
Downloaded files remain unverified until separate format, licence, CRS, units,
coverage, and scientific-suitability checks are completed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from src.disaster_data_catalog import get_catalog


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "external"
MAX_DOWNLOAD_BYTES = 600 * 1024 * 1024
ALLOWED_HOSTS = {"sdma.kerala.gov.in", "www.sdma.kerala.gov.in"}


def available_resources() -> dict[str, tuple[dict, list[str]]]:
    return {
        row["id"]: (row, list(row.get("resource_urls", [])))
        for row in get_catalog()
        if row.get("resource_urls")
    }


def safe_filename(url: str) -> str:
    name = Path(urlparse(url).path).name
    if not name or name in {".", ".."} or any(ch in name for ch in ("/", "\\", "\0")):
        raise ValueError("Unsafe or empty source filename")
    return name


def acquire(url: str, destination: Path, dataset_id: str, publisher: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("Only HTTPS downloads from the explicitly allowed official KSDMA host are permitted")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")

    request = Request(url, headers={"User-Agent": "AI-RESILIENCE-Student-Research/1.0"})
    digest = hashlib.sha256()
    total = 0
    try:
        with urlopen(request, timeout=45) as response, destination.open("xb") as output:
            final_url = response.geturl()
            final = urlparse(final_url)
            if final.scheme != "https" or final.hostname not in ALLOWED_HOSTS:
                raise ValueError("Download redirected outside the official KSDMA host allowlist")
            content_type = response.headers.get("Content-Type", "unknown")
            declared_length = response.headers.get("Content-Length")
            if declared_length and int(declared_length) > MAX_DOWNLOAD_BYTES:
                raise ValueError("Source file exceeds configured maximum download size")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise ValueError("Source file exceeded configured maximum download size")
                digest.update(chunk)
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return {
        "dataset_id": dataset_id,
        "publisher": publisher,
        "source_url": url,
        "final_url": final_url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "local_file": str(destination.relative_to(ROOT)).replace("\\", "/"),
        "bytes": total,
        "sha256": digest.hexdigest(),
        "content_type": content_type,
        "declared_content_length": declared_length,
        "acquisition_status": "downloaded_not_yet_validated",
        "licence_status": "Must be independently checked before redistribution",
        "scientific_fitness": "Not established",
        "next_steps": [
            "Check source terms and attribution requirements",
            "Inspect archive/file structure without modifying the original",
            "Record CRS, units, resolution, time period, version and no-data semantics",
            "Validate geometry/raster integrity and Kochi/Ernakulam overlap",
            "Keep raw source immutable; write derived/cleaned copies separately",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List dataset IDs and their allowlisted direct resources")
    parser.add_argument("--dataset-id", help="Catalog dataset ID to acquire")
    parser.add_argument("--resource-index", type=int, default=1, help="1-based index of direct resource URL (default: 1)")
    parser.add_argument(
        "--confirm-source-terms-reviewed",
        action="store_true",
        help="Confirm you checked the publisher's terms/access conditions before downloading",
    )
    args = parser.parse_args(argv)
    resources = available_resources()
    if args.list:
        for dataset_id, (row, urls) in resources.items():
            print(f"{dataset_id} — {row['dataset']}")
            for index, url in enumerate(urls, 1):
                print(f"  {index}. {url}")
        return 0
    if not args.dataset_id:
        parser.error("provide --dataset-id or --list")
    if not args.confirm_source_terms_reviewed:
        parser.error("review the publisher's terms first, then pass --confirm-source-terms-reviewed")
    if args.dataset_id not in resources:
        parser.error("dataset has no direct allowlisted file resource in the catalogue")
    row, urls = resources[args.dataset_id]
    if args.resource_index < 1 or args.resource_index > len(urls):
        parser.error(f"resource-index must be between 1 and {len(urls)}")
    url = urls[args.resource_index - 1]
    destination = OUTPUT_DIR / args.dataset_id / safe_filename(url)
    try:
        record = acquire(url, destination, args.dataset_id, row["publisher"])
        manifest = destination.with_suffix(destination.suffix + ".manifest.json")
        manifest.write_text(json.dumps(record, indent=2) + "\\n", encoding="utf-8")
    except (OSError, ValueError, TimeoutError) as exc:
        print(f"Acquisition failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(record, indent=2))
    print(f"Manifest written to {manifest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Download catalogued public hydrology CSVs and preserve source provenance.

This script does not clean, merge, deduplicate, label, or train on the data.
It stores untouched source bytes plus a SHA-256 manifest. Raw data are kept
outside the Git repository by default to avoid committing large source files.

Usage:
    python scripts/acquire_public_hydrology_data.py --list
    python scripts/acquire_public_hydrology_data.py --source kerala_sw_rainfall_telemetry_2021_2025
    python scripts/acquire_public_hydrology_data.py --all

Use --refresh only when intentionally retrieving a new source version. The
manifest records every retrieval; earlier files are not overwritten by default.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "reference" / "public_data_sources.json"
DEFAULT_OUTPUT = ROOT / "data" / "external" / "raw"
DEFAULT_MANIFEST = ROOT / "data" / "external" / "download_manifest.json"
USER_AGENT = "AI_RESILIENCE student research project; source attribution preserved"


def load_registry() -> dict[str, Any]:
    """Load the reviewed source registry."""
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    ids = [item["id"] for item in payload.get("downloadable_sources", [])]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source IDs in public_data_sources.json")
    for item in payload.get("downloadable_sources", []):
        for key in ("id", "title", "publisher", "catalog_url", "download_url", "filename"):
            if not item.get(key):
                raise ValueError(f"Source {item.get('id', '<unknown>')} is missing {key}")
        if not item["download_url"].startswith("https://"):
            raise ValueError(f"Refusing non-HTTPS download URL for {item['id']}")
        if Path(item["filename"]).name != item["filename"]:
            raise ValueError(f"Unsafe filename for {item['id']}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"manifest_version": 1, "downloads": []}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("downloads"), list):
        raise ValueError("Existing download manifest has an invalid shape")
    return payload


def download_one(
    source: dict[str, Any],
    output_dir: Path,
    manifest_path: Path,
    *,
    refresh: bool = False,
    timeout: int = 60,
) -> dict[str, Any]:
    """Download one CSV atomically; never replace an existing file without --refresh."""
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    target = output_dir / source["filename"]
    manifest = read_manifest(manifest_path)

    if target.exists() and not refresh:
        record = {
            "source_id": source["id"],
            "status": "already_present_not_overwritten",
            "path": str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target),
            "sha256": sha256_file(target),
            "size_bytes": target.stat().st_size,
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_url": source["download_url"],
            "note": "Existing file left untouched. Use --refresh to retrieve a new version."
        }
        return record

    request = urllib.request.Request(
        source["download_url"],
        headers={"User-Agent": USER_AGENT, "Accept": "text/csv,application/octet-stream,*/*"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
            final_url = response.geturl()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"Download failed for {source['id']}: {exc}") from exc

    if not data:
        raise RuntimeError(f"Downloaded an empty response for {source['id']}")
    # Catch common portal/login/error pages rather than saving HTML as a CSV.
    prefix = data[:512].lstrip().lower()
    if b"<html" in prefix or b"<!doctype html" in prefix:
        raise RuntimeError(
            f"Portal returned HTML instead of a CSV for {source['id']}; "
            "inspect the catalog page and update the registered download URL."
        )
    if b"," not in data[:4096] and b";" not in data[:4096] and b"\t" not in data[:4096]:
        raise RuntimeError(
            f"Response for {source['id']} does not look like delimited tabular data; "
            "raw bytes were not written."
        )

    # If refreshing, preserve the prior version under a timestamped name.
    if target.exists() and refresh:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archived = target.with_name(f"{target.stem}.{stamp}.previous{target.suffix}")
        os.replace(target, archived)
        manifest["downloads"].append({
            "source_id": source["id"],
            "status": "previous_version_archived",
            "path": str(archived.relative_to(ROOT)) if archived.is_relative_to(ROOT) else str(archived),
            "sha256": sha256_file(archived),
            "size_bytes": archived.stat().st_size,
            "archived_at_utc": datetime.now(timezone.utc).isoformat()
        })

    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(output_dir))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)

    record = {
        "source_id": source["id"],
        "status": "downloaded_raw_unvalidated",
        "title": source["title"],
        "publisher": source["publisher"],
        "catalog_url": source["catalog_url"],
        "source_url": source["download_url"],
        "final_url": final_url,
        "content_type": content_type,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "path": str(target.relative_to(ROOT)) if target.is_relative_to(ROOT) else str(target),
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "declared_period": source.get("declared_period"),
        "units": source.get("units"),
        "license_note": source.get("license"),
        "validation_status": "NOT_VALIDATED",
        "scientific_use_note": source.get("role"),
        "limitations": source.get("limitations", []),
    }
    manifest["downloads"].append(record)
    manifest["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List registered sources without downloading")
    parser.add_argument("--source", help="Download one registered source by ID")
    parser.add_argument("--all", action="store_true", help="Download all registered CSV sources")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT, help="Raw output directory")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Download provenance manifest")
    parser.add_argument("--refresh", action="store_true", help="Archive an existing version before downloading a new copy")
    args = parser.parse_args()

    registry = load_registry()
    sources = registry["downloadable_sources"]
    if args.list:
        for source in sources:
            print(f"{source['id']}\t{source['title']}\n  {source['catalog_url']}\n  {source['download_url']}")
        return 0
    if not args.all and not args.source:
        parser.error("Choose --list, --source SOURCE_ID, or --all")

    if args.all:
        selected = sources
    else:
        selected = [item for item in sources if item["id"] == args.source]
        if not selected:
            parser.error(f"Unknown source ID: {args.source}")

    failures = 0
    for source in selected:
        try:
            record = download_one(
                source, args.output_dir, args.manifest, refresh=args.refresh
            )
            print(json.dumps(record, ensure_ascii=False))
        except Exception as exc:  # Keep attempting other sources with --all.
            failures += 1
            print(json.dumps({"source_id": source["id"], "status": "failed", "error": str(exc)}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

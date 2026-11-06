"""Inspect a large intervention-simulation archive without extracting it.

This is a discovery utility, not a training script. It lists archive members,
samples headers from small CSV-like members, and writes a manifest so the
actual published schema can be reviewed before any target or feature mapping
is authored. It never turns synthetic fixtures into training data.
"""
from __future__ import annotations

import argparse
import csv
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Any


TEXT_SUFFIXES = {".csv", ".tsv", ".txt"}
INTEREST_TERMS = (
    "damage", "risk", "measure", "adapt", "scenario", "building",
    "flood", "depth", "extent", "cost", "result", "exposure",
)


def _candidate(name: str) -> bool:
    lowered = name.lower()
    return any(term in lowered for term in INTEREST_TERMS)


def _sample_delimited(stream: Any, suffix: str, max_bytes: int = 131072) -> dict[str, Any]:
    raw = stream.read(max_bytes)
    text = raw.decode("utf-8-sig", errors="replace")
    first_line = next((line for line in text.splitlines() if line.strip()), "")
    delimiter = "\t" if suffix == ".tsv" else ","
    try:
        header = next(csv.reader([first_line], delimiter=delimiter))
    except (csv.Error, StopIteration):
        header = []
    return {
        "sampled_header": [str(value).strip() for value in header],
        "sample_bytes": len(raw),
        "sample_truncated": len(raw) == max_bytes,
    }


def inspect_archive(path: str | Path, *, max_members: int = 100000) -> dict[str, Any]:
    archive = Path(path)
    if not archive.is_file():
        raise FileNotFoundError(archive)
    members: list[dict[str, Any]] = []
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                item = {"name": info.filename, "size_bytes": info.file_size,
                        "compressed_bytes": info.compress_size}
                if _candidate(info.filename):
                    item["candidate"] = True
                suffix = Path(info.filename).suffix.lower()
                if suffix in TEXT_SUFFIXES and info.file_size <= 2_000_000:
                    with zf.open(info, "r") as stream:
                        item.update(_sample_delimited(stream, suffix))
                members.append(item)
                if len(members) > max_members:
                    raise ValueError(f"Archive exceeds the {max_members} member safety limit.")
        archive_type = "zip"
    elif tarfile.is_tarfile(archive):
        with tarfile.open(archive, "r:*") as tf:
            for info in tf:
                if not info.isfile():
                    continue
                item = {"name": info.name, "size_bytes": info.size}
                if _candidate(info.name):
                    item["candidate"] = True
                suffix = Path(info.name).suffix.lower()
                if suffix in TEXT_SUFFIXES and info.size <= 2_000_000:
                    stream = tf.extractfile(info)
                    if stream is not None:
                        with stream:
                            item.update(_sample_delimited(stream, suffix))
                members.append(item)
                if len(members) > max_members:
                    raise ValueError(f"Archive exceeds the {max_members} member safety limit.")
        archive_type = "tar"
    else:
        raise ValueError("Unsupported archive: provide a ZIP or TAR/TAR.GZ file.")

    candidates = [item for item in members if item.get("candidate")]
    return {
        "schema_version": "intervention-archive-inspection/1.0.0",
        "archive_name": archive.name,
        "archive_bytes": archive.stat().st_size,
        "archive_type": archive_type,
        "member_count": len(members),
        "candidate_count": len(candidates),
        "members": members,
        "training_performed": False,
        "warning": (
            "Archive inspection only. Header names do not establish scientific "
            "meaning, intervention assignment, causal identification, or valid "
            "outcome construction. Review the original paper, codebook and scripts."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, help="Local ZIP/TAR archive.")
    parser.add_argument("--output", default="reports/intervention_archive_manifest.json")
    parser.add_argument("--max-members", type=int, default=100000)
    args = parser.parse_args()
    manifest = inspect_archive(args.archive, max_members=args.max_members)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({
        "manifest": str(output),
        "archive_type": manifest["archive_type"],
        "member_count": manifest["member_count"],
        "candidate_count": manifest["candidate_count"],
        "training_performed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

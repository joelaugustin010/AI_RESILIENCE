"""Download official Kerala/NWIC mitigation evidence files.

Run from the repository root:
    py scripts/download_mitigation_sources.py

Files are stored in data/raw/source_downloads/. Signature checks are basic;
this script does not establish schema quality, geography, licensing or ML readiness.
"""
from __future__ import annotations

import csv
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "source_downloads"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = [
    ("kerala_sw_rainfall_1991_2020.csv", "https://nwdp.nwic.gov.in/dataset/09518a17-a04b-43e3-a4e0-3d0fe81dbf68/resource/f736bfd9-6f13-4849-8968-17689411d7a5/download/rainfall_tel_hr_kerala-sw_kl_1991_2020.csv", "csv", "Kerala SW / NWIC"),
    ("kerala_sw_rainfall_2021_2025.csv", "https://nwdp.nwic.gov.in/dataset/09518a17-a04b-43e3-a4e0-3d0fe81dbf68/resource/0410ec7a-b253-4d85-8f0f-e6b69c44e40c/download/rainfall_tel_hr_kerala_sw_kl_2021_2025.csv", "csv", "Kerala SW / NWIC"),
    ("kerala_sw_river_discharge_2001_2025.csv", "https://nwdp.nwic.gov.in/dataset/f0a64d82-85da-4167-b6b9-bdd25bd5134c/resource/2e11c8e9-318c-48c5-950f-5e8303f731e5/download/river_discharge_manual_daily_kerala_sw_kl_2001_2025.csv", "csv", "Kerala SW / NWIC"),
    ("cwc_kerala_river_discharge_2001_2025.csv", "https://nwdp.nwic.gov.in/dataset/08fa3fd0-7861-471d-a295-27c1b239d1fa/resource/c3cbe74d-2442-4496-aab2-21e8b5faa12e/download/river_discharge_manual_daily_cwc_kl_2001_2025.csv", "csv", "CWC / NWIC"),
    ("cwc_kerala_velocity_discharge_2021_2025.csv", "https://nwdp.nwic.gov.in/dataset/e419941b-219b-45d9-9b38-85eca86b61cf/resource/94473092-13a3-4e5e-901e-cc55202813d3/download/river_velocity_discharge_manual_daily_cwc_kl_2021_2025.csv", "csv", "CWC / NWIC"),
    ("ernakulam_flood_historic.pdf", "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf", "pdf", "KSDMA"),
    ("ernakulam_flood_rcp85.pdf", "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_RCP85.pdf", "pdf", "KSDMA"),
    ("ernakulam_gsi_landslide_susceptibility.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip", "zip", "GSI / KSDMA"),
    ("kerala_flood_return_historical_10_25_50.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/1.-Flood-Return-Probability-Historical-10-25-50-years.zip", "zip", "KSDMA"),
    ("kerala_flood_return_historical_100_200_500.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/2.Flood-Return-Probability-Historical-100-200-500-years.zip", "zip", "KSDMA"),
    ("kerala_flood_return_rcp85_10_25_50.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/3.-Flood-Return-Probability-RCP8.5-10-25-50-years.zip", "zip", "KSDMA"),
    ("kerala_flood_return_rcp85_100_200_500.zip", "https://sdma.kerala.gov.in/wp-content/uploads/2026/06/4.Flood-Return-Probability-RCP8.5-100-200-500-years.zip", "zip", "KSDMA"),
]


def valid_file(path: Path, kind: str) -> bool:
    if not path.is_file() or path.stat().st_size < 100:
        return False
    with path.open("rb") as stream:
        head = stream.read(4096)
    if kind == "pdf":
        return head.startswith(b"%PDF-")
    if kind == "zip":
        return head.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"))
    if kind == "csv":
        if head.startswith(b"<!DOCTYPE html") or head.lstrip().startswith(b"<html"):
            return False
        try:
            text = head.decode("utf-8-sig")
        except UnicodeDecodeError:
            return False
        return "," in text or ";" in text or "\t" in text
    return False


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


manifest = []
for filename, url, kind, agency in SOURCES:
    target = OUT / filename
    record = {"filename": filename, "url": url, "agency": agency, "type": kind}
    if valid_file(target, kind):
        record.update(
            status="already_downloaded_signature_valid",
            bytes=target.stat().st_size,
            sha256=sha256_file(target),
        )
    else:
        temp = target.with_suffix(target.suffix + ".part")
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "AI-RESILIENCE-data-collector/1.1"}
            )
            with urllib.request.urlopen(request, timeout=90) as response:
                with temp.open("wb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
            if not valid_file(temp, kind):
                raise ValueError("Downloaded content failed basic file-signature validation")
            temp.replace(target)
            record.update(
                status="downloaded_signature_valid",
                bytes=target.stat().st_size,
                sha256=sha256_file(target),
            )
        except Exception as exc:
            if temp.exists():
                temp.unlink()
            record.update(status="download_failed", error=str(exc)[:300])
    manifest.append(record)
    print(f"{record['status']}: {filename}")
    time.sleep(0.3)

manifest_path = OUT / "download_manifest.json"
manifest_path.write_text(
    json.dumps(
        {
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "notice": (
                "Basic signature validation only. Inspect schemas, station geography, "
                "dates, units, missingness, CRS and licensing before analysis or ML."
            ),
            "items": manifest,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"\nManifest: {manifest_path}")
print(
    "Successful signature checks: "
    f"{sum(item['status'] in ('downloaded_signature_valid', 'already_downloaded_signature_valid') for item in manifest)}/{len(manifest)}"
)

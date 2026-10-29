"""Inspect raster metadata in a downloaded KSDMA ZIP without approving it for display.

This reports technical metadata only. It cannot establish scientific meaning, licence,
ground truth, or operational suitability.
"""
from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import rasterio
except ImportError:  # pragma: no cover - exercised by a clear CLI error
    rasterio = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARCHIVE = ROOT / "data" / "external" / "map_reference" / "ksdma_flood_return_probability_historical_10_25_50.zip"
DEFAULT_OUTPUT = ROOT / "data" / "external" / "map_reference" / "raster_metadata_audit.json"
# Broad Kochi area screening box only; not an official boundary.
KOCHI_SCREENING_BOUNDS = (76.1, 9.7, 76.6, 10.2)


def inspect_archive(archive_path: Path) -> dict[str, Any]:
    if rasterio is None:
        raise RuntimeError("rasterio is required: install it with 'python -m pip install rasterio'.")
    if not archive_path.is_file() or not zipfile.is_zipfile(archive_path):
        raise RuntimeError(f"Missing or invalid raster ZIP: {archive_path}")

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="kochi-raster-audit-") as temp:
        root = Path(temp)
        with zipfile.ZipFile(archive_path) as archive:
            raster_names = [
                info.filename for info in archive.infolist()
                if not info.is_dir() and info.filename.lower().endswith((".tif", ".tiff"))
            ]
            if not raster_names:
                raise RuntimeError("ZIP contains no TIFF rasters to inspect.")
            for index, member in enumerate(raster_names):
                # Avoid extracting paths supplied by the ZIP archive.
                target = root / f"raster_{index}{Path(member).suffix.lower()}"
                with archive.open(member) as src, target.open("wb") as dst:
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        dst.write(chunk)
                try:
                    with rasterio.open(target) as ds:
                        bounds = [float(ds.bounds.left), float(ds.bounds.bottom), float(ds.bounds.right), float(ds.bounds.top)]
                        crs_text = ds.crs.to_string() if ds.crs else None
                        kochi_overlap = None
                        if ds.crs and ds.crs.to_epsg() == 4326:
                            left, bottom, right, top = bounds
                            kleft, kbottom, kright, ktop = KOCHI_SCREENING_BOUNDS
                            kochi_overlap = not (right < kleft or left > kright or top < kbottom or bottom > ktop)
                        sample_summary = []
                        for band in range(1, ds.count + 1):
                            height = min(512, ds.height)
                            width = min(512, ds.width)
                            data = ds.read(band, out_shape=(height, width), masked=True)
                            if data.count():
                                sample_summary.append({
                                    "band": band,
                                    "sampled_min": float(data.min()),
                                    "sampled_max": float(data.max()),
                                    "sampled_valid_count": int(data.count()),
                                    "description": ds.descriptions[band - 1],
                                    "units": ds.units[band - 1] if ds.units else None,
                                    "nodata": ds.nodata,
                                })
                            else:
                                sample_summary.append({
                                    "band": band, "sampled_min": None, "sampled_max": None,
                                    "sampled_valid_count": 0,
                                    "description": ds.descriptions[band - 1],
                                    "units": ds.units[band - 1] if ds.units else None,
                                    "nodata": ds.nodata,
                                })
                        results.append({
                            "archive_member": member,
                            "status": "METADATA_READ_NOT_SCIENTIFICALLY_VALIDATED",
                            "driver": ds.driver,
                            "crs": crs_text,
                            "crs_epsg": ds.crs.to_epsg() if ds.crs else None,
                            "width_pixels": ds.width,
                            "height_pixels": ds.height,
                            "band_count": ds.count,
                            "data_types": list(ds.dtypes),
                            "bounds_in_source_crs": bounds,
                            "resolution_in_source_crs_units": [float(ds.res[0]), float(ds.res[1])],
                            "transform": list(ds.transform)[:6],
                            "nodata": ds.nodata,
                            "band_summaries": sample_summary,
                            "kochi_screening_box_overlap": kochi_overlap,
                            "kochi_screening_box": list(KOCHI_SCREENING_BOUNDS),
                            "limitations": [
                                "Sampled min/max are from a downsampled sample, not guaranteed full-raster extrema.",
                                "A bounding-box overlap is only a screening check, not a polygon-coverage or alignment validation.",
                                "Band values, return-period semantics, vertical/horizontal units, source accuracy and licence require source documentation.",
                                "No raster is approved for map display or exposure analysis by this audit.",
                            ],
                        })
                except Exception as error:
                    results.append({
                        "archive_member": member,
                        "status": "BLOCKED_RASTER_READ",
                        "error": f"{type(error).__name__}: {error}",
                    })

    all_read = bool(results) and all(item["status"] == "METADATA_READ_NOT_SCIENTIFICALLY_VALIDATED" for item in results)
    return {
        "audit_version": 1,
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive": str(archive_path),
        "archive_sha256": _sha256(archive_path),
        "status": "METADATA_READ_NOT_APPROVED_FOR_MAP" if all_read else "BLOCKED_OR_PARTIAL_RASTER_METADATA_AUDIT",
        "raster_count": len(results),
        "rasters": results,
        "approval": "NOT_APPROVED_FOR_MAP_OR_EXPOSURE_ANALYSIS",
    }


def _sha256(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = inspect_archive(args.archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Raster metadata audit: {report['status']}; {report['raster_count']} raster(s)")
    for item in report["rasters"]:
        print(f"- {item['archive_member']}: {item['status']}; CRS={item.get('crs')}; bounds={item.get('bounds_in_source_crs')}; Kochi overlap={item.get('kochi_screening_box_overlap')}")
    print("Metadata inspection is not scientific validation or permission to display the layer.")
    return 0 if report["status"] == "METADATA_READ_NOT_APPROVED_FOR_MAP" else 2


if __name__ == "__main__":
    raise SystemExit(main())

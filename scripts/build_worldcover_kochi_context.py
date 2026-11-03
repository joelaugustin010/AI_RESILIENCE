"""Build a provenance-pinned visual context crop from the acquired ESA tile."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.landcover_context import (
    WORLD_COVER_CLASSES,
    colorize_worldcover,
    validate_worldcover_preview,
)


SOURCE = (
    ROOT
    / "data"
    / "raw"
    / "experimental"
    / "kochidata_2026-11-02"
    / "esa_worldcover_10m_2021_v200_N09E075_Map.tif"
)
SOURCE_METADATA = SOURCE.with_name(SOURCE.name + ".metadata.json")
OUTPUT = (
    ROOT
    / "data"
    / "processed"
    / "spatial_layers"
    / "worldcover_2021_kochi_context.png"
)
OUTPUT_METADATA = OUTPUT.with_name(OUTPUT.stem + ".metadata.json")
SOURCE_SHA256 = "913f22dd9ba2b05f52eeb104ca88aa5162ec2d0a5dcef1124d4f19546ac49558"
# Explicit review rectangle for visualization only; it is not a municipal boundary.
REVIEW_BOUNDS = (76.15, 9.78, 76.42, 10.12)
MAX_IMAGE_DIMENSION = 2400


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata() -> dict[str, Any]:
    if not SOURCE.is_file() or not SOURCE_METADATA.is_file():
        raise FileNotFoundError(f"Required WorldCover source or metadata is missing: {SOURCE}")
    source_metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8"))
    source_hash = _sha256(SOURCE)
    if source_hash != SOURCE_SHA256 or source_metadata.get("sha256") != SOURCE_SHA256:
        raise ValueError("WorldCover source does not match the reviewed SHA-256.")
    if source_metadata.get("license") != "Creative Commons Attribution 4.0 International (CC BY 4.0)":
        raise ValueError("WorldCover source reuse terms differ from the reviewed CC BY 4.0 record.")
    return source_metadata


def build_preview(*, replace: bool = False) -> dict[str, Any]:
    """Create a small legend-based PNG crop; never modifies the acquired GeoTIFF."""
    metadata = _metadata()
    if not replace and (OUTPUT.exists() or OUTPUT_METADATA.exists()):
        raise FileExistsError(
            f"Processed output already exists; use --replace to rebuild: {OUTPUT}"
        )

    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.windows import Window, bounds as window_bounds

    west, south, east, north = REVIEW_BOUNDS
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(SOURCE) as raster:
        if raster.crs is None or raster.crs.to_string() != "EPSG:4326":
            raise ValueError(f"Expected EPSG:4326 source raster, got {raster.crs!s}.")
        if raster.count != 1 or raster.dtypes[0] != "uint8" or raster.nodata != 0:
            raise ValueError("WorldCover source schema differs from the reviewed single-band UInt8 product.")
        if not (
            raster.bounds.left <= west
            and raster.bounds.bottom <= south
            and raster.bounds.right >= east
            and raster.bounds.top >= north
        ):
            raise ValueError("Requested Kochi review rectangle is not fully covered by the source tile.")

        row_start, col_start = raster.index(west, north)
        row_end, col_end = raster.index(east, south)
        col_start = max(0, col_start)
        row_start = max(0, row_start)
        col_end = min(raster.width, col_end)
        row_end = min(raster.height, row_end)
        window = Window(
            col_start,
            row_start,
            col_end - col_start,
            row_end - row_start,
        )
        if window.width <= 0 or window.height <= 0:
            raise ValueError("The requested WorldCover crop contains no raster pixels.")

        scale = min(1.0, MAX_IMAGE_DIMENSION / max(window.width, window.height))
        out_width = max(1, math.ceil(window.width * scale))
        out_height = max(1, math.ceil(window.height * scale))
        values = raster.read(
            1,
            window=window,
            out_shape=(out_height, out_width),
            resampling=Resampling.nearest,
        )
        bounds = list(window_bounds(window, raster.transform))
        source_nodata = raster.nodata
        source_crs = raster.crs.to_string()
        source_resolution = list(raster.res)

    rgba = colorize_worldcover(values, nodata=int(source_nodata))
    preview_image = Image.fromarray(rgba, mode="RGBA")
    preview_image.save(OUTPUT, format="PNG", optimize=True)
    preview_hash = _sha256(OUTPUT)
    preview_classes = sorted(
        {int(code) for code in np.unique(values).tolist() if code != source_nodata}
    )
    output_metadata: dict[str, Any] = {
        "dataset_id": OUTPUT.stem,
        "title": "ESA WorldCover 2021 v200 land-cover context crop for approximate Kochi review bounds",
        "publisher": metadata["publisher"],
        "source_url": metadata["url"],
        "source_file": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": SOURCE_SHA256,
        "retrieved_on": metadata["retrieved_at_utc"][:10],
        "publication_date": metadata["publication_date"],
        "license": metadata["license"],
        "attribution": "© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium",
        "source_crs": source_crs,
        "source_units": "Categorical UInt8 land-cover class; no-data code 0",
        "source_resolution_degrees": source_resolution,
        "processing": {
            "method": "Read only the fixed review rectangle from the source GeoTIFF, downsampled using nearest-neighbour for display, then colorized with the ESA WorldCover v200 class legend.",
            "review_rectangle_wgs84": {
                "west": west,
                "south": south,
                "east": east,
                "north": north,
            },
            "bounds_epsg4326": bounds,
            "image_width_pixels": out_width,
            "image_height_pixels": out_height,
            "resampling": "nearest",
            "rendered_class_codes": preview_classes,
            "classes": {
                str(code): {
                    "label": WORLD_COVER_CLASSES[code]["label"],
                    "rgb": list(WORLD_COVER_CLASSES[code]["color"]),
                }
                for code in preview_classes
            },
            "transparent_nodata_code": int(source_nodata),
            "preview_file": OUTPUT.name,
            "preview_sha256": preview_hash,
        },
        "layer_role": "context",
        "analysis_status": "Display-only categorical land-cover context; not used for hazard, population, exposure, or consequence calculations.",
        "limitations": [
            "2021 remotely sensed land-cover classification; not current building footprints, household data, vegetation condition, impervious fraction, drainage capacity, temperature, or hazard susceptibility.",
            "The review rectangle is a visualization window, not a legal or validated Kochi Corporation boundary.",
            "Image is downsampled for web display; classification accuracy has not been assessed locally.",
            "Transparent pixels represent source NoData only in this crop and are not evidence of no hazard or exposure.",
            "WorldCover class legend attribution is required under CC BY 4.0.",
        ],
    }
    OUTPUT_METADATA.write_text(
        json.dumps(output_metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_metadata


def verify_preview() -> dict[str, Any]:
    """Verify the published preview and pinned source provenance."""
    if not OUTPUT.is_file() or not OUTPUT_METADATA.is_file():
        raise FileNotFoundError(f"WorldCover preview or sidecar is missing: {OUTPUT}")
    record = json.loads(OUTPUT_METADATA.read_text(encoding="utf-8"))
    if SOURCE.is_file() or SOURCE_METADATA.is_file():
        source_metadata = _metadata()
        if record.get("source_sha256") != source_metadata.get("sha256"):
            raise ValueError("Processed metadata source hash does not match the acquired tile.")
    elif (
        record.get("source_sha256") != SOURCE_SHA256
        or record.get("license")
        != "Creative Commons Attribution 4.0 International (CC BY 4.0)"
    ):
        raise ValueError("Processed metadata does not match the reviewed source provenance.")
    validate_worldcover_preview(OUTPUT.read_bytes(), record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="Replace only the processed PNG and its sidecar.")
    parser.add_argument("--verify-only", action="store_true", help="Verify existing raw and processed file checksums.")
    args = parser.parse_args()
    result = verify_preview() if args.verify_only else build_preview(replace=args.replace)
    print(json.dumps({
        "output": str(OUTPUT),
        "preview_sha256": result["processing"]["preview_sha256"],
        "bounds_epsg4326": result["processing"]["bounds_epsg4326"],
        "rendered_class_codes": result["processing"]["rendered_class_codes"],
        "status": result["analysis_status"],
    }, indent=2))


if __name__ == "__main__":
    main()

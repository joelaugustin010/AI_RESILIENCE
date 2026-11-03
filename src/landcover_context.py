"""Visualization helpers for ESA WorldCover context, not hazard classification."""

from __future__ import annotations

import hashlib
import io
from typing import Any

import numpy as np
from PIL import Image


WORLD_COVER_CLASSES = {
    10: {"label": "Tree cover", "color": (0, 100, 0)},
    20: {"label": "Shrubland", "color": (255, 187, 34)},
    30: {"label": "Grassland", "color": (255, 255, 76)},
    40: {"label": "Cropland", "color": (240, 150, 255)},
    50: {"label": "Built-up", "color": (250, 0, 0)},
    60: {"label": "Bare / sparse vegetation", "color": (180, 180, 180)},
    70: {"label": "Snow and ice", "color": (240, 240, 240)},
    80: {"label": "Permanent water bodies", "color": (0, 100, 200)},
    90: {"label": "Herbaceous wetland", "color": (0, 150, 160)},
    95: {"label": "Mangroves", "color": (0, 207, 117)},
    100: {"label": "Moss and lichen", "color": (250, 230, 160)},
}


def colorize_worldcover(values: np.ndarray, nodata: int = 0) -> np.ndarray:
    """Convert known ESA class codes to transparent RGBA visualization pixels."""
    classes = np.asarray(values)
    if classes.ndim != 2:
        raise ValueError("WorldCover values must be a two-dimensional array.")
    if not np.issubdtype(classes.dtype, np.integer):
        raise ValueError("WorldCover class values must use an integer dtype.")

    unknown = set(np.unique(classes).tolist()).difference(WORLD_COVER_CLASSES).difference({nodata})
    if unknown:
        raise ValueError(f"Unknown WorldCover class codes: {sorted(unknown)}.")

    rgba = np.zeros((*classes.shape, 4), dtype=np.uint8)
    for code, definition in WORLD_COVER_CLASSES.items():
        rgba[classes == code, :3] = definition["color"]
        rgba[classes == code, 3] = 220
    return rgba


def validate_worldcover_preview(image_bytes: bytes, metadata: dict[str, Any]) -> None:
    """Verify processed PNG integrity and declared display bounds before mapping."""
    processing = metadata.get("processing")
    if not isinstance(processing, dict):
        raise ValueError("WorldCover preview processing metadata is missing.")
    expected_hash = processing.get("preview_sha256")
    if not isinstance(expected_hash, str) or hashlib.sha256(image_bytes).hexdigest() != expected_hash:
        raise ValueError("WorldCover preview SHA-256 does not match its provenance sidecar.")

    bounds = processing.get("bounds_epsg4326")
    if (
        not isinstance(bounds, list)
        or len(bounds) != 4
        or not all(isinstance(value, (int, float)) for value in bounds)
        or not (bounds[0] < bounds[2] and bounds[1] < bounds[3])
        or not (-180 <= bounds[0] <= 180 and -180 <= bounds[2] <= 180)
        or not (-90 <= bounds[1] <= 90 and -90 <= bounds[3] <= 90)
    ):
        raise ValueError("WorldCover preview geographic bounds are invalid.")

    expected_size = (
        processing.get("image_width_pixels"),
        processing.get("image_height_pixels"),
    )
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            if image.format != "PNG" or image.mode != "RGBA" or image.size != expected_size:
                raise ValueError("WorldCover preview format, mode, or dimensions do not match its metadata.")
            image.verify()
    except (OSError, SyntaxError) as error:
        raise ValueError(f"WorldCover preview is not a valid PNG: {error}") from error

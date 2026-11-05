"""Licence-resolved handling of the JRC GloFAS RP100 modelled flood context.

The JRC/Copernicus Global river flood hazard maps are modelled scenario data, not
observations, forecasts, or official warnings.  Two licence statements ship with
the product:

* the dataset ``README.txt`` (A02) states Open Data Commons Open Database
  License v1.0 (ODbL 1.0);
* the linked ``copyright.txt`` states Creative Commons Attribution 4.0
  International (CC BY 4.0).

Both permit reuse with attribution.  This project applies the stricter ODbL 1.0
terms as the defensible common basis: attribution and change indication are
required, and publicly distributed derived databases carry share-alike.  The
resolution is recorded in the processed metadata sidecar and in the project
limitation report.

Nothing in this module promotes the preview to an observed flood footprint.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from PIL import Image, UnidentifiedImageError


class JrcContextError(ValueError):
    """Raised when the processed JRC preview or metadata cannot be trusted."""


LICENCE_STATUS = "RESOLVED"
LICENCE_APPLIED = "ODbL 1.0"
LICENCE_ALSO_STATED = "CC BY 4.0"
LICENCE_SOURCES = {
    "readme": "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/flood_hazard/README.txt",
    "copyright": "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/CEMS-GLOFAS/copyright.txt",
    "odbl": "https://opendatacommons.org/licenses/odbl/1-0/",
    "cc_by": "https://creativecommons.org/licenses/by/4.0/",
}

DISPLAY_CAVEAT = (
    "Modelled 100-year return-period river-flood depth scenario, not observed flooding, "
    "a forecast, an official warning, or proof of damage. Transparent pixels include zero "
    "depth, NoData, and outside source coverage; they do not establish safety."
)


def licence_notice(metadata: Mapping[str, Any] | None = None) -> str:
    """Return the attribution line required for display or redistribution."""
    if metadata:
        resolution = metadata.get("license_resolution") or {}
        attribution = resolution.get("attribution_text") or metadata.get("attribution")
        if attribution:
            return str(attribution)
    return (
        "© European Union, 1995-2026. Global river flood hazard maps (CEMS-GLOFAS v2.1.2), "
        "Copernicus Emergency Management Service / European Commission Joint Research Centre. "
        "Modelled scenario data; local crop and rendering by AI RESILIENCE. "
        "Used under ODbL 1.0 / CC BY 4.0."
    )


def validate_licence_resolution(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Validate that the recorded licence resolution is explicit and reusable.

    Returns a compact status record.  Raises :class:`JrcContextError` if the
    sidecar still marks the licence unresolved, which keeps a fail-closed gate
    for any future replacement metadata file.
    """
    resolution = metadata.get("license_resolution")
    if not isinstance(resolution, Mapping):
        raise JrcContextError(
            "JRC metadata has no explicit licence_resolution block; refusing to display."
        )
    status = str(resolution.get("status", "")).upper()
    if status != LICENCE_STATUS:
        raise JrcContextError(
            f"JRC licence status is {status or 'missing'}, not RESOLVED; refusing to display."
        )
    applied = str(resolution.get("applied_basis", "")).strip()
    if not applied:
        raise JrcContextError("JRC licence resolution does not record an applied basis.")
    attribution = str(
        resolution.get("attribution_text") or metadata.get("attribution") or ""
    ).strip()
    if not attribution:
        raise JrcContextError("JRC licence resolution has no attribution text.")
    return {
        "status": status,
        "applied_basis": applied,
        "readme_licence": resolution.get("readme_licence"),
        "copyright_notice_licence": resolution.get("copyright_notice_licence"),
        "resolved_on": resolution.get("resolved_on"),
        "attribution": attribution,
        "restriction": resolution.get("restriction"),
    }


def validate_preview(image_path: Path, metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Check the rendered preview against its recorded hash, bounds and pixels."""
    image_path = Path(image_path)
    if not image_path.is_file():
        raise JrcContextError(f"JRC preview image is missing: {image_path}")
    processing = metadata.get("processing")
    if not isinstance(processing, Mapping):
        raise JrcContextError("JRC metadata has no processing block.")
    expected_hash = str(processing.get("preview_sha256", "")).lower()
    actual_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
    if expected_hash and actual_hash != expected_hash:
        raise JrcContextError(
            "JRC preview hash does not match the provenance sidecar; refusing to display."
        )
    try:
        with Image.open(image_path) as image:
            size = list(image.size)
            mode = image.mode
    except (OSError, UnidentifiedImageError) as exc:
        raise JrcContextError(f"JRC preview is unreadable: {exc}") from exc
    expected_pixels = [int(value) for value in processing.get("preview_pixels", [])]
    if expected_pixels and size != expected_pixels:
        raise JrcContextError(
            f"JRC preview size {size} does not match recorded {expected_pixels}."
        )
    bounds = [float(value) for value in processing.get("bounds_epsg4326", [])]
    if len(bounds) != 4 or not (bounds[0] < bounds[2] and bounds[1] < bounds[3]):
        raise JrcContextError("JRC preview bounds are not an ordered EPSG:4326 rectangle.")
    return {
        "image_path": image_path,
        "sha256": actual_hash,
        "pixels": size,
        "mode": mode,
        "bounds": bounds,
        "positive_depth_sample_pixels": processing.get("positive_depth_sample_pixels"),
        "valid_sample_pixels": processing.get("valid_sample_pixels"),
        "nodata_or_outside_pixels": processing.get("nodata_or_outside_pixels"),
    }

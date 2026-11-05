"""Small, read-only reader for the downloaded sparse JRC GeoTIFF tiles.

The source rasters are kept intact. This module reads individual 256x256 tiles,
honours their documented NoData value, and only produces a transparent map
preview. It is not a general-purpose GIS raster engine.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import warnings
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


class FloodRasterError(ValueError):
    """Raised when a source raster cannot be safely read or validated."""


def classify_depth_sample(
    depth_m: float | None, *, within_coverage: bool, coordinates_validated: bool
) -> dict[str, Any]:
    """Label a raster cell sample without calling it a geometric intersection."""
    if not coordinates_validated:
        return {"status": "unknown / unassessable", "depth_m": None,
                "reason": "Asset coordinates have not been independently validated."}
    if not within_coverage or depth_m is None or not math.isfinite(depth_m):
        return {"status": "unknown / unassessable", "depth_m": None,
                "reason": "No valid raster sample is available at the supplied location."}
    if depth_m < 0:
        return {"status": "unknown / unassessable", "depth_m": None,
                "reason": "Negative depth is not a valid modeled flood-depth sample."}
    if depth_m > 0:
        return {"status": "positive modeled depth cell", "depth_m": depth_m,
                "reason": "Nearest raster cell has positive modeled depth; this is not proof of damage or service failure."}
    return {"status": "no positive depth detected in sampled cell", "depth_m": 0.0,
            "reason": "Only the sampled raster cell is described; this does not establish safety."}


class JrcDepthTile:
    """Read a single-band float32, EPSG:4326, DEFLATE GeoTIFF tile."""

    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.is_file():
            raise FloodRasterError(f"Raster file not found: {self.path}")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with Image.open(self.path) as image:
                    tags = image.tag_v2
                    self.width, self.height = image.size
                    self.mode = image.mode
                    self.tags = {int(tag): value for tag, value in tags.items()}
                self._tiff = self.path.read_bytes()
        except (OSError, UnidentifiedImageError) as exc:
            raise FloodRasterError(f"Unreadable GeoTIFF: {exc}") from exc

        if self.mode != "F" or self.width != 11999 or self.height != 11999:
            raise FloodRasterError("Expected the JRC 11999x11999 single-band float32 tile.")
        if self.tags.get(259) != 8 or self.tags.get(317, 1) != 1:
            raise FloodRasterError("Only DEFLATE tiles without a TIFF predictor are supported.")
        if tuple(self.tags.get(339, ())) != (3,):
            raise FloodRasterError("Expected 32-bit floating-point samples.")
        if self.tags.get(42113) not in (-9999, "-9999", b"-9999"):
            raise FloodRasterError("Expected the source NoData tag to be -9999.")
        if not self._has_epsg_4326_key():
            raise FloodRasterError("EPSG:4326 was not found in the GeoTIFF keys.")

        scales = self.tags.get(33550)
        tiepoints = self.tags.get(33922)
        if not scales or not tiepoints or len(scales) < 2 or len(tiepoints) < 6:
            raise FloodRasterError("GeoTIFF georeferencing tags are missing.")
        self.pixel_x, self.pixel_y = float(scales[0]), float(scales[1])
        _, _, _, self.west, self.north, _ = map(float, tiepoints[:6])
        self.nodata = -9999.0
        self.tile_width = int(self.tags.get(322, 256))
        self.tile_height = int(self.tags.get(323, 256))
        self.offsets = tuple(self.tags.get(324, ()))
        self.byte_counts = tuple(self.tags.get(325, ()))
        if self.tile_width != 256 or self.tile_height != 256 or len(self.offsets) != len(self.byte_counts):
            raise FloodRasterError("Unexpected or incomplete TIFF tile index.")
        self.tiles_across = math.ceil(self.width / self.tile_width)

    def _has_epsg_4326_key(self) -> bool:
        directory = self.tags.get(34735, ())
        # GeoKeyDirectory entries are 4-tuples; GeographicTypeGeoKey (2048)
        # has value 4326 in this source file.
        return len(directory) >= 4 and any(
            directory[index] == 2048 and directory[index + 3] == 4326
            for index in range(4, len(directory), 4)
        )

    @lru_cache(maxsize=64)
    def _tile_values(self, index: int) -> tuple[float, ...]:
        offset, count = self.offsets[index], self.byte_counts[index]
        if not offset and not count:
            # GDAL's documented sparse-TIFF convention: an unwritten block
            # reads as the band's declared NoData value when one is present.
            return (-9999.0,) * (self.tile_width * self.tile_height)
        if not offset or not count:
            raise FloodRasterError(f"Inconsistent sparse-tile index at tile {index}.")
        try:
            raw = zlib.decompress(self._tiff[offset:offset + count])
        except zlib.error as exc:
            raise FloodRasterError(f"Could not decompress raster tile {index}: {exc}") from exc
        expected = self.tile_width * self.tile_height * 4
        if len(raw) != expected:
            raise FloodRasterError(f"Tile {index} decoded to {len(raw)} bytes, expected {expected}.")
        return struct.unpack("<65536f", raw)

    def sample(self, longitude: float, latitude: float) -> float | None:
        """Return depth in metres, or None for outside coverage/NoData."""
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise FloodRasterError("Longitude/latitude is outside valid EPSG:4326 ranges.")
        col = math.floor((longitude - self.west) / self.pixel_x)
        row = math.floor((self.north - latitude) / self.pixel_y)
        if col < 0 or row < 0 or col >= self.width or row >= self.height:
            return None
        tile_col, tile_row = col // self.tile_width, row // self.tile_height
        tile_index = tile_row * self.tiles_across + tile_col
        values = self._tile_values(tile_index)
        value = values[(row % self.tile_height) * self.tile_width + (col % self.tile_width)]
        if value == self.nodata or not math.isfinite(value):
            return None
        return value

    def manifest(self, publisher: str, source_url: str, retrieved_on: str) -> dict[str, Any]:
        return {
            "file": self.path.name,
            "bytes": self.path.stat().st_size,
            "sha256": hashlib.sha256(self._tiff).hexdigest(),
            "dimensions": [self.width, self.height],
            "bands": 1,
            "dtype": "float32",
            "compression": "DEFLATE",
            "crs": "EPSG:4326",
            "pixel_size_degrees": [self.pixel_x, self.pixel_y],
            "bounds": [self.west, self.north - self.height * self.pixel_y,
                       self.west + self.width * self.pixel_x, self.north],
            "nodata": self.nodata,
            "publisher": publisher,
            "source_url": source_url,
            "retrieved_on": retrieved_on,
        }


class JrcPermanentWaterTile:
    """Read the JRC permanent-water mask tile (uint8, value 1, NoData 255).

    The JRC README says permanent water bodies are patched into the flood maps.
    Sampling the mask lets a caller exclude permanent-water cells from a flood
    screening so that a river or lake is not reported as flood exposure.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        if not self.path.is_file():
            raise FloodRasterError(f"Raster file not found: {self.path}")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with Image.open(self.path) as image:
                    tags = image.tag_v2
                    self.width, self.height = image.size
                    self.mode = image.mode
                    self.tags = {int(tag): value for tag, value in tags.items()}
                self._tiff = self.path.read_bytes()
        except (OSError, UnidentifiedImageError) as exc:
            raise FloodRasterError(f"Unreadable GeoTIFF: {exc}") from exc
        if self.mode != "L" or self.width != 11999 or self.height != 11999:
            raise FloodRasterError("Expected the JRC 11999x11999 uint8 permanent-water tile.")
        if self.tags.get(259) != 8 or self.tags.get(317, 1) != 1:
            raise FloodRasterError("Only DEFLATE permanent-water tiles without a predictor are supported.")
        if tuple(self.tags.get(339, ())) != (1,):
            raise FloodRasterError("Expected 8-bit unsigned samples in the permanent-water tile.")
        if self.tags.get(42113) not in (255, "255", b"255"):
            raise FloodRasterError("Expected the permanent-water NoData tag to be 255.")
        if not self._has_epsg_4326_key():
            raise FloodRasterError("EPSG:4326 was not found in the permanent-water GeoTIFF keys.")
        scales = self.tags.get(33550)
        tiepoints = self.tags.get(33922)
        if not scales or not tiepoints or len(scales) < 2 or len(tiepoints) < 6:
            raise FloodRasterError("Permanent-water GeoTIFF georeferencing tags are missing.")
        self.pixel_x, self.pixel_y = float(scales[0]), float(scales[1])
        _, _, _, self.west, self.north, _ = map(float, tiepoints[:6])
        self.nodata = 255
        self.tile_width = int(self.tags.get(322, 256))
        self.tile_height = int(self.tags.get(323, 256))
        self.offsets = tuple(self.tags.get(324, ()))
        self.byte_counts = tuple(self.tags.get(325, ()))
        if self.tile_width != 256 or self.tile_height != 256 or len(self.offsets) != len(self.byte_counts):
            raise FloodRasterError("Unexpected or incomplete permanent-water TIFF tile index.")
        self.tiles_across = math.ceil(self.width / self.tile_width)

    def _has_epsg_4326_key(self) -> bool:
        directory = self.tags.get(34735, ())
        return len(directory) >= 4 and any(
            directory[index] == 2048 and directory[index + 3] == 4326
            for index in range(4, len(directory), 4)
        )

    @lru_cache(maxsize=64)
    def _tile_values(self, index: int) -> bytes:
        offset, count = self.offsets[index], self.byte_counts[index]
        if not offset and not count:
            return bytes([255]) * (self.tile_width * self.tile_height)
        if not offset or not count:
            raise FloodRasterError(f"Inconsistent permanent-water sparse-tile index at tile {index}.")
        try:
            raw = zlib.decompress(self._tiff[offset:offset + count])
        except zlib.error as exc:
            raise FloodRasterError(
                f"Could not decompress permanent-water tile {index}: {exc}"
            ) from exc
        expected = self.tile_width * self.tile_height
        if len(raw) != expected:
            raise FloodRasterError(
                f"Permanent-water tile {index} decoded to {len(raw)} bytes, expected {expected}."
            )
        return raw

    def sample(self, longitude: float, latitude: float) -> int | None:
        """Return 1 for permanent water, 0 for other land, None for NoData/outside."""
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
            raise FloodRasterError("Longitude/latitude is outside valid EPSG:4326 ranges.")
        col = math.floor((longitude - self.west) / self.pixel_x)
        row = math.floor((self.north - latitude) / self.pixel_y)
        if col < 0 or row < 0 or col >= self.width or row >= self.height:
            return None
        tile_col, tile_row = col // self.tile_width, row // self.tile_height
        tile_index = tile_row * self.tiles_across + tile_col
        values = self._tile_values(tile_index)
        value = values[(row % self.tile_height) * self.tile_width + (col % self.tile_width)]
        if value == self.nodata:
            return None
        return int(value)


def create_depth_preview(
    tile_paths: list[Path], bounds: tuple[float, float, float, float], output_path: Path,
    width: int = 520, height: int = 520,
) -> dict[str, Any]:
    """Write a non-analytical transparent PNG preview for a geographic bbox."""
    west, south, east, north = map(float, bounds)
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise FloodRasterError("Preview bounds must be an ordered EPSG:4326 rectangle.")
    if width < 2 or height < 2 or width > 1500 or height > 1500:
        raise FloodRasterError("Preview dimensions must be between 2 and 1500 pixels.")
    tiles = [JrcDepthTile(path) for path in tile_paths]
    if not tiles:
        raise FloodRasterError("At least one flood tile is required.")
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = image.load()
    valid = positive = nodata = 0
    for y in range(height):
        lat = north - (y + 0.5) * (north - south) / height
        for x in range(width):
            lon = west + (x + 0.5) * (east - west) / width
            value = None
            for tile in tiles:
                value = tile.sample(lon, lat)
                if value is not None:
                    break
            if value is None:
                nodata += 1
            else:
                valid += 1
                if value > 0:
                    positive += 1
                    # Display-only continuous palette; no risk classes or
                    # thresholds are introduced by this visualization.
                    alpha = 95 + round(120 * min(value, 5.0) / 5.0)
                    pixels[x, y] = (20, 105, 220, alpha)
    if valid == 0:
        raise FloodRasterError("No valid raster samples fall inside the preview bounds.")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG", optimize=True)
    return {
        "preview_file": output_path.name,
        "preview_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "bounds_epsg4326": [west, south, east, north],
        "preview_pixels": [width, height],
        "valid_sample_pixels": valid,
        "positive_depth_sample_pixels": positive,
        "nodata_or_outside_pixels": nodata,
        "rendering": "transparent blue overlay for positive modeled depth; transparent for zero, NoData, and outside source coverage",
    }

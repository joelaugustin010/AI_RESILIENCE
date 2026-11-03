"""Tests for the explicitly non-predictive WorldCover context visualization."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import numpy as np
from PIL import Image

from scripts import build_worldcover_kochi_context
from scripts.build_worldcover_kochi_context import OUTPUT, SOURCE, SOURCE_METADATA, verify_preview
from src.landcover_context import colorize_worldcover, validate_worldcover_preview


class LandCoverContextTests(unittest.TestCase):
    def test_worldcover_classes_are_colorized_without_converting_nodata_to_zero_class(self):
        result = colorize_worldcover(np.array([[50, 80, 0]], dtype=np.uint8))

        self.assertEqual(result.shape, (1, 3, 4))
        self.assertEqual(result[0, 0].tolist(), [250, 0, 0, 220])
        self.assertEqual(result[0, 1].tolist(), [0, 100, 200, 220])
        self.assertEqual(result[0, 2].tolist(), [0, 0, 0, 0])

    def test_unknown_class_codes_fail_explicitly(self):
        with self.assertRaisesRegex(ValueError, "Unknown WorldCover class"):
            colorize_worldcover(np.array([[101]], dtype=np.uint8))

    def test_preview_verification_reports_a_missing_optional_source(self):
        with TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "missing_worldcover.tif"
            metadata = source.with_name(source.name + ".metadata.json")
            with (
                patch.object(build_worldcover_kochi_context, "SOURCE", source),
                patch.object(build_worldcover_kochi_context, "SOURCE_METADATA", metadata),
                self.assertRaisesRegex(
                    FileNotFoundError,
                    "Required WorldCover source or metadata is missing",
                ),
            ):
                build_worldcover_kochi_context.verify_preview()

    @unittest.skipUnless(
        SOURCE.is_file() and SOURCE_METADATA.is_file(),
        "requires the optional local WorldCover source raster and provenance sidecar",
    )
    def test_real_preview_hash_and_geographic_coverage_match_provenance(self):
        metadata = verify_preview()

        self.assertTrue(OUTPUT.is_file())
        self.assertIn("Display-only", metadata["analysis_status"])
        self.assertEqual(metadata["source_crs"], "EPSG:4326")
        self.assertEqual(metadata["processing"]["rendered_class_codes"], sorted(metadata["processing"]["rendered_class_codes"]))
        west, south, east, north = metadata["processing"]["bounds_epsg4326"]
        self.assertLess(west, east)
        self.assertLess(south, north)

        with Image.open(OUTPUT) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.mode, "RGBA")
            self.assertLessEqual(max(image.size), 2400)
            image_bytes = OUTPUT.read_bytes()
            validate_worldcover_preview(image_bytes, metadata)

        with self.assertRaisesRegex(ValueError, "SHA-256"):
            validate_worldcover_preview(b"altered preview", metadata)


if __name__ == "__main__":
    unittest.main()

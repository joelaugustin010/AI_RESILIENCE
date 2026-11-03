"""Tests for converting the preserved OSM road snapshot to map context."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_osm_kochi_context import OSMPreparationError, prepare_layers
from src.spatial_data import read_processed_layers


class OSMContextLayerTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        raw = self.root / "data" / "raw" / "experimental"
        raw.mkdir(parents=True)
        self.source = raw / "openstreetmap_roads_provisional_kochi_bounds.json"
        self.sidecar = self.source.with_name(self.source.name + ".metadata.json")
        self.source.write_text(
            json.dumps(
                {
                    "elements": [
                        {
                            "type": "way",
                            "id": 1,
                            "geometry": [{"lat": 9.93, "lon": 76.27}, {"lat": 9.94, "lon": 76.28}],
                            "tags": {"highway": "primary", "name": "Example Road"},
                        },
                        {
                            "type": "way",
                            "id": 2,
                            "geometry": [{"lat": 9.94, "lon": 76.28}, {"lat": 9.95, "lon": 76.29}],
                            "tags": {"highway": "secondary", "bridge": "yes"},
                        },
                        {
                            "type": "way",
                            "id": 3,
                            "geometry": [{"lat": 9.96, "lon": 76.30}, {"lat": 9.97, "lon": 76.31}],
                            "tags": {"highway": "residential"},
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.sidecar.write_text(
            json.dumps(
                {
                    "sha256": source_hash,
                    "license": "Open Database License (ODbL) 1.0",
                    "crs": "WGS 84 latitude/longitude per OSM API convention",
                    "retrieved_at_utc": "2026-11-01T18:28:39+00:00",
                    "osm_base_timestamp": "2026-11-01T18:27:21Z",
                    "download_size_bytes": self.source.stat().st_size,
                    "source_url": "https://overpass-api.de/api/interpreter?data=example",
                    "query_bounds": {
                        "west": 76.2373589,
                        "south": 9.8934161,
                        "east": 76.3400293,
                        "north": 10.0497693,
                    },
                }
            ),
            encoding="utf-8",
        )
        self.processed_root = self.root / "data" / "processed"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_builds_major_road_and_bridge_layers_with_source_attribution(self):
        result = prepare_layers(self.root)

        self.assertEqual(result["major_roads"]["feature_count"], 2)
        self.assertEqual(result["bridges"]["feature_count"], 1)
        layers = read_processed_layers(self.processed_root)
        self.assertEqual(len(layers), 2)
        self.assertTrue(all(layer["metadata"]["publisher"] == "OpenStreetMap contributors" for layer in layers))
        self.assertTrue(all(layer["metadata"]["layer_role"] == "context" for layer in layers))

    def test_refuses_to_overwrite_existing_context_layer(self):
        layer_dir = self.processed_root / "spatial_layers"
        layer_dir.mkdir(parents=True)
        (layer_dir / "openstreetmap_major_roads_kochi_context.geojson").write_text("preserve", encoding="utf-8")

        with self.assertRaises(FileExistsError):
            prepare_layers(self.root)

    def test_explicit_replacement_keeps_raw_source_unchanged(self):
        source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        prepare_layers(self.root)

        updated = prepare_layers(self.root, replace=True)

        self.assertEqual(updated["major_roads"]["source_sha256"], source_hash)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), source_hash)

    def test_rejects_source_checksum_mismatch(self):
        self.sidecar.write_text(
            self.sidecar.read_text(encoding="utf-8").replace(
                hashlib.sha256(self.source.read_bytes()).hexdigest(), "0" * 64
            ),
            encoding="utf-8",
        )

        with self.assertRaises(OSMPreparationError):
            prepare_layers(self.root)


if __name__ == "__main__":
    unittest.main()

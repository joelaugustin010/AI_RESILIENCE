"""Tests for deterministic OSM context regeneration from a pinned road layer."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.rebuild_kochi_osm_context import rebuild
from src.spatial_data import read_processed_layers


class KochiOSMContextRebuildTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        layer_dir = self.root / "data/processed/spatial_layers"
        layer_dir.mkdir(parents=True)
        self.source = layer_dir / "osm_kochi_roads_20261028T192808Z.geojson"
        self.sidecar = layer_dir / "osm_kochi_roads_20261028T192808Z.metadata.json"
        features = [
            {
                "type": "Feature",
                "id": "way/1",
                "geometry": {"type": "LineString", "coordinates": [[76.27, 9.93], [76.28, 9.94]]},
                "properties": {
                    "osm_type": "way", "osm_id": "1", "feature_type": "road",
                    "feature_name": "Main Road", "source": "OpenStreetMap",
                    "osm_url": "https://www.openstreetmap.org/way/1",
                    "highway": "primary", "bridge": "yes",
                },
            },
            {
                "type": "Feature",
                "id": "way/2",
                "geometry": {"type": "LineString", "coordinates": [[76.28, 9.94], [76.29, 9.95]]},
                "properties": {
                    "osm_type": "way", "osm_id": "2", "feature_type": "road",
                    "feature_name": "Secondary Road", "source": "OpenStreetMap",
                    "osm_url": "https://www.openstreetmap.org/way/2",
                    "highway": "secondary", "bridge": "no",
                },
            },
            {
                "type": "Feature",
                "id": "way/3",
                "geometry": {"type": "LineString", "coordinates": [[76.29, 9.95], [76.30, 9.96]]},
                "properties": {
                    "osm_type": "way", "osm_id": "3", "feature_type": "road",
                    "feature_name": "Local Bridge Road", "source": "OpenStreetMap",
                    "osm_url": "https://www.openstreetmap.org/way/3",
                    "highway": "residential", "bridge": "yes",
                },
            },
        ]
        self.source.write_text(
            json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        source_hash = hashlib.sha256(self.source.read_bytes()).hexdigest()
        metadata = {
            "dataset_id": self.source.stem,
            "title": "Verified OSM road snapshot",
            "source_url": "https://www.openstreetmap.org/",
            "publisher": "OpenStreetMap contributors",
            "retrieved_on": "2026-10-28",
            "publication_date": "Not stated by source; OSM database state as of 2026-10-28T19:25:34Z",
            "license": "Open Database License 1.0 (ODbL); attribution and share-alike apply.",
            "crs": "EPSG:4326",
            "units": "Decimal degrees",
            "geographic_coverage": "Kochi query rectangle only; not an administrative boundary.",
            "limitations": ["Community-mapped context only."],
            "layer_role": "context",
            "required_properties": ["osm_type", "osm_id", "feature_type", "feature_name", "source", "osm_url"],
            "source_database_timestamp": "2026-10-28T19:25:34Z",
            "source_snapshot_sha256": "a" * 64,
            "attribution": "© OpenStreetMap contributors",
            "validation": {"source_sha256": source_hash},
        }
        self.sidecar.write_text(json.dumps(metadata), encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_rebuilds_both_context_layers_and_regenerates_matching_hashes(self):
        result = rebuild(self.root, replace=True)

        self.assertEqual(result["major_roads"]["feature_count"], 2)
        self.assertEqual(result["bridges"]["feature_count"], 2)
        layers = read_processed_layers(self.root / "data/processed")
        self.assertEqual(
            {layer["metadata"]["dataset_id"] for layer in layers},
            {"openstreetmap_major_roads_kochi_context", "openstreetmap_bridges_kochi_context"},
        )
        for layer in layers:
            path = self.root / "data/processed/spatial_layers" / f"{layer['metadata']['dataset_id']}.geojson"
            actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(layer["metadata"]["validation"]["source_sha256"], actual_hash)
            self.assertEqual(layer["metadata"]["layer_role"], "context")
            self.assertEqual(layer["metadata"]["analysis_status"].split(";")[0], "Context display only")

    def test_refuses_a_source_snapshot_with_stale_hash(self):
        metadata = json.loads(self.sidecar.read_text(encoding="utf-8"))
        metadata["validation"]["source_sha256"] = "0" * 64
        self.sidecar.write_text(json.dumps(metadata), encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "content hash"):
            rebuild(self.root, replace=True)


if __name__ == "__main__":
    unittest.main()

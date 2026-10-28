"""Offline validation tests for the bounded OSM acquisition pipeline."""

from __future__ import annotations

import hashlib
import gzip
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.kochi_osm import (
    KOCHI_BBOX,
    _publish_processed_layer,
    _write_exclusive,
    overpass_queries,
    parse_osm_layers,
    write_raw_snapshot,
)
from src.spatial_data import processed_layer_issues, read_processed_layers


def node(osm_id: int, lon: float, lat: float, tags: dict) -> dict:
    return {"type": "node", "id": osm_id, "lon": lon, "lat": lat, "tags": tags}


def way(osm_id: int, points: list[tuple[float, float]], tags: dict, center: tuple[float, float] | None = None) -> dict:
    element = {
        "type": "way",
        "id": osm_id,
        "geometry": [{"lon": lon, "lat": lat} for lon, lat in points],
        "tags": tags,
    }
    if center:
        element["center"] = {"lon": center[0], "lat": center[1]}
    return element


class KochiOSMQueryTests(unittest.TestCase):
    def test_queries_are_bounded_and_do_not_use_invalid_boundary_as_a_mask(self):
        queries = overpass_queries()
        self.assertEqual(set(queries), {"network", "facilities"})
        self.assertIn("76.23735890,10.04976931", queries["network"])
        self.assertIn("9.85000000,76.15000000,10.20000000,76.45000000", queries["facilities"])
        self.assertIn('["waterway"', queries["network"])
        self.assertIn('["amenity"', queries["facilities"])
        self.assertNotIn("poly:", queries["network"])
        self.assertNotIn("poly:", queries["facilities"])

    def test_parse_splits_mapped_roads_waterways_facilities_and_monitors(self):
        payload = {
            "osm3s": {"timestamp_osm_base": "2026-10-28T19:13:19Z"},
            "elements": [
                way(10, [(76.28, 9.95), (76.29, 9.96)], {"highway": "primary", "name": "Test Road"}),
                way(11, [(76.28, 9.95), (76.29, 9.96)], {"railway": "rail", "name": "Test Rail"}),
                way(12, [(76.28, 9.95), (76.29, 9.96)], {"waterway": "drain"}),
                node(13, 76.30, 9.98, {"amenity": "hospital", "name": "Test Hospital"}),
                node(14, 76.31, 9.99, {"amenity": "fire_station"}),
                way(
                    15,
                    [(76.30, 9.97), (76.31, 9.97), (76.31, 9.98), (76.30, 9.97)],
                    {"landuse": "industrial", "name": "Test Estate"},
                    center=(76.305, 9.975),
                ),
                node(16, 76.32, 9.99, {"monitoring:air_quality": "yes", "name": "Test Air Sensor"}),
                way(17, [(76.28, 200), (76.29, 9.96)], {"highway": "secondary"}),
            ],
        }

        layers, qa = parse_osm_layers(payload)

        self.assertEqual(len(layers["roads"]), 1)
        self.assertEqual(len(layers["transit"]), 1)
        self.assertEqual(len(layers["waterways"]), 1)
        self.assertEqual(len(layers["healthcare"]), 1)
        self.assertEqual(len(layers["emergency"]), 1)
        self.assertEqual(len(layers["industry"]), 1)
        self.assertEqual(len(layers["air_monitors"]), 1)
        self.assertEqual(layers["industry"][0]["geometry"]["type"], "Polygon")
        self.assertEqual(layers["air_monitors"][0]["properties"]["data_status"], "PROVISIONAL")
        self.assertEqual(qa["osm_timestamp"], "2026-10-28T19:13:19Z")
        self.assertEqual(len(qa["excluded_by_layer"]["roads"]), 1)

    def test_invalid_industrial_polygon_uses_explicit_overpass_center_fallback(self):
        payload = {
            "osm3s": {"timestamp_osm_base": "2026-10-28T19:13:19Z"},
            "elements": [
                way(
                    20,
                    [(76.30, 9.97), (76.32, 9.99), (76.30, 9.99), (76.32, 9.97), (76.30, 9.97)],
                    {"landuse": "industrial"},
                    center=(76.31, 9.98),
                )
            ],
        }

        layers, _ = parse_osm_layers(payload)

        feature = layers["industry"][0]
        self.assertEqual(feature["geometry"]["type"], "Point")
        self.assertIn("failed structural QA", feature["properties"]["placement_method"])

    def test_raw_writer_refuses_to_replace_an_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "snapshot.json"
            destination.write_bytes(b"original")
            with self.assertRaises(FileExistsError):
                _write_exclusive(destination, b"replacement")
            self.assertEqual(destination.read_bytes(), b"original")

    def test_raw_snapshot_is_losslessly_gzipped_with_both_hashes(self):
        payload = {"osm3s": {"timestamp_osm_base": "2026-10-28T19:25:34Z"}, "elements": []}
        raw = json.dumps(payload).encode("utf-8")
        with tempfile.TemporaryDirectory() as folder:
            snapshot, metadata = write_raw_snapshot(
                Path(folder), "network", raw, payload, "bounded query",
                "https://overpass-api.de/api/interpreter",
                datetime(2026, 10, 28, 19, 28, tzinfo=timezone.utc),
            )

            compressed = snapshot.read_bytes()
            sidecar = snapshot.with_name("kochi_network_20261028T192800Z.metadata.json")

            self.assertEqual(snapshot.name, "kochi_network_20261028T192800Z.json.gz")
            self.assertEqual(gzip.decompress(compressed), raw)
            self.assertEqual(metadata["response_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(metadata["snapshot_file_sha256"], hashlib.sha256(compressed).hexdigest())
            self.assertEqual(json.loads(sidecar.read_text(encoding="utf-8"))["snapshot_compression"], "gzip (lossless)")

    def test_processed_layer_has_hash_checked_provenance_and_loads(self):
        feature = {
            "type": "Feature",
            "id": "way/99",
            "geometry": {
                "type": "LineString",
                "coordinates": [[76.28, 9.95], [76.29, 9.96]],
            },
            "properties": {
                "osm_type": "way",
                "osm_id": "99",
                "feature_type": "mapped road",
                "feature_name": "Test Road",
                "feature_subtype": "highway: primary",
                "source": "OpenStreetMap contributors",
                "osm_url": "https://www.openstreetmap.org/way/99",
            },
        }
        payload = {
            "source_counts_by_layer": {"roads": 1},
            "excluded_by_layer": {"roads": []},
            "duplicate_counts_by_layer": {"roads": 0},
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw_path = root / "snapshot.json"
            raw_path.write_bytes(b"fixture")
            output, metadata = _publish_processed_layer(
                root / "processed",
                "roads",
                [feature],
                {
                    "query_service_url": "https://overpass-api.de/api/interpreter",
                    "osm_timestamp": "2026-10-28T19:13:19Z",
                },
                "bounded fixture query",
                raw_path,
                hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                datetime(2026, 10, 29, tzinfo=timezone.utc),
                payload,
            )

            self.assertTrue(output.is_file())
            self.assertTrue(output.with_name(output.stem + ".metadata.json").is_file())
            self.assertEqual(metadata["validation_status"], "PROVISIONAL")
            self.assertEqual(metadata["validation"]["source_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            layers = read_processed_layers(root / "processed")
            self.assertEqual(len(layers), 1)
            self.assertEqual(layers[0]["metadata"]["logical_layer_id"], "osm_kochi_roads")

    def test_processed_layer_loader_returns_only_latest_logical_snapshot(self):
        feature = {
            "type": "Feature",
            "id": "way/100",
            "geometry": {"type": "LineString", "coordinates": [[76.28, 9.95], [76.29, 9.96]]},
            "properties": {
                "osm_type": "way", "osm_id": "100", "feature_type": "mapped road",
                "feature_name": "Snapshot road", "feature_subtype": "highway: primary",
                "source": "OpenStreetMap contributors", "osm_url": "https://www.openstreetmap.org/way/100",
            },
        }
        payload = {
            "source_counts_by_layer": {"roads": 1},
            "excluded_by_layer": {"roads": []},
            "duplicate_counts_by_layer": {"roads": 0},
        }
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            raw_path = root / "snapshot.json"
            raw_path.write_bytes(b"fixture")
            for hour in (10, 11):
                _publish_processed_layer(
                    root / "processed", "roads", [feature],
                    {
                        "query_service_url": "https://overpass-api.de/api/interpreter",
                        "osm_timestamp": f"2026-10-29T{hour}:00:00Z",
                    },
                    "bounded fixture query", raw_path,
                    hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                    datetime(2026, 10, 29, hour, tzinfo=timezone.utc), payload,
                )

            layers = read_processed_layers(root / "processed")

            self.assertEqual(len(layers), 1)
            self.assertEqual(layers[0]["metadata"]["dataset_id"], "osm_kochi_roads_20261029T110000Z")

            newest_path = root / "processed" / "spatial_layers" / "osm_kochi_roads_20261029T110000Z.geojson"
            newest_path.write_text("{}", encoding="utf-8")
            self.assertEqual(read_processed_layers(root / "processed"), [])
            issues = processed_layer_issues(root / "processed")
            self.assertTrue(any("content hash does not match" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()

"""Acquire and validate public Kochi-relevant research datasets.

Snapshots are written under data/raw/experimental and are never overwritten.
The script does not add any dataset to application inputs.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import rasterio
import shapefile
from pyproj import CRS, Transformer
from pypdf import PdfReader
from rasterio.windows import Window


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "raw" / "experimental" / "kochidata_2026-11-02"
USER_AGENT = "AI_RESILIENCE Kochi data foundation research (public read-only acquisition)"
KOCHI_POINT = (76.27, 9.93)
KOCHI_REVIEW_BOUNDS = (76.2, 9.8, 76.4, 10.2)

DATASETS: tuple[dict[str, Any], ...] = (
    {
        "id": "ksdma_kerala_flood_probability_report_2022",
        "filename": "ksdma_flood_probability_report_2022.pdf",
        "url": "https://sdma.kerala.gov.in/wp-content/uploads/2022/06/Flood-Probability-Report-2022_Final.pdf",
        "publisher": "Kerala State Disaster Management Authority (KSDMA)",
        "publication_date": "2022 report",
        "license": "No dataset-specific reuse licence found on the KSDMA hazard-map page; retain for research review only and obtain permission before redistribution.",
        "type": "pdf",
        "geographic_coverage": "Kerala districts; this is a report, not a local event geometry layer.",
        "temporal_coverage": "Historical-based and RCP 8.5 flood probability products are listed; report-specific baseline and scenario periods require document review.",
        "units": "PDF report and maps; no machine-readable depth, duration, or event-observation units asserted.",
    },
    {
        "id": "ksdma_unep_ernakulam_historical_inundation_map_2020",
        "filename": "ksdma_unep_historical_flood_inundation_map_2020.pdf",
        "url": "https://sdma.kerala.gov.in/wp-content/uploads/2022/02/Image_Final.pdf",
        "publisher": "Kerala State Disaster Management Authority (KSDMA), product credited to UNEP-KSDMA (2020)",
        "publication_date": "2020 product; linked under 2022/02",
        "license": "No dataset-specific reuse licence found on the KSDMA hazard-map page; retain for research review only and obtain permission before redistribution.",
        "type": "pdf",
        "geographic_coverage": "Kerala flood hazard map; Kochi/Ernakulam extent and georeferencing require inspection.",
        "temporal_coverage": "Historical-based inundation product; event/date definitions are not established by catalogue metadata.",
        "units": "Map; numeric pixel values, depth and duration are not asserted.",
    },
    {
        "id": "ksdma_ernakulam_historical_flood_probability_map",
        "filename": "ksdma_ernakulam_historical_flood_probability_2022.pdf",
        "url": "https://sdma.kerala.gov.in/wp-content/uploads/2022/05/Ernakulam_Hist.pdf",
        "publisher": "Kerala State Disaster Management Authority (KSDMA)",
        "publication_date": "2022 upload path; document issue date not yet confirmed",
        "license": "No dataset-specific reuse licence found on the KSDMA hazard-map page; retain for research review only and obtain permission before redistribution.",
        "type": "pdf",
        "geographic_coverage": "Ernakulam district map/report; exact Kochi municipal coverage and map georeferencing require inspection.",
        "temporal_coverage": "Historical flood-probability product; event/reference period is not stated in the reviewed catalogue metadata.",
        "units": "Map/report; no machine-readable depth, duration, or event-observation units asserted.",
    },
    {
        "id": "gsi_ernakulam_landslide_susceptibility_2022",
        "filename": "gsi_ernakulam_landslide_susceptibility_2022.zip",
        "url": "https://sdma.kerala.gov.in/wp-content/uploads/2025/08/Ernakulam.zip",
        "publisher": "Geological Survey of India (GSI), distributed by KSDMA",
        "publication_date": "GSI 2022 per KSDMA catalogue; archive uploaded under 2025/08",
        "license": "No dataset-specific reuse licence found on the KSDMA catalogue; retain for research review only and obtain permission before redistribution.",
        "type": "shapefile_zip",
        "geographic_coverage": "Ernakulam district dataset; local Kochi overlap is measured from feature geometries, not assumed.",
        "temporal_coverage": "Susceptibility mapping labelled GSI 2022; this is not event history.",
        "units": "Categorical susceptibility zones; class meanings require source documentation.",
    },
    {
        "id": "gsi_kerala_district_landslide_susceptibility_map",
        "filename": "gsi_kerala_district_landslide_susceptibility_2022.pdf",
        "url": "https://sdma.kerala.gov.in/wp-content/uploads/2025/06/Landslide_Susceptibility_Zones_Districts_FINAL.pdf",
        "publisher": "Geological Survey of India (GSI), published by KSDMA",
        "publication_date": "GSI 2022 per KSDMA catalogue; PDF uploaded under 2025/06",
        "license": "No dataset-specific reuse licence found on the KSDMA catalogue; retain for research review only and obtain permission before redistribution.",
        "type": "pdf",
        "geographic_coverage": "District maps for Kerala; map scale and Kochi-specific coverage require document inspection.",
        "temporal_coverage": "GSI 2022 susceptibility mapping; not event history.",
        "units": "Categorical susceptibility zones; class definitions require source documentation.",
    },
    {
        "id": "copernicus_dem_glo30_kochi_tile",
        "filename": "copernicus_dem_glo30_N09E076.tif",
        "url": "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N09_00_E076_00_DEM/Copernicus_DSM_COG_10_N09_00_E076_00_DEM.tif",
        "publisher": "Copernicus DEM, Copernicus Programme; distributed via AWS Open Data Registry",
        "publication_date": "GLO-30 Public 2021 release",
        "license": "Copernicus DEM licence; see https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM",
        "type": "geotiff_dem",
        "geographic_coverage": "Tile N09E076; suitability for Kochi is checked against the raster bounds.",
        "temporal_coverage": "Static 2021 digital surface model.",
        "units": "Elevation values; vertical units/reference are checked from raster metadata and product documentation.",
    },
    {
        "id": "esa_worldcover_2021_v200_kochi_tile",
        "filename": "esa_worldcover_10m_2021_v200_N09E075_Map.tif",
        "url": "https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_N09E075_Map.tif",
        "publisher": "European Space Agency (ESA) WorldCover consortium",
        "publication_date": "2021 map, v200 released October 2022",
        "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "type": "geotiff_landcover",
        "geographic_coverage": "Tile coverage is read from the GeoTIFF; Kochi overlap is tested, not inferred from the tile filename.",
        "temporal_coverage": "2021 land-cover classification.",
        "units": "Categorical class codes; class definitions follow the ESA WorldCover product documentation.",
    },
    {
        "id": "worldpop_india_2025_population_100m",
        "filename": "worldpop_india_2025_constrained_100m_R2025A_v1.tif",
        "url": "https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/IND/v1/100m/constrained/ind_pop_2025_CN_100m_R2025A_v1.tif",
        "publisher": "WorldPop, University of Southampton and partner institutions",
        "publication_date": "R2025A release; 2025 population estimate",
        "license": "Dataset-specific licence not established from the inspected summary; preserve for local review only and obtain confirmation before redistribution or integration.",
        "type": "geotiff_population",
        "geographic_coverage": "India country raster; Kochi overlap is tested from the raster bounds.",
        "temporal_coverage": "2025 modelled population estimate.",
        "units": "Estimated persons per 100 m grid cell per WorldPop dataset summary.",
    },
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(dataset: dict[str, Any]) -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / dataset["filename"]
    if path.exists():
        return path
    partial = path.with_suffix(path.suffix + ".part")
    request = urllib.request.Request(
        dataset["url"], headers={"User-Agent": USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            if response.status != 200:
                raise RuntimeError(
                    f"Unexpected HTTP status {response.status} for {dataset['id']}."
                )
            with partial.open("xb") as target:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    target.write(chunk)
            content_type = response.headers.get("Content-Type", "")
            expected_length = response.headers.get("Content-Length")
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    if not partial.is_file() or partial.stat().st_size == 0:
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"Empty download for {dataset['id']}.")
    if expected_length and partial.stat().st_size != int(expected_length):
        partial.unlink(missing_ok=True)
        raise RuntimeError(
            f"Download length mismatch for {dataset['id']}: "
            f"{partial.stat().st_size} != {expected_length}."
        )
    partial.replace(path)
    dataset["_content_type"] = content_type
    return path


def _validate_pdf(path: Path) -> dict[str, Any]:
    if path.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError(f"File is not a PDF: {path.name}.")
    reader = PdfReader(str(path), strict=True)
    if reader.is_encrypted:
        raise RuntimeError(f"PDF is encrypted: {path.name}.")
    page_sizes = [
        {
            "width_points": round(float(page.mediabox.width), 2),
            "height_points": round(float(page.mediabox.height), 2),
        }
        for page in reader.pages
    ]
    return {
        "pdf_page_count": len(reader.pages),
        "pdf_metadata": {
            str(key): str(value) for key, value in (reader.metadata or {}).items()
        },
        "page_sizes": page_sizes[:10],
        "geospatial_viewports_present": any(
            "/VP" in page for page in reader.pages
        ),
        "coverage_status": "Document map extent needs geospatial inspection; district title alone is not a spatial validation.",
    }


def _validate_shapefile_zip(path: Path) -> dict[str, Any]:
    roi_minx, roi_miny, roi_maxx, roi_maxy = KOCHI_REVIEW_BOUNDS
    archive = zipfile.ZipFile(path)
    bad_member = archive.testzip()
    if bad_member:
        raise RuntimeError(f"ZIP CRC check failed for {bad_member}.")
    shp_names = [
        name
        for name in archive.namelist()
        if name.casefold().endswith(".shp") and not name.endswith("/")
    ]
    if not shp_names:
        raise RuntimeError("Shapefile archive contains no .shp member.")
    layers: list[dict[str, Any]] = []
    for shp_name in shp_names:
        stem = shp_name[:-4]
        members = {member.casefold(): member for member in archive.namelist()}
        dbf_name = members.get((stem + ".dbf").casefold())
        shx_name = members.get((stem + ".shx").casefold())
        prj_name = members.get((stem + ".prj").casefold())
        if not dbf_name or not shx_name or not prj_name:
            raise RuntimeError(f"Incomplete shapefile sidecars for {shp_name}.")
        crs = CRS.from_wkt(archive.read(prj_name).decode("utf-8", errors="replace"))
        transformer = Transformer.from_crs(crs, CRS.from_epsg(4326), always_xy=True)
        with archive.open(shp_name) as shp, archive.open(dbf_name) as dbf, archive.open(shx_name) as shx:
            reader = shapefile.Reader(
                shp=io.BytesIO(shp.read()),
                dbf=io.BytesIO(dbf.read()),
                shx=io.BytesIO(shx.read()),
            )
        bounds = tuple(float(value) for value in reader.bbox)
        xs = (bounds[0], bounds[2])
        ys = (bounds[1], bounds[3])
        transformed = [
            transformer.transform(x, y)
            for x in xs
            for y in ys
        ]
        wgs84_bounds = (
            min(point[0] for point in transformed),
            min(point[1] for point in transformed),
            max(point[0] for point in transformed),
            max(point[1] for point in transformed),
        )
        intersects_kochi = (
            wgs84_bounds[0] <= roi_maxx
            and wgs84_bounds[2] >= roi_minx
            and wgs84_bounds[1] <= roi_maxy
            and wgs84_bounds[3] >= roi_miny
        )
        invalid_shape_count = 0
        shape_types: set[int] = set()
        for shape in reader.iterShapes():
            shape_types.add(int(shape.shapeType))
            if len(shape.points) and not all(
                math.isfinite(float(coordinate))
                for point in shape.points
                for coordinate in point[:2]
            ):
                invalid_shape_count += 1
        layers.append(
            {
                "layer": shp_name,
                "feature_count": len(reader),
                "geometry_type_codes": sorted(shape_types),
                "crs_wkt": crs.to_wkt(),
                "source_bounds": bounds,
                "wgs84_bounds_from_extent_corners": wgs84_bounds,
                "intersects_approximate_kochi_bounds": intersects_kochi,
                "fields": [field[0] for field in reader.fields[1:]],
                "nonfinite_coordinate_features": invalid_shape_count,
                "topology_validation": "Coordinate finiteness checked; polygon topology not independently validated.",
            }
        )
    return {
        "zip_crc": "passed",
        "layers": layers,
        "coverage_basis": "Feature-layer extent transformed from declared CRS and compared to approximate Kochi review bounds; not a legal municipal boundary.",
    }


def _validate_geotiff(path: Path, dataset: dict[str, Any]) -> dict[str, Any]:
    with rasterio.open(path) as source:
        if source.crs is None:
            raise RuntimeError(f"GeoTIFF has no CRS: {path.name}.")
        bounds = source.bounds
        point_inside = (
            bounds.left <= KOCHI_POINT[0] <= bounds.right
            and bounds.bottom <= KOCHI_POINT[1] <= bounds.top
        )
        window_stats: dict[str, Any] | None = None
        if point_inside:
            row, col = source.index(*KOCHI_POINT)
            half = 50
            window = Window(
                max(0, col - half),
                max(0, row - half),
                min(source.width, col + half) - max(0, col - half),
                min(source.height, row + half) - max(0, row - half),
            )
            values = source.read(1, window=window, masked=True)
            valid = values.compressed()
            window_stats = {
                "window_shape": list(values.shape),
                "valid_cell_count": int(valid.size),
                "nodata_cell_count": int(values.size - valid.size),
                "valid_min": float(valid.min()) if valid.size else None,
                "valid_max": float(valid.max()) if valid.size else None,
                "unique_values_sample": (
                    [int(value) for value in sorted(set(valid.tolist()))[:32]]
                    if dataset["type"] == "geotiff_landcover" and valid.size
                    else None
                ),
            }
        return {
            "driver": source.driver,
            "width_pixels": source.width,
            "height_pixels": source.height,
            "band_count": source.count,
            "dtype": list(source.dtypes),
            "crs": source.crs.to_string(),
            "bounds": [bounds.left, bounds.bottom, bounds.right, bounds.top],
            "pixel_size": list(source.res),
            "nodata": source.nodata,
            "block_shapes": [list(shape) for shape in source.block_shapes],
            "kochi_reference_point_inside_raster": point_inside,
            "kochi_approximate_bounds_overlap": (
                bounds.left <= KOCHI_REVIEW_BOUNDS[2]
                and bounds.right >= KOCHI_REVIEW_BOUNDS[0]
                and bounds.bottom <= KOCHI_REVIEW_BOUNDS[3]
                and bounds.top >= KOCHI_REVIEW_BOUNDS[1]
            ),
            "sample_window_near_kochi_reference_point": window_stats,
            "value_semantics": {
                "geotiff_landcover": "Categorical ESA WorldCover class code; class meanings must follow the product class legend.",
                "geotiff_dem": "Digital surface elevation values; vertical units/reference and suitability for urban drainage require separate confirmation.",
                "geotiff_population": "WorldPop modelled/constrained population estimate per grid cell; not a census observation or household count.",
            }[dataset["type"]],
        }


def validate(path: Path, dataset: dict[str, Any]) -> dict[str, Any]:
    kind = dataset["type"]
    if kind == "pdf":
        return _validate_pdf(path)
    if kind == "shapefile_zip":
        return _validate_shapefile_zip(path)
    if kind in {"geotiff_dem", "geotiff_landcover", "geotiff_population"}:
        return _validate_geotiff(path, dataset)
    raise ValueError(f"Unsupported dataset type: {kind}")


def acquire() -> list[dict[str, Any]]:
    results = []
    for dataset in DATASETS:
        path = _download(dataset)
        qa = validate(path, dataset)
        metadata = {
            key: value
            for key, value in dataset.items()
            if not key.startswith("_")
        }
        metadata.update(
            {
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "local_file": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
                "http_content_type": dataset.get("_content_type"),
                "verification_status": "downloaded_and_structurally_inspected_research_only",
                "quality_validation": qa,
                "not_integrated_reason": (
                    "Dataset-specific license, resolution, source semantics, or fit for local consequence analysis "
                    "remains insufficient; the snapshot is not an application input."
                ),
            }
        )
        sidecar = path.with_name(path.name + ".metadata.json")
        if sidecar.exists():
            existing = json.loads(sidecar.read_text(encoding="utf-8"))
            if existing.get("sha256") != metadata["sha256"]:
                raise RuntimeError(f"Refusing to overwrite conflicting sidecar: {sidecar}.")
            metadata = existing
        else:
            sidecar.write_text(
                json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        results.append(
            {
                "dataset_id": dataset["id"],
                "local_file": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": metadata["sha256"],
                "verification_status": metadata["verification_status"],
                "quality_validation": qa,
            }
        )
    return results


if __name__ == "__main__":
    for item in acquire():
        print(json.dumps(item, ensure_ascii=False, sort_keys=True))

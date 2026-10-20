# Kochi map reference data

## Kochi Corporation boundary

- File: `kochi_corporation_boundary.geojson`
- Feature: one Polygon, named `Kochi Corporation Boundary` (Ernakulam)
- Upstream layer named by the dataset README: Kerala OpenSDI, `KSUDP_KCH_Corporation_Boundary`
- Download location: [DataMeet Municipal Spatial Data, Kochi](https://github.com/datameet/Municipal_Spatial_Data/tree/master/Kochi)
- Source service: [Kerala OpenSDI layer](https://opensdi.kerala.gov.in/layers/opensdi_data:geonode:KSUDP_KCH_Corporation_Boundary)
- Retrieval date: 2026-10-20
- Source publication/update date: not stated in the file or Kochi README; current legal boundary currency is not verified.
- Coordinate reference: GeoJSON longitude/latitude, interpreted as WGS 84 / EPSG:4326. There is no embedded `crs` member. Coordinates range from 76.2373589 to 76.3400293 east and 9.8897183 to 10.0497693 north.
- Positional accuracy / source map scale: not stated in the available file or README.
- Licence: the dataset-specific Kochi README states Creative Commons Attribution-ShareAlike 2.5 India (CC BY-SA 2.5 IN). Retain attribution and share-alike terms for redistribution/adaptations.
- Attribution: DataMeet Municipal Spatial Data / Pune chapter of DataMeet Trust; original layer attributed by that README to Kerala OpenSDI (`KSUDP_KCH_Corporation_Boundary`).
- Limitations: the source service was not reachable during this review; this is a community-repackaged copy, not verified against the live service. It is a single administrative polygon, not a hazard, exposure, or vulnerability layer, and should not be used as legal boundary evidence.
- SHA-256: `02e3217959ed1edef2c91d852305e86d1d7ff55a90971a8f61fcd3a9ce0dcdbf`

## Not integrated

The Kochi Corporation page for DataMeet states its ward GeoJSON reflects 2022, but the file was not downloaded or independently validated in this milestone. Kerala LRIS lists road and drainage/canal layers, while KSDMA lists flood-return rasters and GSI 2022 landslide shapefiles for Ernakulam. Dataset-level CRS, date/version and reuse terms were not all verifiable from the accessible catalogue pages, so these datasets remain unavailable in the application. The existing sample hospital and facility coordinates are not used as map data.

See [`SPATIAL_DATA_FOUNDATION.md`](SPATIAL_DATA_FOUNDATION.md) and
[`spatial_sources.json`](spatial_sources.json) for the expanded source inventory,
reuse/CRS/date metadata, blockers, and reusable validation/ingestion procedure.
The topology validator detects a local self-intersection in the retained
provisional boundary ring. Its original file and hash are preserved; it is shown
only for orientation and is not treated as a valid spatial coverage mask.

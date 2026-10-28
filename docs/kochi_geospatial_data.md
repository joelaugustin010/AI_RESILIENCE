# Kochi geospatial data status

Reviewed 2026-10-28. This note records the source, license, geographic extent,
validation result, and intended use of the map layers. A structurally valid file
is not proof that a community or government dataset is complete or ground-truth
accurate.

## Current map layers

| Layer | Status | Accepted features | Source snapshot | Map use and limits |
| --- | --- | ---: | --- | --- |
| Kochi Corporation administrative outline | PROVISIONAL | 1 | Existing project copy | Orientation only. The polygon self-intersects; it is not a validated coverage mask or legal boundary. |
| Kochi wards, DataMeet 2022 | PROVISIONAL | 74 of 77 | Existing project copy | Context only. Three invalid polygons are excluded; ward attributes and full current coverage are incomplete or unverified. CC BY-SA 2.5 India. |
| OSM selected roads | PROVISIONAL | 13,123 lines | OSM database 2026-10-28 19:25:34 UTC | Selected routable highway classes within the provisional boundary's numeric extent. Not a complete road register, condition survey, access, or travel-time layer. |
| OSM rail and transit ways | PROVISIONAL | 442 lines | OSM database 2026-10-28 19:25:34 UTC | Selected rail/transit tags in the Ernakulam urban query window; not a complete public transport network or timetable. |
| OSM waterways and drainage-like ways | PROVISIONAL | 2,568 lines | OSM database 2026-10-28 19:25:34 UTC | River, canal, stream, drain, and ditch tags in the urban query window. Drain/ditch tags are not a municipal asset register and do not describe capacity or condition. |
| OSM healthcare | PROVISIONAL | 680 (471 points, 209 polygons) | OSM database 2026-10-28 19:27:36 UTC | Community-mapped facilities only; identity, services, current operation, and completeness are not authenticated. |
| OSM emergency facilities | PROVISIONAL | 105 (44 points, 61 polygons) | OSM database 2026-10-28 19:27:36 UTC | Community-mapped fire/police/emergency features only; operating status and response capability are unknown. |
| OSM industrial features | PROVISIONAL | 313 (76 points, 237 polygons) | OSM database 2026-10-28 19:27:36 UTC | Tagged works/industrial features, not a verified factory, consent, or emissions inventory. Proximity does not establish pollution causation. |
| OSM air-quality monitors | UNAVAILABLE | 0 | OSM database 2026-10-28 19:27:36 UTC | No explicitly air-quality-tagged object was returned in the bounded snapshot. This does not show that monitoring stations do not exist. |
| JRC/Copernicus GloFAS RP100 river flood preview | PROVISIONAL | Raster preview | Existing project copy | Modeled scenario context at about 90 m, not an observation, forecast, warning, or site-specific risk estimate. Transparent pixels do not establish safety. CC BY 4.0 attribution and change indication apply. |

The map displays the OSM groups independently. They start hidden to keep the
initial map responsive. Each OSM GeoJSON sidecar records source query and hash,
database and retrieval timestamps, feature counts, CRS, coverage, licence,
attribution, and limitations. The exact response bodies used for this acquisition
are committed losslessly as gzip files with raw-response and compressed-file
checksums. Future raw outputs remain ignored until reviewed. The loader validates
each candidate and shows only the newest snapshot for a logical layer; if that
newest file fails its hash check, the map does not silently fall back to an older
snapshot.

## Acquisition method

Run `python scripts/acquire_kochi_osm_layers.py --retries 2` from the repository
root when network access to a public Overpass endpoint is available. The script
uses bounded, explicit tag queries; preserves each raw response and SHA-256
sidecar; validates coordinates, geometry, required properties, and provenance;
and refuses to overwrite timestamped outputs. It records empty categories as
unavailable and continues if one thematic query fails. It does not repair,
clip, or assign features to the self-intersecting boundary.

The roads window is the numeric extent of the provisional Kochi Corporation
boundary: south `9.88971828`, west `76.23735890`, north `10.04976931`, east
`76.34002933`. It selects motorway, trunk, primary, secondary, tertiary,
unclassified, residential, and living-street ways. The separate Ernakulam
urban window for transit, waterways, and facilities is south `9.85`, west
`76.15`, north `10.20`, east `76.45`. It selects rail/light-rail/tram/subway,
river/canal/stream/drain/ditch, tagged healthcare and emergency features,
industrial/works tags, and explicit air-monitor tags. Windows are query bounds,
not administrative boundaries. Long ways can extend beyond a query window.

The data comes from [OpenStreetMap](https://www.openstreetmap.org/), retrieved
through the public [Overpass API](https://dev.overpass-api.de/overpass-doc/en/).
OSM data is under the [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/);
retain the attribution [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright)
and applicable share-alike terms. The layer metadata includes the query endpoint
and exact query so a later snapshot can be reproduced.

## Data not suitable for the requested spatial analyses

| Dataset | Status | Reason |
| --- | --- | --- |
| NIHFW National Hospital Directory | UNSUITABLE FOR ANALYSIS | The 180-row Ernakulam review has 31 missing/nonnumeric coordinate pairs and 18 repeated-pair groups covering 63 rows. The source does not define coordinate order, CRS/datum, or location accuracy. The CSV remains review-only; no points were made. The record is published under GODL-India. |
| KSPCB/CPCB air observations joined to station points | UNSUITABLE FOR ANALYSIS | Dated source-reported AQI/pollutant records exist in the project, but station identifiers/coordinates, coordinate reference, exact averaging intervals, and completeness fields are not consistently available. The KSPCB read-only public station-points request returned HTTP 403. The CPCB OGD catalogue requires an API key for resource access; its attempted API route returned HTTP 503. No access restriction was bypassed. |
| KSPCB industrial facilities as mapped assets | UNSUITABLE FOR ANALYSIS | Public industry/consent references do not establish current, georeferenced facility locations or measured emissions. An estate map is not joined to individual firms. |
| Kerala LRIS road and drainage extracts | UNAVAILABLE | The official [LRIS catalogue](https://lris.kslub.kerala.gov.in/) lists relevant themes, but a directly downloadable Kochi layer with dataset-specific schema, CRS, date, and reuse terms was not verified. OSM waterways do not substitute for drainage assets. |
| KSDMA historical flood return-probability rasters | UNSUITABLE FOR ANALYSIS | The [KSDMA catalogue](https://sdma.kerala.gov.in/hazard-maps/) links an archive that was downloaded and inspected, but dataset-level reuse terms and pixel/NoData semantics are absent. It is retained raw and is not rendered, thresholded, polygonized, or overlaid. |
| Other KSDMA/GSI hazard boundaries | UNAVAILABLE | No validated and appropriately reusable Kochi/Ernakulam geometry was acquired. |

KSPCB's [ambient monitoring page](https://kspcb.kerala.gov.in/activities/ambient-monitoring)
lists Ernakulam monitoring locations, and its [IPAM air-quality dashboard](https://www.kspcbipam.kerala.gov.in/Dashboard/airQuality)
describes network cadence and pollutants. These references do not supply a
verified station geometry table for map joining. The [CPCB OGD real-time AQI
catalogue](https://www.data.gov.in/catalog/real-time-air-quality-index) is an
official source reference; no API key or bypass was used. Existing air-pollution
tables and page remain available, but this map makes no station comparison,
spatial interpolation, AQI recalculation, or factory source attribution.

## Analysis supported by current data

No asset-to-hazard exposure, road-access, hospital-proximity, pollution
interpolation, or industrial source-attribution analysis is supported. The
existing exposure interface reports unknown/unassessable exposure when it has
no compatible validated asset and vector hazard layers. The JRC image preview
is contextual raster display, not a vector overlay. Counts and geometry checks
are QA summaries, not risk estimates. No distance, area, flood depth at an
asset, probability, vulnerability, or safety conclusion is derived from OSM.

## Existing layers and project behavior preserved

The merged Kochi PyDeck serialization fix remains in place: the JRC bitmap is
serialized as a literal Data URL, with its original geographic bounds. Existing
boundary and ward layers remain available, and the air-pollution page and its
source-linked reports are unchanged. Relevant source and acquisition records
also remain in `data/reference/spatial_sources.json`,
`data/reference/air_quality_acquisition.json`, and
`data/reference/SPATIAL_DATA_FOUNDATION.md`.

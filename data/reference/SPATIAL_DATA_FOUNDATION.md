# Kochi spatial data foundation

Reviewed 2026-10-20. Source URLs, publishers, retrieval/publication-date status,
reuse terms, CRS, units, coverage, limitations, and blockers are recorded in
[`spatial_sources.json`](spatial_sources.json). Entries marked `candidate_not_ingested`
are leads, not map data. The provisional boundary is the only local polygon in
the map catalog; it is an administrative outline, not a hazard or exposure layer.

## Existing data inventory

- `data/reference/kochi_corporation_boundary.geojson`: one provisional Kochi
  Corporation polygon, with its local source notes and pinned SHA-256 in the
  adjacent metadata JSON. It has no explicit CRS member; the source documentation
  interprets its coordinates as WGS 84 / EPSG:4326. The structural topology
  validator detects a local self-intersection in its ring; the file is retained
  byte-for-byte and can still be shown as an orientation reference, but is not
  accepted as a validated coverage mask for ingestion QA.
- `data/raw/Ernakulam_map_dataset_draft.zip`: draft OCR/text extracts from an
  Ernakulam flood-map PDF. Its own README says parsed exposure table alignment
  must be checked against the PDF. The original PDF is not present and this ZIP
  contains no hazard polygons, so none of its rows are mapped or used for overlay.
- `data/raw/hospital_vulnerability_data.csv` and `air_pollution_data.csv`:
  five-row sample files with undocumented coordinates/source claims; not GIS
  assets and not used for spatial exposure.
- `data/raw/kerala.csv`, the manual rainfall file, and the manual/telemetry river
  files are measurement tables, not infrastructure geometries. Their known QA
  warnings remain active in the application.
- There is no verified Kochi facility inventory, industrial-unit point layer,
  monitoring-station point layer, road/drainage geometry, or hazard polygon/raster
  in the checked-in processed spatial data.

## Source review and what is blocked

The official [KSDMA hazard-map catalogue](https://sdma.kerala.gov.in/hazard-maps/)
links Ernakulam historic and RCP 8.5 flood PDFs, Kerala-wide historic and RCP 8.5
flood-return-probability raster ZIPs, and an Ernakulam GSI (2022) landslide
susceptibility ZIP. On 2026-10-20, the historical 10/25/50-year raster ZIP was
downloaded from the catalogue's linked endpoint and CRC-checked. The untouched
archive is `data/raw/ksdma_flood_return_probability_historical_10_25_50.zip`
(SHA-256 `4057b36cdfc467ecaf618afb1e74b725187ef1d2a20326cdc1e4eb32df54605e`);
its acquisition metadata is in the adjacent `.metadata.json` file. It contains
three single-band 3004×5371 float32 GeoTIFFs, each with an explicit EPSG:4326
GeoKey, labeled historical 10-, 25-, and 50-year products. The raster grid spans
approximately 74.8646–77.3680 E and 8.2909–12.7667 N; these are grid bounds, not
the mapped flood footprint. The catalogue identifies historic/return-probability
products. Each main TIFF declares GDAL_NODATA=-3.402823e38, but valid pixel
units/meaning, NoData interpretation, and dataset-level reuse terms remain
undocumented. The archive is therefore preserved but not unpacked into
processed data, rendered, thresholded, or used for exposure analysis.
Return-period labels are not an event forecast or observed flood depth. The
2026-10-29 review confirmed the ZIP CRC and recorded valid-value ranges in the
source metadata sidecar without interpreting or modifying those values.

The official [Kerala LRIS 2.0 catalogue](https://lris.kslub.kerala.gov.in/),
maintained by the Land Use Department, lists a road network, drainage lines, and
canals. The accessible catalogue did not provide a Kochi extract with per-layer
date, CRS, schema, and reuse terms. Do not assume its drainage inventory is a
municipal storm-drain asset register.

The Government of India [National Hospital Directory](https://www.data.gov.in/resource/national-hospital-directory-geo-code-and-additional-parameters-updated-till-last-month)
is published by NIHFW on data.gov.in; its portal record states Government Open
Data License - India (GODL-India) and describes `Location_Coordinates`. The
portal says published 2017-08-10 and updated 2025-06-02. The raw CSV was obtained
from the portal's linked file endpoint (`data/raw/nihfw_national_hospital_directory.csv`,
SHA-256 `1ddcad9f9b922142a4374c7b89b70fb6cefd8a257448c70a61e1c07d98845134`;
10,341,256 bytes) and remains unchanged. A review-only Ernakulam CSV is at
`data/processed/nihfw_ernakulam_hospitals_coordinate_review.csv`; it retains
source coordinates as text and adds QA flags, without assigning coordinate order,
CRS, or geometry. The filtered subset has 180 records: 149 parse as two finite
numbers and 31 do not; 18 exact repeated coordinate-pair groups contain 63
records. Numeric range checks alone cannot establish valid locations. The source
does not document coordinate order, CRS/datum, or row-level positional quality,
so the records are not plotted and cannot be used in exposure calculations until
the provider confirms those semantics and location QA is completed. GODL-India
requires attribution; the portal links its [reuse terms](https://www.data.gov.in/Godl).

The DataMeet [Kochi municipal repository](https://github.com/datameet/Municipal_Spatial_Data/tree/master/Kochi)
lists `KCH_wards.geojson`, described as wards as of 2022 and scraped from Kerala
OpenSDI's `KSUDP_KCH_Ward_Boundary`. Its dataset-specific README states CC BY-SA
2.5 India terms. We obtained the file on 2026-10-20 from the
[documented raw file endpoint](https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Kochi/KCH_wards.geojson).
The README and [source file page](https://github.com/datameet/Municipal_Spatial_Data/blob/master/Kochi/KCH_wards.geojson)
support the publisher, upstream attribution, vintage and licence claims. The
source uses GeoJSON coordinate semantics (WGS 84 longitude/latitude, decimal
degrees, per [RFC 7946](https://datatracker.ietf.org/doc/html/rfc7946)); the file
does not embed an explicit CRS member.

The exact raw snapshot is preserved at `data/raw/koch_wards_2022.geojson`
(SHA-256 `d8de90012f5c785b9d63c4b6f0b8bee69c72125da828051934de159d8f80dc17`)
with provenance in `data/raw/koch_wards_2022.metadata.json`. It contains 77
newline-delimited Polygon Features with coordinate bounds 76.2373589–76.3400293
E, 9.8934161–10.0497693 N. Three polygons self-intersect, so the processed map
copy excludes them and reports the exclusions. The other 74 geometries pass the
project's structural checks. Six source rows have no `Ward_No` or `Ward_Name`;
they remain in the processed copy with missing values reported. No identifiers
are inferred. The processed copy is
`data/processed/spatial_layers/kochi_wards_datameet_2022.geojson`; its sidecar
records source and processed hashes, counts, validation, and exclusions.

This is a **partial contextual ward layer**, not an authoritative current/legal
boundary, validated completeness mask, hazard layer, or exposure input. The
source's scale, positional accuracy, full current coverage, and exact publication
date are unstated, and its live OpenSDI service was not cross-checked. We found
the attributed upstream Kerala OpenSDI corporation-boundary layer, but did not
obtain a separately validated corrected boundary. The existing provisional
boundary is unchanged and remains excluded from coverage validation because of
its self-intersection.

The [KSPCB IPAM industry dashboard](https://www.kspcbipam.kerala.gov.in/Dashboard/Industry)
identifies itself as a KSPCB portal and refers to industry records from
keralapcbonline.com, but no stable openly licensed facility-geometry export was
verified. Consent/category records alone are not measured emissions and do not
establish pollution causation.

The [CPCB AQI portal](https://airquality.cpcb.gov.in/AQI_India/) is an official
monitoring reference. A stable station-coordinate GIS extract and dataset-level
reuse terms were not verified. AQI values cannot identify a factory or pollutant
source by themselves.

## Air-quality acquisition review (2026-10-20)

The official [KSPCB ambient monitoring page](https://www.kspcb.kerala.gov.in/activities/ambient-monitoring?lang=ml)
lists the Ernakulam NAMP stations used in `data/reference/air_quality_acquisition.json`:
Irumpanam, Eloor, Kalamessery and Udyogamandal (industrial), M.G. Road and Vyttila
(commercial), and Ernakulam South (residential). The [KSPCB IPAM air-quality page](https://www.kspcbipam.kerala.gov.in/Dashboard/airQuality)
describes manual NAMP/SAMP sampling on 8–11 days per month and CAAQMS as 24×7;
it names PM10, PM2.5, SO2, CO, NO, NO2, NOx, NH3 and O3 as CAAQMS parameters.
These are source-reported network facts, not observations ingested by the app.

Acquisition attempts did not yield a verified observation file. The KSPCB e-library
catalogues AQI daily averages and CAAQMS/NAMP reports, but its endpoint returned
502 in the web fetcher and direct workspace HTTPS requests failed before an HTTP
response. The public IPAM render had no dated downloadable Kochi observation table.
The [CPCB OGD real-time AQI catalog](https://www.data.gov.in/catalog/real-time-air-quality-index)
identifies CPCB/MoEFCC, lists pollutant families, and says the resource is released
under NDSAP; its API details require generating an API key and the catalog view
contains no measurement rows. No key was available, so no API call was made.
KSPCB page-level reuse terms for measurement downloads were not established; CPCB's
catalog states the Government Open Data License-India applies to published resources,
but the inaccessible resource schema and specific data could not be checked.

No pollutant-specific observations, monitor coordinates, CRS, time-aligned weather,
or verified facility/emissions dataset were acquired. Consequently the pollution
page does not rank or analyze the undocumented illustrative
`data/raw/air_pollution_data.csv`. Factory source attribution remains unavailable.
The page displays only the source-linked KSPCB station inventory and acquisition
blockers. The full details and limitations are in
`data/reference/air_quality_acquisition.json`.

The Geofabrik alternative considered for hospital/critical infrastructure offers
OpenStreetMap data under ODbL, but the verified India extract is a 1.6 GB PBF and
the workspace currently lacks a successful network download path. It would also
be community-mapped rather than authoritative. No hospital points were therefore
created; NIHFW coordinate semantics remain unresolved and exposure stays unknown.

OpenStreetMap is a possible community-mapped fallback, under ODbL with
attribution/share-alike obligations, but its coverage is not authoritative or
complete. On 2026-10-20, the official OSM map API rejected the Kochi-area bbox
because it exceeded its 50,000-node response cap (the smaller trial also failed).
The main Overpass endpoint returned HTTP 502 with its workers/queue at capacity;
an alternative endpoint did not produce a completed file. No OSM snapshot was
obtained. If later used, record its timestamp, query/area, attribution, and
per-feature limitations.

## Acquisition milestone: flood and hospital sources (2026-10-20)

The downloaded KSDMA raster and NIHFW directory are not compatible verified
spatial layers: the KSDMA archive lacks dataset-level reuse terms and raster
pixel/NoData definitions; the hospital directory lacks coordinate order and CRS
and has material coordinate-quality issues. Therefore **no real-world
hazard–asset exposure analysis has been completed**. The map reports these
acquisition/validation states and continues to label exposure unknown when no
compatible hazard layer is available. It does not treat no detected intersection
as proof of safety. Request from KSDMA the reuse permission, raster band units or
class interpretation, meaning/application of its declared NoData sentinel, and
method/report explaining the 10/25/50-year products. Request from NIHFW the coordinate order, CRS/datum,
geocoding method/accuracy, and corrected duplicate/missing or clearly invalid
hospital coordinates. Until then, do not convert the review CSV to points.

## Reusable local ingestion

`src/spatial_data.py` accepts GeoJSON Feature or FeatureCollection documents in
documented WGS 84 / EPSG:4326, and includes a dedicated normalizer for sources
that store one Feature JSON object per line. It checks provenance fields, file
format, geometry structure and ring validity, coordinate bounds, missing
properties, duplicate features/IDs, and intersection with an optional supplied
coverage polygon. For line-delimited input, it keeps the raw source unchanged,
normalizes a processed copy to a FeatureCollection, and records every invalid
geometry excluded from that view. Accepted/normalized copies go to
`data/processed/spatial_layers/` with provenance and validation sidecars. Other
CRSs and non-GeoJSON inputs are rejected; no CRS is guessed.

The built-in topology checks are intentionally lightweight pure Python and do
not replace a full GEOS/QGIS validation pass for complex, large, or operational
datasets. Ring self-crossings/zero-area, coordinate ranges, holes, and common
point/line/polygon intersections are checked. Do not use this prototype alone to
certify legal boundaries or operational exposure layers; custodians/GIS staff
should independently verify those before decision use.

Example after the source owner and metadata have been verified:

```powershell
python -m src.spatial_data path\to\verified_layer.geojson `
  --metadata path\to\verified_layer.metadata.json `
  --coverage-geojson path\to\validated_city_boundary.geojson
```

Validation only:

```powershell
python -m src.spatial_data path\to\verified_layer.geojson `
  --metadata path\to\verified_layer.metadata.json `
  --coverage-geojson path\to\validated_city_boundary.geojson --validate-only
```

Intersection is topological in longitude/latitude coordinates; boundary contact
counts as intersection. It does not calculate distances or areas. For each asset,
exposure output distinguishes an intersection, no detected intersection within
the supplied hazard layer, and unknown exposure when no compatible hazard layer
is available. Neither of the latter statuses means an asset is safe.

## Current next data request

Ask the relevant custodians for machine-readable copies plus data dictionaries,
CRS, coordinate order/units, publication and update dates, licence/reuse terms,
coverage, positional accuracy, and stable identifiers: KSDMA for flood and GSI
layers, Kerala Land Use Department for roads/drainage, NIHFW for the hospital
directory metadata, KSPCB for industrial records, and CPCB/KSPCB for station
coordinates. Until received and validated, these layers remain unavailable.

## Acquisition milestone: first Kochi flood-hazard preview (2026-10-20)

Two JRC/Copernicus GloFAS v2.1.2 RP100 depth tiles were downloaded for the
Kochi latitude band: `data/raw/jrc_glofas_rp100_ID185_N20_E70_depth.tif` and
`data/raw/jrc_glofas_rp100_ID186_N10_E70_depth.tif`. The source README documents
global land coverage, 3 arc-second (~90 m) resolution, water depth in metres,
and WGS84. It specifies ODbL 1.0; the linked JRC copyright notice specifies
CC BY 4.0 with attribution and indication of changes. No source statement
clarifying precedence or dual application was found. The dataset is provisional
and requires written licence clarification before redistribution or public
display. The GeoTIFFs report EPSG:4326, 11999x11999 float32, DEFLATE, and
`-9999` NoData. The RP100 tile index records both files as modified 2025-12-18.
Hashes and technical metadata are in `data/reference/spatial_sources.json` and
the preview sidecar.

`src/flood_raster.py` was used to create a separate transparent PNG preview
under `data/processed/spatial_layers/`; the source tiles were not modified. The
preview rectangle used the provisional boundary's numeric bounds for rendering
only; the self-intersecting polygon was not used as a mask. Blue pixels show
sampled positive modeled depth. Transparent pixels can mean zero, NoData, or
outside source coverage and cannot establish safety. The JRC README warns about
possible artifacts from model limitations, DEM sinks, tile boundaries, and DEM
issues. The separate spurious-depth and permanent-water masks have not been
downloaded or applied. Since the licensing conflict was reviewed on 2026-10-29,
the application withholds this local preview pending written clarification.

This is a modeled river-flood hazard scenario, but **a hazard–infrastructure
exposure analysis has not been completed**. The JRC preview is withheld because
of the unresolved licence conflict. NIHFW's licensed hospital CSV remains
review-only:
the official resource defines `Location_Coordinates` but does not specify
coordinate order, CRS/datum, geocoding method, positional accuracy, or row-level
location correctness. The Ernakulam subset has 31 missing/nonnumeric pairs and
18 repeated-coordinate groups covering 63 rows. Numeric range plausibility is
not sufficient to convert these to points. A focused Overpass query to an
alternate endpoint did not complete; Healthsites requires an API key, while the
available Geofabrik regional fallback was a 532 MB PBF (roughly 1.1 GB in the
reviewed GIS bundle formats) and is community-mapped rather than authoritative.
No alternate facility file was accepted.

The map does not display the JRC RP100 preview and reports exposure as
unknown/unassessable. A future provider request must confirm the JRC licence
terms and NIHFW coordinate order, CRS/datum, geocoding method/accuracy, and
corrections for missing/repeated/implausible locations; alternatively obtain a
licensed, dated, independently checked facility GIS layer. Separately,
polygon/vector intersection and raster cell sampling are different methods:
the provided `classify_depth_sample` helper deliberately labels cell samples
and never claims damage, failure, or safety. A functioning helper and passing
synthetic tests do not constitute a real-data exposure analysis.

## Hospital source follow-up (2026-10-20)

The official [Kerala Health institution directory](https://health.kerala.gov.in/index.php/institutionSearch)
was checked as an alternative identity/address reference. Its Ernakulam listing
includes facility names, types, addresses, service/beds fields, and "View Map"
controls. The reviewed page does not expose coordinate fields or a downloadable
GIS file. No CRS/datum, geocoding accuracy statement, stable spatial schema, or
spatial-data reuse terms were found. It was therefore not used to create
coordinates or validate NIHFW positions. No page publication/update date was
stated in the reviewed content; access was checked 2026-10-20.

The Kochi map now includes a record-level audit table for all 180 NIHFW
Ernakulam entries, including the original serial number, source coordinate
string, duplicate-pair count, and the reason each record is ineligible for
sampling. It keeps all 31 missing/nonnumeric pairs and all 63 records in the 18
repeated-pair groups visible. None are silently removed, deduplicated, mapped,
or sampled. The official directory is recorded as an identity-only candidate in
the source register and NIHFW review sidecars.

## Acquisition milestone: bounded OpenStreetMap context layers (2026-10-28)

Later Overpass requests succeeded for selected road, transit, waterway, health,
emergency, and industrial tags. The processed layers and exact query snapshots,
counts, timestamps, ODbL terms, attribution, and limitations are listed in
[`docs/kochi_geospatial_data.md`](../../docs/kochi_geospatial_data.md) and
`data/reference/spatial_sources.json`. These are provisional community-mapped
context layers; they do not replace official asset registers or support
exposure, emergency-access, or source-attribution conclusions. No explicitly
air-quality-tagged OSM monitor was returned. KSPCB/CPCB observations still have
no verified spatial station join, and the existing official-source blockers
above remain in effect.

# Phase 2 data acquisition report

**Acquisition date:** 2026-11-01
**Acquisition code:** `scripts/acquire_phase2_data.py`
**Rebuild inventory:** `.venv\Scripts\python.exe scripts\acquire_phase2_data.py inventory`

## Downloaded and inspected

Eight datasets (ten annual/resource files) were downloaded into
`data/raw/experimental/`. None was staged or committed. Their exact byte sizes, SHA-256 values, source URLs,
retrieval times, licence notes, and dataset-specific metadata are recorded in
`data/reference/DATA_PROVENANCE_REGISTER.json` and adjacent JSON sidecars.

| Snapshot(s) | Files | Observed content |
|---|---:|---|
| NWIC/NWDP CWC telemetry rainfall | 1 | CSV; 9,206 rows, 20 fields, 4 stations, 2021-01-03 20:30 to 2025-12-28 02:00; 1,471 duplicate station/time groups and 324 conflicting groups. |
| NWIC/NWDP manual rainfall | 1 | CSV; 109,978 rows, 20 fields, 21 stations, 2000-02-27 21:30 to 2014-12-31 17:30. |
| NWIC/NWDP manual river level | 1 | CSV; 16,005 rows, 23 fields, 6 stations, 2022-01-01 08:00 to 2025-03-31 16:00. |
| NWIC/NWDP telemetry river level | 1 | CSV; 107,064 rows, 23 fields, 6 stations, 2021-06-11 20:00 to 2025-03-10 14:00. |
| IMD 0.25-degree daily rainfall | 3 | NetCDF classic, nationwide 135 x 129 longitude/latitude grid, 365/365/366 days for 2018/2021/2024; daily rainfall in mm. Each file is about 25.4 MB. |
| NASA POWER | 1 | JSON daily series, five parameters, 1,828 dates inclusive from 2020-01-01 through 2025-01-01. |
| OpenStreetMap | 1 | Overpass JSON, 16,378 highway-tagged ways; observed OSM base timestamp 2026-11-01T18:27:21Z. |
| USGS earthquake query | 1 | GeoJSON FeatureCollection, HTTP 200, zero returned features for the documented query. |

The 69-entry provenance inventory includes previously present assets as well
as these snapshots; it is not a count of nine acquired datasets alone.

## Integrity and pre-existing copy comparison

- The four NWDP payloads match the MD5 values published in their NWDP resource
  metadata. This confirms byte agreement with the portal's published hashes,
  not measurement truth or suitability.
- The three IMD files and NASA/OSM/USGS payloads have local SHA-256 values in
  their sidecars. Readers verify these before parsing.
- The three pre-existing manual rainfall/river CSVs are record-for-record
  equal to the downloaded NWDP payloads after CSV parsing. Their raw byte
  differences are CRLF versus LF line endings.
- The CWC telemetry rainfall copy has the same 9,206 rows and exact shared
  field values after parsing, but its schema differs: the existing file has
  `_id`, while the source snapshot has `Block` and `Village`. The CWC source
  payload also contains 324 conflicting station/time groups. Both files are
  preserved; no rows were discarded or averaged.
- Hash agreement does not imply correctness, licence clarity, completeness, or
  validated station coordinates.

## Processing and validation

`src/phase2_data.py` verifies snapshot hashes, parses NASA POWER JSON, extracts
the nearest IMD grid cell to the fixed 9.93 N, 76.27 E reference point, and
loads OSM/USGS summaries without asserting exposure or hazard. IMD axis/time
checks reject malformed, non-daily, non-finite, wrong-year, or negative
non-fill observations. The processing is descriptive; no risk score, warning,
prediction, or probability is computed.

The selected IMD cell is centered at 10.00 N, 76.25 E, offset by about 0.07
degrees north and 0.02 degrees west from the API/reference point. The extracted
cell has 365, 365, and 366 valid daily values for 2018, 2021, and 2024,
respectively, with no missing cell-days in those three annual files. The
nearest-cell choice is a spatial approximation, not a station or ward join.

At that cell the descriptive annual maximum daily rainfall values are 156.03
mm/day (2018-08-16), 134.57 mm/day (2021-05-15), and 126.21 mm/day
(2024-05-24). These are grid-cell values, not verified gauge measurements,
flood impacts, return periods, or predictions. The annual sum of daily grid
values is not used as a decision score.

NASA POWER reports no fill values in the five selected parameters for this
request. Its date coverage includes the end date 2025-01-01. No station match
or event-specific accuracy evaluation was performed.

## Access limitations and non-downloads

- GPM IMERG relevant downloads require NASA PPS/Earthdata registration. No
  credentials were available or bypassed.
- The inspected global NOAA IBTrACS CSV was approximately 333 MB and was not
  acquired. A relevant authorized regional subset is still needed for cyclone
  track integration.
- Public CPCB/KSPCB catalogue pages did not supply a usable and documented
  local pollutant observation extract in this acquisition pass. API-key/
  provider data access and reuse terms remain unresolved.
- There is no validated Kochi drainage or utility network, current hospital
  coordinate layer, local population grid, or facility-specific emission
  inventory among the acquired files.
- The existing KSDMA ZIP and JRC tiles are inventoried as pre-existing project
  data; they were not re-downloaded or promoted to model inputs.

## Reproducibility and preservation

The acquisition script performs public GET/POST requests only, records source
metadata, verifies portal-provided NWDP MD5 values, performs structural QA,
and writes checksummed sidecars. It does not authenticate, bypass restrictions,
overwrite a different existing snapshot, or modify existing source CSVs. A
changed remote payload is saved with a timestamped filename. Use the `inventory`
action to regenerate the register without contacting external sources.

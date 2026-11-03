# Phase 2 data gaps and next requirements

No missing dataset is interpreted as zero hazard, exposure, vulnerability, or
risk. The order below is about safe use, not a risk ranking.

| Priority | Needed evidence | Required fields/validation | Current blocker and permitted next step |
|---|---|---|---|
| 1 | CWC/NWDP rainfall and river-gauge provenance | Provider-confirmed station IDs/coordinates, time zones, instrument/sampling definitions, QA flags, revision history, units, and duplicate/conflict resolution | Current data have unresolved CWC conflicts and local schema differences. Ask provider for authoritative extracts and reconciliation; retain both copies until resolved. |
| 1 | River levels and thresholds | Gauge datum/zero, surveyed station location, stage/discharge metadata, current official action thresholds, and dates/authority | Do not compare the downloaded metre values to danger thresholds until these are obtained. |
| 1 | Kochi municipal and ward boundaries | Current authoritative geometry, CRS/datum, date, licence, completeness, and topology checks | Existing boundary/ward snapshot is provisional. Get a city/LSGD/Kerala official vector layer or verified OSM boundary with provenance. |
| 1 | Drainage and flood pathways | Asset IDs, inlet/outfall/network topology, elevations/capacity, maintenance/condition, tide/river receiving constraints, and outage history | No verified drainage network. Commission/provider records and surveyed hydraulic data are required before causal flood/drainage modelling. |
| 1 | Hospitals, emergency facilities, and population | Verified point/polygon, service status/capacity, operating/backup power/water, catchment and current population counts with privacy-safe aggregation | NIHFW coordinates and provisional boundaries are not spatially validated. Seek current official facility and census/municipal population data; do not geocode or invent points. |
| 2 | Cyclone and compound-hazard observations | Authorized IBTrACS/IMD tracks and advisories, local wind/rain, coastal water/tide, river stages, drainage state, common timezone, and impact/outcome labels | IBTrACS global CSV not downloaded; GPM access requires registration; no paired local impact record. Obtain approved extracts and event records before estimating interaction. |
| 2 | Satellite rainfall/flood observations | GPM IMERG authorized access, JRC/Copernicus version, timestamps, quality flags, spatial resolution, and event labels | GPM registration not available. Existing JRC product is a scenario layer, not a historical event mask; do not conflate. |
| 2 | Earthquake hazard/building vulnerability | GSI/NCS catalogue/hazard studies, site conditions, building inventory, age/code/structural class, and validated fragility/inspection data | USGS query returned zero records; this is not hazard absence. No local building data or vulnerability evidence exists. |
| 2 | Air-quality time series and source attribution | Pollutant-specific observations, units/averaging windows, station coordinates and QA, contemporaneous wind/stability, stack emissions/permits, and source-apportionment evidence | Existing AQI summaries and consent documents are insufficient for attribution; API/permissions unresolved. Request authorized KSPCB/CPCB station data and current facility emissions. |
| 2 | Road connectivity and service cascades | Current authoritative road network, access restrictions, surface/elevation, flood closures, bridge constraints, ambulance routes, hospitals, alternatives and operator failure logs | OSM ways are only mapped features in a provisional bounding box. No routing or accessibility inference is enabled. |
| 3 | Intervention prioritization inputs | Comparable costs, feasibility, time, affected population, infrastructure importance, outcome evidence, uncertainty, and policy weights | No local cost/benefit evidence or agreed weights. Keep candidates unranked until stakeholders provide these records and scales. |
| 3 | Historical validation outcomes | Independent event IDs, observed extents/impacts, source and verification, event time and place, feature cutoff, reproducible splits and predeclared metrics | No matched outcomes exist. The historical-validation module is readiness scaffolding, not accuracy evidence. |
| 3 | Reuse/redistribution terms | Explicit provider licence or written permission for IMD, NASA POWER, KSPCB/KWA reports, and any derived distribution | Public availability is not an explicit open licence. Obtain and preserve permission before bundling restricted files into deployment/release. |

## Immediate external actions

1. Request CWC/NWDP station, conflict, quality, and gauge-datum documentation.
2. Obtain current authoritative municipal/ward, drainage, hospital, emergency
   service, and privacy-safe population layers with reuse terms.
3. Obtain written IMD reuse guidance and validate the grid product against
   independent nearby gauges for the intended years.
4. Arrange authorized GPM/NASA access and acquire a period-limited cyclone
   track extract if it supports a specific, predeclared event analysis.
5. Request pollutant-level KSPCB/CPCB observations and facility emissions
   records; keep AQI out of source attribution.
6. Collect independently sourced flood/road/hospital impact records before
   enabling hazard exposure, cascade estimates, validation scores, or ranked
   recommendations.

## 2026-11-02 acquisition update

The official Census Digital Library's 2011 Ernakulam District Census
Handbook and Kerala village/town directory workbooks are now held as
research-only originals. They are historical, tabular, and lack current
spatial crosswalks; they do not supply current exposure estimates.

LRIS 2.0 advertises Ernakulam drainage, road, waterbody, and watershed WMS
layers, but WFS is disabled and no raw feature export, schema, dataset date,
quality metadata, or reuse terms were available. These map-service layers
were not integrated. All previously listed flood, utility, infrastructure,
impact, and pollution evidence gaps remain open.

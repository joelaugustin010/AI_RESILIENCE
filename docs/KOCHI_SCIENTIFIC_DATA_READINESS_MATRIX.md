# Kochi scientific data readiness matrix

**Purpose:** Decision-support data readiness, by hazard and outcome domain.
This is not a model score, risk ranking, or claim that a hazard is absent.
Review date follows the current Phase 2 inventory (2026-11-02).

## Status vocabulary

| Status | Meaning for the specific use shown |
|---|---|
| `AVAILABLE_AND_SUITABLE` | An inspected, traceable dataset meets the minimum quality, coverage and resolution needs for that use. |
| `AVAILABLE_WITH_LIMITATIONS` | Data exist, but identified coverage, quality, provenance or resolution gaps materially constrain the use. |
| `AVAILABLE_BUT_NOT_SUITABLE` | A related asset exists, but it cannot support the stated use as-is. |
| `REQUIRES_OFFICIAL_ACCESS` | A known official source requires authorized account access, provider confirmation or formal permission. |
| `NOT_FOUND` | No suitable local dataset was found; this is not evidence of zero hazard, exposure or risk. |

No cell implies a probability or confidence score. Availability for hazard
context does not imply suitability for exposure, consequence, calibration, or
validation. No `AVAILABLE_AND_SUITABLE` classification is assigned to local
impact prediction or independent validation because the required event-linked
outcome foundation is absent.

## Readiness by hazard and analysis domain

| Existing selection | Hazard forcing / occurrence | Human exposure | Infrastructure exposure | Environmental exposure | Economic / service outcomes | Local calibration / training outcomes | Independent historical validation |
|---|---|---|---|---|---|---|---|
| Flood | `AVAILABLE_WITH_LIMITATIONS` — partial rainfall and river series; modeled JRC RP100 context; unresolved KSDMA raster | `NOT_FOUND` — no verified population layer or observed flood footprint | `AVAILABLE_BUT_NOT_SUITABLE` — hospital coordinates unverified; OSM roads are context; no drainage/capacity | `NOT_FOUND` — no event-specific contamination/erosion/environmental impact records | `NOT_FOUND` — no reviewed damage, displacement or outage registry | `NOT_FOUND` — no independent flood outcomes | `NOT_FOUND` — no independent event/impact set |
| Cyclone | `AVAILABLE_BUT_NOT_SUITABLE` — IBTrACS source documented but not acquired; no verified local wind/gust series | `NOT_FOUND` — no current population/vulnerability layer matched to storm footprint | `NOT_FOUND` — no building/asset fragility or event-time service layer | `NOT_FOUND` — no event-specific coastal/environmental outcomes | `NOT_FOUND` — no local loss/outage outcomes | `NOT_FOUND` — no local consequence labels | `NOT_FOUND` |
| Earthquake | `AVAILABLE_BUT_NOT_SUITABLE` — USGS query returned zero records; no completeness-described local catalogue or site shaking layer | `NOT_FOUND` — no verified occupancy/exposure layer | `NOT_FOUND` — no building inventory, site class or fragility | `NOT_FOUND` — no observed local environmental impact data | `NOT_FOUND` — no local damage/service loss records | `NOT_FOUND` — no event-linked local damage labels | `NOT_FOUND` |
| Landslide | `AVAILABLE_BUT_NOT_SUITABLE` — rainfall partial; GSI susceptibility source not ingested/validated; no verified terrain/geology inputs | `NOT_FOUND` — no failure footprints or population overlay | `NOT_FOUND` — no verified exposed asset layer or dated failure inventory | `NOT_FOUND` — no local event-specific erosion/environmental outcomes | `NOT_FOUND` — no verified damage/access interruption outcomes | `NOT_FOUND` — no local failure inventory for calibration | `NOT_FOUND` |
| Heatwave | `AVAILABLE_BUT_NOT_SUITABLE` — daily gridded weather context, not a local hourly heat-stress series | `NOT_FOUND` — no verified vulnerable population/occupancy data | `NOT_FOUND` — no cooling, power, water or health-service capacity/outage data | `NOT_FOUND` — no local heat-linked ecosystem outcomes | `NOT_FOUND` — no health, productivity or service outcome registry | `NOT_FOUND` — no local heat-health labels | `NOT_FOUND` |
| Drought | `AVAILABLE_BUT_NOT_SUITABLE` — precipitation records do not provide a continuous local 30-year monthly reference; water-balance variables absent | `NOT_FOUND` — no verified population and water-access vulnerability layer | `NOT_FOUND` — no verified reservoir, groundwater, water-supply capacity or demand layer | `NOT_FOUND` — no local drought-linked crop/ecosystem observations | `NOT_FOUND` — no reviewed agriculture, water restriction or economic outcomes | `NOT_FOUND` — no local outcome labels/reference baseline | `NOT_FOUND` |
| Industrial incident | `AVAILABLE_BUT_NOT_SUITABLE` — permits/consents are not release measurements; no usable release or plume series | `AVAILABLE_BUT_NOT_SUITABLE` — no measured exposure footprint or verified population layer | `AVAILABLE_BUT_NOT_SUITABLE` — industrial documents/map exist, but facility locations/process state are not sufficiently verified | `AVAILABLE_WITH_LIMITATIONS` — dated AQI/report context exists, not pollutant-specific incident attribution | `NOT_FOUND` — no incident-linked damage, health or service outcomes | `NOT_FOUND` — no release/outcome labels | `NOT_FOUND` |
| Infrastructure failure | `AVAILABLE_BUT_NOT_SUITABLE` — no local failure/outage hazard series; scenario inputs are not observations | `NOT_FOUND` — no population service-area/dependency layer | `AVAILABLE_BUT_NOT_SUITABLE` — provisional OSM road geometry only; hospital points and utility/drainage networks not verified | `NOT_FOUND` — no failure-linked environmental records | `NOT_FOUND` — no owner outage, restoration, cost or service impact registry | `NOT_FOUND` — no failure/outage labels | `NOT_FOUND` |
| Compound: cyclone + flood | `AVAILABLE_WITH_LIMITATIONS` — rainfall/river subsets exist; track extract, coastal boundary and synchronized observations absent | `NOT_FOUND` — no compound event footprint/population overlay | `AVAILABLE_BUT_NOT_SUITABLE` — incomplete roads and non-spatial hospital records; drainage absent | `NOT_FOUND` — no synchronized compound environmental outcome | `NOT_FOUND` — no compound damage/outage timeline | `NOT_FOUND` — no compound event labels | `NOT_FOUND` |
| Compound: heavy rainfall + drainage failure | `AVAILABLE_WITH_LIMITATIONS` — rainfall subsets exist, but no local design hyetograph/IDF or complete event observations | `NOT_FOUND` — no verified exposed population/observed inundation layer | `AVAILABLE_BUT_NOT_SUITABLE` — user-entered capacity supports only an illustrative scenario; no verified drainage system/assets | `NOT_FOUND` — no observed event-specific water quality/environment impact | `NOT_FOUND` — no verified damage, outage or cost outcomes | `NOT_FOUND` — no observed drainage-failure outcome series | `NOT_FOUND` |

## Shared asset and validation readiness

| Foundation | Status | Evidence / limitation |
|---|---|---|
| Rainfall measurement history | `AVAILABLE_WITH_LIMITATIONS` | NWDP manual: 21 stations, actual coverage 2000–2014 (not filename 1991–2020). CWC telemetry: 4 stations, 324 conflicting duplicate station-time groups. IMD 0.25° grids are local only for 2018, 2021 and 2024. |
| River levels | `AVAILABLE_WITH_LIMITATIONS` | NWDP manual/telemetry observations for 6 stations, but gauge datum, station metadata and thresholds are unresolved; manual file starts 2022, not stated 2021. |
| Satellite/modelled hazard context | `AVAILABLE_BUT_NOT_SUITABLE` for observed outcomes | JRC GloFAS RP100 is modeled river-flood scenario data; KSDMA archive has unresolved pixel semantics, NoData and reuse terms. |
| Administrative polygons | `AVAILABLE_BUT_NOT_SUITABLE` for exposure | Provisional boundary self-intersects; ward copy is community-repackaged with excluded invalid features and missing identifiers. |
| Hospitals and health facilities | `AVAILABLE_BUT_NOT_SUITABLE` for spatial analysis | NIHFW directory has 180 Ernakulam rows; 31 coordinate pairs unparseable and 18 repeated-pair groups cover 63 records; CRS/order/accuracy and current operational status are not verified. |
| Roads and transport | `AVAILABLE_BUT_NOT_SUITABLE` for routing/disruption | OSM snapshot contains 16,378 highway-tagged ways, but completeness, conditions, passability and authoritative boundaries are unresolved; LRIS export not acquired. |
| Drainage, power, water, telecom | `NOT_FOUND` | No verified current asset GIS, capacity, operating state or dependency topology. |
| Population and vulnerable groups | `NOT_FOUND` | No compatible, current, spatially verified local exposure layer. |
| Air-quality monitoring | `AVAILABLE_WITH_LIMITATIONS` for descriptive context | KSPCB AQI/report artifacts are incomplete; station geometries and pollutant-specific, quality-controlled time series not verified. AQI is not source attribution. |
| Industrial source/release data | `AVAILABLE_BUT_NOT_SUITABLE` | Consent/allotment documents are not current emissions, incident release, plume, exposure or causal evidence. |
| Independent event/outcome registry | `NOT_FOUND` | No reviewed event-ID-linked hazard footprints, human/asset/environment/economic outcomes, negatives/non-events or reporting-completeness metadata. |
| Historical validation | `NOT_FOUND` for disaster consequences | Existing rainfall benchmark is a next-measurement series benchmark; it does not validate flood or other disaster consequences. The five-row flood classifier candidate was not trained. |

## Interpretation and acquisition priority

1. **Do not infer safety from missing data or empty queries.** The zero-feature
   USGS query, raster NoData, absent populations, and missing events are
   unavailable evidence, not zero hazard/exposure.
2. **Do not use source authority as a substitute for fitness.** Each dataset
   needs task-specific provenance, units, time/space coverage, QC, licence,
   and independent checks.
3. **Highest cross-hazard blocker:** obtain an independently reviewed,
   time- and location-resolved event/outcome registry linked to authoritative
   hazard observations and current assets/population.
4. **Next hazard-input priorities:** resolve NWDP station identities, timezone,
   duplicate/conflict groups, gauge datum and measurement QC; obtain long,
   continuous rainfall records; obtain observed flood extents/depth/durations;
   verify terrain/catchments and drainage; and request owner-confirmed
   hospital, road, utility and population products.
5. **Access/terms follow-up:** acquire NASA GPM and NOAA IBTrACS only through
   authorized channels; request NCS/GSI/LRIS/CPCB/KSPCB/CWC/KSDMA metadata,
   usable exports, and reuse conditions directly from publishers/owners.
6. This matrix does not authorize new model development or change the current
   workflow. Existing illustrative and evidence-gated outputs must retain
   their existing labels and limitations until each required data gate passes.

See [Scientific data requirements by hazard](./SCIENTIFIC_DATA_REQUIREMENTS_BY_HAZARD.md),
[Data sources](./DATA_SOURCES.md), [Data quality report](./DATA_QUALITY_REPORT.md),
and [Model validation report](./MODEL_VALIDATION_REPORT.md) for variable-level
requirements, source details, inspected quality and validation boundaries.

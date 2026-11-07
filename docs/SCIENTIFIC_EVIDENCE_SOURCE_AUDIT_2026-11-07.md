# Scientific evidence source audit — 7 November 2026

This audit records what can be obtained from public sources, what is licensed or simulated, and which gaps remain. It is a source-discovery milestone, **not** a claim that the six unresolved models are now trained or validated.

## 1. Flood inundation and impact outcomes

### Public evidence found

- **India Flood Inventory–Impacts v4** (IIT Delhi / Zenodo; DOI 10.5281/zenodo.16994648) covers IMD-sourced flood events from 1967–2023. The release includes an event inventory, district flooded-area and district-impact tables, and a district flood-severity index. The event CSV includes event dates, state/district descriptions, severity, affected area and reported human/animal impacts where available.
- **USGS Global Flood Impacts Database (GFID)** contains 136,642 flood-event records across 197 countries/territories, with harmonized fatalities/affected fields and source-specific damage fields. Its representative coordinates are for event indexing, not exact inundation footprints. Impact definitions, currencies and reporting practices differ by source.

### What this closes — and what it does not

This materially improves the public event/impact reference library and supports event-history/context research. It does **not** provide a complete Kochi flood depth/duration time series, ward-level inundation polygon, compatible river/canal gauge datum, or drainage/outfall state. It cannot directly train a local inundation model or validate affected-population predictions.

### Required next data

- event-specific georeferenced inundation polygons or surveyed depth/duration observations;
- sub-daily rainfall and river/canal levels with station IDs, timestamps and vertical datum;
- tide/surge/outfall and pump/drainage operating state;
- exposure and damage observations with consistent units; and
- entire-event and geographic holdouts.

Sources: [IFI-Impacts v4](https://zenodo.org/records/16994648), [USGS GFID](https://catalog.data.gov/dataset/the-global-flood-impacts-database-gfid), [GFID geocoded-data limitations](https://catalog.data.gov/dataset/geocoded-data-the-global-flood-impacts-database-gfid).

## 2. Landslide events and non-event background

### Public evidence found

- A Kerala 2018 monsoon landslide inventory published through the University of Twente / DANS reports 4,728 mapped landslides for 1 June–26 August 2018.
- NRSC/ISRO's Landslide Atlas describes approximately 80,000 mapped landslides in India for 1998–2022, across 17 states and two Union Territories, with seasonal, event-based and route-wise inventories. It includes the Western Ghats and Kerala event inventories.
- NASA COOLR / Global Landslide Catalog provides report-based and event-based records, but report-based coverage is not a complete census of all failures.

### What this closes — and what it does not

These are credible event-inventory leads, including much stronger Kerala coverage than the older sparse report catalogue. They are **presence records**, not proof that all other map cells or dates were landslide-free. Reporting and mapping effort vary spatially and temporally. NRSC geometry access, licence/reuse, metadata, completeness and scale must be checked before ingestion. No random pseudo-absence sample will be labelled as verified non-events.

### Required next data

- authorized inventory geometries and per-feature dates, source and mapping method;
- DEM-derived slope/curvature, geology, soil, land cover, road cuts and drainage;
- event-aligned rainfall intensity, duration and antecedent wetness;
- survey/monitoring coverage to define credible non-event periods/areas; and
- spatially blocked and event-held-out evaluation with reporting-bias analysis.

Sources: [Kerala 2018 inventory](https://research.utwente.nl/en/datasets/landslide-inventory-of-the-2018-monsoon-rainfall-in-kerala-india/), [NRSC Landslide Atlas](https://www.nrsc.gov.in/nrscnew/resources_atlas_landslide.php), [NASA COOLR](https://gpm.nasa.gov/applications/landslides/coolr).

## 3. Industrial incidents

### Public evidence found

- DGFASLI explains the statutory safety-report, annual safety-audit and major-accident reporting responsibilities for covered installations.
- The Labour Bureau publishes annual Statistics of Factories reports.
- Kerala Electrical Inspectorate publishes electrical-accident statistics, which are not equivalent to process-safety releases at industrial facilities.

### What remains unresolved

No open, machine-readable, provenance-verified facility-level panel was identified with incident and non-incident operating periods, process variables, hazardous-material release quantities/times, inspection/near-miss history, monitoring observations and exposure. State/year aggregate counts cannot be expanded into facility-time training labels.

### Required next data

Use only records lawfully shared by the responsible facility/regulator, with de-identification and owner approval. Record facility/process identity under controlled access, operating exposure time, incident/near-miss definitions, release characteristics, monitoring quality, meteorology and non-event operating periods. Process-safety engineering and consequence models remain primary; ML is not justified until representative labels exist.

Sources: [DGFASLI safety and reporting guidance](https://dgfasli.gov.in/en/faq), [Labour Bureau factory statistics](https://labourbureau.gov.in/annual-report-on-statistics-of-factories), [Kerala Electrical Inspectorate statistics](https://www.dei.kerala.gov.in/electric-statistics).

## 4. Infrastructure failure and restoration

### Public evidence found

- KSEB's HRIS KPI page reports system-level reliability measures including SAIFI and SAIDI. These are aggregate service reliability indicators, not an asset failure log.
- ORNL's EAGLE-I archive provides county-level U.S. customer outage data at 15-minute intervals for 2014–2022. It is not Kerala data and cannot validate a Kochi model.
- CAG's performance audit of KSEBL reports historic aggregate reliability indicators; these do not provide a feeder/asset-by-event feature table.

### What remains unresolved

No open Kochi asset-level dataset was verified with stable asset/feeder IDs, topology, condition/inspection history, maintenance, failure onset, affected customers/services and restoration timestamps. Aggregate SAIDI/SAIFI cannot identify which assets failed or predict their individual failure probabilities.

### Required next data

Request appropriately de-identified feeder/asset event logs, network topology, inspection/maintenance records, planned-outage flags, force-majeure flags, customer counts, outage start/end and restoration sequence. Keep asset reliability, service interruption and hazard-triggered failure as distinct targets.

Sources: [KSEB KPI dashboard](https://hris.kseb.in/kpi/index.html), [ORNL EAGLE-I 2014–2022](https://impact.ornl.gov/en/datasets/eagle-i-power-outage-data-2014-2022/), [CAG Kerala KSEBL performance audit](https://saiindia.gov.in/uploads/download_audit_report/2022/Report-No.-5-of-2022%2C-Govt.of-Kerala-068b1436b0e3030.33693885.pdf).

## 5. Intervention effectiveness

### Evidence tracks

- **Empirical randomized evidence:** the WFP/World Bank Bangladesh 2024 Forecast-Based Anticipatory Action evaluation is a promising licensed candidate for the effect of cash-transfer timing on household flood outcomes. It is not evidence for drainage, embankment, household flood-proofing or other physical interventions. Access, design fields, codebook, survey weights, assignment and household/asset joins must be reviewed under the data-use terms by an authorized adult/organization.
- **Simulation evidence:** the open Geul archive models several flood-risk-reduction measures. It may support a separate simulation-surrogate model, but its labels are generated by a coupled model, not observed intervention outcomes. It is not Kochi-calibrated.

### Decision

The real-world intervention ranking remains withheld. Do not mix randomized cash-assistance outcomes, observational physical works and Geul simulations in one training target or one ranking. The current empirical causal trainers remain untrained on real data.

Sources: [World Bank Bangladesh evaluation catalogue](https://microdata.worldbank.org/catalog/8009), [Geul simulation archive](https://zenodo.org/records/15488420).

## 6. Kochi Operation Breakthrough causal evaluation

### Public evidence found

- KSDMA documents the 21 October 2019 Kochi flood and approval of Operation Breakthrough.
- The Kerala Irrigation Department's Kochi flood-mitigation report describes the 74-division assessment, Phase I/II works, Thevara Kayal mouth desilting and canal interventions. It reports relief narratively after Phase I/II, while also identifying locations that continued to flood.
- G.O.(Rt) No. 474/2024 records technical sanction for Phase III mitigation near High Court Junction and connected drains, with a requirement for progress reporting and quality control.

### What remains unresolved

These documents identify real intervention locations and project milestones, but they do not supply a linked site-by-event outcome panel. A narrative that flooding reduced is not a numerical counterfactual. Technical sanction is not proof of completion or flood reduction. No causal estimate is defensible from the current public material.

### Required next data

For each distinct intervention version (e.g. Thevara Kayal mouth, Koithara Canal, Changadampokku thodu, Karanakodam thodu, Edappally thodu, Ambanattuchira thodu and Mullassery Canal works), obtain:
- work order, design, geospatial footprint, start/completion/commissioning dates and as-built measurements;
- maintenance, blockage, sediment and pump/outfall records;
- site/event rainfall, tide and river/canal level with datum;
- observed inundation depth/duration and a single consistent damage outcome;
- treated, not-yet-treated and comparison sites over repeated events; and
- source IDs, quality flags, units, missingness and collection methods.

The existing Kochi panel auditor checks structural readiness only. A subsequent design review must assess treatment targeting, pre-trends, concurrent works, changing exposure, weather confounding, spillovers and outcome comparability before a difference-in-differences or event-study estimate is considered.

Sources: [KSDMA Kochi 2019](https://sdma.kerala.gov.in/kochi-2019/), [Kerala Irrigation Department report](https://www.irrigation.kerala.gov.in/sites/default/files/2021-08/kochiflood.pdf), [G.O.(Rt) 474/2024](https://document.kerala.gov.in/documents/governmentorders/govtorder1707202414%3A45%3A51.pdf).

## Release decision

| Track | Current evidence status | Model/training decision |
|---|---|---|
| Flood impacts | Public event/district impacts found; local inundation depth/duration absent | Do not claim local flood-impact or inundation prediction |
| Landslide | Kerala/India event inventories identified; defensible background not yet verified | Do not label pseudo-absences as non-events |
| Industrial incident | Public aggregate/statutory sources only | No supervised incident model |
| Infrastructure failure | Aggregate reliability metrics only | No asset-level failure model |
| Intervention effectiveness | Licensed trial candidate + separate open simulation | Empirical causal ranking withheld; simulation surrogate remains separate |
| Kochi causal evaluation | Project reports and sanction records; no linked site-event panel | No causal effect estimate |

The compound workspace now displays this evidence-readiness information for selected flood, landslide, industrial, infrastructure and compound scenarios. It continues to display component evidence and scenario pathways, not a fabricated joint probability or damage prediction.


## Reproducible public flood-inventory audit

The branch now includes `scripts/audit_india_flood_inventory.py`. It retrieves
the published IFI-Impacts v4 event CSV, verifies the publisher-listed MD5
checksum, checks required columns, event-ID uniqueness, date order, coordinate
ranges, Kerala/Ernakulam text coverage and missingness of the reported impact
fields. It emits a compact JSON audit; the raw CSV is held in a temporary
runtime directory and is not committed to the repository.

The `india-flood-inventory-audit` CI job runs this acquisition/audit on PR #82
and uploads only the JSON report. Its expected result is an event-inventory
audit status, never a training-ready or validated-flood-model status.

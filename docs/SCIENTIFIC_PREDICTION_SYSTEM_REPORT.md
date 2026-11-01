# Scientific consequence prediction system report

**Review date:** 2026-11-02  
**Project:** AI_RESILIENCE — Kochi / Ernakulam

## Result

The existing Decision Workflow has been extended, not replaced. It preserves
all ten selections and presents input-derived model outputs with evidence and
validation status. The available verified inputs do **not** support reliable
population, building-damage, environmental-loss or economic-loss predictions.
Those are explicitly shown as `INSUFFICIENT EVIDENCE FOR A RELIABLE ESTIMATE`.

The one dynamic consequence-adjacent result is a **SIMULATED SCENARIO** for
heavy rainfall plus drainage failure: where all required values are supplied,
the app calculates Rational Method peak runoff, compares it with the
user-entered drainage capacity, and displays the resulting relation and
nominal flow excess. It does not claim that a real drain failed, identify an
overflow location, or estimate exposed people/assets, inundation, damage or
service loss.

The retrospective rainfall benchmark predicts the next recorded rainfall
measurement only in a held-out historical dataset. It is not a forecast of
current rainfall, flood occurrence or consequences. No disaster model is
independently validated for local prediction.

## Ten-disaster model and consequence status

| Disaster selection | Model implemented | User inputs used | Consequences it can estimate | Real datasets used | Historical validation performed | Validation results | Remaining limitations | Scientific status |
|---|---|---|---|---|---|---|---|---|
| Flood | Rainfall descriptor and conditional Rational Method runoff. | Rainfall depth/period, optional catchment area and runoff coefficient, source-reported river level. | Scenario peak runoff only; no human, asset, environmental or economic impacts. | Manual rainfall benchmark is separate; IMD/NWDP/rivers/JRC are context-only or excluded from this calculation. | Rainfall measurement benchmark only; no flood-outcome validation. | Manual series holdout: n=11,675; gradient boosting MAE/RMSE 3.0221/5.2122 mm; not flood skill. | No local design hyetograph, hydraulics, verified flood footprints, exposure or independent flood outcomes. | Scenario runoff indicator; flood consequence `INSUFFICIENT EVIDENCE`; **NOT YET VALIDATED**. |
| Cyclone | Idealized dynamic-pressure indicator from wind speed. | Optional user-entered wind speed in km/h. | None; pressure is a physical indicator, not impact. | NOAA NCEI IBTrACS v04r01 North Indian snapshot is acquired and validated but withheld from the app pending rights clarification; no track/wind observations are joined. NASA POWER remains context only. | None. | No cyclone impact metrics. | No confirmed reuse terms, local wind/surge, building inventory or fragility/outcomes. | Physical scenario indicator; consequences `INSUFFICIENT EVIDENCE`; **NOT YET VALIDATED**. |
| Earthquake | Optional reported MMI descriptive review. | Reported MMI integer 1–12. | None; MMI description is not damage estimation. | USGS regional query file; zero records returned and not treated as zero hazard. | None. | No shaking/damage metrics. | No local site motion, geotechnical conditions, building vulnerability or outcome data. | User-reported observation context; consequences `INSUFFICIENT EVIDENCE`; **NOT YET VALIDATED**. |
| Landslide | Rainfall intensity-duration context; no uncalibrated local trigger. | Rainfall depth/period and optional antecedent rainfall. | None; rainfall rate is not a failure or consequence estimate. | IMD grid/NWDP rainfall are limited context and not spatial/time joined. | None. | No landslide metrics. | No high-resolution terrain/geology, failure inventory, calibrated thresholds or exposure. | Screening context only; consequences `INSUFFICIENT EVIDENCE`; **NOT YET VALIDATED**. |
| Heatwave | NOAA/NWS Rothfusz heat-index screening within domain. | Temperature °C and relative humidity %. | Heat-index screening value only; no health impacts or affected people. | No co-located project weather data are used for user scenario. NASA POWER remains broad context only. | None. | No local heat-health metrics. | No local forecast feed, Kerala thresholds, radiation/wind, vulnerability or independent health outcomes. | Scenario screening; consequences `INSUFFICIENT EVIDENCE`; **NOT YET VALIDATED**. |
| Drought | SPI-1 with complete same-location monthly climatology requirement. | User-supplied monthly rainfall CSV (mm), location. | Standardized precipitation anomaly only; no water-supply or economic impact. | No qualifying local record: available manual series is incomplete; three IMD years are non-contiguous. | None. | No drought metrics. | No complete homogeneous 30-year series, water balance, demand/storage or impacts. | Historical index only if eligible data supplied; consequences `INSUFFICIENT EVIDENCE`; **NOT YET VALIDATED**. |
| Industrial incident | Matched pollutant/reference concentration ratio. | Pollutant concentration/reference, matching units and averaging periods. | Descriptive ratio only; no plume, exposure or health estimate. | KSPCB AQI/report and industrial consent records are not source-attribution inputs. | None. | No incident metrics. | No quality-assured source-specific time series, current emissions, meteorology, dispersion or outcomes. | Measurement comparison only; consequences `INSUFFICIENT EVIDENCE`; **NOT YET VALIDATED**. |
| Infrastructure failure | Qualitative failure-mode/dependency review. | Service, reported condition, description, nominated assets. | None; no reliability or service-impact calculation. | OSM road and NIHFW records are not verified network/facility exposure inputs. | None. | No failure metrics. | No owner-confirmed topology, condition, redundancy, failure/outage/repair records. | Qualitative evidence review; consequences `INSUFFICIENT EVIDENCE`; **NOT YET VALIDATED**. |
| Compound: cyclone + flood | Separate cyclone and flood components; unresolved interaction. | Wind and rainfall fields independently; optional runoff inputs. | Component physical indicators only, not combined consequences. | Existing rainfall/river/NASA/JRC context is not synchronized event data. | None. | No joint-event metrics. | No time-aligned hazard sequence, coastal boundary, drainage, footprint, exposure or impacts. | Scenario components only; no summed score or joint probability; **NOT YET VALIDATED**. |
| Compound: heavy rainfall + drainage failure | Rational Method peak flow and explicit capacity comparison. | Rainfall depth/period, catchment area, runoff coefficient, drainage capacity. | Scenario flow/capacity relation and nominal excess flow only; no impacts. | No verified local drainage dataset; rainfall source snapshots are not joined to an assessed catchment. | No consequence validation. | Software tests show input-dependent capacity relation; no historical outcome metrics. | User assumptions, simplified method, no surveyed catchment/network, tide, spatial footprint or impact outcomes. | **SIMULATED SCENARIO** hydraulic indicator; consequence impacts `INSUFFICIENT EVIDENCE`; **NOT YET VALIDATED**. |

Across all ten selections, human, environmental and economic outcomes are
unestimated. Infrastructure impact is also unestimated except for the
explicit drainage flow/capacity scenario indicator, which is not an observed
asset effect.

## Consequence display and recommendation behavior

The common output contract distinguishes observed impacts, scenario/model
indicators, user-supplied context, validation and data requirements. The UI
renders each of four consequence categories and shows dynamic scenario output
values where available; absence is not rendered as zero.

Hazard-specific before/prevention/preparedness, during/response and
after/recovery items remain. A fourth long-term planning action is shown
separately. Recommendations remain unranked, include relevance, evidence or
authority, scope and limitations, and do not claim official emergency
authority.

## Decision Workflow and Kochi map integration

The Decision Workflow now offers **View prone areas on the Kochi map** after
the submitted scenario is assessed. Navigation carries the selected hazard,
location, user-entered conditions, assessment status and available model
indicators in Streamlit session state. The map shows this context and provides
a return link; the submitted workflow inputs remain available when the user
returns.

The map uses the existing reviewed layers rather than creating duplicate
hazard geometries. Its JRC RP100 river-flood layer is available only as
scenario context for Flood and Cyclone + flood selections; it is not generated
from the user's entered values and is not an observed flood or forecast.
The already-acquired ESA WorldCover 2021 product is also available as an
optional, checksum-verified categorical map-context preview for flood,
cyclone, landslide, heatwave, drought and compound selections. It is not
classified as hazard severity and is not used to calculate susceptibility,
population, buildings, exposure or consequences.
Scenario recommendation candidates and their evidence, scope and limitations
also transfer to the map; they remain general rather than location-specific.
Unrelated selections hide that flood overlay and explicitly report that a
compatible hazard layer is unavailable. Existing ward/context geometries can
be selected to inspect their source attributes, but incomplete ward polygons
are not treated as full municipal coverage or used to estimate population,
facility exposure or consequences. No verified hospital, drainage or utility
asset layer is currently plotted.

## Data and validation

No new dataset was downloaded for this milestone. Existing sources and
snapshots retain Phase 2 provenance limitations. No point, ward or raster
overlay is used to infer facility exposure: the provisional corporation
boundary has self-intersection, NIHFW coordinate meaning is unresolved, and
KSDMA raster semantics/reuse remain unresolved. Existing contextual layers
are not treated as validated impact truth.

The rainfall measurement benchmark results and the five-row flood-classifier
readiness blockers are documented in `MODEL_VALIDATION_REPORT.md`. These do
not validate a disaster consequence model. All ten local prediction models
remain `NOT YET VALIDATED`.

## Verification

- Focused model/workflow/Streamlit/rainfall tests from the prior verification:
  **62 passed, 23 subtests passed**.
- Complete repository suite after map integration: **210 passed, 38 subtests
  passed**.
- Focused land-cover, map, workflow and provenance tests: **28 passed**.
- Workflow and map AppTest coverage verifies scenario transfer, general
  recommendations, feature selection handling, WorldCover class display and
  suppression of the flood overlay for an unrelated Heatwave scenario.
- Python compile check for source, Streamlit pages and changed tests: passed.
- Local Streamlit root and `/_stcore/health`: HTTP 200 in the preceding
  verification; nested launcher health and workflow/map navigation were
  checked in this integration.
- Live deployment: not checked.
- `git diff --check` reports trailing blank lines in the pre-existing modified
  `assessment.py` and `src/flood_risk.py`; these unrelated files were preserved.

Git remains on `main`, two commits ahead and 219 behind its local
`origin/main` tracking reference. Existing uncommitted and untracked team work
was not staged, committed, synchronized, or discarded.

## Required next data

Start with provider-confirmed rainfall/gauge IDs, coordinates, time zone,
quality flags and resolution of duplicate conflicts. Obtain current reusable
catchments/drainage/outfalls, flood event footprints/depths, population and
owner-confirmed facility/utilities data. Build independently reviewed,
time/geography-matched event impact outcomes and validate each model against
prespecified baselines before enabling local consequence predictions.

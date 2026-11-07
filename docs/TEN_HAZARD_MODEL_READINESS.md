# Ten-hazard model readiness and scientific completion standard

**Scope:** the ten selectable scenarios in `src/hazard_registry.py`  
**Purpose:** define what a scientifically defensible model would mean for each scenario, what the current platform actually does, and what evidence must exist before a model may be used.

## Important interpretation

The ten entries are the platform's authoritative workflow scope. They are not a universal list of all disasters. The 2025 UNDRR/ISC Hazard Information Profiles describe 281 hazards across eight broad types; a local platform should select and document the hazards relevant to its users rather than imply that ten labels exhaust disaster science.

The platform must distinguish:

1. **Scenario assessment:** transparent calculations and evidence review using supplied or verified inputs.
2. **ML research evidence:** a model card and held-out research metrics with a narrow, explicit target.
3. **Validated prediction:** independently evaluated, calibrated and domain-reviewed predictions for a defined geography, lead time and outcome.
4. **Official warning:** issued only by the competent authority, never by this research application.

A complete workflow registry is not complete predictive coverage. A registered model ID is not proof that a model card, trained artifact, valid skill or operationally usable prediction exists.

## Hazard-by-hazard readiness

| Workflow hazard | Current scientific pathway | Current ML position | Required evidence before stronger modelling |
|---|---|---|---|
| Flood | Rainfall descriptor and optional Rational Method peak-runoff scenario; no inundation depth or flood probability is inferred | Rainfall models are forcing evidence only, not flood prediction | Geolocated observed inundation extent/depth/duration; compatible river/canal levels and datum; rainfall; drainage/pump/outfall capacity; terrain and catchment connectivity; independent event holdouts |
| Cyclone | Wind-speed/pressure indicators and official-source context; no local wind, track or surge forecast is created | Best-track rapid-intensification and wind-change research tasks are not operational forecast models | Archived forecast cycles with issue/valid times; storm-grouped track/intensity/wind/rainfall outcomes; basin-held-out testing; coastal surge/tide observations and local exposure |
| Earthquake | Reported MMI is descriptive context only; no site shaking or damage conversion | Aftershock occurrence is a separate post-mainshock research target; invalidated/no-skill cards remain blocked | Complete regional catalogue with magnitude-of-completeness and sequence metadata; reviewed ground-motion observations; site geology/soil and building inventory; sequence-aware temporal and geographic holdouts |
| Landslide | Rainfall intensity/duration context; no local trigger threshold or susceptibility class | No defensible supervised model without representative non-event sampling | Dated geolocated inventory including failures and non-failures; DEM/slope, geology, soil, land cover, drainage and antecedent rainfall; sampling-bias assessment; spatially blocked event validation |
| Heatwave | Temperature/heat-index screening with explicit distinction from an official heatwave declaration | Kochi grid-point temperature models are research-only and do not establish health impacts | Quality-controlled station Tmax/Tmin/humidity; official IMD heatwave labels/thresholds; consecutive-day and night-time heat; population vulnerability and health outcomes; station- and year-held-out evaluation |
| Drought | Station-level SPI-1 when the reference record and positive-value count pass the implementation's checks | The 30-day rainfall-deficit proxy is not agricultural or hydrological drought; invalidated/no-skill status must block inference | Continuous station rainfall and a suitable reference period; soil moisture, evapotranspiration, stream/reservoir/storage and demand data; crop/water-supply outcomes; season- and region-held-out validation |
| Industrial incident | Like-for-like pollutant concentration/reference comparison only; no source attribution or plume forecast | No defensible supervised model without verified release labels and representative non-events | Facility and process inventory; substance-specific release time/rate/quantity; quality-controlled monitoring; meteorology/terrain; source-specific dispersion evidence; verified incident and non-incident periods |
| Infrastructure failure | Qualitative FMEA and conceptual service-dependency review; no failure probability, availability or restoration time | No supervised model without asset-condition and outage/recovery labels | Asset register and topology; condition/inspection/maintenance history; failure and non-failure records; outage extent, duration and restoration; redundancy and dependency data; asset-owner review |
| Compound: cyclone + flood | Separate cyclone and flood components; interactions are not added into a joint probability | Concurrent cyclone/rainfall association is exploratory and excluded from decision inference | Joint event catalogue with aligned forecast issue times, cyclone track, rainfall, tide/surge, river levels, inundation and impact outcomes; storm-level holdout and dependence modelling |
| Compound: heavy rainfall + drainage failure | Rainfall and drainage-capacity scenario comparison; user-entered capacity/failure assumptions remain explicit | Rainfall is forcing evidence only; it is not a drainage-failure or inundation prediction | Geospatial drainage network, invert levels, cross-sections, blockage/maintenance and pump/outfall states; sub-hourly rainfall; observed water depth/duration; hydraulic calibration and event holdout |

## Shared acceptance gates

A model may move beyond a research-only status only after every applicable gate passes:

1. **Target validity:** one measurable outcome, unit, geography and forecast horizon; target timestamps and aggregation are documented.
2. **Source provenance:** source, licence/permission, version, retrieval date, spatial resolution, temporal resolution, missingness and quality flags are recorded.
3. **Availability-at-issue-time:** every feature is demonstrably available at the prediction issue time; revised or post-event data cannot leak into a forecast.
4. **Independent splits:** time, storm/sequence, site and geography are grouped appropriately; overlapping outcome windows are purged.
5. **Relevant baselines:** persistence, climatology, official operational baseline or a simple physical model is evaluated on the same holdout.
6. **Skill and calibration:** metrics match the task and class imbalance; uncertainty intervals, calibration and decision thresholds are evaluated. A high ROC-AUC alone is insufficient.
7. **Robustness:** performance is examined across seasons, locations, event severities, missing-data regimes and relevant population groups.
8. **External validation:** an untouched geography, event period or independent dataset is evaluated; failure cases and distribution shift are reported.
9. **Domain review:** relevant meteorological, hydrological, geological, public-health, industrial-safety or infrastructure experts review assumptions and use limits.
10. **Safe release:** inference fails closed outside the supported feature/geography/time envelope. No ML score is presented as an official warning, evacuation trigger, causal effect or guaranteed avoided loss.

## Status vocabulary

- `NOT_TRAINED`: no registered model card/artifact is available for that task.
- `NO_SKILL`: the evaluated model did not demonstrate adequate skill against its required baseline; inference is withheld.
- `INSUFFICIENT_TEST_EVENTS`: the evaluation sample cannot support a defensible conclusion.
- `WEAK_RESEARCH_SIGNAL` / `RESEARCH_SIGNAL_NOT_VALIDATED`: narrow research evidence only; no operational claim.
- `EXPLORATORY_ASSOCIATION`: descriptive association, not a causal effect or forecast.
- `VALIDATED_FOR_DEFINED_USE`: reserved for a future, separately reviewed release after the full acceptance gates; this status must never be inferred from successful code execution or a single test split.

## Multi-hazard and compound-scenario rule

Compound scenarios must preserve component identity, timing, dependence and cascading pathways. Component scores must not be summed or multiplied into a joint probability without a validated dependence model. The two compound workflow scenarios are not interchangeable with the eight individual hazards.

## External scientific references

- UNDRR/ISC, [2025 Hazard Definition and Classification Review](https://www.undrr.org/publication/documents-and-publications/hazard-definition-and-classification-review-technical-report): 281 hazards grouped into eight broad types.
- UNDRR, [Hazard terminology](https://www.undrr.org/terminology/hazard): hazards can be single, sequential or combined; risk depends on hazard, exposure, vulnerability and capacity.
- WMO, [Handbook on the use of Risk Knowledge for Multi-Hazard Early Warning Systems](https://wmo.int/files/handbook-use-of-risk-knowledge-multi-hazard-early-warning-systems): risk knowledge, observation/forecasting, communication and preparedness are connected pillars.

## Current completion statement

The repository currently has deterministic assessment modules and a shared ML research engine, but it does not have ten independently validated predictive models. This document is an implementation and release standard, not a claim that missing observations, calibration, validation or expert review have been completed. Each hazard remains eligible for transparent scenario assessment even when its ML model is withheld.

# Disaster model limitations

## Global limitations

- All ten models are screening or scenario assessments. `validated_prediction_available`
  is always false.
- User-entered values are not independently authenticated. A user label of
  “observation” does not make an observation verified.
- No local hazard probability, risk class, injury/death estimate, damage
  estimate, exposed population, or benefit percentage is generated.
- Nominated assets are not mapped. Population context is not a geospatial
  exposure estimate.
- Phase 2 fixed-point, station, raster and road files are described with their
  relevance/status but not silently joined to a scenario location.
- Recommendations are unranked, non-operational planning prompts. Competent
  local emergency authorities supersede this prototype during incidents.
- Passing unit tests proves selected software behavior, not physical validity,
  calibration, data sufficiency, field validation or generalization.

## Model-specific limits

| Model | Primary limits |
|---|---|
| Flood | Mean rainfall intensity may not match time of concentration/design storm. Rational Method is limited to suitable small catchments. No floodplain hydraulics, terrain, drainage network, tide/backwater, depth, duration or flood impact. River gauge datum and thresholds remain unresolved. The JRC GloFAS RP100 layer is licensed modelled scenario context (ODbL 1.0 applied; CC BY 4.0 also stated), not observed flooding; its exposure screening uses provisional OSM assets and excludes JRC-patched permanent water, but no verified population or asset inventory is joined. |
| Cyclone | User wind may be gust, sustained or unknown averaging. Constant-density dynamic pressure is not structural load. No official track, landfall, coastal surge, wind field or building fragility. |
| Earthquake | Reported MMI is optional and unverified. The model does not convert magnitude to shaking, estimate PGA/PGV, site amplification, building damage, aftershock risk or local earthquake hazard. |
| Landslide | Rainfall alone does not establish susceptibility or failure. No calibrated local intensity-duration threshold, slope, geology, land cover, soil moisture, runout or event inventory. |
| Heatwave | NWS regression is a screening approximation in a limited warm/humid domain. It omits solar radiation, wind, exposure duration, work intensity, acclimatization, age/health vulnerability and local Kerala action thresholds. The 1991-2025 descriptive benchmarks are model-grid climatology, not station normals or IMD heatwave criteria. |
| Drought | SPI-1 is precipitation-only and requires >=30 complete years for a station. The 1991-2025 Open-Meteo reanalysis grid-point record now satisfies the length rule, but it is modelled reanalysis rather than a rain-gauge station, so reference homogeneity, local representativeness and station provenance remain unverified. It does not model evapotranspiration, soil moisture, streamflow, reservoir storage, demand or impacts. |
| Industrial incident | The ratio is descriptive and uses a user-supplied comparator. No law/health applicability check, emissions, source term, stack, dispersion, meteorology, toxicology, source attribution or exposure analysis. |
| Infrastructure failure | Failure mode, owner, topology and redundancy are user-described or missing. No event rates, RPN, outage probability, service loss, repair duration or criticality rank. |
| Cyclone + flood | Components are not assumed simultaneous or causal. No common-time storm, rainfall, river, coast, drainage, extent and impact data. No sum or joint probability. |
| Heavy rainfall + drainage failure | Rational Method assumptions may be violated. Capacity is user-entered, not design-verified. A calculated exceedance is not proof of actual surcharge, flooding, failure or exposure. |

## Descriptive benchmark and screening limits

- **Climate benchmarks** (`src/climate_benchmarks.py`) use the Open-Meteo
  1991-2025 archived reanalysis record at a single model grid point. They are
  descriptive climatology, not station normals, forecasts, warnings,
  attribution, or projections. Trends are linear summaries that ignore
  autocorrelation and non-stationarity. Heavy-rain classes and 35/37 °C counts
  are transparent screening values, not official thresholds. The SPI-1 series
  is delegated to the existing drought model and remains descriptive.
- **Flood exposure screening** (`src/exposure_assessment.py`) samples
  provisional OSM asset points against the modelled JRC RP100 raster and
  excludes cells marked as permanent water by the JRC permanent-water tiles.
  It does not establish observed inundation, asset existence, occupancy,
  population, damage, casualties, or safe/unsafe status. NoData and transparent
  pixels are not zero depth and do not establish safety.

## Data gaps that block expansion

See `DATA_GAPS.md`. Key needs include provider-confirmed NWDP station/time/
gauge metadata; local rainfall thresholds; current authoritative boundary,
drainage, road, hospital, utility and population data; GPM/approved cyclone
tracks where relevant; local earthquake/building evidence; pollutant-specific
air measurements and emissions; and independent historical outcomes.

## No-go conditions

Do not use model output as an official warning, route, evacuation instruction,
health diagnosis, building safety finding, environmental compliance finding,
causal industrial attribution, intervention ranking, or validated forecast.
Do not turn unavailable values into zero. Do not deploy quantified local
consequences before independent validation and domain-authority review.

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
| Flood | Mean rainfall intensity may not match time of concentration/design storm. Rational Method is limited to suitable small catchments. No floodplain hydraulics, terrain, drainage network, tide/backwater, depth, duration or flood impact. River gauge datum and thresholds remain unresolved. |
| Cyclone | User wind may be gust, sustained or unknown averaging. Constant-density dynamic pressure is not structural load. No official track, landfall, coastal surge, wind field or building fragility. |
| Earthquake | Reported MMI is optional and unverified. The model does not convert magnitude to shaking, estimate PGA/PGV, site amplification, building damage, aftershock risk or local earthquake hazard. |
| Landslide | Rainfall alone does not establish susceptibility or failure. No calibrated local intensity-duration threshold, slope, geology, land cover, soil moisture, runout or event inventory. |
| Heatwave | NWS regression is a screening approximation in a limited warm/humid domain. It omits solar radiation, wind, exposure duration, work intensity, acclimatization, age/health vulnerability and local Kerala action thresholds. |
| Drought | SPI-1 is precipitation-only and requires >=30 complete years for a station. It does not model evapotranspiration, soil moisture, streamflow, reservoir storage, demand or impacts. Reference homogeneity/provenance is not verified. |
| Industrial incident | The ratio is descriptive and uses a user-supplied comparator. No law/health applicability check, emissions, source term, stack, dispersion, meteorology, toxicology, source attribution or exposure analysis. |
| Infrastructure failure | Failure mode, owner, topology and redundancy are user-described or missing. No event rates, RPN, outage probability, service loss, repair duration or criticality rank. |
| Cyclone + flood | Components are not assumed simultaneous or causal. No common-time storm, rainfall, river, coast, drainage, extent and impact data. No sum or joint probability. |
| Heavy rainfall + drainage failure | Rational Method assumptions may be violated. Capacity is user-entered, not design-verified. A calculated exceedance is not proof of actual surcharge, flooding, failure or exposure. |

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

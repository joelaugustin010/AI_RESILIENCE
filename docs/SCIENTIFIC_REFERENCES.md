# Scientific references for the hazard models

References are method sources, not evidence that local model outputs are
validated. The implementation uses each source only for the stated purpose.

## Cross-cutting and compound risk

- United Nations Office for Disaster Risk Reduction (2017), [Disaster risk
  terminology](https://www.undrr.org/terminology/disaster-risk). Frames hazard,
  exposure, vulnerability and capacity; not a universal numeric equation.
- Zscheischler, J. et al. (2020), “A typology of compound weather and climate
  events,” *Nature Reviews Earth & Environment*, 1, 333-347.
  [doi:10.1038/s43017-020-0060-z](https://doi.org/10.1038/s43017-020-0060-z).
  Supports explicit interaction types and evidence needs; it does not supply
  local Kochi dependence parameters.
- NIST, [Community Resilience Planning Guide, Volume II](https://www.nist.gov/publications/community-resilience-planning-guide-buildings-and-infrastructure-systems-volume-ii).
  Dependency/cascade planning reference, not a Kochi asset dataset.

## Hazard-specific methods

- **Flood and urban runoff:** Federal Highway Administration, *Urban Drainage
  Design Manual, HEC-22*, [report 10009](https://www.fhwa.dot.gov/engineering/hydraulics/pubs/10009/10009.pdf).
  Rational Method unit form is used only as a limited small-catchment peak-flow
  screen; assumptions and non-hydraulic boundary effects are stated.
- **Cyclone:** NOAA National Hurricane Center, [Saffir-Simpson Hurricane Wind
  Scale](https://www.nhc.noaa.gov/aboutsshws.php). Wind-only scale is not used
  to categorize the unverified user wind input or issue a Kerala warning.
  Idealized dynamic pressure `q=1/2 rho v²` is a physical indicator, not a
  damage function.
- **Earthquake:** USGS, [Modified Mercalli Intensity Scale](https://www.usgs.gov/programs/earthquake-hazards/modified-mercalli-intensity-scale).
  Used for descriptions of optional reported MMI; no ground-motion prediction
  is made.
- **Landslide:** Guzzetti, F. et al. (2008), “The rainfall intensity-duration
  control of shallow landslides and debris flows,” *Earth-Science Reviews*,
  86, 1-2, 55-72. [doi:10.1016/j.earscirev.2007.06.003](https://doi.org/10.1016/j.earscirev.2007.06.003).
  Regional empirical thresholds are not portable without local calibration.
- **Heatwave:** U.S. National Weather Service, [Heat Index](https://www.weather.gov/ama/heatindex).
  Documents the Rothfusz regression, applicability, adjustments and U.S.
  screening bands. These bands are not locally adopted Kerala triggers.
- **Drought:** World Meteorological Organization, *Standardized Precipitation
  Index User Guide*, [WMO library record 39629](https://library.wmo.int/idurl/4/39629);
  McKee, T. B., N. J. Doesken and J. Kleist (1993), *The relationship of
  drought frequency and duration to time scales*, [Colorado Climate Center
  copy](https://climate.colostate.edu/pdfs/relationshipofdroughtfrequency.pdf).
  Supports gamma-based precipitation standardization and SPI categories; a
  long local homogeneous reference series is still required.
- **Industrial air incident:** World Health Organization (2021), *WHO global
  air quality guidelines*, [publication 9789240034228](https://www.who.int/publications/i/item/9789240034228).
  Health guideline framework; not a legal Indian compliance standard. U.S.
  EPA [preferred/recommended air-quality dispersion models](https://www.epa.gov/scram/air-quality-dispersion-modeling-preferred-and-recommended-models)
  illustrate source, stack and meteorological inputs absent here.
- **Infrastructure failure:** IEC 60812:2018, *Failure modes and effects
  analysis (FMEA and FMECA)*, [IEC publication record](https://webstore.iec.ch/en/publication/26359);
  NIST Community Resilience Planning Guide above. Used for qualitative
  structure only; no unsupported criticality number is assigned.
- **Compound cyclone/flood:** WMO [Tropical Cyclone Programme](https://wmo.int/activities/tropical-cyclone-programme)
  and Zscheischler et al. support the warning/compound-process context. No
  interaction coefficient or joint event probability is inferred.
- **Compound rainfall/drainage:** FHWA HEC-22 Rational Method reference above;
  only user-entered scenario flow/capacity is compared, not actual drainage
  performance.

## Other reviewed data sources

Existing local/global data source provenance and limitations remain in
`DATA_SOURCES.md`, `DATA_QUALITY_REPORT.md`, and
`data/reference/DATA_PROVENANCE_REGISTER.json`. Scientific citations do not
replace those dataset-specific quality, coverage, coordinate, temporal,
licence or suitability reviews.

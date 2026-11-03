# Consequence assessment methodology

## Current engine boundary

The application returns consequence pathways and evidence status. It does not
estimate casualties, damage, service loss, displaced population, healthcare
demand, or recovery duration. Such estimates require a compatible hazard
footprint/time window, geocoded exposed inventory, vulnerability/damage
functions, and independently reviewed impacts.

The shared consequence contract in `src/disaster_models/common.py` separates:

1. **Population:** an entered affected-population count is identified as
   user-supplied context, not independently verified, spatially matched, or
   estimated. If blank, exposed population is unavailable.
2. **Infrastructure:** multiselect items are user-nominated services/assets,
   not verified locations, exposure, condition, or outage.
3. **Environment/economy:** unquantified without pollutant/emissions,
   environmental, agricultural, economic or service-outcome evidence.
4. **Cascades:** pathways are model-specific but unresolved when local
   topology, event sequence or failure records are absent.

## Hazard-specific consequence pathways

| Hazard | Potential pathways represented, without asserting local impact |
|---|---|
| Flood | Runoff/drainage/outfall, river/backwater, inundation duration, access, service and population exposure. |
| Cyclone | Wind exposure, rain/coastal water, facility continuity and debris/access effects. |
| Earthquake | Ground motion/site conditions, building fragility, aftershocks and utility/road disruption. |
| Landslide | Susceptible slope/material, rainfall/saturation, runout and road/settlement/utility exposure. |
| Heatwave | Duration/activity/shade/hydration, health vulnerability and water/power/health-service demand. |
| Drought | Precipitation anomaly, storage/demand, water supply, agriculture, ecosystems and distributional impacts. |
| Industrial incident | Pollutant-specific concentration, duration, location, wind/dispersion and exposed population. |
| Infrastructure failure | Failure mode, dependent service topology, redundancy, backup capacity and restoration. |
| Cyclone + flood | Component-wise wind and flood effects with event timing, spatial overlap, river/coastal/drainage dependencies unresolved. |
| Heavy rainfall + drainage failure | Optional simplified catchment inflow versus user-supplied design capacity; actual ponding depends on network hydraulics and boundary conditions. |

## Evidence classes

- **Observed/source-reported:** the source or user says a value was observed;
  provenance and measurement quality remain explicit.
- **User-described:** an unverified condition, asset, or count.
- **Derived:** unit conversion, intensity arithmetic, idealized pressure,
  heat-index regression, SPI or Rational Method calculation.
- **Modelled scenario:** a conditional result produced from explicitly
  supplied hypothetical values.
- **Unavailable:** no compatible evidence; not zero impact.

## Minimum future quantitative consequence prerequisites

- Event-specific and validated hazard footprint/intensity and timing.
- Current administrative boundary and compatible CRS/positional uncertainty.
- Facility, road, utility and population inventories with completeness and
  provenance.
- Local fragility/damage and service-interruption functions with applicability
  evidence.
- Observed consequence labels, independent review and leakage-safe validation.
- Privacy, fairness, accessibility, and responsible-authority review.

The model must remain fail-closed until these are documented. Conceptual
service pathways are not vulnerability findings or operational instructions.

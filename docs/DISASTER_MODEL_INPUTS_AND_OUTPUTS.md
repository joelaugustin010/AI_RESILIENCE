# Disaster model inputs and outputs

Ranges below are software input bounds, not local hazard thresholds. Optional
fields may be blank; a missing input produces an unavailable/insufficient
result rather than zero hazard.

| Existing option | Inputs and units | Validation / calculation | Structured output |
|---|---|---|---|
| Flood | Rainfall depth 0-5,000 mm; period 1 h, 24 h, 72 h or unsupported/unspecified; catchment 0.0001-1,000,000 ha; runoff coefficient 0-1; river reading in source-reported m. | Mean depth/duration; optional `Q=0.00277778 C i A`; no river threshold comparison. | Rainfall descriptor, optional peak runoff, raw river status, unclassified flood severity, consequence pathways. |
| Cyclone | Wind 0-500 km/h. | Convert to m/s; `q=0.5*1.225*v²` Pa. | Wind speed and idealized dynamic pressure; no structural load or damage. |
| Earthquake | Optional reported MMI integer 1-12. | Validate ordinal scale and provide qualitative description. | Reported MMI, source-verification caveat, no site shaking estimate. |
| Landslide | Rainfall 0-5,000 mm with explicit period; optional antecedent rainfall 0-20,000 mm. | Mean rate only. No local threshold or terrain model is applied. | Rainfall context and explicit missing susceptibility/trigger status. |
| Heatwave | Temperature -100 to 70 °C; relative humidity 0-100%. | Convert to °F and use NWS Rothfusz regression only for temperature >=80 °F and RH >=40%; apply published humidity adjustments. | Heat index °F/°C and NWS screening band with regional/non-medical caveat, or unavailable. |
| Drought | CSV with exactly `month,precipitation_mm`; ISO `YYYY-MM`; finite non-negative monthly totals, one station, consecutive months, at least 360 values spanning at least 30 years. | Calendar-month gamma fit on positive values, zero-probability adjustment and standard-normal quantile; at least 30 positive reference values and variability for the calendar month. | SPI-1, category, target month, reference count or explicit insufficiency. |
| Industrial incident | Optional pollutant name, concentration, comparator, units and averaging periods. | Compare only finite non-negative values with positive comparator and exactly matching explicit unit/period strings. | Concentration/reference ratio only; no legal compliance or source result. |
| Infrastructure failure | Optional service/failure description, status and nominated services/assets. | Qualitative FMEA/dependency review; no probability or risk-priority number. | Failure context, conceptual consequence pathways and operator evidence requirements. |
| Compound: cyclone + flood | Cyclone wind and flood/rainfall fields independently. | Run both component modules; no component addition or joint probability. | Separate component assessment objects and unresolved interaction state. |
| Compound: heavy rainfall + drainage failure | Rain depth/period, area, coefficient and optional drainage capacity in m³/s. | Rational Method flow; compare only with explicitly supplied positive capacity. Nominal capacity excess is `max(Q - capacity, 0)`. | Input-dependent scenario hydraulic indicator with flow, capacity, ratio and nominal excess; not an observed drain failure, overflow, flood or impact. |

## Common output semantics

- `assessment_type`: observation review, scenario assessment, or evidence
  review. The only possible prediction flag is `false`.
- `result_status`: hazard-specific sufficiency/indicator state, not a risk
  category.
- `potential_consequences`: population and infrastructure status remain
  unestimated/unverified; its `categories` field separates human,
  infrastructure, environmental and economic outcomes. Each currently reports
  no observed impact. Categories report `INSUFFICIENT EVIDENCE` except for
  infrastructure in the complete heavy-rainfall/drainage scenario, which
  carries a simulated flow/capacity indicator but explicitly no impact
  estimate. Human, environmental and economic consequence estimates remain
  unavailable.
- `recommendations`: unranked, hazard-specific actions in before/during/after
  phases plus a separate `long_term` planning item. The `category` field
  distinguishes prevention, preparedness, response, recovery, and long-term
  planning. Each item includes relevance/trigger, supporting evidence or
  authority, scope and limitations.
- `evidence.dataset_relevance`: lists repository datasets considered and why
  each is context-only/excluded.
- `validation`: explicitly says local disaster prediction validation was not
  performed. The separate historical rainfall measurement benchmark does not
  change this status and is not a flood prediction.

The downloadable CSV/HTML report serializes the complete structured model
result, including compound component assessments. No missing value is
converted to zero.

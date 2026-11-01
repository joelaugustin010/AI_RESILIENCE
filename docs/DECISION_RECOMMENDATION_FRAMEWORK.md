# Decision recommendation framework

## Output policy

Each registered hazard model returns three separate lists: `before`, `during`,
and `after`. Recommendation entries include an action, a condition/trigger,
evidence or authority needed, and the invariant label
**“Unranked; follow competent authority guidance.”**

Recommendations are planning prompts tied to a hazard-specific process. They
are not individualized evacuation orders, medical diagnoses, safe-route
advice, verified operational instructions, or claims of benefit.

| Workflow option | Before | During | After |
|---|---|---|---|
| Flood | Verify catchment/drainage/outfalls and source data. | Follow official warnings; report observed inundation; no route inference. | Record high-water marks, duration and service outages; inspect before repair. |
| Cyclone | Monitor IMD/local advisories; review shelter/communications/continuity. | Follow official shelter/evacuation instructions; no safe location produced. | Wait for clearance; obtain qualified structural/utility inspection. |
| Earthquake | Secure contents and arrange preparedness/building review. | Use recognized protective actions and official response. | Avoid damaged structures; qualified structural and utility inspections. |
| Landslide | Review official slope advisories; qualified drainage/slope inspection. | Keep clear of active failures; obey authority closures. | Maintain closures pending geotechnical inspection; document evidence safely. |
| Heatwave | Review heat-health plan, cool spaces, water, outreach. | Follow official health guidance and seek medical care for symptoms. | Document service demand/outages; review continuity and impacts. |
| Drought | Review official supply/storage and contingency triggers. | Coordinate restrictions/allocation with water authorities. | Audit source recovery, service interruption and distributional impacts. |
| Industrial incident | Maintain pollutant inventory, calibration, contacts and notification. | Follow regulator/incident command; preserve measurements; avoid suspected release. | Independent environmental sampling and source review before attribution. |
| Infrastructure failure | Confirm owner, critical function, backup, redundancy and single points. | Notify operator/incident command; record verified service status. | Operator-led restoration, failure analysis and repair verification. |
| Cyclone + flood | Reconcile time-matched advisories, rainfall, river/coastal monitoring, services. | Follow competent-authority warnings; do not combine warning levels. | Common-time event records and independent impact review. |
| Heavy rainfall + drainage failure | Verify drainage design, catchment, rainfall intensity basis and blockages. | Follow flood advisories; report observed ponding/blockage. | Record water levels, outfall and failures; qualified hydraulic review. |

Recommendations are not ranked by model output. Existing user-supplied budget
and action-priority calculations remain arithmetic only. Intervention ranking
requires comparable, locally verified expected risk reduction, exposed
population, infrastructure importance, feasibility, cost, duration,
uncertainty, policy weights and demonstrated/estimated benefit distinctions.

During an emergency, current instructions from competent authorities supersede
this exploratory software.

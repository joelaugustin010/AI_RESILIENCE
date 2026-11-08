# AI RESILIENCE — competition pitch
**Submission date:** Monday, 9 November 2026  
**Project:** Evidence-led multi-hazard disaster resilience for Kochi and Kerala

This is a presentation-ready slide plan and speaking script. Keep the scientific boundaries visible; do not replace them with stronger claims.

## Slide 1 — The problem
**Kochi faces connected risks, not isolated hazards.**
- Heavy rainfall can interact with tides, rivers, drainage limits and exposed infrastructure.
- Cyclones can compound rainfall and coastal disruption.
- Heat, drought, earthquakes, landslides, industrial incidents and infrastructure failures require different evidence and response plans.
- Decision-makers need understandable evidence, uncertainty and practical preparedness actions—not an unexplained risk score.

**Speaker notes:**  
“Our project starts from a simple problem: disaster impacts are shaped by connected hazards, exposed people and infrastructure, and the decisions taken before an event. A single red risk score cannot explain what should be done.”

## Slide 2 — Our solution
**One evidence-to-action workspace.**
- Ten registered hazards, including compound scenarios.
- Scenario assessment that records conditions, evidence quality, uncertainty and missing information.
- Exposure and infrastructure context for Kochi.
- Preparedness, response and recovery actions with their rationale.
- Research ML evidence displayed separately from scenario calculations and official warnings.

**Speaker notes:**  
“AI RESILIENCE brings the evidence and the next decision into one workflow. It helps users ask what is known, what is missing, who or what may be exposed, and which actions are sensible under the selected scenario.”

## Slide 3 — What the system does
**From inputs to a defensible decision.**
1. Select a hazard or compound scenario.
2. Enter available conditions and local context.
3. Review source provenance, completeness and uncertainty.
4. Examine exposed services, dependencies and possible consequences.
5. Compare preparedness options and review recommended actions.
6. Export or explain the assessment, including limitations.

**Speaker notes:**  
“The workflow does not hide missing data. It shows the evidence behind an assessment and distinguishes an assumption from an observation. Recommendations are preparedness guidance, not guarantees that damage will be prevented.”

## Slide 4 — Machine-learning work: what is actually demonstrated
**Nine persisted research model cards; zero independently validated operational models.**
- Three continuous research estimates: next-day precipitation, next-day maximum temperature, and 24-hour cyclone wind change.
- Six exploratory classification/association tasks: extreme rainfall, high temperature, drought, cyclone rapid intensification, earthquake aftershock, and cyclone–rainfall association.
- Best recorded regression comparisons on one temporal holdout:
  - Precipitation MAE 5.794 vs persistence 6.385 (9.24% lower).
  - Maximum-temperature MAE 0.645 vs persistence 0.691 (6.67% lower).
  - Cyclone wind-change MAE 8.338 vs no-change 11.647 (28.41% lower).
- High-temperature classifier: F1 0.743 vs persistence F1 0.692 on one temporal holdout.
- Extreme-rainfall classifier: F1 0.425, equal to persistence; Brier 0.0888, worse than base-rate reference 0.0649.

**Speaker notes:**  
“We have built and persisted real supervised research models. Some regression tasks beat simple baselines on a chronological holdout. But that is not enough to call them validated forecasts. The rainfall classifier, for example, does not beat persistence on F1 and has worse probability error than its base-rate reference. We show these results transparently rather than overstating them.”

## Slide 5 — Ten hazards, different evidence maturity
| Hazard / scenario | Current ML evidence boundary |
|---|---|
| Flood | Rainfall forcing only; not flood occurrence or inundation |
| Cyclone | Retrospective intensity/wind-change research; not track or landfall forecast |
| Earthquake | Aftershock screening after an observed mainshock; not mainshock prediction |
| Landslide | No defensible supervised model; representative non-events are missing |
| Heatwave | High-temperature research screening; not an official heat-health warning |
| Drought | Meteorological rainfall-deficit research; not agricultural/hydrological drought |
| Industrial incident | No defensible supervised model; facility event/control panel is missing |
| Infrastructure failure | No defensible supervised model; asset failure/restoration panel is missing |
| Cyclone + flood | Exploratory concurrent association; not a joint probability or lead-time forecast |
| Heavy rainfall + drainage failure | Rainfall forcing plus deterministic scenario calculation; drainage state is assumed |

**Speaker notes:**  
“All ten hazards are represented in the decision workflow, but that does not mean ten predictive models exist. Where the evidence is not adequate, the system says so and retains scenario-based assessment rather than inventing predictions.”

## Slide 6 — Why trust the presentation?
**Evidence boundaries are part of the design.**
- Model cards preserve targets, features, metrics, baselines and limitations.
- Temporal holdout results are labelled as research-only.
- Independent spatial/temporal validation and calibration remain promotion requirements.
- Reanalysis grid-point weather is not local station measurement.
- Retrospective cyclone best-track data are not operational forecasts.
- The platform is not an IMD/KSDMA warning service; follow official authorities for real decisions.

**Speaker notes:**  
“Trust comes from showing where the evidence stops. We do not turn a model score into an emergency alert. The next scientific milestone is independent station and spatial validation, plus stronger event and non-event datasets for the hazards that currently lack them.”

## Slide 7 — Impact and next steps
**A practical preparedness prototype with a measurable research roadmap.**
- Improve local observation coverage and verified Kochi spatial layers.
- Complete independent spatial and temporal evaluation.
- Add representative, adjudicated event/non-event datasets for landslide, industrial and infrastructure risks.
- Verify map rendering, page navigation, model loading and deployment on the actual exhibition device.
- Work with domain experts and authorities before any operational use.

**Closing:**  
“Our goal is not to claim that disasters can be predicted perfectly. It is to make disaster decisions more transparent, evidence-based and actionable—while being honest about uncertainty.”

---

## 90-second opening pitch

“Good morning. Our project is AI RESILIENCE, an evidence-led disaster resilience platform focused on Kochi and Kerala.

Disasters rarely happen in isolation. Heavy rainfall can combine with high tides, rivers, drainage constraints and infrastructure exposure. A useful resilience system must therefore do more than display a risk score. It must explain the evidence, identify what is missing, show who or what may be exposed, and recommend practical preparedness actions.

AI RESILIENCE brings ten hazards and compound scenarios into one decision workflow. Users can examine conditions, source quality, uncertainty, infrastructure dependencies and mitigation priorities. We have also developed nine supervised machine-learning research models and compare their results with simple baselines. Some continuous estimates improve on their baselines in a chronological holdout, while other classifiers remain weak.

We do not claim that all ten hazards have predictive models, or that any model is an operational warning system. Landslide, industrial incident and infrastructure failure still need better verified training data, and all current models need independent validation.

Our central contribution is an understandable path from evidence to preparedness: show what is known, show what is uncertain, and help users decide what to do next.”

## Live demonstration sequence (5–7 minutes)
1. **Home:** introduce the Kochi-focused objective.
2. **Decision Workflow:** choose one hazard and show conditions, evidence, uncertainty, exposure and precautions.
3. **Kochi Map:** explain each visible layer and legend; distinguish land cover from hazard.
4. **ML Evidence & Demonstration:** show the complete model-card inventory, choose one model, compare it with its baseline and explain one limitation.
5. **Close:** state one practical mitigation action and the platform's non-operational status.

## Presenter checklist
- [ ] Verify the live app and all primary navigation pages on the actual demo device.
- [ ] Verify the ML Evidence & Demonstration page and all model-card rows.
- [ ] Verify the map layers/tiles load; explain their dates and source limitations.
- [ ] Use one preselected scenario with complete inputs to avoid live-demo delays.
- [ ] Keep official warning and emergency guidance boundaries visible.
- [ ] Do not claim independent validation, operational prediction, live satellite imagery or complete Kochi ward boundaries unless separately verified.

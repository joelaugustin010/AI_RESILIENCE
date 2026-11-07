# AI RESILIENCE — Competition demonstration guide

**Submission target:** Monday, 9 November 2026  
**Project focus:** evidence-led multi-hazard resilience for Kochi and Kerala

## 1. Recommended live demonstration (5–7 minutes)

1. Start on the AI RESILIENCE homepage and explain the Kochi-focused objective.
2. Open **Decision Workflow**. Select a hazard and show how the workflow combines conditions, evidence quality, uncertainty, exposed services and preparedness actions.
3. Open **Kochi Map**. Explain the legend before interpreting any layer. Distinguish land cover, infrastructure, exposure and hazard evidence; do not call a land-cover class a danger zone.
4. Open **ML Evidence & Demonstration**. Select a hazard and show the persisted model card, held-out metrics, baseline and validation gate.
5. Finish with one concrete mitigation action and one honest limitation. Explain that the system supports preparedness research and does not issue official warnings.

## 2. What the current supervised-learning work demonstrates

The repository contains nine persisted research model cards: six classifiers and three regressors. Their status is research-only; a single chronological holdout is not independent validation.

### Continuous regression results

| Research task | Held-out cases | Model MAE | Baseline MAE | MAE improvement |
|---|---:|---:|---:|---:|
| Next-day precipitation at Kochi reanalysis grid | 2,192 | 5.794 | 6.385 (persistence) | 9.24% |
| Next-day maximum temperature at Kochi reanalysis grid | 2,192 | 0.645 | 0.691 (persistence) | 6.67% |
| 24-hour cyclone wind change (storm-grouped research) | 1,753 | 8.338 | 11.647 (no-change) | 28.41% |

These are retrospective research estimates from the persisted model cards. Units are those recorded by the underlying datasets/model cards. They are not flood forecasts, heat-health warnings, cyclone track/landfall forecasts, or local impact predictions. The weather inputs are reanalysis grid-point data rather than local station observations; the cyclone model uses retrospective best-track data.

### Classification results and caution

- The high-temperature research classifier recorded F1 0.743, ROC-AUC 0.966 and average precision 0.756 on one temporal holdout. Its persistence baseline F1 was 0.692. The result is a promising research signal, not an operational heatwave declaration or calibrated local warning.
- The extreme-rainfall classifier recorded F1 0.425, equal to its persistence baseline F1 0.425. Its Brier score 0.0888 was worse than the base-rate reference 0.0649. Do not present its output as a reliable rainfall warning.
- The cyclone rapid-intensification, earthquake aftershock, drought and compound association models remain research-only, with task-specific limitations and/or insufficient independent evidence.

## 3. Ten-hazard coverage is not ten predictive models

The Decision Workflow represents all ten registered hazards and compound scenarios. The trained model evidence is uneven:

- Research models cover selected rainfall, temperature, drought, cyclone, aftershock and compound-association tasks.
- Landslide, industrial incident and infrastructure failure do not yet have defensible supervised models because representative verified event/non-event training panels are missing.
- Rainfall forcing evidence is not flood occurrence or inundation prediction.
- A cyclone/rainfall association is not a joint probability or a lead-time compound forecast.

The platform should retain its deterministic/scenario workflows and show evidence gaps instead of filling them with fabricated scores.

## 4. Scientific and safety statement for evaluators

**No model is currently independently validated for operational use.** The model cards record a single temporal holdout. Independent spatial/temporal evaluation, calibration, prospective monitoring, local observation coverage and domain-owner review remain necessary.

This project is a student research and preparedness prototype. It is not an official forecast, emergency alert or emergency-response service. For real decisions, follow IMD, KSDMA and district-authority guidance.

## 5. Final pre-submission verification checklist

- [ ] Open the deployed application and confirm every primary navigation page loads.
- [ ] Confirm the new **ML Evidence & Demonstration** page loads and displays persisted model cards.
- [ ] Demonstrate one Decision Workflow scenario and its precautions.
- [ ] Check Kochi map tiles/layers and explain the legend accurately.
- [ ] Verify that no research-only output is described as an operational warning.
- [ ] Capture screenshots of the homepage, Decision Workflow, Kochi Map and ML demonstration page.
- [ ] Keep the final source branch/commit and the presentation deck available for submission.

## 6. Reproducibility and current blocker

The Kerala cross-location rainfall experiment is tracked separately in PR #101. Its training/evaluation workflow has not produced a new result while GitHub Actions jobs are failing before runner assignment (zero runner ID, no steps, missing job-log blobs). Do not claim that experiment has trained or passed until a real run produces its report. Do not treat a failed runner allocation as a model result.

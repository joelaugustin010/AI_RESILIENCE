# Disaster-specific model training and independent evaluation

## Objective and current status

Keep the ten-hazard conditional scenario output available while adding trained models only where a suitable, documented dataset and defensible target variable exist. The current workflow uses transparent rule-based screening. Evaluation helpers score held-out predictions; they do not train a model or certify data. Do not label any hazard a validated predictive model until the gates below are passed.

## Ten independent tracks

| Track | Target to define before training | Required evidence |
|---|---|---|
| Flood | Event at named place/time or measured flood depth/extent | Timestamped rainfall, river/tide/drainage predictors and verified flood observations |
| Cyclone | Defined local impact or wind/rain target | Authoritative track/intensity history, local observations, timestamps and exposure context |
| Earthquake | Ground-motion or damage target | Authoritative event catalogue, local ground-motion/site data; damage labels for damage prediction |
| Landslide | Event in a defined place/time window or mapped impact | Verified inventory including non-event periods, antecedent rainfall, slope/geology |
| Heatwave | Official station/day classification or specified temperature outcome | Quality-controlled station observations, normals, time window and label definition |
| Drought | Defined index threshold or observed supply/agricultural impact | Rainfall/temperature, soil moisture/storage/supply and documented index/time scale |
| Industrial incident | Verified incident type or measured concentration at place/time | Incident records, substance/release data and monitoring; never infer plume from AQI alone |
| Infrastructure failure | Failure/outage of defined asset in a time window | Asset inventory, timestamped incident/outage records and predictors |
| Compound cyclone + flood | Joint co-occurrence or measured combined impact | Time-aligned cyclone, rainfall, water-level, drainage and impact records |
| Compound heavy rainfall + drainage failure | Defined waterlogging/flood impact under both conditions | Aligned rainfall, verified drainage status and observed impact labels |

These are target definitions to resolve, not claims that suitable datasets already exist.

## Data admission gate

1. Record publisher, exact source URL, retrieval date, version date, licence, geographic/time coverage, units, CRS/datum, update frequency and limitations.
2. Define event and non-event labels. Missing records are not automatically non-events.
3. Ensure predictors were available at prediction time; exclude post-event information and target leakage.
4. Audit missingness, duplicates, impossible values, station/asset identity, coordinate validity, CRS, time zones, sampling gaps and class imbalance.
5. Count independent event/non-event cases by location, time and class. If data are sparse or biased, document the gap instead of training a public-facing predictor.
6. Pin data version, preprocessing, feature list, code commit, random seed and dependency versions.

## Independent evaluation protocol

- Define target, prediction horizon, geography and intended use before inspecting test scores.
- Keep a final test set untouched until model/hyperparameters are fixed. For forecasting, split chronologically. For geographic transfer, hold out entire locations/wards/stations; random row splits alone are insufficient.
- Fit imputation, scaling, feature selection and resampling on training data only.
- Compare with a simple baseline: majority class or persistence for classification; historical/seasonal baseline for numeric forecasts.
- Classification: report prevalence, confusion matrix, event recall/sensitivity, specificity, precision, F1, balanced accuracy and precision-recall performance where appropriate. If probabilities are emitted, assess calibration and Brier score on independent data.
- Regression: report MAE, RMSE and baseline comparison. Include error distributions and performance by location/season where sample size permits.
- Report uncertainty where possible; disclose small test sets, rare-event uncertainty, false-negative consequences and transfer limits.
- Require a second-person review of provenance, target leakage, split design and metrics before claiming validation.

## Promotion gates

1. Data candidate: source/licence recorded; target and coverage described.
2. Research-ready: label audit, quality report and reproducible independent split.
3. Baseline evaluated on held-out data.
4. Candidate model beats baseline on predeclared metrics and passes critical subgroup checks.
5. Independent review completed and limitations recorded.
6. Keep results demonstrative unless suitable validation and domain-expert review support a stronger claim. Never replace official warnings or emergency instructions.

## Reporting record

For each hazard record target, horizon, geography, dataset versions/provenance/licence, event and non-event counts, exclusions, split method, baseline, model/version, metrics, uncertainty, subgroup results, leakage audit, reviewer, limitations, status and date.

## Preserve the current output

The ten-hazard rule-based output remains available for every selection. If data are unavailable or fail a gate, show the conditional scenario output and clearly state no trained predictive model is available for that hazard. Never fabricate probabilities or imply insufficient evidence means safety.

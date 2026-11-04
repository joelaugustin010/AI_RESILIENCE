# Ernakulam AI disaster risk assessment

The Disaster Probability page accepts current local observations in Simple or
Advanced Mode and sends them through one shared, hazard-specific assessment
engine. It covers exactly four hazards:

1. Flood and urban waterlogging.
2. Cyclone and coastal storm impacts.
3. Landslide.
4. Drought and water scarcity.

Preliminary risk categories summarize entered conditions. They are **not event
probabilities, validated forecasts, official warnings, or calibrated numerical
risk scores**. A probability is displayed only if an eligible model passes the
evidence, geographic scope, chronological validation, calibration, baseline,
and feature-schema gates.

## Page and inputs

The page shows the Ernakulam location selector, observation date/time, live-data
retrieval status, and source notes before mode selection. The location selector
contains the district-wide option, 13 municipalities, 82 grama panchayats in
the Kerala 2020 LSGI register, and Kochi Corporation in the current Kerala SEC
register. Register membership is not proof of local model coverage.

- **Simple Mode** groups everyday observations by hazard. Answers remain
  qualitative; they are never converted into scientific measurements.
- **Advanced Mode** groups optional readings by hazard and labels units. It
  includes rainfall intensity and 24/72-hour totals, rainfall duration and
  forecast total, datum-referenced water level and rate of rise, wind/gust,
  pressure, temperature, soil moisture, humidity, rainfall deficit, storm
  distance, coastal water anomaly, and slope. Missing readings remain missing.
  Entering water-level measurements requires a station and measurement
  reference.
- Both modes call the same four hazard-specific pipelines. Results use the
  same compact card format and provide contributing conditions, missing
  evidence, precautions, limitations, and source context.

Coordinates are not requested because user-supplied coordinates cannot
currently be verified against a reliable Ernakulam boundary. Manually entered
measurements and warnings are not independently verified.

## Data sources and current retrieval status

- **KSDMA flood report:** the project reuses the published 2022 Ernakulam
  district historical-scenario table in
  `data/reference/ksdma_ernakulam_flood_return_period_statistics_2022.json`.
  The page charts the six reported affected-area outputs by return period.
  The chart is district aggregate scenario context only; it is not an
  input-based forecast, a selected-locality estimate, or a probability for the
  selected observation time. The source metadata records retrieval on
  2026-10-31.
- **IMD:** API documentation and official warning links are provided. The
  unauthenticated current-weather/city-forecast endpoint check returned HTTP
  401; no token is configured, so no live IMD conditions or warnings are
  retrieved. The IMD gridded-data interface did not provide a verified,
  documented integration path for this page.
- **CWC/NWIC:** the portal is linked as a source, but the local telemetry
  rainfall CSV is excluded from current assessments. Its source-file match,
  station coordinates, time handling, and conflicting duplicate readings
  remain unresolved; the tagged station is not a district-wide observation.
- **Cyclone:** NOAA/NCEI IBTrACS regional tracks are source context only. Track
  positions have not been validated as Ernakulam impacts.
- **Landslide:** NASA catalog reports and the KSDMA/GSI susceptibility layer
  are described as context only. The catalog is incomplete and all three local
  susceptibility geometries fail validity checks.
- **Drought:** no verified Ernakulam drought-index, groundwater, reservoir, or
  drinking-water time series is present in the project data.

No automatic data retrieval or refresh is implemented. No dataset with
unverified source, station, time, unit, or geographic scope is silently used
as a current measurement.

## Assessment methods and limitations

There are no trained, validated Ernakulam input-prediction models in the
repository. The four hazard-specific model artifact paths are under
`models/hazards/ernakulam_input_models/`; none is currently eligible for use.
The page displays no model-generated probabilities or numerical scores.

When a model is absent or not suitable, the engine uses separate
hazard-specific preliminary rules:

- **Flood and urban waterlogging:** reported overflow, rising water, or pooling
  informs the concern category. Rainfall is context only; gauge datum,
  drainage, and tide observations are not retrieved.
- **Cyclone and coastal storm impacts:** a reported official warning or
  storm-like local conditions informs the category. Warnings are not verified;
  wind alone is not cyclone detection. Track, surge, and coastal exposure are
  not retrieved.
- **Landslide:** reported slope movement/cracks and reported wet-ground/rain
  combinations inform the category. No local susceptibility class is assigned.
- **Drought and water scarcity:** reported rainfall departure and water-supply
  impacts inform the category. No drought index, reservoir, or groundwater
  conditions are retrieved.

These are preliminary concern assessments, not event likelihoods. “Not enough
evidence” means available inputs do not establish the hazard's relevant local
indicators. Missing values are never treated as zero or as normal conditions.
Simple Mode answers are never mapped to scientific values.

Available source context includes three NASA catalog reports naming
Ernakulam/Erakulam across two reported dates; this is not a complete landslide
inventory or an event frequency. The KSDMA report lists historical modeled
flood-affected area from 458.67 km² at the 10-year return period to 596.45 km²
at the 500-year return period. Those scenario statistics are not current
conditions and cannot be assigned to any municipality or ward.

No new training data or labels were acquired for this input-prediction
workflow. Existing flood-severity labels, regional weather grids, storm
tracks, and event-only landslide catalogues do not supply correctly matched
Ernakulam predictors and event/non-event outcomes for the four targets.
Training or scoring on those data would not justify probabilities.

## Run and test

From the repository root:

```sh
python3 -m pytest -q tests/test_ernakulam_input_predictions.py tests/test_ernakulam_disaster_dashboard_app.py tests/test_ernakulam_disaster_dashboard.py
streamlit run app.py
```

Open the **AI Disaster Risk Assessment** page from the Streamlit navigation.
For official forecasts and emergency instructions, consult IMD and KSDMA
directly.

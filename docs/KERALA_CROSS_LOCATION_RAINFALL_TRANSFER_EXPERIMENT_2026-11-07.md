# Kerala cross-location rainfall transfer experiment

## Question

Can a next-day rainfall regression model trained on Kottayam, Wayanad and
Thiruvananthapuram reanalysis grid-point records transfer to a completely
held-out Kochi grid point?

## Protocol

- Target: next-day precipitation (mm/day).
- Candidate fitting: target dates before 2015, using only the three non-Kochi
  locations.
- Candidate selection: 2015 through 2019, still using only those three
  locations.
- Final fit: all three non-Kochi locations before 2020.
- Final test: Kochi target dates from 2020 onward. Kochi is excluded from
  fitting and candidate selection.
- Features are numeric current/prior weather values and calendar terms from
  the existing leakage-aware dataset builder. Location identifiers and all
  target-prefixed fields are excluded.
- Candidate estimators are the existing deployment-compatible scikit-learn
  regressors. Selection uses validation MAE only. The held-out test report
  includes equal-count regression reliability bins and mean prediction bias.
- Test comparisons include same-day rainfall persistence and a training-only
  calendar-month median climatology baseline. Both are evaluated on the same
  Kochi holdout, with paired seven-day moving-block bootstrap intervals for
  model MAE improvement. Promotion is blocked unless both lower confidence
  bounds are above zero.
- The holdout report also separates southwest-monsoon (June–September) error
  from other months and reports thresholded wet-day occurrence diagnostics at
  1 mm/day. These are descriptive diagnostics from a point regressor, not
  calibrated event probabilities.

## Interpretation

This is a spatial-and-temporal transfer experiment on modelled reanalysis
grid-point data, not station observations. A successful result would be
evidence of transfer to one held-out grid point only. It would not establish
Kerala-wide skill and would not predict flood occurrence, inundation, depth,
or impacts. The training script writes a research artifact and model card
outside the operational model registry. It must not be used for public
warnings, evacuation or asset decisions.

## Reproduction

After repository dependencies are installed:

```bash
python scripts/train_kerala_cross_location_rainfall.py
```

The script writes `model.joblib` and `model_card.json` under
`models/research/kerala_cross_location_rainfall_nextday/`. CI uploads these
as a short-lived research artifact; it does not add them to the release model
registry or promote them into the application. The focused compile/unit-test
preflight and training job is independent of the full test job and can also be
manually dispatched on this research branch.


## Reproducible CI input acquisition

The raw Open-Meteo weather files used by the shared ML engine are local,
uncommitted research inputs. A clean GitHub Actions checkout therefore does
not contain them. The isolated workflow now runs
`scripts/acquire_kerala_weather_transfer_data.py` before training. It fetches
the exact four location records, validates daily date coverage, field lengths,
numeric values and non-negative precipitation, writes per-file SHA-256 and
source metadata, and uploads an acquisition manifest with the model artifact.
This solves the missing-input failure mode in a clean checkout when the runner
is available. It does not prove that Open-Meteo reanalysis equals station
observations or that the model generalizes.

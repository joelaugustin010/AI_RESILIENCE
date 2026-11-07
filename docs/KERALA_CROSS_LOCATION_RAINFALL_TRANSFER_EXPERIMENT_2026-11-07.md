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
  regressors. Selection uses validation MAE only.
- Test comparison includes a same-day rainfall persistence baseline and a
  paired seven-day moving-block bootstrap interval for MAE improvement.

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
registry or promote them into the application.

# AI RESILIENCE — Kochi Disaster Preparedness Prototype

AI RESILIENCE is a student-built decision-support prototype for exploring disaster preparedness and urban resilience in Kochi/Ernakulam. It brings scenario exploration, spatial context, historical air-quality summaries, hospital-vulnerability evidence, data-readiness checks and mitigation planning into one Streamlit application.

## Run locally

Python 3.11 is recommended.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

If PowerShell blocks activation, use a permitted environment or run the virtual environment's Python directly; do not weaken device security settings without permission.

The homepage has its own implementation and customisation guide in
[`docs/HOMEPAGE_EXPERIENCE.md`](docs/HOMEPAGE_EXPERIENCE.md). To use your own
hero film, place it at `assets/videos/kerala_hero.mp4`; see
[`assets/videos/README.md`](assets/videos/README.md) for export settings.

Optional dependency sets:

- `requirements-data.txt` — PDF extraction and coordinate/geometry support used by some data-validation paths.
- `requirements-scripts.txt` — one-off acquisition and audit scripts only. The Streamlit app and standard test suite do not need these.

The application entry point is `app.py`; all pages are registered there through `st.navigation`.

## Suggested demonstration (5–7 minutes)

1. **Home** — open on the cinematic Kerala introduction: the landscape, the threats, why the evidence chain matters, and where each workspace fits.
2. **Decision Workflow** — change scenario inputs, review the result and explain which inputs affect it.
3. **Kochi Map** — inspect available geographic layers and point out coverage or boundary limitations.
4. **Air Pollution** — show historical monitoring summaries and explain why AQI alone cannot prove which factory caused pollution.
5. **Hospital Vulnerability / Cyclone + Flood** — show what evidence is needed before making exposure claims.
6. **Data Readiness** — review source provenance, integrity checks and unresolved blockers.
7. **Mitigation Budget / Smart Mitigation Design** — demonstrate practical planning based on clearly stated assumptions.

## Shared ML engine

The repository includes a shared, leakage-aware ML engine under `src/ml/`.
It is used as supplementary evidence; the deterministic, evidence-gated hazard
assessments remain authoritative.

```bash
python scripts/train_shared_ml_models.py
```

The command rebuilds the six research models from repository-held data,
performs chronological train/validation/test evaluation, and writes:

- `models/ml/<model_id>/model.joblib` and `model_card.json`
- `reports/ml_model_registry.json`
- `reports/ml_disaster_coverage.json`
- `reports/ml_validation_report.json`

Current coverage of the ten Decision Workflow hazards:

- **Research screening models:** Cyclone (24-hour rapid intensification) and Heatwave. Neither is independently validated.
- **Invalidated models:** Drought (the old 30-day target overlapped historical rainfall features) and Earthquake aftershock (the old seven-day outcome windows crossed temporal split boundaries). Their old metrics and inference are blocked pending corrected retraining.
- **Forcing evidence only:** Flood and Compound rainfall + drainage failure
  (extreme-rainfall screening; no flood, depth, or impact prediction).
- **Exploratory association:** Compound cyclone + flood (concurrent
  cyclone-proximity/rainfall association, including an ablation that tests
  whether cyclone features add incremental skill).
- **No defensible supervised model:** Landslide, Industrial incident, and Infrastructure
  failure, because representative labels or non-event samples are missing.

No shared model is independently validated, calibrated for decision use, or
suitable for warnings, evacuation, damage estimates, or operational planning.
The model cards record every threshold, split, holdout metric, calibration
diagnostic and limitation. See `docs/SHARED_ML_ENGINE.md`.

## Important limitations

- This is a student research and preparedness prototype, **not an official warning system** or emergency-response service.
- Do not present scenario scores as validated probabilities unless the relevant page explicitly documents a validated model, local data and evaluation.
- Historical air-quality readings describe the monitoring record; they do not independently identify a specific industrial source.
- A map layer is not proof of current exposure. Confirm source date, spatial reference system (CRS), coverage, geometry quality and limitations before drawing conclusions.
- Missing, synthetic, illustrative or unverified data must not be described as observed local facts.
- In an actual emergency, follow official Kerala State Disaster Management Authority, IMD and district-administration guidance.

## Quality checks

The repository's GitHub Actions workflow installs the declared dependencies, checks dependency consistency and scientific-library imports, compiles the Python application and research scripts, and runs the test suite. Check the latest workflow result before submission; a successful syntax check alone does not establish scientific validity.

## SDG relevance

The project is aligned conceptually with **SDG 11 (Sustainable Cities and Communities)** and **SDG 13 (Climate Action)** through disaster preparedness, risk communication and resilience planning. This alignment describes the project's goals, not an official SDG endorsement.

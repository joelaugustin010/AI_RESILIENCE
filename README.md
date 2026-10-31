# AI RESILIENCE

AI-powered disaster risk assessment and city resilience prototype, focused on
Kochi / Ernakulam, Kerala. It combines public hazard data, provenance checks,
research baseline models and a Streamlit app that helps explore evidence and
plan mitigation budgets.

> **Safety boundary.** This is an exploratory research prototype. It does not
> issue warnings, is not an official forecast, and its models are research
> baselines that have not been independently validated. Always follow official
> emergency guidance (KSDMA, IMD, CWC).

## Quick start

Requires Python 3.11 or newer.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt -r requirements-data.txt
streamlit run app.py
```

`app.py` is the application entry point. (`main.py` is only a placeholder and is
not used by the app.)

Run the tests:

```bash
python -m pytest -q
```

Tests that need locally acquired source files (PDFs, raw snapshots that are not
committed) are skipped automatically on a clean checkout.

## App pages

| Page | What it does |
| --- | --- |
| Decision Workflow | Connects evidence to a budget decision step by step |
| Disaster Intelligence Assistant | Answers questions grounded in the project's evidence files |
| Kochi Map | Licensed reference geometry and user-reviewed points |
| Air Pollution | AQI monitoring and evidence readiness for Kochi / Ernakulam |
| Data Readiness | Source provenance, validation status and analysis readiness |
| Hazard Model Lab | Training status of the hazard-specific models |
| Hospital Vulnerability | Hospital vulnerability assessment |
| Cyclone + Flood | Qualitative multi-hazard scenario worksheet |
| Flood Model Readiness | What is still needed before a flood probability model is defensible |
| Mitigation Budget | Budget arithmetic for user-supplied intervention estimates |
| Smart Mitigation Design Studio | Mitigation design options, such as integrated stormwater management |

## Repository layout

```
app.py              Streamlit entry point and navigation
app_pages/          One file per app page
src/                Domain logic (flood, air quality, spatial data, evidence fusion, ...)
scripts/             Data acquisition, audit and model-training scripts
models/              Research baseline models and their evaluation reports
data/raw/            Source files as acquired (never edited in place)
data/processed/      Derived files with provenance metadata
data/reference/      Source registries, status definitions and data notes
data/MULTI_HAZARD_MODEL_STATUS.md   Why most hazard models are not trained yet
docs/                Model design, data foundation, testing and data-acquisition notes
                    (start with SCIENTIFIC_MODEL_DESIGN.md and testing.md)
tests/, test_*.py    Test suite
.github/workflows/   CI tests and manual data-acquisition / training jobs
```

## Data and provenance rules

- Raw data is preserved exactly as acquired. Cleaning produces new files.
- Every dataset records its source, retrieval date, licence and SHA-256 in a
  `.metadata.json` file, and tests re-check those hashes.
- A source link is not a dataset, and an event catalogue is not a predictive
  model. Models are only marked trained when a target, leakage-safe predictors
  and a held-out evaluation exist. See `data/MULTI_HAZARD_MODEL_STATUS.md`.
- Some official reports are kept local only because their redistribution terms
  are not established. See `.gitignore` for the list.

### Line endings

Some provenance hashes were recorded from Windows (CRLF) files. `.gitattributes`
pins those exact CSVs to CRLF so the hash checks pass on Windows, macOS and
Linux. Do not re-save those files with different line endings.

## Models

Research baselines currently in `models/hazards/weather_baselines/`:
extreme next-day rainfall and high next-day temperature. Each ships with an
evaluation JSON that states its target, split dates and metrics. Flood and the
other hazard models are not trained yet; the readiness pages explain what data
is missing.

## Automation (GitHub Actions)

| Workflow | Purpose |
| --- | --- |
| Python tests | Runs on every push and pull request to `main` |
| Acquire public disaster data | Downloads catalogued public hydrology data |
| Acquire and store multi-hazard source data | Fetches sources for the non-flood hazards |
| Acquire INDOFLOODS and train flood research baseline | Manual flood baseline training |
| Train historical weather hazard baselines | Retrains the weather baselines |
| Acquire Kochi ward boundary reference candidate | Fetches the ward boundary candidate |

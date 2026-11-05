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

Optional dependency sets:

- `requirements-data.txt` — PDF extraction and coordinate/geometry support used by some data-validation paths (`pypdf`, `shapely`, `pyproj`).
- `requirements-scripts.txt` — one-off acquisition/audit scripts only (`openpyxl`, `mapbox-vector-tile`, `rasterio`). The Streamlit app and the standard test suite do not need these.

The application entry point is `app.py`; the Command Centre is the default landing page. All pages are registered in that file through `st.navigation`.

## Suggested demonstration (5–7 minutes)

1. **Command Centre** — introduce the problem and the evidence-first approach.
2. **Decision Workflow** — change scenario inputs, review the result and explain which inputs affect it.
3. **Kochi Map** — inspect available geographic layers and point out coverage or boundary limitations.
4. **Air Pollution** — show historical monitoring summaries and explain why AQI alone cannot prove which factory caused pollution.
5. **Hospital Vulnerability / Cyclone + Flood** — show what evidence is needed before making exposure claims.
6. **Data Readiness** — review source provenance, integrity checks, descriptive climate benchmarks and unresolved blockers.
7. **Mitigation Budget / Smart Mitigation Design** — demonstrate practical planning based on clearly stated assumptions.

The committed screening and climate reports are offline products; their builders and inputs are documented in `docs/REPRODUCING_REPORTS.md`.

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

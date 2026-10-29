# Test setup

## Clean checkout

The pull request workflow uses Windows and Python 3.11, installs the declared
application and PDF dependencies, checks the installed dependency graph, and
smoke-tests NumPy, SciPy, and scikit-learn imports before running pytest. The
workflow does not acquire or download research files.

For a local Python 3.11 run, create an environment and install the same
requirements:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-data.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "import numpy, scipy, sklearn; from scipy.ndimage import label; label(numpy.array([[1]], dtype=numpy.uint8)); print(numpy.__version__, scipy.__version__, sklearn.__version__)"
.\.venv\Scripts\python.exe -m pytest -q -ra --strict-markers
```

Several direct and transitive requirements are not version-pinned, so these
commands use the versions resolved at installation time; they are not a
platform-specific dependency lock. CI reports the versions selected for its
run with `pip freeze`. A reviewed lockfile should be added after a successful
Python 3.11 resolution and test run.

## Optional local research integrations

Tests that verify hashes, schemas, or extracts from locally acquired research
snapshots carry the `local_research` marker. They are skipped by default with
the missing files or opt-in setting in the skip reason. The regular suite
uses synthetic fixtures for validation logic and remains suitable for a clean
checkout.

When all referenced snapshots are locally available and permitted for local
analysis, run only those integration checks with:

```powershell
$env:AI_RESILIENCE_RUN_LOCAL_RESEARCH_TESTS = "1"
python -m pytest -q -ra --strict-markers -m local_research
```

No test downloads snapshots. A skipped local integration is not a successful
verification of the underlying source data.

## Python 3.11 verification status for this workspace

The Python 3.11 environment was created, but dependency installation could not
complete because the configured package host failed DNS resolution while pip
was retrieving the PyArrow wheel from `files.pythonhosted.org`. The installed
requirements and SciPy import could therefore not be verified here under
Python 3.11. The Python 3.11 compatibility status remains unverified until
the workflow or another clean Python 3.11 environment completes the import
check and test suite.

The failed Python 3.11 resolution had selected these package versions before
the download error: Streamlit 1.66.0, pydeck 0.9.3, pandas 3.1.0, NumPy 2.4.6,
Pillow 12.3.0, scikit-learn 1.9.1, pytest 9.2.0, Plotly 7.1.0, pypdf 6.21.4,
and SciPy 1.17.1. They were resolver selections, not an installed or tested
environment.

The completed local suite runs used the existing Python 3.15 sibling
environment without installing or changing it. Its package versions were
Streamlit 1.66.0, pydeck 0.9.3, pandas 3.0.6, NumPy 2.5.4, Pillow 12.3.0,
scikit-learn 1.9.1, SciPy 1.18.1, pytest 9.1.1, pypdf 6.21.2, and PyArrow
26.0.0; Plotly was not installed there. `pip check` reported no broken
requirements. SciPy's `ndimage.label` imported and executed successfully in
that Python 3.15 environment. These results do not verify Python 3.11.

On 2026-10-29, `python -m pytest -q -ra --strict-markers` completed with 155
passed, 3 skipped, and 13 passing subtests. The three skips are the two
ignored-PDF source checks and the ignored annual-AQI snapshot audit. With
`AI_RESILIENCE_RUN_LOCAL_RESEARCH_TESTS=1`,
`python -m pytest -q -ra --strict-markers -m local_research` completed with 3
passed and 155 deselected. Both runs used the same Python 3.15 interpreter;
test temporary files were directed into the isolated workspace after the
default sandbox denied fixture writes.

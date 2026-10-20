"""Small, read-only data helpers for the AI RESILIENCE demonstration."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = PROJECT_ROOT / "data" / "raw"


def load_dataset(filename: str, required_columns: list[str]) -> pd.DataFrame:
    """Load a project CSV and give a clear error for missing or malformed data."""
    path = RAW_DATA / filename
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")

    try:
        data = pd.read_csv(path, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as error:
        raise ValueError(f"Could not read {path.name}: {error}") from error

    missing = [column for column in required_columns if column not in data.columns]
    if missing:
        raise ValueError(f"{path.name} is missing required columns: {', '.join(missing)}")
    if data.empty:
        raise ValueError(f"{path.name} has no data rows.")
    return data

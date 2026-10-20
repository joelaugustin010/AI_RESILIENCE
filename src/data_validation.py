
"""Basic data validation for the AI RESILIENCE project."""

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

REQUIRED_COLUMNS = {
    "rainfall": ["date", "location", "rainfall_mm"],
    "flood_events": ["event_date", "location", "event_type"],
}


def validate_csv(file_path, dataset_type):
    """Check whether a CSV exists and contains valid required fields."""

    if dataset_type not in REQUIRED_COLUMNS:
        return False, ["Unknown dataset type."]

    path = Path(file_path)

    if not path.is_file():
        return False, [f"File not found: {path}"]

    if path.suffix.lower() != ".csv":
        return False, ["The file must have a .csv extension."]

    try:
        data = pd.read_csv(path)
    except (OSError, UnicodeError, pd.errors.ParserError) as error:
        return False, [f"Could not read CSV: {error}"]

    data.columns = data.columns.str.strip().str.lower()

    problems = []
    required = REQUIRED_COLUMNS[dataset_type]

    missing_columns = [
        column for column in required if column not in data.columns
    ]

    if missing_columns:
        problems.append(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    if data.empty:
        problems.append("The CSV contains no data rows.")

    if not missing_columns and not data.empty:
        if data["location"].isna().any():
            problems.append("Some rows have no location.")

        if (data["location"].astype(str).str.strip() == "").any():
            problems.append("Some rows have an empty location.")

        if dataset_type == "rainfall":
            dates = pd.to_datetime(data["date"], errors="coerce")
            if dates.isna().any():
                problems.append("Some dates are missing or invalid.")

            rainfall = pd.to_numeric(
                data["rainfall_mm"], errors="coerce"
            )

            if rainfall.isna().any():
                problems.append("Some rainfall values are missing or invalid.")
            elif (rainfall < 0).any():
                problems.append("Rainfall cannot be negative.")

        if dataset_type == "flood_events":
            dates = pd.to_datetime(data["event_date"], errors="coerce")

            if dates.isna().any():
                problems.append("Some event dates are missing or invalid.")

            if (
                data["event_type"].isna().any()
                or (data["event_type"].astype(str).str.strip() == "").any()
            ):
                problems.append("Some event types are missing.")

    if problems:
        return False, problems

    return True, [
        f"Validation passed: {len(data)} data rows checked.",
        "This checks basic structure and values, not source authenticity.",
    ]

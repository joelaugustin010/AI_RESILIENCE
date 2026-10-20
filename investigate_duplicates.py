"""Report duplicate CWC rainfall station-time records without changing raw data."""

from pathlib import Path
import sys

import pandas as pd


# Resolve paths from this script so it works regardless of VS Code's working folder.
PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_FILE = PROJECT_ROOT / "data" / "raw" / "kerala.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "cwc_rainfall_conflicts.csv"

KEY_COLUMNS = ["Station", "Data Acquisition Time"]
RAINFALL_COLUMN = "Telemetry Hourly Rainfall (mm)"
REQUIRED_COLUMNS = [*KEY_COLUMNS, RAINFALL_COLUMN]


def main() -> int:
    """Validate the source, summarize duplicate groups, and export conflicts."""
    if not SOURCE_FILE.is_file():
        print(f"ERROR: Source CSV was not found: {SOURCE_FILE}", file=sys.stderr)
        return 1

    try:
        # Keep this original frame unchanged; parsed timestamps are kept separately.
        source = pd.read_csv(SOURCE_FILE, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        print(f"ERROR: Could not read {SOURCE_FILE}: {exc}", file=sys.stderr)
        return 1

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in source.columns]
    if missing_columns:
        print(
            "ERROR: Source CSV is missing required column(s): "
            + ", ".join(missing_columns),
            file=sys.stderr,
        )
        return 1

    # Invalid timestamps cannot safely be assigned to a station-time group.
    parsed_times = pd.to_datetime(
        source["Data Acquisition Time"], dayfirst=True, errors="coerce"
    )
    invalid_timestamp_count = int(parsed_times.isna().sum())
    valid_key_mask = source["Station"].notna() & parsed_times.notna()
    valid_rows = source.loc[valid_key_mask]
    valid_times = parsed_times.loc[valid_key_mask]

    # Mark every row in each duplicate key group, then count groups by distinct
    # observed rainfall measurements. Missing rainfall values remain missing.
    # Use parsed timestamps so different text formats for the same time still match.
    normalized_keys = pd.DataFrame(
        {"Station": valid_rows["Station"], "Data Acquisition Time": valid_times},
        index=valid_rows.index,
    )
    duplicate_mask = normalized_keys.duplicated(KEY_COLUMNS, keep=False)
    duplicate_indices = valid_rows.index[duplicate_mask]

    duplicate_rows = source.loc[duplicate_indices]
    duplicate_keys = normalized_keys.loc[duplicate_indices]
    if duplicate_indices.empty:
        conflict_indices = duplicate_indices
        duplicate_group_count = 0
        conflicting_group_count = 0
        matching_group_count = 0
    else:
        # Group summaries are temporary; the export below retains every source column.
        grouped_rainfall = duplicate_rows[RAINFALL_COLUMN].groupby(
            [duplicate_keys["Station"], duplicate_keys["Data Acquisition Time"]],
            sort=False,
        )
        value_counts = grouped_rainfall.nunique(dropna=True)
        conflicting_keys = value_counts[value_counts > 1].index
        conflicts_mask = pd.MultiIndex.from_arrays(
            [duplicate_keys["Station"], duplicate_keys["Data Acquisition Time"]]
        ).isin(conflicting_keys)
        conflict_indices = duplicate_indices[conflicts_mask]
        duplicate_group_count = int(len(value_counts))
        conflicting_group_count = int((value_counts > 1).sum())
        matching_group_count = duplicate_group_count - conflicting_group_count

    # Exact full-row duplicate check is scoped to rows in duplicate station-time groups.
    exact_duplicate_rows = int(duplicate_rows.duplicated(keep=False).sum())

    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Export original source rows and columns only; no values are corrected or merged.
        source.loc[conflict_indices].to_csv(OUTPUT_FILE, index=False)
    except (OSError, PermissionError) as exc:
        print(f"ERROR: Could not write conflict report {OUTPUT_FILE}: {exc}", file=sys.stderr)
        return 1

    print("=== CWC RAINFALL DUPLICATE SUMMARY ===")
    print(f"Source file: {SOURCE_FILE}")
    print(f"Duplicate station-time groups: {duplicate_group_count:,}")
    print(f"Rows in duplicate groups: {len(duplicate_indices):,}")
    print(f"Groups with conflicting rainfall values: {conflicting_group_count:,}")
    print(f"Groups with matching rainfall values: {matching_group_count:,}")
    print(f"Exact full-row duplicate rows within duplicate groups: {exact_duplicate_rows:,}")
    print(f"Rows with invalid timestamps (excluded from grouping): {invalid_timestamp_count:,}")
    print(f"Conflict report: {OUTPUT_FILE}")
    print("Source data was read only; no duplicate values were changed or removed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only diagnostics for the F.C.S. Mananthavadi river-level records."""

from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATASETS = {
    "manual": (
        ROOT / "data/raw/rwl_manual_hr_kerala_sw_031_2021_2025.csv",
        "River Water Level Manual Hourly (meter)",
    ),
    "telemetry": (
        ROOT / "data/raw/rwl_tel_hr_kerala_sw_031_2021_2025.csv",
        "River Water Level Telemetry Hourly (meter)",
    ),
}
STATION = "F.C.S. Mananthavadi"
TIME_COLUMN = "Data Acquisition Time"
META_COLUMNS = [
    "Agency", "District", "River", "Basin", "Local River", "Latitude",
    "Longitude", "RL_of_zeroGauge", "MeanSeaLevel",
]


def load_station(label: str, path: Path, value_column: str) -> tuple[pd.DataFrame, pd.Series] | None:
    """Read one source and return the station rows plus parsed timestamp series."""
    if not path.is_file():
        print(f"ERROR: {label} file not found: {path}", file=sys.stderr)
        return None
    try:
        frame = pd.read_csv(path, low_memory=False)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        print(f"ERROR: Could not read {label} file {path}: {exc}", file=sys.stderr)
        return None

    print(f"{label} CSV columns and inferred types: {frame.dtypes.astype(str).to_dict()}")

    required = ["Station", TIME_COLUMN, value_column, *META_COLUMNS]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        print(f"ERROR: {label} file is missing columns: {', '.join(missing)}", file=sys.stderr)
        return None

    times = pd.to_datetime(frame[TIME_COLUMN], dayfirst=True, errors="coerce")
    station_mask = frame["Station"].astype("string").str.strip().str.casefold().eq(STATION.casefold())
    station_rows = frame.loc[station_mask].copy()
    station_times = times.loc[station_mask]
    station_rows["_parsed_time"] = station_times
    station_rows["_numeric_value"] = pd.to_numeric(
        station_rows[value_column], errors="coerce"
    )
    return station_rows, times


def print_report(label: str, path: Path, value_column: str, loaded: tuple[pd.DataFrame, pd.Series]) -> None:
    """Print compact file, metadata, sampling, distribution, and gap summaries."""
    rows, all_times = loaded
    times = rows["_parsed_time"].dropna().sort_values()
    values = rows["_numeric_value"].dropna()
    print(f"\n=== {label.upper()} ===")
    print(f"File: {path}")
    print(f"Columns: {len(pd.read_csv(path, nrows=0).columns)}; station rows: {len(rows):,}")
    print(f"Station date range: {times.min()} to {times.max()}")
    print(f"Invalid station timestamps: {int(rows['_parsed_time'].isna().sum()):,}")
    print(f"Source file date range: {all_times.min()} to {all_times.max()}")
    print("Station metadata rows (unique):")
    print(rows[META_COLUMNS].drop_duplicates().to_string(index=False))

    if not values.empty:
        print("Measurement distribution (column label states metres):")
        print(values.describe(percentiles=[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]).round(3).to_string())

    intervals = rows.sort_values("_parsed_time")["_parsed_time"].diff().dropna()
    print("Most common timestamp intervals:")
    print(intervals.value_counts().head(5).to_string())

    ordered = rows.dropna(subset=["_parsed_time", "_numeric_value"]).sort_values("_parsed_time")
    changes = ordered["_numeric_value"].diff().abs()
    if not changes.empty and changes.notna().any():
        index = changes.idxmax()
        current = ordered.loc[index]
        previous = ordered.loc[ordered.index[ordered.index.get_loc(index) - 1]]
        print(
            "Largest adjacent absolute change: "
            f"{abs(current['_numeric_value'] - previous['_numeric_value']):.3f} m "
            f"from {previous['_parsed_time']} ({previous['_numeric_value']:.3f}) "
            f"to {current['_parsed_time']} ({current['_numeric_value']:.3f}); "
            f"elapsed {current['_parsed_time'] - previous['_parsed_time']}"
        )
        print(
            "Lowest/highest records: "
            f"{values.min():.3f} / {values.max():.3f} m"
        )


def main() -> int:
    loaded: dict[str, tuple[pd.DataFrame, pd.Series]] = {}
    for label, (path, value_column) in DATASETS.items():
        result = load_station(label, path, value_column)
        if result is None:
            return 1
        loaded[label] = result
        print_report(label, path, value_column, result)

    manual_rows = loaded["manual"][0]
    telemetry_rows = loaded["telemetry"][0]
    manual_times = set(manual_rows["_parsed_time"].dropna())
    telemetry_times = set(telemetry_rows["_parsed_time"].dropna())
    print("\n=== COMPARISON ===")
    print(f"Station coordinates match: {set(map(tuple, manual_rows[['Latitude', 'Longitude']].drop_duplicates().values)) == set(map(tuple, telemetry_rows[['Latitude', 'Longitude']].drop_duplicates().values))}")
    print(f"Exact timestamp overlap: {len(manual_times & telemetry_times):,}")
    print("No readings are changed, converted, or written by this diagnostic.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

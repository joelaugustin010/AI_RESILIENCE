
from pathlib import Path
import pandas as pd

folder = Path("data/raw")

# 1. Inspect duplicate CWC rainfall records
print("\n=== CWC RAINFALL DUPLICATES ===")

rain = pd.read_csv(folder / "kerala.csv", low_memory=False)
rain["Data Acquisition Time"] = pd.to_datetime(
    rain["Data Acquisition Time"],
    dayfirst=True,
    errors="coerce"
)

duplicate_mask = rain.duplicated(
    ["Station", "Data Acquisition Time"],
    keep=False
)

duplicates = rain.loc[duplicate_mask].sort_values(
    ["Station", "Data Acquisition Time"]
)

print("Rows belonging to duplicate groups:", len(duplicates))
print("\nFirst 15 duplicate rows:")
print(
    duplicates[
        [
            "Station",
            "District",
            "Latitude",
            "Longitude",
            "Data Acquisition Time",
            "Telemetry Hourly Rainfall (mm)"
        ]
    ].head(15).to_string(index=False)
)

# 2. Inspect unusually high river levels
river_files = {
    "manual": (
        "rwl_manual_hr_kerala_sw_031_2021_2025.csv",
        "River Water Level Manual Hourly (meter)"
    ),
    "telemetry": (
        "rwl_tel_hr_kerala_sw_031_2021_2025.csv",
        "River Water Level Telemetry Hourly (meter)"
    )
}

for name, (filename, value_col) in river_files.items():
    print(f"\n=== {name.upper()} RIVER LEVELS ===")

    df = pd.read_csv(folder / filename, low_memory=False)
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    print("\nHighest 10 readings:")
    print(
        df.nlargest(10, value_col)[
            [
                "Station",
                "District",
                "River",
                "Latitude",
                "Longitude",
                "RL_of_zeroGauge",
                "MeanSeaLevel",
                "Data Acquisition Time",
                value_col
            ]
        ].to_string(index=False)
    )

    print("\nStation-level ranges:")
    print(
        df.groupby("Station")[value_col]
        .agg(["count", "min", "median", "max"])
        .round(3)
        .to_string()
    )

print("\nAudit complete. No source files were modified.")

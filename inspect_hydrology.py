from pathlib import Path
import pandas as pd

folder = Path("data/raw")

files = {
    "manual_rainfall": (
        "rainfall_manual_hr_kerala-sw_kl_1991_2020.csv",
        "Manual Hourly Rainfall (mm)"
    ),
    "manual_river": (
        "rwl_manual_hr_kerala_sw_031_2021_2025.csv",
        "River Water Level Manual Hourly (meter)"
    ),
    "telemetry_river": (
        "rwl_tel_hr_kerala_sw_031_2021_2025.csv",
        "River Water Level Telemetry Hourly (meter)"
    ),
    "cwc_rainfall": (
        "kerala.csv",
        "Telemetry Hourly Rainfall (mm)"
    ),
}

station_sets = {}

for name, (filename, value_col) in files.items():
    df = pd.read_csv(folder / filename, low_memory=False)

    df["Data Acquisition Time"] = pd.to_datetime(
        df["Data Acquisition Time"],
        dayfirst=True,
        errors="coerce"
    )

    stations = set(
        df["Station"].dropna().astype(str).str.strip()
    )
    station_sets[name] = stations

    print(f"\n--- {name} ---")
    print("Rows:", len(df))
    print("Unique stations:", len(stations))
    print(
        "Valid timestamps:",
        df["Data Acquisition Time"].notna().sum()
    )
    print(
        "Date range:",
        df["Data Acquisition Time"].min(),
        "to",
        df["Data Acquisition Time"].max()
    )
    print(
        "Duplicate station-time rows:",
        df.duplicated(
            ["Station", "Data Acquisition Time"]
        ).sum()
    )
    print("Missing measurements:", df[value_col].isna().sum())
    print(
        "Measurement range:",
        df[value_col].min(), "to", df[value_col].max()
    )

print("\n--- STATION OVERLAP ---")

for a, b in [
    ("manual_rainfall", "manual_river"),
    ("manual_rainfall", "telemetry_river"),
    ("manual_river", "telemetry_river"),
    ("manual_rainfall", "cwc_rainfall"),
]:
    overlap = station_sets[a] & station_sets[b]
    print(f"{a} vs {b}: {len(overlap)} matching station names")
    print("Examples:", sorted(overlap)[:10])

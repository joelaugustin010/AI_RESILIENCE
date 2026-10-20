"""Descriptive analytics for source-preserving Kerala hydrology observations.

These observations have no verified event outcome labels. This module reports
what is present in each source file and never converts the values into risk
categories or danger-level comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class HydrologyDataset:
    dataset_id: str
    label: str
    file_name: str
    measurement_column: str
    unit: str
    mode: str
    source_note: str
    source_url: str
    warning: str


DATASETS = {
    "rainfall_manual": HydrologyDataset(
        "rainfall_manual", "Kerala SW manual rainfall (hourly)",
        "rainfall_manual_hr_kerala-sw_kl_1991_2020.csv",
        "Manual Hourly Rainfall (mm)", "mm", "rainfall",
        "Kerala Surface Water Department; NWDP resource lists manual hourly rainfall.",
        "https://nwdp.nwic.gov.in/en/dataset/rainfall-manual-hourly-kerala-sw-department/resource/ceb9ffcf-927b-4b34-8ab5-6c3098dd95a9",
        "The filename says 1991–2020, but this local copy's observed timestamps run only from 2000 to 2014. Sampling is irregular and the source timezone is not stated.",
    ),
    "rainfall_cwc": HydrologyDataset(
        "rainfall_cwc", "CWC telemetry rainfall (hourly)", "kerala.csv",
        "Telemetry Hourly Rainfall (mm)", "mm", "rainfall",
        "Agency column says CWC; probable match to the NWDP CWC Kerala 2021–2025 resource. The local file was renamed and was not checksum-matched to the portal export.",
        "https://nwdp.nwic.gov.in/dataset/rainfall-cwc-telemetry-hourly/resource/654dd5af-ec2c-4439-a8a5-f9bf5d61ab74",
        "Contains 1,471 duplicate station-time groups, including 324 with conflicting values. Raw points are shown without deduplication or accumulation.",
    ),
    "river_manual": HydrologyDataset(
        "river_manual", "Kerala SW manual river level", "rwl_manual_hr_kerala_sw_031_2021_2025.csv",
        "River Water Level Manual Hourly (meter)", "m", "river",
        "Kerala Surface Water Department; NWDP manual river-level resources describe values in metres.",
        "https://nwdp.nwic.gov.in/dataset/river-water-level-manual-hourly-kerala-sw-godavari/resource/fe95a85e-142d-4acf-83fc-24499afc546b",
        "Gauge zero and mean-sea-level reference conventions are unresolved. F.C.S. Mananthavadi has a previously flagged large change across a long gap. Some River/Basin labels conflict with the station's district/coordinates (for example, Mananthavadi is labeled River=Luni); do not use them for spatial attribution until the provider confirms them.",
    ),
    "river_telemetry": HydrologyDataset(
        "river_telemetry", "Kerala SW telemetry river level", "rwl_tel_hr_kerala_sw_031_2021_2025.csv",
        "River Water Level Telemetry Hourly (meter)", "m", "river",
        "Kerala Surface Water Department; NWDP telemetry river-level resource covers Kerala 2021–2025.",
        "https://nwdp.nwic.gov.in/dataset/river-water-level-telemetry-hourly-kerala-surface-water-department/resource/a6de190e-40b6-484b-ad4c-a9f811f061ba",
        "Gauge zero and mean-sea-level reference conventions are unresolved. F.C.S. Mananthavadi has a previously flagged large change across a long gap. Some River/Basin labels conflict with the station's district/coordinates (for example, Mananthavadi is labeled River=Luni); do not use them for spatial attribution until the provider confirms them.",
    ),
}


class HydrologyDataError(ValueError):
    """Raised when a source file cannot support the requested descriptive view."""


def load_observations(
    dataset_id: str, root: str | Path = PROJECT_ROOT
) -> tuple[pd.DataFrame, dict[str, int | str | None]]:
    """Read a source CSV and return valid plotting rows plus QA counts.

    The file on disk is read-only. The returned frame is a separate in-memory
    view. Rows with invalid times or values are counted and excluded only from
    the chart, never removed from the source file.
    """
    if dataset_id not in DATASETS:
        raise HydrologyDataError(f"Unknown hydrology dataset: {dataset_id}")
    spec = DATASETS[dataset_id]
    path = Path(root) / "data" / "raw" / spec.file_name
    try:
        raw = pd.read_csv(path, low_memory=False)
    except (OSError, pd.errors.ParserError, UnicodeError) as exc:
        raise HydrologyDataError(f"Could not read {path}: {exc}") from exc

    required = {"Station", "Data Acquisition Time", spec.measurement_column}
    missing = sorted(required - set(raw.columns))
    if missing:
        raise HydrologyDataError("Missing required column(s): " + ", ".join(missing))

    times = pd.to_datetime(raw["Data Acquisition Time"], errors="coerce", dayfirst=True)
    values = pd.to_numeric(raw[spec.measurement_column], errors="coerce")
    stations = raw["Station"].astype("string").str.strip()
    valid = (times.notna() & values.notna() & stations.notna() & stations.ne("")).fillna(False)
    plot_data: dict[str, pd.Series] = {
        "timestamp": times.loc[valid],
        "station": stations.loc[valid],
        "value": values.loc[valid].astype(float),
    }
    if "District" in raw.columns:
        plot_data["district"] = raw["District"].astype("string").str.strip().loc[valid]
    plot = pd.DataFrame(plot_data).sort_values(["timestamp", "station"], kind="stable").reset_index(drop=True)

    # Duplicate groups are counted on valid station-time rows. Conflicts are
    # groups where at least two different numeric measurements occur.
    key_rows = pd.DataFrame({"station": stations.loc[valid], "timestamp": times.loc[valid], "value": values.loc[valid]})
    group_sizes = key_rows.groupby(["station", "timestamp"], dropna=False).size()
    value_counts = key_rows.groupby(["station", "timestamp"], dropna=False)["value"].nunique()
    duplicate_mask = group_sizes.gt(1)
    qa: dict[str, int | str | None] = {
        "raw_rows": int(len(raw)),
        "valid_rows": int(valid.sum()),
        "invalid_timestamp_rows": int(times.isna().sum()),
        "invalid_measurement_rows": int(values.isna().sum()),
        "missing_station_rows": int(stations.isna().sum() + stations.eq("").fillna(False).sum()),
        "duplicate_station_time_groups": int(duplicate_mask.sum()),
        "conflicting_station_time_groups": int((duplicate_mask & value_counts.gt(1)).sum()),
        "station_count": int(plot["station"].nunique()),
        "start": plot["timestamp"].min().isoformat() if not plot.empty else None,
        "end": plot["timestamp"].max().isoformat() if not plot.empty else None,
    }
    return plot, qa


def station_gap_summary(series: pd.DataFrame) -> dict[str, float | int | None]:
    """Describe observed intervals; without a documented schedule, do not infer missing rows."""
    times = pd.to_datetime(series["timestamp"], errors="coerce").dropna().drop_duplicates().sort_values()
    intervals = times.diff().dropna().dt.total_seconds() / 3600
    return {
        "unique_timestamps": int(times.size),
        "median_interval_hours": float(intervals.median()) if not intervals.empty else None,
        "maximum_observed_gap_hours": float(intervals.max()) if not intervals.empty else None,
    }


def rainfall_station_comparison(observations: pd.DataFrame) -> pd.DataFrame:
    """Return comparable per-station descriptive rainfall statistics in mm.

    Values are raw recorded observations, not daily totals. This avoids making
    completeness assumptions or silently summing repeated source rows.
    """
    if observations.empty:
        return pd.DataFrame(columns=["Station", "Records", "Median (mm)", "95th percentile (mm)", "Maximum (mm)"])
    result = observations.groupby("station")["value"].agg(
        Records="size",
        **{"Median (mm)": "median", "95th percentile (mm)": lambda x: x.quantile(0.95), "Maximum (mm)": "max"},
    )
    return result.reset_index().rename(columns={"station": "Station"}).sort_values("Station").reset_index(drop=True)


def filter_observations(
    observations: pd.DataFrame,
    station: str,
    start: object | None = None,
    end: object | None = None,
) -> pd.DataFrame:
    """Select a station and inclusive date range without aggregating source rows."""
    selected = observations.loc[observations["station"].eq(station)].copy()
    if start is not None:
        selected = selected.loc[selected["timestamp"].dt.date >= pd.Timestamp(start).date()]
    if end is not None:
        selected = selected.loc[selected["timestamp"].dt.date <= pd.Timestamp(end).date()]
    return selected.reset_index(drop=True)

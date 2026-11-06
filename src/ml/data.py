"""Dataset construction from traceable, repository-held sources.

Every builder returns a tabular frame plus a provenance dictionary.  Builders
never download data, never synthesise labels, and never use future values as
predictors.  Target columns are named with a ``target_`` prefix so the leakage
guard in :mod:`src.ml.features` can reject them from a feature list.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.ml.paths import (
    CYCLONE_ROOT,
    EARTHQUAKE_ROOT,
    LANDSLIDE_ROOT,
    WEATHER_ROOT,
)

KOCHI_LAT = 9.947276
KOCHI_LON = 76.29921
EARTH_RADIUS_KM = 6371.0088

WEATHER_FILES: dict[str, tuple[str, int]] = {
    "kochi": ("kochi_daily_weather_1991_2025.json", 1991),
    "kottayam": ("kottayam_daily_weather_2000_2025.json", 2000),
    "wayanad": ("wayanad_daily_weather_2000_2025.json", 2000),
    "thiruvananthapuram": ("thiruvananthapuram_daily_weather_2000_2025.json", 2000),
}

WEATHER_NUMERIC = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
)


@dataclass
class Dataset:
    """A model-ready frame and its provenance."""

    name: str
    frame: pd.DataFrame
    target_column: str
    date_column: str
    feature_columns: list[str]
    provenance: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        missing = [
            column
            for column in [self.target_column, self.date_column, *self.feature_columns]
            if column not in self.frame.columns
        ]
        if missing:
            raise ValueError(f"{self.name}: missing dataset columns {missing}")


def haversine_km(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> np.ndarray:
    """Great-circle distance in kilometres, vectorised over numpy inputs."""
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lon1 = np.radians(np.asarray(lon1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    lon2 = np.radians(np.asarray(lon2, dtype=float))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def _json_weather(path: Path, location: str) -> pd.DataFrame:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Weather source is unreadable: {path}") from exc
    daily = payload.get("daily")
    if not isinstance(daily, dict):
        raise RuntimeError(f"Weather source has no daily block: {path}")
    frame = pd.DataFrame(daily)
    frame["date"] = pd.to_datetime(frame["time"], errors="coerce").dt.normalize()
    frame["location"] = location
    for column in WEATHER_NUMERIC:
        frame[column] = pd.to_numeric(frame.get(column), errors="coerce")
    frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    return frame[["date", "location", *WEATHER_NUMERIC]]


def load_weather(location: str = "kochi") -> pd.DataFrame:
    """Load one traceable daily weather record.

    ``kochi`` uses the 1991-2025 reanalysis grid-point record.  Other locations
    use their 2000-2025 records.  All values are modelled reanalysis output, not
    station observations; callers must preserve that distinction.
    """
    key = location.casefold()
    if key not in WEATHER_FILES:
        raise ValueError(f"Unknown weather location: {location!r}")
    filename, _ = WEATHER_FILES[key]
    path = WEATHER_ROOT / filename
    if not path.exists():
        raise RuntimeError(f"Weather source is missing: {path}")
    frame = _json_weather(path, key)
    frame.attrs["source_path"] = str(path.relative_to(path.parents[5]))
    frame.attrs["source_type"] = "MODELLED_REANALYSIS_GRID_POINT_NOT_STATION_OBSERVATION"
    return frame


def load_all_weather_locations() -> pd.DataFrame:
    """Load the four available reanalysis records for pooled research models."""
    frames = []
    for location in WEATHER_FILES:
        try:
            frames.append(load_weather(location))
        except RuntimeError:
            continue
    if len(frames) < 2:
        raise RuntimeError("At least two weather records are required for a pooled model.")
    return pd.concat(frames, ignore_index=True).sort_values(["location", "date"])


def load_cyclone_tracks(min_year: int = 1991) -> pd.DataFrame:
    """Load IBTrACS North Indian Ocean best tracks with a documented wind priority.

    ``USA_WIND`` (1-minute sustained, knots) is preferred for homogeneity;
    ``NEWDELHI_WIND`` then ``WMO_WIND`` fill gaps.  Agency changes are recorded
    as a limitation because they introduce inhomogeneity.
    """
    matches = sorted(CYCLONE_ROOT.glob("ibtracs_north_indian_ocean_*.csv"))
    if not matches:
        raise RuntimeError("IBTrACS North Indian Ocean best-track file is missing.")
    path = matches[0]
    tracks = pd.read_csv(path, low_memory=False)
    required = {"SID", "SEASON", "ISO_TIME", "LAT", "LON"}
    if not required.issubset(tracks.columns):
        raise RuntimeError(f"IBTrACS file lacks required columns: {sorted(required - set(tracks.columns))}")
    tracks["time"] = pd.to_datetime(tracks["ISO_TIME"], errors="coerce")
    tracks["season"] = pd.to_numeric(tracks["SEASON"], errors="coerce")
    for column in (
        "LAT", "LON", "USA_WIND", "WMO_WIND", "NEWDELHI_WIND",
        "USA_PRES", "WMO_PRES", "NEWDELHI_PRES", "STORM_SPEED", "DIST2LAND",
    ):
        tracks[column] = pd.to_numeric(tracks.get(column), errors="coerce")

    tracks["wind_kt"] = (
        tracks["USA_WIND"].fillna(tracks["NEWDELHI_WIND"]).fillna(tracks["WMO_WIND"])
    )
    tracks["pressure_hpa"] = (
        tracks["USA_PRES"].fillna(tracks["WMO_PRES"]).fillna(tracks["NEWDELHI_PRES"])
    )
    tracks["wind_source"] = np.select(
        [
            tracks["USA_WIND"].notna(),
            tracks["NEWDELHI_WIND"].notna(),
            tracks["WMO_WIND"].notna(),
        ],
        ["USA_WIND", "NEWDELHI_WIND", "WMO_WIND"],
        default="unavailable",
    )
    tracks = tracks.rename(
        columns={
            "SID": "storm_id",
            "LAT": "latitude",
            "LON": "longitude",
            "STORM_SPEED": "storm_speed_kt",
            "DIST2LAND": "distance_to_land_km",
            "NATURE": "nature",
            "SUBBASIN": "subbasin",
        }
    )
    tracks = tracks[
        tracks["time"].notna()
        & tracks["latitude"].notna()
        & tracks["longitude"].notna()
        & tracks["wind_kt"].notna()
        & (tracks["season"] >= min_year)
        & tracks["nature"].isin(["TS", "MX", "ET", "DS"])
    ].copy()
    tracks = tracks.sort_values(["storm_id", "time"]).reset_index(drop=True)
    tracks.attrs["source_path"] = str(path.relative_to(path.parents[5]))
    tracks.attrs["wind_priority"] = "USA_WIND > NEWDELHI_WIND > WMO_WIND"
    return tracks[
        [
            "storm_id", "season", "time", "nature", "subbasin", "latitude", "longitude",
            "wind_kt", "pressure_hpa", "wind_source", "storm_speed_kt", "distance_to_land_km",
        ]
    ]


def load_earthquakes(min_magnitude: float = 2.5) -> pd.DataFrame:
    """Load the USGS regional catalogue retained in the repository."""
    matches = sorted(EARTHQUAKE_ROOT.glob("usgs_*events*.csv"))
    if not matches:
        raise RuntimeError("USGS regional earthquake catalogue is missing.")
    path = matches[0]
    frame = pd.read_csv(path, low_memory=False)
    required = {"time", "latitude", "longitude", "depth", "mag"}
    if not required.issubset(frame.columns):
        raise RuntimeError("Earthquake catalogue lacks required columns.")
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce", utc=True)
    for column in ("latitude", "longitude", "depth", "mag"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["time", "latitude", "longitude", "depth", "mag"])
    frame = frame[frame["mag"] >= min_magnitude].sort_values("time").reset_index(drop=True)
    frame.attrs["source_path"] = str(path.relative_to(path.parents[5]))
    frame.attrs["catalogue_limit_note"] = (
        "USGS query is capped at 20,000 events and is not a complete local seismicity catalogue."
    )
    return frame


def load_landslides() -> pd.DataFrame:
    """Load the NASA Global Landslide Catalog (reported events only)."""
    matches = sorted(LANDSLIDE_ROOT.glob("nasa_global_landslide_catalog*.csv"))
    if not matches:
        raise RuntimeError("NASA Global Landslide Catalog is missing.")
    path = matches[0]
    frame = pd.read_csv(path, low_memory=False)
    frame["event_date"] = pd.to_datetime(frame["event_date"], errors="coerce", format="mixed")
    frame["latitude"] = pd.to_numeric(frame["latitude"], errors="coerce")
    frame["longitude"] = pd.to_numeric(frame["longitude"], errors="coerce")
    frame.attrs["source_path"] = str(path.relative_to(path.parents[5]))
    frame.attrs["catalogue_limit_note"] = (
        "Reported-event inventory, not a complete inventory; it has no representative non-event sample."
    )
    return frame


def _calendar_features(frame: pd.DataFrame) -> pd.DataFrame:
    if "date" in frame.columns:
        calendar = frame["date"]
    elif "time" in frame.columns:
        calendar = frame["time"]
    else:
        raise ValueError("Calendar features require a 'date' or 'time' column.")
    day = calendar.dt.dayofyear
    frame["doy_sin"] = np.sin(2 * np.pi * day / 365.25)
    frame["doy_cos"] = np.cos(2 * np.pi * day / 365.25)
    frame["month_sin"] = np.sin(2 * np.pi * calendar.dt.month / 12.0)
    frame["month_cos"] = np.cos(2 * np.pi * calendar.dt.month / 12.0)
    if "time" in frame.columns:
        hour = frame["time"].dt.hour + frame["time"].dt.minute / 60.0
        frame["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
        frame["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)
    return frame


def _weather_lag_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.sort_values(["location", "date"]).copy()
    grouped = frame.groupby("location", sort=False)
    for column in WEATHER_NUMERIC:
        for lag in (1, 2, 3, 7):
            frame[f"{column}_lag{lag}"] = grouped[column].shift(lag)
        frame[f"{column}_prior3_mean"] = grouped[column].transform(
            lambda series: series.shift(1).rolling(3, min_periods=2).mean()
        )
        frame[f"{column}_prior7_mean"] = grouped[column].transform(
            lambda series: series.shift(1).rolling(7, min_periods=4).mean()
        )
    frame["rain_3d_sum"] = grouped["precipitation_sum"].transform(
        lambda series: series.shift(1).rolling(3, min_periods=2).sum()
    )
    frame["rain_7d_sum"] = grouped["precipitation_sum"].transform(
        lambda series: series.shift(1).rolling(7, min_periods=4).sum()
    )
    frame["rain_30d_sum"] = grouped["precipitation_sum"].transform(
        lambda series: series.shift(1).rolling(30, min_periods=20).sum()
    )
    frame["rain_90d_sum"] = grouped["precipitation_sum"].transform(
        lambda series: series.shift(1).rolling(90, min_periods=60).sum()
    )
    frame["dry_days_14"] = grouped["precipitation_sum"].transform(
        lambda series: (series.shift(1) < 1.0).rolling(14, min_periods=7).sum()
    )
    frame["tmax_prior30_mean"] = grouped["temperature_2m_max"].transform(
        lambda series: series.shift(1).rolling(30, min_periods=20).mean()
    )
    frame["tmax_anomaly_30d"] = frame["temperature_2m_max"] - frame["tmax_prior30_mean"]
    return frame


def build_weather_target_dataset(
    location: str = "kochi",
    *,
    lead_days: int = 1,
    target: str = "extreme_rainfall",
) -> Dataset:
    """Build a next-day extreme-rainfall or high-temperature research dataset.

    The target stays continuous; the training layer estimates the event
    threshold from training-era target dates only.  This prevents validation and
    test outcomes from influencing the label definition.
    """
    frame = load_weather(location)
    frame = _weather_lag_features(frame)
    frame = _calendar_features(frame)

    if target == "extreme_rainfall":
        target_column = "target_rain_nextday"
        frame[target_column] = frame.groupby("location")["precipitation_sum"].shift(-lead_days)
    elif target == "high_temperature":
        target_column = "target_tmax_nextday"
        frame[target_column] = frame.groupby("location")["temperature_2m_max"].shift(-lead_days)
    elif target == "drought_onset":
        target_column = "target_rain30_future"
        # Sum the next 30 days (tomorrow through day 30).  Do not shift the
        # rolling result again: that would silently move the target window to
        # days 30-59 and break the documented 30-day outlook.
        future_rain = (
            frame.groupby("location")["precipitation_sum"]
            .transform(lambda series: series.shift(-1).rolling(30, min_periods=30).sum())
        )
        frame[target_column] = future_rain
        lead_days = 30
    else:
        raise ValueError(f"Unsupported weather target: {target!r}")

    frame["target_date"] = frame["date"] + pd.Timedelta(days=lead_days)
    feature_columns = [
        column
        for column in frame.columns
        if column not in {
            "date", "location", "target_date", target_column,
            "target_rain_nextday", "target_tmax_nextday", "target_rain30_future",
        }
        and pd.api.types.is_numeric_dtype(frame[column])
    ]
    frame = frame.dropna(subset=[target_column, "target_date"]).reset_index(drop=True)
    provenance = {
        "source": frame.attrs.get("source_path", f"weather/{location}"),
        "source_type": frame.attrs.get(
            "source_type", "MODELLED_REANALYSIS_GRID_POINT_NOT_STATION_OBSERVATION"
        ),
        "location": location,
        "lead_days": lead_days,
        "target": target,
    }
    return Dataset(
        name=f"weather_{target}_{location}",
        frame=frame,
        target_column=target_column,
        date_column="target_date",
        feature_columns=feature_columns,
        provenance=provenance,
        notes=[
            "Reanalysis grid-point values, not station observations.",
            "Features use current and prior values only; the target is future.",
            "Event thresholds are estimated on training target dates only.",
        ],
    )


def _nearest_fix_index(
    times: np.ndarray,
    target: np.datetime64,
    *,
    tolerance_hours: float,
) -> int | None:
    """Return the nearest track fix within a time tolerance, else ``None``."""
    position = int(np.searchsorted(times, target))
    candidates = []
    if position < len(times):
        candidates.append(position)
    if position - 1 >= 0:
        candidates.append(position - 1)
    best_index: int | None = None
    best_gap = float("inf")
    for candidate in candidates:
        gap_hours = abs(
            (times[candidate] - target) / np.timedelta64(1, "h")
        )
        if gap_hours <= tolerance_hours and gap_hours < best_gap:
            best_index = int(candidate)
            best_gap = float(gap_hours)
    return best_index


def build_cyclone_intensification_dataset(min_year: int = 1991) -> Dataset:
    """Build a 24-hour rapid-intensification dataset from IBTrACS tracks.

    Track fixes are not assumed to be exactly six-hourly.  The future and lag
    values are matched by actual timestamps within an explicit tolerance, and a
    row is dropped when no valid 18-30 hour future fix exists.
    """
    tracks = load_cyclone_tracks(min_year=min_year)
    tracks = tracks.sort_values(["storm_id", "time"]).reset_index(drop=True).copy()
    future_time = np.full(len(tracks), np.datetime64("NaT"), dtype="datetime64[ns]")
    future_wind = np.full(len(tracks), np.nan)
    wind_change = {lag: np.full(len(tracks), np.nan) for lag in (6, 12, 24)}
    pressure_change = {lag: np.full(len(tracks), np.nan) for lag in (6, 12, 24)}

    for _, group in tracks.groupby("storm_id", sort=False):
        group = group.sort_values("time")
        order = group.index.to_numpy()
        times = group["time"].to_numpy()
        wind = group["wind_kt"].to_numpy(dtype=float)
        pressure = group["pressure_hpa"].to_numpy(dtype=float)
        for position, row_index in enumerate(order):
            current_time = times[position]
            target = current_time + np.timedelta64(24, "h")
            matched = _nearest_fix_index(times, target, tolerance_hours=6.0)
            if matched is not None and matched > position:
                future_time[row_index] = times[matched]
                future_wind[row_index] = wind[matched]
            for lag in (6, 12, 24):
                prior_target = current_time - np.timedelta64(lag, "h")
                prior = _nearest_fix_index(
                    times, prior_target, tolerance_hours=(6.0 if lag == 24 else 3.0)
                )
                if prior is not None and prior < position:
                    wind_change[lag][row_index] = wind[position] - wind[prior]
                    pressure_change[lag][row_index] = pressure[position] - pressure[prior]

    tracks["future_time_24h"] = pd.to_datetime(future_time)
    tracks["future_wind_24h"] = future_wind
    for lag in (6, 12, 24):
        tracks[f"wind_chg_{lag}h"] = wind_change[lag]
        tracks[f"pressure_chg_{lag}h"] = pressure_change[lag]
    interval_hours = (
        tracks["future_time_24h"] - tracks["time"]
    ).dt.total_seconds() / 3600.0
    tracks["valid_24h"] = interval_hours.between(18.0, 30.0) & tracks["future_wind_24h"].notna()

    tracks["abs_latitude"] = tracks["latitude"].abs()
    tracks["subbasin_AS"] = (tracks["subbasin"] == "AS").astype(int)
    tracks["wind_squared"] = tracks["wind_kt"] ** 2
    tracks = _calendar_features(tracks)
    tracks["target_date"] = tracks["future_time_24h"]
    tracks["target_ri_24h"] = (tracks["future_wind_24h"] - tracks["wind_kt"]).where(tracks["valid_24h"])
    tracks = tracks.dropna(subset=["target_ri_24h", "target_date"]).reset_index(drop=True)

    feature_columns = [
        "wind_kt", "wind_squared", "pressure_hpa", "latitude", "longitude", "abs_latitude",
        "distance_to_land_km", "storm_speed_kt", "wind_chg_6h", "wind_chg_12h", "wind_chg_24h",
        "pressure_chg_6h", "pressure_chg_12h", "pressure_chg_24h", "subbasin_AS",
        "doy_sin", "doy_cos", "month_sin", "month_cos", "hour_sin", "hour_cos",
    ]
    provenance = {
        "source": tracks.attrs.get("source_path", "cyclone/IBTrACS"),
        "wind_priority": tracks.attrs.get("wind_priority"),
        "storms": int(tracks["storm_id"].nunique()),
        "rows": int(len(tracks)),
    }
    return Dataset(
        name="cyclone_rapid_intensification_24h",
        frame=tracks,
        target_column="target_ri_24h",
        date_column="target_date",
        feature_columns=feature_columns,
        provenance=provenance,
        notes=[
            "Best-track reanalysis, not an operational forecast.",
            "USA_WIND is preferred; agency changes create inhomogeneity.",
            "The label is a >=30 kt increase over the next ~24 hours.",
        ],
    )


def _daily_cyclone_proximity() -> pd.DataFrame:
    tracks = load_cyclone_tracks(min_year=1991)
    tracks["date"] = tracks["time"].dt.normalize()
    tracks["distance_kochi_km"] = haversine_km(
        tracks["latitude"], tracks["longitude"], KOCHI_LAT, KOCHI_LON
    )
    daily = (
        tracks.groupby("date")
        .agg(
            cyclone_min_distance_km=("distance_kochi_km", "min"),
            cyclone_max_wind_kt=("wind_kt", "max"),
            cyclone_fixes=("wind_kt", "size"),
        )
        .reset_index()
    )
    return daily


def build_compound_cyclone_rainfall_dataset() -> Dataset:
    """Build a daily cyclone-proximity / extreme-rainfall association dataset.

    This is an association dataset for testing whether cyclone proximity changes
    the odds of an extreme-rainfall day.  It is not a joint-probability forecast:
    the cyclone position and rainfall are concurrent, and only 1991-2025 Kochi
    reanalysis rainfall is available.
    """
    weather = load_weather("kochi")
    daily = _daily_cyclone_proximity()
    frame = weather.merge(daily, on="date", how="left")
    frame["cyclone_min_distance_km"] = frame["cyclone_min_distance_km"].fillna(9999.0)
    frame["cyclone_max_wind_kt"] = frame["cyclone_max_wind_kt"].fillna(0.0)
    frame["cyclone_fixes"] = frame["cyclone_fixes"].fillna(0).astype(int)
    frame["cyclone_near_500"] = (frame["cyclone_min_distance_km"] <= 500).astype(int)
    frame["cyclone_near_300"] = (frame["cyclone_min_distance_km"] <= 300).astype(int)
    frame["cyclone_distance_capped"] = frame["cyclone_min_distance_km"].clip(upper=2000)
    frame["cyclone_wind_x_near"] = frame["cyclone_max_wind_kt"] * frame["cyclone_near_500"]
    frame = frame.sort_values("date").reset_index(drop=True)
    frame["prior_rain_1d"] = frame["precipitation_sum"].shift(1)
    frame["prior_rain_3d"] = frame["precipitation_sum"].shift(1).rolling(3, min_periods=2).sum()
    frame["prior_rain_7d"] = frame["precipitation_sum"].shift(1).rolling(7, min_periods=4).sum()
    frame["prior_rain_30d"] = frame["precipitation_sum"].shift(1).rolling(30, min_periods=20).sum()
    frame = _calendar_features(frame)
    frame["near500_x_prior7"] = frame["cyclone_near_500"] * frame["prior_rain_7d"]
    frame["near500_x_month_sin"] = frame["cyclone_near_500"] * frame["month_sin"]
    frame["near500_x_month_cos"] = frame["cyclone_near_500"] * frame["month_cos"]
    frame["target_date"] = frame["date"]
    frame["target_extreme_rain"] = frame["precipitation_sum"]

    feature_columns = [
        "cyclone_near_500", "cyclone_near_300", "cyclone_distance_capped",
        "cyclone_max_wind_kt", "cyclone_fixes", "cyclone_wind_x_near",
        "prior_rain_1d", "prior_rain_3d", "prior_rain_7d", "prior_rain_30d",
        "month_sin", "month_cos", "doy_sin", "doy_cos",
        "near500_x_prior7", "near500_x_month_sin", "near500_x_month_cos",
    ]
    frame = frame.dropna(subset=["target_extreme_rain", "target_date"]).reset_index(drop=True)
    return Dataset(
        name="compound_cyclone_rainfall_interaction",
        frame=frame,
        target_column="target_extreme_rain",
        date_column="target_date",
        feature_columns=feature_columns,
        provenance={
            "weather_source": "Open-Meteo ERA5-family reanalysis, Kochi grid point",
            "cyclone_source": "IBTrACS North Indian Ocean best tracks",
            "proximity_definition": "minimum great-circle distance to any 6-hourly track fix on the same date",
        },
        notes=[
            "Concurrent association dataset, not a lead-time forecast.",
            "Cyclone proximity is rare: interpret interaction estimates with wide uncertainty.",
            "Extreme-rain threshold is estimated on training dates only.",
        ],
    )


def build_aftershock_dataset() -> Dataset:
    """Build a mainshock-to-aftershock occurrence dataset from USGS events.

    A mainshock is M>=5.0.  The label is whether at least one M>=4.0 event occurs
    within 50 km and 7 days after it.  Features use only information available at
    the mainshock time.  This is sequence screening, not mainshock prediction.
    """
    events = load_earthquakes(min_magnitude=2.5)
    events = events.sort_values("time").reset_index(drop=True)
    times = events["time"].to_numpy()
    lat = events["latitude"].to_numpy()
    lon = events["longitude"].to_numpy()
    mag = events["mag"].to_numpy()
    main_idx = np.where(mag >= 5.0)[0]
    rows: list[dict[str, Any]] = []
    for idx in main_idx:
        event_time = times[idx]
        if event_time > times[-1] - np.timedelta64(7, "D"):
            continue
        window_end = event_time + np.timedelta64(7, "D")
        start = int(np.searchsorted(times, event_time, side="right"))
        end = int(np.searchsorted(times, window_end, side="right"))
        if end <= start:
            aftershock = 0
        else:
            distances = haversine_km(lat[idx], lon[idx], lat[start:end], lon[start:end])
            candidates = (distances <= 50.0) & (mag[start:end] >= 4.0)
            aftershock = int(np.any(candidates))
        prev_window_start = event_time - np.timedelta64(365, "D")
        prev_start = int(np.searchsorted(times, prev_window_start, side="left"))
        prev_slice = slice(prev_start, idx)
        if idx > prev_start:
            prev_dist = haversine_km(lat[idx], lon[idx], lat[prev_slice], lon[prev_slice])
            prev_m5 = (prev_dist <= 100.0) & (mag[prev_slice] >= 5.0)
            last_m5 = times[prev_slice][prev_m5]
            days_since_m5 = (
                (event_time - last_m5[-1]) / np.timedelta64(1, "D") if last_m5.size else 365.0
            )
            prev_m4_7d = (prev_dist <= 50.0) & (mag[prev_slice] >= 4.0) & (
                times[prev_slice] >= event_time - np.timedelta64(7, "D")
            )
            prev_m4_30d_100km = (prev_dist <= 100.0) & (mag[prev_slice] >= 4.0) & (
                times[prev_slice] >= event_time - np.timedelta64(30, "D")
            )
        else:
            days_since_m5 = 365.0
            prev_m4_7d = np.zeros(0, dtype=bool)
            prev_m4_30d_100km = np.zeros(0, dtype=bool)
        rows.append(
            {
                "time": event_time,
                "target_date": event_time,
                "target_window_end": window_end,
                "magnitude": float(mag[idx]),
                "depth_km": float(events.loc[idx, "depth"]),
                "latitude": float(lat[idx]),
                "longitude": float(lon[idx]),
                "abs_latitude": float(abs(lat[idx])),
                "days_since_prev_m5_100km": float(min(days_since_m5, 365.0)),
                "n_m4_prev7d_50km": int(np.sum(prev_m4_7d)),
                "n_m4_prev30d_100km": int(np.sum(prev_m4_30d_100km)),
                "target_aftershock_m4_7d_50km": aftershock,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError("No eligible M>=5 mainshocks were available for aftershock modelling.")
    frame = frame.sort_values("time").reset_index(drop=True)
    frame = _calendar_features(frame)
    frame["time_since_start_days"] = (frame["time"] - frame["time"].min()).dt.total_seconds() / 86400.0
    feature_columns = [
        "magnitude", "depth_km", "latitude", "longitude", "abs_latitude",
        "days_since_prev_m5_100km", "n_m4_prev7d_50km", "n_m4_prev30d_100km",
        "month_sin", "month_cos", "doy_sin", "doy_cos", "time_since_start_days",
    ]
    return Dataset(
        name="earthquake_aftershock_occurrence",
        frame=frame,
        target_column="target_aftershock_m4_7d_50km",
        date_column="target_date",
        feature_columns=feature_columns,
        provenance={
            "source": events.attrs.get("source_path", "earthquake/USGS"),
            "catalogue_note": events.attrs.get("catalogue_limit_note"),
            "mainshocks": int(len(frame)),
        },
        notes=[
            "Aftershock sequence screening, not earthquake occurrence prediction.",
            "The catalogue is regionally clipped and capped at 20,000 events.",
            "Features use only prior events; the label uses future events.",
        ],
    )


def build_landslide_readiness_dataset() -> Dataset:
    """Build the Kerala-reported landslide event table used for readiness review.

    No background sample is invented here.  The table is deliberately not a
    training dataset; it documents why the available inventory cannot support a
    defensible landslide occurrence model.
    """
    landslides = load_landslides()
    india = landslides[landslides["country_name"].astype(str).str.casefold() == "india"].copy()
    kerala = india[
        india["admin_division_name"].astype(str).str.contains("kerala", case=False, na=False)
    ].copy()
    kerala["target_reported_landslide"] = 1
    kerala["target_date"] = kerala["event_date"]
    kerala = kerala.dropna(subset=["event_date", "latitude", "longitude"]).reset_index(drop=True)
    feature_columns: list[str] = []
    return Dataset(
        name="landslide_reported_events_kerala",
        frame=kerala,
        target_column="target_reported_landslide",
        date_column="target_date",
        feature_columns=feature_columns,
        provenance={
            "source": landslides.attrs.get("source_path", "landslide/NASA_GLC"),
            "india_rows": int(len(india)),
            "kerala_rows": int(len(kerala)),
            "catalogue_note": landslides.attrs.get("catalogue_limit_note"),
        },
        notes=[
            "Reported-event inventory only; no representative non-event sample.",
            "Not used to train a model in this release.",
        ],
    )

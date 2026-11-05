"""Deterministic climate benchmarks from an archived daily weather record.

Purpose
-------
Provide reproducible, location-specific climatology against which the hazard
models and the research ML baselines can be checked.  This module computes
descriptive statistics only:

* heat: percentile thresholds and counts of days above screening temperatures;
* rainfall: annual and monsoon totals, extreme-day counts and wet-day
  percentiles;
* drought: rainfall-only dry-spell and rolling-accumulation indicators;
* wind: 10 m maximum-gust context;
* SPI readiness: whether the record satisfies the 30-year reference length
  required by :mod:`src.disaster_models.drought`, and a descriptive SPI-1
  series when it does.

What this module is **not**
---------------------------
The input is Open-Meteo archived reanalysis (ERA5-family model output) at a
grid point, not a rain-gauge or thermometer observation.  It does not resolve
local convective extremes, urban heat islands, or station exposure.  The
outputs are not forecasts, official warnings, IMD heatwave declarations,
hydrological drought status, attribution statements, or projections.  Trends
are descriptive linear summaries; autocorrelation and non-stationarity are not
modelled.

Every result is labelled ``DESCRIPTIVE_CLIMATOLOGY_BENCHMARK`` and carries the
source limitations into the generated report.
"""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

STATUS = "DESCRIPTIVE_CLIMATOLOGY_BENCHMARK_NOT_FORECAST_OR_WARNING"

REQUIRED_SERIES = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
)

# Absolute temperature screening thresholds.  These are *not* IMD heatwave
# criteria: IMD criteria depend on station normals, departure from normal, and
# whether the station is coastal/plains/hilly.  They are retained only as
# transparent, round-number screening values.
HEAT_SCREENING_THRESHOLDS_C = (35.0, 37.0)
# Rainfall day-class thresholds used by many meteorological services as
# descriptive heavy-rain categories.  They are not local warning thresholds.
RAINFALL_HEAVY_DAY_MM = 50.0
RAINFALL_VERY_HEAVY_DAY_MM = 100.0
RAINFALL_EXTREMELY_HEAVY_DAY_MM = 150.0
DRY_DAY_MM = 1.0
MONSOON_MONTHS = (6, 7, 8, 9)

SOURCE_LICENCE = (
    "Open-Meteo Historical Weather API, free non-commercial use under CC BY 4.0. "
    "Underlying reanalysis data are model output, not station observations."
)
SOURCE_URL = "https://archive-api.open-meteo.com/v1/archive"
PROVIDER = "Open-Meteo Historical Weather API (ERA5-family reanalysis grid point)"

_REPO_ROOT = Path(__file__).resolve().parents[1]


def portable_path(path: Path) -> str:
    """Return a POSIX path relative to the repository when possible.

    Reports are committed and served from a different machine, so embedding an
    absolute local path would leak the developer's filesystem and break
    reproducibility.  A path outside the repository is reduced to its file name
    rather than exposing the local directory.
    """
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return resolved.name


class ClimateBenchmarkError(ValueError):
    """Raised when the weather record cannot support a defensible benchmark."""


def _as_float(value: Any, *, label: str, index: int) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ClimateBenchmarkError(
            f"{label} value at index {index} is not numeric: {value!r}"
        ) from exc
    if not math.isfinite(number):
        raise ClimateBenchmarkError(
            f"{label} value at index {index} is not finite: {value!r}"
        )
    return number


def load_daily_weather(path: Path) -> dict[str, Any]:
    """Load and structurally validate one daily weather JSON file.

    The function fails closed on structural problems (unequal series lengths,
    duplicate or non-consecutive dates, non-finite values, negative rainfall)
    because a benchmark computed from an unvalidated record would be
    misleading.  Missing values are allowed and counted, not imputed.
    """
    path = Path(path)
    if not path.is_file():
        raise ClimateBenchmarkError(f"Weather record not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or not isinstance(payload.get("daily"), Mapping):
        raise ClimateBenchmarkError("Weather record must contain a 'daily' object.")
    daily = payload["daily"]
    if "time" not in daily:
        raise ClimateBenchmarkError("Weather record has no daily time series.")
    times = list(daily["time"])
    if not times:
        raise ClimateBenchmarkError("Weather record has an empty daily time series.")
    lengths = {len(times)} | {
        len(daily.get(name) or []) for name in REQUIRED_SERIES
    }
    if len(lengths) != 1:
        raise ClimateBenchmarkError(
            f"Daily series lengths differ: {sorted(lengths)}; refusing to align them silently."
        )

    parsed: list[date] = []
    for index, value in enumerate(times):
        try:
            parsed.append(date.fromisoformat(str(value)))
        except ValueError as exc:
            raise ClimateBenchmarkError(
                f"Invalid ISO date at index {index}: {value!r}"
            ) from exc
    for previous, current in zip(parsed, parsed[1:]):
        if current - previous != timedelta(days=1):
            raise ClimateBenchmarkError(
                f"Daily dates are not consecutive between {previous} and {current}; "
                "a gap would distort accumulation benchmarks."
            )
    if len(set(parsed)) != len(parsed):
        raise ClimateBenchmarkError("Daily dates contain duplicates.")

    series: dict[str, list[float | None]] = {}
    missing: dict[str, int] = {}
    for name in REQUIRED_SERIES:
        values = [
            _as_float(raw, label=name, index=index)
            for index, raw in enumerate(daily[name])
        ]
        if name == "precipitation_sum":
            if any(value is not None and value < 0 for value in values):
                raise ClimateBenchmarkError("Precipitation contains negative values.")
        if "temperature" in name:
            if any(value is not None and not (-60 <= value <= 60) for value in values):
                raise ClimateBenchmarkError(f"{name} contains an implausible temperature.")
        if "wind" in name:
            if any(value is not None and value < 0 for value in values):
                raise ClimateBenchmarkError(f"{name} contains negative wind speed.")
        series[name] = values
        missing[name] = sum(value is None for value in values)

    units = dict(payload.get("daily_units") or {})
    return {
        "path": path,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "dates": parsed,
        "series": series,
        "missing": missing,
        "units": units,
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "elevation_m": payload.get("elevation"),
        "timezone": payload.get("timezone"),
        "timezone_abbreviation": payload.get("timezone_abbreviation"),
        "first_date": parsed[0].isoformat(),
        "last_date": parsed[-1].isoformat(),
        "day_count": len(parsed),
    }


def percentile(values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile (same convention as NumPy's default)."""
    if not 0 <= q <= 1:
        raise ValueError("Percentile must be between 0 and 1.")
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("Cannot take a percentile of an empty sequence.")
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def ols_trend(xs: Sequence[float], ys: Sequence[float]) -> dict[str, Any]:
    """Ordinary least-squares slope with a normal-approximation 95% interval.

    The interval is approximate and ignores autocorrelation, so it is reported
    as descriptive rather than inferential evidence.
    """
    if len(xs) != len(ys) or len(xs) < 3:
        raise ValueError("OLS trend needs at least three paired values.")
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    if sxx == 0:
        raise ValueError("OLS trend needs variation in the x values.")
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    residuals = [y - (intercept + slope * x) for x, y in zip(xs, ys)]
    sse = sum(residual * residual for residual in residuals)
    sst = sum((y - mean_y) ** 2 for y in ys)
    standard_error = math.sqrt(sse / (n - 2) / sxx) if sse > 0 else 0.0
    return {
        "slope_per_year": slope,
        "slope_per_decade": slope * 10,
        "intercept": intercept,
        "standard_error_per_year": standard_error,
        "ci95_per_year": [
            slope - 1.96 * standard_error,
            slope + 1.96 * standard_error,
        ],
        "ci95_per_decade": [
            (slope - 1.96 * standard_error) * 10,
            (slope + 1.96 * standard_error) * 10,
        ],
        "r_squared": 1 - sse / sst if sst > 0 else None,
        "n_years": n,
        "interval_method": "Normal approximation; autocorrelation and non-stationarity not modelled.",
        "interpretation": "Descriptive linear summary only; not attribution or projection.",
    }


def theil_sen_trend(xs: Sequence[float], ys: Sequence[float]) -> dict[str, Any]:
    """Robust median-of-pairwise-slopes trend (sensitivity check for OLS)."""
    if len(xs) != len(ys) or len(xs) < 3:
        raise ValueError("Theil-Sen trend needs at least three paired values.")
    slopes = [
        (ys[j] - ys[i]) / (xs[j] - xs[i])
        for i in range(len(xs))
        for j in range(i + 1, len(xs))
        if xs[j] != xs[i]
    ]
    slope = statistics.median(slopes)
    return {
        "slope_per_year": slope,
        "slope_per_decade": slope * 10,
        "n_pairwise_slopes": len(slopes),
        "interpretation": "Robust descriptive sensitivity check; not an inferential test.",
    }


def _complete_years(dates: Sequence[date]) -> list[int]:
    counts: dict[int, int] = defaultdict(int)
    for value in dates:
        counts[value.year] += 1
    return [
        year
        for year, count in sorted(counts.items())
        if count == (366 if _is_leap(year) else 365)
    ]


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _yearly(
    dates: Sequence[date],
    values: Sequence[float | None],
    reducer: str,
) -> list[dict[str, Any]]:
    grouped: dict[int, list[float]] = defaultdict(list)
    for day, value in zip(dates, values):
        if value is not None:
            grouped[day.year].append(float(value))
    rows: list[dict[str, Any]] = []
    for year in sorted(grouped):
        items = grouped[year]
        if not items:
            continue
        if reducer == "sum":
            statistic = sum(items)
        elif reducer == "mean":
            statistic = sum(items) / len(items)
        elif reducer == "max":
            statistic = max(items)
        else:
            raise ValueError(f"Unsupported yearly reducer: {reducer}")
        rows.append({"year": year, "value": statistic, "n_days": len(items)})
    return rows


def _annual_counts(
    dates: Sequence[date], values: Sequence[float | None], threshold: float
) -> list[dict[str, Any]]:
    grouped: dict[int, int] = defaultdict(int)
    for day, value in zip(dates, values):
        if value is not None and value >= threshold:
            grouped[day.year] += 1
    return [{"year": year, "days": grouped.get(year, 0)} for year in sorted({d.year for d in dates})]


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "mean": sum(values) / len(values),
        "median": statistics.median(values),
        "minimum": min(values),
        "maximum": max(values),
        "p10": percentile(values, 0.10),
        "p90": percentile(values, 0.90),
    }


def _trend_block(
    rows: Sequence[Mapping[str, Any]], value_key: str = "value"
) -> dict[str, Any] | None:
    if len(rows) < 3:
        return None
    xs = [float(row["year"]) for row in rows]
    ys = [float(row[value_key]) for row in rows]
    return {"ols": ols_trend(xs, ys), "theil_sen": theil_sen_trend(xs, ys)}


def _rolling_sum(values: Sequence[float | None], window: int) -> list[float | None]:
    """Trailing rolling sum; a window containing any missing value is None."""
    output: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < window:
            output.append(None)
            continue
        chunk = values[index + 1 - window : index + 1]
        if any(value is None for value in chunk):
            output.append(None)
        else:
            output.append(sum(float(value) for value in chunk))
    return output


def _period_values(
    dates: Sequence[date],
    values: Sequence[float | None],
    start: date,
    end: date,
) -> list[float]:
    return [
        float(value)
        for day, value in zip(dates, values)
        if value is not None and start <= day <= end
    ]


def heat_benchmarks(
    record: Mapping[str, Any],
    baseline: tuple[date, date],
) -> dict[str, Any]:
    dates = record["dates"]
    tmax = record["series"]["temperature_2m_max"]
    full_values = [float(value) for value in tmax if value is not None]
    baseline_values = _period_values(dates, tmax, baseline[0], baseline[1])
    if len(baseline_values) < 365 * 20:
        raise ClimateBenchmarkError("Heat baseline needs at least 20 years of values.")

    thresholds = {
        "baseline_p90_c": percentile(baseline_values, 0.90),
        "baseline_p95_c": percentile(baseline_values, 0.95),
        "baseline_p99_c": percentile(baseline_values, 0.99),
        "full_record_p90_c": percentile(full_values, 0.90),
        "full_record_p95_c": percentile(full_values, 0.95),
        "full_record_p99_c": percentile(full_values, 0.99),
        "full_record_max_c": max(full_values),
    }
    yearly_mean = _yearly(dates, tmax, "mean")
    yearly_max = _yearly(dates, tmax, "max")
    absolute_counts = {
        f"days_ge_{int(threshold)}c": sum(1 for value in full_values if value >= threshold)
        for threshold in HEAT_SCREENING_THRESHOLDS_C
    }
    annual_absolute = {
        f"days_ge_{int(threshold)}c": _annual_counts(dates, tmax, threshold)
        for threshold in HEAT_SCREENING_THRESHOLDS_C
    }
    baseline_p95 = thresholds["baseline_p95_c"]
    annual_p95 = _annual_counts(dates, tmax, baseline_p95)
    return {
        "thresholds": thresholds,
        "absolute_screening_counts": absolute_counts,
        "annual_mean_tmax_c": yearly_mean,
        "annual_max_tmax_c": yearly_max,
        "annual_days_ge_baseline_p95": annual_p95,
        "annual_absolute_counts": annual_absolute,
        "trend_mean_tmax": _trend_block(yearly_mean),
        "trend_annual_max_tmax": _trend_block(yearly_max),
        "trend_days_ge_baseline_p95": _trend_block(annual_p95, "days"),
        "interpretation": (
            "Percentile thresholds are location-specific reanalysis climatology. "
            "The 35 C and 37 C counts are transparent screening values, not IMD "
            "heatwave criteria. Coastal Kochi heat stress is often humidity-driven; "
            "this record has no humidity series, so no heat index is computed here."
        ),
    }


def rainfall_benchmarks(
    record: Mapping[str, Any],
    baseline: tuple[date, date],
) -> dict[str, Any]:
    dates = record["dates"]
    rain = record["series"]["precipitation_sum"]
    annual = _yearly(dates, rain, "sum")
    monsoon = [
        {
            "year": year,
            "value": sum(
                float(value)
                for day, value in zip(dates, rain)
                if value is not None
                and day.year == year
                and day.month in MONSOON_MONTHS
            ),
        }
        for year in sorted({day.year for day in dates})
    ]
    wet_days = [float(value) for value in rain if value is not None and value >= 1.0]
    all_days = [float(value) for value in rain if value is not None]
    baseline_daily = _period_values(dates, rain, baseline[0], baseline[1])
    wettest_index = max(
        (index for index, value in enumerate(rain) if value is not None),
        key=lambda index: float(rain[index]),
    )
    monthly: dict[int, list[float]] = defaultdict(list)
    for day, value in zip(dates, rain):
        if value is not None:
            monthly[day.month].append(float(value))
    monthly_climatology = []
    for month in range(1, 13):
        values = monthly[month]
        monthly_climatology.append(
            {
                "month": month,
                "mean_daily_mm": sum(values) / len(values),
                "median_daily_mm": statistics.median(values),
                "mean_monthly_total_mm": sum(values) / max(1, len({d.year for d in dates if d.month == month})),
            }
        )
    return {
        "annual_total_mm": _distribution([row["value"] for row in annual]),
        "annual_total_rows": annual,
        "monsoon_total_mm": _distribution([row["value"] for row in monsoon]),
        "monsoon_total_rows": monsoon,
        "daily_all_days_mm": _distribution(all_days),
        "daily_wet_days_mm": _distribution(wet_days),
        "baseline_daily_p95_mm": percentile(baseline_daily, 0.95),
        "baseline_daily_p99_mm": percentile(baseline_daily, 0.99),
        "wet_day_p95_mm": percentile(wet_days, 0.95),
        "wet_day_p99_mm": percentile(wet_days, 0.99),
        "heavy_day_counts": {
            f"days_ge_{int(threshold)}mm": sum(
                1 for value in all_days if value >= threshold
            )
            for threshold in (
                RAINFALL_HEAVY_DAY_MM,
                RAINFALL_VERY_HEAVY_DAY_MM,
                RAINFALL_EXTREMELY_HEAVY_DAY_MM,
            )
        },
        "annual_heavy_day_counts": {
            f"days_ge_{int(threshold)}mm": _annual_counts(dates, rain, threshold)
            for threshold in (
                RAINFALL_HEAVY_DAY_MM,
                RAINFALL_VERY_HEAVY_DAY_MM,
                RAINFALL_EXTREMELY_HEAVY_DAY_MM,
            )
        },
        "wettest_day": {
            "date": dates[wettest_index].isoformat(),
            "precipitation_mm": float(rain[wettest_index]),
        },
        "monthly_climatology": monthly_climatology,
        "trend_annual_total": _trend_block(annual),
        "trend_monsoon_total": _trend_block(monsoon),
        "trend_heavy_days": _trend_block(
            _annual_counts(dates, rain, RAINFALL_HEAVY_DAY_MM), "days"
        ),
        "interpretation": (
            "Grid-point reanalysis totals may differ from rain-gauge totals and do "
            "not resolve local convective extremes. Heavy-day thresholds are "
            "descriptive categories, not local warnings."
        ),
    }


def drought_benchmarks(record: Mapping[str, Any]) -> dict[str, Any]:
    dates = record["dates"]
    rain = record["series"]["precipitation_sum"]
    if any(value is None for value in rain):
        raise ClimateBenchmarkError(
            "Drought accumulation benchmarks require a complete precipitation series."
        )
    values = [float(value) for value in rain]
    dry_spells: list[dict[str, Any]] = []
    start_index = 0
    for index, value in enumerate(values + [DRY_DAY_MM]):
        if value < DRY_DAY_MM:
            continue
        if index > start_index:
            dry_spells.append(
                {
                    "start": dates[start_index].isoformat(),
                    "end": dates[index - 1].isoformat(),
                    "length_days": index - start_index,
                }
            )
        start_index = index + 1
    annual_max_dry = []
    for year in sorted({day.year for day in dates}):
        longest = 0
        current = 0
        for day, value in zip(dates, values):
            if day.year != year:
                continue
            if value < DRY_DAY_MM:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
        annual_max_dry.append(
            {"year": year, "max_consecutive_dry_days": longest}
        )
    windows = {}
    for window in (30, 90):
        rolling = _rolling_sum(rain, window)
        paired = [
            (day, float(value))
            for day, value in zip(dates, rolling)
            if value is not None
        ]
        totals = [value for _, value in paired]
        minimum_day, minimum_value = min(paired, key=lambda item: item[1])
        p05 = percentile(totals, 0.05)
        p10 = percentile(totals, 0.10)
        windows[f"{window}_day"] = {
            "distribution_mm": _distribution(totals),
            "p05_mm": p05,
            "p10_mm": p10,
            "minimum_mm": minimum_value,
            "minimum_window_end_date": minimum_day.isoformat(),
            "windows_at_or_below_p05": sum(
                1 for value in totals if value <= p05
            ),
            "windows_at_or_below_p10": sum(
                1 for value in totals if value <= p10
            ),
            "overlapping_windows_note": (
                "Trailing windows overlap, so counts are not independent events."
            ),
        }
    return {
        "dry_day_threshold_mm": DRY_DAY_MM,
        "dry_spells": dry_spells,
        "longest_dry_spell": max(dry_spells, key=lambda spell: spell["length_days"]),
        "spells_ge_10_days": sum(
            1 for spell in dry_spells if spell["length_days"] >= 10
        ),
        "annual_max_consecutive_dry_days": annual_max_dry,
        "rolling_windows": windows,
        "trend_annual_max_dry_days": _trend_block(
            annual_max_dry, "max_consecutive_dry_days"
        ),
        "interpretation": (
            "Rainfall-only meteorological indicators. These are not SPI values, "
            "hydrological or agricultural drought status, water-supply deficits, "
            "or forecasts; evapotranspiration, soil moisture, storage and demand "
            "are not represented."
        ),
    }


def wind_benchmarks(record: Mapping[str, Any]) -> dict[str, Any]:
    dates = record["dates"]
    gust = record["series"]["wind_gusts_10m_max"]
    annual_max = _yearly(dates, gust, "max")
    all_values = [float(value) for value in gust if value is not None]
    return {
        "daily_gust_kmh": _distribution(all_values),
        "annual_max_gust_rows": annual_max,
        "days_ge_50_kmh": sum(1 for value in all_values if value >= 50.0),
        "annual_days_ge_50_kmh": _annual_counts(dates, gust, 50.0),
        "trend_annual_max_gust": _trend_block(annual_max),
        "interpretation": (
            "10 m maximum gust from reanalysis, not a cyclone boundary-layer wind "
            "field, track, storm surge, or structural design load."
        ),
    }


def monthly_totals(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    dates = record["dates"]
    rain = record["series"]["precipitation_sum"]
    grouped: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for day, value in zip(dates, rain):
        key = f"{day.year:04d}-{day.month:02d}"
        if value is not None:
            grouped[key] += float(value)
            counts[key] += 1
    rows = []
    for key in sorted(grouped):
        year, month = (int(part) for part in key.split("-"))
        expected = _days_in_month(year, month)
        rows.append(
            {
                "month": key,
                "precipitation_mm": grouped[key],
                "days_present": counts[key],
                "complete": counts[key] == expected,
            }
        )
    return rows


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def spi_readiness(record: Mapping[str, Any]) -> dict[str, Any]:
    """Check whether the record satisfies the project SPI-1 reference rule.

    The existing drought model requires at least 30 consecutive years and at
    least 30 values for the target calendar month.  This function reports
    readiness and, when scipy is available, computes a descriptive SPI-1 series
    for the most recent 12 months by delegating to that model.
    """
    rows = monthly_totals(record)
    months = [row["month"] for row in rows]
    complete = all(row["complete"] for row in rows)
    consecutive = True
    for previous, current in zip(rows, rows[1:]):
        py, pm = (int(part) for part in previous["month"].split("-"))
        cy, cm = (int(part) for part in current["month"].split("-"))
        if (cy - py) * 12 + (cm - pm) != 1:
            consecutive = False
            break
    by_calendar: dict[int, int] = defaultdict(int)
    for row in rows:
        by_calendar[int(row["month"][5:7])] += 1
    reference_years = int(months[-1][:4]) - int(months[0][:4]) + 1 if months else 0
    ready = (
        complete
        and consecutive
        and reference_years >= 30
        and all(by_calendar[month] >= 30 for month in range(1, 13))
    )
    result: dict[str, Any] = {
        "month_count": len(rows),
        "first_month": months[0] if months else None,
        "last_month": months[-1] if months else None,
        "reference_years": reference_years,
        "consecutive_complete_months": complete and consecutive,
        "calendar_month_counts": {str(month): by_calendar[month] for month in range(1, 13)},
        "meets_30_year_spi_reference_rule": ready,
        "monthly_totals": rows,
        "note": (
            "Readiness is a data-length check for the existing SPI-1 model. "
            "It is not a drought declaration."
        ),
    }
    if not ready:
        result["spi1_series"] = []
        result["spi1_status"] = "insufficient_reference_record"
        return result
    try:
        from src.disaster_models.drought import calculate_spi1
    except Exception as exc:  # pragma: no cover - import environment dependent
        result["spi1_series"] = []
        result["spi1_status"] = f"unavailable: {type(exc).__name__}"
        return result
    records = [
        {"month": datetime.strptime(row["month"], "%Y-%m"), "precipitation_mm": row["precipitation_mm"]}
        for row in rows
    ]
    series = []
    for end in range(max(0, len(records) - 12), len(records)):
        prefix = records[: end + 1]
        try:
            spi = calculate_spi1(prefix)
        except Exception as exc:  # pragma: no cover - numerical edge case
            series.append({"month": rows[end]["month"], "status": f"error: {type(exc).__name__}"})
            continue
        series.append(
            {
                "month": rows[end]["month"],
                "status": spi.get("status"),
                "spi1": spi.get("spi1"),
                "category": spi.get("category"),
                "reference_count": spi.get("calendar_month_reference_count"),
            }
        )
    result["spi1_series"] = series
    result["spi1_status"] = "descriptive_series_computed"
    result["spi1_source"] = "src.disaster_models.drought.calculate_spi1"
    return result


def compare_overlapping_records(
    primary: Mapping[str, Any], secondary: Mapping[str, Any]
) -> dict[str, Any]:
    """Compare two records over their shared dates without splicing them.

    Different retrieval dates can resolve to slightly different model grid
    cells.  This check makes that visible instead of silently combining files.
    """
    secondary_map = {
        day: {name: secondary["series"][name][index] for name in REQUIRED_SERIES}
        for index, day in enumerate(secondary["dates"])
    }
    overlap = 0
    differences = {name: 0 for name in REQUIRED_SERIES}
    maximum = {name: 0.0 for name in REQUIRED_SERIES}
    for index, day in enumerate(primary["dates"]):
        if day not in secondary_map:
            continue
        overlap += 1
        for name in REQUIRED_SERIES:
            left = primary["series"][name][index]
            right = secondary_map[day][name]
            if left == right:
                continue
            differences[name] += 1
            if left is not None and right is not None:
                maximum[name] = max(maximum[name], abs(float(left) - float(right)))
    return {
        "primary_file": portable_path(primary["path"]),
        "secondary_file": portable_path(secondary["path"]),
        "overlap_days": overlap,
        "differing_days_by_series": differences,
        "maximum_absolute_difference": maximum,
        "elevation_m": {
            "primary": primary.get("elevation_m"),
            "secondary": secondary.get("elevation_m"),
        },
        "interpretation": (
            "Small differences are expected when a provider updates its model or "
            "grid. The files are not spliced; benchmarks use one consistent record."
        ),
    }


def compare_with_training_report(
    report_path: Path, kochi_heat: Mapping[str, Any]
) -> dict[str, Any]:
    """Check whether a pooled training threshold is being mistaken for Kochi's.

    The existing weather training report pools four Kerala locations.  Its 95th
    percentile is therefore not a Kochi-specific threshold.  This function makes
    the distinction explicit instead of treating a mismatch as an error.
    """
    report_path = Path(report_path)
    if not report_path.is_file():
        return {"available": False, "reason": "training report not found"}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    high_temperature = next(
        (
            model
            for model in report.get("models", [])
            if model.get("hazard") == "high_temperature"
        ),
        None,
    )
    if not high_temperature:
        return {"available": False, "reason": "no high_temperature model in report"}
    pooled = high_temperature.get("threshold")
    kochi_p95 = kochi_heat["thresholds"]["baseline_p95_c"]
    return {
        "available": True,
        "training_report": portable_path(report_path),
        "training_threshold_c": pooled,
        "training_locations": high_temperature.get("locations"),
        "kochi_baseline_p95_c": kochi_p95,
        "difference_c": (float(pooled) - float(kochi_p95)) if pooled is not None else None,
        "comparable_as_kochi_threshold": False,
        "reason": (
            "The training threshold is a pooled multi-location research event "
            "definition, not a Kochi-specific climatological threshold. The "
            "difference is expected and must not be reported as a model error."
        ),
    }


def build_benchmark_report(
    weather_path: Path,
    *,
    location_name: str = "Kochi",
    baseline_period: tuple[date, date] = (date(1991, 1, 1), date(2020, 12, 31)),
    comparison_path: Path | None = None,
    training_report_path: Path | None = None,
) -> dict[str, Any]:
    """Build the complete descriptive benchmark report."""
    record = load_daily_weather(weather_path)
    complete_years = _complete_years(record["dates"])
    baseline_dates = [day for day in record["dates"] if baseline_period[0] <= day <= baseline_period[1]]
    if len({day.year for day in baseline_dates}) < 30:
        raise ClimateBenchmarkError(
            "The 1991-2020 baseline does not contain 30 complete years in this record."
        )
    heat = heat_benchmarks(record, baseline_period)
    rainfall = rainfall_benchmarks(record, baseline_period)
    drought = drought_benchmarks(record)
    wind = wind_benchmarks(record)
    spi = spi_readiness(record)
    validation: dict[str, Any] = {
        "record_continuity": {
            "first_date": record["first_date"],
            "last_date": record["last_date"],
            "day_count": record["day_count"],
            "complete_calendar_years": complete_years,
            "complete_year_count": len(complete_years),
            "missing_value_counts": record["missing"],
            "status": "consecutive_daily_record_no_gaps",
        },
    }
    if comparison_path and Path(comparison_path).is_file():
        validation["overlap_comparison"] = compare_overlapping_records(
            record, load_daily_weather(comparison_path)
        )
    if training_report_path and Path(training_report_path).is_file():
        validation["training_threshold_cross_check"] = compare_with_training_report(
            Path(training_report_path), heat
        )
    limitations = [
        "The input is Open-Meteo archived reanalysis at a model grid point, not a rain-gauge, thermometer, or anemometer observation.",
        "Reanalysis does not resolve local convective rainfall extremes, urban heat islands, or station exposure; totals and extremes may differ from local gauges.",
        "The 1991-2020 baseline is a model-era normal, not an official IMD or WMO station normal for Kochi.",
        "Trends are descriptive linear summaries; autocorrelation, model-version changes, non-stationarity and multiple testing are not modelled. They are not attribution or projections.",
        "Heat percentile thresholds are location-specific reanalysis values; the 35 C and 37 C counts are screening values, not IMD heatwave criteria. Humidity is absent, so no heat index is computed.",
        "Heavy-rain day classes are descriptive categories, not local warning thresholds.",
        "Drought indicators are rainfall-only; they are not SPI values in this module, and they do not represent evapotranspiration, soil moisture, storage, demand, agricultural or hydrological drought.",
        "SPI-1 is delegated to the existing drought model only as a descriptive series; it is not a drought declaration or forecast.",
        "Wind values are 10 m reanalysis gusts, not cyclone tracks, boundary-layer winds, storm surge, or design loads.",
        "No independent station, gauge, radar, or impact/outcome dataset was used to validate these benchmarks.",
        "Recent reanalysis months may be preliminary and subject to provider revision.",
    ]
    return {
        "schema_version": 1,
        "status": STATUS,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "location": {
            "name": location_name,
            "latitude": record.get("latitude"),
            "longitude": record.get("longitude"),
            "elevation_m": record.get("elevation_m"),
            "timezone": record.get("timezone"),
        },
        "source": {
            "provider": PROVIDER,
            "source_url": SOURCE_URL,
            "file": portable_path(record["path"]),
            "bytes": record["bytes"],
            "sha256": record["sha256"],
            "retrieved_on": datetime.now(timezone.utc).date().isoformat(),
            "licence": SOURCE_LICENCE,
            "source_type": "MODELLED REANALYSIS GRID POINT; NOT STATION OBSERVATION",
        },
        "record": {
            "first_date": record["first_date"],
            "last_date": record["last_date"],
            "day_count": record["day_count"],
            "complete_calendar_years": complete_years,
            "complete_year_count": len(complete_years),
            "missing_value_counts": record["missing"],
            "units": record["units"],
        },
        "baseline_period": {
            "start": baseline_period[0].isoformat(),
            "end": baseline_period[1].isoformat(),
            "years": len({day.year for day in baseline_dates}),
            "definition": "1991-2020 model-era baseline; not an official station normal.",
        },
        "heat": heat,
        "rainfall": rainfall,
        "drought": drought,
        "wind": wind,
        "spi_readiness": spi,
        "validation": validation,
        "limitations": limitations,
    }

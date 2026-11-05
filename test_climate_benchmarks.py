"""Tests for descriptive climate benchmarks and their validation checks."""

from __future__ import annotations

import json
import math
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.climate_benchmarks import (
    STATUS,
    ClimateBenchmarkError,
    build_benchmark_report,
    compare_overlapping_records,
    compare_with_training_report,
    drought_benchmarks,
    heat_benchmarks,
    load_daily_weather,
    monthly_totals,
    ols_trend,
    percentile,
    rainfall_benchmarks,
    spi_readiness,
    theil_sen_trend,
    wind_benchmarks,
)


ROOT = Path(__file__).resolve().parent
WEATHER = (
    ROOT
    / "data"
    / "external"
    / "hazards"
    / "raw"
    / "weather"
    / "kochi_daily_weather_1991_2025.json"
)
COMPARISON = (
    ROOT
    / "data"
    / "external"
    / "hazards"
    / "raw"
    / "weather"
    / "kochi_daily_weather_2000_2025.json"
)
TRAINING = ROOT / "reports" / "weather_hazard_training.json"
BASELINE = (date(1991, 1, 1), date(2020, 12, 31))


def _synthetic_payload(days: int = 10) -> dict:
    start = date(2020, 1, 1)
    times = [(start + timedelta(days=index)).isoformat() for index in range(days)]
    return {
        "latitude": 9.9,
        "longitude": 76.3,
        "elevation": 4.0,
        "timezone": "Asia/Kolkata",
        "daily_units": {
            "temperature_2m_max": "°C",
            "temperature_2m_min": "°C",
            "precipitation_sum": "mm",
            "wind_speed_10m_max": "km/h",
            "wind_gusts_10m_max": "km/h",
        },
        "daily": {
            "time": times,
            "temperature_2m_max": [30.0 + index * 0.1 for index in range(days)],
            "temperature_2m_min": [22.0 for _ in range(days)],
            "precipitation_sum": [0.0, 5.0, 0.0, 0.0, 20.0, 0.0, 0.0, 0.0, 1.0, 0.0][:days],
            "wind_speed_10m_max": [10.0 for _ in range(days)],
            "wind_gusts_10m_max": [30.0 for _ in range(days)],
        },
    }


def _write(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "weather.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _available() -> bool:
    return WEATHER.is_file()


class TestLoadingAndValidation:
    def test_valid_record_loads_with_units_and_missing_counts(self, tmp_path):
        record = load_daily_weather(_write(tmp_path, _synthetic_payload()))
        assert record["day_count"] == 10
        assert record["first_date"] == "2020-01-01"
        assert record["missing"]["temperature_2m_max"] == 0
        assert record["units"]["precipitation_sum"] == "mm"

    def test_gap_in_dates_is_rejected(self, tmp_path):
        payload = _synthetic_payload()
        payload["daily"]["time"][3] = "2020-01-10"
        with pytest.raises(ClimateBenchmarkError, match="not consecutive"):
            load_daily_weather(_write(tmp_path, payload))

    def test_unequal_series_lengths_are_rejected(self, tmp_path):
        payload = _synthetic_payload()
        payload["daily"]["precipitation_sum"] = payload["daily"]["precipitation_sum"][:-1]
        with pytest.raises(ClimateBenchmarkError, match="lengths differ"):
            load_daily_weather(_write(tmp_path, payload))

    def test_negative_precipitation_is_rejected(self, tmp_path):
        payload = _synthetic_payload()
        payload["daily"]["precipitation_sum"][0] = -1.0
        with pytest.raises(ClimateBenchmarkError, match="negative"):
            load_daily_weather(_write(tmp_path, payload))

    def test_non_finite_value_is_rejected(self, tmp_path):
        payload = _synthetic_payload()
        payload["daily"]["temperature_2m_max"][0] = float("nan")
        with pytest.raises(ClimateBenchmarkError, match="not finite"):
            load_daily_weather(_write(tmp_path, payload))


class TestStatistics:
    def test_percentile_uses_linear_interpolation(self):
        assert percentile([0.0, 10.0], 0.5) == pytest.approx(5.0)
        assert percentile([0.0, 10.0], 0.25) == pytest.approx(2.5)
        assert percentile([1.0, 2.0, 3.0], 0.0) == 1.0
        assert percentile([1.0, 2.0, 3.0], 1.0) == 3.0

    def test_ols_recovers_a_known_slope(self):
        xs = [0, 1, 2, 3, 4]
        ys = [1.0 + 2.0 * x for x in xs]
        result = ols_trend(xs, ys)
        assert result["slope_per_year"] == pytest.approx(2.0)
        assert result["slope_per_decade"] == pytest.approx(20.0)
        assert result["r_squared"] == pytest.approx(1.0)
        assert "not attribution" in result["interpretation"]

    def test_theil_sen_resists_a_single_outlier(self):
        xs = [0, 1, 2, 3, 4]
        ys = [0.0, 1.0, 2.0, 3.0, 100.0]
        robust = theil_sen_trend(xs, ys)
        assert robust["slope_per_year"] == pytest.approx(1.0)


@pytest.mark.skipif(not _available(), reason="1991-2025 weather record not present")
class TestRealRecordBenchmarks:
    def test_heat_thresholds_are_kochi_specific_and_flagged(self):
        record = load_daily_weather(WEATHER)
        heat = heat_benchmarks(record, BASELINE)
        assert 31.0 <= heat["thresholds"]["baseline_p95_c"] <= 33.0
        assert heat["thresholds"]["full_record_max_c"] >= 34.0
        assert heat["absolute_screening_counts"]["days_ge_37c"] == 0
        assert "not IMD" in heat["interpretation"]

    def test_rainfall_totals_and_extremes_are_plausible(self):
        record = load_daily_weather(WEATHER)
        rain = rainfall_benchmarks(record, BASELINE)
        assert 2000 <= rain["annual_total_mm"]["mean"] <= 3500
        assert rain["wettest_day"]["precipitation_mm"] >= 150
        assert rain["heavy_day_counts"]["days_ge_50mm"] > 0
        assert rain["heavy_day_counts"]["days_ge_150mm"] <= rain["heavy_day_counts"]["days_ge_100mm"]

    def test_drought_windows_are_ordered_and_marked_rainfall_only(self):
        record = load_daily_weather(WEATHER)
        drought = drought_benchmarks(record)
        window = drought["rolling_windows"]["30_day"]
        assert window["p05_mm"] < window["p10_mm"] < window["distribution_mm"]["median"]
        assert drought["longest_dry_spell"]["length_days"] >= 30
        assert "not SPI" in drought["interpretation"]
        assert "not independent" in window["overlapping_windows_note"]

    def test_wind_is_labelled_as_gust_context(self):
        record = load_daily_weather(WEATHER)
        wind = wind_benchmarks(record)
        assert wind["daily_gust_kmh"]["maximum"] >= 50
        assert "not a cyclone" in wind["interpretation"]

    def test_monthly_totals_are_complete_and_consecutive(self):
        record = load_daily_weather(WEATHER)
        rows = monthly_totals(record)
        assert len(rows) == 35 * 12
        assert all(row["complete"] for row in rows)
        assert rows[0]["month"] == "1991-01"
        assert rows[-1]["month"] == "2025-12"

    def test_spi_readiness_meets_30_year_rule_and_computes_descriptive_series(self):
        record = load_daily_weather(WEATHER)
        spi = spi_readiness(record)
        assert spi["meets_30_year_spi_reference_rule"] is True
        assert spi["reference_years"] == 35
        assert all(count >= 30 for count in spi["calendar_month_counts"].values())
        assert spi["spi1_status"] == "descriptive_series_computed"
        assert len(spi["spi1_series"]) == 12
        assert all("spi1" in row for row in spi["spi1_series"])

    def test_report_carries_limitations_and_validation_checks(self):
        report = build_benchmark_report(
            WEATHER,
            comparison_path=COMPARISON,
            training_report_path=TRAINING,
        )
        assert report["status"] == STATUS
        assert report["source"]["source_type"].startswith("MODELLED REANALYSIS")
        assert "not a rain-gauge" in " ".join(report["limitations"])
        assert report["validation"]["record_continuity"]["complete_year_count"] == 35
        overlap = report["validation"]["overlap_comparison"]
        assert overlap["overlap_days"] == 9497
        assert overlap["differing_days_by_series"]["precipitation_sum"] == 0
        assert overlap["maximum_absolute_difference"]["temperature_2m_max"] <= 0.1 + 1e-9
        check = report["validation"]["training_threshold_cross_check"]
        assert check["comparable_as_kochi_threshold"] is False
        assert check["difference_c"] == pytest.approx(0.9)

    def test_report_paths_are_portable_and_do_not_leak_local_directories(self):
        report = build_benchmark_report(
            WEATHER,
            comparison_path=COMPARISON,
            training_report_path=TRAINING,
        )
        paths = [
            report["source"]["file"],
            report["validation"]["overlap_comparison"]["primary_file"],
            report["validation"]["overlap_comparison"]["secondary_file"],
        ]
        if "training_threshold_cross_check" in report["validation"]:
            paths.append(
                report["validation"]["training_threshold_cross_check"]["training_report"]
            )
        for value in paths:
            assert not Path(value).is_absolute(), value
            assert "\\" not in value, value
            assert not value.startswith("D:"), value
            assert str(ROOT).replace("\\", "/") not in value, value


@pytest.mark.skipif(not (_available() and COMPARISON.is_file()), reason="weather records not present")
def test_overlap_comparison_does_not_splice_or_hide_differences():
    primary = load_daily_weather(WEATHER)
    secondary = load_daily_weather(COMPARISON)
    comparison = compare_overlapping_records(primary, secondary)
    assert comparison["overlap_days"] == 9497
    assert comparison["elevation_m"]["primary"] != comparison["elevation_m"]["secondary"]
    assert comparison["maximum_absolute_difference"]["temperature_2m_max"] <= 0.1 + 1e-9
    assert "not spliced" in comparison["interpretation"]


@pytest.mark.skipif(not (_available() and TRAINING.is_file()), reason="training report not present")
def test_pooled_training_threshold_is_not_treated_as_kochi_specific():
    record = load_daily_weather(WEATHER)
    heat = heat_benchmarks(record, BASELINE)
    check = compare_with_training_report(TRAINING, heat)
    assert check["available"] is True
    assert check["training_locations"] and len(check["training_locations"]) == 4
    assert check["comparable_as_kochi_threshold"] is False
    assert check["training_threshold_c"] > check["kochi_baseline_p95_c"]

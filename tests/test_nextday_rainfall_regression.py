import pandas as pd

from scripts.train_nextday_rainfall_regression import (
    WEATHER_COLUMNS,
    build_supervised_frame,
)


def make_daily(start="2020-01-01", periods=16):
    dates = pd.date_range(start, periods=periods, freq="D")
    frame = pd.DataFrame({"date": dates, "location": "kochi"})
    for index, column in enumerate(WEATHER_COLUMNS):
        frame[column] = [float(day + index) for day in range(periods)]
    return frame


def test_target_is_next_calendar_day_and_features_are_prior_days_only():
    daily = make_daily()
    supervised = build_supervised_frame(daily)

    row = supervised.loc[supervised["feature_date"] == pd.Timestamp("2020-01-08")].iloc[0]
    assert row["target_date"] == pd.Timestamp("2020-01-09")
    # Jan 8 is the feature date; lag1 is Jan 7, not Jan 8.
    assert row["precipitation_sum_lag1"] == 6.0
    assert row["target_rain_mm"] == 8.0


def test_missing_calendar_day_breaks_lag_chain_instead_of_becoming_a_false_lag():
    daily = make_daily()
    daily = daily.loc[daily["date"] != pd.Timestamp("2020-01-05")]
    supervised = build_supervised_frame(daily)

    # A row immediately after the missing day has no valid seven-day history.
    assert pd.Timestamp("2020-01-06") not in set(supervised["feature_date"])
    # After seven complete days have elapsed, valid rows can resume.
    assert pd.Timestamp("2020-01-12") in set(supervised["feature_date"])

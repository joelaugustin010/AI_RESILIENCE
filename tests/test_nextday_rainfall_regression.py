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
    # The completed Jan 8 observation is available for the Jan 9 prediction.
    assert row["precipitation_sum_feature_day"] == 9.0
    assert row["target_rain_mm"] == 10.0


def test_missing_calendar_day_breaks_lag_chain_instead_of_becoming_a_false_lag():
    daily = make_daily()
    daily = daily.loc[daily["date"] != pd.Timestamp("2020-01-05")]
    supervised = build_supervised_frame(daily)

    # A row immediately after the missing day has no valid seven-day history.
    assert pd.Timestamp("2020-01-06") not in set(supervised["target_date"])
    # Jan 6–12 provide seven complete observations for the Jan 13 target.
    assert pd.Timestamp("2020-01-13") in set(supervised["target_date"])

"""W2 indicator functions: every expected number below is counted by hand from a small fixture."""

import numpy as np
import pandas as pd
import pytest

from indicators.core import (cdd, climatic_balance, count_beyond, leave_one_out_z, r20mm_days,
                             rx1day, season_total, window_series)


def daily(start, values):
    return pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"), dtype=float)


def test_window_series_complete_window_is_returned():
    s = daily("2010-01-01", np.ones(181))  # 1 Jan to 30 Jun 2010
    w = window_series(s, "kharif1", 2010)  # 1 Mar to 30 Jun = 31+30+31+30 = 122 days
    assert len(w) == 122
    assert w.index[0] == pd.Timestamp("2010-03-01") and w.index[-1] == pd.Timestamp("2010-06-30")


def test_window_series_rabi_crosses_the_new_year():
    s = daily("2010-11-01", np.ones(120))  # 1 Nov 2010 to 28 Feb 2011 = 30+31+31+28 = 120 days
    assert len(window_series(s, "rabi", 2010)) == 120


def test_window_series_returns_none_if_any_day_missing_or_nan():
    s = daily("2010-01-01", np.ones(181))
    assert window_series(s.drop(pd.Timestamp("2010-04-15")), "kharif1", 2010) is None
    s2 = s.copy()
    s2.loc["2010-05-05"] = np.nan
    assert window_series(s2, "kharif1", 2010) is None
    assert window_series(s.loc[:"2010-06-29"], "kharif1", 2010) is None  # last day not observed


def test_count_beyond_is_strict_for_heat_and_cold():
    tmax = [34.9, 35.0, 35.1, 40.0, 30.0]
    assert count_beyond(tmax, 35.0, ">") == 2  # 35.1 and 40.0; exactly 35.0 is not above
    tmin = [7.9, 8.0, 3.0, 12.0]
    assert count_beyond(tmin, 8.0, "<") == 2  # 7.9 and 3.0


def test_r20mm_counts_days_at_or_above_20():
    assert r20mm_days([0, 20, 19.9, 25, 5]) == 2  # 20.0 counts (>= 20), 19.9 does not


def test_rx1day_is_the_largest_day():
    assert rx1day([0, 20, 19.9, 25, 5]) == 25.0


def test_cdd_longest_run_below_1mm():
    # <1 flags:  T  T  F  T  T  T  F  T   -> runs 2, 3, 1  (1.0 mm is NOT dry, 0.9 is)
    rain = [0, 0.5, 2, 0, 0, 0, 1.0, 0.9]
    assert cdd(rain) == 3


def test_cdd_all_wet_is_zero_and_all_dry_is_length():
    assert cdd([5, 5, 5]) == 0
    assert cdd([0, 0, 0, 0]) == 4


def test_season_total_and_climatic_balance():
    rain = [10, 0, 5.5]
    et0 = [3, 4, 3.5]
    assert season_total(et0) == 10.5
    assert climatic_balance(rain, et0) == pytest.approx(15.5 - 10.5)  # +5.0


def test_leave_one_out_z_by_hand():
    by_year = {2001: 1.0, 2002: 2.0, 2003: 3.0, 2004: 4.0, 2005: 5.0, 2006: 6.0}
    z, n_other = leave_one_out_z(by_year, 2006)
    # others 1..5: mean 3, sample sd = sqrt(10/4) = 1.58114; z = (6-3)/1.58114
    assert n_other == 5
    assert z == pytest.approx(3.0 / np.sqrt(2.5))


def test_leave_one_out_z_needs_five_other_years():
    by_year = {2001: 1.0, 2002: 2.0, 2003: 3.0, 2004: 4.0, 2005: 5.0}
    z, n_other = leave_one_out_z(by_year, 2005)
    assert n_other == 4 and np.isnan(z)


def test_leave_one_out_z_ignores_nan_years_and_zero_spread():
    by_year = {2001: 1.0, 2002: np.nan, 2003: 1.0, 2004: 1.0, 2005: 1.0, 2006: 1.0, 2007: 2.0}
    z, n_other = leave_one_out_z(by_year, 2007)
    assert n_other == 5 and np.isnan(z)  # others all 1.0: sd = 0, so no z-score
    z2, n2 = leave_one_out_z(by_year, 2002)
    assert np.isnan(z2)  # the year itself is missing

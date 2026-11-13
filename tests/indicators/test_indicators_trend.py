"""Trend + homogeneity check: Theil-Sen/Kendall, then Pettitt on the detrended residuals."""

import numpy as np

from indicators.trend import trend_status

YEARS = list(range(2001, 2025))  # 24 seasons


def test_perfect_line_is_a_trend():
    r = trend_status(YEARS, [2.0 * i for i in range(24)])
    assert r["slope"] == 2.0 and r["tau"] == 1.0
    assert r["kendall_p"] < 0.001
    assert r["pettitt_p"] == 1.0  # residuals are all 0: no break
    assert r["status"] == "trend" and r["n"] == 24


def test_level_shift_is_step_change_not_trend():
    # 12 years at 0, then 12 years at 10: Kendall is "significant" but it is one jump
    r = trend_status(YEARS, [0.0] * 12 + [10.0] * 12)
    assert r["kendall_p"] < 0.05
    assert r["pettitt_p"] < 0.05
    assert r["status"] == "step_change"
    assert r["step_year"] == 2013  # first year of the new level


def test_constant_series_is_no_trend():
    r = trend_status(YEARS, [5.0] * 24)
    assert r["status"] == "no_trend" and r["kendall_p"] == 1.0


def test_alternating_series_is_no_trend():
    # 1,2,1,2,...: concordant 78, discordant 66 -> tau about 0.09, p far above 0.05
    r = trend_status(YEARS, [1.0, 2.0] * 12)
    assert r["status"] == "no_trend"
    assert r["kendall_p"] > 0.3


def test_nan_years_are_dropped_and_counted():
    v = [2.0 * i for i in range(24)]
    v[3] = np.nan
    r = trend_status(YEARS, v)
    assert r["n"] == 23 and r["status"] == "trend"


def test_too_few_years():
    r = trend_status([2001, 2002, 2003, 2004, 2005], [1, 2, 3, 4, 5])
    assert r["status"] == "not_enough_years" and r["n"] == 5


def test_explanation_text_names_the_year_for_a_step():
    r = trend_status(YEARS, [0.0] * 12 + [10.0] * 12)
    assert "level shift around 2013" in r["text"] and "not shown as a trend" in r["text"]

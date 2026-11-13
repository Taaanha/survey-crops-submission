"""Satellite vs ground check: monthly means and bias, worked by hand."""

import numpy as np
import pandas as pd
import pytest

from indicators.ground import bias_table, monthly_mean_rain


def two_years(jan_2002=2.0):
    idx = pd.date_range("2001-01-01", "2002-12-31", freq="D")
    s = pd.Series(1.0, index=idx)
    s.loc["2002-01-01":"2002-01-31"] = jan_2002
    return s


def test_monthly_mean_rain_by_hand():
    m = monthly_mean_rain(two_years(), range(2001, 2003))
    # January: 2001 = 31 x 1 = 31 mm, 2002 = 31 x 2 = 62 mm -> mean 46.5; February: 28 and 28
    assert m.loc[1, "mean_mm"] == 46.5 and m.loc[1, "n_years"] == 2
    assert m.loc[2, "mean_mm"] == 28.0
    # annual mean = (365 + 396) / 2 = 380.5 = sum of the monthly means
    assert m["mean_mm"].sum() == pytest.approx(380.5)


def test_incomplete_month_is_left_out_of_that_year():
    s = two_years().drop(pd.Timestamp("2002-01-10"))
    m = monthly_mean_rain(s, range(2001, 2003))
    assert m.loc[1, "mean_mm"] == 31.0 and m.loc[1, "n_years"] == 1


def test_bias_table_mm_and_percent():
    sat = pd.DataFrame({"mean_mm": [110.0, 45.0, 0.0] + [10.0] * 9, "n_years": 24}, index=range(1, 13))
    normal = pd.Series([100.0, 50.0, 0.0] + [10.0] * 9, index=range(1, 13))
    t = bias_table(sat, normal)
    assert t.loc[1, "bias_mm"] == 10.0 and t.loc[1, "bias_pct"] == pytest.approx(10.0)
    assert t.loc[2, "bias_mm"] == -5.0 and t.loc[2, "bias_pct"] == pytest.approx(-10.0)
    assert np.isnan(t.loc[3, "bias_pct"])  # normal is 0: no percentage
    # annual row: satellite 110+45+0+90 = 245, normal 100+50+0+90 = 240
    a = t.loc["annual"]
    assert a["satellite_mm"] == 245.0 and a["normal_mm"] == 240.0
    assert a["bias_mm"] == 5.0 and a["bias_pct"] == pytest.approx(5.0 / 240.0 * 100)

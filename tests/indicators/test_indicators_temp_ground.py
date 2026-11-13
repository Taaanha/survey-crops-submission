"""POWER temperature vs BMD normals: monthly means and bias in degrees C, worked by hand."""

import numpy as np
import pandas as pd
import pytest

from indicators.ground import monthly_mean_temp, temp_bias_table, temperature_normals


def two_years():
    idx = pd.date_range("2001-01-01", "2002-12-31", freq="D")
    s = pd.Series(20.0, index=idx)
    s.loc["2002-01-01":"2002-01-31"] = 22.0
    return s


def test_monthly_mean_temp_by_hand():
    m = monthly_mean_temp(two_years(), range(2001, 2003))
    # January: 2001 mean 20, 2002 mean 22 -> 21; February: 20 and 20 -> 20
    assert m.loc[1, "mean_c"] == 21.0 and m.loc[1, "n_years"] == 2
    assert m.loc[2, "mean_c"] == 20.0


def test_incomplete_month_left_out():
    s = two_years().drop(pd.Timestamp("2002-01-10"))
    m = monthly_mean_temp(s, range(2001, 2003))
    assert m.loc[1, "mean_c"] == 20.0 and m.loc[1, "n_years"] == 1


def test_temp_bias_table_degrees_and_annual_is_the_mean_not_the_sum():
    model = pd.DataFrame({"mean_c": [20.0, 22.0] + [25.0] * 10, "n_years": 24}, index=range(1, 13))
    normal = pd.Series([21.0, 20.0] + [26.0] * 10, index=range(1, 13))
    t = temp_bias_table(model, normal)
    assert t.loc[1, "bias_c"] == -1.0 and t.loc[2, "bias_c"] == 2.0 and t.loc[3, "bias_c"] == -1.0
    # annual: model (20 + 22 + 250) / 12 = 24.3333, normal (21 + 20 + 260) / 12 = 25.0833, bias = -0.75
    a = t.loc["annual"]
    assert a["model_c"] == pytest.approx(292 / 12) and a["normal_c"] == pytest.approx(301 / 12)
    assert a["bias_c"] == pytest.approx(-0.75)


def test_temperature_normals_read_by_station_and_kind():
    cols = ["item", "value", "unit", "source_title", "source_url", "page", "year", "notes"]
    rows = [[f"cumilla.normal_tmax_{m}", str(25 + i), "deg C", "T", "https://x", "19", "2016", "Period 1981-2010"]
            for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])]
    rows.append(["cumilla.normal_tmin_jan", "12.1", "deg C", "T", "https://x", "19", "2016", "Period 1981-2010"])
    table = pd.DataFrame(rows, columns=cols)
    tmax = temperature_normals(table, "cumilla", "tmax")
    assert list(tmax.index) == list(range(1, 13)) and tmax.loc[1] == 25.0 and tmax.loc[12] == 36.0
    tmin = temperature_normals(table, "cumilla", "tmin")
    assert tmin.loc[1] == 12.1 and tmin.drop(1).isna().all()
    assert temperature_normals(table, "feni", "tmax").isna().all()   # no rows: all NaN, not 0

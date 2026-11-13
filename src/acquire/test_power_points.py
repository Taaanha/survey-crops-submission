"""POWER point responses: column names, fill values and the grid cell POWER reports."""

import numpy as np
import pytest

import power_points as pp

FAKE = {
    "geometry": {"coordinates": [91.5, 23.5, 12.3]},
    "properties": {"parameter": {
        "PRECTOTCORR": {"20240101": 1.5, "20240102": -999},
        "T2M": {"20240101": 20.0, "20240102": 21.0},
        "T2M_MAX": {"20240101": 25.0, "20240102": 26.0},
        "T2M_MIN": {"20240101": 15.0, "20240102": 16.0},
        "RH2M": {"20240101": 70.0, "20240102": 71.0},
        "WS2M": {"20240101": 2.0, "20240102": 2.5},
        "ALLSKY_SFC_SW_DWN": {"20240101": 14.0, "20240102": 15.0},
    }},
}


def test_parse_uses_project_column_names_and_nan_for_fill():
    df, elev = pp.parse_power(FAKE)
    assert list(df.columns) == ["rainfall_mm", "temp_mean_c", "temp_max_c", "temp_min_c",
                                "rh_pct", "wind_speed_ms", "solar_rad_mj_m2"]
    assert str(df.index[0].date()) == "2024-01-01" and df.index.name == "date"
    assert np.isnan(df.loc["2024-01-02", "rainfall_mm"])
    assert df.loc["2024-01-01", "temp_max_c"] == 25.0
    assert elev == 12.3


def test_parse_missing_parameter_is_an_error():
    bad = {"geometry": FAKE["geometry"], "properties": {"parameter": {"T2M": {"20240101": 1}}}}
    with pytest.raises(KeyError):
        pp.parse_power(bad)


def test_request_params_use_ag_community_and_point():
    p = pp.request_params(23.5, 91.5, "20010101", "20241231")
    assert p["community"] == "AG" and p["latitude"] == 23.5 and p["longitude"] == 91.5
    assert p["parameters"].split(",")[0] == "PRECTOTCORR" and p["format"] == "JSON"

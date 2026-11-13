"""District x season feature table: season windows, totals and missing-data rules by hand."""

import numpy as np
import pandas as pd
import pytest

from district_grid.features import COLUMN_INFO, SEASONS, season_features, season_range


def test_season_windows():
    assert season_range("kharif1", 2010) == (pd.Timestamp("2010-03-01"), pd.Timestamp("2010-06-30"))
    assert season_range("kharif2", 2010) == (pd.Timestamp("2010-07-01"), pd.Timestamp("2010-10-31"))
    # rabi of season year 2010 runs from Nov 2010 into Feb 2011 (and a leap February counts 29 days)
    assert season_range("rabi", 2011) == (pd.Timestamp("2011-11-01"), pd.Timestamp("2012-02-29"))
    assert set(SEASONS) == {"kharif1", "kharif2", "rabi"}


def _daily(start, end, **cols):
    idx = pd.date_range(start, end, freq="D", name="date")
    return pd.DataFrame({k: np.full(len(idx), v, dtype=float) for k, v in cols.items()}, index=idx)


def test_rain_total_and_max_for_one_season_by_hand():
    rain = _daily("2010-07-01", "2010-10-31", rainfall_mm=2.0)["rainfall_mm"]   # 123 days of 2 mm
    rain.loc["2010-08-15"] = 50.0
    power = _daily("2010-07-01", "2010-10-31", temp_mean_c=28.0, temp_max_c=32.0, temp_min_c=24.0,
                   rh_pct=80.0, wind_speed_ms=2.0, solar_rad_mj_m2=15.0)
    f = season_features(rain, power, years=[2010], seasons=["kharif2"]).iloc[0]
    assert f["n_days"] == 123
    assert f["rain_total_mm"] == pytest.approx(122 * 2.0 + 50.0)
    assert f["rain_max_1d_mm"] == 50.0
    assert f["tmax_mean_c"] == 32.0 and f["solar_sum_mj_m2"] == pytest.approx(15.0 * 123)
    assert f["imerg_days_obs"] == 123 and f["power_days_obs"] == 123


def test_rain_total_is_nan_if_any_day_is_missing_but_counts_are_reported():
    rain = _daily("2010-07-01", "2010-10-31", rainfall_mm=1.0)["rainfall_mm"]
    rain.loc["2010-09-01"] = np.nan
    power = _daily("2010-07-01", "2010-10-31", temp_mean_c=28.0, temp_max_c=32.0, temp_min_c=24.0,
                   rh_pct=80.0, wind_speed_ms=2.0, solar_rad_mj_m2=15.0)
    f = season_features(rain, power, years=[2010], seasons=["kharif2"]).iloc[0]
    assert np.isnan(f["rain_total_mm"]) and f["imerg_days_obs"] == 122
    assert f["rain_max_1d_mm"] == 1.0           # the maximum of the observed days is still real


def test_season_with_no_data_is_kept_as_nan_row_not_dropped():
    rain = _daily("2010-07-01", "2010-07-10", rainfall_mm=1.0)["rainfall_mm"]
    power = _daily("2010-07-01", "2010-07-10", temp_mean_c=28.0, temp_max_c=32.0, temp_min_c=24.0,
                   rh_pct=80.0, wind_speed_ms=2.0, solar_rad_mj_m2=15.0)
    out = season_features(rain, power, years=[2010, 2011], seasons=["kharif2"])
    assert len(out) == 2 and out.iloc[1]["imerg_days_obs"] == 0 and np.isnan(out.iloc[1]["tmean_c"])


def test_every_feature_column_has_dataset_unit_and_source_url():
    out_cols = set(season_features(pd.Series(dtype=float), pd.DataFrame(), years=[2010], seasons=["rabi"]).columns)
    keys = {c for c in COLUMN_INFO}
    assert {"rain_total_mm", "tmax_mean_c", "solar_sum_mj_m2"} <= keys
    assert keys <= out_cols
    for col, info in COLUMN_INFO.items():
        assert info["dataset"] and info["unit"] and info["source_url"].startswith("https://"), col

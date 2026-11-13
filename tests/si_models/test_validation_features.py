"""W3 validation helpers and the feature table, on hand-worked fixtures."""

import numpy as np
import pandas as pd
import pytest

from si_models import features as F
from si_models.validation import beats, bootstrap_ci, loyo_splits, paired_diff_ci


def test_loyo_splits_never_put_the_test_year_in_train():
    splits = loyo_splits([2003, 2001, 2002, 2002])
    assert [y for _, y in splits] == [2001, 2002, 2003]
    assert splits[0] == ([2002, 2003], 2001)
    assert all(y not in train for train, y in splits)


def test_bootstrap_ci_value_n_and_fixed_seed():
    r = bootstrap_ci([1, 2, 3, 4, np.nan])
    assert r["value"] == 2.5 and r["n"] == 4            # NaN dropped and not counted
    assert r["lo"] <= 2.5 <= r["hi"] and 1 <= r["lo"] and r["hi"] <= 4
    assert bootstrap_ci([1, 2, 3, 4]) == bootstrap_ci([1, 2, 3, 4])   # same seed, same interval
    assert bootstrap_ci([5, 5, 5])["lo"] == 5 == bootstrap_ci([5, 5, 5])["hi"]


def test_bootstrap_ci_small_n_is_not_dressed_up():
    empty, one = bootstrap_ci([]), bootstrap_ci([7.0])
    assert empty["n"] == 0 and np.isnan(empty["value"])
    assert one["value"] == 7.0 and np.isnan(one["lo"]) and np.isnan(one["hi"])


def test_paired_diff_and_beats():
    win = paired_diff_ci([0, 0, 0, 0], [1, 1, 1, 1])
    assert win["value"] == 1 and beats(win)
    tie = paired_diff_ci([0, 1, 0, 1], [1, 0, 1, 0])
    assert tie["value"] == 0 and not beats(tie)
    assert not beats(paired_diff_ci([0], [1]))            # one pair is never a win
    with pytest.raises(ValueError):
        paired_diff_ci([1, 2], [1])


def _features():
    # one district-season, values 1..5 for 2001..2005, and a second district offset by 100
    rows = [{"district": d, "season_year": 2000 + i, "season": "rabi", "x": off + i}
            for d, off in (("a", 0), ("b", 100)) for i in range(1, 6)]
    return pd.DataFrame(rows)


def test_standardize_loyo_hand_worked():
    f = _features()
    z = F.standardize_loyo(f, ["x"], 2005)
    # train years 2001-2004: values 1,2,3,4 -> mean 2.5, sample sd 1.2910
    sd = np.std([1, 2, 3, 4], ddof=1)
    a = z[z.district == "a"].set_index("season_year").x
    assert a[2005] == pytest.approx((5 - 2.5) / sd)
    assert a[2001] == pytest.approx((1 - 2.5) / sd)
    b = z[z.district == "b"].set_index("season_year").x
    assert b[2005] == pytest.approx(a[2005])              # each district uses its own mean


def test_standardize_loyo_ignores_the_test_year_value():
    f = _features()
    g = f.copy()
    g.loc[g.season_year == 2005, "x"] = 9999.0            # change only the held-out year
    z1, z2 = F.standardize_loyo(f, ["x"], 2005), F.standardize_loyo(g, ["x"], 2005)
    train = f.season_year != 2005
    assert np.allclose(z1.loc[train, "x"], z2.loc[train, "x"])   # train z-scores did not move


def test_standardize_loyo_no_spread_is_nan():
    f = _features()
    f["x"] = 3.0
    assert F.standardize_loyo(f, ["x"], 2005).x.isna().all()


def test_season_weather_features_complete_and_incomplete_windows():
    days = pd.date_range("2001-03-01", "2001-10-31", freq="D")
    w = pd.DataFrame({"rainfall_mm": 2.0, "temp_max_c": 30.0, "temp_min_c": 20.0}, index=days)
    w.loc["2001-08-10", "rainfall_mm"] = np.nan           # one missing rain day in kharif2
    out = F.season_weather_features(w, [2001], ["kharif1", "kharif2"]).set_index("season")
    assert out.loc["kharif1", "rain_total_mm"] == 2.0 * 122          # 1 Mar to 30 Jun = 122 days
    assert out.loc["kharif1", "tmax_mean_c"] == 30.0
    assert np.isnan(out.loc["kharif2", "rain_total_mm"])              # NaN, never 0
    assert out.loc["kharif2", "tmin_mean_c"] == 20.0


def test_wide_indicators_keeps_nan_and_drops_rows_without_a_year():
    long = pd.DataFrame([
        {"district": "a", "season_year": 2001.0, "season": "rabi", "indicator": "cdd", "value": 12.0},
        {"district": "a", "season_year": 2001.0, "season": "rabi", "indicator": "smap_rootzone_z", "value": np.nan},
        {"district": "a", "season_year": np.nan, "season": "rabi", "indicator": "grace_fo_trend", "value": 1.0},
    ])
    w = F.wide_indicators(long, ["cdd", "smap_rootzone_z"])
    assert len(w) == 1 and w.cdd[0] == 12.0 and np.isnan(w.smap_rootzone_z[0])
    assert w.season_year.dtype.kind == "i"


def test_ndvi_season_mean_needs_enough_composites():
    dates = pd.date_range("2016-03-05", periods=7, freq="16D")       # all inside kharif1 2016
    m = pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "district": "a",
                      "ndvi": [0.4, 0.5, np.nan, 0.6, 0.5, np.nan, np.nan]})
    out = F.ndvi_season_mean(m, "a", [2016], ["kharif1"])
    assert out.ndvi_n[0] == 4 and out.ndvi_season_mean[0] == pytest.approx(0.5)
    out = F.ndvi_season_mean(m.iloc[:3], "a", [2016], ["kharif1"])
    assert out.ndvi_n[0] == 2 and np.isnan(out.ndvi_season_mean[0])  # 2 composites: not assessed


def test_every_feature_has_a_dataset_and_link():
    from si_models.stress import SATELLITE_FEATURES
    for c in SATELLITE_FEATURES:
        assert F.PROVENANCE[c]["dataset"] and F.PROVENANCE[c]["source_url"].startswith("http")

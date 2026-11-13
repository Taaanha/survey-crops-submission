"""Tests for src/compute/disease_risk (potato late blight; others not assessed)."""

import datetime as dt

import numpy as np
import pandas as pd
import pytest

import disease_risk as dr
from disease_risk import core
from reference import load_file

RULE = {"crop": "potato", "disease": "late_blight", "min_run_days": 10,
        "values": {"tmean_below_c": 25.5, "rain10_mm_at_least": 30.0, "tmin_unfavourable_below_c": 7.2}}
WINDOW = ((11, 1), (11, 30), 55)


def make_weather(first="2000-10-01", last="2003-03-01", rain=0.0, tmean=20.0, tmin=15.0):
    idx = pd.date_range(first, last)
    return pd.DataFrame({"rainfall_mm": rain, "temp_mean_c": tmean, "temp_min_c": tmin}, index=idx)


def set_days(w, start, end, **cols):
    for k, v in cols.items():
        w.loc[start:end, k] = v


def test_longest_run():
    assert dr.longest_run([1, 1, 0, 1, 1, 1, 0]) == 3
    assert dr.longest_run([]) == 0


def test_wet_cool_days_are_favourable_dry_or_hot_or_cold_are_not():
    w = make_weather(rain=3.5)                      # 35 mm per 10 days, 20 C
    assert dr.favourable_days(w, RULE).iloc[20]
    assert not dr.favourable_days(make_weather(rain=2.9), RULE).iloc[20]      # 29 mm < 30
    assert not dr.favourable_days(make_weather(rain=3.5, tmean=26.0), RULE).iloc[20]
    assert not dr.favourable_days(make_weather(rain=3.5, tmin=7.0), RULE).iloc[20]
    assert dr.favourable_days(make_weather(rain=3.5, tmin=7.2), RULE).iloc[20]   # exactly the limit is not below it


def test_missing_input_is_not_favourable():
    w = make_weather(rain=3.5)
    w.iloc[18:23, w.columns.get_loc("rainfall_mm")] = np.nan
    assert not dr.favourable_days(w, RULE).iloc[20]


def test_season_window_is_cited_start_to_end_plus_days():
    a, b = dr.season_window(2005, (11, 1), (11, 30), 55)
    assert a == dt.date(2005, 11, 1) and b == dt.date(2006, 1, 24)


def test_counts_one_wet_season_out_of_three():
    w = make_weather()
    set_days(w, "2001-12-01", "2001-12-14", rainfall_mm=5.0)    # 14 wet days -> a long run in season 2001
    out = dr.count_seasons(w, RULE, *WINDOW, seasons=(2000, 2001, 2002))
    assert out["n_seasons"] == 3 and out["seasons_favourable"] == 1
    by = {r["season"]: r for r in out["per_season"]}
    assert by[2001]["favourable"] and not by[2000]["favourable"] and not by[2002]["favourable"]
    assert by[2000]["favourable_days"] == 0           # an assessed zero is a real 0


def test_short_run_is_not_a_season_but_counts_as_any_day():
    w = make_weather()
    set_days(w, "2001-12-01", "2001-12-03", rainfall_mm=11.0)   # 3 wet days: 10-day total >= 30 for ~10 days only
    out = dr.count_seasons(w, RULE, *WINDOW, seasons=(2001,))
    row = out["per_season"][0]
    assert row["favourable_days"] > 0
    assert row["favourable"] == (row["longest_run_days"] >= 10)


def test_season_without_full_weather_is_skipped_not_zero():
    w = make_weather(first="2001-11-20", last="2003-03-01")      # season 2001 window starts before the data
    out = dr.count_seasons(w, RULE, *WINDOW, seasons=(2001, 2002))
    assert out["skipped_seasons"] == [2001] and out["n_seasons"] == 1
    w2 = make_weather()
    w2.loc["2002-12-05", "rainfall_mm"] = np.nan                   # a gap inside season 2002
    out2 = dr.count_seasons(w2, RULE, *WINDOW, seasons=(2001, 2002))
    assert out2["skipped_seasons"] == [2002]


def kept_skipped():
    return load_file("data/reference/disease_rules_draft.csv")


def test_build_rule_uses_the_three_cited_rows():
    kept, _ = kept_skipped()
    rule = dr.build_rule(kept, "potato")
    assert rule["values"] == {"tmean_below_c": 25.5, "rain10_mm_at_least": 30.0,
                              "tmin_unfavourable_below_c": 7.2}
    assert len(rule["citations"]) == 3 and all(c["source_url"].startswith("http") for c in rule["citations"])


def test_wheat_has_no_usable_source_link_so_not_assessed():
    kept, skipped = kept_skipped()
    out = dr.assess_crop("wheat", make_weather(), kept, skipped, *WINDOW)
    assert out["status"] == "not_assessed" and "source link" in out["reason"]
    assert "seasons_favourable" not in out


def test_lentil_needs_leaf_wetness_so_not_assessed():
    kept, skipped = kept_skipped()
    out = dr.assess_crop("lentil", make_weather(), kept, skipped, *WINDOW)
    assert out["status"] == "not_assessed" and "leaf-wetness" in out["reason"]


@pytest.mark.parametrize("crop", ["mustard", "boro_rice", "nonsense"])
def test_crops_without_a_rule_are_not_assessed(crop):
    kept, skipped = kept_skipped()
    out = dr.assess_crop(crop, make_weather(), kept, skipped, *WINDOW)
    assert out["status"] == "not_assessed" and out["reason"] == "no sourced disease rule for this crop"


def test_potato_without_a_window_is_not_assessed():
    kept, skipped = kept_skipped()
    assert dr.assess_crop("potato", make_weather(), kept, skipped)["status"] == "not_assessed"


def test_assess_potato_reports_counts_and_citations():
    kept, skipped = kept_skipped()
    w = make_weather(first="2000-10-01", last="2003-03-01")
    set_days(w, "2001-12-01", "2001-12-14", rainfall_mm=5.0)
    out = core.assess_crop("potato", w, kept, skipped, *WINDOW)
    assert out["status"] == "assessed" and out["disease"] == "late_blight"
    assert out["n_seasons"] == 2 and out["seasons_favourable"] == 1      # seasons 2001, 2002 have data (2000 starts Oct)
    assert out["citations"][0]["source_url"].startswith("http")


def test_real_data_smoke_cumilla():
    from weather import load_weather
    kept, skipped = kept_skipped()
    w = load_weather("cumilla")
    out = dr.assess_crop("potato", w, kept, skipped, *WINDOW)
    assert out["status"] == "assessed"
    assert out["n_seasons"] == 24 and out["skipped_seasons"] == []
    assert 0 <= out["seasons_favourable"] <= out["seasons_any_favourable_day"] <= 24

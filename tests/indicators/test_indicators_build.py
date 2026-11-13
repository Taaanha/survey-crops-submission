"""District table: season windows, thresholds and not-assessed rows, counted by hand."""

import numpy as np
import pandas as pd
import pytest

from indicators.build import COLUMNS, build_district_table
from indicators.thresholds import classify_item, load_thresholds, select_thresholds

HEAT = {"item": "testcrop.heat.flower_tmax", "kind": "heat_days", "variable": "tmax", "op": ">",
        "value": 35.0, "unit": "degC", "source_title": "Test paper", "source_url": "https://example.org/t",
        "page": "1"}
COLD = {**HEAT, "item": "testcrop.cold.boot_tmin", "kind": "cold_nights", "variable": "tmin", "op": "<",
        "value": 10.0}


def fixture_weather():
    idx = pd.date_range("2006-01-01", "2007-02-28", freq="D")
    w = pd.DataFrame({"rainfall_mm": 0.0, "temp_max_c": 30.0, "temp_min_c": 15.0}, index=idx)
    # kharif2 2006 (1 Jul - 31 Oct, 123 days): rain on Jul 11 (25), Jul 21 (20), Aug 5 (30)
    w.loc["2006-07-11", "rainfall_mm"] = 25.0
    w.loc["2006-07-21", "rainfall_mm"] = 20.0
    w.loc["2006-08-05", "rainfall_mm"] = 30.0
    # three hot days in kharif2 (one is exactly 35.0 and must not count), two cold nights in rabi
    w.loc["2006-08-10":"2006-08-12", "temp_max_c"] = [36.0, 35.0, 41.0]
    w.loc["2006-12-01":"2006-12-02", "temp_min_c"] = [9.9, 4.0]
    return w


def row(df, indicator, season, year=2006):
    r = df[(df.indicator == indicator) & (df.season == season) & (df.season_year == year)]
    assert len(r) == 1, (indicator, season, len(r))
    return r.iloc[0]


@pytest.fixture(scope="module")
def table():
    w = fixture_weather()
    et0 = pd.Series(4.0, index=w.index)
    smap_idx = pd.date_range("2001-01-01", "2006-12-31", freq="D")
    smap = pd.Series(np.nan, index=smap_idx)
    for y, v in zip(range(2001, 2007), [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]):
        smap.loc[f"{y}-07-01":f"{y}-10-31"] = v
    return build_district_table("testville", w, et0, smap, [HEAT, COLD], [2006])


def test_columns_are_the_agreed_long_format(table):
    assert list(table.columns) == COLUMNS


def test_heat_days_counted_in_our_window(table):
    r = row(table, "heat_days__testcrop.heat.flower_tmax", "kharif2")
    assert r.value == 2  # 36 and 41; 35.0 is not above the limit
    assert r.threshold == 35.0 and r.unit == "days" and r.n == 123 and r.status == "ok"
    assert r.threshold_source.startswith("testcrop.heat.flower_tmax") and "https://example.org/t" in r.threshold_source


def test_cold_nights_counted_in_rabi_window(table):
    assert row(table, "cold_nights__testcrop.cold.boot_tmin", "rabi").value == 2  # 9.9 and 4.0
    assert row(table, "cold_nights__testcrop.cold.boot_tmin", "kharif2").value == 0


def test_rain_indicators(table):
    assert row(table, "extreme_rain_days_r20mm", "kharif2").value == 3  # 25, 20, 30
    assert row(table, "rx1day", "kharif2").value == 30.0
    # dry runs: Jul 1-10 = 10, Jul 12-20 = 9, Jul 22-Aug 4 = 10 + 4 = 14, Aug 6-Oct 31 = 26 + 30 + 31 = 87
    assert row(table, "cdd", "kharif2").value == 87


def test_et0_and_balance(table):
    assert row(table, "et0_season_total", "kharif2").value == 492.0  # 123 x 4
    assert row(table, "rain_minus_et0", "kharif2").value == 75.0 - 492.0


def test_smap_z_score_and_n(table):
    r = row(table, "smap_rootzone_z", "kharif2")
    assert r.value == pytest.approx(0.3 / np.sqrt(0.025)) and r.n == 5 and r.status == "ok"


def test_smap_z_is_nan_with_reason_when_other_years_are_too_few(table):
    r = row(table, "smap_rootzone_z", "kharif1")  # SMAP fixture has no kharif1 values
    assert np.isnan(r.value) and r.status.startswith("not enough")


def test_incomplete_window_gives_nan_not_zero(table):
    r = row(table, "heat_days__testcrop.heat.flower_tmax", "kharif1")  # weather starts in Jan 2006: complete
    assert r.value == 0
    w = fixture_weather().drop(pd.Timestamp("2006-08-20"))
    t = build_district_table("testville", w, pd.Series(4.0, index=w.index), None, [HEAT], [2006])
    r2 = row(t, "heat_days__testcrop.heat.flower_tmax", "kharif2")
    assert np.isnan(r2.value) and r2.status.startswith("incomplete")


def test_not_assessed_indicators_are_visible_and_never_zero(table):
    for ind, word in [("modis_ndvi_z", "MODIS"), ("grace_fo_trend", "GRACE"), ("ecostress_et_comparison", "ECOSTRESS")]:
        r = table[(table.indicator == ind) & (table.season == "rabi")]
        assert len(r) == 1
        r = r.iloc[0]
        assert np.isnan(r.value) and r.status.startswith("not assessed") and word in r.status + r.dataset


def test_smap_before_its_first_day_says_so():
    w = fixture_weather()
    smap = pd.Series(0.3, index=pd.date_range("2003-01-01", "2006-12-31", freq="D"))
    t = build_district_table("testville", w, pd.Series(4.0, index=w.index), smap, [], [2001])
    r = row(t, "smap_rootzone_z", "kharif2", year=2001)
    assert np.isnan(r.value) and r.status.startswith("no SMAP data for this window")


def test_no_smap_file_is_reported():
    w = fixture_weather()
    t = build_district_table("testville", w, pd.Series(4.0, index=w.index), None, [], [2006])
    r = row(t, "smap_rootzone_z", "kharif2")
    assert np.isnan(r.value) and r.status.startswith("not assessed")


def test_every_row_has_dataset_and_url(table):
    assert (table.dataset.str.len() > 0).all() and table.source_url.str.startswith("http").all()


# ---------- threshold selection ----------

@pytest.mark.parametrize("item,expected", [
    ("mustard.heat.flowering_tmax_low", ("heat_days", "tmax", ">")),
    ("potato.heat.tuber_tmax", ("heat_days", "tmax", ">")),
    ("potato.heat.tuber_tmin_night_high", ("night_heat_days", "tmin", ">")),
    ("boro_rice.cold.booting_tmin_low", ("cold_nights", "tmin", "<")),
    ("potato.cold.frost_tmin_high", ("cold_nights", "tmin", "<")),
    ("aman_rice.wet.submergence_days", None),
    ("mustard.wet.waterlog_days", None),
    ("boro_rice.cold.seedling_tmean", None),
])
def test_classify_item(item, expected):
    assert classify_item(item) == expected


def test_select_thresholds_drops_repeated_item_and_value():
    kept = pd.DataFrame({
        "item": ["boro_rice.heat.anthesis_tmax", "boro_rice.heat.anthesis_tmax", "wheat.heat.anthesis_tmax"],
        "value": [35.0, 35.0, 31.0], "unit": ["degC"] * 3, "source_title": ["a", "b", "c"],
        "source_url": ["http://a", "http://b", "http://c"], "page": ["1", "2", "3"]})
    got = select_thresholds(kept)
    assert [(g["item"], g["value"]) for g in got] == [("boro_rice.heat.anthesis_tmax", 35.0),
                                                       ("wheat.heat.anthesis_tmax", 31.0)]


def test_real_reference_thresholds_are_all_cited():
    got = load_thresholds()
    assert len(got) == 14  # 7 heat (tmax), 2 hot-night (tmin), 5 cold (tmin); counted from crop_thresholds.csv
    kinds = pd.Series([g["kind"] for g in got]).value_counts().to_dict()
    assert kinds == {"heat_days": 7, "night_heat_days": 2, "cold_nights": 5}
    for g in got:
        assert g["source_url"].startswith("http") and "fabricated" not in g["source_title"].lower()

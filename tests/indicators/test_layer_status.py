"""W2 reads the W1b status table: statuses and reasons come from the table, never from hard-coded text.
Expected values are worked out by hand."""
import numpy as np
import pandas as pd
import pytest

from indicators import layer_status as LS
from sat_layers.status import COLUMNS, load_status


def table(**overrides):
    """A small status table with the three layers W2 asks about, plus SMAP-64."""
    rows = {
        "modis_ndvi_anomaly": ("partial", "9 years of 24 present"),
        "grace_fo": ("partial", "regional only (about 300 km): 48 cells for 64 districts, up to 3 share one cell"),
        "ecostress_et": ("not assessed", "units unresolved (ETdaily unit not confirmed)"),
        "smap_64": ("not assessed", "AppEEARS job did not finish; five live districts use the existing point files"),
    }
    rows.update(overrides)
    df = pd.DataFrame([[k, "d", "c", 1, s, r, "https://x", "u", "res"] for k, (s, r) in rows.items()], columns=COLUMNS)
    return df


def modis(years, district="a", n=20):
    """n composites per year; ndvi value is irrelevant here."""
    rows = [[(pd.Timestamp(y, 1, 1) + pd.Timedelta(days=16 * k)).strftime("%Y-%m-%d"), district, 0.5, 1.0, 0.3, 1.0]
            for y in years for k in range(n)]
    return pd.DataFrame(rows, columns=["date", "district", "ndvi", "coverage", "evi", "coverage_evi"])


def grace(years, per_year, district="a"):
    """One GRACE value per year at 1 July (inside kharif2 and not in kharif1 or rabi): value = per_year*(year-2002)."""
    idx = pd.to_datetime([f"{y}-07-01" for y in years])
    return pd.Series([per_year * (y - 2002) for y in years], index=idx, dtype=float)


def one(rows, indicator, season="kharif2"):
    r = [x for x in rows if x["indicator"] == indicator and x["season"] == season]
    assert len(r) == 1
    return r[0]


# (a) fewer than 6 years present gives "not assessed", and n is read from the data
def test_modis_with_fewer_than_six_years_is_not_assessed():
    r = one(LS.layer_rows("a", ["kharif2"], table(), modis([2015, 2016, 2017]), None), "modis_ndvi_z")
    assert r["status"].startswith("not assessed (needs >=5 other years; only 3 years present")
    assert r["n"] == 3 and np.isnan(r["value"])


def test_modis_years_are_read_from_the_data_not_hard_coded():
    for years in ([2001, 2002, 2003, 2004, 2005, 2006], list(range(2010, 2018))):  # 6 and 8 years
        r = one(LS.layer_rows("a", ["kharif2"], table(), modis(years), None), "modis_ndvi_z")
        assert r["status"].startswith("partial") and r["n"] == len(years)
        assert "9 years of 24 present" in r["status"]  # the table's own reason is carried
        assert np.isnan(r["value"])  # season-level z is not computed here


def test_modis_district_missing_from_the_file_is_not_assessed_with_the_table_reason():
    r = one(LS.layer_rows("zzz", ["kharif2"], table(), modis(range(2015, 2025), district="a"), None), "modis_ndvi_z")
    assert r["status"].startswith("not assessed") and "9 years of 24 present" in r["status"]


# (b) a missing dataset gives "not assessed" with the reason taken from the table
def test_missing_datasets_give_not_assessed_with_the_table_reason():
    rows = LS.layer_rows("a", ["kharif2"], table(), None, None)
    for ind, reason in [("modis_ndvi_z", "9 years of 24 present"), ("grace_fo_trend", "regional only (about 300 km)")]:
        r = one(rows, ind)
        assert r["status"].startswith("not assessed") and reason in r["status"]
    eco = one(rows, "ecostress_et_comparison")
    assert eco["status"].startswith("not assessed (units unresolved") and "ETdaily unit not confirmed" in eco["status"]


def test_a_changed_table_changes_the_output():
    t = table(ecostress_et=("not assessed", "reason written for this test only"))
    assert "reason written for this test only" in one(LS.layer_rows("a", ["kharif2"], t, None, None), "ecostress_et_comparison")["status"]


def test_table_without_a_layer_is_an_error_not_a_default():
    t = table().query("key != 'ecostress_et'")
    with pytest.raises(KeyError):
        LS.layer_rows("a", ["kharif2"], t, None, None)


def test_smap_reason_for_districts_without_a_file_comes_from_the_table():
    assert LS.smap_missing_status(table()) == ("not assessed (AppEEARS job did not finish; five live districts "
                                               "use the existing point files)")


# (c) never a 0 for a not-assessed value
def test_not_assessed_values_are_nan_never_zero():
    rows = LS.layer_rows("a", ["kharif1", "kharif2", "rabi"], table(), modis([2015, 2016]), None)
    assert len(rows) == 9
    for r in rows:
        assert r["status"].startswith("not assessed") and np.isnan(r["value"]) and r["value"] != 0
        assert r["dataset"] and r["source_url"].startswith("https://")  # still cited


# GRACE-FO: season values, trend by hand, regional label carried
def test_grace_season_values_are_means_of_dates_inside_the_window():
    s = pd.Series([1.0, 3.0, 10.0], index=pd.to_datetime(["2010-07-01", "2010-09-01", "2010-12-01"]))
    assert LS.season_values(s, "kharif2", [2010, 2011]) == pytest.approx([2.0, np.nan], nan_ok=True)  # Jul 1-Oct 31 -> (1+3)/2
    assert LS.season_values(s, "rabi", [2010])[0] == 10.0  # rabi starts 1 Nov: Dec 1 is inside


def test_grace_trend_slope_is_exact_and_labelled_regional():
    years = list(range(2002, 2014))  # 12 years, value = 2.0 * (year - 2002): slope 2 cm per year
    r = one(LS.layer_rows("a", ["kharif2"], table(), None, grace(years, 2.0), years=range(2001, 2025)), "grace_fo_trend")
    assert r["value"] == pytest.approx(2.0) and r["n"] == 12 and r["unit"] == "cm per year"
    assert r["status"].startswith("partial (regional, about 300 km, shared cells)")
    assert "up to 3 share one cell" in r["status"]  # the table reason is carried


def test_grace_with_too_few_seasons_gives_nan_with_the_reason():
    years = list(range(2002, 2008))  # 6 seasons, the trend test needs 8
    r = one(LS.layer_rows("a", ["kharif2"], table(), None, grace(years, 2.0), years=range(2001, 2025)), "grace_fo_trend")
    assert np.isnan(r["value"]) and r["n"] == 6 and "need 8" in r["status"]
    assert "regional" in r["status"]


# (d) a stale table, or a stale shipped indicator file, fails a test
def test_shipped_status_table_is_not_stale():
    from sat_layers import intake
    pd.testing.assert_frame_equal(load_status().reset_index(drop=True),
                                  intake.build_status(intake.run_checks()).reset_index(drop=True), check_dtype=False)


def test_shipped_indicator_file_matches_the_status_table():
    import os
    from sat_layers import loaders as L
    path = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed", "indicators_districts_2001_2024.csv")
    d = pd.read_csv(path, keep_default_na=False)
    st = load_status()
    reason = lambda k: st.set_index("key").loc[k, "reason"]
    n_years = len(L.modis_years_present(L.load_modis().data))
    eco = d[d.indicator == "ecostress_et_comparison"]
    assert len(eco) > 0 and (eco.status == f"not assessed ({reason('ecostress_et')})").all()
    mod = d[d.indicator == "modis_ndvi_z"]
    assert (pd.to_numeric(mod.n) == n_years).all() and mod.status.str.contains(reason("modis_ndvi_anomaly"), regex=False).all()
    gr = d[d.indicator == "grace_fo_trend"]
    assert gr.status.str.contains("regional, about 300 km, shared cells", regex=False).all()
    assert gr.status.str.contains(reason("grace_fo"), regex=False).all()
    assert (d[d.status.str.startswith("not assessed")].value.astype(str) == "").all()  # empty (NaN), never 0

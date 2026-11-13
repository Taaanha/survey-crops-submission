"""The committed W1 outputs: 64 rows per season, every column documented, files small."""

import os

import pandas as pd

from district_grid.features import COLUMN_INFO

PROC = os.path.join(os.path.dirname(__file__), "..", "..", "data", "processed")


def _read(name, **kw):
    return pd.read_csv(os.path.join(PROC, name), **kw)


def test_64_districts_in_every_season_and_year():
    t = _read("district_season_features.csv")
    counts = t.groupby(["season_year", "season"])["district"].nunique()
    assert len(counts) == 24 * 3 and (counts == 64).all()
    assert t["season_year"].min() == 2001 and t["season_year"].max() == 2024


def test_every_value_column_has_dataset_unit_and_source_url():
    t = _read("district_season_features.csv")
    info = _read("district_season_features_columns.csv").set_index("column")
    assert set(info.index) == set(COLUMN_INFO)
    for col in COLUMN_INFO:
        assert col in t.columns
        row = info.loc[col]
        assert row["dataset"] and row["unit"] and str(row["source_url"]).startswith("https://")
        assert row["first_season_year"] <= row["last_season_year"]


def test_totals_are_never_filled_in_over_missing_days():
    t = _read("district_season_features.csv")
    partial = t[t["imerg_days_obs"] < t["n_days"]]
    assert partial["rain_total_mm"].isna().all()


def test_rain_is_physical_and_wettest_district_is_in_the_northeast():
    t = _read("district_season_features.csv")
    assert (t["rain_total_mm"] >= 0).all() and (t["rain_max_1d_mm"] < 1000).all()
    k2 = t[t["season"] == "kharif2"].groupby("district")["rain_total_mm"].mean()
    assert k2.idxmax() in {"sylhet", "sunamganj", "moulvibazar", "habiganj", "cox's_bazar", "coxs_bazar",
                           "bandarban", "rangamati", "chattogram", "khagrachari"}


def test_committed_data_files_stay_small():
    for name in os.listdir(PROC):
        if name.startswith(("district_season", "imerg_polygon", "power64")):
            assert os.path.getsize(os.path.join(PROC, name)) < 5_000_000, name

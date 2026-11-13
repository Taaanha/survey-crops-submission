"""
scripts/build_district_features.py

Builds, for all 64 districts, from the downloaded files:
  data/processed/imerg_polygon_daily_wide.csv.gz   IMERG district polygon mean, one column per district
  data/processed/imerg_polygon_coverage.csv        share of each district's weight that has IMERG data
  data/processed/district_season_features.csv      district x season_year x season feature table
  data/processed/district_season_features_columns.csv   dataset, unit, source URL, years covered per column

Needs data/raw/imerg_bgd/ (scripts/fetch_imerg_bgd.py) and data/raw/power64/ (scripts/fetch_power64.py).
Also checks the grid against the existing Giovanni point files of the five live districts.

Run from the repo root:  python scripts/build_district_features.py
"""
import glob
import os
import sys

import _proj  # noqa: F401  PROJ guard: keep first
import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from district_grid.boundaries import LIVE_DISTRICTS, load_districts  # noqa: E402
from district_grid.features import COLUMN_INFO, season_features  # noqa: E402
from district_grid.grid import cell_weights, district_mean, imerg_axes  # noqa: E402

RAW_IMERG = os.path.join(ROOT, "data", "raw", "imerg_bgd")
RAW_POWER = os.path.join(ROOT, "data", "raw", "power64")
PROC = os.path.join(ROOT, "data", "processed")
YEARS = list(range(2001, 2025))  # primary window; IMERG Final Run ends 2025-09-30


def load_imerg_stack():
    dates, fields = [], []
    for p in sorted(glob.glob(os.path.join(RAW_IMERG, "imerg_*.npz"))):
        with np.load(p) as z:
            dates += list(z["dates"])
            fields.append(z["precip_mm"])
    return pd.to_datetime(dates), np.concatenate(fields)


def main():
    lons, lats = imerg_axes()
    districts = load_districts()
    dates, stack = load_imerg_stack()
    print(f"IMERG stack: {len(dates)} days {dates.min().date()} .. {dates.max().date()}, shape {stack.shape[1:]}")
    daily, cover = {}, {}
    weights = {}
    for d in districts:
        w = cell_weights(d["geometry"], lons, lats)
        weights[d["slug"]] = w
        mean, cov = district_mean(stack, w)
        daily[d["slug"]] = pd.Series(mean, index=dates)
        cover[d["slug"]] = float(np.nanmin(cov)), float(np.nanmean(cov)), float(w.sum())
    wide = pd.DataFrame(daily).round(2)
    wide.index.name = "date"
    wide.to_csv(os.path.join(PROC, "imerg_polygon_daily_wide.csv.gz"))
    pd.DataFrame(cover, index=["min_coverage", "mean_coverage", "weight_sum_cells"]).T.round(4) \
        .rename_axis("district").to_csv(os.path.join(PROC, "imerg_polygon_coverage.csv"))

    # check 1: the cell under each live district's old Giovanni point must match our subset exactly
    pts = pd.read_csv(os.path.join(PROC, "imerg_cells.csv"), index_col="district")
    for slug in LIVE_DISTRICTS:
        old = pd.read_csv(os.path.join(PROC, f"imerg_{slug}_daily.csv"), index_col="date", parse_dates=True)["rainfall_mm"]
        i = int(np.argmin(abs(lats - pts.loc[slug, "cell_lat"])))
        j = int(np.argmin(abs(lons - pts.loc[slug, "cell_lon"])))
        mine = pd.Series(stack[:, i, j], index=dates)
        common = old.index.intersection(mine.index)
        diff = (old.loc[common] - mine.loc[common]).abs().max()
        poly = wide[slug].loc[common]
        print(f"  check {slug}: cell vs Giovanni max |diff| = {diff:.3f} mm over {len(common)} days; "
              f"polygon-mean total / point-cell total = {poly.sum() / old.loc[common].sum():.3f}")

    # POWER echoes the query point, so shared native cells are found from identical temperature series
    sig, series = {}, {}
    for d in districts:
        pw = pd.read_csv(os.path.join(RAW_POWER, f"power_{d['slug']}_daily.csv"), index_col="date", parse_dates=True)
        series[d["slug"]] = pw
        sig[d["slug"]] = hash(tuple(pw["temp_max_c"].round(3).fillna(-99).tolist()))
    gid = {s: i for i, s in enumerate(dict.fromkeys(sig.values()))}
    groups = pd.DataFrame({"district": list(sig), "power_cell_group": [gid[v] for v in sig.values()]})
    groups["districts_in_group"] = groups.groupby("power_cell_group")["district"].transform("count")
    groups.to_csv(os.path.join(PROC, "power64_cell_groups.csv"), index=False)
    print(f"POWER: {groups['power_cell_group'].nunique()} distinct temperature series for {len(groups)} districts")

    rows = []
    for d in districts:
        slug = d["slug"]
        power = series[slug]
        f = season_features(wide[slug], power, YEARS)
        f.insert(0, "district", slug)
        rows.append(f)
    table = pd.concat(rows, ignore_index=True)
    table.round(3).to_csv(os.path.join(PROC, "district_season_features.csv"), index=False)

    info = []
    for col, meta in COLUMN_INFO.items():
        ok = table[table[col].notna()]
        info.append({"column": col, **meta, "first_season_year": int(ok["season_year"].min()),
                     "last_season_year": int(ok["season_year"].max()),
                     "district_seasons_with_value": len(ok), "district_seasons_total": len(table)})
    pd.DataFrame(info).to_csv(os.path.join(PROC, "district_season_features_columns.csv"), index=False)
    print(f"feature table: {len(table)} rows ({table['district'].nunique()} districts x "
          f"{table['season'].nunique()} seasons x {len(YEARS)} years)")
    print(table[list(COLUMN_INFO)].isna().sum().to_string())


if __name__ == "__main__":
    main()

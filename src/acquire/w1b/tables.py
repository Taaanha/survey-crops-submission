"""From rasters on the common 0.1 degree grid to small district tables (the files that go in git).

Weights come from district_grid.grid.cell_weights, so a district value is the area-weighted mean
of the cells that have data, with `coverage` = share of the district's weight that had data."""

import numpy as np
import pandas as pd

from district_grid.boundaries import load_districts
from district_grid.grid import cell_weights, district_mean, imerg_axes
from district_grid.regrid import nearest_cell
from w1b.convert import wrap_longitude
from w1b.products import PRODUCTS


def all_district_weights(districts=None):
    """(slugs, weights[n_district, lat, lon]) on the IMERG grid for the 64 districts."""
    districts = districts or load_districts()
    lons, lats = imerg_axes()
    slugs = [d["slug"] for d in districts]
    return slugs, np.stack([cell_weights(d["geometry"], lons, lats) for d in districts])


def stack_to_district_table(stack, dates, slugs, weights, column):
    """[time, lat, lon] raster on the 0.1 degree grid -> long table (date, district, <column>, coverage).
    Rows where no cell had data keep NaN with coverage 0 so a gap is visible, not silently dropped."""
    stack = np.asarray(stack, dtype=float)
    if stack.ndim == 2:
        stack = stack[None]
    if stack.shape[0] != len(dates):
        raise ValueError("number of dates does not match the first axis of the stack")
    frames = []
    for slug, w in zip(slugs, weights):
        mean, cov = district_mean(stack, w)
        frames.append(pd.DataFrame({"date": list(dates), "district": slug,
                                    column: np.atleast_1d(mean), "coverage": np.atleast_1d(cov)}))
    return pd.concat(frames, ignore_index=True)


def scene_stats(stack, dates, column, **meta):
    """[time, y, x] scenes -> one row per scene: mean of the valid pixels (`column`) and clear_share,
    the fraction of pixels with a value. Scenes with no valid pixel keep NaN and clear_share 0.
    `meta` (for example tile='feni', product='eco_et') is added to every row."""
    a = np.asarray(stack, dtype=float)
    if a.ndim == 2:
        a = a[None]
    if a.shape[0] != len(dates):
        raise ValueError("number of dates does not match the first axis of the stack")
    valid = np.isfinite(a)
    n = valid.sum(axis=(1, 2))
    total = np.where(valid, a, 0.0).sum(axis=(1, 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n > 0, total / np.where(n > 0, n, 1), np.nan)
    df = pd.DataFrame({"date": list(dates), **meta, column: mean,
                       "clear_share": n / (a.shape[1] * a.shape[2])})
    return df


def to_wide(table, column):
    """Long table (date, district, <column>, ...) -> one row per date, one column per district.
    Wide files are about a fifth the size, which keeps daily SMAP under the 5 MB git limit."""
    return table.pivot(index="date", columns="district", values=column).sort_index()


def coverage_summary(table):
    """Per district: share of dates with any data, and the lowest coverage seen (0..1)."""
    g = table.groupby("district")
    return pd.DataFrame({"share_of_dates_with_data": g["coverage"].apply(lambda s: float((s > 0).mean())),
                         "min_coverage": g["coverage"].min()}).reset_index()


def static_to_district_table(grids, slugs, weights):
    """{column: [lat, lon] grid} -> one row per district (district, <columns>..., coverage_<column>)."""
    rows = []
    for k, slug in enumerate(slugs):
        row = {"district": slug}
        for col, grid in grids.items():
            m, c = district_mean(grid, weights[k])
            row[col], row[f"coverage_{col}"] = m, c
        rows.append(row)
    return pd.DataFrame(rows)


def grace_table(lwe, times, lons, lats, points, uncertainty=None):
    """GRACE-FO mascon grid -> long table for the district points (nearest cell, 'regional').

    lwe: [time, lat, lon] equivalent water thickness in cm; lons may be 0..360;
    points: {slug: (lon, lat)}. Each row names the mascon cell used (cell_lon, cell_lat), so
    districts sharing one cell are visible; `regional` is always True (about 300 km effective)."""
    lons = wrap_longitude(lons)
    frames = []
    for slug, (lon, lat) in points.items():
        val, cl, ca = nearest_cell(lwe, lons, lats, lon, lat)
        data = {"date": list(times), "district": slug, "lwe_thickness_cm": val,
                "cell_lon": cl, "cell_lat": ca, "regional": True}
        if uncertainty is not None:
            data["uncertainty_cm"] = nearest_cell(uncertainty, lons, lats, lon, lat)[0]
        frames.append(pd.DataFrame(data))
    return pd.concat(frames, ignore_index=True)


def column_rows(spec):
    """Rows for a *_columns.csv like district_season_features_columns.csv.
    spec: [(column, product key, years first, years last, note)]."""
    rows = []
    for column, key, first, last, note in spec:
        p = PRODUCTS[key]
        rows.append({"column": column, "dataset": f"{p['product']} ({p['native']})",
                     "source_url": p["source_url"], "unit": p["unit"], "note": note,
                     "first_year": first, "last_year": last})
    return pd.DataFrame(rows)

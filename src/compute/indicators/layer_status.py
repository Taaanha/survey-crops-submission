"""W2 rows for the satellite layers whose availability comes from the W1b status table.

Status and reason are read from docs/w1b_data_status.csv (sat_layers.status), never typed here, so
when a layer is downloaded or its status changes, W2 follows the table. A value is NaN (never 0)
whenever the indicator is not assessed.

- modis_ndvi_z      : status from `modis_ndvi_anomaly`; n = years present, read from the MODIS data.
                      Fewer than 6 years present (or no data for the district) = not assessed.
                      The season-level z-score value is not computed here (per-composite z-scores
                      are sat_layers.loaders.ndvi_anomaly), so the value stays NaN.
- grace_fo_trend    : status from `grace_fo`, always labelled regional (about 300 km, shared cells);
                      the trend uses the same Theil-Sen + Kendall + Pettitt check as the other trends.
- ecostress_et_comparison : status from `ecostress_et` (units unresolved: not assessed).
"""

import numpy as np
import pandas as pd

from district_grid.features import season_range
from indicators.explain import ECOSTRESS, GRACE, MODIS
from indicators.trend import trend_status
from sat_layers.loaders import MIN_YEARS_FOR_ANOMALY, modis_years_present
from sat_layers.status import load_status

REGIONAL_LABEL = "regional, about 300 km, shared cells"
MIN_OTHER_YEARS = 5


def row(district, year, season, indicator, value, unit, ds, n, status, threshold=np.nan, threshold_source=""):
    """One row of the long indicator table (same columns as indicators.build.COLUMNS)."""
    return {"district": district, "season_year": year, "season": season, "indicator": indicator,
            "value": value, "unit": unit, "threshold": threshold, "threshold_source": threshold_source,
            "dataset": ds["dataset"], "source_url": ds["source_url"], "n": n, "status": status}


def lookup(table, key):
    """(status, reason) of one layer in the status table; a missing key raises KeyError (no default)."""
    idx = table.set_index("key")
    if key not in idx.index:
        raise KeyError(f"{key!r} is not in the status table; known: {sorted(idx.index)}")
    return idx.loc[key, "status"], idx.loc[key, "reason"]


def smap_missing_status(table):
    """Status text for a district without a SMAP point file: the 64-district SMAP reason from the table."""
    st, reason = lookup(table, "smap_64")
    return f"not assessed ({reason})" if st == "not assessed" else f"not assessed (no SMAP file for this district; {st}: {reason})"


def season_values(series, season, years):
    """Mean of the series values dated inside each year's season window; NaN where none fall inside."""
    out = []
    for y in years:
        start, end = season_range(season, y)
        w = series[(series.index >= start) & (series.index <= end)]
        out.append(float(w.mean()) if len(w) else float("nan"))
    return out


def modis_row(district, season, table, modis_df):
    st, reason = lookup(table, "modis_ndvi_anomaly")
    d = None if modis_df is None else modis_df[modis_df.district == district]
    if d is None or len(d) == 0:
        status, n = f"not assessed (no MODIS data for this district; layer status: {st}: {reason})", np.nan
    else:
        n = len(modis_years_present(d))
        if st == "not assessed":
            status = f"not assessed ({reason})"
        elif n < MIN_YEARS_FOR_ANOMALY:
            status = f"not assessed (needs >={MIN_OTHER_YEARS} other years; only {n} years present)"
        else:
            status = (f"{st}: {reason}; season-level z-score not computed here "
                      "(per-composite z-scores: sat_layers.loaders.ndvi_anomaly)")
    return row(district, np.nan, season, "modis_ndvi_z", np.nan, "z-score", MODIS, n, status)


def grace_row(district, season, table, grace, years):
    st, reason = lookup(table, "grace_fo")
    if grace is None or len(grace) == 0:
        status, n, value = f"not assessed (no GRACE-FO series for this district; layer status: {st}: {reason})", np.nan, np.nan
    elif st == "not assessed":
        status, n, value = f"not assessed ({reason})", np.nan, np.nan
    else:
        r = trend_status(list(years), season_values(grace, season, years), unit="cm")
        n = r["n"]
        value = r["slope"] if r["status"] == "trend" else np.nan  # a broken record is not shown as a trend
        status = f"{st} ({REGIONAL_LABEL}): {r['text']}; {reason}"
    return row(district, np.nan, season, "grace_fo_trend", value, "cm per year", GRACE, n, status)


def ecostress_row(district, season, table):
    st, reason = lookup(table, "ecostress_et")
    status = (f"not assessed ({reason})" if st == "not assessed" else
              f"not assessed (comparison with FAO-56 ET0 is not built; layer status: {st}: {reason})")
    return row(district, np.nan, season, "ecostress_et_comparison", np.nan, "mm", ECOSTRESS, np.nan, status)


def layer_rows(district, seasons, table=None, modis_df=None, grace=None, years=range(2001, 2025)):
    """The three satellite-layer rows per season for one district.

    table: status table (DataFrame); read from docs/w1b_data_status.csv when None.
    modis_df: the joined MODIS table (sat_layers.loaders.load_modis().data) or None.
    grace: this district's GRACE-FO values as a Series indexed by date, or None."""
    table = load_status() if table is None else table
    years = list(years)
    rows = []
    for season in seasons:
        rows.append(modis_row(district, season, table, modis_df))
        rows.append(grace_row(district, season, table, grace, years))
        rows.append(ecostress_row(district, season, table))
    return rows

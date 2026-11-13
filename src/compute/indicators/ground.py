"""
src/compute/indicators/ground.py

Satellite vs ground check (W2, item 8): monthly mean rain from a daily satellite series compared
with published station normals. Pure functions; the caveats (normal period unknown, station is a
point, IMERG is a 0.1 degree cell) are written into the report by scripts/build_indicators.py.
"""

import calendar

import numpy as np
import pandas as pd


def monthly_mean_rain(daily, years):
    """Mean monthly rain total (mm) over `years`, only counting months with every day observed.

    Returns a DataFrame indexed by month 1..12 with mean_mm and n_years (years that counted)."""
    rows = []
    for month in range(1, 13):
        totals = []
        for year in years:
            idx = pd.date_range(pd.Timestamp(year, month, 1), periods=calendar.monthrange(year, month)[1], freq="D")
            w = daily.reindex(idx)
            if not w.isna().any():
                totals.append(float(w.sum()))
        rows.append({"month": month, "mean_mm": float(np.mean(totals)) if totals else float("nan"),
                     "n_years": len(totals)})
    return pd.DataFrame(rows).set_index("month")


def bias_table(satellite, normal):
    """Bias of monthly means against a station normal.

    satellite: DataFrame from monthly_mean_rain; normal: Series by month 1..12 (mm).
    Returns rows 1..12 and 'annual' (sum of the 12 months) with satellite_mm, normal_mm,
    bias_mm (satellite minus normal), bias_pct (of the normal; NaN if the normal is 0), n_years."""
    sat = satellite["mean_mm"].astype(float)
    nor = normal.astype(float)
    t = pd.DataFrame({"satellite_mm": sat, "normal_mm": nor, "n_years": satellite["n_years"]}, index=range(1, 13))
    annual = pd.DataFrame({"satellite_mm": [sat.sum(skipna=False)], "normal_mm": [nor.sum(skipna=False)],
                           "n_years": [satellite["n_years"].min()]}, index=["annual"])
    t = pd.concat([t, annual])
    t["bias_mm"] = t["satellite_mm"] - t["normal_mm"]
    t["bias_pct"] = np.where(t["normal_mm"] > 0, t["bias_mm"] / t["normal_mm"].where(t["normal_mm"] > 0) * 100, np.nan)
    return t[["satellite_mm", "normal_mm", "bias_mm", "bias_pct", "n_years"]]


# ---------------- temperature: POWER vs BMD normals (W2 follow-up, item 3) ----------------

def monthly_mean_temp(daily, years):
    """Mean of the daily values (degC) of each calendar month, averaged over `years`; only months
    with every day observed count. Returns month 1..12 with mean_c and n_years."""
    rows = []
    for month in range(1, 13):
        means = []
        for year in years:
            idx = pd.date_range(pd.Timestamp(year, month, 1), periods=calendar.monthrange(year, month)[1], freq="D")
            w = daily.reindex(idx)
            if not w.isna().any():
                means.append(float(w.mean()))
        rows.append({"month": month, "mean_c": float(np.mean(means)) if means else float("nan"),
                     "n_years": len(means)})
    return pd.DataFrame(rows).set_index("month")


def temperature_normals(table, station, kind):
    """Monthly normals (degC) of one station from reference rows named '<station>.normal_<kind>_<mon>'
    (kind 'tmax' or 'tmin'). Months without a row are NaN, never 0."""
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    values = dict(zip(table["item"], table["value"]))
    return pd.Series([float(values[f"{station}.normal_{kind}_{m}"]) if f"{station}.normal_{kind}_{m}" in values
                      else float("nan") for m in months], index=range(1, 13))


def temp_bias_table(model, normal):
    """Bias of monthly mean temperature against a station normal, in degC (model minus normal).

    model: DataFrame from monthly_mean_temp; normal: Series by month 1..12. The 'annual' row is the
    mean of the 12 months (not a sum); it is NaN if any month is missing."""
    mod = model["mean_c"].astype(float)
    nor = normal.astype(float)
    t = pd.DataFrame({"model_c": mod, "normal_c": nor, "n_years": model["n_years"]}, index=range(1, 13))
    annual = pd.DataFrame({"model_c": [mod.mean(skipna=False)], "normal_c": [nor.mean(skipna=False)],
                           "n_years": [model["n_years"].min()]}, index=["annual"])
    t = pd.concat([t, annual])
    t["bias_c"] = t["model_c"] - t["normal_c"]
    return t[["model_c", "normal_c", "bias_c", "n_years"]]

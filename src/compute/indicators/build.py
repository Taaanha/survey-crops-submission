"""
src/compute/indicators/build.py

Builds the long indicator table for ONE district from its daily weather (W2).
Any district slug works: the caller passes the data, nothing here knows a district list.
Rows carry the dataset and a source link; a value is NaN (never 0) when a window is incomplete or
the indicator is not assessed, and `status` says why.
"""

import numpy as np
import pandas as pd

from district_grid.features import SEASONS
from indicators import core
from indicators.explain import ET0, IMERG, POWER, SMAP, ETCCDI_URL
from indicators.heavy_rain import CELL_MEAN_LABEL, heavy_rain_days
from indicators.layer_status import layer_rows, row as _row, smap_missing_status
from sat_layers.status import load_status

SEASON_NAMES = tuple(SEASONS)
COLUMNS = ["district", "season_year", "season", "indicator", "value", "unit", "threshold",
           "threshold_source", "dataset", "source_url", "n", "status"]
TEMP_COLUMN = {"tmax": "temp_max_c", "tmin": "temp_min_c"}
HEAVY_DS = {"dataset": f"{IMERG['dataset']} ({CELL_MEAN_LABEL})", "source_url": IMERG["source_url"]}
NO_HEAVY = "not assessed (no cited heavy-rain row in data/reference; see PROJECT_STATE open questions)"
INCOMPLETE = "incomplete (not every day of the season window was observed)"


def _threshold_source(t):
    return f"{t['item']}; {t['source_url']}"  # full citation: indicators_thresholds.csv


def _smap_by_year(smap, season):
    """Season-mean root-zone moisture for every year whose window is complete in the SMAP file."""
    if smap is None or len(smap) == 0:
        return {}
    out = {}
    for year in range(smap.index.min().year - 1, smap.index.max().year + 1):
        w = core.window_series(smap, season, year)
        out[year] = float(w.mean()) if w is not None else np.nan
    return out


def _smap_row(district, year, season, by_year, smap, missing_status):
    if smap is None:
        return _row(district, year, season, "smap_rootzone_z", np.nan, "z-score", SMAP, np.nan, missing_status)
    z, n_other = core.leave_one_out_z(by_year, year)
    start, end = core.season_range(season, year)
    if start < smap.index.min() or end > smap.index.max():
        status = f"no SMAP data for this window (the file covers {smap.index.min().date()} to {smap.index.max().date()})"
    elif n_other < core.MIN_OTHER_YEARS:
        status = f"not enough other years (n={n_other}, need {core.MIN_OTHER_YEARS})"
    elif np.isnan(by_year.get(year, np.nan)):
        status = "incomplete (SMAP window not fully observed this year)"
    elif np.isnan(z):
        status = "no spread among the other years"
    else:
        status = "ok"
    return _row(district, year, season, "smap_rootzone_z", z, "z-score", SMAP, n_other, status)


def build_district_table(district, weather, et0, smap, thresholds, years, seasons=SEASON_NAMES, layers=None,
                         heavy_rain=None):
    """Long table of indicators for one district.

    weather: daily DataFrame with rainfall_mm (IMERG), temp_max_c, temp_min_c (POWER).
    et0: daily FAO-56 ET0 Series (mm). smap: daily root-zone moisture Series or None.
    thresholds: list of dicts from thresholds.load_thresholds().
    layers: optional dict with "status" (the W1b status table; read from docs/w1b_data_status.csv when
    missing), "modis" (joined MODIS table) and "grace" (this district's GRACE-FO Series). The MODIS,
    GRACE-FO, ECOSTRESS and no-SMAP-file rows take their status and reason from the status table.
    heavy_rain: dict from heavy_rain.load_heavy_rain_threshold(), or None (then not assessed)."""
    layers = layers or {}
    status_table = layers.get("status")
    if status_table is None:
        status_table = load_status()
    smap_missing = smap_missing_status(status_table)
    rows = []
    for season in seasons:
        by_year = _smap_by_year(smap, season)
        for year in years:
            rain = core.window_series(weather["rainfall_mm"], season, year)
            n_rain = core.window_days_observed(weather["rainfall_mm"], season, year)[0]
            ev = core.window_series(et0, season, year)
            n_et = core.window_days_observed(et0, season, year)[0]

            for t in thresholds:
                series = weather[TEMP_COLUMN[t["variable"]]]
                w = core.window_series(series, season, year)
                kw = dict(threshold=t["value"], threshold_source=_threshold_source(t))
                ind = f"{t['kind']}__{t['item']}"
                if w is None:
                    n_obs = core.window_days_observed(series, season, year)[0]
                    rows.append(_row(district, year, season, ind, np.nan, "days", POWER, n_obs, INCOMPLETE, **kw))
                else:
                    rows.append(_row(district, year, season, ind, core.count_beyond(w, t["value"], t["op"]),
                                     "days", POWER, len(w), "ok", **kw))

            etc = f"ETCCDI standard index, not a Bangladesh-specific limit: {ETCCDI_URL}"
            rain_specs = [("extreme_rain_days_r20mm", "days", core.r20mm_days, core.R20MM_LIMIT_MM),
                          ("rx1day", "mm", core.rx1day, np.nan),
                          ("cdd", "days", core.cdd, core.CDD_WET_DAY_MM)]
            for name, unit, fn, limit in rain_specs:
                val, status = (np.nan, INCOMPLETE) if rain is None else (fn(rain), "ok")
                rows.append(_row(district, year, season, name, val, unit, IMERG, n_rain, status,
                                 threshold=limit, threshold_source=etc))

            if heavy_rain is None:
                rows.append(_row(district, year, season, "heavy_rain_days_bmd", np.nan, "days", HEAVY_DS, n_rain, NO_HEAVY))
            else:
                src = (f"{heavy_rain['item']}; {heavy_rain['source_url']}; page {heavy_rain['page'] or 'not recorded'}; "
                       f"{heavy_rain['via']}")
                val, status = (np.nan, INCOMPLETE) if rain is None else (heavy_rain_days(rain, heavy_rain["value"]), "ok")
                rows.append(_row(district, year, season, "heavy_rain_days_bmd", val, "days", HEAVY_DS, n_rain, status,
                                 threshold=heavy_rain["value"], threshold_source=src))

            et_val = np.nan if ev is None else core.season_total(ev)
            rows.append(_row(district, year, season, "et0_season_total", et_val, "mm", ET0, n_et,
                             "ok" if ev is not None else INCOMPLETE))
            if rain is None or ev is None:
                bal, status = np.nan, INCOMPLETE
            else:
                bal, status = core.climatic_balance(rain, ev), "ok"
            rows.append(_row(district, year, season, "rain_minus_et0", bal, "mm",
                             {"dataset": f"{IMERG['dataset']} minus {ET0['dataset']}", "source_url": IMERG["source_url"]},
                             min(n_rain, n_et), status))
            rows.append(_smap_row(district, year, season, by_year, smap, smap_missing))

        rows.extend(layer_rows(district, [season], status_table, layers.get("modis"), layers.get("grace"), years))

    df = pd.DataFrame(rows, columns=COLUMNS)
    df["season_year"] = df["season_year"].astype("Int64")
    return df

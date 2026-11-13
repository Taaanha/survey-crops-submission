"""
src/compute/indicators/core.py

Small, pure indicator functions for one season window of daily values (W2).
No AI, no file reading. Season windows are OUR analysis windows (district_grid.features), not a
cited crop calendar. A value is only computed when every day of the window was observed.
"""

import numpy as np
import pandas as pd

from district_grid.features import season_range  # noqa: F401  (re-exported for build.py)
from risk_calendar import count_days
from agroclimate import dry_spell_length

R20MM_LIMIT_MM = 20.0   # ETCCDI R20mm: days with rain >= 20 mm
CDD_WET_DAY_MM = 1.0    # ETCCDI CDD: a dry day has rain < 1 mm
MIN_OTHER_YEARS = 5     # SMAP z-score needs at least this many other years


def window_series(series, season, year):
    """The daily values of one season window, or None unless every day is present and not NaN."""
    a, b = season_range(season, year)
    w = series.reindex(pd.date_range(a, b, freq="D"))
    return None if w.isna().any() else w


def window_days_observed(series, season, year):
    """(days observed, days in the window)."""
    a, b = season_range(season, year)
    w = series.reindex(pd.date_range(a, b, freq="D"))
    return int(w.notna().sum()), len(w)


def count_beyond(values, limit, op):
    """Days strictly above (op '>') or below (op '<') a limit."""
    return count_days(values, limit, op)


def r20mm_days(rain):
    """ETCCDI R20mm: number of days with rain >= 20 mm."""
    return int(np.sum(np.asarray(rain, dtype=float) >= R20MM_LIMIT_MM))


def rx1day(rain):
    """Largest one-day rain (mm) in the window."""
    return float(np.max(np.asarray(rain, dtype=float)))


def cdd(rain):
    """ETCCDI CDD: longest run of consecutive days with rain < 1 mm."""
    return dry_spell_length(pd.Series(np.asarray(rain, dtype=float)), CDD_WET_DAY_MM)


def season_total(values):
    return float(np.sum(np.asarray(values, dtype=float)))


def climatic_balance(rain, et0):
    """Season rain minus season reference evaporation (mm). NOT the Kc-weighted crop balance."""
    return season_total(rain) - season_total(et0)


def leave_one_out_z(by_year, year, min_other=MIN_OTHER_YEARS):
    """z-score of one year's value against the OTHER years (their mean and sample sd, ddof=1).

    Returns (z, n_other). z is NaN if the year is missing, fewer than `min_other` other years
    have a value, or the other years have no spread."""
    s = pd.Series(by_year, dtype=float)
    others = s.drop(index=year, errors="ignore").dropna()
    n_other = int(len(others))
    if n_other < min_other or year not in s.index or np.isnan(s.loc[year]):
        return float("nan"), n_other
    sd = float(others.std(ddof=1))
    if sd == 0.0 or np.isnan(sd):
        return float("nan"), n_other
    return float((s.loc[year] - others.mean()) / sd), n_other

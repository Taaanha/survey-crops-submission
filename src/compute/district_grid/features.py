"""District x season feature table (Layer 1, deterministic, no AI).

Three analysis windows per season year Y (our aggregation choice, NOT a cited crop calendar; W2
computes the crop-stage indicators with cited limits):
    kharif1  1 Mar - 30 Jun of Y     kharif2  1 Jul - 31 Oct of Y     rabi  1 Nov of Y - end Feb of Y+1

Rain comes from NASA GPM IMERG V07 Final Run (district polygon means); temperature, humidity,
wind and solar radiation come from NASA POWER at the district query point. A season total is
only given when every day was observed; otherwise it is NaN and the observed-day counts say why.
"""

import numpy as np
import pandas as pd

SEASONS = {"kharif1": (3, 1, 6, 30), "kharif2": (7, 1, 10, 31), "rabi": (11, 1, 2, None)}

IMERG = {"dataset": "NASA GPM IMERG V07 Final Run daily (GPM_3IMERGDF.07), district polygon mean",
         "source_url": "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary"}
POWER = {"dataset": "NASA POWER daily, AG community, district query point",
         "source_url": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"}

# every feature column: where it comes from, its unit, and a link (no source, no column)
COLUMN_INFO = {
    "rain_total_mm": {**IMERG, "unit": "mm per season", "note": "NaN unless every day observed"},
    "rain_max_1d_mm": {**IMERG, "unit": "mm per day", "note": "largest observed day"},
    "tmean_c": {**POWER, "unit": "degC", "note": "mean of daily T2M"},
    "tmax_mean_c": {**POWER, "unit": "degC", "note": "mean of daily T2M_MAX"},
    "tmin_mean_c": {**POWER, "unit": "degC", "note": "mean of daily T2M_MIN"},
    "rh_mean_pct": {**POWER, "unit": "percent", "note": "mean of daily RH2M"},
    "wind_mean_ms": {**POWER, "unit": "m/s", "note": "mean of daily WS2M at 2 m"},
    "solar_sum_mj_m2": {**POWER, "unit": "MJ/m2 per season", "note": "sum of daily ALLSKY_SFC_SW_DWN"},
}


def season_range(season, year):
    """(first day, last day) of a season for season year `year`."""
    m1, d1, m2, d2 = SEASONS[season]
    start = pd.Timestamp(year, m1, d1)
    if m2 < m1:  # rabi crosses into the next year
        end = pd.Timestamp(year + 1, m2, 1) + pd.offsets.MonthEnd(0)
    else:
        end = pd.Timestamp(year, m2, d2)
    return start, end


def _nan_row():
    return {c: np.nan for c in COLUMN_INFO}


def season_features(rain, power, years, seasons=("kharif1", "kharif2", "rabi")):
    """One row per (year, season) for ONE district.

    rain: Series of daily mm indexed by date; power: DataFrame with the POWER columns of
    src/acquire/power_points.py. Seasons with no data stay as NaN rows."""
    rows = []
    for year in years:
        for season in seasons:
            a, b = season_range(season, year)
            n_days = (b - a).days + 1
            r = rain.loc[a:b].dropna() if len(rain) else rain
            p = power.loc[a:b] if len(power) else power
            row = {"season_year": year, "season": season, "start": a.date().isoformat(),
                   "end": b.date().isoformat(), "n_days": n_days, **_nan_row(),
                   "imerg_days_obs": int(len(r)),
                   "power_days_obs": int(p["temp_mean_c"].notna().sum()) if "temp_mean_c" in p else 0}
            if len(r):
                row["rain_max_1d_mm"] = float(r.max())
                if len(r) == n_days:
                    row["rain_total_mm"] = float(r.sum())
            if row["power_days_obs"]:
                row.update(tmean_c=p["temp_mean_c"].mean(), tmax_mean_c=p["temp_max_c"].mean(),
                           tmin_mean_c=p["temp_min_c"].mean(), rh_mean_pct=p["rh_pct"].mean(),
                           wind_mean_ms=p["wind_speed_ms"].mean())
                if p["solar_rad_mj_m2"].notna().sum() == n_days:
                    row["solar_sum_mj_m2"] = float(p["solar_rad_mj_m2"].sum())
            rows.append(row)
    return pd.DataFrame(rows)

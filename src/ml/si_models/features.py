"""Season feature table for the W3 models: one row per (district, season_year, season).

Inputs: the W2 indicator table (data/processed/indicators_*.csv), IMERG rain and POWER temperature
(through compute.weather.load_weather), SMAP z-scores from the W2 table, MODIS NDVI season means.
Not inputs (by rule): ECOSTRESS (units unresolved), GRACE-FO (regional), HLS (two tiles, no Jun-Aug).
A value that was not observed stays NaN, never 0. Any district slug works: the caller passes the data.
"""

import numpy as np
import pandas as pd

from district_grid.features import season_range
from indicators.core import window_series
from indicators.explain import ET0 as ET0_DS, IMERG, MODIS as MODIS_DS, POWER, SMAP as SMAP_DS

KEY = ["district", "season_year", "season"]
# every feature column: dataset and link (no source, no column)
PROVENANCE = {
    "rain_total_mm": IMERG, "rx1day": IMERG, "extreme_rain_days_r20mm": IMERG, "cdd": IMERG,
    "tmax_mean_c": POWER, "tmin_mean_c": POWER, "rain_minus_et0": ET0_DS,
    "smap_rootzone_z": SMAP_DS, "ndvi_season_mean": MODIS_DS,
}
W2_INDICATORS = ["rx1day", "extreme_rain_days_r20mm", "cdd", "rain_minus_et0", "smap_rootzone_z"]
MIN_NDVI_COMPOSITES = 4   # a season mean needs at least this many of its ~7 composites: our choice


def season_weather_features(weather, years, seasons):
    """rain_total_mm, tmax_mean_c, tmin_mean_c per (season_year, season); NaN unless every day of
    the window was observed."""
    rows = []
    for y in years:
        for s in seasons:
            rain = window_series(weather["rainfall_mm"], s, y)
            tmax = window_series(weather["temp_max_c"], s, y)
            tmin = window_series(weather["temp_min_c"], s, y)
            rows.append({"season_year": int(y), "season": s,
                         "rain_total_mm": float(rain.sum()) if rain is not None else np.nan,
                         "tmax_mean_c": float(tmax.mean()) if tmax is not None else np.nan,
                         "tmin_mean_c": float(tmin.mean()) if tmin is not None else np.nan})
    return pd.DataFrame(rows)


def wide_indicators(long_table, indicators=W2_INDICATORS):
    """The W2 long table turned into one column per indicator (rows without a season year dropped)."""
    t = long_table[long_table.indicator.isin(indicators) & long_table.season_year.notna()]
    wide = t.pivot_table(index=KEY, columns="indicator", values="value", aggfunc="first", dropna=False)
    wide = wide.reindex(columns=indicators).reset_index()
    wide["season_year"] = wide.season_year.astype(int)
    wide.columns.name = None
    return wide


def ndvi_season_mean(modis_df, district, years, seasons, min_composites=MIN_NDVI_COMPOSITES):
    """Mean NDVI of the composites dated inside each season window; NaN with fewer than
    `min_composites` valid composites. Returns columns season_year, season, ndvi_season_mean, ndvi_n."""
    d = modis_df[modis_df.district == district]
    s = pd.Series(d.ndvi.values, index=pd.to_datetime(d.date.values)).dropna()
    rows = []
    for y in years:
        for season in seasons:
            a, b = season_range(season, y)
            w = s[(s.index >= a) & (s.index <= b)]
            rows.append({"season_year": int(y), "season": season, "ndvi_n": int(len(w)),
                         "ndvi_season_mean": float(w.mean()) if len(w) >= min_composites else np.nan})
    return pd.DataFrame(rows)


def build_features(district, weather, indicators_long, years, seasons, modis_df=None):
    """All feature columns for one district. modis_df None (or MODIS not assessed) leaves NDVI NaN."""
    f = season_weather_features(weather, years, seasons)
    f.insert(0, "district", district)
    f = f.merge(wide_indicators(indicators_long[indicators_long.district == district]), on=KEY, how="left")
    if modis_df is not None:
        f = f.merge(ndvi_season_mean(modis_df, district, years, seasons), on=["season_year", "season"], how="left")
    else:
        f["ndvi_season_mean"], f["ndvi_n"] = np.nan, 0
    return f


def standardize_loyo(features, cols, test_year):
    """z-scores of `cols` per (district, season), using the mean and sample sd of the years OTHER than
    `test_year` only. The test year's own values never enter the mean or sd (no leak).
    A group with fewer than 2 train values, or no spread, gives NaN."""
    out = features[KEY].copy()
    train = features[features.season_year != test_year]
    g = train.groupby(["district", "season"])[cols]
    mean, sd, n = g.mean(), g.std(ddof=1), g.count()
    idx = pd.MultiIndex.from_frame(features[["district", "season"]])
    for c in cols:
        m = mean[c].reindex(idx).values
        s = sd[c].reindex(idx).values
        k = n[c].reindex(idx).values
        s = np.where((k >= 2) & (s > 0), s, np.nan)
        out[c] = (features[c].values - m) / s
    return out

"""
scripts/build_indicators.py

W2: builds the indicator tables for the districts you name (default: the five live ones).
Any district slug that has data/processed/power_<slug>_daily.csv and imerg_<slug>_daily.csv works.

Writes (data/processed/):
  indicators_districts_2001_2024.csv   long table: district, season_year, season, indicator, value, unit,
                                       threshold, threshold_source, dataset, source_url, n, status
  indicators_trends_2001_2024.csv      Theil-Sen/Kendall + Pettitt-on-residuals per district, season, variable
  indicators_thresholds.csv            the cited limits used: crop_thresholds.csv, Tmin rows of r04_cold_injury.csv
                                       and the heavy-rain row (full source title, URL, page)
  indicators_explainers.csv            one plain-English line per indicator family

Run from the repo root:  python scripts/build_indicators.py [slug slug ...]
"""
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from district_grid.features import SEASONS  # noqa: E402
from indicators import core  # noqa: E402
from indicators.build import build_district_table  # noqa: E402
from indicators.explain import ET0, EXPLAINERS, GRACE, IMERG, POWER  # noqa: E402
from indicators.layer_status import lookup, season_values  # noqa: E402
from indicators.cold_limits import load_cold_limits  # noqa: E402
from indicators.heavy_rain import load_heavy_rain_threshold  # noqa: E402
from indicators.thresholds import load_thresholds  # noqa: E402
from indicators.trend import trend_status  # noqa: E402
from sat_layers import loaders as layer_loaders  # noqa: E402
from sat_layers.status import load_status  # noqa: E402
from water_balance import weather_table  # noqa: E402
from weather import load_weather  # noqa: E402

LIVE = ["cumilla", "feni", "brahmanbaria", "noakhali", "sylhet"]
YEARS = list(range(2001, 2025))
OUT = os.path.join(ROOT, "data", "processed")
TREND_VARIABLES = [("rain_total", "mm", IMERG), ("tmean", "degC", POWER), ("et0_total", "mm", ET0)]
REGIONAL_NOTE = "regional (about 300 km), shared cells: not district groundwater"


def load_smap(slug):
    path = os.path.join(OUT, f"smap_{slug}_2015_2026.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path, index_col="date", parse_dates=True)["sm_rootzone"]


def load_grace_series(slug, grace):
    """This district's GRACE-FO values (cm) as a Series indexed by date, or None if it is not in the file."""
    g = grace[grace.district == slug]
    return None if g.empty else pd.Series(g.lwe_thickness_cm.values, index=pd.to_datetime(g.date.values))


def trend_rows(slug, weather, et0, grace_series=None, status_table=None):
    rows = []
    for season in SEASONS:
        for var, unit, ds in TREND_VARIABLES:
            vals = []
            for y in YEARS:
                if var == "rain_total":
                    w = core.window_series(weather["rainfall_mm"], season, y)
                    vals.append(np.nan if w is None else w.sum())
                elif var == "tmean":
                    w = core.window_series(weather["temp_mean_c"], season, y)
                    vals.append(np.nan if w is None else w.mean())
                else:
                    w = core.window_series(et0, season, y)
                    vals.append(np.nan if w is None else w.sum())
            r = trend_status(YEARS, vals, unit=unit)
            rows.append({"district": slug, "season": season, "variable": var, "unit": unit, "note": "",
                         "dataset": ds["dataset"], "source_url": ds["source_url"], "n": r["n"],
                         "slope_per_year": r["slope"], "tau": r["tau"], "kendall_p": r["kendall_p"],
                         "pettitt_p": r["pettitt_p"], "step_year": r["step_year"], "status": r["status"],
                         "alpha": r["alpha"], "text": r["text"]})
        if grace_series is not None and status_table is not None:  # GRACE-FO: assessed only as regional
            st, reason = lookup(status_table, "grace_fo")
            if st != "not assessed":
                r = trend_status(YEARS, season_values(grace_series, season, YEARS), unit="cm")
                rows.append({"district": slug, "season": season, "variable": "grace_lwe", "unit": "cm", "note": REGIONAL_NOTE,
                             "dataset": GRACE["dataset"], "source_url": GRACE["source_url"], "n": r["n"],
                             "slope_per_year": r["slope"], "tau": r["tau"], "kendall_p": r["kendall_p"],
                             "pettitt_p": r["pettitt_p"], "step_year": r["step_year"], "status": r["status"],
                             "alpha": r["alpha"], "text": f"{r['text']} ({REGIONAL_NOTE}; layer status {st}: {reason})"})
    return rows


def main(slugs):
    meta = pd.read_csv(os.path.join(OUT, "district_metadata.csv")).set_index("district")
    thresholds = load_thresholds()
    cold, cold_rejected = load_cold_limits()
    have = {(t["item"], t["value"]) for t in thresholds}
    thresholds += [dict(c) for c in cold if (c["item"], c["value"]) not in have]
    heavy = load_heavy_rain_threshold()
    if heavy is None:
        print("heavy-rain days: NOT ASSESSED (no cited row)")
    else:
        print(f"heavy-rain limit {heavy['value']} {heavy['unit']}: {heavy['source_title']} | {heavy['source_url']} | "
              f"page {heavy['page'] or 'not recorded'} | via {heavy['via'][:30]}")
    print(f"cold limits from r04 used: {[c['item'] for c in cold]}")
    reasons = pd.Series([r["reason"].split(" (")[0] for r in cold_rejected]).value_counts().to_dict()
    print(f"r04 rows not used: {len(cold_rejected)} {reasons}")
    for r in cold_rejected:
        if "tmin" in r["item"]:
            print(f"   Tmin-named row not used: {r['item']} = {r['value'][:40]!r}: {r['reason']}")
    status_table = load_status()
    modis = layer_loaders.load_modis().data
    grace = layer_loaders.load_grace().data
    print(f"{len(thresholds)} cited temperature limits")
    tables, trends = [], []
    for slug in slugs:
        weather = load_weather(slug)  # IMERG rain + POWER temperature, never POWER rain
        et0 = weather_table(weather, meta.loc[slug, "latitude"], meta.loc[slug, "elevation_m"])["et0_mm"]
        smap = load_smap(slug)
        gs = load_grace_series(slug, grace)
        t = build_district_table(slug, weather, et0, smap, thresholds, YEARS,
                                 layers={"status": status_table, "modis": modis, "grace": gs}, heavy_rain=heavy)
        tables.append(t)
        trends.extend(trend_rows(slug, weather, et0, gs, status_table))
        ok = (t.status == "ok").sum()
        print(f"{slug}: {len(t)} rows, {ok} ok, SMAP file: {smap is not None}")
    long = pd.concat(tables, ignore_index=True)
    long.to_csv(os.path.join(OUT, "indicators_districts_2001_2024.csv"), index=False, float_format="%.4f")
    pd.DataFrame(trends).to_csv(os.path.join(OUT, "indicators_trends_2001_2024.csv"), index=False, float_format="%.5g")
    pd.DataFrame([{"indicator": k, "one_liner": v} for k, v in EXPLAINERS.items()]).to_csv(
        os.path.join(OUT, "indicators_explainers.csv"), index=False)
    if heavy is not None:
        thresholds.append({"item": heavy["item"], "kind": "heavy_rain_days_bmd", "variable": "rain", "op": ">=",
                           "value": heavy["value"], "unit": "mm per day", "crop": "", "stage": "",
                           "source_title": heavy["source_title"], "source_url": heavy["source_url"], "page": heavy["page"]})
    pd.DataFrame(thresholds)[["item", "kind", "variable", "op", "value", "unit", "crop", "stage",
                              "source_title", "source_url", "page"]].to_csv(
        os.path.join(OUT, "indicators_thresholds.csv"), index=False)
    print(long.groupby("status").size().sort_values(ascending=False).head(12).to_string())
    for f in ("indicators_districts_2001_2024.csv", "indicators_trends_2001_2024.csv", "indicators_explainers.csv"):
        print(f, round(os.path.getsize(os.path.join(OUT, f)) / 1e6, 2), "MB")


if __name__ == "__main__":
    main(sys.argv[1:] or LIVE)

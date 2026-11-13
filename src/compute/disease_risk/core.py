"""
src/compute/disease_risk/core.py

Counts, over the past seasons (2001-2024), in how many seasons the weather was favourable
for a crop disease inside the crop growing window. It never says a disease occurred.

Only rules whose every number has a source row in data/reference/disease_rules_draft.csv
(kept by the strict loader: real source link, parseable value) are used. Today that is
potato late blight (Hyre 1954). A crop with no usable rule is "not assessed", never 0.
No AI, no network.
"""

import datetime as dt

import numpy as np
import pandas as pd

SEASONS = tuple(range(2001, 2025))
DISEASES = {
    "potato": {"disease": "late_blight", "prefix": "potato.disease.late_blight_rule",
               "parts": {"tmean_below_c": "tmax", "rain10_mm_at_least": "rain_mm",
                         "tmin_unfavourable_below_c": "unfavorable_tmin"},
               "label": {"en": "Potato late blight", "bn": "আলুর লেট ব্লাইট"}},
    "wheat": {"disease": "blast", "prefix": "wheat.disease.blast_rule",
              "parts": {"tmax_above_c": "tmax", "rain_above_mm": "rain_mm"},
              "label": {"en": "Wheat blast", "bn": "গমের ব্লাস্ট"}},
    "lentil": {"disease": "stemphylium_blight", "prefix": "lentil.disease.stemphylium_rule",
               "parts": {"tmin_c": "tmin", "tmax_c": "tmax", "wetness_hours": "wetness_hours"},
               "label": {"en": "Lentil Stemphylium blight", "bn": "মসুরের স্টেমফিলিয়াম ব্লাইট"}},
}
# Rules we can compute. Wheat blast and lentil rows are listed above only so we can say
# why they are not assessed; they are not computed.
COMPUTABLE = {"potato"}
MISSING_INPUT = {"lentil": "leaf-wetness hours (not in our weather data)"}
# Hyre's note in the cited row: onset 7-14 days after 10 consecutive favourable days.
MIN_RUN_DAYS = 10
RAIN_WINDOW_DAYS = 10
TEMP_WINDOW_DAYS = 5


def build_rule(kept, crop):
    """The rule for `crop` from kept reference rows (a DataFrame with item, value, unit,
    source_title, source_url, page), or None if any number is missing."""
    spec = DISEASES.get(crop)
    if spec is None or crop not in COMPUTABLE:
        return None
    values, cites = {}, []
    for key, part in spec["parts"].items():
        row = kept[kept["item"] == f"{spec['prefix']}.{part}"]
        if row.empty:
            return None
        r = row.iloc[0]
        values[key] = float(r["value"])
        cites.append({"item": r["item"], "source_title": r["source_title"],
                      "source_url": r["source_url"], "page": r.get("page")})
    return {"crop": crop, "disease": spec["disease"], "label": spec["label"], "values": values,
            "min_run_days": MIN_RUN_DAYS, "citations": cites}


def favourable_days(weather, rule):
    """Boolean Series by date: 5-day mean temperature below the limit AND 10-day rain total at
    or above the limit (both trailing, ending that day) AND that day's minimum temperature
    not below the 'unfavourable' limit. A day with a missing input is False."""
    v = rule["values"]
    tmean = weather["temp_mean_c"].rolling(TEMP_WINDOW_DAYS, min_periods=TEMP_WINDOW_DAYS).mean()
    rain = weather["rainfall_mm"].rolling(RAIN_WINDOW_DAYS, min_periods=RAIN_WINDOW_DAYS).sum()
    ok = (tmean < v["tmean_below_c"]) & (rain >= v["rain10_mm_at_least"]) \
        & (weather["temp_min_c"] >= v["tmin_unfavourable_below_c"])
    return ok.fillna(False).astype(bool)


def longest_run(flags):
    """Longest run of consecutive True values."""
    best = cur = 0
    for f in np.asarray(flags, dtype=bool):
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def season_window(year, start_md, end_md, extra_days):
    """(first day, last day) of the growing window for the season that starts in `year`:
    the cited sowing-window start, to the sowing-window end plus `extra_days`."""
    start = dt.date(year, *start_md)
    end = dt.date(year, *end_md) + dt.timedelta(days=int(extra_days))
    return start, end


def count_seasons(weather, rule, start_md, end_md, extra_days, seasons=SEASONS):
    """Per-season and total counts. A season whose window is not fully covered by the weather
    table is left out of n_seasons (listed in skipped_seasons), never counted as 0."""
    flags = favourable_days(weather, rule)
    cols = ["temp_mean_c", "rainfall_mm", "temp_min_c"]
    rows, skipped = [], []
    for y in seasons:
        a, b = season_window(y, start_md, end_md, extra_days)
        idx = pd.date_range(a, b)
        # the 10-day rain total needs the days before the window too
        need = pd.date_range(a - dt.timedelta(days=RAIN_WINDOW_DAYS - 1), b)
        if len(weather.index.intersection(need)) < len(need) or weather.loc[need, cols].isna().any().any():
            skipped.append(y)
            continue
        f = flags.loc[idx]
        run = longest_run(f.values)
        rows.append({"season": y, "favourable_days": int(f.sum()), "longest_run_days": int(run),
                     "favourable": bool(run >= rule["min_run_days"])})
    return {"n_seasons": len(rows), "seasons_favourable": sum(r["favourable"] for r in rows),
            "seasons_any_favourable_day": sum(r["favourable_days"] > 0 for r in rows),
            "skipped_seasons": skipped, "per_season": rows,
            "window": {"start": list(start_md), "end": list(end_md), "extra_days": int(extra_days),
                       "first_season": rows[0]["season"] if rows else None,
                       "last_season": rows[-1]["season"] if rows else None}}


def not_assessed(crop, kept, skipped=None):
    """Why a crop has no disease count: a reason string, never a zero."""
    spec = DISEASES.get(crop)
    if spec is not None and crop in MISSING_INPUT:
        return f"the rule needs {MISSING_INPUT[crop]}"
    if spec is not None:
        listed = {f"{spec['prefix']}.{p}" for p in spec["parts"].values()}
        if skipped is not None and len(skipped) and listed & set(skipped["item"]):
            return "the rule has no usable source link in data/reference"
        if not listed <= set(kept["item"]):
            return "the rule is incomplete in data/reference"
    return "no sourced disease rule for this crop"


def assess_crop(crop, weather, kept, skipped, start_md=None, end_md=None, extra_days=None):
    """One result per crop: {"status": "assessed", ...counts, "rule"} or
    {"status": "not_assessed", "crop", "reason"}. start_md / end_md / extra_days describe the
    growing window (from the crop spec); missing -> not assessed."""
    rule = build_rule(kept, crop)
    if rule is None:
        return {"status": "not_assessed", "crop": crop, "reason": not_assessed(crop, kept, skipped)}
    if start_md is None or end_md is None or extra_days is None:
        return {"status": "not_assessed", "crop": crop,
                "reason": "the crop growing window is not sourced"}
    out = count_seasons(weather, rule, start_md, end_md, extra_days)
    if out["n_seasons"] == 0:
        return {"status": "not_assessed", "crop": crop, "reason": "no season has complete weather"}
    return {"status": "assessed", "crop": crop, "disease": rule["disease"], "label": rule["label"],
            "rule": {"values": rule["values"], "min_run_days": rule["min_run_days"]},
            "citations": rule["citations"], **out}

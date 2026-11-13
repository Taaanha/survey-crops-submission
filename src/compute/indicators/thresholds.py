"""
src/compute/indicators/thresholds.py

Picks the cited temperature limits out of data/reference/crop_thresholds.csv (W2, item 1).
load_reference() already drops placeholder / uncited rows, so every row returned here has a
source. Nothing is invented: a limit that is not in the file is not counted.

item name -> indicator family
  *.heat.*tmax*      -> heat_days        days Tmax above the limit
  *tmin_night*       -> night_heat_days  days Tmin above the limit (hot nights)
  *.cold.*tmin*      -> cold_nights      days Tmin below the limit
  *_days, *tmean*    -> skipped (not a daily-temperature limit we count)
"""

import pandas as pd

from reference import load_reference

FILE = "crop_thresholds.csv"


def classify_item(item):
    """(kind, variable, op) for a threshold item name, or None if we do not count it."""
    s = item.lower()
    if s.endswith("_days") or "tmean" in s:
        return None
    if "tmin_night" in s:
        return ("night_heat_days", "tmin", ">")
    if ".heat." in s and "tmax" in s:
        return ("heat_days", "tmax", ">")
    if ".cold." in s and "tmin" in s:
        return ("cold_nights", "tmin", "<")
    return None


def select_thresholds(kept):
    """List of threshold dicts from a table of kept reference rows; repeated item+value dropped."""
    out, seen = [], set()
    for _, r in kept.iterrows():
        c = classify_item(str(r["item"]))
        if c is None or pd.isna(r["value"]):
            continue
        key = (r["item"], float(r["value"]))
        if key in seen:
            continue
        seen.add(key)
        parts = str(r["item"]).split(".")
        out.append({"item": r["item"], "kind": c[0], "variable": c[1], "op": c[2],
                    "value": float(r["value"]), "unit": r["unit"],
                    "crop": parts[0], "stage": parts[2] if len(parts) > 2 else "",
                    "source_title": r["source_title"], "source_url": r["source_url"], "page": r["page"]})
    return out


def load_thresholds():
    """All cited heat / hot-night / cold limits from the reference file."""
    return select_thresholds(load_reference(files=[FILE]).kept)

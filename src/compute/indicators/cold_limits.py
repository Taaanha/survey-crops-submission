"""
src/compute/indicators/cold_limits.py

Tmin-only cold limits from data/reference/r04_cold_injury.csv (W2 follow-up, item 2).

A row is used only if ALL hold, checked in this order (otherwise it is listed in `rejected`
with the first reason, so the research teammate can fix it at the source):
  1. it is a Tmin limit: the item ends in _tmin (or has _tmin_) or the unit says "Tmin". Daily-mean
     (*tmean*), duration (*_days or unit days), lethal-minimum (tlmin) and "type not stated" rows are not Tmin.
  2. not a placeholder; the item name is a lower-case dotted name; the source link is http(s)
  3. the value is one plain number or "below N" (ranges, notes like "(SUSPECT)" and text are not)
Repeated item+value rows are counted once. Each limit is for the crop stage the source describes;
the season window it is counted in is ours. The reference file is never edited here.
"""

import os
import re

import pandas as pd

from reference import ITEM_RE, NUMBER_RE, REFERENCE_DIR

FILE = "r04_cold_injury.csv"
BELOW_RE = re.compile(r"^below\s+(-?\d+(?:\.\d+)?)$", re.IGNORECASE)
TMIN_ITEM_RE = re.compile(r"(^|_)tmin($|_)")


def parse_limit(value):
    """A plain number, or 'below N', as a float; anything else (ranges, notes) is None."""
    raw = str(value).strip()
    if NUMBER_RE.match(raw):
        return float(raw)
    m = BELOW_RE.match(raw)
    return float(m.group(1)) if m else None


def is_tmin_row(item, unit):
    """True if the row is a minimum-temperature limit (see the module text)."""
    name = item.lower().split(".")[-1]
    if name.endswith("_days") or "tmean" in name or unit.strip().lower() == "days":
        return False
    return bool(TMIN_ITEM_RE.search(name)) or unit.strip().lower().endswith("tmin")


def select_cold_limits(table):
    """(limits, rejected) from a table of raw string rows (columns item, value, unit, source_title,
    source_url, page, notes). limits: dicts shaped like thresholds.select_thresholds."""
    limits, rejected, seen = [], [], set()
    for _, r in table.iterrows():
        item, unit = str(r["item"]).strip(), str(r["unit"])

        def reject(reason):
            rejected.append({"item": item, "value": str(r["value"]), "reason": reason})

        if not is_tmin_row(item, unit):
            reject("not a Tmin limit (daily mean, duration, lethal minimum or temperature type not stated)")
        elif str(r["source_title"]).strip().upper().startswith("PLACEHOLDER"):
            reject("placeholder: source_title starts with PLACEHOLDER")
        elif not ITEM_RE.match(item):
            reject("item name is malformed")
        elif not re.match(r"^https?://", str(r["source_url"]).strip(), re.IGNORECASE):
            reject("source_url is missing or not http(s)")
        elif parse_limit(r["value"]) is None:
            reject("value is not one plain number or 'below N'")
        else:
            value = parse_limit(r["value"])
            if (item, value) in seen:
                continue
            seen.add((item, value))
            parts = item.split(".")
            limits.append({"item": item, "kind": "cold_nights", "variable": "tmin", "op": "<", "value": value,
                           "unit": "degC", "crop": parts[0], "stage": parts[2] if len(parts) > 2 else "",
                           "source_title": str(r["source_title"]).strip(), "source_url": str(r["source_url"]).strip(),
                           "page": str(r["page"]).strip(), "file": FILE})
    return limits, rejected


def load_cold_limits(reference_dir=REFERENCE_DIR):
    """(limits, rejected) from r04_cold_injury.csv."""
    table = pd.read_csv(os.path.join(reference_dir, FILE), dtype=str, keep_default_na=False)
    return select_cold_limits(table)

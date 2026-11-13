"""
src/compute/indicators/heavy_rain.py

Heavy-rain days (W2 follow-up, item 1): days with rain at or above a heavy-rain limit that comes
only from a cited reference row, counted next to the ETCCDI R20mm index (core.r20mm_days).

Which row: `climate.rain.heavy_day_mm` if a file has it (read by the strict loader); otherwise the
BMD scale row `bmd_heavy_rain_min` in data/reference/r03_heavy_rain.csv. The strict loader skips
that row because its item name has no dots, so it is read from the file directly and the
returned dict says so (`via`). Its source is a news report quoting the BMD scale and the row has
no page: both are passed through, never filled in. No usable row means None (not assessed).

The IMERG number is a mean over a 0.1 degree cell, not rainfall at a point, so a point limit is
reached less often: CELL_MEAN_LABEL goes into the dataset text of every row.
"""

import os
import re

import numpy as np
import pandas as pd

from reference import NUMBER_RE, REFERENCE_DIR, load_reference

FILE = "r03_heavy_rain.csv"
STRICT_ITEM = "climate.rain.heavy_day_mm"
RAW_ITEM = "bmd_heavy_rain_min"
CELL_MEAN_LABEL = "cell-mean, not point rainfall; may undercount point extremes"


def heavy_rain_days(rain, limit):
    """Days with rain at or above `limit` (mm); the limit's own value counts."""
    return int(np.sum(np.asarray(rain, dtype=float) >= float(limit)))


def _from_strict_loader(reference_dir):
    ref = load_reference(reference_dir=reference_dir)
    rows = ref.rows(STRICT_ITEM)
    rows = rows[rows["kind"] == "number"]
    if rows.empty:
        return None
    r = rows.iloc[0]
    return {"item": r["item"], "value": float(r["value"]), "unit": r["unit"],
            "source_title": r["source_title"], "source_url": r["source_url"], "page": r["page"],
            "notes": r["notes"], "via": "strict loader"}


def _from_raw_row(reference_dir):
    path = os.path.join(reference_dir, FILE)
    if not os.path.exists(path):
        return None
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    hit = table[table["item"].str.strip() == RAW_ITEM]
    if hit.empty:
        return None
    r = hit.iloc[0]
    if not re.match(r"^https?://", r["source_url"].strip(), re.IGNORECASE) or not NUMBER_RE.match(r["value"].strip()):
        return None
    return {"item": RAW_ITEM, "value": float(r["value"]), "unit": r["unit"], "source_title": r["source_title"],
            "source_url": r["source_url"].strip(), "page": r["page"].strip(), "notes": r["notes"],
            "via": "raw row (the strict loader rejects this item name: no dots; rename to "
                   f"{STRICT_ITEM} in data/reference)"}


def load_heavy_rain_threshold(reference_dir=REFERENCE_DIR):
    """The cited heavy-rain limit as a dict (item, value, unit, source_title, source_url, page,
    notes, via), or None when no cited row exists (the indicator is then not assessed)."""
    return _from_strict_loader(reference_dir) or _from_raw_row(reference_dir)

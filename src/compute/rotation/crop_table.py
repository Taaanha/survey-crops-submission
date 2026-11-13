"""
src/compute/rotation/crop_table.py

Loader for data/reference/crops.csv, the wide crop table (one row per crop and
variety class). Every filled cell points at the existing reference row it was
copied from (the *_src columns, "file:item"); every blank cell is listed in the
row's needs_source column. Nothing here fills a gap with a guess.

The old strict loader (reference.py) skips this file with reason "header"
because its columns are not item/value; the rotation engine reads it here.
"""

import os

import pandas as pd

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CROP_TABLE_PATH = os.path.join(REPO_ROOT, "data", "reference", "crops.csv")


def load_crop_table(path=CROP_TABLE_PATH):
    """crops.csv as strings ("" where blank, never NaN)."""
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")


def parse_mmdd(text):
    """"0615" -> (6, 15)."""
    padded = str(text).strip().zfill(4)
    return int(padded[:2]), int(padded[2:])


def parse_number(text, end="high"):
    """A number or an "A-B" range from a cell; for a range `end` picks "low" or "high"."""
    text = str(text).strip()
    if "-" in text[1:]:
        low, high = text.split("-", 1)
        return float(low) if end == "low" else float(high)
    return float(text)


def pick_row(table, crop, variety_class=None):
    """The crop's row: the named variety class, else the first row with a duration
    and a sowing window, else the first row. None if the crop is not in the table."""
    rows = table[table["crop"] == crop]
    if rows.empty:
        return None
    if variety_class:
        named = rows[rows["variety_class"] == variety_class]
        if not named.empty:
            return named.iloc[0]
    usable = rows[(rows["duration_days"] != "") & (rows["sow_start_mmdd"] != "")]
    return (usable if not usable.empty else rows).iloc[0]


def is_usable(row):
    """A row can be chained only with a cited duration and sowing window."""
    return bool(row["duration_days"] and row["sow_start_mmdd"] and row["sow_end_mmdd"])


def missing_reason(row):
    """Why a row cannot be used in a rotation (its needs_source text), or ""."""
    if is_usable(row):
        return ""
    gaps = [c for c in ("duration_days", "sow_start_mmdd", "sow_end_mmdd") if not row[c]]
    return "no cited " + ", ".join(gaps) + " (NEEDS SOURCE in data/reference/crops.csv)"

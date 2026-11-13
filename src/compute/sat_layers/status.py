"""The data status table: which W1b layer is assessed, partial or not assessed, and why.

The table is docs/w1b_data_status.csv, written by scripts/build_w1b_intake.py from checks on the
files in data/processed/. W2 and later code reads it here instead of hard-coding "not downloaded":

    status_of("modis_ndvi_anomaly")  ->  ("partial", "9 years of 24 present ...")
    require_assessed("ecostress_et") ->  raises NotAssessed with the reason

A layer that is not assessed must be shown as "not assessed" with its reason, never as 0."""

import os

import pandas as pd

STATUS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs", "w1b_data_status.csv")
STATUSES = ("assessed", "partial", "not assessed")
COLUMNS = ["key", "dataset", "coverage", "districts", "status", "reason", "source_url", "units", "resolution"]


class NotAssessed(Exception):
    """Raised by require_assessed for a layer that is not assessed."""


def load_status(path=STATUS_PATH):
    """The status table as a DataFrame (one row per layer)."""
    df = pd.read_csv(path, keep_default_na=False)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"status table is missing columns {missing}")
    bad = sorted(set(df.status) - set(STATUSES))
    if bad:
        raise ValueError(f"unknown status values {bad}; allowed {STATUSES}")
    return df


def status_of(key, path=STATUS_PATH):
    """(status, reason) for one layer key; unknown keys raise KeyError (no silent default)."""
    df = load_status(path).set_index("key")
    if key not in df.index:
        raise KeyError(f"{key!r} is not in the status table; known: {sorted(df.index)}")
    return df.loc[key, "status"], df.loc[key, "reason"]


def require_assessed(key, allow_partial=True, path=STATUS_PATH):
    """Returns the status if the layer may be used; raises NotAssessed (with the reason) otherwise.
    allow_partial=False also refuses layers marked 'partial'."""
    status, reason = status_of(key, path)
    if status == "not assessed" or (status == "partial" and not allow_partial):
        raise NotAssessed(f"{key}: {status} ({reason})")
    return status

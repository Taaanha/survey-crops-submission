"""Problem 1: seasonal transitions (green-up and browning dates) from MODIS 16-day NDVI.

Method A (fixed threshold): the date NDVI crosses a cited threshold, by straight-line interpolation
between two composites. The only cited value is the global bare-soil limit 0.1 (r02_ndvi_bare_soil.csv,
marked provisional); the Bangladesh row is a GAP. A district-mean series that never reaches the
threshold gives no date: "not assessed", never a made-up threshold.
Method B (smoothing + change point): Savitzky-Golay smoothing (5 composites, order 2: our choice),
then the Pettitt change point (compute.change_point) of the smoothed values inside a search window;
the date is the midpoint between the two composites around the break.

Neither method fits parameters on other years, so there is nothing to leak between years.
Composites are 16 days apart: an error below about 16 days cannot be resolved.
The satellite sees the canopy turning green, which comes after transplanting; no cited lag is
available, so none is subtracted. District means mix rice with every other land cover.
"""

import re

import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

from change_point import pettitt_test

COMPOSITE_DAYS = 16
MIN_FOUND_SHARE = 0.5   # a method is assessed for a transition only if it gives a date in at least half the district-years: our choice
SG_WINDOW, SG_ORDER = 5, 2     # our choice
# Search windows (our choice, deliberately wide: about four months). (name, direction, start (month, day,
# year offset), end (month, day, year offset)) for cycle year Y.
SEARCH = {
    "boro_greenup": ("up", (12, 1, -1), (3, 31, 0)),
    "boro_browning": ("down", (4, 1, 0), (6, 30, 0)),
    "aman_greenup": ("up", (6, 1, 0), (9, 30, 0)),
    "aman_browning": ("down", (10, 1, 0), (1, 31, 1)),
}
PUBLIC_URL = re.compile(r"^https?://[^/\s]+\.(?!pdf\b)[a-z]{2,}(/|$)", re.I)


def is_public_url(url):
    """True for an http(s) link with a real host; placeholders such as https://brridhan28.pdf are refused."""
    return bool(PUBLIC_URL.match(str(url).strip())) and "n/a" not in str(url).lower()


def window_dates(spec, year):
    (m1, d1, o1), (m2, d2, o2) = spec
    return pd.Timestamp(year + o1, m1, d1), pd.Timestamp(year + o2, m2, d2)


def threshold_crossings(dates, ndvi, threshold):
    """[(date, 'up' | 'down')] where the series crosses `threshold` between two consecutive valid
    composites (linear interpolation). NaN composites are skipped, not filled."""
    d = pd.to_datetime(pd.Series(list(dates)))
    v = np.asarray(ndvi, dtype=float)
    keep = ~np.isnan(v)
    d, v = d[keep].reset_index(drop=True), v[keep]
    out = []
    for i in range(1, len(v)):
        lo, hi = v[i - 1], v[i]
        if (lo < threshold <= hi) or (lo >= threshold > hi):
            frac = (threshold - lo) / (hi - lo)
            out.append(((d[i - 1] + (d[i] - d[i - 1]) * float(frac)).round("s"), "up" if hi > lo else "down"))
    return out


def smooth(ndvi, window=SG_WINDOW, order=SG_ORDER):
    """(smoothed values, number of NaN composites filled by linear interpolation before smoothing)."""
    s = pd.Series(np.asarray(ndvi, dtype=float))
    n_filled = int(s.isna().sum())
    filled = s.interpolate(limit_direction="both").values
    if len(filled) < window:
        return filled, n_filled
    return savgol_filter(filled, window, order), n_filled


def change_point_date(dates, values, direction):
    """Date of the Pettitt change point of `values`, or None when there are fewer than 4 values or
    the level moves the other way. Returns (date, p)."""
    d = pd.to_datetime(pd.Series(list(dates))).reset_index(drop=True)
    v = np.asarray(values, dtype=float)
    if len(v) < 4:
        return None, float("nan")
    r = pettitt_test(v)
    rises = r["mean_after"] > r["mean_before"]
    if rises != (direction == "up"):
        return None, float(r["p"])
    k = r["split"]
    return d[k - 1] + (d[k] - d[k - 1]) / 2, float(r["p"])


def days_outside(date, start, end):
    """0 inside the window [start, end]; otherwise days to the nearest edge (negative = early)."""
    if date < start:
        return int((date - start).days)
    if date > end:
        return int((date - end).days)
    return 0


def _mmdd(rows, pick):
    vals = [(int(r.month), int(r.day)) for r in rows.itertuples()]
    return pick(vals) if vals else None


def reference_windows(kept):
    """Cited field-establishment windows built from crop_calendar.csv rows that the strict loader kept
    and that carry a public URL. Each window is {start, end, derivation, sources} with (month, day,
    year offset) edges, or {status: 'not assessed', reason}."""
    k = kept[kept.source_url.map(is_public_url)]

    def rows(item):
        return k[k.item == item]

    def age(item):
        r = rows(item)
        return (int(r.low.min()), int(r.high.max())) if len(r) and r.low.notna().all() else None

    def src(*items):
        return sorted({f"{r.item}; {r.source_url}" for i in items for r in rows(i).itertuples()})

    out = {}
    b0, b1, bage = _mmdd(rows("boro_rice.sow.seedbed_start"), min), _mmdd(rows("boro_rice.sow.window_end"), max), age("boro_rice.stage.seedling_age")
    if b0 and b1 and bage:
        start = pd.Timestamp(2000, *b0) + pd.Timedelta(days=bage[0])
        out["boro_greenup"] = {
            "start": (start.month, start.day, -1 if start.month >= 7 else 0), "end": (b1[0], b1[1], 0),
            "derivation": f"earliest cited seedbed sowing {b0[1]:02d}/{b0[0]:02d} + youngest cited seedling age "
                          f"{bage[0]} days, to the cited date transplanting should be complete",
            "sources": src("boro_rice.sow.seedbed_start", "boro_rice.sow.window_end", "boro_rice.stage.seedling_age")}
    else:
        out["boro_greenup"] = {"status": "not assessed", "reason": "no cited Boro seedbed start, seedling age and transplanting end with a public URL"}
    a0, a1, aage = _mmdd(rows("aman_rice.sow.window_start"), min), _mmdd(rows("aman_rice.sow.window_end"), max), age("aman_rice.stage.seedling_age")
    if a0 and a1 and aage:
        s, e = pd.Timestamp(2001, *a0) + pd.Timedelta(days=aage[0]), pd.Timestamp(2001, *a1) + pd.Timedelta(days=aage[1])
        out["aman_greenup"] = {
            "start": (s.month, s.day, 0), "end": (e.month, e.day, 0),
            "derivation": f"cited seedbed sowing window {a0[1]:02d}/{a0[0]:02d} to {a1[1]:02d}/{a1[0]:02d} "
                          f"(both variety groups) + cited seedling age {aage[0]} to {aage[1]} days",
            "sources": src("aman_rice.sow.window_start", "aman_rice.sow.window_end", "aman_rice.stage.seedling_age")}
    else:
        out["aman_greenup"] = {"status": "not assessed", "reason": "no cited Aman seedbed window and seedling age with a public URL"}
    out["boro_browning"] = {"status": "not assessed", "reason": "no cited Boro harvest window: the BAMIS duration row "
                            "does not say where the count starts and its stage dates are a GAP"}
    out["aman_browning"] = {"status": "not assessed", "reason": "no cited Aman harvest window: the only days-to-maturity "
                            "row cites a placeholder URL (BRRI handbook), so it is not used"}
    return out


def detect(modis_df, district, years, threshold=None):
    """One row per (year, transition): date_a (threshold, None if never crossed), date_b (change point),
    p_b, n_composites and n_filled. `threshold` None means Method A is not run."""
    d = modis_df[modis_df.district == district].sort_values("date")
    dates, ndvi = pd.to_datetime(d.date.values), d.ndvi.values.astype(float)
    sm, _ = smooth(ndvi) if len(ndvi) else (ndvi, 0)
    rows = []
    for y in years:
        for name, (direction, a, b) in SEARCH.items():
            start, end = window_dates((a, b), y)
            m = (dates >= start) & (dates <= end)
            n_valid = int((~np.isnan(ndvi[m])).sum())
            date_a = None
            if threshold is not None:
                hits = [t for t, way in threshold_crossings(dates[m], ndvi[m], threshold) if way == direction]
                date_a = hits[0] if hits else None
            date_b, p = (None, float("nan"))
            if n_valid >= 4:
                date_b, p = change_point_date(dates[m], sm[m], direction)
            rows.append({"district": district, "year": int(y), "transition": name, "date_a": date_a,
                         "date_b": date_b, "p_b": p, "n_composites": int(m.sum()), "n_valid": n_valid,
                         "n_filled": int(m.sum()) - n_valid})
    return pd.DataFrame(rows)


def add_errors(detected, windows):
    """Adds err_a and err_b: days outside the cited window (0 = inside; NaN where there is no date or
    no cited window)."""
    out = detected.copy()
    for col, err in (("date_a", "err_a"), ("date_b", "err_b")):
        vals = []
        for r in out.itertuples():
            w = windows.get(r.transition, {})
            date = getattr(r, col)
            if "start" not in w or date is None or pd.isna(date):
                vals.append(np.nan)
            else:
                s, e = window_dates((w["start"], w["end"]), r.year)
                vals.append(days_outside(date, s, e))
        out[err] = vals
    return out

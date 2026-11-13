"""One small loader per W1b satellite layer. Each returns a Layer: the data, its provenance
(dataset, source URL, resolution, coverage years, units) and plain-language notes with the caveats.

Rules kept here: a missing value stays NaN (never 0); a loader never fills or interpolates; the
ECOSTRESS loader refuses to hand out the series unless the caller says it accepts the risk.
No AI, no network."""

import glob
import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from indicators.core import MIN_OTHER_YEARS, leave_one_out_z
from sat_layers.provenance import provenance

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "processed")
CLEAR_MIN = 0.5            # a scene counts as "clear enough" at this clear_share: OUR choice, not a standard
MIN_COMPOSITES = 20        # a calendar year counts as present with at least this many of its 23 MODIS composites: our choice
MIN_YEARS_FOR_ANOMALY = 6  # the rule given for the vegetation anomaly: fewer than 6 years means not assessed
GAP_DAYS = 40              # a gap longer than this between GRACE-FO dates is listed


class LayerUnverified(Exception):
    """Raised when a layer whose units or mask could not be confirmed is requested without opt-in."""


@dataclass
class Layer:
    data: pd.DataFrame
    provenance: dict
    notes: list = field(default_factory=list)


def _years(dates):
    y = pd.to_datetime(pd.Series(list(dates))).dt.year
    return sorted(int(v) for v in y.unique())


# ---------------- NASADEM ----------------

def load_nasadem(data_dir=DATA_DIR):
    """64-district mean elevation (m) and mean slope (degrees), one row per district."""
    df = pd.read_csv(os.path.join(data_dir, "nasadem_district_static.csv"))
    return Layer(df, provenance("nasadem", "2000 (single acquisition)"), [
        "Use slope only as a relative ranking between districts: about 2 degrees on flat delta "
        "districts is probably surface noise, not real terrain.",
        "Coastal 0.1 degree cells include sea pixels, which lowers their mean elevation a little.",
    ])


def nasadem_tile_summary(name, data_dir=DATA_DIR):
    """30 m demo tile: pixel count, lowest and highest elevation, and how many pixels are below 0 m
    (DEM noise: Bangladesh has almost no land below sea level)."""
    e = np.load(os.path.join(data_dir, f"nasadem_30m_{name}.npz"))["elev_m"].astype(float)
    e[e == -32768] = np.nan
    ok = e[np.isfinite(e)]
    return {"tile": name, "n_pixels": int(ok.size), "min_m": float(ok.min()), "max_m": float(ok.max()),
            "n_below_0m": int((ok < 0).sum()), "share_below_0m": float((ok < 0).mean())}


# ---------------- GRACE-FO ----------------

def load_grace(data_dir=DATA_DIR):
    """District table of the JPL mascon values. Always REGIONAL; never district groundwater."""
    df = pd.read_csv(os.path.join(data_dir, "grace_district_monthly.csv"))
    if not df["regional"].all():
        raise ValueError("GRACE-FO rows must all be flagged regional")
    return Layer(df, provenance("grace", f"{df.date.min()[:4]} to {df.date.max()[:4]}"), [
        "Regional signal (about 300 km effective); districts sharing a mascon cell share one series.",
        "Dates are irregular and have gaps (see grace_gaps); do not interpolate silently.",
    ])


def grace_gaps(df, min_days=GAP_DAYS):
    """[(from_date, to_date, days)] for gaps longer than `min_days` between consecutive dates."""
    d = pd.Series(sorted(pd.to_datetime(df["date"]).unique()))
    step = d.diff().dt.days
    return [(d[i - 1].date().isoformat(), d[i].date().isoformat(), int(step[i])) for i in step.index[step > min_days]]


def grace_cells(df):
    """(number of distinct mascon cells used, most districts sharing one cell)."""
    one = df.drop_duplicates("district")
    sizes = one.groupby(["cell_lon", "cell_lat"]).size()
    return int(len(sizes)), int(sizes.max())


# ---------------- MODIS ----------------

def load_modis(data_dir=DATA_DIR):
    """All modis_district_<year>.csv.gz files joined, one row per (date, district).

    Each year file starts with the previous year's last composite, so the same (date, district)
    appears twice; copies must agree exactly or this raises (no silent choice)."""
    files = sorted(glob.glob(os.path.join(data_dir, "modis_district_*.csv.gz")))
    if not files:
        raise FileNotFoundError("no modis_district_<year>.csv.gz files in " + data_dir)
    raw = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    key = ["date", "district"]
    dup = raw[raw.duplicated(key, keep=False)]
    if len(dup):
        spread = dup.groupby(key)[["ndvi", "evi"]].agg(lambda s: s.nunique(dropna=False))
        if (spread > 1).any().any():
            raise ValueError("overlapping MODIS composites disagree between year files")
    df = raw.drop_duplicates(key).sort_values(key).reset_index(drop=True)
    years = modis_years_present(df)
    return Layer(df, provenance("modis", f"composite years with data: {years}"), [
        f"{len(years)} calendar years present; the rest of 2001-2024 is not downloaded.",
        "NaN = no good pixel (cloud or poor quality) in that district and composite; it is not 0.",
        "Quality rule (pixel_reliability = 0 kept) is recalled from the product guide, not yet confirmed.",
    ])


def modis_years_present(df, min_composites=MIN_COMPOSITES):
    """Calendar years with at least `min_composites` composites in the table (the single carry-over
    composite from the previous December does not make a year)."""
    n_dates = df.groupby(pd.to_datetime(df["date"]).dt.year).date.nunique()
    return sorted(int(y) for y in n_dates.index if n_dates[y] >= min_composites)


def ndvi_anomaly(df, district, min_other=MIN_OTHER_YEARS, min_years=MIN_YEARS_FOR_ANOMALY):
    """NDVI z-score of each composite against the same composite (same day of year) in the OTHER years.

    Returns (table, status). table columns: date, year, doy, ndvi, z, n_other. z is NaN where fewer
    than `min_other` other years have a value. status is 'not assessed (needs >=5 other years)' when
    fewer than `min_years` years are present, else 'partial (n years of 24)'."""
    years = modis_years_present(df)
    d = df[df.district == district].copy()
    d["date"] = pd.to_datetime(d["date"])
    d["year"], d["doy"] = d.date.dt.year, d.date.dt.dayofyear
    d = d[d.year.isin(years)]
    if len(years) < min_years:
        out = d.assign(z=np.nan, n_other=0)[["date", "year", "doy", "ndvi", "z", "n_other"]]
        return out, f"not assessed (needs >={min_other} other years; only {len(years)} present)"
    rows = []
    for doy, g in d.groupby("doy"):
        by_year = dict(zip(g.year, g.ndvi))
        for _, r in g.iterrows():
            z, n = leave_one_out_z(by_year, r.year, min_other)
            rows.append({"date": r.date, "year": r.year, "doy": doy, "ndvi": r.ndvi, "z": z, "n_other": n})
    return (pd.DataFrame(rows).sort_values("date").reset_index(drop=True),
            f"partial ({len(years)} years of 24 present)")


# ---------------- HLS ----------------

def load_hls(data_dir=DATA_DIR):
    """Tile-mean HLS NDVI per scene for the two 20 km demo tiles (2024)."""
    df = pd.read_csv(os.path.join(data_dir, "hls_ndvi_tile_series.csv"))
    return Layer(df, provenance("hls", _years(df.date)), [
        "Tile mean over a 20 km box, not a single field.",
        f"Scenes with clear_share >= {CLEAR_MIN} are 'usable'; that cut-off is our choice.",
        "About 1% of red/NIR values were outside 0-1 and were set to missing in the Colab run (as reported by the user).",
    ])


def hls_clear_counts(df, min_clear=CLEAR_MIN):
    """Per tile and sensor: scenes listed, scenes with any valid pixel, scenes with clear_share >= min_clear."""
    g = df.groupby(["tile", "sensor"])
    return pd.DataFrame({"scenes": g.size(), "with_pixels": g.tile_mean_ndvi.apply(lambda s: int(s.notna().sum())),
                         "usable": g.clear_share.apply(lambda s: int((s >= min_clear).sum()))}).reset_index()


# ---------------- ECOSTRESS ----------------

def load_ecostress(data_dir=DATA_DIR, allow_unverified=False):
    """ECOSTRESS tile ET series. Refused unless allow_unverified=True: the ETdaily units are unresolved
    (see docs/results/w1b_intake_checks.md)."""
    if not allow_unverified:
        raise LayerUnverified(
            "ECOSTRESS ETdaily units are unresolved: the file tags W/m2 (also on the 0/1 cloud layer, so the tag "
            "is not reliable per layer) while the values look like mm/day. The series is not used for any "
            "comparison. What would resolve it: the ETdaily unit stated in the ECO_L3T_JET.002 User Guide or "
            "ATBD. Pass allow_unverified=True only to inspect the raw file.")
    df = pd.read_csv(os.path.join(data_dir, "ecostress_tile_series.csv"))
    return Layer(df, provenance("ecostress", _years(df.date.str[:10])), [
        "UNRESOLVED units: do not use for any comparison or convert to another unit.",
        "Cloud mask: cloud = 1 behaves as cloudy with no ET value in one scene; not documented.",
        "Only ET is in the file; ECOSTRESS land-surface temperature was not delivered.",
    ])

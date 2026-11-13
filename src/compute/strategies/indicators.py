"""
src/compute/strategies/indicators.py

W4 rotation-level indicators (Layer 1, no AI):

- bare_field_days: days of the rotation year with no crop in the field, from
  OUR sowing-to-harvest windows in the rotation evaluation, never from
  satellite observation (the label says so).
- problem_year_range: the rotation's problem-year count with a percentile
  bootstrap range. Same settings as W3 (src/ml/si_models/validation.py:
  seed 20261112, 2000 draws, 95%), reimplemented here with numpy only so
  Layer 1 does not import Layer 2.
- heavy_rain_days_per_year: days at or above a cited heavy-rain limit
  (the reference row if one exists, otherwise ETCCDI R20mm; `which` says which).
- slope_class: NASADEM mean slope as a tercile class across the 64 districts.
  A RELATIVE ranking only: median slope on mostly flat delta land is about
  2 degrees and probably surface noise, and the tercile breakpoints are our
  choice. The reason text comes from docs/w1b_data_status.csv.
- erosion_exposure = bare days x heavy-rain days x slope class, a relative
  index with no physical unit. Any gap component makes it a gap, never a 0.
"""

import os

import numpy as np
import pandas as pd

from common import Provenance, measured
from indicators.heavy_rain import CELL_MEAN_LABEL, heavy_rain_days, load_heavy_rain_threshold
from reference import NUMBER_RE, REFERENCE_DIR
from sat_layers.status import status_of

# Bootstrap settings, kept equal to src/ml/si_models/validation.py (W3).
SEED = 20261112
N_BOOT = 2000
LEVEL = 0.95

DAYS_IN_YEAR = 365                      # our convention; leap days are ignored
BARE_NOTE = ("bare-field days are counted from our windows (sowing to harvest in the "
             "rotation evaluation, Kharif-1 fallow included), not satellite-observed")
R20_ITEM = "etccdi_r20mm_threshold"
R20_FILE = "r03_heavy_rain.csv"

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
NASADEM_PATH = os.path.join(REPO_ROOT, "data", "processed", "nasadem_district_static.csv")
NASADEM_KEY = "nasadem_slope"
TERCILE_NOTE = ("relative ranking only ({reason}); the tercile breakpoints across the "
                "64 districts are our choice, not a cited erosion class")


def _gap(reason):
    return {"status": "gap", "reason": reason}


# ---------------- bare-field days ----------------

def bare_field_days(evaluation):
    """Per feasible year: 365 minus the days a crop is in the field (sowing to
    harvest per slot). Years that are infeasible or missing a date are listed
    in years_not_counted. Median across counted years."""
    prov_source = evaluation["summary"]["n_years"]["provenance"]
    per_year, skipped = [], []
    for y in evaluation["years"]:
        dates = [(s.get("sowing_date"), s.get("harvest_date")) for s in y["slots"]]
        if not y["feasible"] or any(a is None or b is None for a, b in dates):
            skipped.append(y["year"])
            continue
        in_field = sum((pd.Timestamp(b) - pd.Timestamp(a)).days for a, b in dates)
        per_year.append({"year": y["year"], "days": DAYS_IN_YEAR - in_field})
    if not per_year:
        return _gap("no feasible year with complete sowing and harvest dates")
    prov = Provenance(dataset=prov_source["dataset"], source_url=prov_source["source_url"],
                      retrieved=prov_source["retrieved"],
                      granule_or_file=prov_source["granule_or_file"], note=BARE_NOTE)
    days = [r["days"] for r in per_year]
    return {"status": "assessed", "per_year": per_year, "years_not_counted": skipped,
            "days_median": measured(float(np.median(days)), "days per year", prov),
            "note": BARE_NOTE}


# ---------------- problem years with a bootstrap range ----------------

def _bootstrap_count(flags, n_boot=N_BOOT, seed=SEED, level=LEVEL):
    x = np.asarray(flags, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    counts = x[idx].sum(axis=1)
    a = (1 - level) / 2
    return int(round(np.quantile(counts, a))), int(round(np.quantile(counts, 1 - a)))


def problem_year_range(evaluation):
    """The summary's problem-year count plus a bootstrap range over the per-year
    problem flags. Not assessed (gap) when the rotation has no sourced hazard."""
    s = evaluation["summary"]
    if s.get("problem_years") is None or not s.get("hazards_checked"):
        return _gap("not assessed: no sourced hazard for this rotation")
    flags = [1 if y.get("problem_year") else 0
             for y in evaluation["years"] if y["feasible"] and y.get("problem_year") is not None]
    if not flags:
        return _gap("not assessed: no feasible year with an assessed problem flag")
    lo, hi = _bootstrap_count(flags)
    return {"status": "assessed", "count": s["problem_years"], "n": len(flags),
            "lo": lo, "hi": hi, "level": LEVEL, "n_boot": N_BOOT, "seed": SEED,
            "hazards_checked": list(s.get("hazards_checked", [])),
            "note": ("percentile bootstrap over the per-year problem flags; same settings "
                     "as the W3 model comparison (src/ml/si_models/validation.py)")}


# ---------------- heavy-rain days ----------------

def _r20_fallback(reference_dir):
    path = os.path.join(reference_dir, R20_FILE)
    if not os.path.exists(path):
        return None
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    hit = table[table["item"].str.strip() == R20_ITEM]
    if hit.empty or not NUMBER_RE.match(hit.iloc[0]["value"].strip()):
        return None
    r = hit.iloc[0]
    if not r["source_url"].strip().lower().startswith("http"):
        return None
    return {"item": R20_ITEM, "value": float(r["value"]), "unit": r["unit"],
            "source_title": r["source_title"], "source_url": r["source_url"].strip(),
            "page": r["page"].strip(), "notes": r["notes"],
            "via": "raw row (ETCCDI R20mm fallback; no dotted item name for the strict loader)"}


def heavy_rain_days_per_year(rain, years, reference_dir=REFERENCE_DIR,
                             rain_provenance=None):
    """Mean yearly count of days with rain at or above the cited limit.

    rain: a daily series indexed by date (IMERG rain, mm). years: calendar
    years to count. Returns None when no cited threshold row exists."""
    threshold = load_heavy_rain_threshold(reference_dir)
    which = "cited reference row"
    if threshold is None:
        threshold = _r20_fallback(reference_dir)
        which = "ETCCDI R20mm fallback"
    if threshold is None:
        return None
    counts = []
    for year in years:
        chunk = rain.loc[f"{year}-01-01":f"{year}-12-31"]
        if len(chunk):
            counts.append(heavy_rain_days(chunk.values, threshold["value"]))
    if not counts:
        return None
    rp = rain_provenance or {}
    prov = Provenance(
        dataset=rp.get("dataset", "daily rain series") + f"; limit: {threshold['source_title']}",
        source_url=threshold["source_url"],
        retrieved=rp.get("retrieved", _today()),
        granule_or_file=rp.get("granule_or_file", "caller-supplied rain series"),
        note=f"{CELL_MEAN_LABEL}; threshold via {threshold['via']}")
    return {"days_mean": measured(float(np.mean(counts)), "days per year", prov),
            "threshold": {"value": float(threshold["value"]), "unit": threshold["unit"],
                          "source_title": threshold["source_title"],
                          "source_url": threshold["source_url"], "via": threshold["via"]},
            "which": which, "n_years": len(counts), "note": CELL_MEAN_LABEL}


def _today():
    import datetime
    return datetime.date.today().isoformat()


# ---------------- slope class ----------------

def slope_class(district, path=NASADEM_PATH, status_reason=None):
    """Tercile class (1 low, 2 middle, 3 high) of the district's NASADEM mean
    slope across every district in the file. Relative ranking only."""
    if not os.path.exists(path):
        return _gap(f"NASADEM static table not found: {path}")
    table = pd.read_csv(path)
    hit = table[table["district"] == district]
    if hit.empty:
        return _gap(f"{district} is not in {os.path.basename(path)}")
    if status_reason is None:
        try:
            _, status_reason = status_of(NASADEM_KEY)
        except (KeyError, FileNotFoundError, ValueError):
            status_reason = "status table unavailable; NASADEM slope is treated as relative only"
    slopes = table["slope_mean_deg"].astype(float)
    q1, q2 = float(np.quantile(slopes, 1 / 3)), float(np.quantile(slopes, 2 / 3))
    value = float(hit.iloc[0]["slope_mean_deg"])
    cls = 1 if value <= q1 else (2 if value <= q2 else 3)
    note = TERCILE_NOTE.format(reason=status_reason)
    prov = Provenance(dataset="NASADEM mean slope (30 m, regridded, district mean)",
                      source_url="https://appeears.earthdatacloud.nasa.gov/api/product/NASADEM_NC.001",
                      retrieved=_file_date(path),
                      granule_or_file="data/processed/nasadem_district_static.csv", note=note)
    return {"status": "assessed", "class": cls,
            "slope": measured(value, "degrees (mean slope)", prov),
            "breakpoints_deg": [round(q1, 3), round(q2, 3)],
            "n_districts": int(len(table)), "note": note}


def _file_date(path):
    import datetime
    return datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()


# ---------------- erosion exposure ----------------

def erosion_exposure(bare, heavy, slope):
    """bare days x heavy-rain days x slope class, a relative index. Gap when any
    component is a gap or not computed; the reasons are passed through."""
    reasons = []
    if bare.get("status") != "assessed":
        reasons.append(f"bare-field days: {bare.get('reason', 'not assessed')}")
    if heavy is None or heavy.get("days_mean") is None:
        reasons.append("heavy-rain days: no cited threshold row (not assessed)")
    if slope.get("status") != "assessed":
        reasons.append(f"slope class: {slope.get('reason', 'not assessed')}")
    if reasons:
        return _gap("; ".join(reasons))
    value = bare["days_median"]["value"] * heavy["days_mean"]["value"] * slope["class"]
    bp = bare["days_median"]["provenance"]
    note = ("relative index only: bare days (our windows) x mean heavy-rain days "
            f"({heavy['which']}) x slope tercile class ({slope['note']})")
    prov = Provenance(dataset="erosion exposure (derived)",
                      source_url=heavy["days_mean"]["provenance"]["source_url"],
                      retrieved=bp["retrieved"],
                      granule_or_file=bp["granule_or_file"], note=note)
    return {"status": "assessed",
            "index": measured(round(value, 1), "relative index (days x days x class)", prov),
            "components": {"bare_days_median": bare["days_median"],
                           "heavy_rain_days_mean": heavy["days_mean"],
                           "slope_class": slope["class"]},
            "note": note}

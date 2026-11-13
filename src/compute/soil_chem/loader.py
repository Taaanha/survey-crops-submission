"""
Reads data/processed/soilgrids_ph_oc_points.csv (written by scripts/fetch_soil_ph_oc.py)
and returns it as measured numbers with provenance. Layer 1: no network, no AI.

Layers are reported one by one (0-5, 5-15, 15-30 cm) with the service's Q0.05..Q0.95
range. They are NOT averaged into one 0-30 cm range: quantiles of separate layers
cannot be combined honestly. A missing value is a gap with its reason, never 0.
"""

import os

import pandas as pd

from common import Provenance, measured

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CSV_PATH = os.path.join(ROOT, "data", "processed", "soilgrids_ph_oc_points.csv")
LABEL = "SoilGrids model estimate, 250 m, not a soil test; confirm with a local soil test"
DEPTHS = ("0-5cm", "5-15cm", "15-30cm")
PROPS = {"ph": "phh2o", "organic_carbon": "soc"}
STAT_KEY = {"mean": "mean", "Q0.05": "q05", "Q0.5": "q50", "Q0.95": "q95"}
STATUS_KEYS = {"phh2o": ("soilgrids_ph", "SoilGrids soil pH (H2O), 0-30 cm in three layers"),
               "soc": ("soilgrids_soc", "SoilGrids soil organic carbon, 0-30 cm in three layers")}
STATUS_COLUMNS = ["key", "dataset", "coverage", "districts", "status", "reason",
                  "source_url", "units", "resolution"]


def _load(path):
    return pd.read_csv(path or CSV_PATH, keep_default_na=False, dtype=str)


def _property(df, point_id, prop):
    sub = df[(df.point_id == point_id) & (df.property == prop)]
    layers, reasons = [], []
    for depth in DEPTHS:
        entry = {"depth": depth}
        for _, r in sub[sub.depth == depth].iterrows():
            if r.status != "assessed":
                reasons.append(f"{depth} {r.statistic}: {r.reason}")
                continue
            prov = Provenance(dataset=r.dataset, source_url=r.source_url, retrieved=r.fetch_date,
                              granule_or_file="data/processed/soilgrids_ph_oc_points.csv",
                              note=f"{r.resolution}; raw {r.raw_value} {r.mapped_units} / {r.d_factor}; "
                                   f"query {r['query']}")
            entry[STAT_KEY[r.statistic]] = measured(float(r.value), r.units, prov)
        layers.append(entry)
    complete = all(k in e for e in layers for k in ("mean", "q05", "q95"))
    if complete:
        return {"status": "assessed", "layers": layers}
    return {"status": "gap", "reason": "; ".join(reasons[:3]) or "no rows for this point"}


def soil_baseline(point_id, path=None):
    """{"status", "label", "point_id", "ph", "organic_carbon"} for one saved point
    (a district name or a demo field), or a gap with the reason."""
    try:
        df = _load(path)
    except OSError:
        return {"status": "gap", "reason": "SoilGrids file not fetched yet "
                                           "(run scripts/fetch_soil_ph_oc.py)"}
    if (df.point_id == point_id).sum() == 0:
        return {"status": "gap", "reason": f"SoilGrids not fetched for {point_id}"}
    out = {"label": LABEL, "point_id": point_id}
    for key, prop in PROPS.items():
        out[key] = _property(df, point_id, prop)
    if all(out[k]["status"] == "gap" for k in PROPS):
        reasons = "; ".join(f"{k}: {out[k]['reason']}" for k in PROPS)
        return {"status": "gap", "reason": f"SoilGrids has no value here ({reasons})"}
    out["status"] = "assessed"
    return out


def status_rows(path=None):
    """Two rows for docs/w1b_data_status.csv (pH, organic carbon)."""
    from common import Provenance as _  # noqa: F401  (keeps import order explicit)
    url = "https://docs.isric.org/globaldata/soilgrids/index.html"
    try:
        df = _load(path)
    except OSError:
        df = None
    rows = []
    for prop, (key, name) in STATUS_KEYS.items():
        unit = "pH (H2O)" if prop == "phh2o" else "g/kg (SoilGrids stores dg/kg; read from the service's d_factor)"
        if df is None or df.empty:
            rows.append({"key": key, "dataset": name, "coverage": "none", "districts": 0,
                         "status": "not assessed", "reason": "file not fetched yet",
                         "source_url": url, "units": unit, "resolution": "250 m"})
            continue
        sub = df[df.property == prop]
        ok, bad = [], []
        for pid, g in sub.groupby("point_id"):
            (ok if (g.status == "assessed").all() else bad).append(pid)
        fetched = sorted(sub.fetch_date.unique())
        status = "assessed" if not bad else ("partial" if ok else "not assessed")
        reason = "all points have values" if not bad else (
            "gap (SoilGrids returned null or the call failed; never filled from a neighbour): "
            + ", ".join(sorted(bad)))
        rows.append({"key": key, "dataset": name,
                     "coverage": f"{len(ok)} of {len(ok) + len(bad)} points; fetched {', '.join(fetched)}",
                     "districts": len(ok), "status": status, "reason": reason,
                     "source_url": url, "units": unit,
                     "resolution": "250 m model estimate at the point, not a soil test"
                     if False else "250 m"})
    return rows

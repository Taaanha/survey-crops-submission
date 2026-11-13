"""Intake checks on the delivered W1b files, and the status table built from them.

run_checks() reads the files in data/processed/ and returns plain numbers (nothing assumed);
build_status() turns them into one row per layer. Nothing is written here: the script
scripts/build_w1b_intake.py writes docs/w1b_data_status.csv and docs/results/w1b_intake_checks.md."""

import os

import numpy as np
import pandas as pd

from sat_layers import loaders as L
from sat_layers.provenance import PROVENANCE
from sat_layers.status import COLUMNS

LIVE = ("cumilla", "feni", "brahmanbaria", "noakhali", "sylhet")
# ECOSTRESS: 1 W/m2 sustained for a day = 0.0864 MJ/m2/day; 1 MJ/m2/day of latent heat = 0.408 mm/day
# (FAO-56 eq. 20). The Colab run applied this factor to ETdaily; dividing by it recovers the raw layer.
MM_PER_DAY_PER_WM2 = 0.0864 * 0.408


def run_checks(data_dir=L.DATA_DIR):
    """Facts about each delivered file, computed from the files."""
    c = {}
    modis = L.load_modis(data_dir)
    m = modis.data
    files = sorted(f for f in os.listdir(data_dir) if f.startswith("modis_district_") and f.endswith(".csv.gz"))
    years = L.modis_years_present(m)
    _, a_status = L.ndvi_anomaly(m, LIVE[0])
    n_raw = sum(len(pd.read_csv(os.path.join(data_dir, f))) for f in files)
    c["modis"] = {"files": len(files), "years": years, "rows_raw": n_raw, "rows_joined": len(m),
                  "districts": int(m.district.nunique()), "first_date": m.date.min(), "last_date": m.date.max(),
                  "missing_years_2001_2024": [y for y in range(2001, 2025) if y not in years],
                  "ndvi_missing_share": float(m.ndvi.isna().mean()), "anomaly_status": a_status,
                  "ndvi_missing_top": m.groupby("district").ndvi.apply(lambda s: float(s.isna().mean())).sort_values(ascending=False).head(3).to_dict()}
    g = L.load_grace(data_dir).data
    cells, most = L.grace_cells(g)
    c["grace"] = {"districts": int(g.district.nunique()), "dates": int(g.date.nunique()), "first": g.date.min(),
                  "last": g.date.max(), "cells": cells, "most_sharing": most, "gaps": L.grace_gaps(g),
                  "unc_min": float(g.uncertainty_cm.min()), "unc_max": float(g.uncertainty_cm.max()),
                  "lwe_min": float(g.lwe_thickness_cm.min()), "lwe_max": float(g.lwe_thickness_cm.max())}
    n = L.load_nasadem(data_dir).data
    c["nasadem"] = {"districts": int(len(n)), "tiles": [L.nasadem_tile_summary(t, data_dir) for t in ("feni", "cumilla")],
                    "slope_live": {d: float(n.set_index("district").loc[d, "slope_mean_deg"]) for d in LIVE},
                    "slope_min": float(n.slope_mean_deg.min()), "slope_median": float(n.slope_mean_deg.median())}
    h = L.load_hls(data_dir).data
    ok = h[h.clear_share >= L.CLEAR_MIN]
    by_month = ok.date.str[5:7].astype(int).value_counts().to_dict()
    c["hls"] = {"counts": L.hls_clear_counts(h), "scenes": int(len(h)), "first": h.date.min(), "last": h.date.max(),
                "usable_by_month": {mo: int(by_month.get(mo, 0)) for mo in range(1, 13)}}
    e = L.load_ecostress(data_dir, allow_unverified=True).data
    raw = e.et_mm_day / MM_PER_DAY_PER_WM2
    c["ecostress"] = {"rows": int(len(e)), "products": sorted(e["product"].unique()), "first": e.date.min()[:10],
                      "last": e.date.max()[:10], "converted_median": float(e.et_mm_day.median()),
                      "converted_max": float(e.et_mm_day.max()), "raw_median": float(raw.median()),
                      "raw_max": float(raw.max()), "exact_zero": int((e.et_mm_day == 0).sum())}
    return c


def _row(key, dataset, coverage, districts, status, reason, prov):
    return {"key": key, "dataset": dataset, "coverage": coverage, "districts": districts, "status": status,
            "reason": reason, "source_url": prov["source_url"], "units": prov["units"], "resolution": prov["resolution"]}


def build_status(c):
    """Status table (columns status.COLUMNS) from run_checks() output."""
    P = PROVENANCE
    m, g, n, h, e = c["modis"], c["grace"], c["nasadem"], c["hls"], c["ecostress"]
    usable = h["counts"]
    use_txt = "; ".join(f"{r.tile} {r.sensor}: {r.usable} of {r.scenes}" for r in usable.itertuples())
    rows = [
        _row("smap_64", "SMAP L4 root-zone soil moisture, 64 districts", "none", 0, "not assessed",
             "AppEEARS job did not finish; five live districts use the existing point files (smap_live5)", P["smap_live"]),
        _row("smap_live5", "SMAP L4 root-zone soil moisture, point pixel", "2015-03-31 to 2026 (existing files)", 5, "partial",
             "five live districts only, one 9 km pixel at the district point (not a polygon mean)", P["smap_live"]),
        _row("modis_ndvi", "MODIS MOD13Q1 NDVI and EVI, 16-day", f"{len(m['years'])} of 24 years: {m['years']}", m["districts"],
             "partial", f"years missing from 2001-2024: {m['missing_years_2001_2024']}; "
             f"{m['ndvi_missing_share']:.1%} of district-composites have no good pixel (NaN, not 0)", P["modis"]),
        _row("modis_ndvi_anomaly", "MODIS NDVI z-score vs same composite in other years", f"{len(m['years'])} years",
             m["districts"], "not assessed" if m["anomaly_status"].startswith("not assessed") else "partial",
             m["anomaly_status"], P["modis"]),
        _row("nasadem_elevation", "NASADEM mean elevation", "2000 (single acquisition)", n["districts"], "assessed",
             "complete, no missing values; coastal cells include some sea pixels", P["nasadem"]),
        _row("nasadem_slope", "NASADEM mean slope", "2000 (single acquisition)", n["districts"], "partial",
             f"relative ranking only: median {n['slope_median']:.1f} degrees on mostly flat land is probably surface noise", P["nasadem"]),
        _row("grace_fo", "JPL GRACE and GRACE-FO mascons", f"{g['first'][:7]} to {g['last'][:7]}, {g['dates']} irregular dates",
             g["districts"], "partial", f"regional only (about 300 km): {g['cells']} cells for {g['districts']} districts, "
             f"up to {g['most_sharing']} share one cell; {len(g['gaps'])} gaps over {L.GAP_DAYS} days; never district groundwater", P["grace"]),
        _row("hls_ndvi", "HLS NDVI, two 20 km demo tiles", f"{h['first']} to {h['last']}, {h['scenes']} scenes", 2, "partial",
             f"demo tiles and 2024 only; scenes with clear_share >= {L.CLEAR_MIN} (our cut-off): {use_txt}", P["hls"]),
        _row("ecostress_et", "ECOSTRESS ETdaily, two demo tiles", f"{e['first']} to {e['last']}, {e['rows']} scenes", 2,
             "not assessed", "units unresolved: the file tags W/m2, also on the 0/1 cloud layer, while the raw values, "
             f"median about {e['raw_median']:.0f}, look like mm/day and not W/m2; only the ETdaily unit in the "
             "ECO_L3T_JET user guide or ATBD resolves it; cloud = 1 as cloudy is supported by one scene, not documented", P["ecostress"]),
        _row("ecostress_lst", "ECOSTRESS land-surface temperature, two demo tiles", "none", 0, "not assessed",
             "not in the delivered file (only ET rows)", P["ecostress"]),
        _row("gedi_agbd", "GEDI L4B biomass", "none", 0, "not assessed", "download not run; context only (mostly measures trees)",
             {"source_url": "https://doi.org/10.3334/ORNLDAAC/2299", "units": "Mg/ha (to confirm)", "resolution": "1 km"}),
    ]
    from soil_chem import status_rows        # W4 soil rows survive a rebuild of the table
    rows += status_rows()
    return pd.DataFrame(rows, columns=COLUMNS)

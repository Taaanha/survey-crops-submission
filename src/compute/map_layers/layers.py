"""Map layers (W5, Layer 1): the catalogue and the per-district values for one year.

Reads only files already in the repo (data/processed/*, docs/w1b_data_status.csv). Every layer of the
status table is listed; one that is not assessed is listed as disabled with its reason, never
hidden and never filled with 0. Every response carries its dataset and source URL. No AI, no
network."""

import functools
import os

import numpy as np
import pandas as pd

from map_layers.outlines import LIVE_DISTRICTS, SLUG_LIST
from sat_layers import loaders
from sat_layers.status import STATUS_PATH, NotAssessed, load_status

DATA_DIR = loaders.DATA_DIR
YEARS = tuple(range(2001, 2025))
SEASONS = ("kharif1", "kharif2", "rabi")
SEASON_NOTE = ("Season windows are our analysis windows (1 Mar-30 Jun, 1 Jul-31 Oct, 1 Nov-end Feb), "
               "not a cited crop calendar.")
MODIS_MIN_DISTRICT = 12     # a district-year needs more than half of the 23 composites: our choice
SMAP_MIN_DAYS = 300        # a calendar year of SMAP needs at least this many days: our choice
SCOPE_BY_COUNT = {64: "64 districts", 5: "5 live districts", 2: "demo fields", 0: "none yet"}
TABLE_DISABLED = {          # status-table layers that are listed but have no district map values
    "modis_ndvi_anomaly": "No season-level value yet (partial); the MODIS NDVI layer shows the "
                          "yearly NDVI itself.",
    "hls_ndvi": "Two 20 km demo tiles in 2024 only: not a district layer (the Field Passport "
                "shows what is in the repo).",
    "soilgrids_ph": "Point values at the district centroids and demo fields (most are masked cells), "
                    "shown in the W4 organic-matter indicator: not a map layer.",
    "soilgrids_soc": "Point values at the district centroids and demo fields (most are masked cells), "
                     "shown in the W4 organic-matter indicator: not a map layer.",
}
SCOPE_OVERRIDE = {"soilgrids_ph": "5 live districts", "soilgrids_soc": "5 live districts"}
CAVEATS = {
    "nasadem_elevation": ["Mean over the district polygon from 30 m pixels (single acquisition, 2000); "
                          "coastal cells include some sea pixels."],
    "nasadem_slope": ["Slope is a relative ranking only: about 2 degrees on flat delta districts is "
                      "probably surface noise, not real terrain."],
    "grace_fo": ["Regional signal, about 300 km effective: 48 mascon cells serve the 64 districts, so "
                 "neighbouring districts share one cell and one series.",
                 "Value = mean of the dates present in the year (n shown); irregular dates, gaps of "
                 "more than 40 days; never district groundwater."],
    "modis_ndvi": ["Only years present in the repo are shown (2015-2024); a year needs "
                   f"{loaders.MIN_COMPOSITES} composites overall and a district at least {MODIS_MIN_DISTRICT} "
                   "usable ones (our rules).",
                   "Yearly mean of 16-day composites; composites with no good pixel (often cloudy "
                   "monsoon dates) are left out, never counted as 0, so n is shown."],
    "smap_live5": ["One 9 km pixel at the district point (not a polygon mean), five live districts only.",
                   f"Yearly mean of daily root-zone moisture; a year needs at least {SMAP_MIN_DAYS} "
                   "days present (our rule), so 2015 (starts 31 March) has no value."],
}
W2_GROUPS = (("heat_days", "Heat days"), ("night_heat_days", "Hot nights"), ("cold_nights", "Cold nights"),
             ("extreme_rain_days", "Extreme-rain days (R20mm)"), ("heavy_rain_days", "Heavy-rain days (BMD)"),
             ("rx1day", "Heaviest rain day"), ("cdd", "Longest dry spell"), ("et0_season", "Reference evaporation"),
             ("rain_minus_et0", "Rain minus evaporation"), ("smap_rootzone_z", "Soil-moisture z-score"))


# ---------------- loading (cached) ----------------

@functools.lru_cache(maxsize=1)
def _w2():
    t = pd.read_csv(os.path.join(DATA_DIR, "indicators_districts_2001_2024.csv"), keep_default_na=False,
                    na_values=[""])
    return t[t.season.isin(SEASONS)]


@functools.lru_cache(maxsize=1)
def _grace():
    return loaders.load_grace(DATA_DIR)


@functools.lru_cache(maxsize=1)
def _modis():
    return loaders.load_modis(DATA_DIR)


@functools.lru_cache(maxsize=8)
def _smap(district):
    return pd.read_csv(os.path.join(DATA_DIR, f"smap_{district}_2015_2026.csv"), parse_dates=["date"])


def _w2_indicators():
    """Indicators with a value in every year window (the season tables, not the 15-row trends)."""
    t = _w2()
    n_years = t.groupby("indicator").season_year.nunique()
    return sorted(n_years[n_years >= len(YEARS)].index)


def _w2_label(indicator, row):
    base = indicator.split("__")[0]
    group = dict(W2_GROUPS).get(base) or next((v for k, v in W2_GROUPS if base.startswith(k)), base)
    if "__" in indicator:
        item = indicator.split("__", 1)[1]
        parts = item.split(".")
        crop, stage = parts[0].replace("_", " "), (parts[2] if len(parts) > 2 else "")
        return f"{group}: {crop}, {stage.replace('_', ' ')} (limit {row.threshold:g} {'C'})"
    return group


def _w2_years(indicator):
    t = _w2()
    s = t[(t.indicator == indicator) & (t.status == "ok") & t.value.notna()]
    return sorted(int(y) for y in s.season_year.unique())


# ---------------- catalogue ----------------

def _entry(key, label, group, scope, status, enabled, reason, dataset, url, unit, resolution, years,
           static=False, seasons=None, caveats=()):
    return {"key": key, "label": label, "group": group, "scope": scope, "status": status,
            "enabled": enabled, "reason": reason, "dataset": dataset, "source_url": url, "unit": unit,
            "resolution": resolution, "available_years": years, "static": static,
            "seasons": seasons, "caveats": list(caveats)}


def catalog(status_path=STATUS_PATH):
    """One entry per layer. Every row of the data status table is here; a layer that is not
    assessed is enabled=False with its reason. W2 indicator layers cover the five live districts."""
    out = []
    grace_years = sorted({int(d[:4]) for d in _grace().data.date})
    modis_years = loaders.modis_years_present(_modis().data)
    for r in load_status(status_path).itertuples():
        scope = SCOPE_OVERRIDE.get(r.key) or SCOPE_BY_COUNT.get(int(r.districts), f"{int(r.districts)} districts")
        enabled = r.status != "not assessed" and r.key not in TABLE_DISABLED
        reason = r.reason if r.status == "not assessed" else TABLE_DISABLED.get(r.key, "")
        years, static = [], False
        if enabled:
            if r.key.startswith("nasadem"):
                static = True
            elif r.key == "grace_fo":
                years = grace_years
            elif r.key == "modis_ndvi":
                years = modis_years
            elif r.key == "smap_live5":
                years = _smap_years()
        group = {"nasadem": "Terrain", "grace": "Water storage", "modis": "Vegetation",
                 "smap": "Soil moisture"}.get(r.key.split("_")[0], "Other satellite layers")
        out.append(_entry(r.key, str(r.dataset), group, scope, r.status, enabled,
                          reason or (r.reason if r.status == "partial" else ""), str(r.dataset),
                          r.source_url, r.units, r.resolution, years, static,
                          None, CAVEATS.get(r.key, [r.reason] if r.status == "partial" else [])))
    t = _w2()
    for ind in _w2_indicators():
        rows = t[t.indicator == ind]
        first = rows.iloc[0]
        years = _w2_years(ind)
        out.append(_entry(f"w2:{ind}", _w2_label(ind, first), "W2 indicators (5 live districts)",
                          "5 live districts", "assessed", True, "", first.dataset, first.source_url,
                          first.unit, "district point / cell (see dataset)", years, False,
                          list(SEASONS), [SEASON_NOTE]))
    return out


def _smap_years():
    years = set()
    for d in LIVE_DISTRICTS:
        s = _smap(d)
        counts = s.dropna(subset=["sm_rootzone"]).groupby(s.date.dt.year).size()
        years |= {int(y) for y, n in counts.items() if n >= SMAP_MIN_DAYS and y <= 2024}
    return sorted(years)


# ---------------- values ----------------

def _rows(values, notes=None, n=None, default_note="no value"):
    notes, n = notes or {}, n or {}
    out = []
    for d in SLUG_LIST:
        v = values.get(d)
        ok = v is not None and not (isinstance(v, float) and np.isnan(v))
        out.append({"district": d, "value": float(v) if ok else None, "n": n.get(d),
                    "note": notes.get(d, "" if ok else default_note)})
    return out


def _response(entry, year, season, rows, prov, caveats, status_note=""):
    return {"key": entry["key"], "label": entry["label"], "unit": entry["unit"], "year": year,
            "season": season, "static": entry["static"], "rows": rows, "scope": entry["scope"],
            "status": entry["status"], "status_note": status_note, "caveats": caveats,
            "provenance": prov}


def _check_year(year):
    if year is None or isinstance(year, bool) or int(year) != year or not YEARS[0] <= int(year) <= YEARS[-1]:
        raise ValueError(f"year must be a whole year from {YEARS[0]} to {YEARS[-1]}")
    return int(year)


def layer_values(key, year=None, season=None, status_path=STATUS_PATH):
    """Values of one layer for all 64 districts (None + a note where there is no value).
    Raises KeyError for an unknown layer and NotAssessed for a disabled one."""
    entry = {e["key"]: e for e in catalog(status_path)}.get(key)
    if entry is None:
        raise KeyError(f"unknown layer {key!r}")
    if not entry["enabled"]:
        raise NotAssessed(f"{key}: {entry['status']} ({entry['reason']})")
    prov = {"dataset": entry["dataset"], "source_url": entry["source_url"],
            "resolution": entry["resolution"], "units": entry["unit"]}
    if entry["static"]:
        return _static_values(entry, prov)
    year = _check_year(year)
    if key.startswith("w2:"):
        return _w2_values(entry, year, season, prov)
    note = ""
    if year not in entry["available_years"]:
        note = f"no data for {year}; years with data: {entry['available_years'][0]}-{entry['available_years'][-1]}"
    values, notes, ns = {}, {}, {}
    if not note:
        values, notes, ns = {"grace_fo": _grace_year, "modis_ndvi": _modis_year,
                             "smap_live5": _smap_year}[key](year)
    return _response(entry, year, None, _rows(values, notes, ns, "no value for this year"), prov,
                     entry["caveats"], note)


def _static_values(entry, prov):
    df = loaders.load_nasadem(DATA_DIR).data.set_index("district")
    col = {"nasadem_elevation": "elev_mean_m", "nasadem_slope": "slope_mean_deg"}[entry["key"]]
    unit = "m" if col.startswith("elev") else "degrees"
    r = _response(entry, None, None, _rows(df[col].to_dict(), default_note="no value"), prov,
                  entry["caveats"], "")
    r["unit"] = unit
    return r


def _grace_year(year):
    g = _grace().data
    g = g[g.date.str[:4] == str(year)]
    grp = g.groupby("district").lwe_thickness_cm
    return grp.mean().to_dict(), {}, grp.size().to_dict()


def _modis_year(year):
    m = _modis().data
    m = m[pd.to_datetime(m.date).dt.year == year].dropna(subset=["ndvi"])
    grp = m.groupby("district").ndvi
    n = grp.size()
    ok = n[n >= MODIS_MIN_DISTRICT].index
    notes = {d: f"fewer than {MODIS_MIN_DISTRICT} usable composites" for d in SLUG_LIST if d not in ok}
    return grp.mean()[ok].to_dict(), notes, n.to_dict()


def _smap_year(year):
    values, ns, notes = {}, {}, {}
    for d in SLUG_LIST:
        if d not in LIVE_DISTRICTS:
            notes[d] = "not assessed: SMAP for 64 districts did not finish (5 live districts only)"
            continue
        s = _smap(d).dropna(subset=["sm_rootzone"])
        s = s[s.date.dt.year == year]
        ns[d] = int(len(s))
        if len(s) >= SMAP_MIN_DAYS:
            values[d] = float(s.sm_rootzone.mean())
    return values, notes, ns


def _w2_values(entry, year, season, prov):
    season = season or "rabi"
    if season not in SEASONS:
        raise ValueError(f"season must be one of {list(SEASONS)}")
    ind = entry["key"][3:]
    t = _w2()
    s = t[(t.indicator == ind) & (t.season_year == year) & (t.season == season)]
    values, notes, ns = {}, {}, {}
    for r in s.itertuples():
        ns[r.district] = None if pd.isna(r.n) else int(r.n)
        if r.status == "ok" and pd.notna(r.value):
            values[r.district] = float(r.value)
        else:
            notes[r.district] = str(r.status)
    for d in SLUG_LIST:
        if d not in LIVE_DISTRICTS:
            notes[d] = "not assessed: W2 indicators exist for the five live districts only"
    note = ""
    if not values:
        note = (f"no value for {year}: this indicator has data for "
                f"{entry['available_years'][0]}-{entry['available_years'][-1]}")
    return _response(entry, year, season, _rows(values, notes, ns), prov, entry["caveats"], note)

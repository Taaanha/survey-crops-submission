"""Relative vulnerability zones for the passport fields (W5 follow-up, Layer 1).

Only data already in the repo is used:
  low-lying       = the lowest third of the NASADEM 30 m elevations of the whole tile;
  flood-exposed   = the upper third of the T3b flood-history layer (open-water days, upper bound) among
                    the pixels that were observed, and at least one day (needs data/raw/opera_layers);
  both            = the overlap of the two, the flood layer re-sampled to the NASADEM pixels (nearest).
Every zone is a relative ranking within the tile: our choice, not a cited vulnerability class. Cold-prone,
erosion and water-stress zones stay "not assessed" with their reasons. Missing is NaN inside and None in
the output, never 0. No AI, no network."""

import json
import os

import numpy as np

from sat_layers.provenance import PROVENANCE

LABEL = "relative ranking within this tile, our choice, not a cited vulnerability class"
NOT_IN_REPO = "not assessed (layer not in the repo)"
OPERA_URL = "https://podaac.jpl.nasa.gov/dataset/OPERA_L3_DSWX-S1_V1"
OPERA_DATASET = "NASA OPERA DSWx-HLS and DSWx-S1 surface water (T3b per-pixel flood history)"
OBSERVED_WITH_DAYS = ("ok", "still wet at series end", "drain not confirmed")
LOW_SHARE = 100.0 / 3          # the lowest third
HIGH_PCT = 200.0 / 3           # the cut of the upper third


# ----------------------------------------------------------------------------------- pure grid functions

def lowest_third_cut(tile_elev):
    """The elevation (m) at the lowest third of the tile's finite pixels, and how many pixels that
    takes in practice (whole-metre elevations tie at the cut, so the share can exceed a third). None when
    the tile is empty or flat, because then there is no lowest third."""
    e = np.asarray(tile_elev, float)
    fin = e[np.isfinite(e)]
    if fin.size == 0 or fin.min() == fin.max():
        return None
    cut = float(np.percentile(fin, LOW_SHARE))
    n = int((fin <= cut).sum())
    return {"cut_m": cut, "n_pixels": int(fin.size), "n_flagged": n, "share_of_tile": n / fin.size}


def low_lying(elev, cut_m):
    """1.0 where elevation <= cut, 0.0 where above, NaN where elevation is missing."""
    e = np.asarray(elev, float)
    return np.where(np.isfinite(e), (e <= cut_m).astype(float), np.nan)


def flood_days(days, status):
    """Open-water days per pixel with unknown kept unknown: 0 only where the pixel was observed and had
    no event; the stored days where there is an event (or a still-wet / unconfirmed drain) and a value;
    NaN for 'no observations', 'too few observations', and for a status with no stored value (-1)."""
    d = np.asarray(days, float)
    st = np.asarray(status, dtype=object)
    out = np.full(d.shape, np.nan)
    out[st == "no event"] = 0.0
    has = np.isin(st, OBSERVED_WITH_DAYS) & (d >= 0)
    out[has] = d[has]
    return out


def flood_cut(tile_days):
    """The cut of the upper third of the observed pixels, and how many pixels are flagged. None when
    no pixel was observed. A pixel is exposed when its days are at or above the cut AND above 0, so
    that a mostly dry tile (cut = 0) flags only pixels that really had open water."""
    d = np.asarray(tile_days, float)
    obs = d[np.isfinite(d)]
    if obs.size == 0:
        return None
    cut = float(np.percentile(obs, HIGH_PCT))
    n = int(((obs >= cut) & (obs > 0)).sum())
    return {"cut_days": cut, "n_observed": int(obs.size), "n_flagged": n, "share_of_observed": n / obs.size}


def flood_exposed(days, cut_days):
    """1.0 exposed, 0.0 not exposed, NaN where the pixel was not observed."""
    d = np.asarray(days, float)
    return np.where(np.isfinite(d), ((d >= cut_days) & (d > 0)).astype(float), np.nan)


def overlap(a, b):
    """Both flagged. Three-valued AND: 1 when both are 1; 0 when either is a known 0; else unknown."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape:
        raise ValueError("the two zone grids must have the same shape")
    out = np.full(a.shape, np.nan)
    out[(a == 0) | (b == 0)] = 0.0
    out[(a == 1) & (b == 1)] = 1.0
    return out


def sample_nearest(grid, rows, cols):
    """grid[rows, cols] with NaN wherever the index falls outside the grid."""
    g = np.asarray(grid, float)
    r, c = np.asarray(rows), np.asarray(cols)
    ok = (r >= 0) & (r < g.shape[0]) & (c >= 0) & (c < g.shape[1])
    out = np.full(r.shape, np.nan)
    out[ok] = g[r[ok], c[ok]]
    return out


def summary(zone):
    z = np.asarray(zone, float)
    known = int(np.isfinite(z).sum())
    flagged = int((z == 1).sum())
    return {"n_flagged": flagged, "n_known": known, "n_unknown": int(z.size - known),
            "share_of_known": None if known == 0 else flagged / known}


def to_lists(zone):
    """Nested lists of 1 / 0 / None for JSON."""
    return [[None if not np.isfinite(v) else int(v) for v in row] for row in np.asarray(zone, float)]


# ------------------------------------------------------------------------------------- the passport block

def _zone(key, name, status, reason, dataset, url, grid=None, **extra):
    out = {"key": key, "name": name, "label": LABEL, "status": status, "reason": reason, "dataset": dataset,
           "source_url": url, "grid": grid, "value": None, "caveats": []}
    out.update(extra)
    return out


def _not_assessed(key, name, reason, prov_key):
    p = PROVENANCE[prov_key]
    return _zone(key, name, "not assessed", reason, p["dataset"], p["source_url"])


def _read_flood_tile(field, layers_dir):
    """(whole-tile flood days with unknown as NaN, manifest, None) or (None, None, reason)."""
    base = os.path.join(layers_dir, f"layers_manifest_{field['district']}.json")
    tif = os.path.join(layers_dir, f"{field['district']}_open_water.tif")
    if not (os.path.exists(base) and os.path.exists(tif)):
        return None, None, NOT_IN_REPO
    try:
        from common import proj_guard
        proj_guard.apply()
        import rasterio
        from field_profile.events import STATUS
        with open(base, encoding="utf-8") as fh:
            man = json.load(fh)
        with rasterio.open(tif) as ds:
            names = list(ds.descriptions)
            days = ds.read(names.index("inundation_days_max") + 1).astype(float)
            codes = ds.read(names.index("status") + 1)
    except (ImportError, RuntimeError, ValueError, OSError, KeyError) as err:
        return None, None, f"not assessed (the flood-history layers could not be read: {err})"
    labels = np.array(list(STATUS) + [""], dtype=object)
    status = labels[np.where((codes >= 0) & (codes < len(STATUS)), codes, len(STATUS))]
    return flood_days(days, status), man, None


def _flood_rowcol(man, lats, lons):
    """Row and column of the flood tile for each (lat, lon) pixel centre (nearest pixel by floor)."""
    from rasterio.warp import transform
    g = man["grid"]
    la, lo = np.meshgrid(lats, lons, indexing="ij")
    xs, ys = transform("EPSG:4326", g["crs"], lo.ravel().tolist(), la.ravel().tolist())
    a, _, c, _, e, f = g["transform"]
    cols = np.floor((np.array(xs) - c) / a).astype(int).reshape(la.shape)
    rows = np.floor((np.array(ys) - f) / e).astype(int).reshape(la.shape)
    return rows, cols


def zones_block(field, half, data_dir, layers_dir):
    """The 'vulnerability_zones' block of the passport of one demo field: a (2*half+1)-pixel window of
    each zone, the cut computed from the whole tile (not from the window), everything labelled."""
    from map_layers import passport as P            # lazy: passport imports this module
    elev, lats, lons = P._tile(field["tile"], data_dir)
    row, col = P._centre(lats, lons, field["lat"], field["lon"])
    nas = PROVENANCE["nasadem"]
    pixel = "1 arc-second NASADEM pixels (about 30 m); row 0 is the northern edge."

    cut = lowest_third_cut(elev)
    zones = {}
    low_win = None
    if cut is None:
        zones["low_lying"] = _zone("low_lying", "Low-lying (lowest third of the tile)", "not assessed",
                                   "the tile's elevation is flat or empty, so it has no lowest third",
                                   nas["dataset"], nas["source_url"])
    else:
        low_win = low_lying(P._window(elev, row, col, half), cut["cut_m"])
        zones["low_lying"] = _zone(
            "low_lying", "Low-lying (lowest third of the tile)", "assessed", "", nas["dataset"],
            nas["source_url"], to_lists(low_win), pixel_size_m=30, tile=field["tile"],
            cut_m=cut["cut_m"], tile_pixels=cut["n_pixels"], share_of_tile=cut["share_of_tile"],
            window_summary=summary(low_win), unit="1 = in the lowest third, 0 = not, None = no elevation",
            caveats=[pixel, "The cut is the elevation at the lowest third of all pixels of this tile; "
                     "elevations are whole metres, so ties can put more than a third in the zone "
                     "(share_of_tile says how many)."])

    fdays, man, why = _read_flood_tile(field, layers_dir)
    fwin = None
    if fdays is None:
        zones["flood_exposed"] = _zone("flood_exposed", "Flood-exposed (upper third of the flood history)",
                                       "not assessed", why, OPERA_DATASET, OPERA_URL)
        zones["low_and_flood_exposed"] = _zone(
            "low_and_flood_exposed", "Low-lying and flood-exposed", "not assessed",
            "needs the flood-exposed zone, which is not assessed: " + why, nas["dataset"], nas["source_url"])
    else:
        fcut = flood_cut(fdays)
        from field_profile.profile import _pixel
        hit = _pixel(man, field["lat"], field["lon"])
        if fcut is None or hit is None:
            why = ("no pixel of the flood-history tile was observed" if fcut is None
                   else "the field is outside the 20 km flood-history box")
            zones["flood_exposed"] = _zone("flood_exposed", "Flood-exposed (upper third of the flood history)",
                                           "not assessed", f"not assessed ({why})", OPERA_DATASET, OPERA_URL)
            zones["low_and_flood_exposed"] = _zone(
                "low_and_flood_exposed", "Low-lying and flood-exposed", "not assessed",
                "needs the flood-exposed zone, which is not assessed: " + why, nas["dataset"], nas["source_url"])
        else:
            exposed_tile = flood_exposed(fdays, fcut["cut_days"])
            fwin = P._window(exposed_tile, hit[0], hit[1], half)
            zones["flood_exposed"] = _zone(
                "flood_exposed", "Flood-exposed (upper third of the flood history)", "assessed", "",
                OPERA_DATASET, OPERA_URL, to_lists(fwin), pixel_size_m=30, cut_days=fcut["cut_days"],
                tile_observed_pixels=fcut["n_observed"], share_of_observed=fcut["share_of_observed"],
                window_summary=summary(fwin), built=man["built"],
                unit="1 = open water on more days than the cut (and at least 1 day), 0 = not, None = not observed",
                caveats=["Days under open water 1 Jul-30 Nov 2024, an upper bound (days between two clear "
                         "dates count towards the maximum); one season only, so this is a relative ranking "
                         "of 2024, not a flood-frequency class.",
                         "0 only where the pixel was observed with no open-water event; a pixel with no or too "
                         "few observations is None, never 0.",
                         "When most of the tile stayed dry the cut is 0 days and every pixel with at least one "
                         "day is exposed."])
            if low_win is None:
                zones["low_and_flood_exposed"] = _zone(
                    "low_and_flood_exposed", "Low-lying and flood-exposed", "not assessed",
                    "needs the low-lying zone, which is not assessed", nas["dataset"], nas["source_url"])
            else:
                dlat, dlon = lats[1] - lats[0], lons[1] - lons[0]
                wl = lats[0] + dlat * np.arange(row - half, row + half + 1)
                wo = lons[0] + dlon * np.arange(col - half, col + half + 1)
                rows, cols = _flood_rowcol(man, wl, wo)
                both = overlap(low_win, sample_nearest(exposed_tile, rows, cols))
                zones["low_and_flood_exposed"] = _zone(
                    "low_and_flood_exposed", "Low-lying and flood-exposed", "assessed", "",
                    nas["dataset"] + " + " + OPERA_DATASET, nas["source_url"], to_lists(both),
                    pixel_size_m=30, window_summary=summary(both), also_cites=OPERA_URL,
                    unit="1 = in both zones, 0 = not in both, None = unknown",
                    caveats=[pixel, "The flood-exposed zone is read at the nearest flood-history pixel centre "
                             "for each NASADEM pixel (the two 30 m grids are not aligned), so edges are "
                             "approximate."])

    zones["cold_prone"] = _not_assessed(
        "cold_prone", "Cold-prone", "no night-minimum temperature exists below the district point: POWER "
        "gives one value per 0.5 degree cell and the ECOSTRESS surface-temperature layer was not delivered "
        "(docs/w1b_data_status.csv), so a cold zone inside the field cannot be drawn", "ecostress")
    zones["erosion"] = _not_assessed(
        "erosion", "Erosion", "needs field-level bare-soil days and a cited erosion model; the repo has "
        "slope (a relative ranking only) and district-level bare days, and no cited erosion factors, so "
        "no zone is drawn", "nasadem")
    zones["water_stress"] = _not_assessed(
        "water_stress", "Water stress", "the SMAP pixel grid is not in the repo (one 9 km pixel is wider "
        "than this window) and the ECOSTRESS evaporation units are unresolved, so no water-stress zone is "
        "drawn", "smap_live")
    return {"label": LABEL, "status": "assessed" if low_win is not None or fwin is not None else "not assessed",
            "half_width": int(half), "zones": zones,
            "note": "Zones rank pixels against the rest of the same tile; they are not thresholds from a "
                    "paper and not a vulnerability class."}

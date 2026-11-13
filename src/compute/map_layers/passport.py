"""Field Passport (W5, Layer 1): what is known about one demo field, each layer on its own real pixel
grid so the uncertainty is visible (a 30 m pixel is small, a 9 km SMAP pixel is not).

Only layers that exist in the repo are drawn: the NASADEM 30 m tiles, and the T3b flood-history
layers when data/raw/opera_layers exists on the machine. Everything else is "not assessed" with the
reason, and its pixel size is still stated. Missing pixels are None, never 0. No AI, no network."""

import json
import os

import numpy as np

from map_layers import zones
from sat_layers.provenance import PROVENANCE

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DATA_DIR = os.path.join(ROOT, "data", "processed")
LAYERS_DIR = os.path.join(ROOT, "data", "raw", "opera_layers")
NODATA = -32768
LOCATION_SOURCE = ("Google Maps place pin for the research station, plot picked on Esri World Imagery "
                   "(team field record, web/app/index.html)")
RECORD_NOTE = ("The field's location is the team's field record, not NASA data; the layers below are "
               "NASA data for the 30 m pixels around that point.")
FIELDS = (
    {"id": "CUM-ARF-01", "name": "BARI Agricultural Research Field", "lat": 23.47051, "lon": 91.15637,
     "district": "cumilla", "tile": "cumilla"},
    {"id": "CUM-BRRI-02", "name": "BRRI Paddy Cultivation Field", "lat": 23.46915, "lon": 91.15880,
     "district": "cumilla", "tile": "cumilla"},
)
OPERA_URL = "https://podaac.jpl.nasa.gov/dataset/OPERA_L3_DSWX-S1_V1"


def demo_fields():
    """The demo fields (id, name, lat, lon, district) with where their location comes from."""
    return [{k: f[k] for k in ("id", "name", "lat", "lon", "district")}
            | {"location_source": LOCATION_SOURCE, "record_note": RECORD_NOTE} for f in FIELDS]


def _field(field_id):
    for f in FIELDS:
        if f["id"] == field_id:
            return f
    raise KeyError(f"unknown demo field {field_id!r}; known: {[f['id'] for f in FIELDS]}")


def _tile(name, data_dir):
    z = np.load(os.path.join(data_dir, f"nasadem_30m_{name}.npz"))
    elev, lats, lons = z["elev_m"].astype(float), z["lats"], z["lons"]
    elev[elev == NODATA] = np.nan
    if lats[0] < lats[-1]:                      # make row 0 the northern edge
        elev, lats = elev[::-1], lats[::-1]
    return elev, lats, lons


def _window(arr, row, col, half):
    """(2*half+1) square around (row, col); outside the tile is NaN."""
    n = 2 * half + 1
    out = np.full((n, n), np.nan)
    r0, c0 = row - half, col - half
    r1, c1 = max(r0, 0), max(c0, 0)
    r2, c2 = min(row + half + 1, arr.shape[0]), min(col + half + 1, arr.shape[1])
    if r2 > r1 and c2 > c1:
        out[r1 - r0:r2 - r0, c1 - c0:c2 - c0] = arr[r1:r2, c1:c2]
    return out


def _listed(grid):
    return [[None if not np.isfinite(v) else float(v) for v in row] for row in grid]


def _centre(lats, lons, lat, lon):
    row, col = int(np.argmin(abs(lats - lat))), int(np.argmin(abs(lons - lon)))
    if not (lats.min() - 1e-3 <= lat <= lats.max() + 1e-3 and lons.min() - 1e-3 <= lon <= lons.max() + 1e-3):
        raise ValueError("the field is outside the elevation tile")
    return row, col


def elevation_window(tile, lat, lon, half_width=7, data_dir=DATA_DIR):
    """Elevation (m) of the 30 m pixels around (lat, lon); row 0 is the northern edge."""
    elev, lats, lons = _tile(tile, data_dir)
    row, col = _centre(lats, lons, lat, lon)
    return {"grid": _listed(_window(elev, row, col, half_width)), "row": row, "col": col}


def slope_window(tile, lat, lon, half_width=7, data_dir=DATA_DIR):
    """Slope (degrees) derived from the 30 m elevation by finite differences; pixel spacing is
    1 arc-second: 30.9 m north-south and 28.4 m east-west at this latitude."""
    elev, lats, lons = _tile(tile, data_dir)
    row, col = _centre(lats, lons, lat, lon)
    dy = abs(lats[0] - lats[1]) * 111_320.0
    dx = abs(lons[1] - lons[0]) * 111_320.0 * np.cos(np.radians(lat))
    big = _window(elev, row, col, half_width + 1)
    gy, gx = np.gradient(big, dy, dx)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))[1:-1, 1:-1]
    return {"grid": _listed(slope)}


def _layer(key, label, pixel_m, status, reason, dataset, url, unit, grid=None, half=None,
           caveats=(), extra=None):
    out = {"key": key, "label": label, "pixel_size_m": pixel_m, "status": status, "reason": reason,
           "dataset": dataset, "source_url": url, "unit": unit, "grid": grid,
           "extent_m": None if half is None else (2 * half + 1) * pixel_m, "caveats": list(caveats)}
    out.update(extra or {})
    return out


def _flood_layer(f, half, layers_dir):
    """T3b flood history (open-water days, 30 m) when its GeoTIFF layers are on this machine."""
    label = "Flood history: days under open water, 1 Jul-30 Nov 2024 (upper bound)"
    base = dict(key="opera_inundation_days_30m", label=label, pixel_m=30,
                dataset="NASA OPERA DSWx-HLS and DSWx-S1 surface water (T3b per-pixel flood history)",
                url=OPERA_URL, unit="days")
    manifest = os.path.join(layers_dir, f"layers_manifest_{f['district']}.json")
    tif = os.path.join(layers_dir, f"{f['district']}_open_water.tif")
    if not (os.path.exists(manifest) and os.path.exists(tif)):
        return _layer(base["key"], label, 30, "not assessed",
                      "the T3b flood-history layers are not in the repo (data/raw/opera_layers is not in "
                      "git); build them with the T3b code or download them from the data repo",
                      base["dataset"], base["url"], "days")
    try:
        from common import proj_guard
        proj_guard.apply()   # a PostgreSQL PROJ database must not shadow rasterio's
        import rasterio
        from rasterio.windows import Window
        from field_profile.profile import _pixel
        with open(manifest, encoding="utf-8") as fh:
            man = json.load(fh)
        hit = _pixel(man, f["lat"], f["lon"])
        if hit is None:
            raise ValueError("outside the 20 km flood-history box")
        row, col = hit
        with rasterio.open(tif) as ds:
            band = list(ds.descriptions).index("inundation_days_max") + 1
            win = Window(col - half, row - half, 2 * half + 1, 2 * half + 1)
            data = ds.read(band, window=win, boundless=True, fill_value=-1).astype(float)
            sband = list(ds.descriptions).index("status") + 1
            codes = ds.read(sband, window=win, boundless=True, fill_value=-1)
    except (ImportError, RuntimeError, ValueError) as err:   # RuntimeError: proj_guard without rasterio
        return _layer(base["key"], label, 30, "not assessed", f"flood-history layers could not be read: {err}",
                      base["dataset"], base["url"], "days")
    data[data < 0] = np.nan
    from field_profile.events import STATUS
    status_grid = [[STATUS[int(c)] if c >= 0 else None for c in row] for row in codes]
    return _layer(base["key"], label, 30, "assessed", "", base["dataset"], base["url"], "days",
                  _listed(data), half, [
                      "Open water only (the flood signal); standing paddy also looks like water in the "
                      "'any water' view, which is context only and not drawn here.",
                      "An empty cell is not zero: status_grid says 'no event' (observed, no open water) or why "
                      "there is no value (for example 'no observations').",
                      "Upper bound: the days between two clear satellite dates where the water state "
                      "is not observed count towards the maximum.",
                      "OPERA DSWx scenes exist from 21 Aug 2024 (radar); the window is July-November 2024."],
                  {"built": man["built"], "status_grid": status_grid})


def _not_in_repo(key, label, pixel_m, reason, prov_key):
    p = PROVENANCE[prov_key]
    return _layer(key, label, pixel_m, "not assessed", reason, p["dataset"], p["source_url"], p["units"])


def field_passport(field_id, half_width=7, data_dir=DATA_DIR, layers_dir=LAYERS_DIR):
    """The passport of one demo field: a (2*half_width+1)-pixel square of every layer that is in the
    repo, and 'not assessed' entries (with reasons and pixel sizes) for the rest."""
    f = _field(field_id)
    half = int(half_width)
    if not 1 <= half <= 20:
        raise ValueError("half_width must be between 1 and 20 pixels")
    nasadem = PROVENANCE["nasadem"]
    elev = elevation_window(f["tile"], f["lat"], f["lon"], half, data_dir)
    slope = slope_window(f["tile"], f["lat"], f["lon"], half, data_dir)
    pixel = ("1 arc-second pixels (about 30 m); NASADEM acquisition of 2000. "
             "Row 0 is the northern edge.")
    layers = [
        _layer("nasadem_elevation_30m", "Elevation", 30, "assessed", "", nasadem["dataset"],
               nasadem["source_url"], "m", elev["grid"], half, [pixel]),
        _layer("nasadem_slope_30m", "Slope (derived from the elevation)", 30, "assessed", "",
               nasadem["dataset"], nasadem["source_url"], "degrees", slope["grid"], half,
               ["Slope is a relative ranking only: derived from the 30 m elevation by finite "
                "differences, so surface noise in the DEM shows up as slope on flat land.", pixel]),
        _flood_layer(f, half, layers_dir),
        _not_in_repo("hls_ndvi_30m", "NDVI at 30 m (HLS)", 30,
                     "the HLS pixel files are on Google Drive and not in git; the repo keeps only a "
                     "20 km tile-mean series, which is not a field value", "hls"),
        _not_in_repo("ecostress_et_70m", "Evaporation at 70 m (ECOSTRESS)", 70,
                     "ECOSTRESS evaporation units are unresolved (see docs/w1b_data_status.csv)", "ecostress"),
        _not_in_repo("modis_ndvi_250m", "NDVI at 250 m (MODIS)", 250,
                     "only district means are in the repo; the 250 m pixel files are not", "modis"),
        _not_in_repo("smap_9km", "Root-zone soil moisture at 9 km (SMAP)", 9000,
                     "only the district-point series is in the repo, not the pixel grid; one 9 km pixel "
                     f"is about {int(9000 / ((2 * half + 1) * 30))} times wider than this "
                     f"{(2 * half + 1) * 30} m window", "smap_live"),
    ]
    field = demo_fields()[[x["id"] for x in FIELDS].index(field_id)]
    return {"field": field, "half_width": half, "window_m": (2 * half + 1) * 30, "layers": layers,
            "vulnerability_zones": zones.zones_block(f, half, data_dir, layers_dir)}

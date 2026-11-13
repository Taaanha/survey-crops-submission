"""Field water profile (T3b): map layers on disk and the answer for one field.

write_layers() runs the per-pixel event logic once and saves GeoTIFF layers (open water = the
flood signal; any water = context only) plus a small manifest. field_profile(lat, lon) reads one
pixel and returns the metrics with provenance. Outside the 20 km box the answer is
'not covered', never zeros."""

import datetime as dt
import glob
import json
import math
import os

import numpy as np

from .core import DISTRICT_POINTS, PRODUCTS
from .events import STATUS, load_rules, profile_stack

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_LAYERS_DIR = os.path.join(ROOT, "data", "raw", "opera_layers")
DEFAULT_CACHE_DIR = os.path.join(ROOT, "data", "raw", "opera_layers_hf")
AREA_NOTE = ("Area = a 20 km window around the district point, not the administrative district.")
VIEWS = ("open_water", "any_water")
LABELS = {
    "open_water": "Open water (the flood signal)",
    "any_water": ("Any water, including inundated vegetation and partial water "
                  "(context only: standing paddy also looks like this)"),
}
JRC_LABEL = "JRC Global Surface Water occurrence (non-NASA product, Landsat-based)"
_EPOCH = dt.date(1970, 1, 1)


# ---------------------------------------------------------------- writing

def _write_tif(path, grid, bands, names, dtype, nodata):
    import rasterio
    from rasterio.transform import Affine
    h, w = grid["height"], grid["width"]
    opts = dict(driver="GTiff", height=h, width=w, count=len(bands), dtype=dtype,
                crs=grid["crs"], transform=Affine(*grid["transform"]), nodata=nodata,
                compress="deflate")
    if h >= 256 and w >= 256:
        opts.update(tiled=True, blockxsize=256, blockysize=256)
    with rasterio.open(path, "w", **opts) as dst:
        for i, band in enumerate(bands, 1):
            dst.write(np.asarray(band, dtype=dtype), i)
        dst.descriptions = tuple(names)


def write_layers(district, grid, dates, stack, entries, out_dir, rules=None, jrc=None,
                 jrc_info=None, built=None):
    """Event metrics for every pixel of a class stack [dates, rows, cols] (2 open water,
    1 partial/vegetation water, 0 not water, 255 no observation), saved as GeoTIFF layers in
    out_dir with layers_manifest_<district>.json. entries = per-date dicts with `date`,
    `granules`, `source_urls` (the T3a manifest 'dates'). jrc = optional uint8 [rows, cols]
    occurrence % (255 = no data) with jrc_info {dataset, source_url, licence, retrieved}.
    Returns the manifest path."""
    rules = dict(rules) if rules is not None else load_rules()
    stack = np.asarray(stack)
    if stack.shape != (len(dates), grid["height"], grid["width"]):
        raise ValueError(f"stack shape {stack.shape} does not match dates/grid")
    os.makedirs(out_dir, exist_ok=True)
    files = {}
    for view in VIEWS:
        out = profile_stack(dates, stack, view, rules)
        names = list(out)
        files[view] = f"{district}_{view}.tif"
        _write_tif(os.path.join(out_dir, files[view]), grid, [out[n] for n in names], names,
                   np.int32, -1)
    if jrc is not None:
        files["jrc_occurrence"] = f"{district}_jrc_occurrence.tif"
        _write_tif(os.path.join(out_dir, files["jrc_occurrence"]), grid,
                   [np.asarray(jrc)], ["occurrence_pct"], np.uint8, 255)
    manifest = {
        "district": district, "grid": grid, "rules": rules, "files": files,
        "built": built or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
        "products": PRODUCTS, "area_note": AREA_NOTE,
        "jrc": jrc_info if jrc is not None else None,
        "dates": [{"date": e["date"], "granules": e["granules"],
                   "source_urls": e.get("source_urls", [])} for e in entries],
    }
    path = os.path.join(out_dir, f"layers_manifest_{district}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    if os.path.getsize(path) > 1_000_000:
        raise RuntimeError("layers manifest is over 1 MB")
    return path


# ---------------------------------------------------------------- reading

def _iso(days):
    return None if days < 0 else (_EPOCH + dt.timedelta(days=int(days))).isoformat()


def _opt(v):
    return None if v < 0 else int(v)


def _pixel(manifest, lat, lon):
    from rasterio.warp import transform
    g = manifest["grid"]
    xs, ys = transform("EPSG:4326", g["crs"], [lon], [lat])
    a, _, c, _, e, f = g["transform"]
    col, row = int(math.floor((xs[0] - c) / a)), int(math.floor((ys[0] - f) / e))
    if 0 <= col < g["width"] and 0 <= row < g["height"]:
        return row, col
    return None


def _read_pixel(path, row, col):
    import rasterio
    from rasterio.windows import Window
    with rasterio.open(path) as ds:
        vals = ds.read(window=Window(col, row, 1, 1))[:, 0, 0].tolist()
        return dict(zip(ds.descriptions, vals))


def _metrics(v, view):
    ws, we = v["window_start"], v["window_end"]
    return {
        "label": LABELS[view], "status": STATUS[int(v["status"])],
        "n_events": _opt(v["n_events"]), "n_observed": _opt(v["n_observed"]),
        "first_wet_date": _iso(v["first_wet_date"]), "last_wet_date": _iso(v["last_wet_date"]),
        "first_dry_date": _iso(we), "drain_date": _iso(v["drain_date"]),
        "drain_window": [_iso(ws), _iso(we)] if ws >= 0 else None,
        "gap_days": _opt(v["gap_days"]),
        "inundation_days_min": _opt(v["inundation_days_min"]),
        "inundation_days_max": _opt(v["inundation_days_max"]),
    }


def _km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * math.asin(math.sqrt(a))


def _not_covered(lat, lon, district=None):
    return {"covered": False, "status": "not covered", "district": district, "lat": lat,
            "lon": lon, "area_note": AREA_NOTE,
            "note": "No layers cover this point; nothing is assumed."}


def _answer(manifest, base, district, row, col, lat, lon):
    by_date = {e["date"]: [g for lst in e["granules"].values() for g in lst]
               for e in manifest["dates"]}
    files, metrics, ids = manifest["files"], {}, {}
    for view in VIEWS:
        v = _read_pixel(os.path.join(base, files[view]), row, col)
        metrics[view] = _metrics(v, view)
        m = metrics[view]
        ids[view] = {"last_wet": by_date.get(m["last_wet_date"], []),
                     "first_dry": by_date.get(m["first_dry_date"], [])}
    jrc = {"value_pct": None, "label": JRC_LABEL, "dataset": None, "source_url": None}
    if "jrc_occurrence" in files:
        val = _read_pixel(os.path.join(base, files["jrc_occurrence"]), row, col)["occurrence_pct"]
        info = manifest.get("jrc") or {}
        jrc.update(value_pct=None if val == 255 else int(val), **info)
    datasets = [f"OPERA {p} ({short})" for p, short in manifest["products"].items()]
    if manifest.get("jrc"):
        datasets.append(manifest["jrc"]["dataset"] + " (non-NASA)")
    main = metrics["open_water"]
    return {
        "covered": True, "district": district, "lat": lat, "lon": lon,
        "pixel": {"row": row, "col": col}, "status": main["status"],
        "drain_date": main["drain_date"], "drain_window": main["drain_window"],
        "gap_days": main["gap_days"], "metrics": metrics, "jrc_occurrence": jrc,
        "provenance": {"datasets": datasets, "granule_ids": ids, "retrieved": manifest["built"],
                       "granule_note": "last_wet and first_dry = granules of the dates that "
                                       "bound the drain window"},
        "area_note": AREA_NOTE, "rules": manifest["rules"],
    }


def field_profile(lat, lon, district=None, source="local", layers_dir=None, cache_dir=None):
    """Flood history of the 30 m pixel at (lat, lon): open-water metrics (the flood signal),
    any-water metrics (context only), a JRC occurrence value (non-NASA, labelled), and
    provenance (datasets, granule IDs of the dates around the drain). source 'local' reads
    layers_dir (default data/raw/opera_layers); 'hf' downloads the district's layers from the
    Hugging Face dataset into cache_dir first. Outside the 20 km box or without layers:
    {"covered": False, "status": "not covered"}."""
    if source not in ("local", "hf"):
        raise ValueError("source must be 'local' or 'hf'")
    bases = {}
    if source == "local":
        base = layers_dir or DEFAULT_LAYERS_DIR
        if district:
            candidates = [district]
        else:
            candidates = sorted(os.path.basename(p)[len("layers_manifest_"):-len(".json")]
                                for p in glob.glob(os.path.join(base, "layers_manifest_*.json")))
        bases = {d: base for d in candidates}
    else:
        from . import hf
        cache = cache_dir or DEFAULT_CACHE_DIR
        if district:
            candidates = [district]
        else:
            near = sorted((_km(lat, lon, *pt), d) for d, pt in DISTRICT_POINTS.items())
            candidates = [d for km, d in near if km <= 25]
        for d in candidates:
            bases[d] = hf.download_layers(d, cache)  # the folder the downloader reports
    for d in candidates:
        base = bases[d]
        mpath = os.path.join(base, f"layers_manifest_{d}.json")
        if not os.path.exists(mpath):
            continue
        with open(mpath, encoding="utf-8") as f:
            manifest = json.load(f)
        hit = _pixel(manifest, lat, lon)
        if hit:
            return _answer(manifest, base, d, hit[0], hit[1], lat, lon)
    return _not_covered(lat, lon, district)
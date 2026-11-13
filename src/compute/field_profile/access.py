"""OPERA DSWx access for the field water profile (T3a): coverage queries and water stacks.

Network code. Credentials come from .env / the environment (EARTHDATA_TOKEN) and are
never printed. Only the district window is read (HTTPS range requests through a WarpedVRT),
never whole tiles. Raw per-granule windows are cached OUTSIDE git (out_dir, data/raw/ is
gitignored); the manifest written to data/processed/ is small and has no pixels."""

import datetime as dt
import json
import os
from collections import Counter

import numpy as np

from .core import (NO_OBS, NOT_WATER, OPEN_WATER, PARTIAL_WATER, PRODUCTS, district_grid,
                   encode_hls, encode_s1, merge_water, validate_manifest)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MANIFEST_DIR = os.path.join(ROOT, "data", "processed")
S1_AREA_CACHE = os.path.join(ROOT, "cache", "dswx_area")  # written by scripts/fetch_dswx.py --area
ENCODERS = {"DSWx-HLS": encode_hls, "DSWx-S1": encode_s1}
CLASSES_REFERENCE = "data/reference/opera_classes.csv"


def _parse_id(granule_id):
    """OPERA_L3_DSWx-S1_T46QCL_20240821T120455Z_20251107T032635Z_S1A_30_v1.0
    -> (tile, sensing time, production time, UTC date)."""
    parts = granule_id.split("_")
    tile, sensing, production = parts[3], parts[4], parts[5]
    return tile, sensing, production, f"{sensing[:4]}-{sensing[4:6]}-{sensing[6:8]}"


def _search(product, grid, start, end):
    """Granule records for one product over the grid box; the latest production of each
    (tile, sensing time) only. No downloads."""
    import earthaccess
    found = earthaccess.search_data(short_name=PRODUCTS[product],
                                    bounding_box=tuple(grid["bbox_lonlat"]),
                                    temporal=(start, end + "T23:59:59Z"))
    best = {}
    for g in found:
        gid = g["meta"]["native-id"]
        tile, sensing, production, date = _parse_id(gid)
        if not (start <= date <= end):
            continue
        links = [u for u in g.data_links() if u.endswith("_B01_WTR.tif")]
        if not links:
            continue
        attrs = {a["Name"]: a["Values"][0] for a in g["umm"].get("AdditionalAttributes", [])
                 if a.get("Values")}
        rec = {"id": gid, "product": product, "tile": tile, "date": date, "sensing": sensing,
               "production": production, "url": links[0],
               "tile_cloud_coverage": attrs.get("CLOUD_COVERAGE") or attrs.get("CloudCover")}
        kept = best.get((tile, sensing))
        if kept is None or production > kept["production"]:
            best[(tile, sensing)] = rec
    return sorted(best.values(), key=lambda r: (r["sensing"], r["tile"]))


def _week_start(date):
    d = dt.date.fromisoformat(date)
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def opera_coverage(district, start, end):
    """Which OPERA granules (DSWx-HLS and DSWx-S1) touch the district's 20 km box between
    start and end (YYYY-MM-DD, inclusive)? Metadata only, nothing is downloaded.
    Returns {district, start, end, bbox_lonlat, products: {name: {short_name, n_granules,
    first_date, last_date, per_week, per_date, granules}}}."""
    grid = district_grid(district)
    out = {"district": district, "start": start, "end": end,
           "bbox_lonlat": grid["bbox_lonlat"], "products": {}}
    for product in PRODUCTS:
        recs = _search(product, grid, start, end)
        dates = sorted(r["date"] for r in recs)
        out["products"][product] = {
            "short_name": PRODUCTS[product], "n_granules": len(recs),
            "first_date": dates[0] if dates else None, "last_date": dates[-1] if dates else None,
            "per_week": dict(sorted(Counter(_week_start(d) for d in dates).items())),
            "per_date": dict(sorted(Counter(dates).items())),
            "granules": recs,
        }
    return out


def _login():
    """Earthdata login from .env / environment; returns an authenticated HTTPS file system."""
    import earthaccess
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
    if not (os.environ.get("EARTHDATA_TOKEN")
            or (os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"))):
        raise RuntimeError("Earthdata credentials are not set (EARTHDATA_TOKEN in .env)")
    if not earthaccess.login(strategy="environment").authenticated:
        raise RuntimeError("earthaccess could not authenticate")
    return earthaccess.get_fsspec_https_session()


def _read_window(fs, url, grid):
    """The district grid's window of one WTR band, nearest neighbour, 255 outside the tile."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.enums import Resampling
    from rasterio.transform import Affine
    from rasterio.vrt import WarpedVRT
    with rasterio.open(fs.open(url)) as ds:
        with WarpedVRT(ds, crs=CRS.from_string(grid["crs"]), transform=Affine(*grid["transform"]),
                       width=grid["width"], height=grid["height"],
                       resampling=Resampling.nearest, src_nodata=255, nodata=255) as vrt:
            return vrt.read(1)


def _raw_window(rec, district, grid, raw_dir, state):
    """Raw WTR codes of one granule on the district grid: from the cache, else read."""
    path = os.path.join(raw_dir, rec["id"] + ".npz")
    if os.path.exists(path):
        return np.load(path)["wtr"]
    shared = os.path.join(S1_AREA_CACHE, district, rec["id"] + ".npz")
    if rec["product"] == "DSWx-S1" and os.path.exists(shared):  # same grid, checked by shape
        arr = np.load(shared)["wtr"]
        if arr.shape == (grid["height"], grid["width"]):
            np.savez_compressed(path, wtr=arr)
            return arr
    if "fs" not in state:
        state["fs"] = _login()
    arr = _read_window(state["fs"], rec["url"], grid)
    np.savez_compressed(path, wtr=arr)
    return arr


def _shares(arr):
    n = arr.size
    return {"open_water": round(float((arr == OPEN_WATER).sum() / n), 4),
            "partial_water": round(float((arr == PARTIAL_WATER).sum() / n), 4),
            "not_water": round(float((arr == NOT_WATER).sum() / n), 4),
            "no_obs": round(float((arr == NO_OBS).sum() / n), 4)}

def build_water_stack(district, start, end, out_dir, manifest_dir=None):
    """Builds the per-date water stack for the district box and writes it plus a manifest.
    Stack: <out_dir>/<district>/water_stack_<start>_<end>.npz with `dates` (YYYY-MM-DD, UTC)
    and `water` (uint8 [dates, rows, cols]: 1 water, 0 not water, 255 no observation).
    Manifest: <manifest_dir or data/processed>/field_profile_manifest_<district>.json (dates,
    granule IDs and source URLs per date, grid, per-date shares by product and merged).
    Returns (stack_path, manifest_path)."""
    grid = district_grid(district)
    base = os.path.join(out_dir, district)
    raw_dir = os.path.join(base, "raw_windows")
    os.makedirs(raw_dir, exist_ok=True)
    records = []
    for product in PRODUCTS:
        records += _search(product, grid, start, end)
    by_date = {}
    for rec in records:
        by_date.setdefault(rec["date"], []).append(rec)

    state, dates, layers, entries, failed = {}, [], [], [], []
    for date in sorted(by_date):
        parts, used, per_product = [], {p: [] for p in PRODUCTS}, {}
        for product in PRODUCTS:
            encoded = []
            for rec in [r for r in by_date[date] if r["product"] == product]:
                try:
                    raw = _raw_window(rec, district, grid, raw_dir, state)
                except Exception as err:  # one bad granule must not stop the build
                    failed.append({"id": rec["id"], "error": type(err).__name__})
                    continue
                encoded.append(ENCODERS[product](raw))
                used[product].append(rec)
            if encoded:
                merged_product = merge_water(*encoded)
                per_product[product] = _shares(merged_product)
                parts.append(merged_product)
        if not parts:
            continue
        merged = merge_water(*parts)
        dates.append(date)
        layers.append(merged)
        entries.append({
            "date": date,
            "granules": {p: [r["id"] for r in used[p]] for p in PRODUCTS},
            "source_urls": [r["url"] for p in PRODUCTS for r in used[p]],
            "shares": {"merged": _shares(merged), **per_product},
        })

    os.makedirs(base, exist_ok=True)
    stack_path = os.path.join(base, f"water_stack_{start}_{end}.npz")
    np.savez_compressed(stack_path, dates=np.array(dates), water=np.stack(layers))
    manifest = {
        "district": district, "start": start, "end": end,
        "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "grid": grid, "classes_reference": CLASSES_REFERENCE,
        "encoding": {"2": "open water", "1": "inundated vegetation / partial water",
                     "0": "not water", "255": "no observation"},        "products": {p: PRODUCTS[p] for p in PRODUCTS},
        "stack_file": os.path.relpath(stack_path, ROOT) if stack_path.startswith(ROOT) else stack_path,
        "failed_granules": failed, "dates": entries,
    }
    problems = validate_manifest(manifest)
    if problems:
        raise RuntimeError("manifest invalid: " + "; ".join(problems[:5]))
    mdir = manifest_dir or MANIFEST_DIR
    os.makedirs(mdir, exist_ok=True)
    manifest_path = os.path.join(mdir, f"field_profile_manifest_{district}.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    if os.path.getsize(manifest_path) > 1_000_000:
        raise RuntimeError("manifest is over 1 MB")
    return stack_path, manifest_path

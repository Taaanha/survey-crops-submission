"""One-off (T3b): make the Feni river fixture's position info match its new window."""
import _proj  # noqa: F401  PROJ guard: keep first (before rasterio / pyproj)
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import district_grid  # noqa: E402
from rasterio.warp import transform  # noqa: E402

META = os.path.join(ROOT, "tests", "fixtures", "field_profile", "feni_river_meta.json")
meta = json.load(open(META, encoding="utf-8"))
print("old grid key:", meta.get("grid"))
print("old origin key:", meta.get("window_origin_rowcol_in_district_grid"))
print("note:", meta.get("note"))

r0, c0, n = 462, 462, 50
g = district_grid("feni")
res, left, top = g["transform"][0], g["transform"][2], g["transform"][5]
xl, xr = left + c0 * res, left + (c0 + n) * res
yt, yb = top - r0 * res, top - (r0 + n) * res
lons, lats = transform(g["crs"], "EPSG:4326", [xl, xr, xl, xr], [yb, yb, yt, yt])
meta["grid"] = {"crs": g["crs"], "transform": [res, 0.0, xl, 0.0, -res, yt], "width": n,
                "height": n, "res": res, "bbox_lonlat": [min(lons), min(lats), max(lons), max(lats)]}
meta["window_origin_rowcol_in_district_grid"] = [r0, c0]
meta.pop("window_origin_row_col", None)
json.dump(meta, open(META, "w", encoding="utf-8"), indent=1)
print("fixed. new origin:", [r0, c0])
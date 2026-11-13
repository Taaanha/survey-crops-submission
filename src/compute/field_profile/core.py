"""Pure parts of the field water profile: class encoding, merging, grid, manifest check.

Encoding of every pixel on every date (T3b):
  2 = open water (the flood signal)
  1 = inundated vegetation / partial water (context only: standing Aman paddy also looks like this)
  0 = not water
  255 = no observation
Class codes come from the OPERA product specifications, cited row by row in
data/reference/opera_classes.csv (HLS: JPL D-107395 Rev B; S1: JPL D-108761 Rev A,
Table 4-1 in both)."""

import numpy as np

OPEN_WATER, PARTIAL_WATER, NOT_WATER, NO_OBS = 2, 1, 0, 255

# DSWx-HLS WTR: 0 not water, 1 open water, 2 partial surface water, 252 snow/ice,
# 253 cloud/shadow, 254 ocean masked, 255 fill.
_HLS = {0: NOT_WATER, 1: OPEN_WATER, 2: PARTIAL_WATER, 252: NO_OBS, 253: NO_OBS,
        254: NO_OBS, 255: NO_OBS}
# DSWx-S1 WTR: 0 not water, 1 open water, 3 inundated vegetation, 250 HAND masked
# (ground too high for surface water; treatment set by the rule hand_masked_as),
# 251 layover/shadow masked, 255 fill.
_S1 = {0: NOT_WATER, 1: OPEN_WATER, 3: PARTIAL_WATER, 251: NO_OBS, 255: NO_OBS}
_HAND_CHOICES = {"not_water": NOT_WATER, "no_observation": NO_OBS}

# Strength order for a same-date merge, weakest first.
_ORDER = [NO_OBS, NOT_WATER, PARTIAL_WATER, OPEN_WATER]
_RANK = np.zeros(256, dtype=np.uint8)
for _i, _c in enumerate(_ORDER):
    _RANK[_c] = _i
_CODE = np.array(_ORDER, dtype=np.uint8)

PRODUCTS = {"DSWx-HLS": "OPERA_L3_DSWX-HLS_V1", "DSWx-S1": "OPERA_L3_DSWX-S1_V1"}
AREA_SIZE_M = 20000.0
RES_M = 30.0

# District points (same as src/acquire/fetch_power.DISTRICTS; copied so compute does not import acquire).
DISTRICT_POINTS = {
    "cumilla": (23.4607, 91.1809), "noakhali": (22.8696, 91.0995), "feni": (23.0159, 91.3976),
    "brahmanbaria": (23.9571, 91.1119), "sylhet": (24.8949, 91.8687),
}


def _lookup(raw, table, name):
    raw = np.asarray(raw)
    lut = np.full(256, -1, dtype=np.int16)
    for code, val in table.items():
        lut[code] = val
    out = lut[raw.astype(np.int64)]
    if (out < 0).any():
        bad = sorted(set(np.unique(raw[out < 0]).tolist()))
        raise ValueError(f"unknown {name} class code(s) {bad}")
    return out.astype(np.uint8)


def encode_hls(raw):
    """DSWx-HLS WTR codes -> 2 / 1 / 0 / 255."""
    return _lookup(raw, _HLS, "DSWx-HLS")


def encode_s1(raw, hand_masked_as="not_water"):
    """DSWx-S1 WTR codes -> 2 / 1 / 0 / 255. HAND-masked pixels (code 250) become
    'not_water' (default) or 'no_observation', as set by the project rule hand_masked_as."""
    if hand_masked_as not in _HAND_CHOICES:
        raise ValueError(f"hand_masked_as must be one of {sorted(_HAND_CHOICES)}, got {hand_masked_as!r}")
    table = dict(_S1)
    table[250] = _HAND_CHOICES[hand_masked_as]
    return _lookup(raw, table, "DSWx-S1")


def merge_water(*arrays):
    """Same-date merge of encoded arrays (HLS, S1, several tiles): the strongest class wins
    (open water > partial/vegetation water > not water > no observation). No observation
    only if every input is missing."""
    if not arrays:
        raise ValueError("merge_water needs at least one array")
    first = np.asarray(arrays[0])
    best = np.zeros(first.shape, dtype=np.uint8)
    for a in arrays:
        a = np.asarray(a)
        if a.shape != first.shape:
            raise ValueError(f"shape mismatch {a.shape} vs {first.shape}")
        if not np.isin(a, _ORDER).all():
            raise ValueError("merge_water got a code that is not 2/1/0/255")
        best = np.maximum(best, _RANK[a])
    return _CODE[best]


def district_grid(district, size_m=AREA_SIZE_M, res=RES_M):
    """Fixed 20 km x 20 km box of 30 m pixels around the district point, in the point's
    UTM zone (north), snapped to multiples of 30 m so it lines up with the OPERA MGRS tiles
    (same recipe as scripts/fetch_dswx.area_grid). Returns a JSON-friendly dict:
    crs, transform (a, b, c, d, e, f), width, height, res, bbox_lonlat (W, S, E, N)."""
    from rasterio.warp import transform
    lat, lon = DISTRICT_POINTS[district]
    zone = int((lon + 180) // 6) + 1
    epsg = 32600 + zone
    xs0, ys0 = transform("EPSG:4326", f"EPSG:{epsg}", [lon], [lat])
    x, y = xs0[0], ys0[0]
    n = int(round(size_m / res))
    left = round((x - size_m / 2) / res) * res
    top = round((y + size_m / 2) / res) * res
    xs = [left, left + n * res]
    ys = [top - n * res, top]
    lons, lats = transform(f"EPSG:{epsg}", "EPSG:4326",
                           [xs[0], xs[1], xs[0], xs[1]], [ys[0], ys[0], ys[1], ys[1]])
    return {"crs": f"EPSG:{epsg}", "transform": [res, 0.0, float(left), 0.0, -res, float(top)],
            "width": n, "height": n, "res": res,
            "bbox_lonlat": [min(lons), min(lats), max(lons), max(lats)]}


def validate_manifest(m):
    """List of problems (empty = fine): required keys, one entry per date, and every date
    having at least one granule ID and at least one source URL."""
    problems = []
    for key in ("district", "grid", "classes_reference", "dates"):
        if key not in m:
            problems.append(f"missing key '{key}'")
    seen = set()
    for entry in m.get("dates", []):
        d = entry.get("date", "?")
        if d in seen:
            problems.append(f"duplicate date {d}")
        seen.add(d)
        ids = [g for lst in entry.get("granules", {}).values() for g in lst]
        if not ids:
            problems.append(f"{d}: no granule ID")
        if not entry.get("source_urls"):
            problems.append(f"{d}: no source URL")
    return problems
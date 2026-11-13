"""Quality masks and unit conversions for the W1b rasters. Pure numpy; every rule is named.

OPEN QUESTIONS (listed in docs/PROJECT_STATE.md, to confirm against the product user guides):
- MOD13Q1 pixel_reliability: 0 is taken as "good data" (kept). The AppEEARS API gives the valid
  range (0 to 3) but not the class names.
- HLS Fmask bits: 1 cloud, 2 adjacent to cloud or shadow, 3 cloud shadow, 4 snow or ice are
  treated as "not clear". The AppEEARS API gives the fill value (255) but not the bit meanings."""

import numpy as np

from w1b.products import VALID_RANGE

MOD13_KEEP = (0,)
FMASK_BAD_BITS = (1, 2, 3, 4)
FMASK_FILL = 255


def check_range(arr, lo, hi, name, tolerance=0.01):
    """Raise if more than `tolerance` of the finite values lie outside [lo, hi].
    This catches a raster that still carries its raw integers (scale factor not applied)."""
    a = np.asarray(arr, dtype=float)
    fin = a[np.isfinite(a)]
    if fin.size == 0:
        return
    out = np.mean((fin < lo) | (fin > hi))
    if out > tolerance:
        raise ValueError(f"{name}: {out:.1%} of values are outside [{lo}, {hi}]; "
                         "check that the scale factor was applied")


def mod13_clean(vi, reliability, keep=MOD13_KEEP, name="ndvi"):
    """MOD13Q1 NDVI or EVI (already scaled) -> (array with NaN where not kept, share kept).
    A pixel is kept when its pixel_reliability is in `keep` and the value is inside the valid range."""
    lo, hi = VALID_RANGE[name]
    v = np.asarray(vi, dtype=float)
    rel = np.asarray(reliability, dtype=float)
    good = np.isin(rel, keep) & (v >= lo) & (v <= hi)
    finite = np.isfinite(v)
    out = np.where(good, v, np.nan)
    share = float(good.sum() / finite.sum()) if finite.any() else 0.0
    check_range(v[finite & np.isin(rel, keep)], lo, hi, name)
    return out, share


def fmask_clear(fmask, bad_bits=FMASK_BAD_BITS):
    """True where an HLS Fmask pixel is observed and none of `bad_bits` is set."""
    f = np.asarray(fmask, dtype=float)  # a decoded file may show the fill value 255 as NaN
    ok = np.isfinite(f) & (f != FMASK_FILL)
    f = np.where(ok, f, 0).astype(np.int64)
    for b in bad_bits:
        ok &= ((f >> b) & 1) == 0
    return ok


def ndvi(nir, red):
    """(NIR - red) / (NIR + red); NaN where either is NaN or the sum is not positive."""
    n = np.asarray(nir, dtype=float)
    r = np.asarray(red, dtype=float)
    s = n + r
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(s > 0, (n - r) / np.where(s > 0, s, 1), np.nan)


def hls_ndvi(red, nir, fmask):
    """HLS NDVI from scaled reflectance (0..1) with cloud, shadow and snow pixels set to NaN.
    Landsat HLS (HLSL30) uses B05 as `nir`; Sentinel-2 HLS (HLSS30) uses B8A."""
    check_range(red, 0.0, 1.0, "HLS red reflectance")
    check_range(nir, 0.0, 1.0, "HLS NIR reflectance")
    out = ndvi(nir, red)
    return np.where(fmask_clear(fmask), out, np.nan)


SMAP_VALID = (0.0, 0.9)  # valid range of sm_rootzone / sm_surface in the AppEEARS layer record
# 1 MJ/m2/day of latent heat = 0.408 mm/day of water (FAO-56, Allen et al. 1998, eq. 20: 1/2.45);
# 1 W/m2 sustained for a day = 0.0864 MJ/m2/day.
MM_PER_DAY_PER_WM2 = 0.0864 * 0.408


def mask_range(arr, lo, hi):
    """Copy of `arr` with values outside [lo, hi] (fill values, bad pixels) set to NaN."""
    a = np.asarray(arr, dtype=float)
    return np.where((a >= lo) & (a <= hi), a, np.nan)


def wm2_to_mm_per_day(w_m2):
    """Daily-mean latent heat flux (W/m2, ECOSTRESS ETdaily) -> evaporation in mm of water per day."""
    return np.asarray(w_m2, dtype=float) * MM_PER_DAY_PER_WM2


def find_variable(names, layer):
    """Name in `names` that holds AppEEARS layer `layer` (exact, then suffix, then substring match,
    ignoring case). Raises KeyError listing what exists, so a surprise in the file is visible."""
    low = {n.lower(): n for n in names}
    want = layer.lower()
    for test in (lambda k: k == want, lambda k: k.endswith(want), lambda k: want in k):
        hits = [low[k] for k in low if test(k)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise KeyError(f"layer {layer!r} matches several variables: {hits}")
    raise KeyError(f"layer {layer!r} not found; the file has {sorted(names)}")


def find_coord(names, axis):
    """Name of the 'lat' or 'lon' coordinate among `names` (lat/latitude/y, lon/longitude/x)."""
    options = {"lat": ("lat", "latitude", "y"), "lon": ("lon", "longitude", "x")}[axis]
    low = {n.lower(): n for n in names}
    for o in options:
        if o in low:
            return low[o]
    raise KeyError(f"no {axis} coordinate among {sorted(names)}")


def wrap_longitude(lons):
    """0..360 degrees east -> -180..180 (GRACE-FO grids use 0..360)."""
    lons = np.asarray(lons, dtype=float)
    return np.where(lons > 180, lons - 360, lons)


def kelvin_to_celsius(k):
    """Kelvin -> degrees Celsius (ECOSTRESS LST)."""
    return np.asarray(k, dtype=float) - 273.15

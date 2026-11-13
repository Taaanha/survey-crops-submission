"""Common 0.1 degree analysis grid over Bangladesh and exact district averages on it.

The grid is the GPM IMERG V07 grid (cell centres at x.x5). Arrays are [lat, lon] (or
[time, lat, lon]). A district's weight for a cell is the share of that cell's area inside the
district polygon, computed exactly with shapely in degree space; the cos(latitude) difference
inside one district (under 2%) is ignored and said so in docs/harmonisation.md."""

import numpy as np
from shapely.geometry import box

RES = 0.1
# GES DISC IMERG index ranges used for the Bangladesh subset: lon cells 2678..2729, lat cells 1104..1167
LON_IDX = (2678, 2729)
LAT_IDX = (1104, 1167)


def imerg_axes():
    """(lons, lats): cell-centre coordinates of the Bangladesh box on the IMERG grid."""
    lons = np.round(-179.95 + RES * np.arange(LON_IDX[0], LON_IDX[1] + 1), 2)
    lats = np.round(-89.95 + RES * np.arange(LAT_IDX[0], LAT_IDX[1] + 1), 2)
    return lons, lats


def cell_weights(geom, lons, lats, res=RES):
    """[lat, lon] array: share (0..1) of each cell's area that lies inside `geom`."""
    w = np.zeros((len(lats), len(lons)))
    minx, miny, maxx, maxy = geom.bounds
    half = res / 2
    for i, la in enumerate(lats):
        if la + half <= miny or la - half >= maxy:
            continue
        for j, lo in enumerate(lons):
            if lo + half <= minx or lo - half >= maxx:
                continue
            cell = box(lo - half, la - half, lo + half, la + half)
            if geom.intersects(cell):
                w[i, j] = geom.intersection(cell).area / cell.area
    return w


def district_mean(field, weights):
    """Area-weighted mean of `field` ([lat, lon] or [time, lat, lon]) over a district.

    Missing (NaN) cells are left out and the weights renormalised. Returns (mean, coverage):
    coverage is the share of the district's weight that had data. No data gives (NaN, 0.0)."""
    f = np.asarray(field, dtype=float)
    valid = ~np.isnan(f)
    num = np.nansum(f * weights, axis=(-2, -1))
    seen = (valid * weights).sum(axis=(-2, -1))
    total = weights.sum()
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(seen > 0, num / np.where(seen > 0, seen, 1), np.nan)
        coverage = seen / total if total > 0 else seen * 0.0
    if mean.ndim == 0:
        return float(mean), float(coverage)
    return mean, coverage

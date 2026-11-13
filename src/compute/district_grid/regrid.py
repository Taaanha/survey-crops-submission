"""Put finer or coarser rasters onto the common 0.1 degree grid (rules in docs/harmonisation.md).

- bin_mean_to_grid : native pixels finer than 0.1 degree (SMAP 9 km, MODIS 250 m, NASADEM 30 m)
  are averaged inside each 0.1 degree cell.
- nearest_cell     : coarser grids (GRACE-FO 0.5 degree mascons) take the nearest cell's value.
- slope_degrees    : terrain slope from a geographic-grid DEM (used before averaging NASADEM).

Pure numpy, no network, no AI. Rasters are [lat, lon] (or [time, lat, lon]); coordinates are
cell centres in degrees."""

import numpy as np

from .grid import RES

# Metres per degree of latitude on a sphere of the mean Earth radius (6,371,000 m). A sphere is
# off by well under 1% over Bangladesh, which changes a slope in degrees by a similar fraction.
M_PER_DEG = 6371000.0 * np.pi / 180.0


def _cell_index(coords, centres):
    """Index of the 0.1 degree cell holding each coordinate (-1 if outside the grid).
    A coordinate exactly on a cell edge goes to the upper cell."""
    centres = np.asarray(centres, dtype=float)
    idx = np.floor((np.asarray(coords, dtype=float) - (centres[0] - RES / 2)) / RES + 1e-9).astype(int)
    idx[(idx < 0) | (idx >= len(centres))] = -1
    return idx


def bin_mean_to_grid(values, lons, lats, grid_lons, grid_lats):
    """Mean of the native pixels whose centres fall inside each 0.1 degree cell.

    values: [lat, lon] or [time, lat, lon]; lons/lats: 1-D pixel-centre coordinates (any order).
    grid_lons/grid_lats: the ascending cell centres from imerg_axes().
    Returns (mean, count) shaped like values with the lat/lon axes replaced by the grid; mean is
    NaN where a cell holds no valid pixel. NaN pixels are ignored."""
    v = np.asarray(values, dtype=float)
    if v.ndim == 3:
        out = [bin_mean_to_grid(v[t], lons, lats, grid_lons, grid_lats) for t in range(v.shape[0])]
        return np.stack([o[0] for o in out]), np.stack([o[1] for o in out])
    if v.shape != (len(lats), len(lons)):
        raise ValueError(f"values shape {v.shape} does not match ({len(lats)} lats, {len(lons)} lons)")
    ny, nx = len(grid_lats), len(grid_lons)
    li = _cell_index(lats, grid_lats)
    lj = _cell_index(lons, grid_lons)
    target = li[:, None] * nx + lj[None, :]
    ok = (li[:, None] >= 0) & (lj[None, :] >= 0) & np.isfinite(v)
    sums = np.bincount(target[ok], weights=v[ok], minlength=ny * nx).reshape(ny, nx)
    count = np.bincount(target[ok], minlength=ny * nx).reshape(ny, nx)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(count > 0, sums / np.where(count > 0, count, 1), np.nan)
    return mean, count


def bin_mean_scattered(values, lon, lat, grid_lons, grid_lats):
    """Like bin_mean_to_grid, for pixels whose centres are not on a lon/lat axis pair (a raster in a
    projected grid): `values`, `lon`, `lat` are same-shaped arrays of pixel values and centres."""
    v = np.asarray(values, dtype=float).ravel()
    ny, nx = len(grid_lats), len(grid_lons)
    li = _cell_index(np.asarray(lat, dtype=float).ravel(), grid_lats)
    lj = _cell_index(np.asarray(lon, dtype=float).ravel(), grid_lons)
    ok = (li >= 0) & (lj >= 0) & np.isfinite(v)
    target = li[ok] * nx + lj[ok]
    sums = np.bincount(target, weights=v[ok], minlength=ny * nx).reshape(ny, nx)
    count = np.bincount(target, minlength=ny * nx).reshape(ny, nx)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(count > 0, sums / np.where(count > 0, count, 1), np.nan)
    return mean, count


def nearest_cell(field, lons, lats, lon, lat):
    """Value of a coarse grid at the cell nearest to (lon, lat).

    field: [..., lat, lon]; lons/lats: 1-D cell centres. Returns (value, cell_lon, cell_lat),
    where value keeps any leading (time) axis."""
    lons = np.asarray(lons, dtype=float)
    lats = np.asarray(lats, dtype=float)
    j = int(np.argmin(np.abs(lons - lon)))
    i = int(np.argmin(np.abs(lats - lat)))
    return np.asarray(field)[..., i, j], float(lons[j]), float(lats[i])


def slope_degrees(elev, lats, step_deg):
    """Terrain slope in degrees for a DEM on a regular lat/lon grid (rows follow `lats`).

    Central differences; east-west spacing shrinks with cos(latitude). Edge rows and columns use
    one-sided differences. NaN elevations give NaN slopes around them."""
    z = np.asarray(elev, dtype=float)
    lats = np.asarray(lats, dtype=float)
    if z.shape[0] != len(lats):
        raise ValueError("elev rows must match lats")
    dz_dy = np.gradient(z, lats * M_PER_DEG, axis=0)
    dx = abs(step_deg) * M_PER_DEG * np.cos(np.radians(lats))
    dz_dx = np.gradient(z, axis=1) / dx[:, None]
    return np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))

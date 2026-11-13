"""NASADEM (30 m) and GEDI (1 km) onto the 0.1 degree grid, without holding the whole raster.

NASADEM over the Bangladesh box is about 18,000 x 22,700 pixels, so it is processed one row of
0.1 degree cells at a time (with a one-pixel margin so slopes at the strip edge are right)."""

import numpy as np

from district_grid.regrid import RES, bin_mean_scattered, bin_mean_to_grid, slope_degrees


def dem_cell_stats(read_strip, grid_lons, grid_lats, step_deg):
    """Mean elevation and mean slope per 0.1 degree cell.

    read_strip(lat_min, lat_max) -> (elev[lat, lon] in metres, lons, lats): the DEM rows between
    those latitudes (the notebook reads them from the NetCDF). Returns three [lat, lon] arrays:
    elev_mean_m, slope_mean_deg and pixel_count."""
    ny, nx = len(grid_lats), len(grid_lons)
    elev = np.full((ny, nx), np.nan)
    slope = np.full((ny, nx), np.nan)
    count = np.zeros((ny, nx), dtype=int)
    margin = 2 * abs(step_deg)
    for i, la in enumerate(grid_lats):
        z, lons, lats = read_strip(la - RES / 2 - margin, la + RES / 2 + margin)
        if z.size == 0:
            continue
        s = slope_degrees(z, lats, step_deg)
        row_mask = (np.asarray(lats) >= la - RES / 2) & (np.asarray(lats) < la + RES / 2)
        e_mean, c = bin_mean_to_grid(z[row_mask], lons, np.asarray(lats)[row_mask], grid_lons, grid_lats)
        s_mean, _ = bin_mean_to_grid(s[row_mask], lons, np.asarray(lats)[row_mask], grid_lons, grid_lats)
        elev[i], slope[i], count[i] = e_mean[i], s_mean[i], c[i]
    return elev, slope, count


def gedi_cell_means(values, lon2d, lat2d, grid_lons, grid_lats, nodata=None):
    """GEDI L4B 1 km raster -> mean aboveground biomass density per 0.1 degree cell.
    `lon2d`/`lat2d` are the pixel-centre longitudes and latitudes (same shape as `values`).
    Pixels equal to `nodata` are ignored. Context only: GEDI mostly measures trees, not field crops."""
    v = np.asarray(values, dtype=float).copy()
    if nodata is not None:
        v[v == nodata] = np.nan
    return bin_mean_scattered(v, lon2d, lat2d, grid_lons, grid_lats)

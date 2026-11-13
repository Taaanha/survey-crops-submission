"""
src/acquire/imerg_subset.py

Helpers to read NASA GPM IMERG V07 Final Run daily precipitation (GPM_3IMERGDF.07, GES DISC)
for the Bangladesh box on the native 0.1 degree grid, through the NASA Earthdata OPeNDAP
(Hyrax) service. The server cuts the box out of each global file, so a day is about 40 KB.

Only the backend/scripts fetch live data. The Earthdata token is passed in by the caller (read
from the environment) and is never printed.
"""

import datetime as dt
import io

import numpy as np
import xarray as xr

from district_grid.grid import LAT_IDX, LON_IDX, imerg_axes

BASE = ("https://opendap.earthdata.nasa.gov/collections/C2723754864-GES_DISC/granules/"
        "GPM_3IMERGDF.07%3A3B-DAY.MS.MRG.3IMERG.{date}-S000000-E235959.V07{ver}.nc4")
# DAP4 constraint: coordinates plus precipitation[time=0][lon range][lat range] (axis order lon, lat)
CE = (f"/lon[{LON_IDX[0]}:{LON_IDX[1]}];/lat[{LAT_IDX[0]}:{LAT_IDX[1]}];/time;"
      f"/precipitation[0][{LON_IDX[0]}:{LON_IDX[1]}][{LAT_IDX[0]}:{LAT_IDX[1]}]")
PRODUCT = "GPM_3IMERGDF.07"
DOI = "10.5067/GPM/IMERGDF/DAY/07"
SOURCE_URL = "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary"
VERSION_LETTERS = ("B", "A")  # the file version letter varies over the record; try B first


def granule_url(day, ver="B"):
    """OPeNDAP URL (DAP4 netCDF response) for one day; add CE as the dap4.ce query parameter."""
    return BASE.format(date=day.strftime("%Y%m%d"), ver=ver) + ".dap.nc4"


def parse_dap_bytes(content):
    """netCDF bytes of one subset day -> float array [lat, lon] in mm/day, NaN where no data.
    Raises ValueError if the coordinates are not the common Bangladesh 0.1 degree grid."""
    with xr.open_dataset(io.BytesIO(content), engine="h5netcdf") as ds:
        lons, lats = imerg_axes()
        if (ds["lon"].size != lons.size or ds["lat"].size != lats.size
                or not np.allclose(ds["lon"].values, lons, atol=1e-3)
                or not np.allclose(ds["lat"].values, lats, atol=1e-3)):
            raise ValueError("IMERG subset is not on the expected Bangladesh 0.1 degree grid")
        arr = ds["precipitation"].isel(time=0).transpose("lat", "lon").values.astype("float64")
    arr[arr < -9000] = np.nan  # safety net if the fill value was not decoded
    return arr


def fetch_day(session, token, day, timeout=180):
    """Fetch one day. Returns (field or None, version letter or None, last HTTP status)."""
    status = None
    for ver in VERSION_LETTERS:
        r = session.get(granule_url(day, ver), params={"dap4.ce": CE},
                        headers={"Authorization": f"Bearer {token}"}, timeout=timeout)
        status = r.status_code
        if status == 200:
            return parse_dap_bytes(r.content), ver, status
        if status not in (400, 404):
            break  # not a "no such file" answer: let the caller retry
    return None, None, status


def days_between(start, end):
    return [start + dt.timedelta(i) for i in range((end - start).days + 1)]

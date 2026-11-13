"""IMERG subset helpers: URL, constraint expression, and parsing of a DAP4 netCDF response."""

import datetime as dt
import io

import numpy as np
import pytest
import xarray as xr

import imerg_subset as m


def test_constraint_matches_the_common_grid_indices():
    assert m.CE == "/lon[2678:2729];/lat[1104:1167];/time;/precipitation[0][2678:2729][1104:1167]"


def test_granule_url_has_date_and_version_letter():
    u = m.granule_url(dt.date(2023, 7, 1), "B")
    assert u.endswith("3B-DAY.MS.MRG.3IMERG.20230701-S000000-E235959.V07B.nc4.dap.nc4")
    assert "GPM_3IMERGDF.07%3A" in u and u.startswith("https://opendap.earthdata.nasa.gov/")


def _fake_response(values, fill_at=None):
    """A DAP4-like netCDF: precipitation[time, lon, lat] with GES DISC's axis order."""
    from district_grid.grid import imerg_axes
    lons, lats = imerg_axes()
    arr = np.asarray(values, dtype="float32").reshape(1, len(lons), len(lats))
    if fill_at is not None:
        arr[0, fill_at[0], fill_at[1]] = -9999.9
    ds = xr.Dataset({"precipitation": (("time", "lon", "lat"), arr, {"_FillValue": np.float32(-9999.9)})},
                    coords={"time": [0], "lon": lons.astype("float32"), "lat": lats.astype("float32")})
    return ds.to_netcdf(engine="h5netcdf")


def test_parse_returns_lat_lon_array_and_turns_fill_into_nan():
    from district_grid.grid import imerg_axes
    lons, lats = imerg_axes()
    vals = np.arange(len(lons) * len(lats), dtype="float32").reshape(len(lons), len(lats))  # [lon, lat]
    field = m.parse_dap_bytes(_fake_response(vals, fill_at=(3, 5)))
    assert field.shape == (len(lats), len(lons))
    assert field[7, 2] == vals[2, 7]                    # transposed to [lat, lon]
    assert np.isnan(field[5, 3])                       # the fill value became NaN
    assert not np.isnan(field[0, 0])


def test_parse_rejects_a_response_on_the_wrong_grid():
    ds = xr.Dataset({"precipitation": (("time", "lon", "lat"), np.zeros((1, 2, 2), "float32"))},
                    coords={"time": [0], "lon": [1.05, 1.15], "lat": [1.05, 1.15]})
    with pytest.raises(ValueError):
        m.parse_dap_bytes(ds.to_netcdf(engine="h5netcdf"))

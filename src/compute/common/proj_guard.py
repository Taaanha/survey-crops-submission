"""PROJ guard. Run `apply()` BEFORE rasterio, pyproj or geopandas are imported.

Why: on Windows a PostgreSQL/PostGIS install sets PROJ_LIB (and GDAL_DATA) to its own folders.
That PROJ database is older than the one inside rasterio's wheel, so CRS lookups fail with
"EPSG code is unknown". This points PROJ_DATA / PROJ_LIB (and GDAL_DATA) at rasterio's bundled
copies, overriding whatever is set. It never imports rasterio itself (that would be too late)."""

import importlib.util
import os


def _rasterio_dir():
    spec = importlib.util.find_spec("rasterio")
    if spec is None or not spec.submodule_search_locations:
        return None
    return list(spec.submodule_search_locations)[0]


def rasterio_proj_data():
    """Path of rasterio's bundled proj_data folder (needs proj.db inside), else None."""
    base = _rasterio_dir()
    path = os.path.join(base, "proj_data") if base else None
    return path if path and os.path.isfile(os.path.join(path, "proj.db")) else None


def apply():
    """Set PROJ_DATA, PROJ_LIB and GDAL_DATA to rasterio's bundled folders. Returns the PROJ path."""
    proj = rasterio_proj_data()
    if proj is None:
        raise RuntimeError("rasterio's bundled proj_data/proj.db was not found; "
                           "reinstall rasterio (pip install --force-reinstall rasterio)")
    os.environ["PROJ_DATA"] = proj
    os.environ["PROJ_LIB"] = proj
    gdal = os.path.join(_rasterio_dir(), "gdal_data")
    if os.path.isdir(gdal):
        os.environ["GDAL_DATA"] = gdal
    return proj

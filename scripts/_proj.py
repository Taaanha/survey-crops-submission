"""PROJ guard for run scripts. `import _proj` as the FIRST import (before numpy-using geo libraries:
rasterio, pyproj, geopandas). It points PROJ_DATA / PROJ_LIB / GDAL_DATA at rasterio's bundled
folders so a PostgreSQL PROJ database cannot shadow them (see src/compute/common/proj_guard.py)."""

import importlib.util
import os

_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "compute", "common", "proj_guard.py")
_spec = importlib.util.spec_from_file_location("proj_guard", _path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_mod.apply()

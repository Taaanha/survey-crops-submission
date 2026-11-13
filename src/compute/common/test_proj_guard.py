"""PROJ guard: a PostgreSQL/PostGIS PROJ database on PROJ_LIB must not shadow rasterio's own."""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SNIPPET = """
import importlib.util, sys
spec = importlib.util.spec_from_file_location("proj_guard", sys.argv[1])
g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
g.apply()
import rasterio
from rasterio.crs import CRS
print(CRS.from_epsg(4326).to_epsg(), CRS.from_epsg(32646).to_epsg())
"""


def _run(env_extra):
    env = dict(os.environ, **env_extra)
    return subprocess.run([sys.executable, "-c", SNIPPET, os.path.join(HERE, "proj_guard.py")],
                          env=env, capture_output=True, text=True, timeout=120)


def test_bundled_dir_is_found_without_importing_rasterio():
    import importlib.util
    spec = importlib.util.spec_from_file_location("proj_guard", os.path.join(HERE, "proj_guard.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    path = g.rasterio_proj_data()
    assert path and os.path.isfile(os.path.join(path, "proj.db"))


def test_guard_overrides_existing_wrong_values():
    bad = os.path.join(HERE, "no_such_proj_dir")
    r = _run({"PROJ_LIB": bad, "PROJ_DATA": bad})
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["4326", "32646"]


def test_crs_lookup_by_epsg_code_works_in_this_process():
    from rasterio.crs import CRS
    assert CRS.from_epsg(4326).to_epsg() == 4326
    assert CRS.from_epsg(32646).to_epsg() == 32646  # UTM 46N, covers Bangladesh

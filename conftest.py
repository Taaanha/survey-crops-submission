"""Root conftest: runs before any test module is imported (for both `src` and `tests`).
PROJ guard first, so a PostgreSQL PROJ database cannot shadow rasterio's (see proj_guard.py)."""

import importlib.util
import os

_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "compute", "common", "proj_guard.py")
_spec = importlib.util.spec_from_file_location("proj_guard", _p)
_g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_g)
_g.apply()

import sys  # noqa: E402

_ROOT = os.path.dirname(os.path.abspath(__file__))
for _sub in (("src", "compute"), ("src", "acquire")):
    _path = os.path.join(_ROOT, *_sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)

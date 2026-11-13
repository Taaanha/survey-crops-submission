"""Probe run in a FRESH interpreter by test_no_shapely.py (not collected by pytest).

Blocks the named packages with sys.modules[name] = None (what the deployed API sees when the package is
not installed), records every attempt to import them (with the repo frames that asked), imports app.py
and calls every route once. Prints one JSON object on the last line of stdout.

usage: python probe_blocked_imports.py <repo_root> <blocked,comma,separated>"""

import builtins
import importlib
import json
import os
import sys
import traceback

ROOT = os.path.abspath(sys.argv[1])
BLOCKED = [b for b in sys.argv[2].split(",") if b]
attempts = []


def _record(name):
    frames = [f"{os.path.relpath(f.filename, ROOT)}:{f.lineno}" for f in traceback.extract_stack()
              if f.filename.startswith(ROOT) and "probe_blocked_imports" not in f.filename]
    attempts.append({"module": name, "chain": frames})


_real_import = builtins.__import__
_real_import_module = importlib.import_module


def _hit(name):
    return name.split(".")[0] in BLOCKED


def _import(name, globals=None, locals=None, fromlist=(), level=0):
    if level == 0 and _hit(name):
        _record(name)
    return _real_import(name, globals, locals, fromlist, level)


def _import_module(name, package=None):
    if _hit(name):
        _record(name)
    return _real_import_module(name, package)


builtins.__import__ = _import
importlib.import_module = _import_module
for b in BLOCKED:
    sys.modules[b] = None          # the user-specified block: any import now raises ImportError

sys.path.insert(0, ROOT)
os.chdir(ROOT)
# no live fetches from a test: SoilGrids and the other live sources just fail over to their fallbacks
import requests  # noqa: E402


def _no_network(*a, **k):
    raise requests.ConnectionError("network disabled in the probe")


requests.get = _no_network
requests.sessions.Session.request = _no_network

from fastapi.testclient import TestClient  # noqa: E402

import app as api  # noqa: E402

client = TestClient(api.app, raise_server_exceptions=False)
CALLS = {
    ("GET", "/"): None,
    ("GET", "/openapi.json"): None,
    ("GET", "/api/v1/districts"): None,
    ("GET", "/api/v1/advisory"): {"district": "cumilla", "prev_harvest": "2024-11-10", "lang": "bn"},
    ("GET", "/api/v1/soil"): {"lat": 23.45, "lon": 91.2},
    ("GET", "/api/v1/risk-calendar"): {"district": "cumilla", "crop": "wheat"},
    ("GET", "/api/v1/post-flood"): {"district": "feni", "flood_date": "2024-08-21"},
    ("GET", "/api/v1/field-twin"): {"district": "cumilla", "year": 2019, "crop": "mustard",
                                    "sow_date": "2019-11-10"},
    ("GET", "/api/v1/images/{name}"): None,
    ("GET", "/api/v1/enso-lens"): None,
    ("GET", "/api/v1/warnings"): None,
    ("GET", "/api/v1/map/layers"): None,
    ("GET", "/api/v1/map/outlines"): None,
    ("GET", "/api/v1/map/values"): {"layer": "nasadem_elevation"},
    ("GET", "/api/v1/map/scenario"): {"district": "cumilla", "crop": "mustard", "rain_pct": 10,
                                      "temp_add_c": 1},
    ("GET", "/api/v1/map/passport"): {"field": "CUM-ARF-01"},
    ("GET", "/api/v1/map/passport#2"): {"field": "CUM-BRRI-02", "half_width": 3},
}
POST = {
    "/api/v1/rotation/rank": {"district": "cumilla", "weights": {"save_water": 0.4, "lowest_risk": 0.3, "flood_safety": 0.3}},
    "/api/v1/ask": {"question": "when to sow wheat in Cumilla?"},
}


def routes():
    """Every (method, path) the app serves, from app.routes, so a new route cannot be missed."""
    out = []
    for r in api.app.routes:
        for m in sorted(getattr(r, "methods", None) or []):
            if m != "HEAD":
                out.append((m, r.path))
    return out


results = {}
unprobed = []
for method, path in routes():
    if method == "POST":
        body = POST.get(path)
        resp = client.post(path, json=body or {})
        results[f"{method} {path}"] = resp.status_code
        continue
    probes = [(k, v) for k, v in CALLS.items() if k[0] == "GET" and k[1].split("#")[0] == path]
    if not probes and path not in ("/docs", "/docs/oauth2-redirect", "/redoc"):
        unprobed.append(f"{method} {path}")      # still called, bare, so an import inside it is seen
    for (_, p), params in probes:
        url = p.split("#")[0].replace("{name}", "does-not-exist.png")
        resp = client.get(url, params=params or {})
        results[f"{method} {p}"] = resp.status_code
    if not probes:
        results[f"{method} {path}"] = client.get(path).status_code

internal_errors = {}
for k, code in results.items():
    if code == 500:
        internal_errors[k] = True

loaded = sorted(m for m in sys.modules if m.split(".")[0] in BLOCKED and sys.modules[m] is not None)
heavy = sorted(m for m in ("district_grid.boundaries", "district_grid.grid") if m in sys.modules)
print(json.dumps({"blocked": BLOCKED, "attempts": attempts, "results": results,
                  "internal_errors": sorted(internal_errors), "unprobed": unprobed, "blocked_modules_loaded": loaded,
                  "shapely_modules_loaded": heavy}))

"""The deployed API (requirements-api.txt) does not install shapely. Prove that no route needs it.

A fresh interpreter blocks shapely (sys.modules['shapely'] = None), imports app.py, and calls every
route that app.py and src/api/map_routes.py register. The probe also records every attempt to import
shapely with the repo frames that asked, so a future import chain is reported, not just detected.
A fresh process is used because in this test process shapely is already imported by other tests."""

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROBE = os.path.join(os.path.dirname(__file__), "probe_blocked_imports.py")


def run_probe(blocked):
    proc = subprocess.run([sys.executable, PROBE, ROOT, blocked], capture_output=True, text=True,
                          timeout=600, cwd=ROOT)
    assert proc.returncode == 0, proc.stderr[-3000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def probe():
    return run_probe("shapely")


def test_requirements_api_really_omits_shapely():
    with open(os.path.join(ROOT, "requirements-api.txt"), encoding="utf-8") as f:
        assert "shapely" not in f.read().lower()


def test_no_route_tries_to_import_shapely(probe):
    chains = [f"{a['module']} <- " + " > ".join(a["chain"]) for a in probe["attempts"]]
    assert probe["attempts"] == [], "shapely is reached by:\n" + "\n".join(chains)


def test_shapely_only_modules_are_never_loaded(probe):
    assert probe["shapely_modules_loaded"] == []
    assert probe["blocked_modules_loaded"] == []


def test_every_route_was_called_and_none_crashed(probe):
    assert probe["unprobed"] == [], f"add a probe call for: {probe['unprobed']}"
    assert probe["internal_errors"] == [], probe["results"]
    expected = {"POST /api/v1/rotation/rank": 200, "GET /api/v1/images/{name}": 404}
    for route, code in expected.items():
        assert probe["results"][route] == code, (route, probe["results"][route])
    for route in ("GET /api/v1/map/layers", "GET /api/v1/map/outlines", "GET /api/v1/map/values",
                  "GET /api/v1/map/scenario", "GET /api/v1/map/passport", "GET /api/v1/districts",
                  "GET /api/v1/advisory", "GET /api/v1/field-twin", "POST /api/v1/rotation/rank"):
        assert route in probe["results"], route


def test_the_probe_would_notice_a_shapely_import(tmp_path):
    """Guards the guard: a route module that imports shapely must show up in 'attempts'."""
    import textwrap
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    (fake_root / "app.py").write_text(textwrap.dedent("""
        import sys
        from fastapi import FastAPI
        app = FastAPI()
        @app.get("/x")
        def x():
            from shapely.geometry import box
            return {}
        """), encoding="utf-8")
    proc = subprocess.run([sys.executable, PROBE, str(fake_root), "shapely"], capture_output=True,
                          text=True, timeout=120, cwd=str(fake_root))
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["attempts"] and out["attempts"][0]["module"].startswith("shapely")
    assert out["internal_errors"] == ["GET /x"]


def test_passport_survives_a_deployment_without_rasterio_or_shapely():
    """requirements-api.txt omits rasterio too. Where the T3b layers are on disk but rasterio is not
    installed, the passport must say 'not assessed' for the flood zones, not return a 500."""
    out = run_probe("shapely,rasterio")
    assert out["internal_errors"] == [], out["results"]
    assert out["results"]["GET /api/v1/map/passport"] == 200

"""
Tests for the neighbour-median estimate used when a point's own SoilGrids cell is masked
(src/acquire/soilgrids_neighbours.py and its use in GET /api/v1/soil). SoilGrids is mocked.

Run from the repo root: python -m pytest src/api/test_soil_neighbours.py -q
"""

import json
import math
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROOT = os.path.abspath(os.path.join(ROOT, ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import app as api  # noqa: E402

sg = api.soilgrids_point
import soilgrids_neighbours as nb  # noqa: E402

client = TestClient(api.app)
URL = "/api/v1/soil?lat=23.45&lon=91.2"


def cell(ph, oc, sand=30.0, silt=30.0, clay=40.0):
    return {"sand": sand, "silt": silt, "clay": clay, "ph": ph,
            "organic_carbon_g_kg": oc, "texture": "clay loam"}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(sg, "FIXTURE_PATH", str(tmp_path / "fx.json"))
    sg.reset_state()
    yield tmp_path
    sg.join_background()
    sg.reset_state()


def test_ring_points_are_equidistant_in_km():
    pts = nb.ring_points(23.46, 91.18, 1)
    assert len(pts) == 8
    for plat, plon in pts:
        km = math.hypot((plat - 23.46) * 111.19,
                        (plon - 91.18) * 111.19 * math.cos(math.radians(23.46)))
        assert km == pytest.approx(1.0, abs=0.02)


def test_median_ignores_masked_cells_and_reports_spread():
    cells = [cell(5.0, 10.0), cell(5.4, 14.0), cell(6.0, 30.0), None, None]
    est = nb.median_estimate(cells)
    assert est["ph"] == pytest.approx(5.4) and est["organic_carbon_g_kg"] == pytest.approx(14.0)
    assert est["n_cells"] == 3 and est["spread"]["ph"] == [5.0, 6.0]
    assert est["sand"] + est["silt"] + est["clay"] == pytest.approx(100.0)
    assert est["texture"]


def test_too_few_cells_is_not_estimated():
    assert nb.median_estimate([cell(5.0, 10.0), cell(5.2, 11.0), None, None]) is None
    assert nb.median_estimate([None] * 8) is None


def test_second_ring_used_only_when_first_has_too_few():
    asked = []

    def fetch(lat, lon):
        asked.append((lat, lon))
        return cell(5.0, 10.0) if len(asked) > 8 else None     # ring 1 all masked

    out = nb.estimate_from_neighbours(23.46, 91.18, fetch)
    assert out["ring_km"] == 2 and len(asked) == 16 and out["soil"]["n_cells"] == 8


def test_failed_calls_count_as_no_cell_never_a_guess():
    n = {"i": 0}

    def fetch(lat, lon):
        n["i"] += 1
        if n["i"] % 2:
            raise RuntimeError("503")
        return cell(5.0, 10.0)

    out = nb.estimate_from_neighbours(23.46, 91.18, fetch)
    assert out["soil"]["n_cells"] == 4 and out["n_failed"] == 4


# ---------------- through the route ----------------

def write_masked_with_estimate(path):
    est_soil = cell(5.4, 14.0)
    est_soil.update({"n_cells": 6, "spread": {"ph": [5.0, 6.0]}})
    pt = {"lat": 23.45, "lon": 91.2, "label": "masked", "status": "masked",
          "retrieved": "2026-11-13", "soil": None,
          "estimate": {"method": "median", "retrieved": "2026-11-13", "soil": est_soil,
                       "ring_km": 1, "n_cells": 6}}
    path.write_text(json.dumps({"points": [pt]}), encoding="utf-8")


def test_masked_point_shows_labelled_estimate_not_its_own_value(isolated, monkeypatch):
    write_masked_with_estimate(isolated / "fx.json")
    calls = []
    monkeypatch.setattr(sg.requests, "get", lambda *a, **k: calls.append(1))
    body = client.get(URL).json()
    soil = body["data"]["soil"]
    assert soil["ph"]["value"] == 5.4 and soil["organic_carbon_g_kg"]["value"] == 14.0
    assert body["source_mode"] == "fixture" and calls == []
    notice = [n for n in body["notices"] if "median of 6" in n["en"]]
    assert notice and notice[0]["level"] == "caution"
    assert "not this point's own value" in notice[0]["en"] and notice[0]["bn"]


def test_masked_point_without_estimate_still_falls_back_to_district(isolated):
    pt = {"lat": 23.45, "lon": 91.2, "label": "m", "status": "masked",
          "retrieved": "2026-11-13", "soil": None}
    (isolated / "fx.json").write_text(json.dumps({"points": [pt]}), encoding="utf-8")
    body = client.get(URL).json()
    assert body["data"]["soil"]["estimate"] == "district"
    assert body["data"]["soil"]["ph"]["value"] is None

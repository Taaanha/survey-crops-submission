"""
Tests for the SoilGrids background fetch, cache and saved fixture
(src/acquire/soilgrids_point.py, GET /api/v1/soil). SoilGrids is always mocked.

Run from the repo root: python -m pytest src/api/test_soil_cache.py -q
"""

import json
import os
import sys
import threading

import pytest
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import app as api  # noqa: E402
from test_soil import ALL, Reply, fake_get, payload  # noqa: E402

sg = api.soilgrids_point
client = TestClient(api.app)
URL = "/api/v1/soil?lat=23.45&lon=91.2"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(sg, "FIXTURE_PATH", str(tmp_path / "no_fixture.json"))
    monkeypatch.setattr(sg, "RETRY_DELAY_S", 0)
    monkeypatch.setattr(sg, "FAIL_COOLDOWN_S", 0)
    sg.reset_state()
    yield tmp_path
    sg.join_background()
    sg.reset_state()


def slow_get(release, reply):
    """A SoilGrids that does not answer until `release` is set."""
    calls = []

    def get(url, params=None, timeout=None):
        calls.append(1)
        release.wait(5)
        return reply
    return get, calls


def write_fixture(path, **point):
    base = {"lat": 23.45, "lon": 91.2, "label": "test point", "status": "assessed",
            "retrieved": "2026-11-13",
            "soil": {"sand": 20.0, "silt": 30.0, "clay": 50.0, "ph": 5.1,
                     "organic_carbon_g_kg": 18.0, "texture": "clay"}}
    base.update(point)
    path.write_text(json.dumps({"points": [base]}), encoding="utf-8")


# ---------------- slow SoilGrids: honest notice, worker finishes, cache fills ----------------

def test_slow_answer_gives_honest_notice_then_fills_cache(monkeypatch):
    monkeypatch.setattr(sg, "WAIT_S", 0.05)
    release = threading.Event()
    get, calls = slow_get(release, Reply(payload()))
    monkeypatch.setattr(sg.requests, "get", get)
    first = client.get(URL).json()
    assert first["data"]["soil"]["estimate"] == "district"
    assert any("slow to answer" in n["en"] and "background" in n["en"] for n in first["notices"])
    assert not any("did not answer in time" in n["en"] for n in first["notices"])
    release.set()
    sg.join_background()
    second = client.get(URL).json()                  # the worker finished: cache, no new call
    assert second["source_mode"] == "cache" and second["data"]["soil"]["estimate"] == "field"
    assert second["data"]["soil"]["ph"]["value"] == 5.2
    assert second["data"]["soil"]["organic_carbon_g_kg"]["value"] == pytest.approx(15.3, abs=0.1)
    assert len(calls) == 1


def test_one_worker_per_point_while_it_runs(monkeypatch):
    monkeypatch.setattr(sg, "WAIT_S", 0.05)
    release = threading.Event()
    get, calls = slow_get(release, Reply(payload()))
    monkeypatch.setattr(sg.requests, "get", get)
    client.get(URL), client.get(URL)
    release.set()
    sg.join_background()
    assert len(calls) == 1


# ---------------- retries and cooldown ----------------

def test_5xx_is_retried_but_429_is_not(monkeypatch):
    seq = iter([Reply({}, 503), Reply({}, 502), Reply(payload())])
    monkeypatch.setattr(sg.requests, "get", lambda *a, **k: next(seq))
    assert client.get(URL).json()["data"]["soil"]["estimate"] == "field"
    calls = fake_get(monkeypatch, Reply({}, 429))
    client.get("/api/v1/soil?lat=23.5&lon=91.3")
    assert len(calls) == 1


def test_timeout_notice_is_the_only_one_that_says_in_time(monkeypatch):
    fake_get(monkeypatch, error=requests.Timeout("slow"))
    body = client.get(URL).json()
    assert any("did not answer in time" in n["en"] for n in body["notices"])


def test_failure_cooldown_does_not_hammer_soilgrids(monkeypatch):
    monkeypatch.setattr(sg, "FAIL_COOLDOWN_S", 60)
    calls = fake_get(monkeypatch, Reply({}, 503))
    client.get(URL)
    n = len(calls)
    body = client.get(URL).json()
    assert len(calls) == n                           # no new call inside the cooldown
    assert any("returned an error" in x["en"] for x in body["notices"])


# ---------------- null, cache ----------------

def test_null_answer_is_cached_as_no_value(monkeypatch):
    calls = fake_get(monkeypatch, Reply(payload(null=ALL)))
    client.get(URL)
    body = client.get(URL).json()
    assert len(calls) == 1 and body["data"]["soil"]["estimate"] == "district"
    assert any("no value" in n["en"] for n in body["notices"])


def test_memory_cache_survives_a_read_only_disk(monkeypatch):
    def no_disk(*a, **k):
        raise OSError("read-only")
    monkeypatch.setattr(sg.os, "makedirs", no_disk)
    calls = fake_get(monkeypatch, Reply(payload()))
    client.get(URL)
    assert client.get(URL).json()["source_mode"] == "cache" and len(calls) == 1


def test_stale_cache_is_served_and_refreshed_behind(monkeypatch, tmp_path):
    old = {"lat": 23.45, "lon": 91.2, "retrieved": "2020-01-01",
           "soil": {"sand": 20.0, "silt": 30.0, "clay": 50.0, "ph": 4.0,
                    "organic_carbon_g_kg": 9.0, "texture": "clay"}}
    (tmp_path / "23.450_91.200.json").write_text(json.dumps(old), encoding="utf-8")
    calls = fake_get(monkeypatch, Reply(payload()))
    body = client.get(URL).json()
    assert body["source_mode"] == "cache" and body["data"]["soil"]["ph"]["value"] == 4.0
    sg.join_background()
    assert len(calls) == 1
    assert client.get(URL).json()["data"]["soil"]["ph"]["value"] == 5.2


# ---------------- saved fixture ----------------

def test_saved_value_is_served_as_fixture_with_its_date_then_refreshed(monkeypatch, tmp_path):
    fx = tmp_path / "fx.json"
    write_fixture(fx)
    monkeypatch.setattr(sg, "FIXTURE_PATH", str(fx))
    calls = fake_get(monkeypatch, Reply(payload()))
    body = client.get(URL).json()
    assert body["source_mode"] == "fixture" and body["data"]["soil"]["estimate"] == "field"
    assert body["data"]["soil"]["ph"]["value"] == 5.1
    assert body["data"]["soil"]["organic_carbon_g_kg"]["value"] == 18.0
    assert any("saved SoilGrids value" in n["en"] and "2026-11-13" in n["en"]
               for n in body["notices"])
    sg.join_background()
    assert len(calls) == 1                           # refreshed behind the answer
    again = client.get(URL).json()                   # now the fresh cache wins
    assert again["source_mode"] == "cache" and again["data"]["soil"]["ph"]["value"] == 5.2


def test_fixture_is_exact_point_only_never_a_neighbour(monkeypatch, tmp_path):
    fx = tmp_path / "fx.json"
    write_fixture(fx, lat=23.46)                     # about 1 km from the request
    monkeypatch.setattr(sg, "FIXTURE_PATH", str(fx))
    fake_get(monkeypatch, error=requests.Timeout("slow"))
    body = client.get(URL).json()
    assert body["data"]["soil"]["estimate"] == "district"
    assert body["data"]["soil"]["ph"]["value"] is None


def test_masked_fixture_stays_masked_without_a_call(monkeypatch, tmp_path):
    fx = tmp_path / "fx.json"
    write_fixture(fx, status="masked", soil=None)
    monkeypatch.setattr(sg, "FIXTURE_PATH", str(fx))
    calls = fake_get(monkeypatch, Reply(payload()))
    body = client.get(URL).json()
    assert calls == [] and body["source_mode"] == "fixture"
    assert any("no value" in n["en"] for n in body["notices"])


def test_committed_fixture_file_is_well_formed():
    with open(os.path.join(ROOT, "demo_fixtures", "soilgrids_points.json"),
              encoding="utf-8") as f:
        doc = json.load(f)
    assert doc["dataset"] and doc["source_url"].startswith("https://")
    assert doc["points"]
    for pt in doc["points"]:
        assert pt["status"] in ("assessed", "masked") and pt["retrieved"] and pt["label"]
        assert (pt["soil"] is None) == (pt["status"] == "masked")
        if "estimate" in pt:                         # only a masked point carries an estimate
            assert pt["status"] == "masked" and pt["estimate"]["n_cells"] >= 3

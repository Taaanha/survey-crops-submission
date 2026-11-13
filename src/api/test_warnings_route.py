"""GET /api/v1/warnings: live answer, heavy-rain day, Open-Meteo down (cache, fixture, nothing), provenance."""

import json
import re

import pytest
from fastapi.testclient import TestClient

import open_meteo
import safe_fetch
from app import app

client = TestClient(app)
URL = "/api/v1/warnings?district=cumilla"
BANNED = re.compile(r"predict|forecast", re.I)


def payload(rain=(0, 2, 1, 0, 0, 0, 0), tmax=28.0, tmin=18.0):
    days = [f"2026-11-{13 + i}" for i in range(7)]
    return {"daily": {"time": days, "precipitation_sum": list(rain),
                      "temperature_2m_max": [tmax] * 7, "temperature_2m_min": [tmin] * 7},
            "retrieved_on": "2026-11-13"}


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(safe_fetch, "CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setattr(safe_fetch, "FIXTURE_DIR", str(tmp_path / "fixtures"))
    (tmp_path / "fixtures").mkdir()
    monkeypatch.delenv("OFFLINE", raising=False)
    return tmp_path


def live(monkeypatch, data):
    monkeypatch.setattr(safe_fetch.requests, "get", lambda *a, **k: FakeResponse(data))


def down(monkeypatch):
    def boom(*a, **k):
        raise ConnectionError("no network")
    monkeypatch.setattr(safe_fetch.requests, "get", boom)


def prov_ids(body):
    return {p["id"] for p in body["provenance"]}


def src_ids(node, out=None):
    out = set() if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            out.update(v) if k == "src" else src_ids(v, out)
    elif isinstance(node, list):
        for v in node:
            src_ids(v, out)
    return out


def test_normal_days_give_an_honest_empty_list(dirs, monkeypatch):
    live(monkeypatch, payload())
    body = client.get(URL).json()
    assert body["is_mock"] is False and body["source_mode"] == "live" and body["errors"] == []
    assert body["data"]["warnings"] == []
    assert body["data"]["valid_from"] == "2026-11-13" and body["data"]["valid_to"] == "2026-11-19"
    assert "om" in prov_ids(body)
    assert any("No warning limit" in n["en"] for n in body["notices"])


def test_heavy_rain_day_warns_and_every_src_resolves(dirs, monkeypatch):
    live(monkeypatch, payload(rain=(0, 0, 51.4, 0, 0, 0, 0)))
    body = client.get(URL).json()
    assert body["is_mock"] is False
    (w,) = body["data"]["warnings"]
    assert w["type"] == "heavy_rain" and w["date"] == "2026-11-15"
    assert w["forecast"]["value"] == 51.4 and w["forecast"]["src"] == ["om"]
    assert w["threshold"]["value"] == 44 and w["threshold"]["unit"] == "mm/24h"
    assert w["action"]["en"] and w["action"]["bn"]
    assert src_ids(body["data"]) <= prov_ids(body)
    by_id = {p["id"]: p for p in body["provenance"]}
    assert by_id[w["threshold"]["src"][0]]["url"].startswith("http")
    assert by_id["om"]["retrieved"] and "open-meteo" in by_id["om"]["url"]
    assert any("Open-Meteo" in n["en"] and "not NASA" in n["en"] for n in body["notices"])


def test_no_banned_words_in_user_facing_text(dirs, monkeypatch):
    live(monkeypatch, payload(rain=(60,) * 7, tmax=36.0, tmin=5.0))
    body = client.get(URL).json()
    assert {w["type"] for w in body["data"]["warnings"]} == {"heavy_rain", "heat", "cold"}
    texts = [n["en"] + n["bn"] for n in body["notices"]]
    texts += [w["action"]["en"] + w["action"]["bn"] for w in body["data"]["warnings"]]
    assert not [t for t in texts if BANNED.search(t)]


def test_open_meteo_down_uses_the_fixture_and_says_so(dirs, monkeypatch):
    (dirs / "fixtures" / "openmeteo_cumilla.json").write_text(json.dumps(payload(rain=(70,) + (0,) * 6)))
    down(monkeypatch)
    body = client.get(URL).json()
    assert body["source_mode"] == "fixture" and body["is_mock"] is False
    assert body["data"]["warnings"][0]["type"] == "heavy_rain"
    assert body["notices"][0]["level"] == "caution" and "saved copy" in body["notices"][0]["en"]
    assert next(p for p in body["provenance"] if p["id"] == "om")["retrieved"] == "2026-11-13"


def test_open_meteo_down_uses_todays_cache_first(dirs, monkeypatch):
    live(monkeypatch, payload())
    assert client.get(URL).json()["source_mode"] == "live"
    down(monkeypatch)
    assert client.get(URL).json()["source_mode"] == "cache"


def test_open_meteo_down_and_nothing_saved_is_a_clear_error_not_an_empty_body(dirs, monkeypatch):
    down(monkeypatch)
    r = client.get(URL)
    body = r.json()
    assert r.status_code == 404 and body["errors"][0]["code"] == "NO_DATA_FOR_PERIOD"
    assert body["errors"][0]["en"] and body["errors"][0]["bn"]


def test_bad_district_and_missing_district(dirs):
    assert client.get("/api/v1/warnings?district=paris").json()["errors"][0]["code"] == "DISTRICT_NOT_COVERED"
    assert client.get("/api/v1/warnings").json()["errors"][0]["code"] == "BAD_PARAMETER"


def test_parse_keeps_a_missing_number_as_none():
    p = payload()
    p["daily"]["precipitation_sum"][1] = None
    assert open_meteo.parse_daily(p)[1]["rain_mm"] is None


def test_dockerfile_ships_the_weather_fixtures():
    """The Render image must carry demo_fixtures/ so the saved copy exists when Open-Meteo is down."""
    import os
    root = os.path.join(os.path.dirname(__file__), "..", "..")
    assert "COPY demo_fixtures/ demo_fixtures/" in open(os.path.join(root, "Dockerfile")).read()
    ignore = open(os.path.join(root, ".dockerignore")).read().splitlines()
    assert "demo_fixtures/" not in ignore
    for d in ("cumilla", "feni", "brahmanbaria", "noakhali", "sylhet"):
        assert os.path.isfile(os.path.join(root, "demo_fixtures", f"openmeteo_{d}.json"))

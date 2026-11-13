"""W5 map endpoints: envelope, provenance on every payload, disabled layers visible with a reason,
slider results equal to the Layer 1 numbers, and the usual error envelope."""

import os
import re
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import app as api  # noqa: E402
from map_layers import scenario  # noqa: E402

client = TestClient(api.app)
BASE = "/api/v1/map"


def get(path, **params):
    return client.get(BASE + path, params=params)


def test_layers_lists_disabled_layers_with_their_reason():
    r = get("/layers")
    assert r.status_code == 200
    body = r.json()
    assert body["endpoint"] == BASE + "/layers" and body["errors"] == []
    layers = {x["key"]: x for x in body["data"]["layers"]}
    for key in ("smap_64", "ecostress_et", "ecostress_lst", "gedi_agbd"):
        assert layers[key]["enabled"] is False and layers[key]["reason"]
    assert layers["nasadem_elevation"]["enabled"] is True
    assert body["data"]["years"] == [2001, 2024]
    assert body["provenance"]


def test_outlines_carry_licence_and_64_features():
    body = get("/outlines").json()
    assert len(body["data"]["features"]) == 64
    prov = body["provenance"][0]
    assert "CC BY 3.0 IGO" in prov["licence"] or "Creative Commons" in prov["licence"]
    assert prov["source_url"].startswith("https://")


def test_values_have_64_rows_and_a_source():
    body = get("/values", layer="nasadem_slope").json()
    assert len(body["data"]["rows"]) == 64
    assert body["provenance"][0]["source_url"].startswith("http")
    body = get("/values", layer="grace_fo", year=2010).json()
    assert body["data"]["year"] == 2010 and any("regional" in c.lower() for c in body["data"]["caveats"])


def test_values_for_a_not_assessed_layer_is_a_clear_error_not_zeros():
    r = get("/values", layer="ecostress_et")
    assert r.status_code == 404
    err = r.json()["errors"][0]
    assert err["code"] == "NO_DATA_FOR_PERIOD" and "units unresolved" in err["en"]
    assert r.json()["data"] is None


@pytest.mark.parametrize("params", [{}, {"layer": "nope"}, {"layer": "grace_fo"},
                                    {"layer": "grace_fo", "year": "abc"},
                                    {"layer": "w2:cdd", "year": 2010, "season": "winter"}])
def test_values_bad_parameters(params):
    r = get("/values", **params)
    assert r.status_code == 400 and r.json()["errors"][0]["code"] == "BAD_PARAMETER"


def test_scenario_equals_layer1_and_is_labelled():
    r = get("/scenario", district="cumilla", crop="wheat", rain_pct=-30, temp_add_c=2)
    assert r.status_code == 200
    d = r.json()["data"]
    direct = scenario.run_scenario("cumilla", "wheat", -30, 2)
    assert d["scenario"]["irrigation_mm_mean"] == direct["scenario"]["irrigation_mm_mean"]
    assert d["baseline"]["irrigation_mm_mean"] == direct["baseline"]["irrigation_mm_mean"]
    assert d["label"] == "what-if on past seasons, not a forecast"
    assert r.json()["provenance"]
    zero = get("/scenario", district="cumilla", crop="wheat", rain_pct=0, temp_add_c=0).json()["data"]
    assert zero["scenario"] == zero["baseline"]
    other = {k: v for k, v in r.json().items() if k != "narration"}
    assert not re.search(r"predict", str(other).lower())


@pytest.mark.parametrize("params,code", [
    ({"district": "cumilla", "crop": "wheat", "rain_pct": 31, "temp_add_c": 0}, "BAD_PARAMETER"),
    ({"district": "cumilla", "crop": "wheat", "rain_pct": 0, "temp_add_c": 3}, "BAD_PARAMETER"),
    ({"district": "cumilla", "crop": "wheat", "rain_pct": "x", "temp_add_c": 0}, "BAD_PARAMETER"),
    ({"district": "cumilla", "crop": "banana", "rain_pct": 0, "temp_add_c": 0}, "BAD_PARAMETER"),
    ({"district": "dhaka", "crop": "wheat", "rain_pct": 0, "temp_add_c": 0}, "DISTRICT_NOT_COVERED"),
    ({"crop": "wheat", "rain_pct": 0, "temp_add_c": 0}, "BAD_PARAMETER"),
])
def test_scenario_errors(params, code):
    r = get("/scenario", **params)
    assert r.status_code == 400 and r.json()["errors"][0]["code"] == code


def test_passport_has_layers_and_not_assessed_entries():
    body = get("/passport", field="CUM-ARF-01").json()
    layers = {x["key"]: x for x in body["data"]["layers"]}
    assert layers["nasadem_elevation_30m"]["status"] == "assessed"
    assert layers["hls_ndvi_30m"]["status"] == "not assessed"
    assert body["provenance"]
    assert get("/passport", field="NOPE").status_code == 400


def test_passport_zones_are_labelled_and_cited():
    body = get("/passport", field="CUM-BRRI-02", half_width=3).json()
    vz = body["data"]["vulnerability_zones"]
    assert "not a cited vulnerability class" in vz["label"]
    assert vz["zones"]["low_lying"]["status"] == "assessed"
    for key in ("cold_prone", "erosion", "water_stress"):
        assert vz["zones"][key]["status"] == "not assessed"
    urls = {p["url"] for p in body["provenance"]}
    for z in vz["zones"].values():
        assert z["source_url"] in urls, z["key"]       # every zone shown is in the provenance list

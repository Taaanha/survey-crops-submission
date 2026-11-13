"""Contract tests for POST /api/v1/rotation/rank (T2): same top-level keys and
component shape as web/mock/rotation_rank.json, provenance on every measure,
and the usual error envelope."""

import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import app as api  # noqa: E402

URL = "/api/v1/rotation/rank"
client = TestClient(api.app)
WEIGHTS = {"save_water": 0.5, "lowest_risk": 0.3, "soil_health": 0.2}
PROV_KEYS = ("dataset", "source_url", "retrieved", "granule_or_file")


def mock():
    with open(os.path.join(ROOT, "web", "mock", "rotation_rank.json"), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def body():
    r = client.post(URL, json={"district": "cumilla", "weights": WEIGHTS})
    assert r.status_code == 200, r.text[:500]
    return r.json()


def test_top_level_keys_and_envelope_match_the_mock(body):
    assert set(body) == set(mock()) - {"mock_note"}
    assert body["endpoint"] == URL and body["is_mock"] is False and body["errors"] == []
    assert body["source_mode"] in ("live", "cache", "fixture")
    assert body["request"]["weights"] == WEIGHTS


def test_data_shape_matches_the_mock(body):
    ref = mock()["data"]
    assert set(body["data"]) == set(ref)
    assert set(body["data"]["weights"]) == set(ref["weights"]) == {"requested", "normalised"}
    assert set(body["data"]["ranked"][0]) == set(ref["ranked"][0])
    assert set(body["data"]["ranked"][0]["components"]) == set(ref["ranked"][0]["components"])
    comp = body["data"]["ranked"][0]["components"]["save_water"]
    assert set(comp) == set(ref["ranked"][0]["components"]["save_water"])
    assert set(body["data"]["unranked"][0]) == set(ref["unranked"][0])


def test_ranking_is_ordered_and_components_add_up(body):
    ranked = body["data"]["ranked"]
    assert [r["rank"] for r in ranked] == list(range(1, len(ranked) + 1))
    assert [r["score"] for r in ranked] == sorted((r["score"] for r in ranked), reverse=True)
    assert sum(body["data"]["weights"]["normalised"].values()) == pytest.approx(1)
    for row in ranked:
        total = sum(c["contribution"] for c in row["components"].values())
        assert abs(total - row["score"]) < 1e-9
        for c in row["components"].values():
            assert abs(c["weight"] * (c["normalised"] or 0) - c["contribution"]) < 1e-9


def test_every_raw_value_carries_provenance_listed_in_the_envelope(body):
    listed = {p["source_url"] for p in body["provenance"]}
    assert listed and all(all(p.get(k) for k in PROV_KEYS) and p["url"] for p in body["provenance"])
    for row in body["data"]["ranked"]:
        for c in row["components"].values():
            if c["raw"] is not None:
                assert set(c["raw"]) == {"value", "unit", "provenance"}
                assert all(c["raw"]["provenance"].get(k) for k in PROV_KEYS)
                assert c["raw"]["provenance"]["source_url"] in listed


def test_weights_that_do_not_sum_to_one_are_normalised():
    r = client.post(URL, json={"district": "cumilla", "weights": {"save_water": 0.2, "lowest_risk": 0.2}})
    assert r.status_code == 200
    assert r.json()["data"]["weights"]["normalised"]["save_water"] == pytest.approx(0.5)


def test_flood_safety_leaves_unassessed_rotations_unranked_with_a_reason():
    r = client.post(URL, json={"district": "cumilla", "weights": {"flood_safety": 1}})
    data = r.json()["data"]
    assert r.status_code == 200 and data["ranked"]
    assert all("not assessed" in u["reason"] for u in data["unranked"]) and data["unranked"]
    assert any(n["level"] == "caution" for n in r.json()["notices"])


@pytest.mark.parametrize("payload,status,code", [
    ({"district": "cumilla", "weights": {}}, 400, "BAD_PARAMETER"),
    ({"district": "cumilla", "weights": {k: 0 for k in WEIGHTS}}, 400, "BAD_PARAMETER"),
    ({"district": "cumilla", "weights": {"save_water": 2}}, 400, "BAD_PARAMETER"),
    ({"district": "cumilla", "weights": {"cheapest": 1}}, 400, "BAD_PARAMETER"),
    ({"district": "cumilla", "weights": "all"}, 400, "BAD_PARAMETER"),
    ({"district": "cumilla"}, 400, "BAD_PARAMETER"),
    ({"weights": WEIGHTS}, 400, "BAD_PARAMETER"),
    ({"district": "dhaka", "weights": WEIGHTS}, 400, "DISTRICT_NOT_COVERED"),
    ([1, 2], 400, "BAD_PARAMETER"),
])
def test_errors_use_the_error_envelope(payload, status, code):
    r = client.post(URL, json=payload)
    body = r.json()
    assert r.status_code == status
    assert set(body) == set(json.load(open(os.path.join(ROOT, "web", "mock", "error.json"),
                                           encoding="utf-8"))) - {"mock_note"}
    assert body["data"] is None and body["errors"][0]["code"] == code
    assert body["errors"][0]["en"] and body["errors"][0]["bn"]


def test_all_zero_weights_error_says_what_to_do():
    r = client.post(URL, json={"district": "cumilla", "weights": {k: 0 for k in WEIGHTS}})
    assert "at least one" in r.json()["errors"][0]["en"]


def test_invalid_json_body_is_an_error_not_an_empty_response():
    r = client.post(URL, content="nope", headers={"content-type": "application/json"})
    assert r.status_code == 400 and r.json()["errors"][0]["code"] == "BAD_PARAMETER"


def test_wording_never_says_predict_or_forecast(body):
    text = json.dumps(body, ensure_ascii=False).lower()
    assert "predict" not in text and "forecast" not in text

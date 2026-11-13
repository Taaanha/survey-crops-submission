"""Tests for GET /api/v1/rotation/strategies and GET /api/v1/models."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient  # noqa: E402

import app as api  # noqa: E402

client = TestClient(api.app)
CURRENT = "aman_rice@06-15>boro_rice"


def nan_to_none(x):
    if isinstance(x, dict):
        return {k: nan_to_none(v) for k, v in x.items()}
    if isinstance(x, list):
        return [nan_to_none(v) for v in x]
    return None if isinstance(x, float) and x != x else x


def test_models_serves_the_w3_metrics_and_cards_unchanged():
    r = client.get("/api/v1/models")
    assert r.status_code == 200
    b = r.json()
    assert b["errors"] == [] and b["is_mock"] is False and b["endpoint"] == "/api/v1/models"
    with open(os.path.join(ROOT, "docs", "results", "w3_metrics.json"), encoding="utf-8") as f:
        import json
        # the envelope turns NaN (not assessed) into null; nothing else may differ
        assert b["data"]["metrics"] == nan_to_none(json.load(f))
    assert len(b["data"]["cards"]) == 6
    assert b["provenance"] and all(p["url"].startswith("http") for p in b["provenance"])
    assert "forecast" not in b["notices"][0]["en"].lower().replace("not a forecast", "")


@pytest.fixture(scope="module")
def strategies():
    r = client.get("/api/v1/rotation/strategies", params={"district": "cumilla", "current": CURRENT})
    assert r.status_code == 200, r.text[:500]
    return r.json()


def test_strategies_has_baseline_alternatives_and_pest_rule(strategies):
    d = strategies["data"]
    assert strategies["errors"] == []
    for key in ("baseline", "alternatives", "crops_not_offered", "priority_matrix", "pest_rule"):
        assert key in d
    assert d["baseline"]["role"] == "baseline"


def test_strategies_every_provenance_entry_has_a_link(strategies):
    assert strategies["provenance"]
    assert all(p["url"] for p in strategies["provenance"])


@pytest.mark.parametrize("params,status,code", [
    ({}, 400, "BAD_PARAMETER"),
    ({"district": "cumilla"}, 400, "BAD_PARAMETER"),
    ({"district": "cumilla", "current": "nonsense"}, 400, "BAD_PARAMETER"),
    ({"district": "dhaka", "current": CURRENT}, 400, "DISTRICT_NOT_COVERED"),
])
def test_strategies_errors_use_the_envelope(params, status, code):
    r = client.get("/api/v1/rotation/strategies", params=params)
    assert r.status_code == status
    b = r.json()
    assert b["data"] is None and b["errors"][0]["code"] == code

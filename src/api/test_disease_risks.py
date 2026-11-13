"""GET /api/v1/risk-calendar: the additive disease_risks field (potato late blight; others not assessed)."""

import re

import pytest
from fastapi.testclient import TestClient

from app import app

client = TestClient(app)
BANNED = re.compile(r"predict|forecast", re.I)


def get(district, crop):
    return client.get(f"/api/v1/risk-calendar?district={district}&crop={crop}").json()


def test_potato_has_counts_with_sources_that_resolve():
    r = get("cumilla", "potato")
    d = r["data"]["disease_risks"]
    assert len(d) == 1 and d[0]["status"] == "assessed"
    fav, n = d[0]["seasons_favourable"], d[0]["seasons_counted"]
    assert n["value"] == 24 and 0 <= fav["value"] <= 24
    ids = {p["id"] for p in r["provenance"]}
    assert {"imerg", "power"} <= set(fav["src"]) and set(fav["src"]) <= ids
    urls = [p["url"] for p in r["provenance"] if p["id"] in fav["src"] and p["id"] not in ("imerg", "power")]
    assert urls and all(u.startswith("http") for u in urls)
    assert f"{fav['value']} of 24" in d[0]["text"]["en"] and "Conditions favourable" in d[0]["text"]["en"]


def test_existing_risk_calendar_keys_are_unchanged():
    data = get("cumilla", "potato")["data"]
    for key in ("recommended_window", "hazards", "grid", "water", "sensitivity", "sowing_dates"):
        assert key in data


@pytest.mark.parametrize("crop,reason", [("wheat", "source link"), ("lentil", "leaf-wetness"),
                                         ("mustard", "no sourced disease rule")])
def test_crops_without_a_usable_rule_say_not_assessed(crop, reason):
    d = get("noakhali", crop)["data"]["disease_risks"][0]
    assert d["status"] == "not_assessed" and reason in d["reason"]
    assert "seasons_favourable" not in d


def test_no_banned_words_in_the_disease_text():
    d = get("sylhet", "potato")["data"]["disease_risks"][0]
    text = " ".join([d["text"]["en"], d["meaning"]["en"], d["window"]["note"]["en"]])
    assert not BANNED.search(text)

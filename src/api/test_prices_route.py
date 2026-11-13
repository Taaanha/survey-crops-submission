"""GET /api/v1/rotation/strategies: the market_price indicator carries type, month, market and source mode
(fixtures only); a crop with no price is a gap, never 0; the word "income" only appears as "not income per hectare"."""

import re

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)
BANNED = re.compile(r"predict|forecast", re.I)
URL = "/api/v1/rotation/strategies?district=cumilla&current=aman_rice@06-15>mustard"


def options():
    r = client.get(URL).json()
    d = r["data"]
    return r, {o["id"]: o for o in [d["baseline"]] + d["alternatives"]}


def test_priced_option_has_date_type_market_source_and_fixture_mode():
    r, opts = options()
    m = opts["aman_rice@06-15>wheat"]["indicators"]["market_price"]
    assert m["status"] == "assessed" and m["measure"]["value"] == 40.32
    assert (m["as_of"], m["price_type"], m["source_mode"]) == ("2026-02", "wholesale", "fixture")
    assert m["market"] == "not stated in the source"
    assert m["measure"]["provenance"]["source_url"].startswith("https://")
    assert m["past_range"]["status"] == "gap"
    assert any("a price, not income per hectare" in line for line in opts["aman_rice@06-15>wheat"]["card"]["benefits"]
               + opts["aman_rice@06-15>wheat"]["card"]["evidence"]), "card text names it a price"


def test_unpriced_options_are_gaps_with_no_number():
    _, opts = options()
    for key in ("aman_rice@06-15>mustard", "aman_rice@06-15>boro_rice"):
        m = opts[key]["indicators"]["market_price"]
        assert m["status"] == "gap" and "measure" not in m


def test_price_source_is_in_provenance_and_no_banned_words():
    r, opts = options()
    urls = {p["url"] for p in r["provenance"]}
    assert opts["aman_rice@06-15>wheat"]["indicators"]["market_price"]["measure"]["provenance"]["source_url"] in urls \
        or any("fas.usda.gov" in (u or "") for u in urls)
    m = opts["aman_rice@06-15>wheat"]["indicators"]["market_price"]
    assert not BANNED.search(m["caveat"] + m["past_range"]["reason"])


def test_advisory_options_carry_a_dated_price_or_not_assessed():
    r = client.get("/api/v1/advisory?district=cumilla&prev_harvest=2026-11-20").json()
    by = {o["crop"]: o["market_price"] for o in r["data"]["options"]}
    assert by["wheat"]["status"] == "assessed" and by["wheat"]["price"]["value"] == 40.32
    assert by["wheat"]["as_of"] == "2026-02" and by["wheat"]["source_mode"] == "fixture"
    assert set(by["wheat"]["price"]["src"]) <= {p["id"] for p in r["provenance"]}
    assert by["mustard"]["status"] == "not_assessed" and "price" not in by["mustard"]
    assert "a price, not income per hectare" in by["wheat"]["label"]["en"]
    text = " ".join([by["wheat"]["caveat"], by["wheat"]["past_range"]["reason"], by["mustard"]["text"]["en"]])
    assert not BANNED.search(text)

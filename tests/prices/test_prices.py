"""Tests for src/compute/prices and its use in strategies.facts.price (fixtures only, no network)."""

import os
import re
import shutil

import pytest

import prices
from strategies import facts

BANNED = re.compile(r"predict|forecast", re.I)


@pytest.mark.parametrize("value,unit,expected", [
    (40.32, "BDT/kg", 40.32), ("40.32", "bdt/kg", 40.32),
    (4000, "BDT/100kg", 40.0), (4000, "BDT/quintal", 40.0), (40000, "BDT/tonne", 40.0),
])
def test_unit_conversion(value, unit, expected):
    assert prices.to_bdt_per_kg(value, unit) == pytest.approx(expected)


@pytest.mark.parametrize("value,unit", [(1, "USD/kg"), (1, "BDT/maund"), (1, ""), ("abc", "BDT/kg"), (float("nan"), "BDT/kg")])
def test_unconvertible_is_none_not_a_guess(value, unit):
    assert prices.to_bdt_per_kg(value, unit) is None


def test_price_type_and_variant_from_the_item_name():
    assert prices.price_type("wheat.price.wholesale") == "wholesale"
    assert prices.price_type("lentil.price.retail_high_quality") == "retail"
    assert prices.price_variant("lentil.price.retail_high_quality") == "high_quality"
    assert prices.price_type("wheat.price.farmgate_or_wholesale") is None      # does not say which
    assert prices.price_variant("wheat.price.wholesale") is None


def test_describe_gives_month_market_and_fixture_mode():
    d = prices.describe("wheat.price.wholesale")
    assert d["as_of"] == "2026-02" and d["price_type"] == "wholesale"
    assert d["market"] == "not stated in the source" and d["source_mode"] == "fixture"
    assert d["past_range"]["status"] == "gap" and "12 months" in d["past_range"]["reason"]
    assert not BANNED.search(d["caveat"] + d["past_range"]["reason"])


def test_describe_unknown_item_has_no_date():
    d = prices.describe("nothing.price.retail")
    assert d["as_of"] is None and d["market"] == "not stated in the source"


def test_every_price_row_with_a_number_has_a_month():
    import pandas as pd
    rows = pd.read_csv(os.path.join("data", "reference", "prices.csv"), dtype=str)
    rows = rows[pd.to_numeric(rows["value"], errors="coerce").notna()]
    meta = prices.load_meta()
    assert set(rows["item"]) <= set(meta), sorted(set(rows["item"]) - set(meta))


def test_wheat_has_a_dated_cited_price():
    p = facts.price("wheat")
    assert p["status"] == "assessed" and p["measure"]["value"] == 40.32 and p["measure"]["unit"] == "BDT/kg"
    assert p["as_of"] == "2026-02" and p["price_type"] == "wholesale" and p["source_mode"] == "fixture"
    assert p["measure"]["provenance"]["source_url"].startswith("https://www.fas.usda.gov/")


def test_a_crop_without_a_price_stays_a_gap_never_zero():
    for crop in ("mustard", "boro_rice", "sesame"):
        p = facts.price(crop)
        assert p["status"] == "gap" and "measure" not in p and "value" not in p


def test_price_row_in_another_unit_is_converted_and_unknown_units_skipped(tmp_path):
    ref_dir = tmp_path / "ref"
    ref_dir.mkdir()
    for name in facts.FACT_FILES:
        shutil.copy(os.path.join(facts.REFERENCE_DIR, name), ref_dir / name)
    head = "item,value,unit,source_title,source_url,page,year,notes\n"
    (ref_dir / "prices.csv").write_text(
        head + "maize.price.wholesale,5000,USD/ton,Test A,https://example.org/a,1,2026,unknown unit\n"
               "maize.price.retail,4400,BDT/100kg,Test B,https://example.org/b,1,2026,per quintal\n",
        encoding="utf-8")
    p = facts.price("maize", reference_dir=str(ref_dir))
    assert p["status"] == "assessed" and p["item"] == "maize.price.retail"     # USD row skipped
    assert p["measure"]["value"] == pytest.approx(44.0) and p["measure"]["unit"] == "BDT/kg"
    assert "converted from 4400" in p["measure"]["provenance"]["note"]
    assert p["as_of"] is None                                                   # no month listed for this item in price_meta.csv


def test_card_text_names_type_and_month():
    from strategies.cards import _month_text
    assert _month_text("2026-02") == "Feb 2026" and _month_text(None) == "" and _month_text("x") == ""

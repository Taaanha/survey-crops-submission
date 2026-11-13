"""Per-crop cited facts (root depth, family, nitrogen fixing, forage, residue,
price, pest rule). Real reference rows are used; a fact with no row is a gap."""

import pytest

from strategies import facts

REF = facts.load_facts_reference()


# ---------------- root depth (FAO-56 Table 22) ----------------

def test_wheat_root_depth_comes_from_table_22():
    out = facts.root_depth("wheat", REF)
    assert out["status"] == "assessed"
    assert out["zr_min_m"]["unit"] == "m"
    assert "x0490e" in out["zr_min_m"]["provenance"]["source_url"]  # fao.org FAO-56 page
    assert out["zr_min_m"]["value"] < out["zr_max_m"]["value"]

def test_aman_rice_maps_to_the_table_22_rice_row():
    out = facts.root_depth("aman_rice", REF)
    assert out["status"] == "assessed"
    assert (out["zr_min_m"]["value"], out["zr_max_m"]["value"]) == (0.5, 1.0)
    assert "rice" in out["note"]  # says it used the generic Rice row

def test_unknown_crop_root_depth_is_a_gap():
    out = facts.root_depth("dragonfruit", REF)
    assert out["status"] == "gap"
    assert "dragonfruit" in out["reason"]


# ---------------- family and pest-cycle rule ----------------

def test_families_of_the_live_crops():
    assert facts.family("wheat", REF)["value"] == "Poaceae"
    assert facts.family("lentil", REF)["value"] == "Fabaceae"
    assert facts.family("mustard", REF)["value"] == "Brassicaceae"

def test_pest_rule_is_cited_and_labelled_needs_local_review():
    rule = facts.pest_rule(REF)
    assert rule["status"] == "assessed"
    assert rule["provenance"]["source_url"].startswith("http")
    assert "needs local review" in rule["note"]

def test_pest_break_same_family_is_no_break():
    out = facts.pest_cycle_break(["aman_rice", "boro_rice"], REF)
    assert out["status"] == "assessed"
    assert out["breaks_cycle"] is False      # Poaceae -> Poaceae

def test_pest_break_family_change_is_a_break():
    out = facts.pest_cycle_break(["aman_rice", "lentil"], REF)
    assert out["breaks_cycle"] is True       # Poaceae -> Fabaceae
    assert "needs local review" in out["note"]

def test_pest_break_with_an_unknown_family_is_a_gap():
    out = facts.pest_cycle_break(["aman_rice", "dragonfruit"], REF)
    assert out["status"] == "gap"


# ---------------- nitrogen fixing ----------------

def test_lentil_fixes_nitrogen_with_a_source():
    out = facts.nitrogen_fixing("lentil")
    assert out["status"] == "assessed" and out["value"] is True
    assert out["source"]  # the legume_src cell from crops.csv

def test_wheat_does_not_fix_nitrogen():
    out = facts.nitrogen_fixing("wheat")
    assert out["status"] == "assessed" and out["value"] is False

def test_crop_not_in_the_table_is_a_gap():
    assert facts.nitrogen_fixing("dragonfruit")["status"] == "gap"


# ---------------- forage, residue, price ----------------

def test_wheat_has_no_forage_rows_so_forage_is_a_gap():
    assert facts.forage("wheat", REF)["status"] == "gap"

def test_mung_bean_forage_rows_are_cited():
    out = facts.forage("mung_bean", REF)
    assert out["status"] == "assessed"
    assert all(r["provenance"]["source_url"].startswith("http") for r in out["rows"])

def test_wheat_residue_row_is_the_cited_straw_ratio():
    out = facts.residue("wheat", REF)
    assert out["status"] == "assessed"
    items = [r["item"] for r in out["rows"]]
    assert "wheat.residue.straw_to_grain_ratio" in items

def test_price_prefers_the_farmgate_or_wholesale_row():
    out = facts.price("wheat", REF)
    if out["status"] == "assessed":          # the row may be a GAP in data/reference
        assert out["measure"]["unit"].startswith("BDT")
        assert out["item"]
    else:
        assert "no cited price" in out["reason"]

def test_lentil_price_exists_and_is_wholesale():
    out = facts.price("lentil", REF)
    assert out["status"] == "assessed"
    assert "wholesale" in out["item"] or "farmgate" in out["item"]

def test_price_for_unknown_crop_is_a_gap():
    assert facts.price("dragonfruit", REF)["status"] == "gap"

"""Five-heading cards: deterministic text, no AI, no 'predict'/'forecast',
gaps named under Information gaps, SAAO reminder under Risks."""

import json

import pytest

from strategies import cards
from strategy_fixtures import m

PEST_RULE = {"status": "assessed", "value": "not recommended to plant the same family in succession",
             "provenance": {"dataset": "Penn State Extension", "source_url": "https://example.org/psu",
                            "retrieved": "2026-11-12", "granule_or_file": "data/reference/crop_family.csv"},
             "note": "needs local review (US vegetable-garden source, not Bangladesh field crops)"}


def _strategy(sid="aman_rice@06-15>wheat", rabi="wheat", water=120.0, problems=3,
              legumes=0, price_gap=False):
    ind = {
        "water_use": {"status": "assessed", "worst20": m(water, "mm"), "median": m(water, "mm")},
        "problem_years": {"status": "assessed", "count": m(problems, "years"), "n": 24,
                          "lo": max(0, problems - 2), "hi": problems + 2, "level": 0.95,
                          "hazards_checked": ["heat_flowering"]},
        "bare_field_days": {"status": "assessed", "days_median": m(130, "days per year"),
                            "note": "from our windows, not satellite-observed", "per_year": [],
                            "years_not_counted": []},
        "erosion_exposure": {"status": "assessed", "index": m(1560.0, "relative index"),
                             "note": "relative ranking only"},
        "nitrogen_fixing": {"status": "assessed", "count": m(legumes, "crops"), "unknown": []},
        "organic_matter": {"status": "gap", "reason": "no cited residue row for wheat straw return"},
        "pest_cycle_break": {"status": "assessed", "breaks_cycle": False,
                             "families": ["Poaceae", "Poaceae"], "note": "needs local review"},
        "root_depth": {"status": "assessed", "by_crop": {}, "note": ""},
        "forage": {"status": "gap", "reason": "no cited forage row for wheat"},
        "market_price": ({"status": "gap", "reason": "no cited price for wheat"} if price_gap else
                         {"status": "assessed", "measure": m(35.0, "BDT/kg"),
                          "item": "wheat.price.farmgate_or_wholesale", "crop": "wheat"}),
    }
    return {"id": sid, "role": "alternative",
            "rotation": {"id": sid, "slots": [{"crop": "aman_rice"}, {"crop": rabi}]},
            "indicators": ind,
            "evidence_n_years": 24,
            "datasets": ["NASA GPM IMERG V07", "NASA POWER"]}


def test_card_has_exactly_the_five_headings():
    card = cards.five_heading_card(_strategy(), baseline=_strategy("base"), pest_rule=PEST_RULE)
    assert list(card) == ["why_suggested", "evidence", "benefits",
                          "information_gaps", "risks_to_check_locally"]
    for key in card:
        assert isinstance(card[key], list) and card[key]

def test_card_never_says_predict_or_forecast():
    card = cards.five_heading_card(_strategy(), baseline=_strategy("base"), pest_rule=PEST_RULE)
    text = json.dumps(card).lower()
    assert "predict" not in text and "forecast" not in text

def test_risks_include_the_saao_reminder_and_pest_local_review():
    card = cards.five_heading_card(_strategy(), baseline=_strategy("base"), pest_rule=PEST_RULE)
    text = " ".join(card["risks_to_check_locally"])
    assert "confirm with your SAAO" in text
    assert "needs local review" in text

def test_gaps_are_named_under_information_gaps():
    card = cards.five_heading_card(_strategy(price_gap=True), baseline=_strategy("base"),
                                   pest_rule=PEST_RULE)
    text = " ".join(card["information_gaps"])
    assert "no cited price for wheat" in text
    assert "no cited forage row for wheat" in text

def test_evidence_names_datasets_and_n_seasons():
    card = cards.five_heading_card(_strategy(), baseline=_strategy("base"), pest_rule=PEST_RULE)
    text = " ".join(card["evidence"])
    assert "24" in text and "IMERG" in text

def test_baseline_card_says_it_is_the_current_rotation():
    base = _strategy("base")
    base["role"] = "baseline"
    card = cards.five_heading_card(base, baseline=base, pest_rule=PEST_RULE)
    assert any("current rotation" in line for line in card["why_suggested"])

def test_why_suggested_compares_against_the_baseline_with_past_season_wording():
    better = _strategy(water=50.0, problems=1)
    base = _strategy("base", water=200.0, problems=10)
    card = cards.five_heading_card(better, baseline=base, pest_rule=PEST_RULE)
    text = " ".join(card["why_suggested"]).lower()
    assert "past seasons" in text or "tested on" in text

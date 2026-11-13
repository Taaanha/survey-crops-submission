"""Priority matrix (water, soil health, low risk, income): property tests in the
same spirit as tests/priorities (a gap is never scored as zero; direction holds;
normalisation is min-max; ties and no-contrast are explicit)."""

import pytest

from strategies import matrix
from strategy_fixtures import m


def _ind(water=100.0, legumes=0, problems=2, n=24, price=50.0,
         water_gap=None, soil_gap=None, risk_gap=None, income_gap=None):
    def gap(reason):
        return {"status": "gap", "reason": reason}
    return {
        "water_use": gap(water_gap) if water_gap else
        {"status": "assessed", "worst20": m(water, "mm"), "median": m(water, "mm")},
        "nitrogen_fixing": gap(soil_gap) if soil_gap else
        {"status": "assessed", "count": m(legumes, "crops"), "unknown": []},
        "problem_years": gap(risk_gap) if risk_gap else
        {"status": "assessed", "count": m(problems, "years"), "n": n,
         "lo": problems, "hi": problems, "level": 0.95},
        "market_price": gap(income_gap) if income_gap else
        {"status": "assessed", "measure": m(price, "BDT/kg"), "item": "x.price.wholesale",
         "crop": "x"},
    }


def strat(sid, **kw):
    return {"id": sid, "indicators": _ind(**kw)}


def test_best_on_water_is_the_lowest_irrigation():
    out = matrix.priority_matrix([strat("a", water=200), strat("b", water=50), strat("c", water=120)])
    assert out["best"]["water"] == ["b"]
    assert out["cells"]["b"]["water"]["normalised"] == 1.0

def test_best_on_income_is_the_highest_price():
    out = matrix.priority_matrix([strat("a", price=20), strat("b", price=80)])
    assert out["best"]["income"] == ["b"]

def test_a_gap_is_listed_not_scored_as_zero():
    out = matrix.priority_matrix([strat("a"), strat("b", income_gap="no cited price for wheat")])
    cell = out["cells"]["b"]["income"]
    assert cell["status"] == "gap"
    assert cell.get("normalised") is None
    assert "no cited price" in cell["reason"]
    assert out["best"]["income"] == ["a"]

def test_every_priority_gapped_leaves_best_none_with_reason():
    out = matrix.priority_matrix([strat("a", income_gap="gap"), strat("b", income_gap="gap")])
    assert out["best"]["income"] is None
    assert "not assessed" in out["best_reasons"]["income"]

def test_equal_values_are_flagged_no_contrast_and_tie_lists_everyone():
    out = matrix.priority_matrix([strat("a", water=100), strat("b", water=100)])
    assert out["cells"]["a"]["water"]["no_contrast"] is True
    assert out["best"]["water"] == ["a", "b"]

def test_normalised_values_stay_between_zero_and_one():
    out = matrix.priority_matrix([strat("a", water=10, legumes=2, problems=0, price=90),
                                  strat("b", water=300, legumes=0, problems=20, price=10)])
    for sid in ("a", "b"):
        for key in matrix.PRIORITIES:
            v = out["cells"][sid][key]["normalised"]
            assert v is None or 0.0 <= v <= 1.0

def test_low_risk_uses_the_problem_share_not_the_raw_count():
    # same count, different n: the smaller share must win
    out = matrix.priority_matrix([strat("a", problems=2, n=4), strat("b", problems=2, n=24)])
    assert out["best"]["low_risk"] == ["b"]

def test_income_metric_is_labelled_price_not_income_per_hectare():
    out = matrix.priority_matrix([strat("a")])
    assert "price" in out["priorities"]["income"]["metric"].lower()
    assert "per hectare" not in out["priorities"]["income"]["metric"].lower() or \
           "not income per hectare" in out["priorities"]["income"]["metric"].lower()

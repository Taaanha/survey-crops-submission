"""T2 acceptance tests (written before the module)."""

import random

import pytest

from priorities import PrioritiesError, normalise_weights, score_rotations
from priority_fixtures import fake_eval

KEYS = ("save_water", "soil_health", "lowest_risk", "flood_safety")


def three():
    return [fake_eval("wheat", irrigation=300.0, legumes=0, problems=0, flood=0),
            fake_eval("mustard", irrigation=250.0, legumes=0, problems=13, flood=13),
            fake_eval("lentil", irrigation=280.0, legumes=1, problems=2, flood=1)]


def order(result):
    return [r["id"] for r in result["ranked"]]


# ---- 1. property: raising save_water never lifts a thirstier rotation over a thriftier one ----

def test_raising_save_water_never_moves_a_higher_irrigation_rotation_above_a_lower_one():
    rng = random.Random(2)
    for _ in range(300):
        evals = [fake_eval(f"r{i}", irrigation=float(rng.randint(100, 900)),
                           legumes=rng.randint(0, 2), problems=rng.randint(0, 24),
                           flood=rng.randint(0, 12)) for i in range(rng.randint(3, 6))]
        # a pair that is equal on every metric except irrigation
        shared = dict(legumes=rng.randint(0, 2), problems=rng.randint(0, 24), flood=rng.randint(0, 12))
        evals += [fake_eval("low", irrigation=200.0, **shared), fake_eval("high", irrigation=500.0, **shared)]
        weights = {k: rng.random() for k in KEYS}
        weights["lowest_risk"] = max(weights["lowest_risk"], 0.01)   # never all zero
        raised = dict(weights, save_water=min(1.0, weights["save_water"] + rng.random()))
        before, after = order(score_rotations(evals, weights)), order(score_rotations(evals, raised))
        if before.index("low") < before.index("high"):
            assert after.index("low") < after.index("high"), (weights, raised)
        if raised["save_water"] > 0:
            assert after.index("low") < after.index("high"), raised


def test_save_water_alone_orders_by_irrigation():
    assert order(score_rotations(three(), {"save_water": 1})) == ["mustard", "lentil", "wheat"]


# ---- 2. weights ----

def test_weights_are_normalised_to_sum_one():
    w = normalise_weights({"save_water": 0.5, "lowest_risk": 0.25, "soil_health": 0.25})
    assert w == {"save_water": 0.5, "soil_health": 0.25, "lowest_risk": 0.25, "flood_safety": 0.0}
    w = normalise_weights({"save_water": 1, "lowest_risk": 1, "soil_health": 1, "flood_safety": 1})
    assert w == {k: 0.25 for k in KEYS}
    assert sum(normalise_weights({"save_water": 0.3, "flood_safety": 0.9}).values()) == pytest.approx(1)


def test_missing_keys_count_as_zero():
    assert normalise_weights({"lowest_risk": 0.4})["lowest_risk"] == 1.0


def test_all_zero_weights_are_a_clear_error():
    for weights in ({}, {k: 0 for k in KEYS}):
        with pytest.raises(PrioritiesError) as err:
            normalise_weights(weights)
        assert "at least one" in str(err.value)
    with pytest.raises(PrioritiesError):
        score_rotations(three(), {k: 0 for k in KEYS})


@pytest.mark.parametrize("bad", [{"save_water": -0.1}, {"save_water": 1.5}, {"save_water": "high"},
                                 {"save_water": float("nan")}, {"save_water": True},
                                 {"cheapest": 1}, [("save_water", 1)], None])
def test_bad_weights_are_rejected(bad):
    with pytest.raises(PrioritiesError):
        normalise_weights(bad)


# ---- 3. transparent components ----

def test_contributions_sum_to_the_total_score():
    rng = random.Random(5)
    for _ in range(100):
        evals = [fake_eval(f"r{i}", irrigation=float(rng.randint(100, 900)), legumes=rng.randint(0, 3),
                           problems=rng.randint(0, 24), flood=rng.randint(0, 12)) for i in range(5)]
        weights = {k: rng.random() for k in KEYS}
        weights["save_water"] = max(weights["save_water"], 0.01)
        for row in score_rotations(evals, weights)["ranked"]:
            parts = sum(c["contribution"] for c in row["components"].values())
            assert abs(parts - row["score"]) < 1e-9
            for c in row["components"].values():
                assert abs(c["weight"] * (c["normalised"] or 0.0) - c["contribution"]) < 1e-12


def test_each_component_shows_raw_normalised_weight_contribution():
    result = score_rotations(three(), {"save_water": 0.8, "lowest_risk": 0.4})
    top = result["ranked"][0]
    assert set(top["components"]) == set(KEYS)
    water = top["components"]["save_water"]
    assert set(water) >= {"raw", "normalised", "weight", "contribution", "direction", "label"}
    assert water["raw"]["unit"] == "mm" and water["raw"]["provenance"]["source_url"]
    assert water["weight"] == pytest.approx(2 / 3)
    assert result["weights"]["normalised"]["save_water"] == pytest.approx(2 / 3)
    assert result["weights"]["requested"]["save_water"] == 0.8


def test_min_max_normalisation_and_direction():
    result = score_rotations(three(), {"save_water": 1, "lowest_risk": 1, "soil_health": 1})
    by_id = {r["id"]: r["components"] for r in result["ranked"]}
    assert by_id["mustard"]["save_water"]["normalised"] == 1.0      # lowest irrigation = best
    assert by_id["wheat"]["save_water"]["normalised"] == 0.0
    assert by_id["lentil"]["soil_health"]["normalised"] == 1.0      # most legumes = best
    assert by_id["wheat"]["lowest_risk"]["normalised"] == 1.0       # fewest problem years = best
    assert by_id["mustard"]["lowest_risk"]["normalised"] == 0.0
    assert by_id["lentil"]["save_water"]["normalised"] == pytest.approx((300 - 280) / (300 - 250))
    assert by_id["lentil"]["lowest_risk"]["raw"]["value"] == pytest.approx(2 / 24)


def test_a_metric_where_all_options_are_equal_is_flagged_and_does_not_reorder():
    result = score_rotations(three(), {"soil_health": 0.2, "save_water": 0.8})
    assert result["ranked"][0]["components"]["soil_health"]["no_contrast"] is False   # lentil has 1
    equal = [fake_eval("a", legumes=0, irrigation=1.0), fake_eval("b", legumes=0, irrigation=2.0)]
    flat = score_rotations(equal, {"soil_health": 0.5, "save_water": 0.5})
    assert all(r["components"]["soil_health"]["no_contrast"] for r in flat["ranked"])
    assert order(flat) == ["a", "b"]


def test_unknown_legume_flag_is_never_scored_as_zero():
    evals = [fake_eval("a", unknown=("wheat",), legumes=0), fake_eval("b", legumes=0), fake_eval("c", legumes=1)]
    result = score_rotations(evals, {"soil_health": 1})
    assert [u["id"] for u in result["unranked"]] == ["a"]           # not ranked last as "0 legumes"
    assert "NEEDS SOURCE" in result["unranked"][0]["reason"]
    assert order(result) == ["c", "b"]
    # with soil health at weight 0 the unknown flag does not matter
    assert score_rotations(evals, {"save_water": 1})["unranked"] == []


def test_equal_values_give_half_and_no_nan_or_division_error():
    import math
    evals = [fake_eval("a", irrigation=5.0, legumes=1, problems=0, flood=0),
             fake_eval("b", irrigation=5.0, legumes=1, problems=0, flood=0)]
    result = score_rotations(evals, {k: 1 for k in ("save_water", "soil_health", "lowest_risk", "flood_safety")})
    for row in result["ranked"]:
        assert math.isfinite(row["score"]) and row["score"] == pytest.approx(0.5)
        for c in row["components"].values():
            assert c["normalised"] == 0.5 and c["no_contrast"] is True and math.isfinite(c["contribution"])


def test_unranked_entries_carry_reason_and_how_to_include():
    evals = [fake_eval("ok", problems=1, flood=1), fake_eval("wheat", problems=3, flood=None)]
    result = score_rotations(evals, {"flood_safety": 0.5, "save_water": 0.5})
    (entry,) = result["unranked"]
    assert entry["id"] == "wheat" and "not assessed" in entry["reason"]
    assert "wheat" in entry["how_to_include"] and "Flood safety" in entry["how_to_include"]
    assert "Set the flood_safety weight to 0" in entry["how_to_include"]
    # following the hint ranks it
    again = score_rotations(evals, {"save_water": 1})
    assert again["unranked"] == [] and len(again["ranked"]) == 2


def test_contributions_still_sum_to_the_score():
    evals = [fake_eval("a", irrigation=100.0, legumes=0, problems=2, flood=1),
             fake_eval("b", irrigation=300.0, legumes=2, problems=5, flood=3)]
    for row in score_rotations(evals, {"save_water": 0.3, "soil_health": 0.2, "lowest_risk": 0.3, "flood_safety": 0.2})["ranked"]:
        assert sum(c["contribution"] for c in row["components"].values()) == pytest.approx(row["score"])


def test_flood_safety_uses_only_flood_related_problem_years():
    evals = [fake_eval("dry_hit", problems=10, flood=0), fake_eval("wet_hit", problems=10, flood=10)]
    result = score_rotations(evals, {"flood_safety": 1})
    assert order(result) == ["dry_hit", "wet_hit"]
    assert result["ranked"][1]["components"]["flood_safety"]["raw"]["value"] == pytest.approx(10 / 24)


def test_rotations_not_assessed_on_a_weighted_metric_are_listed_not_scored_as_zero():
    evals = [fake_eval("ok", problems=1, flood=1), fake_eval("boro", problems=None, flood=None),
             fake_eval("noflood", problems=3, flood=None)]
    risk = score_rotations(evals, {"lowest_risk": 1})
    assert order(risk) == ["ok", "noflood"]
    assert [u["id"] for u in risk["unranked"]] == ["boro"] and "not assessed" in risk["unranked"][0]["reason"]
    flood = score_rotations(evals, {"flood_safety": 1})
    assert order(flood) == ["ok"] and {u["id"] for u in flood["unranked"]} == {"boro", "noflood"}
    water_only = score_rotations(evals, {"save_water": 1})       # unweighted gaps do not matter
    assert len(water_only["ranked"]) == 3 and water_only["unranked"] == []


def test_field_profile_hook_is_not_silently_ignored():
    with pytest.raises(NotImplementedError):
        score_rotations(three(), {"flood_safety": 1}, field_profile={"events": 2})


def test_ranking_is_deterministic_with_ties_broken_by_id():
    evals = [fake_eval("b"), fake_eval("a"), fake_eval("c")]
    assert order(score_rotations(evals, {"save_water": 1})) == ["a", "b", "c"]
    assert order(score_rotations(list(reversed(evals)), {"save_water": 1})) == ["a", "b", "c"]


def test_ranks_start_at_one_and_score_is_between_zero_and_one():
    result = score_rotations(three(), {k: 1 for k in KEYS})
    assert [r["rank"] for r in result["ranked"]] == [1, 2, 3]
    assert all(0.0 <= r["score"] <= 1.0 for r in result["ranked"])
    scores = [r["score"] for r in result["ranked"]]
    assert scores == sorted(scores, reverse=True)

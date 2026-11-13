"""T1 acceptance tests (written before the engine)."""

import json

import pandas as pd
import pytest

import risk_calendar as rc
from water_balance import crop_season

from rotation import candidate_rotations, evaluate_rotation, excluded_crops, load_context
from rotation_fixtures import crop_row, temp_spec, synthetic_weather, make_context

AMAN_SHORT = crop_row("aman_rice", "kharif2", 100, "0615", "0715", seedling="25-30")
AMAN_LONG = crop_row("aman_rice", "kharif2", 150, "0615", "0715", seedling="25-30")
WHEAT = crop_row("wheat", "rabi", 104, "1115", "1130")
MUSTARD = crop_row("mustard", "rabi", 97, "1015", "1115")
AMAN_JUL = {"crop": "aman_rice", "sow_mmdd": "07-15"}
AMAN_JUN = {"crop": "aman_rice", "sow_mmdd": "06-15"}


def rot(*slots):
    return {"id": ">".join(s["crop"] for s in slots), "slots": list(slots)}


def numbers_without_provenance(node, path="summary"):
    """Paths of numeric leaves that are not inside a {value, unit, provenance}."""
    bad = []
    if isinstance(node, dict):
        if {"value", "unit", "provenance"} <= set(node):
            prov = node["provenance"]
            if not all(prov.get(k) for k in ("dataset", "source_url", "retrieved", "granule_or_file")):
                bad.append(path + " (incomplete provenance)")
            return bad
        for k, v in node.items():
            bad += numbers_without_provenance(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            bad += numbers_without_provenance(v, f"{path}[{i}]")
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        if not path.endswith(".year"):       # a year label identifies a row; it is not a measurement
            bad.append(path)
    return bad


# 1. long Aman + mustard whose window ends before Aman harvest + turnaround
def test_long_aman_then_mustard_is_infeasible():
    w = synthetic_weather({})
    specs = {"mustard": temp_spec("mustard", (10, 15), (11, 15))}
    long_ctx = make_context([AMAN_LONG, MUSTARD], specs, w)
    out = evaluate_rotation("x", rot(AMAN_JUL, {"crop": "mustard"}), years=[2001, 2002, 2003],
                            context=long_ctx)
    # seedbed 15 Jul + 150 d = 12 Dec; + 7 d turnaround = 19 Dec > mustard window end 15 Nov
    assert [y["feasible"] for y in out["years"]] == [False, False, False]
    assert "window" in out["years"][0]["infeasible_reason"]
    assert out["summary"]["infeasible_years"]["value"] == 3
    # control: a 100-day Aman harvests 23 Oct, +7 = 30 Oct, inside the mustard window
    short_ctx = make_context([AMAN_SHORT, MUSTARD], specs, w)
    ok = evaluate_rotation("x", rot(AMAN_JUL, {"crop": "mustard"}), years=[2001], context=short_ctx)
    assert ok["years"][0]["feasible"] is True
    assert ok["years"][0]["slots"][1]["sowing_date"] == "2001-10-30"


# 2. determinism, synthetic and real data
def test_same_inputs_same_outputs_synthetic():
    ctx = make_context([AMAN_SHORT, WHEAT], {"wheat": temp_spec("wheat", (11, 15), (11, 30))},
                       synthetic_weather({}))
    args = ("x", rot(AMAN_JUL, {"crop": "wheat"}))
    a = evaluate_rotation(*args, years=[2001, 2002, 2003], context=ctx)
    b = evaluate_rotation(*args, years=[2001, 2002, 2003], context=ctx)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_same_inputs_same_outputs_real_data():
    first = candidate_rotations("cumilla")
    assert first == candidate_rotations("cumilla") and first
    a = evaluate_rotation("cumilla", first[0], years=[2005, 2006, 2007])
    b = evaluate_rotation("cumilla", first[0], years=[2005, 2006, 2007])
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# 3. the Kc-weighted water number is the existing water balance, unchanged
def test_irrigation_is_the_existing_kc_weighted_water_balance():
    ctx = load_context("cumilla")
    spec = ctx.specs["wheat"]
    sow = pd.Timestamp("2005-11-15")
    targets = rc.calibrate(spec, rc.mean_climate(ctx.weather["temp_mean_c"]))
    row = rc.season_row(spec, targets, ctx.weather, sow, ctx.water)
    direct = crop_season("wheat", sow, ctx.weather, ctx.water["kc_table"], ctx.water["crop_params"],
                         ctx.water["soil"])
    assert row["net_irrigation_mm"] == direct["net_irrigation_mm"]
    out = evaluate_rotation("cumilla", {"id": "t", "slots": [AMAN_JUL, {"crop": "wheat"}]},
                            years=[2005], context=ctx)
    wheat_slot = out["years"][0]["slots"][1]
    if wheat_slot["sowing_date"] == "2005-11-15":
        assert wheat_slot["irrigation_mm"]["value"] == direct["net_irrigation_mm"]


# 4. problems in X of N equals a hand count on a 3-year fixture
def test_problems_x_of_n_matches_hand_count():
    # wheat sown 15 Nov; flowering span = days 47..53 after sowing = 1-7 Jan of year+1.
    # 2001: 7 hot days (problem); 2002: 2 hot days (< hot_days = 3, no problem); 2003: 3 hot (problem)
    hot = {2001: pd.date_range("2002-01-01", "2002-01-07"),
           2002: pd.date_range("2003-01-01", "2003-01-02"),
           2003: pd.date_range("2004-01-02", "2004-01-04")}
    ctx = make_context([AMAN_SHORT, WHEAT], {"wheat": temp_spec("wheat", (11, 15), (11, 30))},
                       synthetic_weather(hot))
    out = evaluate_rotation("x", rot(AMAN_JUL, {"crop": "wheat"}), years=[2001, 2002, 2003],
                            context=ctx)
    assert [y["problem_year"] for y in out["years"]] == [True, False, True]
    s = out["summary"]
    assert (s["problem_years"]["value"], s["n_years"]["value"]) == (2, 3)
    assert "problems in 2 of 3 years" in s["problem_line"]


# 5. every numeric field in the summary (and the details) has a provenance object
def test_every_number_has_provenance():
    ctx = make_context([AMAN_SHORT, WHEAT, MUSTARD],
                       {"wheat": temp_spec("wheat", (11, 15), (11, 30)),
                        "mustard": temp_spec("mustard", (10, 15), (11, 15))}, synthetic_weather({}))
    out = evaluate_rotation("x", rot(AMAN_JUL, {"crop": "wheat"}), years=[2001, 2002, 2003],
                            context=ctx)
    assert numbers_without_provenance(out["summary"]) == []
    assert numbers_without_provenance(out["years"], "years") == []
    real = evaluate_rotation("cumilla", candidate_rotations("cumilla")[0], years=[2005, 2006])
    assert numbers_without_provenance(real["summary"]) == []
    assert numbers_without_provenance(real["years"], "years") == []


# extras: legumes are counted only where the table cites them; unknown is reported, not guessed
def test_legume_count_uses_only_cited_flags():
    lentil = crop_row("lentil", "rabi", 119, "1024", "1115", legume="yes")
    ctx = make_context([AMAN_SHORT, lentil, WHEAT],
                       {"lentil": temp_spec("lentil", (10, 24), (11, 15)),
                        "wheat": temp_spec("wheat", (11, 15), (11, 30))}, synthetic_weather({}))
    one = evaluate_rotation("x", rot(AMAN_JUL, {"crop": "lentil"}), years=[2001], context=ctx)
    assert one["summary"]["legume_count"]["value"] == 1
    two = evaluate_rotation("x", rot(AMAN_JUL, {"crop": "wheat"}), years=[2001], context=ctx)
    assert two["summary"]["legume_count"]["value"] == 0
    assert "wheat" in two["summary"]["legume_unknown_crops"]


# cross-check against the prebuilt risk calendar (built by the existing code)
def test_per_year_numbers_agree_with_the_prebuilt_risk_calendar():
    table = pd.read_csv(rc.RISK_CALENDAR_PATH)
    row = table[(table["district"] == "cumilla") & (table["crop"] == "wheat")
                & (table["sowing_mmdd"] == "11-15")].iloc[0]
    out = evaluate_rotation("cumilla", {"id": "t", "slots": [AMAN_JUN, {"crop": "wheat"}]})
    wheat = [y["slots"][1] for y in out["years"]]
    assert {s["sowing_date"][5:] for s in wheat} == {"11-15"}
    mean = sum(s["irrigation_mm"]["value"] for s in wheat) / len(wheat)
    assert abs(mean - row["irrigation_mm_mean"]) < 0.1
    assert sum(1 for s in wheat if s["problem"]) == row["problem_years"]


def test_nothing_assessed_is_not_reported_as_zero_problems():
    out = evaluate_rotation("cumilla", {"id": "t", "slots": [AMAN_JUN, {"crop": "boro_rice"}]},
                            years=[2005, 2006])
    assert out["summary"]["problem_years"] is None
    assert "not assessed" in out["summary"]["problem_line"]


def test_candidates_and_exclusions():
    ids = [r["id"] for r in candidate_rotations("cumilla")]
    assert "aman_rice@06-15>wheat" in ids
    assert "aman_rice@07-15>wheat" not in ids          # 15 Jul + 135 d + 7 d is after 30 Nov
    assert "aman_rice@07-15>wheat" in [r["id"] for r in
                                       candidate_rotations("cumilla", include_infeasible=True)]
    names = {e["crop"] for e in excluded_crops()}
    assert {"potato", "mung_bean"} <= names


def test_unusable_crop_and_unknown_district_are_refused():
    with pytest.raises(ValueError, match="potato"):
        evaluate_rotation("cumilla", {"id": "t", "slots": [AMAN_JUN, {"crop": "potato"}]})
    with pytest.raises(ValueError, match="unknown district"):
        load_context("atlantis")


def test_aman_duration_basis_moves_the_harvest():
    ctx = make_context([AMAN_SHORT, MUSTARD], {"mustard": temp_spec("mustard", (10, 15), (11, 15))},
                       synthetic_weather({}))
    args = ("x", rot(AMAN_JUL, {"crop": "mustard"}))
    seedbed = evaluate_rotation(*args, years=[2001], context=ctx)
    assert seedbed["years"][0]["slots"][0]["harvest_date"] == "2001-10-23"
    ctx.aman_duration_from = "transplanting"          # + 30 days (high end of the cited 25-30)
    later = evaluate_rotation(*args, years=[2001], context=ctx)
    assert later["years"][0]["slots"][0]["harvest_date"] == "2001-11-22"
    assert later["years"][0]["feasible"] is False     # 22 Nov + 7 d = 29 Nov is after the 15 Nov window end

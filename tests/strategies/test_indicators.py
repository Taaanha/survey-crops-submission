"""W4 indicators: bare-field days, problem-year bootstrap range, heavy-rain days,
slope class and erosion exposure. Every expected number is a hand count."""

import numpy as np
import pandas as pd
import pytest

from strategies import indicators as ind
from strategy_fixtures import fake_eval, two_clean_years, year_row, slot


# ---------------- bare-field days (hand-counted) ----------------

def test_bare_days_hand_count():
    # 365 - (135 + 100) = 130 in both years (see strategy_fixtures docstring)
    out = ind.bare_field_days(fake_eval())
    assert out["status"] == "assessed"
    assert [r["days"] for r in out["per_year"]] == [130, 130]
    assert out["days_median"]["value"] == 130
    assert out["days_median"]["unit"] == "days per year"

def test_bare_days_label_says_windows_not_satellite():
    out = ind.bare_field_days(fake_eval())
    assert "from our windows" in out["note"]
    assert "not satellite-observed" in out["note"]

def test_bare_days_skips_infeasible_and_incomplete_years():
    years = two_clean_years() + [
        year_row(2003, [slot("aman_rice", "2003-06-15", None)], feasible=False),
        year_row(2004, [slot("aman_rice", "2004-06-15", None)], feasible=True),  # no harvest date
    ]
    out = ind.bare_field_days(fake_eval(years=years))
    assert [r["year"] for r in out["per_year"]] == [2001, 2002]
    assert out["years_not_counted"] == [2003, 2004]

def test_bare_days_with_no_countable_year_is_a_gap():
    years = [year_row(2001, [slot("aman_rice", "2001-06-15", None)], feasible=False)]
    out = ind.bare_field_days(fake_eval(years=years))
    assert out["status"] == "gap"
    assert "no feasible year" in out["reason"]


# ---------------- problem-year bootstrap range ----------------

def test_problem_range_all_zero_flags_is_zero_to_zero():
    ev = fake_eval(years=two_clean_years((False, False)), problems=0)
    out = ind.problem_year_range(ev)
    assert (out["count"]["value"], out["lo"], out["hi"]) == (0, 0, 0)

def test_problem_range_all_one_flags_is_n_to_n():
    ev = fake_eval(years=two_clean_years((True, True)), problems=2)
    out = ind.problem_year_range(ev)
    assert (out["count"]["value"], out["lo"], out["hi"]) == (2, 2, 2)

def test_problem_range_is_deterministic_and_brackets_the_count():
    years = two_clean_years((True, False)) + [
        year_row(2003, [slot("aman_rice", "2003-06-15", "2003-10-28")], problem=True)]
    ev = fake_eval(years=years, problems=2)
    a, b = ind.problem_year_range(ev), ind.problem_year_range(ev)
    assert (a["lo"], a["hi"]) == (b["lo"], b["hi"])
    assert a["lo"] <= a["count"]["value"] <= a["hi"]
    assert a["n_boot"] == ind.N_BOOT and a["seed"] == ind.SEED and a["level"] == ind.LEVEL

def test_problem_range_not_assessed_without_a_sourced_hazard():
    ev = fake_eval(problems=None, checked=())
    out = ind.problem_year_range(ev)
    assert out["status"] == "gap"
    assert "no sourced hazard" in out["reason"]


# ---------------- heavy-rain days ----------------

def _rain(days_by_year):
    """Daily series: each year gets the asked number of 50 mm days, rest 0."""
    idx = pd.date_range("2001-01-01", "2002-12-31", freq="D")
    s = pd.Series(0.0, index=idx)
    for year, n in days_by_year.items():
        s.loc[f"{year}-01-01":f"{year}-01-{n:02d}"] = 50.0
    return s

def test_heavy_rain_days_mean_hand_count():
    out = ind.heavy_rain_days_per_year(_rain({2001: 3, 2002: 5}), years=(2001, 2002))
    assert out is not None
    # (3 + 5) / 2 = 4.0, and the BMD 44 mm row exists in data/reference
    assert out["days_mean"]["value"] == 4.0
    assert out["threshold"]["value"] >= 20
    assert out["which"] in ("cited reference row", "ETCCDI R20mm fallback")

def test_heavy_rain_uses_a_cited_threshold_and_says_which():
    out = ind.heavy_rain_days_per_year(_rain({2001: 1, 2002: 1}), years=(2001, 2002))
    prov = out["days_mean"]["provenance"]
    assert prov["source_url"].startswith("http")
    assert "cell-mean" in prov["note"] or "cell-mean" in out["note"]


# ---------------- slope class ----------------

def test_slope_class_terciles_hand_count(tmp_path):
    rows = ["district,elev_mean_m,coverage_elev_mean_m,slope_mean_deg,coverage_slope_mean_deg"]
    # 9 districts, slopes 1..9: terciles at 3.6666 and 6.3333 -> 1-3 low, 4-6 mid, 7-9 high
    for i in range(1, 10):
        rows.append(f"d{i},10,1.0,{float(i)},1.0")
    p = tmp_path / "nasadem.csv"
    p.write_text("\n".join(rows), encoding="utf-8")
    assert ind.slope_class("d2", path=str(p))["class"] == 1
    assert ind.slope_class("d5", path=str(p))["class"] == 2
    assert ind.slope_class("d9", path=str(p))["class"] == 3

def test_slope_class_says_relative_ranking_and_our_breakpoints():
    out = ind.slope_class("cumilla")
    assert out["class"] in (1, 2, 3)
    assert "relative ranking only" in out["note"]
    assert "our choice" in out["note"]

def test_slope_class_unknown_district_is_a_gap():
    out = ind.slope_class("atlantis")
    assert out["status"] == "gap"


# ---------------- erosion exposure ----------------

def test_erosion_exposure_is_the_hand_product():
    bare = {"status": "assessed", "days_median": {"value": 100, "unit": "days per year",
            "provenance": {"dataset": "t", "source_url": "https://x", "retrieved": "2026-11-12",
                           "granule_or_file": "f", "note": ""}}, "note": "n"}
    heavy = {"days_mean": {"value": 4.0, "unit": "days per year",
             "provenance": {"dataset": "t", "source_url": "https://x", "retrieved": "2026-11-12",
                            "granule_or_file": "f", "note": ""}},
             "threshold": {"value": 44.0}, "which": "cited reference row", "note": ""}
    slope = {"status": "assessed", "class": 3, "note": "relative ranking only"}
    out = ind.erosion_exposure(bare, heavy, slope)
    assert out["status"] == "assessed"
    assert out["index"]["value"] == 100 * 4.0 * 3
    assert "relative" in out["index"]["unit"]

def test_erosion_exposure_with_a_gap_component_is_a_gap_not_zero():
    gap = {"status": "gap", "reason": "no feasible year"}
    heavy = {"days_mean": {"value": 4.0, "unit": "d", "provenance": {}}, "which": "x", "note": ""}
    slope = {"status": "assessed", "class": 2, "note": ""}
    out = ind.erosion_exposure(gap, heavy, slope)
    assert out["status"] == "gap"
    assert "0" != str(out.get("index"))
    assert "no feasible year" in out["reason"]

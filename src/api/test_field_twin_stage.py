"""
T0: the Field Twin heat flag must judge each crop stage against that stage's own
sourced limit (wheat: 31 C at anthesis, 35.4 C in grain fill), not the
flowering limit on every day.

Run from the repo root: python -m pytest src/api/test_field_twin_stage.py -q
"""

import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import app as api  # noqa: E402

ANTHESIS, GRAINFILL = 31.0, 35.4   # data/reference/crop_thresholds.csv (wheat.heat.*)


def limit(hazard, value, span):
    return {"event": "heat", "hazard": hazard, "limit": {"value": value}, "span": span}


def week(tmax, first_day, limits):
    """A 7-day week starting `first_day` days after sowing, all days at `tmax` C."""
    row = {"tmax_highest_c": tmax, "tmin_mean_c": 10.0, "rain_mm": 0.0,
           "stress_days": 0, "irrigation_events": 0}
    return api.twin_week_events(row, limits, tmax=np.full(7, float(tmax)),
                                tmin=np.full(7, 10.0), first_day=first_day)["events"]


LIMITS = [limit("heat_anthesis", ANTHESIS, (50, 56)),       # flowering window
          limit("heat_grainfill", GRAINFILL, (57, 90))]     # grain fill


def test_grain_fill_day_is_judged_against_the_grain_fill_limit():
    # 33 C is above the anthesis limit (31) but below the grain-fill limit (35.4).
    assert "heat" not in week(33.0, 60, LIMITS)
    assert "heat" in week(36.0, 60, LIMITS)


def test_anthesis_day_is_judged_against_the_anthesis_limit():
    assert "heat" in week(33.0, 50, LIMITS)
    assert "heat" not in week(30.0, 50, LIMITS)


def test_week_outside_every_heat_stage_is_never_heat_flagged():
    assert "heat" not in week(40.0, 10, LIMITS)


def test_week_straddling_two_stages_uses_each_days_own_limit():
    # days 53-59: 53-56 anthesis (limit 31), 57-59 grain fill (limit 35.4)
    tmax = np.array([30, 30, 30, 30, 33, 33, 33], dtype=float)   # 33 only on grain-fill days
    row = {"tmax_highest_c": 33.0, "tmin_mean_c": 10.0, "rain_mm": 0.0,
           "stress_days": 0, "irrigation_events": 0}
    ev = api.twin_week_events(row, LIMITS, tmax=tmax, tmin=np.full(7, 10.0), first_day=53)["events"]
    assert "heat" not in ev
    tmax[1] = 33.0   # 33 C on an anthesis day (day 54)
    row2 = dict(row)
    ev2 = api.twin_week_events(row2, LIMITS, tmax=tmax, tmin=np.full(7, 10.0), first_day=53)["events"]
    assert "heat" in ev2


def test_twin_heat_limits_carry_their_stage_span():
    out = api.twin_heat_limits("wheat", {"flowering": 50, "maturity": 90})
    spans = {l["hazard"]: l["span"] for l in out}
    assert spans["heat_anthesis"] == (47, 53)          # 7-day window centred on day 50
    assert spans["heat_grainfill"] == (54, 90)
    values = {l["hazard"]: l["limit"]["value"] for l in out}
    assert values["heat_anthesis"] == ANTHESIS and values["heat_grainfill"] == GRAINFILL


# ---- value-level test: limits come from the reference table, not from this file ----

def _reference_limit(item):
    from reference import load_reference
    rows = load_reference().rows(item)
    assert len(rows) >= 1, item
    return float(rows.iloc[0]["value"])


def test_33c_is_flagged_at_anthesis_but_not_in_grain_fill_using_reference_limits():
    anthesis = _reference_limit("wheat.heat.anthesis_tmax")
    grainfill = _reference_limit("wheat.heat.grainfill_tmax")
    assert anthesis < 33.0 < grainfill, "the test day must sit between the two sourced limits"
    limits = api.twin_heat_limits("wheat", {"flowering": 50, "maturity": 90})
    anth_span = {l["hazard"]: l["span"] for l in limits}["heat_anthesis"]
    fill_span = {l["hazard"]: l["span"] for l in limits}["heat_grainfill"]
    # the app's own limits must equal the table's
    assert {l["hazard"]: l["limit"]["value"] for l in limits} == {
        "heat_anthesis": anthesis, "heat_grainfill": grainfill}
    assert "heat" in week(33.0, anth_span[0], limits)         # anthesis: flagged
    assert "heat" not in week(33.0, fill_span[0] + 1, limits)  # grain fill: not flagged

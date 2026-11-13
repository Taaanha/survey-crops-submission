"""T3b: per-pixel event metrics on synthetic series (written before the code).

Series use 1 = wet, 0 = dry, 255 = no observation on a list of ISO dates. Rules (data/reference/
field_profile_rules.csv): an event starts at the first observed wet date after >= 2 observed dry
dates (or at the series start); it ends at the first observed dry date confirmed by the next
observed date also dry. Nothing is interpolated."""

import numpy as np
import pytest

from field_profile import (NO_OBS, STATUS, binary_water, load_rules, pixel_events,
                           profile_stack)

RULES = dict(min_obs_per_event=2, max_drain_window_days=12, dry_obs_to_separate_events=2)


def dates(n, step=6, start="2024-08-21"):
    base = np.datetime64(start)
    return [str(base + int(i * step)) for i in range(n)]


def run(series, step=6, **kw):
    d = dates(len(series), step)
    return d, pixel_events(d, np.array(series, dtype=np.uint8), **{**RULES, **kw})


# (a) simple flood -> correct drain date
def test_simple_flood_drain_date():
    d, r = run([0, 0, 1, 1, 1, 0, 0, 0])
    assert r["n_events"] == 1 and r["status"] == "ok"
    e = r["events"][0]
    assert e["start_date"] == d[2] and e["last_wet_date"] == d[4]
    assert e["drain_date"] == d[5]                     # first observed dry date, confirmed by d[6]
    assert e["drain_window"] == [d[4], d[5]] and e["gap_days"] == 6
    assert e["inundation_days_min"] == 12              # d[2] -> d[4]
    assert e["inundation_days_max"] == 24              # last dry before start d[1] -> drain d[5]
    assert r["first_wet_date"] == d[2]
    assert r["drain_date"] == d[5] and r["drain_window"] == [d[4], d[5]]
    assert r["last_wet_date"] == d[4] and r["first_dry_date"] == d[5]
    assert r["gap_days"] == 6


# (b) cloud gap -> window and gap_days, no interpolation
def test_cloud_gap_gives_window_not_a_guess():
    d, r = run([0, 0, 1, 1, NO_OBS, 0, 0])             # gap 12 days = the limit
    e = r["events"][0]
    assert r["status"] == "ok"
    assert e["last_wet_date"] == d[3] and e["drain_date"] == d[5]
    assert e["drain_window"] == [d[3], d[5]] and e["gap_days"] == 12
    assert e["window_unobserved_dates"] == 1           # d[4] had no observation


def test_gap_beyond_limit_is_too_few_and_has_no_drain_date():
    d, r = run([0, 0, 1, 1, NO_OBS, NO_OBS, 0, 0])     # gap 18 days > 12
    e = r["events"][0]
    assert r["status"] == "too few observations"
    assert e["drain_date"] is None and r["drain_date"] is None
    assert e["gap_days"] == 18 and e["window_unobserved_dates"] == 2   # reported, not interpolated


# (c) wet blip, one dry, wet again = one event unless 2 dry
def test_one_dry_between_wet_is_one_event():
    d, r = run([0, 0, 1, 0, 1, 1, 0, 0])
    assert r["n_events"] == 1
    assert r["events"][0]["last_wet_date"] == d[5]
    assert r["events"][0]["drain_date"] == d[6]


def test_two_dry_dates_split_events():
    d, r = run([0, 0, 1, 1, 0, 0, 1, 1, 0, 0])
    assert r["n_events"] == 2
    assert [e["start_date"] for e in r["events"]] == [d[2], d[6]]
    assert [e["drain_date"] for e in r["events"]] == [d[4], d[8]]


def test_dry_confirmation_skips_missing_dates():
    # wet, dry (d4), no obs, dry (d6): two dry OBSERVATIONS confirm the drain at d4
    d, r = run([0, 0, 1, 1, 0, NO_OBS, 0, 0])
    assert r["events"][0]["drain_date"] == d[4]


# (d) never wet
def test_never_wet_has_no_events():
    d, r = run([0, 0, 0, 255, 0])
    assert r["n_events"] == 0 and r["status"] == "no event"
    assert r["first_wet_date"] is None and r["drain_date"] is None and r["events"] == []
    assert r["n_observations"] == 4


def test_never_observed_is_not_zero_events():
    d, r = run([255, 255, 255])
    assert r["status"] == "no observations" and r["n_events"] is None


# (f) too few observations
def test_single_wet_observation_is_too_few():
    d, r = run([0, 0, 1, 0, 0, 0])
    assert r["n_events"] == 1 and r["status"] == "too few observations"
    assert r["events"][0]["drain_date"] is None and r["drain_date"] is None
    assert r["events"][0]["n_obs_event"] == 1


def test_min_obs_rule_is_a_parameter():
    d, r = run([0, 0, 1, 0, 0, 0], min_obs_per_event=1)
    assert r["status"] == "ok" and r["events"][0]["drain_date"] == d[3]


# series edges
def test_wet_at_series_start_is_left_censored():
    d, r = run([1, 1, 0, 0, 0])
    e = r["events"][0]
    assert e["start_date"] == d[0] and e["left_censored"] is True
    assert e["inundation_days_max"] is None            # start unknown
    assert e["inundation_days_min"] == 6 and e["drain_date"] == d[2]


def test_still_wet_at_series_end_has_no_drain():
    d, r = run([0, 0, 1, 1, 1])
    assert r["status"] == "still wet at series end"
    assert r["drain_date"] is None and r["events"][0]["inundation_days_max"] is None


def test_single_dry_at_end_is_not_confirmed():
    d, r = run([0, 0, 1, 1, 0])
    assert r["status"] == "drain not confirmed" and r["drain_date"] is None


# (e) a pixel that is only "inundated vegetation" all season
def test_binary_water_views():
    states = np.array([2, 1, 0, 255], dtype=np.uint8)
    assert binary_water(states, "open_water").tolist() == [1, 0, 0, 255]
    assert binary_water(states, "any_water").tolist() == [1, 1, 0, 255]
    with pytest.raises(ValueError):
        binary_water(states, "water")


def test_paddy_pixel_open_water_zero_events_any_water_reports_it():
    d = dates(8)
    stack = np.zeros((8, 1, 2), dtype=np.uint8)
    stack[2:6, 0, 0] = 1        # pixel 0: inundated vegetation only (standing Aman paddy)
    stack[2:6, 0, 1] = 2        # pixel 1: open water
    ow = profile_stack(d, stack, "open_water", RULES)
    aw = profile_stack(d, stack, "any_water", RULES)
    assert ow["n_events"][0, 0] == 0 and ow["n_events"][0, 1] == 1
    assert aw["n_events"][0, 0] == 1 and aw["n_events"][0, 1] == 1
    assert STATUS[int(ow["status"][0, 0])] == "no event"
    assert STATUS[int(aw["status"][0, 0])] == "ok"


def test_profile_stack_matches_pixel_events_and_marks_nodata():
    rng = np.random.default_rng(3)
    d = dates(14)
    stack = rng.choice([0, 1, 2, 255], size=(14, 6, 7), p=[.45, .15, .2, .2]).astype(np.uint8)
    out = profile_stack(d, stack, "open_water", RULES)
    base = np.datetime64("1970-01-01")
    for y in range(6):
        for x in range(7):
            r = pixel_events(d, binary_water(stack[:, y, x], "open_water"), **RULES)
            assert STATUS[int(out["status"][y, x])] == r["status"]
            assert out["n_events"][y, x] == (-1 if r["n_events"] is None else r["n_events"])
            if r["drain_date"] is None:
                assert out["drain_date"][y, x] == -1
            else:
                days = int((np.datetime64(r["drain_date"]) - base).astype(int))
                assert out["drain_date"][y, x] == days
                assert out["gap_days"][y, x] == r["gap_days"]


def test_rules_load_from_csv():
    rules = load_rules()
    assert rules["hand_masked_as"] in ("not_water", "no_observation")
    assert rules["min_obs_per_event"] >= 1 and rules["max_drain_window_days"] > 0
    assert rules["dry_obs_to_separate_events"] == 2
    assert 0 < rules["peak_min_observed_share"] <= 1

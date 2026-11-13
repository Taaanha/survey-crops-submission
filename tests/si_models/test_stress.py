"""Problem 2 (stressed seasons): hand-worked flags, event scoring and the no-leak proof."""

import numpy as np
import pandas as pd

from si_models import stress
from si_models.features import KEY

COLS = ["u", "v"]


def _features(seed=1, years=range(2001, 2013), districts=("a", "b", "c")):
    rng = np.random.default_rng(seed)
    rows = [{"district": d, "season_year": y, "season": "rabi", "u": rng.normal(), "v": rng.normal()}
            for d in districts for y in years]
    f = pd.DataFrame(rows)
    f.loc[(f.district == "a") & (f.season_year == 2007), ["u", "v"]] = [9.0, -9.0]   # one extreme season
    return f


def test_zscore_flag_hand_worked():
    assert stress.zscore_flag([0.5, -1.9]) is False
    assert stress.zscore_flag([0.5, -2.0]) is True          # at the limit counts
    assert stress.zscore_flag([2.5, 0.0], limit=3.0) is False
    assert np.isnan(stress.zscore_flag([np.nan, 5.0]))      # missing input: not assessed, never False


def test_forest_cutoff_is_a_training_quantile_with_a_floor():
    scores = np.arange(10, dtype=float)
    assert stress.forest_cutoff(scores, 0.5) == np.quantile(scores, 0.5)
    assert stress.forest_cutoff(scores, 0.0) == np.quantile(scores, 0.1)   # floor: one of ten rows


def test_loyo_stress_flags_the_extreme_season_with_both_methods():
    flags = stress.loyo_stress(_features(), COLS)
    assert len(flags) == 36 and set(flags.n_train) == {33}                  # 3 districts x 11 other years
    hit = flags[(flags.district == "a") & (flags.season_year == 2007)].iloc[0]
    assert bool(hit.flag_a)
    assert bool(hit.flag_b) and hit.score_b <= hit.cutoff_b


def test_loyo_stress_is_repeatable_with_the_fixed_seed():
    a, b = stress.loyo_stress(_features(), COLS), stress.loyo_stress(_features(), COLS)
    pd.testing.assert_frame_equal(a, b)


def test_no_leak_changing_the_evaluation_year_changes_nothing_else():
    """Proof that no information from the evaluation year reaches the fitted model: rewrite the 2007
    values of districts a and b and check that the model used for 2007 is identical (same cut-off)
    and that district c, whose own 2007 values are untouched, gets exactly the same score and flags."""
    f = _features()
    g = f.copy()
    change = (g.season_year == 2007) & (g.district != "c")       # district c keeps its 2007 values
    g.loc[change, ["u", "v"]] = [[50.0, 50.0]] * int(change.sum())
    r1 = stress.loyo_stress(f, COLS).set_index(KEY)
    r2 = stress.loyo_stress(g, COLS).set_index(KEY)
    k = ("c", 2007, "rabi")
    # same fitted model for the 2007 fold: cut-off identical, and the unchanged row scores identically
    assert r1.loc[k, "cutoff_b"] == r2.loc[k, "cutoff_b"]
    assert r1.loc[k, "score_b"] == r2.loc[k, "score_b"]
    assert r1.loc[k, "flag_a"] == r2.loc[k, "flag_a"]
    assert r1.loc[("a", 2007, "rabi"), "cutoff_b"] == r2.loc[("a", 2007, "rabi"), "cutoff_b"]


def test_training_rows_never_include_the_test_year(monkeypatch):
    seen = []
    real = stress.fit_forest

    def spy(z_train, seed=stress.SEED):
        seen.append(len(z_train))
        return real(z_train, seed)

    monkeypatch.setattr(stress, "fit_forest", spy)
    f = _features()
    stress.loyo_stress(f, COLS)
    assert seen == [len(f) - 3] * 12            # every fold: all rows minus the 3 rows of the held-out year


def test_rows_with_missing_features_are_not_assessed():
    f = _features()
    f.loc[(f.district == "b") & (f.season_year == 2003), "u"] = np.nan
    flags = stress.loyo_stress(f, COLS).set_index(KEY)
    row = flags.loc[("b", 2003, "rabi")]
    assert np.isnan(row.flag_a) and np.isnan(row.flag_b)


def _flags():
    return pd.DataFrame({
        "district": ["a", "a", "a", "b", "b"], "season_year": [2001, 2002, 2003, 2001, 2002], "season": "rabi",
        "flag_a": [True, False, False, True, np.nan], "flag_b": [False, False, True, True, np.nan]})


def test_score_against_events_hand_worked():
    events = pd.DataFrame({"district": ["a", "b", "b"], "season_year": [2001, 2001, 2002], "season": "rabi"})
    s = stress.score_against_events(_flags(), events, "flag_a")
    # assessed rows: 4 (b 2002 is NaN). events assessed: a2001 (flagged), b2001 (flagged) -> 2 of 2
    assert (s["hits"], s["n_events_assessed"], s["n_events_listed"]) == (2, 2, 3)
    assert (s["flags_outside_events"], s["n_other_seasons"]) == (0, 2)
    assert s["hit_rate"]["value"] == 1.0 and s["hit_rate"]["n"] == 2
    b = stress.score_against_events(_flags(), events, "flag_b")
    assert (b["hits"], b["flags_outside_events"]) == (1, 1)
    assert b["outside_rate"]["value"] == 0.5


def test_no_events_means_not_assessed_and_the_app_keeps_method_a():
    empty = pd.DataFrame(columns=KEY)
    res = stress.compare(_flags(), empty)
    assert res["method_a"]["n_events_assessed"] == 0 and np.isnan(res["method_a"]["hit_rate"]["value"])
    assert res["use"] == "A"


def test_b_does_not_win_on_two_events():
    events = pd.DataFrame({"district": ["a", "b"], "season_year": [2003, 2001], "season": "rabi"})
    res = stress.compare(_flags(), events)       # B flags both, A flags one: still too few events to call a win
    assert res["method_b"]["hits"] == 2 and res["method_a"]["hits"] == 1
    assert res["use"] == "A"


def test_event_summary_counts_one_regional_event_once():
    # a and b are hit by the SAME event in 2001: one independent event, flagged in 2 of 2 districts
    events = pd.DataFrame({"district": ["a", "b", "a"], "season_year": [2001, 2001, 2003], "season": "rabi",
                           "event": ["flood", "flood", "other"]})
    s = stress.event_summary(_flags(), events, "flag_a")
    assert (s["n_events"], s["n_events_any_flag"]) == (2, 1)
    flood = [e for e in s["events"] if e["event"] == "flood"][0]
    assert flood["districts_assessed"] == ["a", "b"] and flood["districts_flagged"] == ["a", "b"]
    # an event whose district-season was not assessed (b 2002 is NaN) is not counted
    none = stress.event_summary(_flags(), pd.DataFrame({"district": ["b"], "season_year": [2002], "season": "rabi",
                                                        "event": ["x"]}), "flag_a")
    assert none["n_events"] == 0

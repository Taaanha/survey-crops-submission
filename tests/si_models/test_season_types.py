"""Problem 3 (season types): hand-worked labels, silhouette, k choice and leave-one-year-out."""

import numpy as np
import pandas as pd
import pytest

from si_models import season_types as st


def test_percentile_label_hand_worked():
    rain, tmax = np.arange(1.0, 11.0), np.arange(21.0, 31.0)      # 80th percentile: 8.2 and 28.2
    assert st.percentile_label(rain, tmax, 9.0, 25.0) == "wet"
    assert st.percentile_label(rain, tmax, 5.0, 29.0) == "hot"
    assert st.percentile_label(rain, tmax, 8.2, 28.2) == "hot and wet"   # at the cut counts
    assert st.percentile_label(rain, tmax, 8.1, 28.1) == "typical"
    assert st.percentile_label(rain, tmax, np.nan, 25.0) is None
    assert st.percentile_label(rain[:4], tmax[:4], 9.0, 25.0) is None    # fewer than 5 other years


def test_heldout_silhouette_hand_worked():
    z_train = np.array([[0.0, 0.0], [0.0, 2.0], [10.0, 0.0]])
    labels = np.array(["x", "x", "y"], dtype=object)
    # point (0, 1): a = mean(1, 1) = 1; b = distance to (10, 0) = sqrt(101)
    s = st.heldout_silhouette(z_train, labels, [0.0, 1.0], "x")
    assert s == pytest.approx((np.sqrt(101) - 1) / np.sqrt(101))
    assert st.heldout_silhouette(z_train, labels, [10.0, 0.0], "x") < 0          # wrong group: negative
    assert np.isnan(st.heldout_silhouette(z_train, labels, [0.0, 1.0], "z"))     # label unseen in training
    assert np.isnan(st.heldout_silhouette(z_train[:2], labels[:2], [0.0, 1.0], "x"))  # only one label


def _blobs(k, n=30, seed=0):
    rng = np.random.default_rng(seed)
    centres = np.array([[0, 0], [8, 0], [0, 8], [8, 8]])[:k]
    return np.vstack([c + rng.normal(scale=0.3, size=(n, 2)) for c in centres])


@pytest.mark.parametrize("k", [2, 3, 4])
def test_choose_k_finds_the_number_of_clear_groups(k):
    best, scores = st.choose_k(_blobs(k))
    assert best == k and set(scores) == {2, 3, 4, 5}


def _features(years=range(2001, 2015)):
    rng = np.random.default_rng(3)
    rows = []
    for d in ("a", "b"):
        for y in years:
            wet = y % 2 == 0                       # even years wet and cool, odd years dry and hot
            rows.append({"district": d, "season_year": y, "season": "kharif2",
                         "rain_total_mm": (1500 if wet else 700) + rng.normal(scale=20),
                         "tmax_mean_c": (30 if wet else 33) + rng.normal(scale=0.1)})
    return pd.DataFrame(rows)


def test_loyo_season_types_on_two_clear_groups():
    res, centres = st.loyo_season_types(_features())
    assert len(res) == 28 and len(centres) == 2 and set(res.k) == {2}
    assert res.stable_b.mean() == 1.0 and res.sil_b.min() > 0.5
    out = st.compare(res, centres)
    assert out["use"] in ("A", "B") and out["method_b"]["k_all_years"] == 2
    assert out["method_a"]["stability"]["n"] == 28 and out["silhouette_b_minus_a"]["n"] > 0


def test_loyo_season_types_no_leak():
    """Rewriting the held-out year's values in one district must not change the label, stability
    inputs or silhouette of the other district's row for that year beyond its own values: the fold
    model is fitted on the other years only, so the unchanged row gets the same type and k."""
    f = _features()
    g = f.copy()
    g.loc[(g.season_year == 2008) & (g.district == "a"), ["rain_total_mm", "tmax_mean_c"]] = [5000.0, 45.0]
    r1, _ = st.loyo_season_types(f)
    r2, _ = st.loyo_season_types(g)
    pick = lambda r: r[(r.district == "b") & (r.season_year == 2008)].iloc[0]  # noqa: E731
    a, b = pick(r1), pick(r2)
    assert (a.label_a, a.label_b, a.k) == (b.label_a, b.label_b, b.k)
    assert a.sil_a == pytest.approx(b.sil_a) and a.sil_b == pytest.approx(b.sil_b)


def test_percentile_labels_exclude_year_changes_the_thresholds():
    f = pd.DataFrame({"district": "a", "season": "rabi", "season_year": range(2001, 2008),
                      "rain_total_mm": [1.0, 2, 3, 4, 5, 100, 200],
                      "tmax_mean_c": [30.0, 29, 28, 27, 26, 25, 24]})   # 2005 is never hot
    with_all = st.percentile_labels(f)
    without = st.percentile_labels(f, exclude_year=2007)
    # 2005 (rain 5): 80th percentile with 2007 in is 81 -> typical; without 2007 it is 5 -> wet
    assert with_all[4] == "typical" and without[4] == "wet"

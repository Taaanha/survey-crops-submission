"""Validation helpers shared by the three W3 comparisons (Layer 2, no AI).

- loyo_splits: leave-one-year-out. The evaluation year never reaches the fitted model.
- bootstrap_ci: percentile bootstrap interval for one statistic, fixed seed, n always reported.
- paired_diff_ci: bootstrap interval of mean(b - a) on paired items; "B beats A" only when the
  whole interval is above 0.

With 5 districts and 10 to 24 seasons the samples are small, so the intervals are wide. Rows from
the same year in neighbouring districts are not independent, so the true intervals are wider still.
"""

import numpy as np

SEED = 20261112
N_BOOT = 2000
LEVEL = 0.95
SMALL_SAMPLE_NOTE = ("Small sample (5 districts, 10 to 24 seasons): intervals are wide, and district-seasons of "
                     "the same year are not independent, so the true uncertainty is larger. Needs local validation.")


def loyo_splits(years):
    """[(train_years, test_year)] with every year held out once; train never contains the test year."""
    ys = sorted({int(y) for y in years})
    return [([t for t in ys if t != y], y) for y in ys]


def bootstrap_ci(values, stat=np.mean, n_boot=N_BOOT, seed=SEED, level=LEVEL):
    """{value, lo, hi, n, n_boot, level} for stat(values). NaNs are dropped and not counted in n.
    n = 0 gives value NaN; n < 2 gives lo and hi NaN (no interval from one item)."""
    x = np.asarray(values, dtype=float)
    x = x[~np.isnan(x)]
    out = {"value": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": int(len(x)),
           "n_boot": int(n_boot), "level": level}
    if len(x) == 0:
        return out
    out["value"] = float(stat(x))
    if len(x) < 2:
        return out
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(x), size=(n_boot, len(x)))
    stats = np.array([stat(x[d]) for d in draws])
    a = (1 - level) / 2
    out["lo"], out["hi"] = float(np.quantile(stats, a)), float(np.quantile(stats, 1 - a))
    return out


def paired_diff_ci(a, b, n_boot=N_BOOT, seed=SEED, level=LEVEL):
    """Bootstrap interval of mean(b - a) over pairs where both are present."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != b.shape:
        raise ValueError("paired_diff_ci needs two sequences of the same length")
    return bootstrap_ci(b - a, np.mean, n_boot, seed, level)


def beats(diff):
    """True only when the whole interval of (B - A) is above 0. A NaN interval is never a win."""
    return bool(diff["n"] >= 2 and not np.isnan(diff["lo"]) and diff["lo"] > 0)

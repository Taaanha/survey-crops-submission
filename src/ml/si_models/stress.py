"""Problem 2: flags past seasons that look unusual (never a statement about a coming season).

Method A (z-score rule): a district-season is flagged when any feature is at least Z_LIMIT sample
standard deviations from that district-season's mean over the OTHER years. Z_LIMIT = 2 is our choice.
Method B (Isolation Forest): fitted on the z-scores of the other years (all districts pooled, one
model per season); the held-out year is flagged when its score is below a cut-off taken from the
TRAINING scores at Method A's training flag rate, so both methods get the same alarm budget.

Leave-one-year-out throughout: the held-out year never reaches the mean, the sd, the forest or the
cut-off. Scored against cited events only (data/reference/w3_known_events.csv). The event list is
not a complete list of bad seasons, so "flags outside listed events" is an upper bound on false alarms.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from si_models.features import KEY, standardize_loyo
from si_models.validation import SEED, bootstrap_ci, loyo_splits, paired_diff_ci

Z_LIMIT = 2.0            # our choice, not a cited limit
N_TREES = 200
WEATHER_FEATURES = ["rain_total_mm", "rx1day", "extreme_rain_days_r20mm", "cdd", "rain_minus_et0",
                    "tmax_mean_c", "tmin_mean_c"]
SATELLITE_FEATURES = WEATHER_FEATURES + ["smap_rootzone_z", "ndvi_season_mean"]
# smap_rootzone_z is already a leave-one-year-out z-score from W2, so it is not standardized again
ALREADY_Z = ("smap_rootzone_z",)


def zscore_flag(z_row, limit=Z_LIMIT):
    """True when any |z| >= limit; NaN (not assessed) when any z is missing."""
    z = np.asarray(z_row, dtype=float)
    if np.isnan(z).any():
        return float("nan")
    return bool(np.max(np.abs(z)) >= limit)


def fit_forest(z_train, seed=SEED):
    """Isolation Forest on complete training rows (fixed seed)."""
    return IsolationForest(n_estimators=N_TREES, random_state=seed).fit(np.asarray(z_train, dtype=float))


def forest_cutoff(train_scores, budget):
    """Score at or below which a season is flagged: the `budget` quantile of the TRAINING scores.
    budget is floored at one training row so the cut-off always exists."""
    s = np.asarray(train_scores, dtype=float)
    return float(np.quantile(s, max(budget, 1.0 / len(s))))


def _z_table(features, cols, test_year):
    to_scale = [c for c in cols if c not in ALREADY_Z]
    z = standardize_loyo(features, to_scale, test_year)
    for c in cols:
        if c in ALREADY_Z:
            z[c] = features[c].values
    return z[KEY + list(cols)]


def loyo_stress(features, cols, seed=SEED, limit=Z_LIMIT):
    """One row per district-season with flag_a, flag_b (True/False, or NaN = not assessed), score_b
    and cutoff_b, each produced by a model that never saw that row's year."""
    rows = []
    for _, year in loyo_splits(features.season_year):
        z = _z_table(features, cols, year)
        for season, zs in z.groupby("season"):
            train = zs[(zs.season_year != year)].dropna(subset=cols)
            test = zs[zs.season_year == year]
            if len(train) < 10:
                forest = None
            else:
                forest = fit_forest(train[cols].values, seed)
                train_a = np.array([zscore_flag(r, limit) for r in train[cols].values], dtype=float)
                cutoff = forest_cutoff(forest.score_samples(train[cols].values), float(train_a.mean()))
            for _, r in test.iterrows():
                vals = r[cols].values.astype(float)
                flag_a = zscore_flag(vals, limit)
                if forest is None or np.isnan(vals).any():
                    score, flag_b, cut = np.nan, np.nan, np.nan
                else:
                    score = float(forest.score_samples(vals.reshape(1, -1))[0])
                    flag_b, cut = bool(score <= cutoff), cutoff
                rows.append({"district": r.district, "season_year": int(r.season_year), "season": season,
                             "flag_a": flag_a, "flag_b": flag_b, "score_b": score, "cutoff_b": cut,
                             "n_train": int(len(train))})
    return pd.DataFrame(rows).sort_values(KEY).reset_index(drop=True)


def score_against_events(flags, events, column):
    """Hits and flags outside listed events for one method column ('flag_a' or 'flag_b').

    events: DataFrame with district, season_year, season (cited rows only). Only assessed rows count.
    Returns hit_rate and outside_rate as bootstrap dicts (value, lo, hi, n) plus the plain counts."""
    f = flags.dropna(subset=[column]).copy()
    f[column] = f[column].astype(bool)
    ev = set(map(tuple, events[KEY].astype({"season_year": int}).values.tolist())) if len(events) else set()
    is_event = np.array([(d, int(y), s) in ev for d, y, s in f[KEY].values], dtype=bool)
    hit, out = f[column].values[is_event].astype(float), f[column].values[~is_event].astype(float)
    return {"hits": int(hit.sum()), "n_events_assessed": int(len(hit)), "n_events_listed": int(len(ev)),
            "flags_outside_events": int(out.sum()), "n_other_seasons": int(len(out)),
            "hit_rate": bootstrap_ci(hit), "outside_rate": bootstrap_ci(out)}


def event_summary(flags, events, column):
    """One entry per INDEPENDENT event (the `event` column): the district-seasons assessed and flagged.
    Districts hit by the same regional event share one weather situation, so they are not independent
    hits. Returns {"n_events": events with at least one assessed district-season, "n_events_any_flag":
    of those, events where any district was flagged, "events": [{event, season_year, season,
    districts_assessed, districts_flagged}]}."""
    f = flags.dropna(subset=[column]).copy()
    f[column] = f[column].astype(bool)
    out = []
    for (event, year, season), grp in events.groupby(["event", "season_year", "season"]):
        keys = set(zip(grp.district, grp.season_year.astype(int), grp.season))
        hit = f[[(d, int(y), s) in keys for d, y, s in f[KEY].values]]
        if hit.empty:
            continue
        out.append({"event": event, "season_year": int(year), "season": season,
                    "districts_assessed": sorted(hit.district), "districts_flagged": sorted(hit[hit[column]].district)})
    return {"n_events": len(out), "n_events_any_flag": sum(1 for e in out if e["districts_flagged"]), "events": out}


def compare(flags, events):
    """Scores for both methods and the decision. B is used only if it finds more of the listed events
    (paired interval of the hit difference above 0) without flagging more seasons outside them."""
    a, b = score_against_events(flags, events, "flag_a"), score_against_events(flags, events, "flag_b")
    both = flags.dropna(subset=["flag_a", "flag_b"])
    ev = set(map(tuple, events[KEY].astype({"season_year": int}).values.tolist())) if len(events) else set()
    is_event = np.array([(d, int(y), s) in ev for d, y, s in both[KEY].values], dtype=bool)
    fa, fb = both.flag_a.values.astype(float), both.flag_b.values.astype(float)
    hit_diff = paired_diff_ci(fa[is_event], fb[is_event])
    out_diff = paired_diff_ci(fa[~is_event], fb[~is_event])
    b_wins = bool(hit_diff["n"] >= 2 and hit_diff["lo"] > 0 and not out_diff["lo"] > 0)
    return {"method_a": a, "method_b": b, "hit_rate_b_minus_a": hit_diff, "outside_rate_b_minus_a": out_diff,
            "agreement": bootstrap_ci((fa == fb).astype(float)),
            "use": "B" if b_wins else "A",
            "reason": ("Isolation Forest found more of the listed events without more flags outside them"
                       if b_wins else "Isolation Forest did not beat the z-score rule on the listed events "
                       "(the interval of the difference includes 0 or there are too few events), so the app uses the z-score rule")}

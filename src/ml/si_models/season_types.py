"""Problem 3: season types from season rain (IMERG) and mean daily maximum temperature (POWER).

Method A (percentile rule): within one district-season, a year is "wet" when its rain is at or above
the 80th percentile of the OTHER years, "hot" when its mean Tmax is, "hot and wet" when both, else
"typical". The top 20% cut is our choice, not a cited limit.
Method B (k-means): on the z-scores of the two features (z from the other years only), all districts
pooled, k from 2 to 5 chosen by the silhouette of the training years.

Scored with leave-one-year-out, two numbers per held-out district-season:
- stable: does the type given without that year match the type given when all years are used?
- held-out silhouette: is the held-out season closer to the training seasons of its own type than
  to those of the nearest other type (-1 to 1; near 0 means the types overlap)?
There is no ground truth for a "season type", so these measure consistency, not correctness.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from si_models.features import KEY, standardize_loyo
from si_models.validation import SEED, bootstrap_ci, loyo_splits, paired_diff_ci

COLS = ["rain_total_mm", "tmax_mean_c"]
TOP_SHARE = 0.20          # our choice
K_RANGE = (2, 3, 4, 5)
NO_YEAR = -1              # standardize_loyo with a year that does not exist = use all years


def percentile_label(train_rain, train_tmax, rain, tmax, top_share=TOP_SHARE):
    """Type of one season from the other years of the same district-season. NaN input gives None."""
    if np.isnan(rain) or np.isnan(tmax) or len(train_rain) < 5:
        return None
    wet = rain >= np.quantile(np.asarray(train_rain, dtype=float), 1 - top_share)
    hot = tmax >= np.quantile(np.asarray(train_tmax, dtype=float), 1 - top_share)
    return "hot and wet" if (wet and hot) else "wet" if wet else "hot" if hot else "typical"


def percentile_labels(features, exclude_year=None, top_share=TOP_SHARE):
    """Method A label for every row; thresholds from all years of the same district-season except
    `exclude_year` (None = thresholds fitted on every year present, the row's own included)."""
    labels = []
    for _, r in features.iterrows():
        g = features[(features.district == r.district) & (features.season == r.season)
                     & (features.season_year != exclude_year)]
        g = g.dropna(subset=COLS)
        labels.append(percentile_label(g.rain_total_mm.values, g.tmax_mean_c.values,
                                       r.rain_total_mm, r.tmax_mean_c, top_share))
    return np.array(labels, dtype=object)


def choose_k(z_train, ks=K_RANGE, seed=SEED):
    """(k, silhouette by k) with the largest training silhouette; ties go to the smaller k."""
    scores = {}
    for k in ks:
        if k >= len(z_train):
            continue
        lab = KMeans(n_clusters=k, n_init=10, random_state=seed).fit_predict(z_train)
        scores[k] = float(silhouette_score(z_train, lab)) if len(set(lab)) > 1 else float("nan")
    best = max(sorted(scores), key=lambda k: (scores[k] if not np.isnan(scores[k]) else -2, -k))
    return best, scores


def fit_kmeans(z_train, seed=SEED, ks=K_RANGE):
    k, scores = choose_k(z_train, ks, seed)
    return KMeans(n_clusters=k, n_init=10, random_state=seed).fit(z_train), scores


def heldout_silhouette(z_train, labels_train, z, label):
    """Silhouette of one held-out point against the TRAINING points: (b - a) / max(a, b), where a is
    its mean distance to training points with its own label and b the smallest mean distance to the
    training points of another label. NaN if its label has no training points or there is no other label."""
    z_train, labels_train = np.asarray(z_train, dtype=float), np.asarray(labels_train, dtype=object)
    dist = np.sqrt(((z_train - np.asarray(z, dtype=float)) ** 2).sum(axis=1))
    own = labels_train == label
    others = [v for v in set(labels_train.tolist()) if v != label]
    if not own.any() or not others:
        return float("nan")
    a = dist[own].mean()
    b = min(dist[labels_train == v].mean() for v in others)
    return float((b - a) / max(a, b)) if max(a, b) > 0 else float("nan")


def _nearest(centres_from, centres_to):
    """For each centre in `centres_from`, the index of the nearest centre in `centres_to`."""
    d = ((centres_from[:, None, :] - centres_to[None, :, :]) ** 2).sum(axis=2)
    return d.argmin(axis=1)


def loyo_season_types(features, seed=SEED):
    """(table, centres). One row per held-out district-season: label_a, label_b, stable_a, stable_b,
    sil_a, sil_b, k. centres = the k-means centres fitted on all years (z units), to describe the types."""
    feats = features.dropna(subset=COLS).reset_index(drop=True)
    full_a = percentile_labels(feats)
    z_full = standardize_loyo(feats, COLS, NO_YEAR)
    ok_full = z_full[COLS].notna().all(axis=1).values
    km_full, _ = fit_kmeans(z_full.loc[ok_full, COLS].values, seed)
    rows = []
    for _, year in loyo_splits(feats.season_year):
        z = standardize_loyo(feats, COLS, year)
        ok = z[COLS].notna().all(axis=1).values
        tr, te = ok & (feats.season_year.values != year), ok & (feats.season_year.values == year)
        if tr.sum() < 10 or not te.any():
            continue
        z_tr = z.loc[tr, COLS].values
        km, _ = fit_kmeans(z_tr, seed)
        to_full = _nearest(km.cluster_centers_, km_full.cluster_centers_)
        lab_tr_b = km.labels_.astype(object)
        lab_tr_a = percentile_labels(feats[tr], exclude_year=year)
        a_ok = np.array([v is not None for v in lab_tr_a])
        for i in np.where(te)[0]:
            r = feats.iloc[i]
            g = feats[(feats.district == r.district) & (feats.season == r.season) & (feats.season_year != year)]
            la = percentile_label(g.rain_total_mm.values, g.tmax_mean_c.values, r.rain_total_mm, r.tmax_mean_c)
            zi = z.loc[i, COLS].values.astype(float)
            lb = int(km.predict(zi.reshape(1, -1))[0])
            full_b = int(km_full.predict(z_full.loc[i, COLS].values.astype(float).reshape(1, -1))[0])
            rows.append({"district": r.district, "season_year": int(year), "season": r.season,
                         "label_a": la, "label_b": lb, "k": int(km.n_clusters),
                         "stable_a": float(la == full_a[i]) if la is not None and full_a[i] is not None else np.nan,
                         "stable_b": float(to_full[lb] == full_b),
                         "sil_a": heldout_silhouette(z_tr[a_ok], lab_tr_a[a_ok], zi, la) if la is not None else np.nan,
                         "sil_b": heldout_silhouette(z_tr, lab_tr_b, zi, lb)})
    return pd.DataFrame(rows).sort_values(KEY).reset_index(drop=True), km_full.cluster_centers_


def compare(result, centres_full):
    """Metrics for both methods and the decision. B replaces A only if its held-out silhouette is
    higher (whole interval of B - A above 0) and its stability is not lower (interval not below 0)."""
    sil = paired_diff_ci(result.sil_a.values, result.sil_b.values)
    stab = paired_diff_ci(result.stable_a.values, result.stable_b.values)
    b_wins = bool(sil["n"] >= 2 and sil["lo"] > 0 and not stab["hi"] < 0)
    ks = result.k.value_counts().sort_index()
    return {"method_a": {"stability": bootstrap_ci(result.stable_a.values),
                         "heldout_silhouette": bootstrap_ci(result.sil_a.values),
                         "share_by_type": result.label_a.value_counts(normalize=True).round(3).to_dict()},
            "method_b": {"stability": bootstrap_ci(result.stable_b.values),
                         "heldout_silhouette": bootstrap_ci(result.sil_b.values),
                         "k_all_years": int(len(centres_full)),
                         "k_by_heldout_row": {int(k): int(v) for k, v in ks.items()},
                         "centres_all_years_z": [dict(zip(COLS, (round(float(v), 3) for v in c))) for c in centres_full]},
            "silhouette_b_minus_a": sil, "stability_b_minus_a": stab,
            "use": "B" if b_wins else "A",
            "reason": ("k-means types are better separated on held-out seasons and no less stable" if b_wins else
                       "k-means did not beat the percentile rule on both measures, so the app uses the percentile rule")}

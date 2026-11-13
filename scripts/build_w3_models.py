"""
scripts/build_w3_models.py

W3: runs the three comparisons (two methods each) for the districts you name (default: the five
live ones) and writes
  docs/results/w3_metrics.json            metrics for both methods per problem, with n, intervals, sources
  docs/results/w3_stress_flags.csv        held-out flags per district-season (both methods)
  docs/results/w3_season_types.csv        held-out season types (both methods)
  docs/results/w3_transitions.csv         NDVI transition dates and errors
  src/ml/si_models/cards/*.md             one model card per model

Dataset availability is read from docs/w1b_data_status.csv (never typed here).
Run from the repo root:  python scripts/build_w3_models.py [slug slug ...]
"""
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for sub in (("src", "compute"), ("src", "ml")):
    sys.path.insert(0, os.path.join(ROOT, *sub))
from district_grid.features import SEASONS  # noqa: E402
from reference import load_reference  # noqa: E402
from sat_layers import loaders  # noqa: E402
from sat_layers.status import NotAssessed, require_assessed, status_of  # noqa: E402
from si_models import features as F, report, season_types, stress, transitions  # noqa: E402
from si_models.validation import SEED, SMALL_SAMPLE_NOTE, bootstrap_ci, paired_diff_ci  # noqa: E402
from weather import load_weather  # noqa: E402

LIVE = ["cumilla", "feni", "brahmanbaria", "noakhali", "sylhet"]
YEARS = list(range(2001, 2025))
PROC = os.path.join(ROOT, "data", "processed")
RESULTS = os.path.join(ROOT, "docs", "results")
CARDS = os.path.join(ROOT, "src", "ml", "si_models", "cards")
EXCLUDED = ["ecostress_et", "grace_fo", "hls_ndvi"]   # never model inputs; the reason is read from the status table
MODEL_INPUT_NOTE = {"ecostress_et": "not a model input", "grace_fo": "not a model input (regional, about 300 km)",
                    "hls_ndvi": "not a district-level input (two demo tiles)"}


def layer(key):
    st, reason = status_of(key)
    return {"key": key, "status": st, "reason": reason}


def sources(cols):
    seen = {}
    for c in cols:
        seen[F.PROVENANCE[c]["dataset"]] = F.PROVENANCE[c]["source_url"]
    return [{"dataset": d, "source_url": u} for d, u in seen.items()]


def run_stress(feats, cols, events):
    flags = stress.loyo_stress(feats, cols)
    res = stress.compare(flags, events)
    res["independent_events"] = {"method_a": stress.event_summary(flags, events, "flag_a"),
                                 "method_b": stress.event_summary(flags, events, "flag_b")}
    res["n_district_seasons_assessed"] = int(flags.flag_a.notna().sum())
    res["years"] = sorted(int(y) for y in flags.dropna(subset=["flag_a"]).season_year.unique())
    res["features"], res["sources"] = cols, sources(cols)
    return flags, res


def transition_metrics(tr):
    out = {}
    for name, g in tr.groupby("transition"):
        ea, eb = g.err_a.abs(), g.err_b.abs()
        out[name] = {
            "method_a": {"dates_found": int(g.date_a.notna().sum()), "abs_error_days_median": bootstrap_ci(ea, np.median)},
            "method_b": {"dates_found": int(g.date_b.notna().sum()), "abs_error_days_median": bootstrap_ci(eb, np.median),
                         "signed_error_days_median": bootstrap_ci(g.err_b, np.median),
                         "share_inside_window": bootstrap_ci((g.err_b.dropna() == 0).astype(float))},
            "abs_error_b_minus_a": paired_diff_ci(ea.values, eb.values),
            "n_district_years": int(len(g)), "composites_filled": int(g.n_filled.sum())}
    return out


def main(slugs):
    os.makedirs(CARDS, exist_ok=True)
    long = pd.read_csv(os.path.join(PROC, "indicators_districts_2001_2024.csv"))
    layers = {k: layer(k) for k in ["modis_ndvi", "smap_live5"] + EXCLUDED}
    try:
        require_assessed("modis_ndvi")
        modis = loaders.load_modis().data
        modis_years = loaders.modis_years_present(modis)
    except NotAssessed:
        modis, modis_years = None, []
    feats = []
    for slug in slugs:
        if slug not in set(long.district):
            print(f"{slug}: not in the W2 indicator table, skipped (run scripts/build_indicators.py {slug})")
            continue
        feats.append(F.build_features(slug, load_weather(slug), long, YEARS, list(SEASONS), modis))
    feats = pd.concat(feats, ignore_index=True)
    events, events_unused = report.load_events()
    events = events[events.district.isin(slugs)]
    # cited events outside the scored years cannot be scored: reported, never counted as hits or misses
    outside = events[~events.season_year.isin(YEARS)]
    events = events[events.season_year.isin(YEARS)]
    events_not_scored = [{"district": e.district, "season_year": int(e.season_year), "season": e.season,
                          "event": e.event, "source_url": e.source_url,
                          "reason": f"not scored (outside the data period {YEARS[0]}-{YEARS[-1]}; "
                                    "IMERG rain ends 2025-09-30)"} for e in outside.itertuples()]
    out = {"seed": SEED, "districts": list(feats.district.unique()), "note": SMALL_SAMPLE_NOTE,
           "layers": layers, "excluded_inputs": {k: MODEL_INPUT_NOTE[k] + "; status table: " + layers[k]["status"]
                                                 + " (" + layers[k]["reason"] + ")" for k in EXCLUDED}}

    # ---- problem 2: stressed seasons
    flags_w, res_w = run_stress(feats, stress.WEATHER_FEATURES, events)
    flags_s, res_s = run_stress(feats, stress.SATELLITE_FEATURES, events)
    out["stressed_seasons"] = {
        "events_used": events.to_dict("records"), "events_not_used": events_unused,
        "events_not_scored": events_not_scored,
        "z_limit": stress.Z_LIMIT, "z_limit_source": "our choice",
        "weather_2001_2024": res_w, "with_smap_ndvi": res_s,
        "caveat": "The event list is not a complete list of bad seasons, so flags outside it are an upper bound on false alarms."}
    flags_w.assign(feature_set="weather").merge(
        flags_s[F.KEY + ["flag_a", "flag_b"]].rename(columns={"flag_a": "flag_a_sat", "flag_b": "flag_b_sat"}),
        on=F.KEY, how="left").to_csv(os.path.join(RESULTS, "w3_stress_flags.csv"), index=False, float_format="%.4f")

    # ---- problem 3: season types
    types, centres = season_types.loyo_season_types(feats)
    res_t = season_types.compare(types, centres)
    res_t.update({"top_share": season_types.TOP_SHARE, "top_share_source": "our choice",
                  "n_district_seasons": int(len(types)), "features": season_types.COLS,
                  "sources": sources(season_types.COLS),
                  "caveat": "No ground truth exists for a season type; the scores measure consistency, not correctness."})
    out["season_types"] = res_t
    types.to_csv(os.path.join(RESULTS, "w3_season_types.csv"), index=False, float_format="%.4f")

    # ---- problem 1: transitions
    thr = report.load_ndvi_threshold()
    windows = transitions.reference_windows(load_reference().kept)
    p1 = {"modis_status": layers["modis_ndvi"], "years": modis_years, "threshold": thr, "reference_windows": windows,
          "resolution_note": f"Composites are {transitions.COMPOSITE_DAYS} days apart: an error below about "
                             f"{transitions.COMPOSITE_DAYS} days cannot be resolved.",
          "sources": [dict(F.MODIS_DS)]}
    if modis is None or not modis_years:
        p1["status"] = "not assessed (" + layers["modis_ndvi"]["reason"] + ")"
        tr = pd.DataFrame()
    else:
        tr = pd.concat([transitions.detect(modis, s, modis_years, None if thr is None else thr["value"])
                        for s in feats.district.unique()], ignore_index=True)
        tr = transitions.add_errors(tr, windows)
        p1["by_transition"] = transition_metrics(tr)
        found_a, n_all = int(tr.date_a.notna().sum()), int(len(tr))
        share = transitions.MIN_FOUND_SHARE
        a_ok = [k for k, v in p1["by_transition"].items() if v["method_a"]["dates_found"] >= share * v["n_district_years"]]
        p1["method_a_status"] = ("assessed for " + ", ".join(a_ok) if a_ok else
                                 "not assessed (no cited threshold row)" if thr is None else
                                 f"not assessed (the district-mean NDVI crosses the cited {thr['value']} bare-soil limit in only "
                                 f"{found_a} of {n_all} district-year search windows, below our {int(share * 100)}% rule; "
                                 "the Bangladesh-specific threshold row is a GAP)")
        diffs = [p1["by_transition"][k]["abs_error_b_minus_a"] for k in a_ok]
        b_better = any(d["n"] >= 2 and d["hi"] < 0 for d in diffs)
        p1["use"] = "B" if (not a_ok or b_better) else "A"
        p1["reason"] = ("Method A is not assessed, so the two methods cannot be compared; the app shows the Method B "
                        "dates as estimates that need local validation" if not a_ok else
                        "smoothing + change point has the smaller error" if b_better else
                        "smoothing + change point did not beat the fixed threshold, so the app uses the threshold")
        tr.to_csv(os.path.join(RESULTS, "w3_transitions.csv"), index=False)
    out["seasonal_transitions"] = p1

    with open(os.path.join(RESULTS, "w3_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    write_cards(out)
    print(json.dumps({"stress_use": res_w["use"], "types_use": res_t["use"], "transitions_use": p1.get("use"),
                      "events_used": len(events), "modis_years": len(modis_years)}))
    return out


def write_cards(out):
    fm, seed = report.fmt, out["seed"]
    st, sw, ss = out["stressed_seasons"], out["stressed_seasons"]["weather_2001_2024"], out["stressed_seasons"]["with_smap_ndvi"]
    ev = "; ".join(f"{e['district']} {e['season_year']} {e['season']} {e['event']} ({e['source_url']})" for e in st["events_used"]) or "none"
    gap = "; ".join(f"{u['item']}: {u['reason'].split('. ')[0]}" for u in st["events_not_used"]) or "none"
    nots = "; ".join(f"{e['district']} {e['season_year']} {e['season']} {e['event']}: {e['reason']}" for e in st["events_not_scored"]) or "none"
    inp = lambda res: [(s["dataset"], s["source_url"]) for s in res["sources"]]  # noqa: E731
    for key, name, method in (("method_a", "stress_zscore", f"z-score rule: flagged when any feature is {st['z_limit']} or more "
                               "standard deviations from the other years of the same district-season (limit: our choice)"),
                              ("method_b", "stress_isolation_forest", "Isolation Forest (200 trees) fitted on the other years; "
                               "cut-off from the training scores at the z-score rule's training flag rate")):
        metrics = []
        for label, res in (("weather features, 2001-2024", sw), ("with SMAP and NDVI", ss)):
            m = res[key]
            ie = res["independent_events"][key]
            metrics += [(f"{label}: independent events with any district flagged",
                         f"{ie['n_events_any_flag']} of {ie['n_events']} (" + "; ".join(
                             f"{e['event']} {e['season_year']}: {len(e['districts_flagged'])} of {len(e['districts_assessed'])} districts flagged"
                             for e in ie["events"]) + ")"),
                        (f"{label}: listed district-seasons flagged", f"{m['hits']} of {m['n_events_assessed']} assessed "
                         f"({m['n_events_listed']} listed); rate {fm(m['hit_rate'])}"),
                        (f"{label}: seasons flagged outside listed events", f"{m['flags_outside_events']} of "
                         f"{m['n_other_seasons']}; rate {fm(m['outside_rate'])}"),
                        (f"{label}: years", f"{res['years'][0]} to {res['years'][-1]} (n = {len(res['years'])} years, "
                         f"{res['n_district_seasons_assessed']} district-seasons)")]
        limits = [f"Cited events used: {ev}.", "Districts hit by the same regional event are not independent hits: the four Aug 2024 districts count as one event, so the district-season "
                  "hit rate overstates the evidence (2 independent events in all).",
                  f"Rows not used (GAP, reason from the reference file): {gap}.", f"Cited events not scored: {nots}.", st["caveat"],
                  "SMAP has 10 usable years and MODIS NDVI only the years in the status table, so the second feature set covers fewer seasons.",
                  "Weather values are area values (IMERG 0.1 degree, POWER about 0.5 degree), not a field.",
                  "With several features and a limit of 2, the rule flags a large share of ordinary seasons; the limit was not tuned on the events."]
        used = ("yes" if sw["use"] == key[-1].upper() else "no") + f": {sw['reason']}"
        card = report.model_card(name, "flags past seasons that look unusual", method, inp(ss),
                                 f"{sw['n_district_seasons_assessed']} district-seasons", metrics, limits, used, seed)
        open(os.path.join(CARDS, f"{name}.md"), "w", encoding="utf-8", newline="\n").write(card)

    t = out["season_types"]
    for key, name, method in (("method_a", "season_type_percentile", f"percentile rule: top {int(t['top_share'] * 100)}% of the other "
                               "years for rain and/or mean Tmax (cut: our choice)"),
                              ("method_b", "season_type_kmeans", "k-means on z-scores of season rain and mean Tmax; k from 2 to 5 by training silhouette")):
        m = t[key]
        metrics = [("stability (same type with and without the year)", fm(m["stability"])),
                   ("held-out silhouette (-1 to 1)", fm(m["heldout_silhouette"]))]
        if key == "method_b":
            metrics.append(("k", f"{m['k_all_years']} with all years; by held-out row: {m['k_by_heldout_row']}"))
            metrics.append(("type centres with all years (z units)", str(m["centres_all_years_z"])))
        else:
            metrics.append(("share of seasons by type", str(m["share_by_type"])))
        used = ("yes" if t["use"] == key[-1].upper() else "no") + f": {t['reason']}"
        card = report.model_card(name, "season types (hot, wet, typical) for past seasons", method, inp(t),
                                 f"{t['n_district_seasons']} district-seasons, 2001-2024", metrics,
                                 [t["caveat"], "Season windows are our analysis windows, not a cited crop calendar."], used, seed)
        open(os.path.join(CARDS, f"{name}.md"), "w", encoding="utf-8", newline="\n").write(card)

    p = out["seasonal_transitions"]
    thr = p["threshold"]
    for key, name, method in (("method_a", "transition_threshold", "fixed NDVI threshold" + (f" {thr['value']} ({thr['source_url']}; provisional, global, not Bangladesh rice)" if thr else " (no cited row)")),
                              ("method_b", "transition_changepoint", "Savitzky-Golay smoothing (5 composites, order 2: our choice) + Pettitt change point in a four-month search window (our choice)")):
        metrics, limits = [], [p["resolution_note"]]
        for tname, v in p.get("by_transition", {}).items():
            w = p["reference_windows"][tname]
            m = v[key]
            if "start" in w:
                metrics.append((f"{tname}: median days outside the cited window", f"{fm(m['abs_error_days_median'], 0)}; dates found {m['dates_found']} of {v['n_district_years']}"))
                if key == "method_b":
                    metrics.append((f"{tname}: share of dates inside the window", fm(m["share_inside_window"])))
            else:
                metrics.append((f"{tname}: error", f"not assessed ({w['reason']}); dates found {m['dates_found']} of {v['n_district_years']}"))
        for tname, w in p["reference_windows"].items():
            if "start" in w:
                limits.append(f"{tname} window: {w['derivation']}. Sources: {'; '.join(w['sources'])}.")
        limits += ["The satellite sees the canopy turning green, which is later than transplanting; no cited lag is subtracted.",
                   "District-mean NDVI mixes rice with all other land cover; June to August composites are often cloudy.",
                   f"MODIS status: {p['modis_status']['status']} ({p['modis_status']['reason']})."]
        if key == "method_a":
            limits.append(f"Method A status: {p.get('method_a_status', p.get('status'))}.")
        used = ("yes" if p.get("use") == key[-1].upper() else "no") + f": {p.get('reason', p.get('status'))}"
        card = report.model_card(name, "estimated green-up and browning dates from MODIS NDVI", method,
                                 [(s["dataset"], s["source_url"]) for s in p["sources"]],
                                 f"{len(p['years'])} years ({p['years'][0] if p['years'] else 'none'} to {p['years'][-1] if p['years'] else 'none'}) x {len(out['districts'])} districts",
                                 metrics, limits, used, seed)
        open(os.path.join(CARDS, f"{name}.md"), "w", encoding="utf-8", newline="\n").write(card)


if __name__ == "__main__":
    main(sys.argv[1:] or LIVE)

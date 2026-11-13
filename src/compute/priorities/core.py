"""
src/compute/priorities/core.py

Farmer priorities (T2): a transparent weighted re-ranking of the rotations the
rotation module evaluates. The four priorities are save_water, soil_health,
lowest_risk and flood_safety. Each has ONE metric, read from the rotation
summary (its public output); each metric is min-max normalised across the
candidates (1 = best) and the score is sum(weight x normalised). Every
component is returned (raw value with provenance, normalised value, weight,
contribution), so the screen can show the reasoning. No other factor exists.

A record of past seasons (2001-2024), not a forecast.
"""

import math

from rotation import candidate_rotations, evaluate_rotation, load_context

KEYS = ("save_water", "soil_health", "lowest_risk", "flood_safety")
FLOOD_HAZARDS = ("waterlog",)      # risk_calendar hazards caused by too much water
NO_CONTRAST = 0.5                  # normalised value when every candidate is equal on a metric
TIE_DECIMALS = 12                  # scores closer than this are a tie (broken by rotation id)

METRICS = {
    "save_water": {"label": "Save water", "direction": "lower", "unit": "mm",
                   "metric": "irrigation need in the driest 20% of years (Kc-weighted FAO-56 balance)"},
    "soil_health": {"label": "Soil health", "direction": "higher", "unit": "crops",
                    "metric": "number of legume crops in the rotation"},
    "lowest_risk": {"label": "Lowest risk", "direction": "lower", "unit": "share of years",
                    "metric": "share of past seasons with a problem for any assessed hazard"},
    "flood_safety": {"label": "Flood safety", "direction": "lower", "unit": "share of years",
                     "metric": "share of past seasons with a flood-related problem (waterlogging)"},
}


class PrioritiesError(ValueError):
    """The weights are not usable (the API turns this into BAD_PARAMETER)."""


# ---------------- weights ----------------

def normalise_weights(weights):
    """{save_water, soil_health, lowest_risk, flood_safety} each 0-1 (missing = 0),
    scaled to sum to 1. All zero is an error."""
    if not isinstance(weights, dict):
        raise PrioritiesError("weights must be an object with the keys " + ", ".join(KEYS))
    unknown = sorted(set(weights) - set(KEYS))
    if unknown:
        raise PrioritiesError(f"unknown priority: {', '.join(map(str, unknown))} (use {', '.join(KEYS)})")
    clean = {}
    for key in KEYS:
        value = weights.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise PrioritiesError(f"weight for {key} must be a number between 0 and 1")
        if not 0 <= value <= 1:
            raise PrioritiesError(f"weight for {key} must be between 0 and 1, got {value}")
        clean[key] = float(value)
    total = sum(clean.values())
    if total <= 0:
        raise PrioritiesError("Give at least one priority a weight above zero.")
    return {key: clean[key] / total for key in KEYS}


# ---------------- raw metrics (from the rotation summary only) ----------------

def _value(measure):
    return None if measure is None else measure["value"]


def _share(summary, count, what):
    """count / n_years as a measure that keeps the count's provenance."""
    n = summary["n_years"]["value"]
    prov = dict(count["provenance"])
    prov["note"] = f"{what}: {count['value']} of {n} years, divided by {n}" + (
        f" ({prov['note']})" if prov.get("note") else "")
    return {"value": count["value"] / n, "unit": "share of years", "provenance": prov}


def flood_safety_raw(summary, field_profile=None):
    """Flood-related problem-year share, or (None, reason).
    TODO(T3): when field_profile(lat, lon) exists, combine it here (inundation days per
    event, drain date) so the metric describes THIS field, not the district."""
    if field_profile is not None:
        raise NotImplementedError("field water profile arrives with task T3")
    by_hazard = summary.get("problem_years_by_hazard") or {}
    flood = [h for h in FLOOD_HAZARDS if h in by_hazard]
    if not flood:
        return None, "not assessed: no sourced flood-related hazard for this rotation"
    first = by_hazard[flood[0]]
    total = {"value": sum(by_hazard[h]["value"] for h in flood), "unit": "years",
             "provenance": first["provenance"]}
    return _share(summary, total, "years with " + " or ".join(flood)), None


def raw_metrics(evaluation, field_profile=None):
    """{priority: (measure or None, reason_if_missing or None, note or None)}."""
    s = evaluation["summary"]
    out = {}
    irr = s.get("irrigation_mm_worst20")
    out["save_water"] = (irr, None if irr else "not assessed: no water model for this rotation", None)
    unknown = s.get("legume_unknown_crops") or []
    # an unknown legume flag is "unknown", never a 0: the rotation cannot be scored on soil health
    out["soil_health"] = (None if unknown else s["legume_count"],
                          ("not assessed: legume flag unknown (NEEDS SOURCE) for " + ", ".join(unknown))
                          if unknown else None, None)
    problems = s.get("problem_years")
    out["lowest_risk"] = (
        _share(s, problems, "years with a problem") if problems else None,
        None if problems else "not assessed: no sourced hazard for this rotation", None)
    flood, reason = flood_safety_raw(s, field_profile)
    out["flood_safety"] = (flood, reason, None)
    return out


# ---------------- scoring ----------------

def _normalise(values, direction):
    """{id: 0..1} (1 = best) and whether the candidates differ at all."""
    lo, hi = min(values.values()), max(values.values())
    if hi == lo:
        return {k: NO_CONTRAST for k in values}, True
    span = hi - lo
    return {k: ((v - lo) if direction == "higher" else (hi - v)) / span for k, v in values.items()}, False


def _how_to_include(row, norm):
    """A plain hint for an unranked rotation: which weighted priorities it could not be
    assessed on, and that setting those weights to 0 compares it on the others."""
    gaps = [k for k in KEYS if norm[k] > 0 and row["raw"][k][0] is None]
    crops = [slot["crop"] for slot in row["rotation"].get("slots", []) if slot["crop"] != "aman_rice"]
    what = ", ".join(crops) or row["id"]
    parts = [f"{METRICS[k]['label']} is not assessed for {what} ({row['raw'][k][1].replace('not assessed: ', '')})"
             for k in gaps]
    zero = " and ".join(gaps)
    return "; ".join(parts) + f". Set the {zero} weight{'s' if len(gaps) > 1 else ''} to 0 to compare it on the other priorities."


def score_rotations(evaluations, weights, field_profile=None):
    """Rank evaluate_rotation() results for the given priority weights.

    Returns {"weights": {requested, normalised}, "metrics", "ranked", "unranked"}.
    A rotation that is not assessed on a metric with weight > 0 is listed in
    "unranked" with the reason, never scored as zero."""
    norm = normalise_weights(weights)
    requested = {k: float(weights.get(k, 0)) for k in KEYS}
    rows = []
    for ev in evaluations:
        rows.append({"id": ev["rotation"]["id"], "rotation": ev["rotation"],
                     "problem_line": ev["summary"].get("problem_line"),
                     "raw": raw_metrics(ev, field_profile)})
    ranked_rows, unranked = [], []
    for row in rows:
        missing = [f"{METRICS[k]['label']}: {row['raw'][k][1]}" for k in KEYS
                   if norm[k] > 0 and row["raw"][k][0] is None]
        if missing:
            unranked.append({"id": row["id"], "rotation": row["rotation"], "reason": "; ".join(missing),
                             "how_to_include": _how_to_include(row, norm)})
        else:
            ranked_rows.append(row)
    unranked.sort(key=lambda u: u["id"])

    normalised, contrast = {}, {}
    for key in KEYS:
        present = {r["id"]: _value(r["raw"][key][0]) for r in ranked_rows if r["raw"][key][0] is not None}
        normalised[key], contrast[key] = _normalise(present, METRICS[key]["direction"]) if present else ({}, False)

    ranked = []
    for row in ranked_rows:
        components = {}
        for key in KEYS:
            raw, _, note = row["raw"][key]
            n = normalised[key].get(row["id"])
            components[key] = {"label": METRICS[key]["label"], "metric": METRICS[key]["metric"],
                               "direction": METRICS[key]["direction"], "raw": raw, "normalised": n,
                               "weight": norm[key], "contribution": norm[key] * (n or 0.0),
                               "no_contrast": bool(contrast[key]), "note": note}
        ranked.append({"id": row["id"], "rotation": row["rotation"], "problem_line": row["problem_line"],
                       "score": sum(c["contribution"] for c in components.values()),
                       "components": components})
    ranked.sort(key=lambda r: (-round(r["score"], TIE_DECIMALS), r["id"]))
    for i, row in enumerate(ranked, start=1):
        row["rank"] = i
    return {"weights": {"requested": requested, "normalised": norm}, "metrics": METRICS,
            "ranked": ranked, "unranked": unranked}


def evaluate_candidates(district, context=None, years=None):
    """evaluate_rotation() for every candidate rotation of a district (the slow
    step; the API caches it so a change of weights re-scores instantly)."""
    ctx = context or load_context(district)
    return [evaluate_rotation(district, rot, years=years, context=ctx)
            for rot in candidate_rotations(district, ctx)]


def rank_rotations(district, weights, context=None, years=None, field_profile=None):
    """Candidate rotations for a district, evaluated by the rotation module
    and ranked for the given weights."""
    normalise_weights(weights)                     # fail fast, before any weather is loaded
    result = score_rotations(evaluate_candidates(district, context, years), weights, field_profile)
    return {"district": district, **result}

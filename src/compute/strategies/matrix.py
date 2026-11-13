"""
src/compute/strategies/matrix.py

Priority matrix for the W4 strategies: which strategy best fits each of the
four farmer priorities (water, soil health, low risk, income). Same honesty
rules as the T2 ranking (src/compute/priorities): min-max normalisation
(1 = best), a strategy that is not assessed on a priority is shown as a gap
with its reason and NEVER scored as zero, equal values are flagged
no_contrast, and ties are listed, not broken silently.

"Income" is the cited market price (BDT/kg) of the rotation's non-Aman crop,
never income per hectare: no yield-times-price model exists in the repo.
"""

PRIORITIES = ("water", "soil_health", "low_risk", "income")

META = {
    "water": {"label": "Save water", "direction": "lower",
              "metric": "irrigation need in the driest 20% of years, mm "
                        "(Kc-weighted FAO-56 balance)"},
    "soil_health": {"label": "Soil health", "direction": "higher",
                    "metric": "number of legume (nitrogen-fixing) crops in the rotation"},
    "low_risk": {"label": "Lowest risk", "direction": "lower",
                 "metric": "share of past seasons with a problem for any assessed hazard"},
    "income": {"label": "Income", "direction": "higher",
               "metric": "cited market price of the rotation's non-Aman crop, BDT/kg "
                         "(a price, not income per hectare: no yield model is wired)"},
}

NO_CONTRAST = 0.5


def _raw(strategy, key):
    """(value, measure_or_None, reason_or_None) for one priority."""
    ind = strategy["indicators"]
    if key == "water":
        w = ind.get("water_use", {})
        if w.get("status") == "assessed":
            return w["worst20"]["value"], w["worst20"], None
        return None, None, w.get("reason", "not assessed")
    if key == "soil_health":
        n = ind.get("nitrogen_fixing", {})
        if n.get("status") == "assessed" and not n.get("unknown"):
            return n["count"]["value"], n["count"], None
        return None, None, n.get("reason", "not assessed: legume flag unknown")
    if key == "low_risk":
        p = ind.get("problem_years", {})
        if p.get("status") == "assessed" and p.get("n"):
            return p["count"]["value"] / p["n"], p["count"], None
        return None, None, p.get("reason", "not assessed")
    if key == "income":
        m = ind.get("market_price", {})
        if m.get("status") == "assessed":
            return m["measure"]["value"], m["measure"], None
        return None, None, m.get("reason", "not assessed")
    raise KeyError(key)


def _normalise(values, direction):
    lo, hi = min(values.values()), max(values.values())
    if hi == lo:
        return {k: NO_CONTRAST for k in values}, True
    span = hi - lo
    return {k: ((v - lo) if direction == "higher" else (hi - v)) / span
            for k, v in values.items()}, False


def priority_matrix(strategies):
    """{"priorities", "cells": {id: {priority: cell}}, "best", "best_reasons"}.

    cell: {"status", "raw" (value), "measure", "normalised", "no_contrast"} or
    {"status": "gap", "reason"}. best[priority]: ids tied for best, or None
    (with best_reasons[priority]) when no strategy is assessed on it."""
    raws = {s["id"]: {k: _raw(s, k) for k in PRIORITIES} for s in strategies}
    cells = {sid: {} for sid in raws}
    best, best_reasons = {}, {}
    for key in PRIORITIES:
        present = {sid: r[key][0] for sid, r in raws.items() if r[key][0] is not None}
        norm, flat = _normalise(present, META[key]["direction"]) if present else ({}, False)
        for sid, r in raws.items():
            value, measure, reason = r[key]
            if value is None:
                cells[sid][key] = {"status": "gap", "reason": reason, "normalised": None}
            else:
                cells[sid][key] = {"status": "assessed", "raw": value, "measure": measure,
                                   "normalised": norm[sid], "no_contrast": flat}
        if not present:
            best[key] = None
            best_reasons[key] = f"not assessed for any strategy ({META[key]['label']})"
        else:
            top = max(norm.values())
            best[key] = sorted(sid for sid, v in norm.items() if v == top)
    return {"priorities": META, "cells": cells, "best": best, "best_reasons": best_reasons,
            "note": ("a strategy that is not assessed on a priority is a gap with its "
                     "reason, never a zero; 1 = best under min-max normalisation")}

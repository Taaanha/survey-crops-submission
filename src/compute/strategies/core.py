"""
src/compute/strategies/core.py

W4 Rotation Strategy Exploration (Layer 1, no AI): the farmer's CURRENT
rotation is the required baseline, every other feasible candidate rotation is
an alternative, and each strategy carries the W4 indicators, a deterministic
five-heading card and a place in the priority matrix. A record of past
seasons; nothing here is a prediction.

Crops are offered only through the rotation engine's candidate list (cited
duration, window and Kc chain); everything else is listed under
crops_not_offered with the reason, never silently dropped.
"""

import os

import pandas as pd

import risk_calendar as rc
from rotation import candidate_rotations, evaluate_rotation, excluded_crops, load_context
from rotation.crop_table import load_crop_table

from soil_chem import soil_baseline

from . import facts
from .cards import five_heading_card
from .indicators import (bare_field_days, erosion_exposure, heavy_rain_days_per_year,
                         problem_year_range, slope_class)
from .matrix import priority_matrix

DATASETS = ("NASA GPM IMERG V07 Final Run (rain)",
            "NASA POWER (temperature, RH, wind, solar)",
            "FAO-56 (Kc water balance, Table 22 root depth)",
            "NASADEM (district mean slope, relative only)",
            "data/reference/*.csv (cited crop facts)")

NEW_PARAMS_FILE = "new_crop_params.csv"


def _gap(reason):
    return {"status": "gap", "reason": reason}


def _by_crop_fact(crops, fn):
    """Per-crop fact rolled up: assessed when at least one crop has a row;
    the crops without one are listed in missing_crops."""
    by_crop = {crop: fn(crop) for crop in crops}
    missing = [c for c, v in by_crop.items() if v["status"] == "gap"]
    if len(missing) == len(by_crop):
        return _gap("; ".join(by_crop[c]["reason"] for c in missing))
    out = {"status": "assessed", "by_crop": by_crop}
    if missing:
        out["missing_crops"] = missing
        out["note"] = "no cited row for: " + ", ".join(missing)
    return out


def attach_soil(residue, soil):
    """The organic-matter indicator = cited residue rows + the SoilGrids baseline.
    Either part may be a gap; both gaps stay a gap with both reasons."""
    r_ok, s_ok = residue.get("status") == "assessed", soil.get("status") == "assessed"
    if not r_ok and not s_ok:
        return {"status": "gap", "reason": f"{residue['reason']}; {soil['reason']}"}
    out = dict(residue) if r_ok else {"status": "assessed", "by_crop": {},
                                      "residue_note": residue["reason"]}
    if s_ok:
        out["soil_baseline"] = soil
    else:
        out["soil_note"] = soil["reason"]
    return out


def _water_use(summary):
    worst = summary.get("irrigation_mm_worst20")
    if worst is None:
        return _gap("not assessed: no water model for this rotation "
                    "(Aman alone, or no Kc chain)")
    return {"status": "assessed", "worst20": worst,
            "median": summary.get("irrigation_mm_median"),
            "note": "Kc-weighted FAO-56 water balance (never cut)"}


def _nitrogen(summary):
    unknown = summary.get("legume_unknown_crops") or []
    out = {"status": "assessed", "count": summary["legume_count"], "unknown": unknown,
           "note": "count of crops whose cited legume flag is yes"}
    if unknown:
        out["reason"] = ("not assessed: legume flag unknown (NEEDS SOURCE) for "
                         + ", ".join(unknown))
    return out


def _strategy(rot, evaluation, role, ref, crop_table, heavy, slope, soil):
    crops = [s["crop"] for s in rot["slots"]]
    rabi = [c for c in crops if c != "aman_rice"]
    summary = evaluation["summary"]
    bare = bare_field_days(evaluation)
    ind = {
        "water_use": _water_use(summary),
        "problem_years": problem_year_range(evaluation),
        "bare_field_days": bare,
        "erosion_exposure": erosion_exposure(bare, heavy, slope),
        "nitrogen_fixing": _nitrogen(summary),
        "organic_matter": attach_soil(
            _by_crop_fact(crops, lambda c: facts.residue(c, ref)), soil),
        "pest_cycle_break": facts.pest_cycle_break(crops, ref),
        "root_depth": _by_crop_fact(crops, lambda c: facts.root_depth(c, ref)),
        "forage": _by_crop_fact(crops, lambda c: facts.forage(c, ref)),
        "market_price": (facts.price(rabi[0], ref) if rabi else
                         _gap("no non-Aman crop in this rotation to price")),
    }
    return {"id": rot["id"], "role": role, "rotation": evaluation["rotation"],
            "problem_line": summary.get("problem_line"),
            "evidence_n_years": summary["n_years"]["value"],
            "datasets": list(DATASETS),
            "indicators": ind,
            "summary": summary}


def _new_param_gaps(reference_dir=facts.REFERENCE_DIR):
    """{crop: [items whose value is GAP]} from new_crop_params.csv (raw read)."""
    path = os.path.join(reference_dir, NEW_PARAMS_FILE)
    if not os.path.exists(path):
        return {}
    table = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    gaps = {}
    for _, r in table.iterrows():
        if r["value"].strip().upper() == "GAP":
            gaps.setdefault(r["item"].split(".")[0], []).append(r["item"])
    return gaps


def crops_not_offered(ctx, reference_dir=facts.REFERENCE_DIR):
    """Crops that are NOT offered as strategies, each with its reason: unusable
    crops.csv rows, and crops that have reference rows (crop_family.csv) but no
    crops.csv row the rotation engine can chain."""
    out = [{"crop": e["crop"], "variety_class": e["variety_class"], "reason": e["reason"]}
           for e in excluded_crops(ctx)]
    in_table = set(ctx.crop_table["crop"])
    family_rows, _ = facts._load_raw("family", reference_dir)
    named = {item.split(".")[0] for item in family_rows["item"]} if not family_rows.empty else set()
    gaps = _new_param_gaps(reference_dir)
    for crop in sorted(named - in_table - {"rotation"}):
        reason = ("not in data/reference/crops.csv: no cited duration, sowing window "
                  "and Kc chain for the rotation engine")
        if crop in gaps:
            reason += " (GAP rows in new_crop_params.csv: " + ", ".join(gaps[crop]) + ")"
        out.append({"crop": crop, "variety_class": None, "reason": reason})
    return out


def build_strategies(district, current, years=None, context=None):
    """The W4 strategy set for a district.

    current (required): the farmer's current rotation, as a candidate rotation
    id (e.g. "aman_rice@06-15>boro_rice") or a rotation dict with "slots".
    Returns {"district", "baseline", "alternatives", "crops_not_offered",
    "priority_matrix", "pest_rule", "assumptions"}. Every number carries
    provenance; what cannot be assessed is a gap with its reason, never 0."""
    ctx = context or load_context(district)
    cands = candidate_rotations(district, ctx)
    by_id = {c["id"]: c for c in cands}
    if isinstance(current, str):
        if current not in by_id:
            raise ValueError(f"current rotation {current!r} is not a candidate for "
                             f"{district}; known: {sorted(by_id)}")
        current_rot = by_id[current]
    elif isinstance(current, dict) and current.get("slots"):
        current_rot = dict(current)
        current_rot.setdefault("id", "current")
    else:
        raise ValueError("current rotation is required (the baseline): pass a candidate "
                         "id or a rotation dict with slots")

    ref = facts.load_facts_reference()
    crop_table = load_crop_table()
    heavy = heavy_rain_days_per_year(ctx.weather["rainfall_mm"], years=rc.SEASONS,
                                     rain_provenance=ctx.weather_provenance.to_dict())
    slope = slope_class(district)
    soil = soil_baseline(district)
    pest = facts.pest_rule(ref)

    rotations = [current_rot] + [c for c in cands if c["id"] != current_rot["id"]]
    strategies = []
    for i, rot in enumerate(rotations):
        ev = evaluate_rotation(district, rot, years=years, context=ctx)
        role = "baseline" if i == 0 else "alternative"
        strategies.append(_strategy(rot, ev, role, ref, crop_table, heavy, slope, soil))
    baseline = strategies[0]
    for s in strategies:
        s["card"] = five_heading_card(s, baseline, pest)

    assumptions = list(baseline["summary"].get("assumptions", [])) + [
        "bare-field days use a 365-day year and our sowing-to-harvest windows, "
        "not satellite observation",
        "the erosion-exposure slope terciles across the 64 districts are our choice",
    ]
    return {"district": district,
            "baseline": baseline,
            "alternatives": strategies[1:],
            "crops_not_offered": crops_not_offered(ctx),
            "priority_matrix": priority_matrix(strategies),
            "pest_rule": pest,
            "assumptions": assumptions}

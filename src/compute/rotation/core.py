"""
src/compute/rotation/core.py

Full-year rotations (Kharif-2 Aman -> Rabi crop -> ...) built by CHAINING the
existing per-crop risk calendar and water balance (risk_calendar.season_row,
summarise, calibrate; water_balance via the calendar). This file only decides
dates and counts; it holds no threshold, stage length or water formula.

Rotation year Y: the Aman seedbed is sown in calendar year Y; the rabi crop
belongs to risk-calendar season Y (1 Aug Y - 31 Jul Y+1). A record of past
seasons, not a forecast.

Chain rule, per year: crop N+1 is sown on max(harvest of N + turnaround, start
of N+1's cited window). If that date is after the window end, the rotation is
infeasible that year. Infeasible years are counted apart from problem years.
"""

import numpy as np
import pandas as pd

import risk_calendar as rc
from common import measured

from .context import load_context, table_provenance
from .crop_table import (is_usable, missing_reason, parse_mmdd, parse_number, pick_row)

DEFAULT_YEARS = rc.SEASONS
KHARIF1_NOTE = ("Kharif-1 is left fallow: no crop with a cited sowing window and duration "
                "(mung bean has only Kc and root depth in the repo; NEEDS SOURCE)")


# ---------------- candidates ----------------

def excluded_crops(context=None, district="cumilla"):
    """[{crop, variety_class, reason}] for crop-table rows that cannot be chained."""
    ctx = context or load_context(district, with_weather=False)
    return [{"crop": r["crop"], "variety_class": r["variety_class"], "reason": missing_reason(r)}
            for _, r in ctx.crop_table.iterrows() if not is_usable(r)]


def _nominal_harvest(ctx, row, sow):
    """Harvest date from the cited duration (used only to prune candidates)."""
    extra = parse_number(row["seedling_age_days"]) if (
        ctx.aman_duration_from == "transplanting" and row["seedling_age_days"]) else 0.0
    return sow + pd.Timedelta(days=int(round(extra + float(row["duration_days"]))))


def candidate_rotations(district, context=None, include_infeasible=False):
    """Rotations worth evaluating, from the crop table alone (no weather): each
    cited Kharif-2 Aman seedbed date (window start and end) followed by every
    rabi crop that has a cited duration, a sowing window and a risk-calendar
    spec, kept only if the nominal harvest + turnaround is not after the next
    window end. Each rotation is {"id", "slots", "kharif1"}."""
    ctx = context or load_context(district, with_weather=False)
    table, turn = ctx.crop_table, ctx.turnaround()
    out = []
    for _, aman in table[table["phase"] == "kharif2"].iterrows():
        if not is_usable(aman):
            continue
        for md in (aman["sow_start_mmdd"], aman["sow_end_mmdd"]):
            seedbed = pd.Timestamp(year=2001, month=parse_mmdd(md)[0], day=parse_mmdd(md)[1])
            harvest = _nominal_harvest(ctx, aman, seedbed)
            for _, nxt in table[table["phase"] == "rabi"].iterrows():
                if not is_usable(nxt) or nxt["crop"] not in ctx.specs:
                    continue
                end = rc.season_date(2001, *parse_mmdd(nxt["sow_end_mmdd"]))
                fits = harvest + pd.Timedelta(days=turn) <= end
                if fits or include_infeasible:
                    label = f"{aman['crop']}@{md[:2]}-{md[2:]}>{nxt['crop']}"
                    out.append({"id": label, "kharif1": KHARIF1_NOTE,
                                "statically_infeasible": not fits,
                                "slots": [{"crop": aman["crop"], "variety_class": aman["variety_class"],
                                           "sow_mmdd": f"{md[:2]}-{md[2:]}"},
                                          {"crop": nxt["crop"], "variety_class": nxt["variety_class"]}]})
    return out


# ---------------- one year ----------------

def _resolve_slots(ctx, rotation):
    slots = []
    for i, slot in enumerate(rotation["slots"]):
        row = pick_row(ctx.crop_table, slot["crop"], slot.get("variety_class"))
        if row is None or not is_usable(row):
            reason = "not in the crop table" if row is None else missing_reason(row)
            raise ValueError(f"cannot chain {slot['crop']}: {reason}")
        sow_md = None
        if i == 0:   # the first crop's sowing date is fixed by the rotation (default: window start)
            text = slot.get("sow_mmdd")
            sow_md = parse_mmdd(text.replace("-", "")) if text else parse_mmdd(row["sow_start_mmdd"])
        slots.append({"crop": slot["crop"], "row": row, "sow_md": sow_md,
                      "win": (parse_mmdd(row["sow_start_mmdd"]), parse_mmdd(row["sow_end_mmdd"]))})
    return slots


def _targets(ctx, crop, seasons):
    spec = ctx.specs[crop]
    if spec["stage_method"] != "gdd":
        return {}
    clim = rc.mean_climate(ctx.weather["temp_mean_c"], seasons)
    return rc.calibrate(spec, clim)


def _covered_seasons(ctx):
    first, last = ctx.weather.index.min(), ctx.weather.index.max()
    return tuple(s for s in rc.SEASONS
                 if first <= rc.season_date(s, 8, 1) and rc.season_date(s, 7, 31) + pd.Timedelta(days=1) <= last)


def _modelled_slot(ctx, slot, sow, targets):
    """Risk-calendar result for one crop sown on `sow`, or None if weather is short."""
    spec = ctx.specs[slot["crop"]]
    row = rc.season_row(spec, targets, ctx.weather, sow, ctx.water, ctx.risk_params())
    if row is None:
        return None
    summary = rc.summarise([row], spec, ctx.risk_params(), water=ctx.water is not None)
    problem = None if summary["problem_years"] is None else bool(summary["problem_years"])
    days = row.get("maturity_days")
    irrigation = row.get("net_irrigation_mm")
    checked = [h["hazard"] for h in spec["hazards"]] if problem is not None else []
    return {"problem": problem,
            "maturity_days": None if days is None or pd.isna(days) else int(days),
            "irrigation_mm": None if irrigation is None or pd.isna(irrigation) else float(irrigation),
            "checked": checked,
            "hits": [h for h in checked if summary.get(f"problem_years_{h}") == 1],
            "missing": [m["hazard"] for m in spec["missing"]]}


def _plain_slot(ctx, slot):
    """A crop with no risk-calendar spec (Aman): harvest from the cited duration."""
    row = slot["row"]
    extra = parse_number(row["seedling_age_days"]) if (
        ctx.aman_duration_from == "transplanting" and row["seedling_age_days"]) else 0.0
    days = int(round(extra + float(row["duration_days"])))
    return {"problem": None, "maturity_days": days, "irrigation_mm": None,
            "checked": [], "hits": [], "missing": ["all (no hazard or water model for this crop yet)"]}


def _year(ctx, slots, year, targets):
    """Raw per-year result, or None if weather is too short to judge the year."""
    turn = pd.Timedelta(days=ctx.turnaround())
    out, harvest = [], None
    for i, slot in enumerate(slots):
        row = slot["row"]
        if i == 0:
            sow = pd.Timestamp(year=year, month=slot["sow_md"][0], day=slot["sow_md"][1])
        else:
            start = rc.season_date(year, *slot["win"][0])
            end = rc.season_date(year, *slot["win"][1])
            earliest = harvest + turn
            sow = max(earliest, start)
            if sow > end:
                reason = (f"{slots[i - 1]['crop']} harvest {harvest.date()} + {turn.days} days "
                          f"turnaround = {earliest.date()}, after the {slot['crop']} sowing "
                          f"window end {end.date()}")
                out.append({"crop": slot["crop"], "sowing_date": None, "harvest_date": None})
                return {"year": year, "feasible": False, "reason": reason, "slots": out}
        if slot["crop"] in ctx.specs:
            result = _modelled_slot(ctx, slot, sow, targets.get(slot["crop"], {}))
            if result is None:
                return None
        else:
            result = _plain_slot(ctx, slot)
        days = result["maturity_days"]
        harvest = None if days is None else sow + pd.Timedelta(days=days)
        if harvest is None and i < len(slots) - 1:
            return None                      # next crop cannot be placed: year not judged
        out.append({"crop": slot["crop"], "phase": row["phase"], "sowing_date": sow,
                    "harvest_date": harvest, **result})
    return {"year": year, "feasible": True, "reason": None, "slots": out}


# ---------------- presentation (every number carries provenance) ----------------

def _date(d):
    return None if d is None else str(pd.Timestamp(d).date())


def _present_year(raw, wprov, tprov):
    slots = []
    for s in raw["slots"]:
        irr = s.get("irrigation_mm")
        days = s.get("maturity_days")
        slots.append({
            "crop": s["crop"], "phase": s.get("phase"), "sowing_date": _date(s["sowing_date"]),
            "harvest_date": _date(s["harvest_date"]), "problem": s.get("problem"),
            "assessed": bool(s.get("checked")), "hazards_hit": list(s.get("hits", [])),
            "maturity_days": None if days is None else measured(int(days), "days", tprov),
            "irrigation_mm": None if irr is None else measured(round(irr, 1), "mm", wprov)})
    irrigation = [s["irrigation_mm"] for s in raw["slots"] if s.get("irrigation_mm") is not None]
    problems = [s.get("problem") for s in raw["slots"] if s.get("problem") is not None]
    problem_year = None if (not raw["feasible"] or not problems) else any(problems)
    return {"year": raw["year"], "feasible": raw["feasible"],
            "infeasible_reason": raw["reason"], "problem_year": problem_year,
            "irrigation_mm": measured(round(sum(irrigation), 1), "mm", wprov)
            if raw["feasible"] and irrigation else None,
            "slots": slots}


def _summary(ctx, rotation, slots, raw_years, dropped, wprov, tprov):
    n = len(raw_years)
    feasible = [y for y in raw_years if y["feasible"]]
    problem = [y for y in feasible
               if any(s.get("problem") for s in y["slots"])]
    irr = [sum(s["irrigation_mm"] for s in y["slots"] if s.get("irrigation_mm") is not None)
           for y in feasible if any(s.get("irrigation_mm") is not None for s in y["slots"])]
    legumes = [s["crop"] for s in slots if s["row"]["is_legume"].strip().lower() == "yes"]
    unknown = sorted({s["crop"] for s in slots if not s["row"]["is_legume"].strip()})
    checked = sorted({h for y in feasible for s in y["slots"] for h in s.get("checked", [])})
    missing = sorted({h for y in raw_years for s in y["slots"] for h in s.get("missing", [])})
    line = (f"problems in {len(problem)} of {n} years" if checked
            else "problems not assessed: no sourced hazard for this rotation")
    if n - len(feasible):
        line += f"; not feasible in {n - len(feasible)} of {n} years"
    line += f" (checked: {', '.join(checked) if checked else 'nothing assessed'})"
    count = lambda v, unit, prov: measured(int(v), unit, prov)
    return {
        "n_years": count(n, "years", wprov), "feasible_years": count(len(feasible), "years", wprov),
        "infeasible_years": count(n - len(feasible), "years", wprov),
        "problem_years": count(len(problem), "years", wprov) if checked else None,
        "problem_or_infeasible_years": count(len(problem) + n - len(feasible), "years", wprov)
        if checked else None,
        "problem_years_by_hazard": {
            h: count(sum(h in s.get("hits", []) for y in feasible for s in y["slots"]), "years", wprov)
            for h in checked},
        "problem_line": line,
        "irrigation_mm_median": measured(round(float(np.median(irr)), 1), "mm", wprov) if irr else None,
        "irrigation_mm_worst20": measured(round(rc.worst_mean(irr), 1), "mm", wprov) if irr else None,
        "irrigation_years": count(len(irr), "years", wprov),
        "legume_count": count(len(legumes), "crops", tprov),
        "legume_unknown_crops": unknown,
        "hazards_checked": checked, "hazards_missing": missing,
        "dropped_years": [{"year": y} for y in dropped],
        "assumptions": [ctx.turnaround_note(),
                        f"Aman life cycle counted {'from the seedbed date' if ctx.aman_duration_from == 'seedbed' else 'from transplanting'} "
                        "(the BRRI row does not say which; NEEDS SOURCE)",
                        "Aman's own risk (flood exposure, cold at flowering) is not yet assessed, so its problems "
                        "and irrigation are not counted; Aman seedbed dates differ between candidates, "
                        "so comparisons between Aman classes are incomplete",
                        KHARIF1_NOTE],
    }


def evaluate_rotation(district, rotation, years=None, context=None):
    """Evaluate one rotation over past seasons.

    rotation: {"id", "slots": [{"crop", "variety_class"?, "sow_mmdd"? (first slot)}]}.
    years: rotation years (default 2001-2024). Returns {"district", "rotation",
    "summary", "years"}; every number is {"value", "unit", "provenance"}."""
    ctx = context or load_context(district)
    years = list(DEFAULT_YEARS if years is None else years)
    slots = _resolve_slots(ctx, rotation)
    covered = _covered_seasons(ctx)
    targets = {s["crop"]: _targets(ctx, s["crop"], covered) for s in slots if s["crop"] in ctx.specs}
    wprov = ctx.weather_provenance
    tprov = table_provenance(note="cited durations and windows from data/reference/crops.csv")
    raw, dropped = [], []
    for y in years:
        result = _year(ctx, slots, int(y), targets)
        (dropped.append(int(y)) if result is None else raw.append(result))
    return {"district": district,
            "rotation": {"id": rotation.get("id"), "slots": rotation["slots"],
                         "kharif1": rotation.get("kharif1", KHARIF1_NOTE)},
            "summary": _summary(ctx, rotation, slots, raw, dropped, wprov, tprov),
            "years": [_present_year(r, wprov, tprov) for r in raw]}

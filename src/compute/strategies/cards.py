"""
src/compute/strategies/cards.py

The five-heading card per strategy, filled deterministically from the computed
indicators (Layer 1, no AI, plain templates): Why suggested, Evidence,
Benefits, Information gaps, Risks to check locally. Past-seasons wording only;
the words "predict" and "forecast" never appear.
"""

HEADINGS = ("why_suggested", "evidence", "benefits",
            "information_gaps", "risks_to_check_locally")

SAAO_LINE = ("Please confirm with your SAAO (upazila agriculture officer) before changing "
             "the rotation: this card supports local judgment, it does not replace it.")


def _crops(strategy):
    return [s["crop"] for s in strategy["rotation"]["slots"]]


def _non_aman(strategy):
    names = [c for c in _crops(strategy) if c != "aman_rice"]
    return ", ".join(names) if names else strategy["id"]


def _problem_text(p):
    rng = f" (bootstrap {int(p['level'] * 100)}%: {p['lo']} to {p['hi']})" if "lo" in p else ""
    return f"problems in {p['count']['value']} of {p['n']} past seasons{rng}"


def _why(strategy, baseline, ind, bind):
    lines = []
    if strategy.get("role") == "baseline":
        lines.append("This is your current rotation, shown as the baseline so every "
                     "alternative is compared against the same past seasons.")
        p = ind.get("problem_years", {})
        if p.get("status") == "assessed":
            lines.append(f"Tested on past seasons: {_problem_text(p)}.")
        return lines
    p, bp = ind.get("problem_years", {}), bind.get("problem_years", {})
    if p.get("status") == "assessed" and bp.get("status") == "assessed":
        lines.append(f"Tested on {p['n']} past seasons: {_problem_text(p)}, against "
                     f"{bp['count']['value']} of {bp['n']} for your current rotation.")
    elif p.get("status") == "assessed":
        lines.append(f"Tested on {p['n']} past seasons: {_problem_text(p)} "
                     "(your current rotation is not assessed on this).")
    w, bw = ind.get("water_use", {}), bind.get("water_use", {})
    if w.get("status") == "assessed" and bw.get("status") == "assessed":
        a, b = w["worst20"]["value"], bw["worst20"]["value"]
        direction = "less" if a < b else ("more" if a > b else "the same")
        lines.append(f"Irrigation need in the driest 20% of past seasons: {a} mm, "
                     f"{direction} than the current rotation's {b} mm "
                     "(Kc-weighted FAO-56 balance).")
    n = ind.get("nitrogen_fixing", {})
    if n.get("status") == "assessed" and n["count"]["value"] > 0:
        lines.append(f"Adds {int(n['count']['value'])} nitrogen-fixing (legume) crop(s), "
                     "from the cited legume flag.")
    if not lines:
        lines.append("Offered as an alternative tested on the same past seasons; "
                     "see the indicators for how it compares.")
    return lines


def _evidence(strategy, ind):
    lines = [f"Tested on {strategy.get('evidence_n_years', 'the available')} past seasons; "
             "every number carries its dataset and source link."]
    if strategy.get("datasets"):
        lines.append("Datasets: " + ", ".join(strategy["datasets"]) + ".")
    p = ind.get("problem_years", {})
    if p.get("status") == "assessed" and p.get("hazards_checked"):
        lines.append("Hazards checked: " + ", ".join(p["hazards_checked"]) + ".")
    bare = ind.get("bare_field_days", {})
    if bare.get("status") == "assessed":
        lines.append(f"Bare-field days: about {bare['days_median']['value']:.0f} per year, "
                     "from our windows, not satellite-observed.")
    return lines


def _soil_lines(om):
    soil = om.get("soil_baseline")
    if not soil:
        return []
    lines = []
    oc = soil["organic_carbon"]
    if oc["status"] == "assessed":
        parts = [f"{l['depth']} {l['mean']['value']:.1f} {l['mean']['unit']} "
                 f"(model range {l['q05']['value']:.1f} to {l['q95']['value']:.1f})"
                 for l in oc["layers"]]
        lines.append("Soil organic carbon at the district point: " + "; ".join(parts)
                     + f". {soil['label']}.")
    ph = soil["ph"]
    if ph["status"] == "assessed":
        parts = [f"{l['depth']} pH {l['mean']['value']:.1f} "
                 f"(model range {l['q05']['value']:.1f} to {l['q95']['value']:.1f})"
                 for l in ph["layers"]]
        lines.append("Soil pH at the district point: " + "; ".join(parts) + f". {soil['label']}.")
    return lines


def _benefits(strategy, ind):
    lines = []
    n = ind.get("nitrogen_fixing", {})
    if n.get("status") == "assessed" and n["count"]["value"] > 0:
        lines.append(f"{int(n['count']['value'])} legume crop(s): nitrogen fixing, "
                     "per the cited legume flag.")
    pest = ind.get("pest_cycle_break", {})
    if pest.get("status") == "assessed" and pest.get("breaks_cycle"):
        lines.append("Changes crop family between seasons ("
                     + " then ".join(pest.get("families", [])) +
                     "); the cited rule links a family change to avoiding pest "
                     "buildup (needs local review).")
    rd = ind.get("root_depth", {})
    if rd.get("status") == "assessed" and rd.get("by_crop"):
        deep = {c: v["zr_max_m"]["value"] for c, v in rd["by_crop"].items()
                if v.get("status") == "assessed"}
        if deep:
            crop, zr = max(deep.items(), key=lambda kv: kv[1])
            lines.append(f"Deepest cited rooting depth: {crop} up to {zr} m "
                         "(FAO-56 Table 22; deeper roots are read as better infiltration).")
    f = ind.get("forage", {})
    if f.get("status") == "assessed":
        lines.append("Cited forage rows exist for this rotation's crops "
                     "(values quoted as stated in the source).")
    m = ind.get("market_price", {})
    if m.get("status") == "assessed":
        when = _month_text(m.get("as_of"))
        lines.append(f"Cited market price for {m['crop']}: {m['measure']['value']} "
                     f"{m['measure']['unit']}, {m.get('price_type', 'price type not stated')}"
                     f"{', reported ' + when if when else ''} "
                     "(a price, not income per hectare).")
    om = ind.get("organic_matter", {})
    lines += _soil_lines(om)
    if om.get("status") == "assessed" and om.get("by_crop"):
        lines.append("Cited residue rows exist (organic-matter context; no per-hectare "
                     "amount is computed).")
    if not lines:
        lines.append("No cited benefit row beyond the indicators above.")
    return lines


def _gaps(ind):
    lines = []
    for name, value in ind.items():
        if isinstance(value, dict) and value.get("status") == "gap":
            label = name.replace("_", " ")
            lines.append(f"{label}: {value['reason']}")
    om = ind.get("organic_matter", {})
    for key, what in (("soil_note", "soil baseline"), ("residue_note", "residue rows")):
        if om.get(key):
            lines.append(f"organic matter, {what}: {om[key]}")
    soil = om.get("soil_baseline", {})
    for prop in ("ph", "organic_carbon"):
        if soil.get(prop, {}).get("status") == "gap":
            lines.append(f"soil {prop.replace('_', ' ')} (SoilGrids): {soil[prop]['reason']}")
    n = ind.get("nitrogen_fixing", {})
    if n.get("status") == "assessed" and n.get("unknown"):
        lines.append("legume flag unknown (NEEDS SOURCE) for: " + ", ".join(n["unknown"]))
    if not lines:
        lines.append("No known information gap for this strategy's indicators.")
    return lines


def _risks(strategy, ind, pest_rule):
    lines = [SAAO_LINE]
    if pest_rule and pest_rule.get("status") == "assessed":
        lines.append("Pest-cycle rule: " + pest_rule["value"] + " — " + pest_rule["note"] + ".")
    ero = ind.get("erosion_exposure", {})
    if ero.get("status") == "assessed":
        lines.append("Erosion exposure is a relative ranking only (flat delta land; "
                     "slope terciles are our choice); check the field's real slope and "
                     "drainage locally.")
    bare = ind.get("bare_field_days", {})
    if bare.get("status") == "assessed":
        lines.append("Bare-field days come from our sowing-to-harvest windows, not from "
                     "satellite observation; actual field cover may differ.")
    m = ind.get("market_price", {})
    if m.get("status") == "assessed":
        lines.append("Prices move with season and market; check the current local price "
                     "before deciding.")
    return lines


def five_heading_card(strategy, baseline, pest_rule=None):
    """The five-heading card as an ordered dict of lists of plain sentences."""
    ind, bind = strategy["indicators"], baseline["indicators"]
    return {"why_suggested": _why(strategy, baseline, ind, bind),
            "evidence": _evidence(strategy, ind),
            "benefits": _benefits(strategy, ind),
            "information_gaps": _gaps(ind),
            "risks_to_check_locally": _risks(strategy, ind, pest_rule)}


MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _month_text(as_of):
    """'2026-02' -> 'Feb 2026'; anything else -> ''."""
    try:
        year, month = str(as_of).split("-")[:2]
        return f"{MONTHS[int(month) - 1]} {int(year)}"
    except (ValueError, IndexError):
        return ""

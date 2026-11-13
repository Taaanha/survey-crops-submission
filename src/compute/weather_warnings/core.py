"""Weather-outlook warnings: pure comparison of daily numbers with sourced thresholds. No AI, no network.

Thresholds are never written here. Each rule only names a row (file + item) in data/reference/; the
value, unit and source link come from that row. A row is used only if it has a number, an http source
link, and no placeholder / suspect / gap marker in its notes. Otherwise the rule is skipped and
reported in `skipped`, and no warning is ever made from it.
"""

import os
import re

import pandas as pd

REFERENCE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "reference")
BAD_MARKERS = ("placeholder", "suspect", "fabricated", "gap")
URL_RE = re.compile(r"^https?://[^\s/]+\.[^\s/]+\S*$", re.I)
NUMBER_RE = re.compile(r"^(?:below|above|under|over|>|<)?\s*(-?\d+(?:\.\d+)?)\s*$", re.I)

# (type, field, op, crop, stage_en, stage_bn, file, item). field: rain_mm / tmax_c / tmin_c.
# op "ge" = value >= threshold, "gt" = value > threshold, "lt" = value < threshold.
ANY_EN, ANY_BN = "any stage (the source gives no stage)", "যেকোনো পর্যায়"
FLOWER_EN, FLOWER_BN = "flowering", "ফুল ফোটার সময়"
RULES = [
    ("heavy_rain", "rain_mm", "ge", None, None, None, "r03_heavy_rain.csv", "bmd_heavy_rain_min"),
    ("heavy_rain", "rain_mm", "gt", None, None, None, "r03_heavy_rain.csv", "bmd_very_heavy_rain_above"),
    ("heat", "tmax_c", "gt", "mustard", FLOWER_EN, FLOWER_BN, "crop_thresholds.csv",
     "mustard.heat.flowering_tmax_high"),
    ("heat", "tmax_c", "gt", "wheat", FLOWER_EN, FLOWER_BN, "crop_thresholds.csv",
     "wheat.heat.anthesis_tmax"),
    ("heat", "tmax_c", "gt", "lentil", FLOWER_EN, FLOWER_BN, "crop_thresholds.csv",
     "lentil.heat.flowering_tmax"),
    ("heat", "tmax_c", "gt", "boro rice", FLOWER_EN, FLOWER_BN, "crop_thresholds.csv",
     "boro_rice.heat.anthesis_tmax"),
    ("cold", "tmin_c", "lt", "boro rice", ANY_EN, ANY_BN, "r04_cold_injury.csv",
     "boro_rice.cold.bamis_warning_tmin"),
    ("cold", "tmin_c", "lt", "mustard", ANY_EN, ANY_BN, "r04_cold_injury.csv",
     "mustard.cold.bamis_warning_tmin"),
    ("cold", "tmin_c", "lt", "potato", ANY_EN, ANY_BN, "r04_cold_injury.csv",
     "potato.cold.bamis_warning_tmin"),
    # Present on purpose: these rows are marked SUSPECT / PLACEHOLDER in the CSVs, so they are skipped.
    ("cold", "tmin_c", "lt", "wheat", ANY_EN, ANY_BN, "r04_cold_injury.csv",
     "wheat.cold.bamis_warning_tmin"),
    ("cold", "tmin_c", "lt", "aman rice", FLOWER_EN, FLOWER_BN, "crop_thresholds.csv",
     "aman_rice.cold.flowering_tmin"),
]
UNITS = {"rain_mm": "mm/24h", "tmax_c": "°C", "tmin_c": "°C"}
HEADLINE = {"heavy_rain": max, "heat": max, "cold": min}   # the most severe exceeded level leads

ACTIONS = {
    "heavy_rain": {
        "en": "Heavy rain is expected. Keep drains open and check low plots for standing water. "
              "Ask your SAAO before sowing or spraying on this day.",
        "bn": "ভারী বৃষ্টির সম্ভাবনা আছে। নালা খোলা রাখুন এবং নিচু জমিতে পানি জমছে কি না দেখুন। "
              "এই দিনে বোনা বা স্প্রে করার আগে আপনার উপসহকারী কৃষি কর্মকর্তার সাথে কথা বলুন।"},
    "heat": {
        "en": "A hot day is expected. This heat can hurt: {crops}. Check which stage your crop is at "
              "and ask your SAAO about light irrigation.",
        "bn": "গরম দিনের সম্ভাবনা আছে। এই গরমে ক্ষতি হতে পারে: {crops}। আপনার ফসল কোন পর্যায়ে আছে দেখুন "
              "এবং হালকা সেচের বিষয়ে আপনার উপসহকারী কৃষি কর্মকর্তার সাথে কথা বলুন।"},
    "cold": {
        "en": "A cold night is expected. Cold can hurt: {crops}. "
              "Ask your SAAO how to protect it.",
        "bn": "ঠান্ডা রাতের সম্ভাবনা আছে। ঠান্ডায় ক্ষতি হতে পারে: {crops}। "
              "রক্ষার উপায় জানতে আপনার উপসহকারী কৃষি কর্মকর্তার সাথে কথা বলুন।"},
}
CROP_BN = {"mustard": "সরিষা", "wheat": "গম", "lentil": "মসুর", "boro rice": "বোরো ধান",
           "potato": "আলু", "aman rice": "আমন ধান"}


def _number(text):
    m = NUMBER_RE.match(str(text).strip())
    return float(m.group(1)) if m else None


def _unusable_reason(row):
    """None if the row is fit to warn on, else why it is not."""
    if _number(row["value"]) is None:
        return "value is not a single number"
    if not URL_RE.match(str(row.get("source_url", "")).strip()):
        return "no usable http source link"
    if any(m in str(row.get("notes", "")).lower() for m in BAD_MARKERS):
        return "notes mark it as placeholder, suspect or a gap"
    return None


def load_thresholds(reference_dir=REFERENCE_DIR):
    """Returns (thresholds, skipped). thresholds: one dict per usable rule (value, unit, source).
    skipped: [{"item", "file", "reason"}] for every rule with no usable sourced row."""
    tables, thresholds, skipped = {}, [], []
    for typ, field, op, crop, stage_en, stage_bn, fname, item in RULES:
        if fname not in tables:
            path = os.path.join(reference_dir, fname)
            tables[fname] = (pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
                             if os.path.exists(path) else None)
        table = tables[fname]
        rows = [] if table is None else table[table["item"] == item].to_dict("records")
        reasons = [_unusable_reason(r) for r in rows]
        good = [r for r, why in zip(rows, reasons) if why is None]
        if not good:
            skipped.append({"item": item, "file": fname,
                            "reason": reasons[0] if reasons else "no such row in the reference file"})
            continue
        row = good[0]
        thresholds.append({"type": typ, "field": field, "op": op, "crop": crop, "stage_en": stage_en,
                           "stage_bn": stage_bn, "item": item, "file": fname, "value": _number(row["value"]),
                           "unit": UNITS[field], "source_title": row["source_title"],
                           "source_url": row["source_url"].strip(), "page": row.get("page", ""),
                           "year": row.get("year", "")})
    return thresholds, skipped


def _exceeds(value, op, limit):
    if op == "ge":
        return value >= limit
    return value > limit if op == "gt" else value < limit


def _action(typ, crops):
    """Action text. Heat names the stage the source gives (e.g. "mustard at flowering")."""
    def join(key_stage, names):
        parts = []
        for t in crops:
            name = names.get(t["crop"], t["crop"])
            stage = t[key_stage] if key_stage == "stage_bn" or t["stage_en"] != ANY_EN else ""
            parts.append(f"{name} ({stage})" if stage and typ == "heat" else name)
        return ", ".join(dict.fromkeys(parts))
    return {"en": ACTIONS[typ]["en"].format(crops=join("stage_en", {}) or "crop"),
            "bn": ACTIONS[typ]["bn"].format(crops=join("stage_bn", CROP_BN) or "ফসল")}


def evaluate_days(days, thresholds):
    """days: [{"date", "rain_mm", "tmax_c", "tmin_c"}] (a missing number is None: not assessed).
    One warning per (type, date): the most severe exceeded level is the headline `threshold`, and
    `crops` lists every crop-specific level exceeded. Nothing exceeded = no warning (empty list)."""
    out = []
    for day in days:
        for typ in ("heavy_rain", "heat", "cold"):
            hit = [t for t in thresholds if t["type"] == typ and day.get(t["field"]) is not None
                   and _exceeds(day[t["field"]], t["op"], t["value"])]
            if not hit:
                continue
            head = HEADLINE[typ](hit, key=lambda t: t["value"])
            crops = [t for t in hit if t["crop"]]
            out.append({"type": typ, "date": day["date"],
                        "expected": {"value": day[head["field"]], "unit": head["unit"]},
                        "threshold": head, "crops": crops, "action": _action(typ, crops)})
    return out

"""
src/api/disease_block.py

Builds the additive `disease_risks` list for GET /api/v1/risk-calendar from
src/compute/disease_risk. Pure builder: app.py passes the helpers it owns, so this file
imports nothing from app.py. Every number carries `src` ids that resolve in provenance[].
A crop with no sourced rule gets status "not_assessed" and a reason, never a 0.
"""

import functools
import os

import disease_risk as dr
from reference import REFERENCE_DIR, load_file
from weather import load_weather

DISEASE_FILE = os.path.join(REFERENCE_DIR, "disease_rules_draft.csv")
BN_MONTHS = ["জানু", "ফেব্রু", "মার্চ", "এপ্রিল", "মে", "জুন", "জুলাই", "আগস্ট", "সেপ্টে", "অক্টো", "নভে", "ডিসে"]
EN_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WINDOW_NOTE = {
    "en": "No sourced harvest date exists for potato, so the window runs from the start of the cited sowing "
          "window to the end of that window plus 55 days (the cited upper tuber-start day count). Later "
          "weather is not counted.",
    "bn": "আলুর ফসল তোলার কোনো সূত্রসহ তারিখ নেই, তাই সময়কাল ধরা হয়েছে উৎসের বপন-সময়ের শুরু থেকে "
          "তার শেষ + ৫৫ দিন (উৎসের কন্দ-শুরুর সর্বোচ্চ দিন) পর্যন্ত। এর পরের আবহাওয়া গণনায় নেই।"}
MEANING = {
    "en": "Past seasons show weather that suits this disease. It does not mean the disease occurred.",
    "bn": "অতীত মৌসুমে এই রোগের অনুকূল আবহাওয়া কতবার ছিল তা দেখানো হয়েছে। এর মানে এই নয় যে রোগ হয়েছিল।"}
RULE_NOTICE = {
    "en": "The late-blight weather rule is from a 1954 paper; the exact page in that journal issue is not "
          "pinned yet. Only weather is counted. Insect pests, soil nutrients and prices are not checked.",
    "bn": "লেট ব্লাইটের আবহাওয়া-নিয়মটি ১৯৫৪ সালের একটি গবেষণা থেকে; সেই সংখ্যার সঠিক পৃষ্ঠা এখনও নির্দিষ্ট করা "
          "হয়নি। শুধু আবহাওয়া গণনা হয়েছে। পোকা, মাটির পুষ্টি ও দাম যাচাই করা হয়নি।"}
NOT_ASSESSED_REASON_BN = "এই ফসলের রোগের জন্য সূত্রসহ কোনো আবহাওয়া-নিয়ম ব্যবহার করা যায়নি।"
RULE_LABELS = {
    "tmean_below_c": ("5-day mean temperature below", "degC"),
    "rain10_mm_at_least": ("10-day rain total at least", "mm"),
    "tmin_unfavourable_below_c": ("Daily minimum below this is not favourable", "degC"),
}


@functools.lru_cache(maxsize=1)
def reference_rows():
    return load_file(DISEASE_FILE)


@functools.lru_cache(maxsize=8)
def district_weather(district):
    return load_weather(district)


def _date_text(first, last, months):
    return f"{first.day} {months[first.month - 1]} to {last.day} {months[last.month - 1]}"


def build_disease_risks(district, crop, spec, ref_ids_for, bn_digits):
    """The list for one district x crop (always one entry)."""
    kept, skipped = reference_rows()
    spec = spec or {}
    window = spec.get("window") or {}
    tuber = (spec.get("stage_days") or {}).get("tuber_end")
    start, end = window.get("start"), window.get("end")
    extra = tuber["value"] if tuber and crop == "potato" else None
    has_rule = dr.build_rule(kept, crop) is not None
    weather = district_weather(district) if has_rule and start and end and extra is not None else None
    res = dr.assess_crop(crop, weather, kept, skipped, tuple(start) if start else None,
                         tuple(end) if end else None, extra)
    if res["status"] != "assessed":
        reason = res["reason"]
        label = (dr.DISEASES.get(crop) or {}).get("label")
        return [{"crop": crop, "status": "not_assessed", "disease_label": label, "reason": reason,
                 "text": {"en": f"Disease weather risk: not assessed ({reason}).",
                          "bn": NOT_ASSESSED_REASON_BN}}]
    src = ["imerg", "power"] + ref_ids_for(res["citations"])
    n, fav, anyd = res["n_seasons"], res["seasons_favourable"], res["seasons_any_favourable_day"]
    first, last = dr.season_window(2001, tuple(start), tuple(end), extra)
    win_en, win_bn = _date_text(first, last, EN_MONTHS), _date_text(first, last, BN_MONTHS)
    name = res["label"]
    unit = f"past seasons (of {n})"

    def m(value, u=unit):
        return {"value": value, "unit": u, "src": list(dict.fromkeys(src))}

    run = res["rule"]["min_run_days"]
    return [{
        "crop": crop, "disease": res["disease"], "disease_label": name, "status": "assessed",
        "seasons_favourable": m(fav),
        "seasons_any_favourable_day": m(anyd),
        "seasons_counted": m(n, "past seasons"),
        "skipped_seasons": res["skipped_seasons"],
        "min_run_days": m(run, "days in a row"),
        "window": {"start": list(start), "end": list(end), "extra_days": m(extra, "days"),
                   "text": {"en": win_en, "bn": win_bn}, "note": WINDOW_NOTE},
        "rule": [{"id": k, "label": RULE_LABELS[k][0], **m(v, RULE_LABELS[k][1])}
                 for k, v in res["rule"]["values"].items()],
        "per_season": res["per_season"],
        "meaning": MEANING,
        "text": {"en": f"Conditions favourable for {name['en'].lower()} in {fav} of {n} past seasons "
                       f"({run} favourable days in a row, {win_en}). {MEANING['en']}",
                 "bn": f"{name['bn']}-এর অনুকূল আবহাওয়া অতীতের {bn_digits(n)} মৌসুমের মধ্যে {bn_digits(fav)}টিতে "
                       f"ছিল ({bn_digits(run)} দিন পরপর, {win_bn})। {MEANING['bn']}"},
    }]

"""
src/agents/ask_tools.py

The tools the /ask agent can call. Each one asks an existing, cited API
endpoint (through `api`, a function the caller supplies) and returns:

  {"tool", "args", "ok", "text": {"en", "bn"}, "data", "sources", "notices",
   "error"}

`text` is the sentence the user will see. It is the endpoint's own guarded
narration, or (soil, warnings, rotation ranking) built here from numbers in
`data`. Nothing is invented: guard() later checks every number against
{"data", "sources"}. No AI calls in this file.

All Bangla text NEEDS NATIVE REVIEW (docs/AI_USE.md).
"""

import re

from language import BN_CROPS, EN_CROPS, localise_digits

DISTRICTS = {
    "cumilla": ("Cumilla", "কুমিল্লা"), "feni": ("Feni", "ফেনী"),
    "brahmanbaria": ("Brahmanbaria", "ব্রাহ্মণবাড়িয়া"),
    "noakhali": ("Noakhali", "নোয়াখালী"), "sylhet": ("Sylhet", "সিলেট"),
}
CAL_CROPS = ["wheat", "mustard", "lentil", "potato", "boro_rice"]
PRIORITIES = {  # key -> (en, bn)
    "save_water": ("saving water", "পানি সাশ্রয়"),
    "soil_health": ("soil health", "মাটির স্বাস্থ্য"),
    "lowest_risk": ("lowest risk", "কম ঝুঁকি"),
    "flood_safety": ("flood safety", "বন্যা নিরাপত্তা"),
}

TOOLS = [
    {"type": "function", "function": {
        "name": "get_advice",
        "description": "Ranked crop options for what to sow next in a district: sowing window, "
                       "problems in X of N past years, irrigation need. Use for 'what should I "
                       "plant', 'what to grow now'.",
        "parameters": {"type": "object", "properties": {
            "district": {"type": "string", "enum": list(DISTRICTS)},
            "prev_harvest": {"type": "string",
                             "description": "YYYY-MM-DD the last crop was harvested. Leave out if unknown."},
            "water": {"type": "string", "enum": ["rain_only", "limited", "regular", "plenty"]},
            "priority": {"type": "array", "items": {"type": "string",
                         "enum": ["risk", "water", "more", "soil"]}}},
            "required": ["district"]}}},
    {"type": "function", "function": {
        "name": "get_crop_risk",
        "description": "Sowing-date risk for one crop in a district: problems in X of N past years.",
        "parameters": {"type": "object", "properties": {
            "district": {"type": "string", "enum": list(DISTRICTS)},
            "crop": {"type": "string", "enum": CAL_CROPS}},
            "required": ["district", "crop"]}}},
    {"type": "function", "function": {
        "name": "get_rotation_ranking",
        "description": "Whole-year crop rotations ranked by what the farmer cares about.",
        "parameters": {"type": "object", "properties": {
            "district": {"type": "string", "enum": list(DISTRICTS)},
            "priorities": {"type": "array", "items": {"type": "string", "enum": list(PRIORITIES)}}},
            "required": ["district", "priorities"]}}},
    {"type": "function", "function": {
        "name": "get_soil",
        "description": "Soil texture around the district (a model estimate, not a lab test).",
        "parameters": {"type": "object", "properties": {
            "district": {"type": "string", "enum": list(DISTRICTS)}}, "required": ["district"]}}},
    {"type": "function", "function": {
        "name": "get_warnings",
        "description": "Weather warnings for the next few days, with actions.",
        "parameters": {"type": "object", "properties": {
            "district": {"type": "string", "enum": list(DISTRICTS)}}, "required": ["district"]}}},
]


def _fail(name, args, en, bn=None):
    return {"tool": name, "args": args, "ok": False, "text": {"en": en, "bn": bn or en},
            "data": None, "sources": [], "notices": [], "error": en}


def _call(api, method, path, params=None, body=None):
    """-> (envelope or None, error dict or None). Never raises."""
    try:
        status, env = api(method, path, params, body)
    except Exception as exc:  # noqa: BLE001 - one failing tool must not stop the answer
        return None, {"en": f"The data service failed ({type(exc).__name__}).",
                      "bn": "ডেটা সার্ভিস সাড়া দেয়নি।"}
    if not isinstance(env, dict) or env.get("data") is None or status != 200:
        errs = (env or {}).get("errors") or [{}]
        return None, {"en": errs[0].get("en") or "No answer from the data service.",
                      "bn": errs[0].get("bn") or "ডেটা সার্ভিস থেকে উত্তর আসেনি।"}
    return env, None


def _wrap(name, args, env, text):
    return {"tool": name, "args": args, "ok": True, "text": text,
            "data": env["data"], "sources": env.get("provenance") or [],
            "notices": env.get("notices") or [], "error": None}


def _narration(name, args, env):
    n = env.get("narration") or {}
    if not (n.get("en") and n.get("bn")):
        return _fail(name, args, "The service gave no readable summary for this.",
                     "এর জন্য পড়ার মতো সারসংক্ষেপ পাওয়া যায়নি।")
    return _wrap(name, args, env, {"en": n["en"], "bn": n["bn"]})


def _crop(slot_crop, lang):
    names = BN_CROPS if lang == "bn" else EN_CROPS
    return names.get(slot_crop, slot_crop)


def _rank_text(env, priorities):
    data = env["data"]
    ranked = data.get("ranked") or []
    if not ranked:
        return None
    top = ranked[0]
    slots = (top.get("rotation") or {}).get("slots") or []
    crops = [s.get("crop") for s in slots if s.get("crop")]
    labels = {l: " এবং ".join(PRIORITIES[k][1] for k in priorities) if l == "bn"
              else " and ".join(PRIORITIES[k][0] for k in priorities) for l in ("en", "bn")}
    en = f"Best rotation for {labels['en']}: " + ", then ".join(_crop(c, "en") for c in crops) + "."
    bn = f"{labels['bn']} অনুযায়ী সেরা ঘূর্ণন: " + ", তারপর ".join(_crop(c, "bn") for c in crops) + "।"
    m = re.search(r"problems in (\d+) of (\d+) years", str(top.get("problem_line", "")))
    if m:
        en += f" It had problems in {m.group(1)} of {m.group(2)} past years."
        bn += f" গত {m.group(2)} বছরের {m.group(1)} বছরে সমস্যা হয়েছে।"
    raw = ((top.get("components") or {}).get("save_water") or {}).get("raw")
    if "save_water" in priorities and isinstance(raw, dict) and isinstance(raw.get("value"), (int, float)):
        mm = round(raw["value"])
        en += f" It needs about {mm} mm of irrigation in the driest 20% of years."
        bn += f" সবচেয়ে শুকনো ২০% বছরে এতে প্রায় {mm} মিমি সেচ লাগে।"
    if data.get("unranked"):
        en += " Some rotations could not be ranked: not assessed."
        bn += " কিছু ঘূর্ণন মূল্যায়ন করা হয়নি।"
    return {"en": en, "bn": localise_digits(bn, "bn")}


def _soil_text(env, did):
    soil = env["data"].get("soil") or {}
    tex = soil.get("texture") or {}
    parts = [(k, (soil.get(f"{k}_pct") or {}).get("value")) for k in ("sand", "silt", "clay")]
    if not tex.get("en") or any(v is None for _, v in parts):
        return None
    adv = env["data"].get("test_advice") or {}
    names = {"sand": ("sand", "বালি"), "silt": ("silt", "পলি"), "clay": ("clay", "এঁটেল")}
    en = (f"Soil around {DISTRICTS[did][0]}: {tex['en']} (" +
          ", ".join(f"{names[k][0]} {v:g}%" for k, v in parts) +
          "), a model estimate, not a lab test. " + (adv.get("en") or ""))
    bn = (f"{DISTRICTS[did][1]} এলাকার মাটি: {tex.get('bn') or tex['en']} (" +
          ", ".join(f"{names[k][1]} {v:g}%" for k, v in parts) +
          "); এটি মডেলের অনুমান, ল্যাব পরীক্ষা নয়। " + (adv.get("bn") or ""))
    return {"en": en.strip(), "bn": localise_digits(bn.strip(), "bn")}


def _warn_text(env, did):
    d = env["data"]
    ws = d.get("warnings") or []
    if not ws:
        return {"en": f"No weather warnings for {DISTRICTS[did][0]} from {d.get('valid_from')} to {d.get('valid_to')}.",
                "bn": localise_digits(f"{DISTRICTS[did][1]}-এ {d.get('valid_from')} থেকে {d.get('valid_to')} পর্যন্ত কোনো আবহাওয়া সতর্কতা নেই।", "bn")}
    groups = {}  # same advice on several days is shown once, with all its dates
    for w in ws:
        act = w.get("action") or {}
        g = groups.setdefault((act.get("en", ""), act.get("bn", "")), [])
        g.append(str(w.get("date")))
    items = list(groups.items())[:3]
    en = " ".join(f"{', '.join(dates)}: {a[0]}" for a, dates in items)
    bn = " ".join(f"{', '.join(dates)}: {a[1]}" for a, dates in items)
    return {"en": en.strip(), "bn": localise_digits(bn.strip(), "bn")}


def run_tool(name, args, api, today):
    """Run one tool by name. `args` is a dict (already parsed). Unknown tool
    or bad arguments give ok=False with a plain-language error."""
    args = args if isinstance(args, dict) else {}
    did = args.get("district")
    if name not in {t["function"]["name"] for t in TOOLS}:
        return _fail(name, args, f"Unknown tool: {name}.")
    if did not in DISTRICTS:
        return _fail(name, args, "This district is not covered (basic mode only).",
                     "এই জেলা এখনো কভার করা হয়নি (শুধু সাধারণ মোড)।")

    if name == "get_advice":
        params = {"district": did, "prev_harvest": args.get("prev_harvest") or today}
        if args.get("water"):
            params["water"] = args["water"]
        if args.get("priority"):
            params["priority"] = ",".join(args["priority"])
        env, err = _call(api, "GET", "/api/v1/advisory", params)
        return _fail(name, args, err["en"], err["bn"]) if err else _narration(name, args, env)
    if name == "get_crop_risk":
        params = {"district": did, "crop": args.get("crop")}
        env, err = _call(api, "GET", "/api/v1/risk-calendar", params)
        return _fail(name, args, err["en"], err["bn"]) if err else _narration(name, args, env)
    if name == "get_rotation_ranking":
        keys = [k for k in (args.get("priorities") or []) if k in PRIORITIES] or ["lowest_risk"]
        env, err = _call(api, "POST", "/api/v1/rotation/rank", None,
                         {"district": did, "weights": {k: 1.0 for k in keys}})
        if err:
            return _fail(name, args, err["en"], err["bn"])
        text = _rank_text(env, keys)
        return _wrap(name, args, env, text) if text else _fail(name, args, "No rotation could be ranked.", "কোনো ঘূর্ণন র‍্যাঙ্ক করা যায়নি।")
    builder = {"get_soil": ("/api/v1/soil", _soil_text), "get_warnings": ("/api/v1/warnings", _warn_text)}[name]
    env, err = _call(api, "GET", builder[0], {"district": did})
    if err:
        return _fail(name, args, err["en"], err["bn"])
    text = builder[1](env, did)
    return _wrap(name, args, env, text) if text else _fail(name, args, "The service gave no readable answer.", "পড়ার মতো উত্তর পাওয়া যায়নি।")


def guard_view(result):
    """What guard() sees for a tool result: the numbers plus their sources."""
    return {"data": result["data"], "sources": result["sources"]}

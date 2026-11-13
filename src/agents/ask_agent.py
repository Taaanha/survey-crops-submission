"""
src/agents/ask_agent.py  (T17)

The /ask agent: a plain loop, at most STEP_CAP (6) model calls.

  question -> model picks tools (Hugging Face free model) -> tools ask the
  cited API -> answer = the tools' own sentences (+ one short model
  sentence if it passes guard()) -> template/rule fallback if the model is
  missing, slow, garbled or wrong. It never returns an empty answer.

The model decides WHICH tools to call. It never supplies a fact: every
number in the final text must be in a tool result that has a dataset and a
link (guard()). No token, no network or a bad reply -> rule_route() picks
the tools from keywords and the answer is the same, from the same data.
"""

import json
import os

import requests

from ask_tools import DISTRICTS, TOOLS, guard_view, run_tool
from guard import guard
from language import NO_ANSWER, compose_answer, detect_language

STEP_CAP = 6
HF_URL = "https://router.huggingface.co/v1/chat/completions"
DEFAULT_MODEL = "meta-llama/Llama-3.1-8B-Instruct"

SYSTEM = (
    "You help farmers in Bangladesh choose crops. You have tools that return "
    "checked facts from NASA satellite data. Rules: (1) Call a tool for every "
    "factual question; never answer a fact from memory. (2) Use only these "
    "districts: {districts}. If none is named, use {district}. (3) After the "
    "tool results, write ONE short plain sentence of help in {language}. Do "
    "not repeat numbers, do not name a crop the tools did not return, and "
    "never use the words predict or forecast. The facts are shown to the "
    "farmer separately."
)


def hf_chat(messages, tools, model=None, token=None, timeout=25):
    """One call to the free Hugging Face router. Returns
    {"content", "tool_calls": [{"id", "name", "arguments"}]}; raises on any
    failure (the loop catches it and uses the rule router)."""
    token = token or os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not set")
    r = requests.post(
        HF_URL, timeout=timeout,
        headers={"Authorization": f"Bearer {token}"},
        json={"model": model or os.environ.get("HF_MODEL", DEFAULT_MODEL),
              "messages": messages, "tools": tools, "tool_choice": "auto",
              "max_tokens": 220, "temperature": 0.1})
    r.raise_for_status()
    msg = r.json()["choices"][0]["message"]
    calls = [{"id": c.get("id") or f"call_{i}", "name": c["function"]["name"],
              "arguments": c["function"].get("arguments") or "{}"}
             for i, c in enumerate(msg.get("tool_calls") or [])]
    return {"content": msg.get("content") or "", "tool_calls": calls}


def find_district(question, default):
    """A district named in the question (English or Bangla), else `default`."""
    low = question.lower()
    for did, (en, bn) in DISTRICTS.items():
        if did in low or en.lower() in low or bn in question:
            return did
    return default if default in DISTRICTS else "cumilla"


_KEYWORDS = [  # (tool, priorities or None, English words, Bangla words)
    ("get_soil", None, ("soil", "texture", "clay", "sand", "ph "), ("মাটি",)),
    ("get_warnings", None, ("warning", "weather", "alert", "storm", "heat wave", "cold wave"),
     ("সতর্ক", "আবহাওয়া", "ঝড়")),
    ("get_rotation_ranking", ["save_water"], ("irrigat", "water", "pump", "dry"), ("সেচ", "পানি", "শুকনো")),
    ("get_rotation_ranking", ["flood_safety"], ("flood",), ("বন্যা",)),
    ("get_rotation_ranking", ["soil_health"], ("legume", "soil health", "fertil"), ("ডাল", "উর্বর")),
    ("get_rotation_ranking", ["lowest_risk"], ("rotation", "safe", "risk"), ("ঘূর্ণন", "ঝুঁকি", "নিরাপদ")),
]
_CROP_WORDS = {"wheat": ("wheat", "গম"), "mustard": ("mustard", "সরিষা"),
               "lentil": ("lentil", "মসুর", "ডাল"), "potato": ("potato", "আলু"),
               "boro_rice": ("boro", "বোরো")}


def rule_route(question, district):
    """Fallback when the model cannot help: pick up to two tool calls from
    keywords. Always returns at least one call (get_advice)."""
    low = question.lower()
    calls = []
    for crop, words in _CROP_WORDS.items():
        if any(w in low or w in question for w in words):
            calls.append(("get_crop_risk", {"district": district, "crop": crop}))
            break
    for tool, prios, en, bn in _KEYWORDS:
        if calls and prios == ["lowest_risk"]:
            continue  # "is mustard risky?" is already answered by the crop's own risk
        if any(w in low for w in en) or any(w in question for w in bn):
            args = {"district": district}
            if prios:
                args["priorities"] = prios
            if (tool, args) not in calls:
                calls.append((tool, args))
    return (calls or [("get_advice", {"district": district})])[:2]


def _compact(result):
    """What the model sees of a tool result: its sentence only."""
    return json.dumps({"ok": result["ok"], "summary": result["text"]["en"]})


def run_agent(question, district, page_lang, api, today, llm=hf_chat):
    """Answer one question. `api(method, path, params, body) -> (status,
    envelope)` is how tools reach the data; `llm(messages, tools)` is the
    model (None or failing = rule router). Returns a dict, never raises."""
    lang = detect_language(question, page_lang)
    district = find_district(question, district)
    results, called, seen = [], [], set()
    model_text, llm_error, steps = None, None, 0
    messages = [
        {"role": "system", "content": SYSTEM.format(
            districts=", ".join(DISTRICTS), district=district,
            language="Bangla" if lang == "bn" else "English")},
        {"role": "user", "content": question}]

    def execute(name, args):
        key = (name, json.dumps(args, sort_keys=True))
        if key in seen:
            return next((r for r in results if (r["tool"], json.dumps(r["args"], sort_keys=True)) == key), None)
        seen.add(key)
        res = run_tool(name, args, api, today)
        results.append(res)
        called.append({"name": name, "args": args})
        return res

    if llm is not None:
        try:
            while steps < STEP_CAP:
                msg = llm(messages, TOOLS)
                steps += 1
                if not msg["tool_calls"]:
                    model_text = msg["content"] if results else None
                    break
                messages.append({"role": "assistant", "content": msg["content"] or None,
                                 "tool_calls": [{"id": c["id"], "type": "function",
                                                 "function": {"name": c["name"], "arguments": c["arguments"]}}
                                                for c in msg["tool_calls"]]})
                for c in msg["tool_calls"]:
                    try:
                        args = json.loads(c["arguments"])
                    except ValueError:
                        args = {}
                    args = args if isinstance(args, dict) else {}
                    args.setdefault("district", district)
                    res = execute(c["name"], args) or {"ok": False, "text": {"en": "Already asked."}}
                    messages.append({"role": "tool", "tool_call_id": c["id"], "content": _compact(res)})
        except Exception as exc:  # noqa: BLE001 - any model failure -> rule router
            llm_error = f"{type(exc).__name__}: {str(exc)[:120]}"
            model_text = None

    if not any(r["ok"] for r in results):
        for name, args in rule_route(question, district):
            execute(name, args)

    ok = [r for r in results if r["ok"]]
    views = [guard_view(r) for r in ok]
    warnings_only = bool(ok) and all(r["tool"] == "get_warnings" for r in ok)

    out = {}
    for ln in ("en", "bn"):  # both languages so the page switch needs no new call
        base_ln = " ".join(r["text"][ln] for r in ok) if ok else (
            results[0]["text"][ln] if results else NO_ANSWER[ln])
        out[ln] = compose_answer(ln, None, views, model_text if ln == lang else None,
                                 base_text=base_ln, disclaimer=bool(ok) and not warnings_only)
    chosen = out[lang]
    g = guard(chosen["text"], views)
    sources, seen_src = [], set()
    for r in ok:
        for s in r["sources"]:
            k = (s.get("dataset"), s.get("url") or s.get("source_url"))
            if k not in seen_src:
                seen_src.add(k)
                sources.append(s)
    return {"lang": lang, "district": district, "text": {"en": out["en"]["text"], "bn": out["bn"]["text"]},
            "narrator": chosen["narrator"], "tools_called": called, "steps_used": steps,
            "step_cap": STEP_CAP, "guard": {"numbers_checked": g["checked"],
                                            "numbers_blocked": len(g["blocked_numbers"])},
            "provenance_check": "passed" if g["passed"] else "blocked_fallback_used",
            "ok": bool(ok), "sources": sources,
            "notices": [n for r in ok for n in r["notices"]],
            "llm_used": steps > 0 and llm_error is None, "llm_error": llm_error}

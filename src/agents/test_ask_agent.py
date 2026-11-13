"""
Unit tests for src/agents/ask_agent.py and ask_tools.py (T17).
A fake API and a fake model are used, so no network and no token are needed.
Bangla strings here need native review (docs/AI_USE.md).
"""

import json

from ask_agent import STEP_CAP, find_district, rule_route, run_agent
from ask_tools import run_tool

SRC = [{"id": "imerg", "dataset": "NASA GPM IMERG V07 Final Run",
        "url": "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary"}]
ADVICE = {"data": {"district": "cumilla", "years_used": {"value": 24},
                   "options": [{"crop": "wheat", "problem_years": {"value": 0, "unit": "of 24 years"}}]},
          "narration": {"en": "Cumilla: top-ranked Wheat had problems in 0 of 24 years here.",
                        "bn": "কুমিল্লা: প্রথম পছন্দ গম, ২৪ বছরের মধ্যে ০ বছরে সমস্যা হয়েছে।"},
          "provenance": SRC, "notices": [], "errors": []}
RISK = {"data": {"crop": "mustard", "years_used": {"value": 24}},
        "narration": {"en": "Mustard in Feni: problems in 3 to 24 of 24 years.",
                      "bn": "ফেনীতে সরিষা: ২৪ বছরের ৩ থেকে ২৪ বছরে সমস্যা।"},
        "provenance": SRC, "notices": [], "errors": []}
RANK = {"data": {"ranked": [{"rotation": {"slots": [{"crop": "aman_rice"}, {"crop": "mustard"}]},
                             "problem_line": "problems in 6 of 24 years (checked: heat)",
                             "components": {"save_water": {"raw": {"value": 257.6, "unit": "mm"}}}}],
                 "metrics": {"save_water": {"metric": "irrigation need in the driest 20% of years (Kc-weighted)"}},
                 "unranked": []},
        "narration": None, "provenance": SRC, "notices": [], "errors": []}
SOIL = {"data": {"soil": {"texture": {"en": "Clay", "bn": "এঁটেল"}, "sand_pct": {"value": 23.6},
                          "silt_pct": {"value": 34.0}, "clay_pct": {"value": 42.4}},
                 "test_advice": {"en": "Test your soil.", "bn": "মাটি পরীক্ষা করান।"}},
        "narration": None, "provenance": SRC, "notices": [], "errors": []}
WARN = {"data": {"valid_from": "2026-11-14", "valid_to": "2026-11-20",
                 "warnings": [{"date": "2026-11-16", "action": {"en": "Hot day.", "bn": "গরম দিন।"}},
                              {"date": "2026-11-17", "action": {"en": "Hot day.", "bn": "গরম দিন।"}}]},
        "narration": None, "provenance": SRC, "notices": [], "errors": []}


def fake_api(overrides=None):
    table = {"/api/v1/advisory": ADVICE, "/api/v1/risk-calendar": RISK, "/api/v1/rotation/rank": RANK,
             "/api/v1/soil": SOIL, "/api/v1/warnings": WARN}
    table.update(overrides or {})

    def api(method, path, params=None, body=None):
        env = table.get(path)
        return (200, env) if env else (404, {"data": None, "errors": [{"en": "nope", "bn": "না"}]})
    return api


def scripted_llm(*steps):
    """Each step is a list of (tool, args) calls, or a string for the final text."""
    it = iter(steps)

    def llm(messages, tools):
        step = next(it)
        if isinstance(step, str):
            return {"content": step, "tool_calls": []}
        return {"content": "", "tool_calls": [
            {"id": f"c{i}", "name": n, "arguments": json.dumps(a)} for i, (n, a) in enumerate(step)]}
    return llm


def ask(q, llm=None, api=None, district="cumilla", lang=None):
    return run_agent(q, district, lang, api or fake_api(), "2026-11-14", llm=llm)


# ---- routing without a model ----
def test_no_model_uses_rule_router_and_still_answers():
    r = ask("What should I plant?")
    assert r["tools_called"][0]["name"] == "get_advice" and r["ok"] and not r["llm_used"]
    assert "0 of 24 years" in r["text"]["en"] and r["guard"]["numbers_blocked"] == 0


def test_bangla_question_gets_bangla_answer_with_bangla_digits():
    r = ask("আমার জমিতে কী লাগাবো?")
    assert r["lang"] == "bn" and r["narrator"] == "template"
    assert "২৪" in r["text"]["bn"] and "গম" in r["text"]["bn"]
    assert not any(c.isascii() and c.isalpha() for c in r["text"]["bn"])


def test_crop_question_does_not_also_run_generic_risk_ranking():
    names = [c[0] for c in rule_route("Is mustard risky?", "feni")]
    assert names == ["get_crop_risk"]


def test_rule_route_keywords():
    assert rule_route("how much irrigation?", "cumilla")[0][1]["priorities"] == ["save_water"]
    assert rule_route("সেচ কত লাগবে", "cumilla")[0][0] == "get_rotation_ranking"
    assert rule_route("my soil?", "cumilla")[0][0] == "get_soil"
    assert rule_route("weather alert", "cumilla")[0][0] == "get_warnings"
    assert rule_route("hello", "cumilla")[0][0] == "get_advice"


def test_find_district_english_and_bangla():
    assert find_district("is it ok in Sylhet?", "cumilla") == "sylhet"
    assert find_district("ফেনীতে কী চাষ করব", "cumilla") == "feni"
    assert find_district("anything", "bogus") == "cumilla"


# ---- the model's part ----
def test_model_picks_tool_and_good_sentence_is_kept():
    llm = scripted_llm([("get_crop_risk", {"district": "feni", "crop": "mustard"})],
                       "Check the sowing dates before you start.")
    r = ask("Is mustard ok in Feni?", llm=llm)
    assert r["llm_used"] and r["narrator"] == "model" and r["steps_used"] == 2
    assert "Check the sowing dates" in r["text"]["en"] and "problems in 3 to 24" in r["text"]["en"]


def test_model_invented_number_is_dropped_but_facts_stay():
    llm = scripted_llm([("get_advice", {"district": "cumilla"})], "It will fail in 12 years.")
    r = ask("What to plant?", llm=llm)
    assert r["narrator"] == "template" and "12 years" not in r["text"]["en"]
    assert "0 of 24 years" in r["text"]["en"]


def test_model_naming_another_crop_is_dropped():
    llm = scripted_llm([("get_advice", {"district": "cumilla"})], "Potato is also a good idea.")
    assert ask("What to plant?", llm=llm)["narrator"] == "template"


def test_model_forecast_word_is_dropped():
    llm = scripted_llm([("get_advice", {"district": "cumilla"})], "This forecast looks fine.")
    assert ask("What to plant?", llm=llm)["narrator"] == "template"


def test_bangla_question_with_english_model_text_gets_bangla_template():
    llm = scripted_llm([("get_advice", {"district": "cumilla"})], "Wheat looks good here.")
    r = ask("কী লাগাবো?", llm=llm)
    assert r["narrator"] == "template" and "Wheat" not in r["text"]["bn"]


def test_model_text_before_any_tool_is_ignored_and_router_used():
    r = ask("What to plant?", llm=scripted_llm("Plant rice, I am sure."))
    assert "Plant rice" not in r["text"]["en"] and r["tools_called"][0]["name"] == "get_advice"


def test_model_failure_falls_back_without_error():
    def boom(messages, tools):
        raise RuntimeError("HF_TOKEN is not set")
    r = ask("What to plant?", llm=boom)
    assert r["ok"] and not r["llm_used"] and "RuntimeError" in r["llm_error"]


def test_step_cap_is_six_and_answer_is_still_given():
    n = {"i": 0}

    def looping(messages, tools):
        n["i"] += 1
        return {"content": "", "tool_calls": [{"id": f"c{n['i']}", "name": "get_crop_risk",
                "arguments": json.dumps({"district": "feni", "crop": "mustard", "x": n["i"]})}]}
    r = ask("mustard?", llm=looping)
    assert r["steps_used"] == STEP_CAP == 6 and n["i"] == 6
    assert r["ok"] and r["narrator"] == "template"


def test_bad_tool_arguments_do_not_crash():
    llm = lambda m, t: {"content": "", "tool_calls": [{"id": "a", "name": "get_soil", "arguments": "{not json"}]} \
        if not any(x["role"] == "tool" for x in m) else {"content": "", "tool_calls": []}
    r = ask("my soil?", llm=llm)
    assert r["ok"] and "Clay" in r["text"]["en"]


def test_unknown_tool_name_is_a_failed_result_not_a_crash():
    assert run_tool("drop_tables", {"district": "cumilla"}, fake_api(), "2026-11-14")["ok"] is False


# ---- correctness guarantees ----
def test_uncited_data_is_never_shown_as_fact():
    uncited = dict(ADVICE, provenance=[])
    r = ask("What to plant?", api=fake_api({"/api/v1/advisory": uncited}))
    assert "0 of 24" not in r["text"]["en"] and r["guard"]["numbers_blocked"] == 0
    assert "could not find a checked number" in r["text"]["en"]


def test_api_failure_gives_plain_message_not_empty():
    r = ask("What to plant?", api=lambda *a: (500, {}))
    assert r["ok"] is False and r["text"]["en"].strip() and r["text"]["bn"].strip()


def test_uncovered_district_in_tool_is_reported_not_invented():
    res = run_tool("get_advice", {"district": "dhaka"}, fake_api(), "2026-11-14")
    assert res["ok"] is False and "not covered" in res["text"]["en"]


def test_rank_text_uses_only_returned_numbers():
    r = ask("rotation for saving water", api=fake_api())
    t = r["text"]["en"]
    assert "Aman rice, then Mustard" in t and "6 of 24" in t and "258 mm" in t
    assert r["guard"]["numbers_blocked"] == 0


def test_warnings_same_advice_merged_and_no_past_seasons_line():
    r = ask("any weather warning?")
    assert r["text"]["en"].startswith("2026-11-16, 2026-11-17: Hot day.")
    assert "not a forecast" not in r["text"]["en"]


def test_soil_text_cites_district_estimate():
    r = ask("soil?")
    assert "Clay (sand 23.6%, silt 34%, clay 42.4%)" in r["text"]["en"]
    assert "এঁটেল" in r["text"]["bn"] and "২৩.৬%" in r["text"]["bn"]


def test_sources_are_returned():
    r = ask("What to plant?")
    assert r["sources"] and r["sources"][0]["dataset"].startswith("NASA GPM IMERG")

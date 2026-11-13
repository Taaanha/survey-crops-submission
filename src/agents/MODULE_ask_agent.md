# ask agent (T17, POST /api/v1/ask)
Layer: 3 agents
Code: src/agents/ask_agent.py, src/agents/ask_tools.py
Purpose (2-3 sentences): Answers a free-text farmer question in English or Bangla. A free Hugging Face model (HF_TOKEN from the environment, model from HF_MODEL, default Llama-3.1-8B-Instruct) only chooses which tools to call, at most 6 model calls; the answer is the tools' own cited sentences plus at most one short model sentence that passes guard(). With no token, no network or a bad model reply, a keyword router picks the tools and the answer is the same, from the same data.
Public API (exact signatures + one-line description each):
- `run_agent(question, district, page_lang, api, today, llm=hf_chat)` : answers one question; returns text (en and bn), tools_called, steps_used, guard counts, sources; never raises, never empty.
- `rule_route(question, district)` : up to two (tool, args) calls chosen from keywords; always at least get_advice.
- `find_district(question, default)` : a district named in the question (English or Bangla), else the default.
- `hf_chat(messages, tools, model=None, token=None, timeout=25)` : one call to the Hugging Face router (requests, no extra library); raises on any failure.
- `run_tool(name, args, api, today)` : runs one of the five tools (get_advice, get_crop_risk, get_rotation_ranking, get_soil, get_warnings) through the cited API; ok=False with a plain message on any failure.
- `guard_view(result)` : the {data, sources} pair guard() checks a tool result against.
Inputs (data files / other modules) and their provenance: the app's own endpoints (/advisory, /risk-calendar, /rotation/rank, /soil, /warnings) reached through the `api` function the caller passes (app.py passes an in-process client); their provenance entries carry through to the answer.
Outputs (shape + units + provenance fields): see docs/api_contract.md, POST /api/v1/ask; `provenance` is the union of the tools' sources.
Reference tables used (data/reference/*.csv rows): none directly; the endpoints use them.
Tests (file names + what each proves): src/agents/test_ask_agent.py (routing, model sentence kept or dropped, invented number, other crop, forecast word, 6-step cap, model failure, uncited data never shown, Bangla answer); src/api/test_app.py (the real endpoint, bad requests).
Known limitations / honest caveats: Only five tools; questions outside them get the general advice answer. The model's sentence is checked for numbers, banned words and crop names, not for meaning. get_advice assumes the last crop was harvested today unless the model passes a date. Warnings are a short-range outlook (Open-Meteo, non-NASA), so their answers omit the "past seasons" line. HF free tier can be slow or rate-limited (25 s timeout, then the rule router). Not run against the live Hugging Face model in tests (no token in CI). Bangla wording needs native review.
CHAT KIT: src/agents/MODULE_ask_agent.md, src/agents/ask_agent.py, src/agents/ask_tools.py, src/agents/guard.py, src/agents/language.py, src/agents/test_ask_agent.py
Last changed: 2026-11-14 by agents-ask-t17

# provenance guard (guard())
Layer: 3 agents
Code: src/agents/guard.py
Purpose (2–3 sentences): The gate between any generated sentence and the user. `guard()` extracts every number (English and Bangla digits, commas, %) and allows it only if it appears, within rounding at the precision written, in a tool result that carries both `dataset` and `url`. Anything else is blocked. Plain Python, no AI. Never cut.
Public API (exact signatures + one-line description each):
- `find_numbers(text)` : list of {"raw", "value"} for every number in the text.
- `guard(text, tool_results)` : returns {"passed", "blocked_numbers", "checked"}; callers fall back to the template sentence when it does not pass.
Inputs (data files / other modules) and their provenance: the narrated text and the tool results (a list, or a dict keyed by tool name) the model received this turn.
Outputs (shape + units + provenance fields): the dict above; no units.
Reference tables used (data/reference/*.csv rows): none.
Tests (file names + what each proves): src/agents/test_guard.py (includes a fabricated number being blocked, Bangla digits, rounding, uncited results). src/agents/test_tool_functions.py covers the tools that feed it.
Known limitations / honest caveats: guard accepts the link under `source_url` (what `common.Provenance` writes; preferred) or the older `url`; a source with an empty link or no `dataset` is still not citable. Provenance written inside each number (`{value, unit, provenance}`, as the rotation module does) is not read by guard yet: tool wrappers must put a `source` or `sources` entry next to the numbers (T17). The Hugging Face agent loop (T17) is not built; only guard and two tools exist. app.py already runs guard() on its template narration.
CHAT KIT: src/agents/MODULE_provenance_guard.md, src/agents/guard.py, src/agents/test_guard.py, src/agents/tools.json
Last changed: 2026-10-24 by fixups-after-t2 (source_url accepted; tests for it)

# language layer (language.py)
Layer: 3 agents. Code: src/agents/language.py. Purpose: pick the answer language (question script first, then the page EN/বাংলা switch) and build the final chat answer. English: the model's sentence if it passes guard() and has no "predict/forecast", else the English template. Bangla: the Bangla template carries every fact; the model may add one linking sentence, dropped if it is not clean Bangla, is garbled, uses পূর্বাভাস/ভবিষ্যদ্বাণী, or fails guard(). It never answers in English when Bangla was asked.
Public API: `detect_language(text, page_lang=None)`, `normalise_digits(text)`, `localise_digits(text, lang)`, `template_answer(lang, facts)`, `looks_garbled_bn(text)`, `compose_answer(lang, facts, tool_results, model_text=None)` -> {text, lang, narrator, guard_passed, language_note}. Facts kinds: problem_years, irrigation_need, not_assessed.
Tests: src/agents/test_language.py (guard with Bangla digits, detection, Bangla template fallback). Voice: web/app/chat_voice.js (mic bn-BD / en-US, speaker hides if no voice; not yet wired into a chat panel).
Caveats: all Bangla text NEEDS NATIVE REVIEW. Only three fact kinds exist; T17 adds more. The HF loop is not built.
Last changed: 2026-11-14 by agents-bilingual-chat

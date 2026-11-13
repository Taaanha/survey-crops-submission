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

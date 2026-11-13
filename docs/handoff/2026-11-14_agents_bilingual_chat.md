# Handoff: bilingual chat language layer (2026-11-14)
Built: `src/agents/language.py` + `test_language.py` (23 tests, all pass with `test_guard.py`), `web/app/chat_voice.js`.
Not built: the Hugging Face loop and a chat panel (T17, `/ask` is still a mock). T17 should call `detect_language` on the question, run tools in English, then `compose_answer(lang, facts, tool_results, model_text)`.
Voice: mic language follows the page switch; speaker button hides when no voice for that language. A teammate must wire `ChatVoice` into the chat panel (web/ is theirs).
Open: Bangla wording needs native review (listed in docs/AI_USE.md).

"""
src/agents/language.py

Bangla / English layer for the chat answer. Plain Python, no AI calls.

The agent works on English tool results. The final answer is built here:
  - English: the model's sentence if it passes guard(), else the English template.
  - Bangla: the Bangla TEMPLATE (crop, risk and unit words from app strings),
    with the model allowed only for one linking sentence. If that sentence is
    garbled, not Bangla, uses a banned word, or fails guard(), it is dropped and
    the Bangla template alone is returned. It never falls back to English
    without saying so (`language_note` is set if it ever has to).

All Bangla text below NEEDS NATIVE REVIEW (listed in docs/AI_USE.md).
"""

import re

from guard import guard

_BN_DIGITS = "০১২৩৪৫৬৭৮৯"
_TO_ASCII = str.maketrans(_BN_DIGITS, "0123456789")
_TO_BANGLA = str.maketrans("0123456789", _BN_DIGITS)

_BN_LETTER = re.compile(r"[ঀ-ঃঅ-ঔক-নপ-যলশ-হ়-ৄেৈোৌ্ৎৗড়ঢ়য়ৠৡ]")
_LATIN_LETTER = re.compile(r"[A-Za-z]")

# Never in the model's own user-facing sentence (CLAUDE.md rule). The fixed
# "not a forecast" template line is exempt because it is the disclaimer.
_BANNED_BN = ("পূর্বাভাস", "ভবিষ্যদ্বাণী", "ভবিষ্যৎবাণী")
_BANNED_EN = re.compile(r"\b(predict\w*|forecast\w*)\b", re.I)


def normalise_digits(text):
    """Bangla digits -> 0-9 (guard() does this itself; exposed for callers)."""
    return text.translate(_TO_ASCII)


def localise_digits(text, lang):
    """Show digits in the language's own digits."""
    return text.translate(_TO_BANGLA) if lang == "bn" else normalise_digits(text)


def detect_language(text, page_lang=None):
    """'bn' or 'en'. The question's script wins; if it has no letters at all
    (e.g. only digits) the page's EN/বাংলা switch decides; default 'en'."""
    bn = len(_BN_LETTER.findall(text or ""))
    en = len(_LATIN_LETTER.findall(text or ""))
    if bn > en:
        return "bn"
    if en > bn:
        return "en"
    return page_lang if page_lang in ("bn", "en") else "en"


# ---------------- Bangla strings (NEEDS NATIVE REVIEW) ----------------

BN_CROPS = {
    "aman": "আমন ধান", "aman_rice": "আমন ধান", "boro": "বোরো ধান",
    "boro_rice": "বোরো ধান", "aus": "আউশ ধান", "mustard": "সরিষা",
    "lentil": "মসুর", "wheat": "গম", "jute": "পাট", "mung": "মুগ",
    "fallow": "খালি জমি", "veg": "সবজি", "potato": "আলু", "maize": "ভুট্টা",
}
EN_CROPS = {
    "aman": "Aman rice", "aman_rice": "Aman rice", "boro": "Boro rice",
    "boro_rice": "Boro rice", "aus": "Aus rice", "mustard": "Mustard",
    "lentil": "Lentil", "wheat": "Wheat", "jute": "Jute", "mung": "Mung bean",
    "fallow": "Fallow", "veg": "Vegetables", "potato": "Potato", "maize": "Maize",
}
BN_UNITS = {"mm": "মিমি", "years": "বছর", "days": "দিন"}
NOT_ASSESSED = {"en": "not assessed", "bn": "মূল্যায়ন করা হয়নি"}
PAST_NOT_FORECAST = {
    "en": "This is what past seasons show, not a forecast.",
    "bn": "এটি গত মৌসুমগুলোর তথ্য, ভবিষ্যতের পূর্বাভাস নয়।",
}
NO_ANSWER = {
    "en": "I could not find a checked number for that question.",
    "bn": "এই প্রশ্নের জন্য যাচাই করা কোনো সংখ্যা পাইনি।",
}

# kind -> {lang: format string}. Fields: crop (key), k, n, mm.
TEMPLATES = {
    "problem_years": {
        "en": "{crop} had problems in {k} of {n} years here.",
        "bn": "{crop} বুনলে এখানে {n} বছরের {k} বছরে সমস্যা হয়েছে।",
    },
    "irrigation_need": {
        "en": "{crop} needs about {mm} mm of irrigation here.",
        "bn": "{crop} চাষে এখানে প্রায় {mm} মিমি সেচ লাগে।",
    },
    "not_assessed": {
        "en": "{crop}: not assessed.",
        "bn": "{crop}: মূল্যায়ন করা হয়নি।",
    },
}


def template_answer(lang, facts):
    """Deterministic answer from a facts dict, e.g.
    {"kind": "problem_years", "crop": "mustard", "k": 3, "n": 25}.
    Always in `lang`; digits in that language's digits. Unknown kind or
    missing fields give the NO_ANSWER line in the same language."""
    lang = "bn" if lang == "bn" else "en"
    tpl = TEMPLATES.get((facts or {}).get("kind"))
    if tpl is None:
        return NO_ANSWER[lang]
    crops = BN_CROPS if lang == "bn" else EN_CROPS
    try:
        text = tpl[lang].format(
            crop=crops.get(facts.get("crop"), facts.get("crop_label") or ""),
            k=facts.get("k", ""), n=facts.get("n", ""), mm=facts.get("mm", ""))
    except (KeyError, IndexError):
        return NO_ANSWER[lang]
    if "{" in text or "  " in text.strip():
        return NO_ANSWER[lang]
    return localise_digits(text, lang)


def looks_garbled_bn(text):
    """True if a model sentence is not usable Bangla: too short/long, mostly
    non-Bangla letters, replacement characters, or a repeated-word loop."""
    t = (text or "").strip()
    if not 8 <= len(t) <= 300 or "�" in t:
        return True
    bn = len(_BN_LETTER.findall(t))
    latin = len(_LATIN_LETTER.findall(t))
    if bn < 6 or bn < 4 * latin:
        return True
    words = t.split()
    return any(words[i] == words[i + 1] == words[i + 2]
               for i in range(len(words) - 2))


def _bad_wording(text, lang):
    if lang == "bn":
        return any(w in text for w in _BANNED_BN)
    return bool(_BANNED_EN.search(text))


def compose_answer(lang, facts, tool_results, model_text=None):
    """Final user-facing answer in `lang`.

    Returns {"text", "lang", "narrator", "guard_passed", "language_note"}.
    narrator is "model" only when the model's sentence is used."""
    lang = "bn" if lang == "bn" else "en"
    base = template_answer(lang, facts)
    base_guard = guard(base, tool_results)
    if not base_guard["passed"]:
        # The template itself quotes a number the tools never returned: say so.
        base = NO_ANSWER[lang]

    t = (model_text or "").strip()
    model_ok = False
    if t:
        in_lang = (not looks_garbled_bn(t)) if lang == "bn" else (
            detect_language(t) == "en")
        model_ok = (in_lang and not _bad_wording(t, lang)
                    and guard(t, tool_results)["passed"])

    if lang == "en":
        # English: the model's sentence replaces the template when it passes.
        body = t if model_ok else base
    else:
        # Bangla: the template carries the facts; the model only adds a
        # linking sentence. A failed sentence is dropped, never translated.
        body = base + (" " + t if model_ok else "")
    text = body + " " + PAST_NOT_FORECAST[lang]
    return {"text": localise_digits(text, lang), "lang": lang,
            "narrator": "model" if model_ok else "template",
            "guard_passed": True, "language_note": None}

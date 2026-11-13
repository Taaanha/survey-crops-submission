"""
Unit tests for src/agents/language.py (and guard() with Bangla digits).
Bangla strings here need native review (docs/AI_USE.md).
"""

from guard import guard
from language import (compose_answer, detect_language, localise_digits,
                      looks_garbled_bn, normalise_digits, template_answer,
                      NO_ANSWER, PAST_NOT_FORECAST)

CITED = {
    "problem_years": 3, "n_years": 25, "irrigation_mm": 187.6,
    "source": {"dataset": "NASA GPM IMERG V07 Final Run",
               "source_url": "https://gpm.nasa.gov/"},
}
FACTS = {"kind": "problem_years", "crop": "mustard", "k": 3, "n": 25}


# ---- guard() with Bangla digits ----
def test_guard_accepts_bangla_digits_that_match():
    assert guard("২৫ বছরের ৩ বছরে সমস্যা", [CITED])["passed"] is True


def test_guard_blocks_bangla_digit_not_in_tool_result():
    r = guard("২৫ বছরের ৮ বছরে সমস্যা", [CITED])
    assert r["passed"] is False and r["blocked_numbers"] == ["৮"]


def test_guard_bangla_decimal_and_uncited():
    assert guard("প্রায় ১৮৭.৬ মিমি", [CITED])["passed"] is True
    assert guard("৩ বছর", [{"problem_years": 3}])["passed"] is False


def test_digit_helpers():
    assert normalise_digits("১২৩.৪৫") == "123.45"
    assert localise_digits("3 of 25", "bn") == "৩ of ২৫"
    assert localise_digits("৩ বছর", "en") == "3 বছর"


# ---- language detection ----
def test_detect_by_script():
    assert detect_language("আমার জমিতে এবার কী লাগাবো?") == "bn"
    assert detect_language("What should I plant this year?") == "en"


def test_detect_question_beats_page_switch():
    assert detect_language("সরিষা কেমন?", page_lang="en") == "bn"
    assert detect_language("Is mustard ok?", page_lang="bn") == "en"


def test_detect_falls_back_to_page_switch():
    assert detect_language("2024", page_lang="bn") == "bn"
    assert detect_language("২৫", page_lang="en") == "en"
    assert detect_language("") == "en"


# ---- templates ----
def test_bangla_template_has_bangla_crop_and_digits():
    t = template_answer("bn", FACTS)
    assert t == "সরিষা বুনলে এখানে ২৫ বছরের ৩ বছরে সমস্যা হয়েছে।"


def test_english_template_uses_ascii_digits():
    assert template_answer("en", FACTS) == "Mustard had problems in 3 of 25 years here."


def test_unknown_kind_stays_in_language():
    assert template_answer("bn", {"kind": "zzz"}) == NO_ANSWER["bn"]
    assert template_answer("bn", {"kind": "problem_years", "crop": "mustard"}) == NO_ANSWER["bn"]


def test_not_assessed_is_words_not_zero():
    t = template_answer("bn", {"kind": "not_assessed", "crop": "jute"})
    assert "মূল্যায়ন করা হয়নি" in t and "০" not in t


# ---- garbled detection ----
def test_garbled_detection():
    assert looks_garbled_bn("") is True
    assert looks_garbled_bn("the answer is here for you") is True
    assert looks_garbled_bn("সমস্যা সমস্যা সমস্যা সমস্যা আছে") is True
    assert looks_garbled_bn("এই এলাকায় ভাল বৃষ্টি� হয়েছে") is True
    assert looks_garbled_bn("এই এলাকায় গত মৌসুমে বৃষ্টি ভালো ছিল।") is False


# ---- compose_answer / Bangla fallback ----
def test_bangla_fallback_is_bangla_template_when_model_is_english():
    r = compose_answer("bn", FACTS, [CITED], model_text="Mustard is fine, 3 of 25.")
    assert r["narrator"] == "template"
    assert "সরিষা বুনলে" in r["text"] and PAST_NOT_FORECAST["bn"] in r["text"]
    assert not any(c.isascii() and c.isalpha() for c in r["text"])


def test_bangla_fallback_when_model_fails_guard():
    r = compose_answer("bn", FACTS, [CITED],
                       model_text="এই এলাকায় ৯৯ বছরে সমস্যা হয়েছে বলে দেখা গেছে।")
    assert r["narrator"] == "template" and "৯৯" not in r["text"]


def test_bangla_fallback_when_model_garbled():
    r = compose_answer("bn", FACTS, [CITED], model_text="সমস্যা সমস্যা সমস্যা সমস্যা সমস্যা")
    assert r["narrator"] == "template"


def test_bangla_model_linking_sentence_is_kept_when_good():
    link = "এই তথ্য নাসার স্যাটেলাইট থেকে এসেছে।"
    r = compose_answer("bn", FACTS, [CITED], model_text=link)
    assert r["narrator"] == "model" and link in r["text"]
    assert r["text"].startswith("সরিষা বুনলে")


def test_bangla_model_banned_word_is_dropped():
    r = compose_answer("bn", FACTS, [CITED], model_text="এই বছর সরিষার পূর্বাভাস ভালো।")
    assert r["narrator"] == "template"


def test_bangla_output_digits_are_bangla():
    r = compose_answer("bn", FACTS, [CITED])
    assert "২৫" in r["text"] and "25" not in r["text"]


def test_english_model_sentence_used_when_it_passes():
    r = compose_answer("en", FACTS, [CITED],
                       model_text="Mustard had trouble in 3 of 25 past seasons.")
    assert r["narrator"] == "model" and "25" in r["text"]


def test_english_falls_back_to_template_on_invented_number():
    r = compose_answer("en", FACTS, [CITED], model_text="Mustard failed in 12 of 25 years.")
    assert r["narrator"] == "template" and "12" not in r["text"]


def test_english_model_cannot_say_forecast():
    r = compose_answer("en", FACTS, [CITED], model_text="This forecast says 3 of 25 years.")
    assert r["narrator"] == "template"


def test_template_with_uncited_numbers_gives_no_answer_line_in_language():
    r = compose_answer("bn", FACTS, [{"problem_years": 3}])
    assert NO_ANSWER["bn"] in r["text"]

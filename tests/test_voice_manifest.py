"""The voice lines in web/pages/voice.js and web/audio/narration_manifest.json must match,
and no line may use the words the app never says to a farmer."""
import json
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


def _page_lines():
    src = (WEB / "pages" / "voice.js").read_text(encoding="utf-8")
    return json.loads(re.search(r"var PV = (\{.*?\n\});", src, re.S).group(1))


def _manifest():
    return json.loads((WEB / "audio" / "narration_manifest.json").read_text(encoding="utf-8"))


def test_every_page_line_is_in_the_manifest_with_the_same_text():
    man = {m["id"]: m for m in _manifest()}
    for key, line in _page_lines().items():
        assert key in man, key
        assert man[key]["en"] == line["en"] and man[key]["bn"] == line["bn"], key


def test_manifest_ids_are_unique_and_have_both_languages():
    ids = [m["id"] for m in _manifest()]
    assert len(ids) == len(set(ids))
    for m in _manifest():
        assert m["en"].strip() and m["bn"].strip(), m["id"]


def test_no_banned_words_except_the_not_a_forecast_disclaimer():
    for m in _manifest():
        text = m["en"].replace("not a forecast", "")
        assert not re.search(r"predict|forecast", text, re.I), m["id"]

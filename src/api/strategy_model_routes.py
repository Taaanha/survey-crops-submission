"""Two read-only endpoints (proposed in docs/contract_change_proposals.md sections 10 and 13).

  GET /api/v1/rotation/strategies?district=&current=   the W4 strategy cards
  GET /api/v1/models                                    the W3 model metrics and model cards

They only read Layer 1 (strategies) and the files the W3 build wrote; nothing is computed here and
nothing is invented. register(app, envelope, ApiError, provenance_of) is called once from app.py."""

import functools
import glob
import json
import os

from fastapi.responses import JSONResponse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
METRICS_PATH = os.path.join(ROOT, "docs", "results", "w3_metrics.json")
CARDS_GLOB = os.path.join(ROOT, "src", "ml", "si_models", "cards", "*.md")
LIVE = ("cumilla", "feni", "brahmanbaria", "noakhali", "sylhet")


@functools.lru_cache(maxsize=1)
def load_models():
    """W3 metrics JSON plus the markdown model cards, read once."""
    with open(METRICS_PATH, encoding="utf-8") as f:
        metrics = json.load(f)
    cards = {}
    for path in sorted(glob.glob(CARDS_GLOB)):
        with open(path, encoding="utf-8") as f:
            cards[os.path.splitext(os.path.basename(path))[0]] = f.read()
    return metrics, cards


def event_sources(metrics):
    """Unique cited sources of the known events used to score the models."""
    out, seen = [], set()
    for e in metrics.get("stressed_seasons", {}).get("events_used", []):
        url = e.get("source_url")
        if url and url not in seen:
            seen.add(url)
            out.append({"id": f"w{len(out) + 1}", "dataset": e.get("source_title", ""), "url": url,
                        "source_url": url})
    return out


def register(app, envelope, ApiError, provenance_of):
    def respond(endpoint, request, build):
        try:
            data, notices, provenance = build()
            return JSONResponse(envelope(endpoint, request, data, None, notices, provenance=provenance))
        except ApiError as err:
            body = envelope(endpoint, request, None,
                            errors=[{"code": err.code, "en": err.en, "bn": err.bn}], provenance=[])
            return JSONResponse(body, status_code=err.status)
        except Exception as exc:  # noqa: BLE001 - the contract forbids an empty body
            err = ApiError("INTERNAL", f"Internal error: {type(exc).__name__}")
            return JSONResponse(envelope(endpoint, request, None, provenance=[], errors=[
                {"code": err.code, "en": err.en, "bn": err.bn}]), status_code=500)

    @app.get("/api/v1/rotation/strategies")
    def rotation_strategies(district: str = None, current: str = None):
        endpoint = "/api/v1/rotation/strategies"
        request = {"district": district, "current": current}

        def build():
            if not district:
                raise ApiError("BAD_PARAMETER", "Missing parameter: district.", "district")
            if district.lower() not in LIVE:
                raise ApiError("DISTRICT_NOT_COVERED",
                               "Survey Crops covers Cumilla, Feni, Brahmanbaria, Noakhali and "
                               "Sylhet for now.")
            if not current:
                raise ApiError("BAD_PARAMETER", "Missing parameter: current.", "current")
            from strategies import build_strategies  # Layer 1, no AI
            try:
                data = build_strategies(district.lower(), current)
            except ValueError as err:
                raise ApiError("BAD_PARAMETER", f"Bad parameter: {err}", "current") from err
            notices = [{"level": "info",
                        "en": "A record of past seasons (2001-2024) for the area around your field, "
                              "not a forecast. What could not be assessed is shown as a gap, never 0.",
                        "bn": "অতীত মৌসুমের (২০০১-২০২৪) রেকর্ড, আপনার জমির আশেপাশের এলাকার জন্য; "
                              "পূর্বাভাস নয়। যা মূল্যায়ন করা যায়নি তা ফাঁক হিসেবে দেখানো হয়েছে, কখনও ০ নয়।"}]
            return data, notices, provenance_of(data)
        return respond(endpoint, request, build)

    @app.get("/api/v1/models")
    def models():
        endpoint = "/api/v1/models"

        def build():
            metrics, cards = load_models()
            data = {"metrics": metrics, "cards": cards,
                    "note": "Metrics are held-out (leave-one-year-out) and come from "
                            "docs/results/w3_metrics.json, written by scripts/build_w3_models.py. "
                            "Shown exactly as built; nothing is rounded or edited here."}
            notices = [{"level": "caution",
                        "en": metrics.get("note", "Small sample: intervals are wide."),
                        "bn": "ছোট নমুনা: অনিশ্চয়তার পরিসর বড়। স্থানীয়ভাবে যাচাই দরকার।"}]
            return data, notices, event_sources(metrics)
        return respond(endpoint, {}, build)

"""
src/api/price_block.py

The additive `market_price` field on each /api/v1/advisory option. A cited price (never income per hectare)
with its type, month, market and source mode; a crop with no cited price is "not_assessed", never 0.
Pure builder: app.py passes `ref_ids_for_items`, so nothing is imported from app.py.
"""

import functools

from strategies import facts

LABEL = {"en": "a price, not income per hectare",
         "bn": "এটি একটি দাম, হেক্টর প্রতি আয় নয়"}
NOT_ASSESSED = {"en": "Price: not assessed (no cited price for this crop).",
                "bn": "দাম: মূল্যায়ন হয়নি (এই ফসলের সূত্রসহ দাম নেই)।"}


@functools.lru_cache(maxsize=1)
def _reference():
    return facts.load_facts_reference()


def build_market_price(crop, ref_ids_for_items):
    p = facts.price(crop, _reference())
    if p["status"] != "assessed":
        return {"status": "not_assessed", "reason": p["reason"], "text": NOT_ASSESSED}
    src = ref_ids_for_items([p["item"]])
    m = p["measure"]
    return {"status": "assessed",
            "price": {"value": m["value"], "unit": m["unit"], "src": src},
            "price_type": p["price_type"], "variant": p["variant"], "as_of": p["as_of"],
            "market": p["market"], "source_mode": p["source_mode"], "label": LABEL,
            "past_range": p["past_range"], "caveat": p["caveat"]}

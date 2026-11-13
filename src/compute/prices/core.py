"""
src/compute/prices/core.py

Describes a cited market price: BDT/kg, price type (retail / wholesale / farmgate), the month it was
reported, the market (or "not stated in the source"), and where it came from. Layer 1, no AI, no network.

Today every price is a saved fixture (rows of data/reference/prices.csv, dates in price_meta.csv), so
`source_mode` is always "fixture". No free, permitted live source has been approved (see
docs/PROJECT_STATE.md Open questions). A price is never an income figure and is never extended or
estimated: a crop with no cited price is "not assessed".
"""

import os

import pandas as pd

META_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "price_meta.csv")
SOURCE_MODE = "fixture"
TARGET_UNIT = "BDT/kg"
# exact definitions only (1 quintal = 100 kg, 1 tonne = 1000 kg)
UNIT_FACTORS = {"bdt/kg": 1.0, "bdt/100kg": 0.01, "bdt/quintal": 0.01, "bdt/tonne": 0.001, "bdt/t": 0.001}
PRICE_TYPES = ("farmgate", "wholesale", "retail")
NOT_STATED = "not stated in the source"
PAST_RANGE_GAP = ("no dated price history in the repo, so the lowest and highest price of the last 12 months "
                  "cannot be shown")
CAVEAT = ("Prices come from different dates and products (for example dal versus grain); "
          "compare across crops with care. A price is not income per hectare.")


def to_bdt_per_kg(value, unit):
    """The value in BDT/kg, or None when the unit is not one we can convert exactly."""
    factor = UNIT_FACTORS.get(str(unit).strip().lower().replace(" ", ""))
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if factor is None or number != number else number * factor


def price_type(item):
    """retail / wholesale / farmgate from the item name (crop.price.<type>[_variant]), else None."""
    tail = str(item).split(".price.", 1)[-1]
    for kind in PRICE_TYPES:
        if tail.startswith(kind) or f"_{kind}" in tail:
            # 'farmgate_or_wholesale' does not say which one the number is
            return None if "_or_" in tail else kind
    return None


def price_variant(item):
    """'high_quality', 'coarse', ... when the item name carries one, else None."""
    tail = str(item).split(".price.", 1)[-1]
    for kind in PRICE_TYPES:
        if tail.startswith(kind + "_") and "_or_" not in tail:
            return tail[len(kind) + 1:]
    return None


def load_meta(path=META_PATH):
    """{item: {"as_of": "YYYY-MM", "market": str}} from price_meta.csv (empty dict if the file is missing)."""
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    return {r["item"]: {"as_of": r["as_of"], "market": r["market"] or NOT_STATED} for _, r in df.iterrows()}


def describe(item, meta=None):
    """Everything about a price row except the number: type, variant, month, market, source mode."""
    meta = load_meta() if meta is None else meta
    m = meta.get(item, {})
    return {"price_type": price_type(item) or NOT_STATED, "variant": price_variant(item),
            "as_of": m.get("as_of"), "market": m.get("market", NOT_STATED),
            "source_mode": SOURCE_MODE,
            "past_range": {"status": "gap", "reason": PAST_RANGE_GAP},
            "caveat": CAVEAT}

# prices (api-live-prices)
Layer: 1 compute (used by src/compute/strategies/facts.py `price()` and by src/api/price_block.py for `/api/v1/advisory`)
Code: src/compute/prices/core.py
Purpose (2–3 sentences): Describes a cited market price: BDT/kg, price type (retail / wholesale / farmgate), the month it was reported, the market (or "not stated in the source"), and that it is a saved copy. Every price today is a fixture (rows of `data/reference/prices.csv`, months in `price_meta.csv`); no free, permitted live source has been approved. A price is never income per hectare and is never extended or estimated; a crop with no cited price is "not assessed".
Public API (exact signatures + one-line description each):
- `to_bdt_per_kg(value, unit)` : the value in BDT/kg for BDT/kg, BDT/100kg, BDT/quintal, BDT/tonne (exact definitions only), else None.
- `price_type(item)` : retail / wholesale / farmgate from the item name, or None (e.g. "farmgate_or_wholesale" does not say which).
- `price_variant(item)` : `high_quality`, `coarse`, ... when the item name carries one, else None.
- `load_meta(path=META_PATH)` : `{item: {"as_of": "YYYY-MM", "market": str}}` from price_meta.csv.
- `describe(item, meta=None)` : price type, variant, month, market, `source_mode` "fixture", `past_range` (a gap with the reason) and a caveat.
Inputs (data files / other modules) and their provenance: `data/reference/prices.csv` (strict loader, via strategies.facts); `src/compute/prices/price_meta.csv` (month and market per item, taken from each row's own source title or note).
Outputs (shape + units + provenance fields): see `market_price` in `docs/contract_change_proposals.md` section 17. The number's provenance is the prices.csv row (dataset, source_url, retrieved, file:line).
Reference tables used (data/reference/*.csv rows): `prices.csv` (DAM figures reported by Business Insider Bangladesh, Mar 2024; DAM wheat, Feb 2026, reported by USDA FAS GAIN; Dhaka aman coarse rice, Sep 2026, FPMU). GAP rows (no source) are skipped by the loader and stay "not assessed".
Tests (file names + what each proves): tests/prices/test_prices.py (unit conversion, unconvertible unit is skipped not guessed, price type, every priced row has a month, wheat dated and cited, no price stays a gap, card month text); src/api/test_prices_route.py (strategies and advisory answers carry type / month / market / fixture mode, unpriced crops are gaps, provenance resolves, no banned words).
Known limitations / honest caveats: (1) Not live: there is no fetch, so there is no live / cache path and no 12-month range ("past prices: not assessed"). (2) Months only; the market is "not stated" except Dhaka for the rice row. (3) The month is keyed by item name in price_meta.csv: if a price row's value is replaced, its month must be updated too. (4) Prices are from different dates and products (dal versus grain, 2024 versus 2026); the strategies "income" priority compares them, so treat that comparison with care. (5) The rotation ranking (`/rotation/rank`) has no income component and was not changed.
CHAT KIT: src/compute/prices/core.py, src/compute/prices/price_meta.csv, src/compute/strategies/facts.py, src/api/price_block.py, data/reference/prices.csv
Last changed: 2026-11-13 by api-live-prices

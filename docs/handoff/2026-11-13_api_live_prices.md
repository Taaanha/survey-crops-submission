# Handoff 13 Nov 2026: api-live-prices (prices as fixtures)

## What was asked
Show the latest cited market price per crop, never predicted. After the research step no free, permitted, working live source existed for our crops, so Tanha chose "prices as fixtures": dated saved prices, honestly labelled, no live fetch.

## What changed
- `data/reference/prices.csv` (teammate-owned): 4 rows appended (wheat wholesale 40.32 and retail 43.85 BDT/kg, DAM Feb 2026 via USDA FAS GAIN; Dhaka aman coarse rice retail 51 and wholesale 43, FPMU Sep 2026). Nothing changed or deleted.
- New `src/compute/prices/` (core.py, price_meta.csv with the month and market of each row, MODULE.md) and `tests/prices/test_prices.py`.
- `src/compute/strategies/facts.py` `price()` now converts units exactly (or skips) and adds price type, month, market, `source_mode` "fixture", `past_range` gap; `cards.py` names the type and month.
- `src/api/price_block.py` + `app.py`: `market_price` on each `/api/v1/advisory` option (additive); `src/api/test_prices_route.py`.
- Web: `web/pages/price.js` (shared), `web/adapters/advisory.js`, `web/adapters/strategies.js`, `web/modes.html` (script tag + the rotation card), `web/pages/data.js` (strategies card).
- Docs: contract_change_proposals.md section 17, PROJECT_STATE.md Open questions, AI_USE.md.

## Result
Wheat 40.32 BDT/kg (wholesale, reported Feb 2026), lentil 125.35 (wholesale high-quality dal, Mar 2024), potato 23.30 (Mar 2024) each with a Source button. Mustard and boro rice: "not assessed". "Past prices (12 months)": not assessed for every crop.

## Not done (and why)
- No live fetch, cache or `safe_fetch` path, no WFP key: no approved source (Open questions).
- `/rotation/rank` was not changed: it has no income component and adding one would change the ranking.
- No `web/mock/live` sample (the mock files were not touched).

## Caveats
Months only; the market is unknown for most rows; prices of different dates and products are compared by the strategies "income" priority; the browser pane could not open the local site, so the web part was checked by running real API answers through the adapters and `csPriceHtml` in Node.

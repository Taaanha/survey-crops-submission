# strategies (W4 Rotation Strategy Exploration, Layer 1)

Code: src/compute/strategies/core.py, src/compute/strategies/indicators.py, src/compute/strategies/facts.py, src/compute/strategies/cards.py, src/compute/strategies/matrix.py

The farmer's CURRENT rotation is the required baseline; every other feasible
candidate from the rotation engine is an alternative. Each strategy carries
the W4 indicators, a deterministic five-heading card (Why suggested, Evidence,
Benefits, Information gaps, Risks to check locally) and a place in the
priority matrix (water, soil health, low risk, income). No AI; a record of
past seasons, never a prediction. What cannot be assessed is a gap with its
reason, never 0.

## Files
- `core.py` — `build_strategies(district, current)`: assembles baseline +
  alternatives, `crops_not_offered` (with reasons, including GAP rows in
  `new_crop_params.csv`), the matrix and the assumptions list.
- `indicators.py` — bare-field days (from OUR sowing-to-harvest windows, not
  satellite-observed), problem-year count with a percentile bootstrap range
  (same settings as W3's `src/ml/si_models/validation.py`, reimplemented with
  numpy only so Layer 1 never imports Layer 2), heavy-rain days (cited BMD row
  via W2's loader, ETCCDI R20mm fallback, `which` says which), NASADEM slope
  tercile class (relative ranking only; breakpoints are our choice; reason from
  `docs/w1b_data_status.csv`), erosion exposure = bare x heavy-rain x slope class
  (relative index).
- `facts.py` — per-crop cited facts: FAO-56 Table 22 root depth and residue /
  price rows through the strict loader; crop family, pest-cycle rule and forage
  read RAW with a source-URL check because the strict loader skips every row in
  `crop_family.csv` and `forage.csv` (unit/value format) — the provenance note
  says so (same pattern as W2's `heavy_rain.py`). Pest-cycle break is labelled
  "needs local review". Prices are market prices (BDT/kg), never income per
  hectare (no yield model).
- `cards.py` — the five-heading card, filled from templates; the words
  "predict" and "forecast" never appear (tested).
- `matrix.py` — the priority matrix with T2's honesty rules: min-max
  normalisation, gaps never scored as zero, no_contrast flagged, ties listed.

- organic matter indicator = cited residue rows + the SoilGrids pH / organic-carbon baseline at the district point (`attach_soil`, from `soil_chem`), labelled "SoilGrids model estimate, 250 m, not a soil test; confirm with a local soil test"; a masked point is a named gap. Not used in the priority matrix.

## Tests
`tests/strategies/` (56 tests): hand-counted fixtures for bare days (130 of
365), bootstrap edge cases, slope terciles (9 synthetic districts), the erosion
product, fact provenance on real reference rows, matrix property tests
extending `tests/priorities`, card wording, and the real-data acceptance run
on Cumilla (baseline always shown; >= 3 strategies; gaps only for unsourced
values; no predict/forecast anywhere in the JSON).

## API
Not wired into `app.py` yet; the endpoint shape is to be proposed in
`docs/contract_change_proposals.md` (shared-file rule).

# ENSO lens (El Niño years)
Layer: 1 compute (the API endpoint is still a mock)
Code: src/compute/enso.py
Purpose (2–3 sentences): Labels years el_nino / la_nina / neutral from NOAA CPC's ONI series using the standard CPC rule (at least 5 consecutive overlapping seasons at +0.5 or -0.5). It is meant for comparing El Niño years with all years, always labelled "context, not forecast", with n shown.
Public API (exact signatures + one-line description each):
- `label_enso_years(oni_df, warm_threshold=WARM_THRESHOLD, cold_threshold=COLD_THRESHOLD, min_seasons=MIN_SEASONS)` : label per calendar year.
- `classify_oni(anom, warm_threshold=WARM_THRESHOLD, strong_threshold=STRONG_WARM_THRESHOLD, cold_threshold=COLD_THRESHOLD)` : label for one anomaly value.
- `season_enso_labels(oni_df, season='ASO')` : simpler label from one 3-month season, for the rabi crop.
Inputs (data files / other modules) and their provenance: `data/reference/oni.csv` (NOAA CPC Oceanic Niño Index, fetched by scripts/fetch_oni.py).
Outputs (shape + units + provenance fields): pandas Series or strings of labels; provenance is the NOAA CPC table cited in oni.csv.
Reference tables used (data/reference/*.csv rows): oni.csv.
Tests (file names + what each proves): src/compute/test_enso.py (episode rule on synthetic ONI and edge cases).
Known limitations / honest caveats: `/api/v1/enso-lens` still serves web/mock/enso_lens.json with `is_mock: true`. The El Niño-years test needs POWER 1981-2000, which is not added yet. The group comparison itself is `hindcast.compare_groups`.
CHAT KIT: src/compute/MODULE_enso.md, src/compute/enso.py, src/compute/test_enso.py, src/compute/hindcast.py (compare_groups only), web/mock/enso_lens.json
Last changed: 2026-10-24 by session A (partition)

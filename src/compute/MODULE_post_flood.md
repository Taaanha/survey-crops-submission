# post-flood readiness (SMAP recovery + OPERA recession)
Layer: 1 compute
Code: src/compute/post_flood.py, src/compute/flood_area.py
Purpose (2–3 sentences): After a flood, when is a plot ready to sow again? Two NASA signals: SMAP root-zone moisture returning to a normal level (a calendar-window percentile of every other year, held for several days), and OPERA DSWx-S1 radar water maps showing the flood receding. The earliest sowing date feeds back into the risk calendar (the cascade). Today the radar signal is a ~20 km box, not per pixel (tasks T3/T5).
Public API (exact signatures + one-line description each):
- `smap_days_to_normal(smap_df, flood_date, pct=80, window_days=15, hold_days=7, value_col='sm_rootzone')` : days until soil moisture is normal.
- `smap_recovery_curve(smap_df, start, end, pct=80, window_days=15, value_col='sm_rootzone')` : the curve behind it.
- `water_persistence(dswx_df, water_threshold=0.1, valid_threshold=0.5, date_col='date', water_col='water_fraction', valid_col='valid_fraction')` : how long water stayed.
- `flood_recession(dswx_area_df, fraction_of_peak=0.1, hold_scenes=2, valid_threshold=0.5, baseline=0.0, value_col='flood_km2', date_col='date', valid_col='valid_fraction')` : recession from the peak flood area.
- `earliest_sowing_date(days_to_normal_result, water_persistence_result)` : combines the signals.
- `crops_still_possible(earliest_date, district, crops=None, path=CROP_CALENDAR_PATH)` : crops whose sowing window is still open.
- `combine_scenes(arrays)` : merge DSWx-S1 scenes on one grid (flood_area.py).
- `permanent_water_mask(reference_arrays, min_share=0.5, min_valid=3)` : water that is normally there (flood_area.py).
- `flood_stats(wtr, permanent, known, pixel_km2)` : flood area numbers (flood_area.py).
- `flood_mask(wtr, permanent, known)` : boolean flood-water mask (flood_area.py).
Inputs (data files / other modules) and their provenance: `data/processed/smap_<district>_2015_2026.csv` (NASA SMAP L4), `dswx_<district>.csv` and `dswx_area_<district>.csv` (OPERA DSWx-S1, built by scripts/fetch_dswx.py), `data/reference/crop_calendar.csv`.
Outputs (shape + units + provenance fields): dicts with dates, days and the thresholds used; scene dates come from the CSVs. Provenance is attached by app.py (`smap`, OPERA entries).
Reference tables used (data/reference/*.csv rows): crop_calendar.csv (sowing windows).
Tests (file names + what each proves): src/compute/test_post_flood.py, src/compute/test_flood_area.py. Results: docs/results/post_flood.md and the drying-curve CSVs.
Known limitations / honest caveats: OPERA DSWx-S1 over Feni/Cumilla exists only from 21 Aug 2024. SMAP is 9-36 km. The 70th / 90th percentile sensitivity is reported in docs/results/post_flood.md.
CHAT KIT: src/compute/MODULE_post_flood.md, src/compute/post_flood.py, src/compute/test_post_flood.py, docs/results/post_flood.md, web/mock/post_flood.json
Last changed: 2026-10-24 by session A (partition)

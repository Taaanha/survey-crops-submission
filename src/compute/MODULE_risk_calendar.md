# risk calendar and ranking
Layer: 1 compute
Code: src/compute/risk_calendar.py
Purpose (2–3 sentences): For each district x crop x sowing date, counts in how many of the 2001-2024 seasons NASA data showed a problem (a cited hazard threshold crossed at a sensitive stage, or waterlogging), plus water-stress days and net irrigation. It ranks sowing options by the average and by the worst 20% of years, and builds the "what can still be sown" options after a harvest or a flood. A record of past seasons, not a forecast.
Public API (exact signatures + one-line description each):
- `build_crop_specs(ref, crops=CROPS)` : cited spec per crop (window, stage days, hazards, missing items).
- `build_crop_spec(ref, crop)` : the same for one crop.
- `prepare_weather(district, metadata=None)` : load_weather plus FAO-56 ET0.
- `evaluate_season(spec, targets, weather, sow, params=DEFAULT_PARAMS)` : stage days and hazard-day counts for one sowing date and season.
- `summarise(rows, spec, params=DEFAULT_PARAMS, water=True)` : one calendar row (problem years, irrigation mean and worst 20%).
- `crop_calendar(district, spec, weather, seasons=SEASONS, params=DEFAULT_PARAMS, water=None, sow_dates=None, sensitivity=True)` : rows for one district and crop.
- `build_calendar(districts, specs, ref, seasons=SEASONS, params=DEFAULT_PARAMS, with_water=True, weather_by_district=None)` : all districts.
- `season_row(spec, targets, weather, sow, water=None, params=DEFAULT_PARAMS)` : the per-season row for one sowing date (stage days, hazard days, water columns); used by the rotation engine.
- `rotation_options(district, previous_crop_harvest_date, earliest_ready_date=None, turnaround_days=TURNAROUND_DAYS, planned_next_crop=None, calendar=None, ref=None)` : ranked options after a harvest or a flood.
- `worst_mean(values, fraction=WORST_FRACTION, highest_is_worst=True)` : mean of the worst 20%.
- `threshold_value(hazard, end)` : the onset or severe end of a cited range.
- `load_reference_for_calendar()` : strict reference loader for the calendar.
Inputs (data files / other modules) and their provenance: `load_weather()` (IMERG + POWER); `data/processed/kc_table.csv`, `district_metadata.csv`; the reference CSVs below. Prebuilt table: `data/processed/risk_calendar.csv` (built by scripts/build_risk_calendar.py).
Outputs (shape + units + provenance fields): DataFrame or dict rows with problem_years, n_years, irrigation_mm_mean / worst20, irrigation_events, stress days. Each window, stage and threshold is cited through the spec.
Reference tables used (data/reference/*.csv rows): crop_calendar.csv, crop_thresholds.csv, crop_params.csv, paddy_params.csv, crop_area_by_district.csv, soil_params.csv.
Tests (file names + what each proves): src/compute/test_risk_calendar.py (synthetic calendar, ranking, rotation options); src/compute/test_risk_calendar_real.py (real-data smoke). Results: docs/results/risk_calendar.md.
Known limitations / honest caveats: the file is ~970 lines, too big to paste whole; use the line ranges in the CHAT KIT. Unsourced thresholds are skipped and reported (`hazards_missing`), never guessed. Three PLACEHOLDER rows in crop_thresholds.csv are rejected by the reference loader.
CHAT KIT: src/compute/MODULE_risk_calendar.md, src/compute/risk_calendar.py (read in line ranges), src/compute/test_risk_calendar.py, src/compute/reference.py, data/reference/crop_calendar.csv, data/reference/crop_thresholds.csv
Last changed: 2026-10-24 by T1 (added `season_row`)

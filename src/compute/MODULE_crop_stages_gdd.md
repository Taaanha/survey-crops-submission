# crop stages and growing degree days
Layer: 1 compute
Code: src/compute/risk_calendar.py
Purpose (2–3 sentences): Turns cited stage timings into days after sowing for any sowing date and year. Crops with a `gdd` stage method accumulate degree days (calibrated on the district's mean climate); the others use cited fixed days. It also gives the day span of each stage a hazard threshold applies to (flowering window, grain fill, tuber, booting).
Public API (exact signatures + one-line description each):
- `mean_climate(tmean, seasons=SEASONS)` : mean temperature for each of the 365 days of a season.
- `gdd_target(clim, start_offset, days, base_temp)` : GDD accumulated in the mean climate over `days`.
- `days_to_target(tmean_from_sowing, base_temp, target)` : days after sowing until GDD reaches a target.
- `calibrate(spec, clim)` : GDD target per stage so the middle sowing date hits the cited days.
- `season_stages(spec, targets, tmean_from_sowing)` : stage name to days after sowing for one season.
- `stage_span(stage, stages, params)` : (first_day, last_day) inclusive for a hazard stage, or None.
Inputs (data files / other modules) and their provenance: crop specs from `build_crop_specs()` (see MODULE_risk_calendar.md); daily mean temperature (NASA POWER).
Outputs (shape + units + provenance fields): integer day offsets after sowing; provenance is the spec's citations (crop_calendar.csv rows).
Reference tables used (data/reference/*.csv rows): crop_calendar.csv (stage days, base temperature, sowing window). The stage each threshold applies to is coded in `HAZARDS` in risk_calendar.py; the threshold values are in crop_thresholds.csv.
Tests (file names + what each proves): src/compute/test_risk_calendar.py (GDD, stages, spans on synthetic data); src/api/test_field_twin_stage.py (the field twin uses the spans).
Known limitations / honest caveats: stage timings are generic cited values, not variety-specific. If a stage timing is missing or never reached, the span is None and that hazard is not assessed.
CHAT KIT: src/compute/MODULE_crop_stages_gdd.md, src/compute/risk_calendar.py (read lines 180-215 and 443-507), src/compute/test_risk_calendar.py, data/reference/crop_calendar.csv
Last changed: 2026-10-24 by session A (partition)

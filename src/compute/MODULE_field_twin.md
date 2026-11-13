# field twin (closest past year and week-by-week replay)
Layer: 1 compute + API (the replay lives in app.py)
Code: app.py, src/agents/tool_functions.py
Purpose (2–3 sentences): Shows one past season as an example: the analog year whose NASA signature up to the decision date is closest, or the week-by-week replay of a crop sown on a chosen date (rain, ET0, crop demand, stress, irrigation, heat and cold flags). An example, never a forecast, and never used for ranking. Never cut (the analog backtest). The analog maths is in MODULE_hindcast.md.
Public API (exact signatures + one-line description each):
- `twin_heat_limits(crop, stages=None)` : the crop's cited temperature limits; with `stages`, each limit carries its stage `span`.
- `twin_stage_days(crop, sow, w)` : stage name to days after sowing, as the risk calendar computes them.
- `twin_week_events(row, heat_limits, tmax=None, tmin=None, first_day=0)` : adds `events` to a weekly row; each limit is judged only on its own stage's days.
- `twin_events_rule(heat_limits)` : the explanatory block returned with the replay.
- `stage_names(crop, days)` : Kc stage name per day, for display.
- `field_twin(district: str=None, year: str=None, crop: str=None, sow_date: str=None, lang: str='en', lat: str=None, lon: str=None)` : GET /api/v1/field-twin.
- `tool_nearest_analog_year(district, current_season, decision_date='10-31')` : agent tool for the analog year.
- `tool_backtest_rotation(district, analog_year, rotation_plan)` : agent tool for the rotation backtest.
Inputs (data files / other modules) and their provenance: `load_weather()` (IMERG + POWER), SMAP (comparison only), `water_balance.crop_season`, risk-calendar crop specs, `data/reference/crop_thresholds.csv`.
Outputs (shape + units + provenance fields): weekly rows (mm/week, °C, days) with `events` in {heat, night_heat, cold, rain, dry, irrigation, ok}; every measure has `src` ids that point to provenance entries (dataset + URL).
Reference tables used (data/reference/*.csv rows): crop_thresholds.csv (`wheat.heat.anthesis_tmax` 31, `wheat.heat.grainfill_tmax` 35.4, mustard and lentil flowering, potato night, boro anthesis); crop_params.csv; soil_params.csv.
Tests (file names + what each proves): src/api/test_field_twin_stage.py (T0: each stage judged by its own limit); src/api/test_app.py (twin contract and events); src/compute/test_agroclimate.py; src/agents/test_tool_functions.py.
Known limitations / honest caveats: the boro rice replay is not built (ponded paddy). The twin uses IMERG rain; SMAP is shown only for comparison (not independent). If a stage is never reached, its limit is not flagged. The response thresholds gained two additive fields, `stage` and `span` (day range after sowing); docs/api_contract.md and web/mock/field_twin.json do not show them yet (shared-file PR).
CHAT KIT: src/compute/MODULE_field_twin.md, app.py (read lines 1690-1900), src/api/test_field_twin_stage.py, src/compute/agroclimate.py, data/reference/crop_thresholds.csv
Last changed: 2026-10-24 by session A (T0 fix)

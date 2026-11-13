# water balance (FAO-56 root zone)
Layer: 1 compute
Code: src/compute/water_balance.py
Purpose (2–3 sentences): Daily FAO-56 Chapter 8 root-zone water balance for one crop, sowing date and year, from NASA weather for the area around a field. It answers two questions: how many rainfed days were water-stressed, and how many mm of irrigation (and how many waterings) keep the crop out of stress. It is Kc-weighted, so crops with different water use are compared fairly (never cut).
Public API (exact signatures + one-line description each):
- `load_crop_params(path=CROP_PARAMS_PATH)` : cited crop rooting depth and depletion-fraction table (GAP rows are not in it).
- `load_crop_params_report(path=CROP_PARAMS_PATH)` : (params, not_assessed): the same table plus every GAP row as {item, crop, key, status: "not assessed", reason}, so a crop without a sourced value (khesari) is reported, never silently dropped or turned into 0.
- `load_soil_params(path=SOIL_PARAMS_PATH)` : per-district field capacity, wilting point and clay %.
- `total_available_water(theta_fc, theta_wp, zr_m)` : total available water in mm.
- `adjusted_p(p_table, etc_mm)` : FAO-56 depletion-fraction adjustment for high ETc.
- `kc_daily(kc_table, crop)` : daily Kc curve from the stage table.
- `weather_table(power_df, latitude_deg, elevation_m)` : adds FAO-56 ET0 to a weather table.
- `simulate_balance(rain_mm, et0_mm, kc, taw_mm, p, initial_depletion_mm=0.0, irrigate=False, adjust_p=False)` : the daily loop.
- `crop_season(crop, sowing_date, weather, kc_table, crop_params, soil, initial_depletion_frac=None, spinup_start='08-01', adjust_p=False)` : one season, rainfed and irrigated results.
- `crop_season_all_years(crop, sowing_mmdd, weather, kc_table, crop_params, soil, years=None, **kwargs)` : the same for every year.
- `reference_grass_balance(weather, soil, zr_m, p, start, end)` : grass-reference balance used to compare with SMAP.
- `weekly_anomaly_correlation(model, observed, months=None)` : r between model and SMAP weekly anomalies.
Inputs (data files / other modules) and their provenance: `load_weather()` output (NASA GPM IMERG rain + NASA POWER temperature/RH/wind/solar); `data/processed/kc_table.csv` (FAO-56 Kc); `data/reference/crop_params.csv` and `soil_params.csv` (cited; soil from ISRIC SoilGrids).
Outputs (shape + units + provenance fields): dicts and DataFrames in mm and days (net_irrigation_mm, irrigation_events, water_stress_days, etc_mm, rain_mm, harvest_date, daily frames). Provenance is attached by the caller (app.py `water_src`).
Reference tables used (data/reference/*.csv rows): crop_params.csv (`<crop>.zr_min_m`, `zr_max_m`, `p`); soil_params.csv (`<district>.theta_fc_m3m3`, `theta_wp_m3m3`, `clay_pct`).
Tests (file names + what each proves): src/compute/test_water_balance.py (GAP rows come back as not assessed with their reason, also on the real file; FAO-56 formulas, balance closure, irrigated vs rainfed, SMAP correlation helper). Validation numbers: docs/results/water_balance_validation.md.
Known limitations / honest caveats: model-vs-SMAP r is not independent evidence for IMERG (SMAP L4 rain is corrected to IMERG). Boro rice uses the paddy bucket in risk_calendar.py, not this module.
CHAT KIT: src/compute/MODULE_water_balance.md, src/compute/water_balance.py, src/compute/test_water_balance.py, data/reference/crop_params.csv, data/reference/soil_params.csv
Last changed: 2026-10-24 by session A (partition)

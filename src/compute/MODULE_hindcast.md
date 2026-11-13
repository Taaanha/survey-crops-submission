# hindcast, analog year and trends
Layer: 1 compute
Code: src/compute/hindcast.py, src/compute/change_point.py, src/compute/agroclimate.py
Purpose (2–3 sentences): Tests the analog-year method honestly: leave one year out, compare against climatology, and report skill with a sign test. It also gives onset sensitivity, Mann-Kendall / Theil-Sen trends and group comparisons. `agroclimate.py` holds the field-twin building blocks (rain onset, feature table with `decision_date`, nearest analog year, rotation backtest). Never cut.
Public API (exact signatures + one-line description each):
- `window_stat(series, start, end, how='sum')` : statistic over a date window.
- `seasonal_series(series, years, start_mmdd, end_mmdd, start_offset=0, end_offset=0, how='sum')` : one value per season.
- `rank_analogs(current_season, feature_table, candidate_years, k, features=FEATURES)` : the k closest years.
- `loo_hindcast(outcome, features=None, phases=None, k=5, feature_cols=FEATURES)` : leave-one-year-out estimates vs the outcome.
- `sign_test_p(wins, losses)` : two-sided sign-test p.
- `skill_table(table, methods, reference='climatology')` : skill = 1 - MAE_method / MAE_reference.
- `compare_groups(group, rest)` : medians, difference and Mann-Whitney p (the El Nino lens uses this).
- `trend(series)` : Mann-Kendall (Kendall tau) and Theil-Sen slope for a series indexed by year.
- `unconfirmed_onset(onset_doy, year, decision_date='10-31', dry_spell_days=7)` : onset not yet known at the decision date.
- `onset_sensitivity(rain, years, week_mm=(15.0, 20.0, 25.0), confirm_mm=(350.0, 450.0, 550.0), decision_date='10-31')` : onset under other rules.
- `onset_shift_summary(table, default=(20.0, 450.0))` : how much onset moves.
- `pettitt_test(values)` : single change point (change_point.py).
- `rain_onset(daily_rainfall, year, min_week_mm=20.0, dry_spell_days=7, dry_day_threshold=1.0, confirm_window_days=30, min_confirm_total_mm=450.0)` : rainy-season onset (agroclimate.py).
- `build_feature_table(df, years=range(2001, 2026), decision_date='10-31')` : per-year features using only data up to `decision_date`.
- `nearest_analog_year(current_season, feature_table, features=FEATURES, candidate_years=None)` : the field-twin year.
- `backtest_rotation(rotation_plan, analog_year, power_df, smap_series, kc_table, latitude_deg, elevation_m, kc_low=0.3, kc_high=1.2, pctl_low=20, pctl_high=60, window_days=15)` : replay a rotation in the analog year (Kc-weighted water comparison).
Inputs (data files / other modules) and their provenance: `load_weather()` (IMERG + POWER), SMAP root-zone series (NASA SMAP L4), `data/processed/kc_table.csv`.
Outputs (shape + units + provenance fields): pandas tables and dicts; skill, p-values, slopes, always with n. Provenance is attached by callers.
Reference tables used (data/reference/*.csv rows): none directly.
Tests (file names + what each proves): src/compute/test_hindcast.py, test_agroclimate.py, test_change_point.py. Results: docs/results/hindcast.md.
Known limitations / honest caveats: the analog year is an example, never a forecast, and is not used for ranking. POWER rain has step changes (~1997, ~2014-15): never use it for trends or rankings; POWER 1981-2025 is appendix only. The POWER-vs-IMERG homogeneity check (T9b) is not built yet.
CHAT KIT: src/compute/MODULE_hindcast.md, src/compute/hindcast.py, src/compute/agroclimate.py, src/compute/test_hindcast.py, docs/results/hindcast.md
Last changed: 2026-10-24 by session A (partition)

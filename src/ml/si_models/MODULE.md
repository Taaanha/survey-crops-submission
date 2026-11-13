# si_models: the three W3 season-insight comparisons (Layer 2)

Three problems, two methods each, scored honestly on held-out years. A real trained model where a
model is fitted (Isolation Forest, k-means); no AI/LLM calls anywhere. Every number in the outputs
carries a dataset and a source link; "not assessed" (with the reason) is used wherever a source,
threshold or window is missing — never 0.

Code: src/ml/si_models/validation.py, src/ml/si_models/features.py, src/ml/si_models/stress.py, src/ml/si_models/season_types.py, src/ml/si_models/transitions.py, src/ml/si_models/report.py

Dataset availability is read from `docs/w1b_data_status.csv` through `sat_layers.status` (never
typed here). ECOSTRESS (units unresolved) and GRACE-FO (regional, about 300 km) are NOT model
inputs; HLS (two demo tiles, no June-August scenes) is not a district-level input.

## The three problems
1. **Seasonal transitions** (`transitions.py`): green-up and browning dates from MODIS 16-day NDVI.
   Method A = cited fixed threshold (only the global 0.1 bare-soil limit exists; the Bangladesh row
   is a GAP, so A is "not assessed" when the series rarely crosses it). Method B = Savitzky-Golay
   smoothing + Pettitt change point (`compute.change_point`). Error = days outside the cited
   BRRI/BARC field-establishment windows built by `reference_windows()` from `crop_calendar.csv`
   rows with public URLs; harvest windows have no cited row, so browning error is not assessed.
   16-day composites: error below about 16 days cannot be resolved.
2. **Stressed seasons** (`stress.py`): flags past seasons that look unusual. Method A = z-score rule
   (|z| >= 2 on any feature; limit is our choice). Method B = Isolation Forest with the cut-off
   taken from the training scores at Method A's training flag rate. Scored as hits / flags outside
   the cited events in `data/reference/w3_known_events.csv` (loaded by `report.load_events`; a row
   without a readable source is never used).
3. **Season types** (`season_types.py`): Method A = percentile rule (top 20% rain and/or Tmax of
   the other years; our choice). Method B = k-means (k by silhouette). Scored by leave-one-year-out
   stability and held-out silhouette; no ground truth exists, so this is consistency, not correctness.

## Validation (validation.py)
`loyo_splits` keeps the evaluation year out of every fit; `standardize_loyo` (features.py) computes
z-scores from the other years only; tests in `tests/si_models/` prove no leak by rewriting the
held-out year and checking nothing else moves. `bootstrap_ci` puts a fixed-seed percentile interval
on every statistic and always reports n. Method B replaces A only when the paired interval clears 0.

## API
- `loyo_splits(years)` : [(train_years, test_year)], every year held out once.
- `bootstrap_ci(values, stat=np.mean, n_boot=N_BOOT, seed=SEED, level=LEVEL)` : {value, lo, hi, n, ...}.
- `paired_diff_ci(a, b, n_boot=N_BOOT, seed=SEED, level=LEVEL)` : interval of mean(b - a).
- `build_features(district, weather, indicators_long, years, seasons, modis_df=None)` : one row per
  district-season; any district slug works.
- `standardize_loyo(features, cols, test_year)` : leak-free z-scores.
- `loyo_stress(features, cols, seed=SEED, limit=Z_LIMIT)` : held-out flags for both methods.
- `score_against_events(flags, events, column)` / `compare(flags, events)` : scores and the A/B decision.
- `event_summary(flags, events, column)` : one entry per independent event (the `event` column), so districts hit by the same regional event are reported as one event, not several hits.
- `loyo_season_types(features, seed=SEED)` : (held-out types table, all-years k-means centres).
- `detect(modis_df, district, years, threshold=None)` / `add_errors(detected, windows)` : transition dates and errors.
- `reference_windows(kept)` : cited field-establishment windows or "not assessed" with the reason.
- `load_events(path=EVENTS_PATH)` / `load_ndvi_threshold(path=NDVI_PATH, item=NDVI_ITEM)` : cited rows only.
- `model_card(name, problem, method, inputs, n_text, metrics, limits, used_by_app, seed)` : markdown card.

## Build and outputs
`python scripts/build_w3_models.py [slug ...]` (default: the five live districts) writes
`docs/results/w3_metrics.json`, `w3_stress_flags.csv`, `w3_season_types.csv`, `w3_transitions.csv`
and one model card per model in `src/ml/si_models/cards/`. Wording rule kept throughout: these
describe past seasons ("flags past seasons that look unusual", "estimated", "tested on").

Tests: `python -m pytest tests/si_models -q`

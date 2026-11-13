# Architecture map (24 Oct 2026)

One row per module. Layers: **1** = `src/compute` (pure Python, no AI), **2** = `src/ml` (real model; the folder is empty today), **3** = `src/agents` (free HF model; only `guard` and two tools exist), **4** = `web/` (renders API JSON only), **API** = `app.py`, **acq** = data fetching (not a layer; writes `data/processed/`).
Each feature has a `MODULE*.md` next to its code. A chat assistant should read only that file plus its CHAT KIT.

## 1. Layout facts a new reader needs
- `app.py` is at the **repo root** (not in `src/api/`); `src/api/` holds only the API tests and `MODULE_api.md`.
- Modules import each other by **bare name** (`import risk_calendar`, `from weather import load_weather`). `app.py` adds `src/compute`, `src/agents`, `src/acquire` to `sys.path`; `tests/conftest.py` does the same for `tests/`.
- Old tests sit **next to the code** (`src/compute/test_*.py`). New feature tests go in `tests/<feature>/` (rule from session A).
- Run everything: `python -m pytest src tests -q` from the repo root.

## 2. Module table

| path | layer | purpose | public API | depends on | tests | data inputs |
|---|---|---|---|---|---|---|
| src/compute/weather.py | 1 | one loader for daily weather (IMERG rain + POWER rest) | `load_weather` | pandas | test_weather.py | data/processed/imerg_*_daily.csv, power_*_daily.csv |
| src/compute/reference.py | 1 | strict loader of cited values; rejects placeholders / no source | `load_reference`, `check_row`, `citation`, `parse_value`, `ReferenceData` | pandas | test_reference.py | data/reference/*.csv |
| src/compute/agroclimate.py | 1 | rain onset, feature table (`decision_date`), analog year, ET0, rotation backtest | `rain_onset`, `dry_spell_length`, `build_feature_table`, `nearest_analog_year`, `eto_penman_monteith`, `backtest_rotation` | numpy, pandas | test_agroclimate.py | weather, SMAP, kc_table.csv (passed in) |
| src/compute/water_balance.py | 1 | FAO-56 root-zone balance: stress days, irrigation mm | `crop_season`, `crop_season_all_years`, `simulate_balance`, `weather_table`, `kc_daily`, `load_crop_params`, `load_soil_params`, `reference_grass_balance`, `weekly_anomaly_correlation` | agroclimate | test_water_balance.py | data/reference/crop_params.csv, soil_params.csv; data/processed/kc_table.csv |
| src/compute/risk_calendar.py | 1 | crop x sowing date x hazard over 2001-2024; GDD stages; ranking; rotation options | `build_crop_specs`, `crop_calendar`, `build_calendar`, `evaluate_season`, `season_row`, `summarise`, `rotation_options`, `stage_span`, `season_stages`, `calibrate` (+ ~25 helpers) | reference, water_balance, weather, calendar | test_risk_calendar.py, test_risk_calendar_real.py | data/reference/crop_calendar.csv, crop_thresholds.csv, crop_params.csv, paddy_params.csv, crop_area_by_district.csv; data/processed/risk_calendar.csv, kc_table.csv, district_metadata.csv |
| src/compute/hindcast.py | 1 | leave-one-year-out hindcast, sign test, trends, onset sensitivity, group comparison | `loo_hindcast`, `skill_table`, `compare_groups`, `trend`, `onset_sensitivity`, `rank_analogs`, `seasonal_series`, ... | agroclimate, scipy | test_hindcast.py | weather tables passed in |
| src/compute/change_point.py | 1 | Pettitt change-point test | `pettitt_test` | numpy | test_change_point.py | none |
| src/compute/enso.py | 1 | El Nino / La Nina year labels from ONI | `label_enso_years`, `classify_oni`, `season_enso_labels` | pandas | test_enso.py | data/reference/oni.csv |
| src/compute/post_flood.py | 1 | SMAP days-to-normal, DSWx-S1 persistence / recession, earliest sowing date | `smap_days_to_normal`, `smap_recovery_curve`, `water_persistence`, `flood_recession`, `earliest_sowing_date`, `crops_still_possible` | numpy, pandas | test_post_flood.py | data/processed/smap_*.csv, dswx_*.csv, dswx_area_*.csv; data/reference/crop_calendar.csv |
| src/compute/flood_area.py | 1 | DSWx-S1 arrays to flood-water mask and stats | `combine_scenes`, `permanent_water_mask`, `flood_stats`, `flood_mask` | numpy | test_flood_area.py | arrays built by scripts/fetch_dswx.py |
| src/compute/common/ | 1 | **new** shared contract: Provenance + measured | `Provenance`, `measured` | none | tests/common/test_common_provenance.py | none |
| src/compute/rotation/ | 1 | **new (T1)** full-year rotations by chaining the risk calendar and water balance: feasibility, problem years, Kc-weighted irrigation, legumes | `candidate_rotations`, `evaluate_rotation`, `excluded_crops`, `load_context`, `load_crop_table`, `RotationContext` | risk_calendar (public API), common | tests/rotation/ | data/reference/crops.csv (+ everything risk_calendar reads) |
| src/compute/priorities/ | 1 | **new (T2)** farmer priorities: weighted re-ranking of rotations with normalised, visible components | `normalise_weights`, `score_rotations`, `evaluate_candidates`, `rank_rotations`, `flood_safety_raw`, `PrioritiesError` | rotation (public API) | tests/priorities/, src/api/test_rotation_rank.py | none directly (through rotation) |
| src/agents/guard.py | 3 | provenance gate: blocks numbers not in a cited tool result | `guard`, `find_numbers` | re | test_guard.py | none |
| src/agents/tool_functions.py | 3 | two agent tools over Layer 1 (analog year, backtest) | `tool_nearest_analog_year`, `tool_backtest_rotation`, `candidate_years` | agroclimate, weather | test_tool_functions.py | data/processed/*, tools.json |
| src/agents/tools.json | 3 | tool schemas for the HF model | (data) | n/a | n/a | n/a |
| src/agents/check_hf_*.py, smoke_test_tools.py | 3 | manual connection / tool-call checks (not unit tests) | scripts | `openai` SDK pointed at the HF router (only in src/agents, never src/compute) | n/a | HF token from env |
| src/ml/ | 2 | **empty**; drain-time model is task T8 | none | n/a | n/a | n/a |
| src/acquire/safe_fetch.py | acq | live -> cache -> fixture fetch with `source_mode` | `fetch_json` | requests | test_safe_fetch.py | cache/, demo_fixtures/ |
| src/acquire/fetch_power.py | acq | download NASA POWER for a district | `fetch` | requests | none | writes data/processed/power_*.csv |
| src/acquire/fetch_soilgrids.py | acq | builds data/reference/soil_params.csv from SoilGrids | `usda_texture`, `query_point`, `district_texture`, `main` | requests | none directly (imported by soilgrids_point, so only indirectly exercised) | data/raw/soilgrids_points.json |
| src/acquire/soilgrids_point.py | acq | topsoil at one field point for /api/v1/soil | `soil_at`, `fetch_point`, `parse_response`, `SoilGridsError` | fetch_soilgrids | src/api/test_soil.py (mocked) | ISRIC SoilGrids REST |
| app.py | API | FastAPI v1: envelope, provenance, narration, 7 endpoints + 3 mocks | `app`, `measure`, `respond`, `narrate`, `field_twin`, `advisory`, ... | src/compute, guard, soilgrids_point | src/api/test_app.py, test_soil.py, test_assumptions_doc.py, test_field_twin_stage.py | data/processed/*, data/reference/*, web/mock/*.json |
| web/app/index.html, config.js, bn/, fields/ | 4 | static site: renders API JSON; Bangla audio in bn/ | none | `API_BASE` in config.js | none (manual) | API only |
| web/mock/*.json | 4 | example responses = the contract fixtures | none | docs/api_contract.md | checked by test_app.py | n/a |
| scripts/*.py | tooling | build tables, fetch NASA data, validate, deploy | CLI | compute, requests | build_assumptions_doc via test_assumptions_doc.py; check_module_docs via tests/docs | NASA services, data/ |

## 3. Dependency diagram (arrows = "imports / reads")

```
web/app (HTML) --HTTP--> app.py (API)
                          |-- src/agents/guard.py                  (narration check)
                          |-- src/acquire/soilgrids_point.py --> fetch_soilgrids.py
                          |-- src/compute/risk_calendar.py ---+--> water_balance.py --> agroclimate.py
                          |        |                          +--> reference.py
                          |        +--------------------------+--> weather.py
                          |-- src/compute/post_flood.py
                          |-- src/compute/water_balance.py
                          +-- src/compute/weather.py, reference.py

src/agents/tool_functions.py --> agroclimate.py, weather.py
src/compute/hindcast.py      --> agroclimate.py
src/compute/enso.py, change_point.py, flood_area.py   (leaf modules, no compute imports)
src/compute/common/          (leaf; new modules import ONLY this + public APIs)

Data (read-only inputs):  data/processed/*.csv   data/reference/*.csv   web/mock/*.json
Rule: arrows only go down (web -> API -> agents/compute -> common/data). Never up.
```

## 4. Provenance gaps (nothing refactored in session A; fix when each task touches the code)

| where | gap vs rule "every number carries dataset, source_url, retrieved, granule/file" |
|---|---|
| app.py `measure()` and `build_provenance()` | measures are `{value, unit, src}`; provenance entries have `dataset`, `url`, `period`, `note` but **no `retrieved` and no `granule_or_file`** |
| docs/api_contract.md | does not mention `retrieved` or `granule_or_file` |
| src/agents/guard.py | (closed in fixups-after-t2) accepts `source_url` (preferred) or `url` next to `dataset`; an empty link or missing dataset still blocks |
| src/compute/* (all old modules) | return plain pandas / dicts; provenance is attached later by app.py, not by the function |
| src/compute/reference.py | reads columns `item,value,unit,source_title,source_url,page,year,notes`; the new rule uses `name,value,unit,source_title,source_url,page_or_table,note`. An adapter is needed before T1 |
| OPERA DSWx-S1 / SMAP | provenance names the dataset, not the granule ids; T3 must return granule ids |
| web/mock/enso_lens.json, warnings.json, ask.json | mocks, not real data (`is_mock: true`) |

## 5. Size watch (rule: new files under ~400 lines so they paste into a chat)

| file | lines | note |
|---|---|---|
| app.py | ~1950 | split per endpoint when T18 adds endpoints; new endpoints should import from new feature modules |
| src/compute/risk_calendar.py | ~970 | T1 rotation engine goes in its own folder, not here |
| src/api/test_app.py | ~720 | add new endpoint tests in new files |
| web/app/index.html | ~1290 | frontend teammate's file |
| src/compute/water_balance.py | ~380, agroclimate.py ~420 | borderline |

## 6. Where a new feature goes (rule from session A)

```
src/compute/<feature>/__init__.py   public API only
src/compute/<feature>/core.py       (+ small helper files)
src/compute/<feature>/MODULE.md
tests/<feature>/test_<feature>_*.py   (unique file names: there are no __init__.py files)
data/reference/<feature>_*.csv      every coefficient: name,value,unit,source_title,source_url,page_or_table,note
```
A module may import only `common` and the public API listed in another module's MODULE file.

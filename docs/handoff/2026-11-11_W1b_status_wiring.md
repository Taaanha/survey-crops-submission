# Handoff: ECOSTRESS findings recorded, W2 reads the W1b status table, MODIS 2017 accepted

Branch: `w1b-status-wiring` (cut from `w2-indicators`; the W1b intake files were still uncommitted, so they are in this working tree too). Nothing committed.

## 1. What was done
**Part 1, ECOSTRESS (recorded exactly as supplied, from Tanha's Colab run; not re-run here)**
- ETdaily metadata says "W/m²", but the same tag is on the 0/1 `cloud` layer, so the units attribute looks like a blanket label.
- `cloud` has only 0 and 1. In one scene: 2,433,733 pixels = 0, 844,427 = 1. cloud = 1 pixels have no ETdaily value; cloud = 0 pixels have one in 53.6% of cases (median raw ET 1.91). Mask: supported by one scene, not documented.
- Raw values (median about 2) are plausible as mm/day, not as W/m² (about 0.07 mm/day). **Units UNRESOLVED; no conversion, no unit chosen.**
- Status stays "not assessed (units unresolved)" for any comparison with FAO-56 ET0. `load_ecostress` still refuses the series; its message now says the units are unresolved and that the ETdaily unit in the ECO_L3T_JET.002 User Guide or ATBD would resolve it (that unit is not assumed).
- Recorded in `docs/results/w1b_intake_checks.md`, `docs/harmonisation.md`, and Open questions in `docs/PROJECT_STATE.md`.

**Part 2, W2 reads the status table** (`src/compute/indicators/layer_status.py`, used by `build.py` and `scripts/build_indicators.py`)
| Indicator | Status now comes from | Behaviour |
|---|---|---|
| `modis_ndvi_z` | `modis_ndvi_anomaly` | n = years present, read from the MODIS data (10 now). Fewer than 6 years, or no data for the district: "not assessed (needs >=5 other years; only n years present)". Otherwise "partial: <table reason>". Value stays NaN (season-level z not computed here). |
| `grace_fo_trend` | `grace_fo` | Trend by the existing Theil-Sen + Kendall + Pettitt rule. Status text starts "partial (regional, about 300 km, shared cells)" and carries the table reason. Slope given only when the series is a trend, else NaN. Also written to `indicators_trends_2001_2024.csv` as variable `grace_lwe` with a `note` column. |
| `ecostress_et_comparison` | `ecostress_et` | "not assessed (units unresolved: ...)", value NaN. |
| SMAP, districts without a point file | `smap_64` | "not assessed (AppEEARS job did not finish; five live districts use the existing point files)". The five live districts keep their point files. |
A key missing from the table is a `KeyError`, not a default. Regenerated: `data/processed/indicators_*`, `docs/results/w2_homogeneity.md` (now includes the GRACE-FO regional rows; two sentences in `build_w2_reports.py` were corrected for that).

**MODIS 2017 accepted.** `modis_district_2017.csv.gz`: 64 districts, 24 dates, starts 2016-12-18 (previous year's last composite), no duplicates, overlaps with the 2016 and 2018 files match exactly (128 rows, largest NDVI difference 0.0). MODIS now has 10 years (2015-2024), 14,784 joined rows; 2001-2014 still missing. Status table, intake report and the affected tests updated.

## 2. Tests first, as asked (`tests/indicators/test_layer_status.py`, 13 tests; hand-worked)
(a) fewer than 6 years gives "not assessed" (3 years; 6 and 8 years give partial with n read from the data); (b) missing datasets give "not assessed" with the reason from the table, and a changed table changes the output; (c) not-assessed rows are NaN, never 0, and still carry dataset + URL; (d) a stale status table fails (`test_shipped_status_table_is_not_stale`) and a stale shipped indicator file fails (`test_shipped_indicator_file_matches_the_status_table`). Also: GRACE-FO slope exactly 2 cm per year on a fixture line; fewer than 8 seasons gives NaN with "need 8". Tests for the refusal message are in `tests/sat_layers/test_loaders.py`.

## 3. One point to confirm
Your brief says MODIS needs "at least 6 other years"; the rule already in the code and in the status table is **at least 6 years present, and at least 5 other years per composite**, and test (a) says "fewer than 6 years". I kept the existing rule. If you meant 6 other years (so 7 years present), change `MIN_YEARS_FOR_ANOMALY` and `MIN_OTHER_YEARS`; the effect today is none (10 years are present).

## 4. Tests and checks
`python -m pytest src tests -q`: **645 passed, 5 skipped** (was 632 before this task). `python scripts/check_module_docs.py`: 18 module files, 0 problems. No new file near 5 MB (largest new/changed: `indicators_districts_2001_2024.csv`, 2.3 MB). No credentials in code or docs (searched). `notebooks/w1b_earthdata_colab.ipynb` was not touched by this task (it still shows an outside edit in `git status`).

## 5. Still open
ECOSTRESS unit (User Guide/ATBD); MODIS 2001-2014; SMAP-64; GEDI; ECOSTRESS LST; a season-level MODIS NDVI z-score (needs a rule for how many composites a season window must have: a choice for Tanha); the `wm2_to_mm_per_day` factor and notebook cell 9 must not be used for ECOSTRESS.

## 6. Files
New: `src/compute/indicators/layer_status.py`, `tests/indicators/test_layer_status.py`, `data/processed/modis_district_2017.csv.gz`, this handoff. Changed: `src/compute/indicators/{build,explain}.py` and `MODULE.md`; `src/compute/sat_layers/{loaders,provenance,intake}.py`; `scripts/{build_indicators,build_w2_reports,build_w1b_intake}.py`; `tests/sat_layers/*`, `tests/indicators/test_indicators_build.py`; regenerated `data/processed/indicators_*`, `docs/w1b_data_status.csv`, `docs/results/{w1b_intake_checks,w2_homogeneity}.md`; `docs/{harmonisation,PROJECT_STATE,AI_USE}.md`.

## 7. Self-review checklist
- [x] ECOSTRESS findings recorded exactly as given, nothing added; units UNRESOLVED; no conversion, no unit chosen or assumed.
- [x] Loader refusal kept; message says units are unresolved and what would resolve them.
- [x] Added under Open questions in PROJECT_STATE.md and to `w1b_intake_checks.md`.
- [x] W2 statuses and reasons come from the table; MODIS years read from the data; GRACE-FO labelled regional; ECOSTRESS "not assessed (units unresolved)"; SMAP-64 reason from the table, live districts keep point files.
- [x] Tests written first; (a), (b), (c), (d) covered with hand-worked fixtures.
- [x] Never a 0 for a not-assessed value (test over every such row, plus the shipped file).
- [x] No AI/LLM imports in `src/compute/`; no "predict"/"forecast" in new text; no credentials; every new row carries dataset + source URL.
- [x] No file near 5 MB; nothing staged or committed; notebook untouched.
- [x] Docs: PROJECT_STATE row and open questions, harmonisation, AI_USE, MODULE.md (indicators), handoff.
- [ ] Not done: items in section 5, and the 6-vs-5 other-years wording in section 3 needs your confirmation.

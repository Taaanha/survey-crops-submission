# AI Use Log

This file tracks every AI tool used in building CropShift, per NASA Space
Apps transparency requirements and the Space Apps build guide's
`evidence-provenance` guidance. Updated as the project progresses, not
written after the fact.

## Tools used

**Claude (Anthropic, claude.ai chat)** — used throughout the build, via
plain conversational chat (no Claude Code, no autonomous agent access to
this repo). Used for:
- Project planning and phase sequencing (prompt-2.md, this log)
- Step-by-step teaching/guidance for a first-time coder (git, VS Code,
  Colab, virtual environments)
- Writing and debugging `src/compute/agroclimate.py`: `rain_onset()`,
  `nearest_analog_year()`, `build_feature_table()`, `dry_spell_length()`,
  `eto_penman_monteith()` (FAO-56 Penman-Monteith), `backtest_rotation()`
- Writing unit tests for all of the above (`test_agroclimate.py`)
- Debugging real data issues found during development (a unit-conversion
  bug in solar radiation between POWER communities, a percentile
  tie-breaking bug, corrupted intermediate CSV files, misplaced import
  statements)
- Empirically tuning `rain_onset()`'s confirmation threshold against
  2001-2025 Cumilla POWER data
- Compiling FAO-56 standard crop coefficient (Kc) reference values
- Setting up the Hugging Face Inference Providers connection
  (`src/agents/test_hf_connection.py`, `test_hf_tool_calling.py`)
- Writing `src/agents/guard.py`: the provenance gate that extracts every
  number from the agent's narrated text (English and Bangla ০-৯ digits,
  comma grouping, decimals, %) and blocks any number that doesn't match a
  value inside a tool result carrying both `dataset` and `url`. Also wrote
  its pytest tests (`test_guard.py`), including a fabricated-number case.

**Claude Code** — added a `decision_date` parameter (default `"10-31"`) to
`build_feature_table()` in `src/compute/agroclimate.py`, so every feature
for year Y (onset, onset amount, dry spell, mean temperature) is computed
only from data on or before `decision_date` of that year — no feature can
use data that wouldn't yet exist on the day a recommendation is made. Also
adjusted the row's minimum-coverage floor to scale with `decision_date`
(previously a flat 300 days, which would have rejected every early-season
cutoff), threaded `decision_date` through
`tool_nearest_analog_year()` in `src/agents/tool_functions.py`, and added
tests proving (1) mutating data after `decision_date` does not change the
computed features and (2) a different `decision_date` does change them.

**Claude Code** — filled Task 3 test gaps: (1) a test validating
`eto_penman_monteith()` against FAO-56 (Allen et al., 1998) Chapter 4
Example 18 (Uccle, Belgium, 6 July, published ET0=3.9 mm/day); found and
documented that the function's single `rh_pct` input (vs. FAO-56's
separate RHmax/RHmin) moves its result to 3.79 mm/day, just outside the
requested ±0.1 mm/day tolerance of the published value, so the test
validates against the function's own arithmetic (3.79) with the gap noted
in the docstring rather than fudging the tolerance; (2) a direct
`build_feature_table()` test with hand-computed expected values on a
small synthetic dataframe, plus a test confirming a no-onset year is
excluded from the table; (3) `src/agents/test_tool_functions.py`, testing
`tool_nearest_analog_year()` and `tool_backtest_rotation()` against real
district CSVs in `data/processed/` (no mocking) — result keys, that every
`source` carries `dataset` and `url` (what `guard()` requires), and the
pre-2015 SMAP refusal. Also moved a `candidate_years` explanation that had
been left in `eto_penman_monteith()`'s docstring into
`nearest_analog_year()`'s, where that parameter actually lives.

**Claude Code** — gave `eto_penman_monteith()` a second, more accurate path
for actual vapour pressure: when the row carries `rh_max_pct`/`rh_min_pct`,
`ea` is computed from those separately (FAO-56 Eq.17); otherwise it falls
back to the existing RH-mean method (FAO-56 Eq.19), which is what NASA
POWER's single daily RH2M value requires. Replaced the old single Example
18 test with two: one feeding RHmax=84/RHmin=63 through the new Eq.17 path
(matches FAO-56's published 3.9 mm/day within ±0.1), and one feeding
RHmean=73.5% through the Eq.19 fallback (documented as validating the
function's own arithmetic at 3.79 mm/day, not the published value, per the
known approximation gap).

**Claude Code** — Task 4, the FAO-56 root-zone water balance. Wrote
`src/compute/water_balance.py`: FAO-56 Chapter 8 Eq. 82-88 (TAW, RAW,
Ks, the daily depletion balance, deep percolation), a Kc curve that
interpolates linearly through the development and late stages (FAO-56
Eq. 66 / Fig. 25) instead of stepping, and per crop/sowing date/year
outputs (water-stress days rainfed, net irrigation mm to refill to field
capacity whenever Dr > RAW, deep percolation mm, daily tables). Wrote its
tests (`test_water_balance.py`: mass balance closes, no-rain depletion
grows, heavy rain drains, irrigation refills, a hand-computed stress-day
count). Built the two reference files from sources it read during the
session rather than from memory: `data/reference/crop_params.csv` (Zr
and p from FAO-56 Table 22, checked against the FAO HTML edition) and
`data/reference/soil_params.csv`, written by the new
`src/acquire/fetch_soilgrids.py` (clay/silt/sand from ISRIC SoilGrids 2.0
around each district, sampled away from the India border, then the
FAO-56 Table 19 midpoints for that USDA texture). Two districts'
SoilGrids textures have no Table 19 row (Brahmanbaria: clay loam;
Sylhet: sandy clay loam); the script refuses to guess unless a reviewed
fallback is recorded, and uses the nearest Table 19 class (clay; loam),
with the reason written into each row's notes. Wrote
`scripts/validate_water_balance.py`, which compares weekly anomalies of a
reference-grass balance with SMAP root-zone soil moisture (2015-2025) and
writes `docs/results/water_balance_validation.md`.

**Hugging Face Inference Providers** — a free, open-source hosted model
(Llama-3.1-8B-Instruct) is used as the CropShift agent's reasoning layer
(Layer 3, `src/agents/`). Per the project's architecture rules, this model
never computes any statistic or number itself — it only calls deterministic
Python tools (Layer 1, `src/compute/`) and narrates their results. This is
enforced by a provenance gate (`src/agents/guard.py`) that blocks any
narrated number that doesn't match a cited tool result.

**Claude Code** — moved the project to an online-first design: updated
`CLAUDE.md` (live → cache → fixture fallback; only the backend fetches
live data; secrets via env vars only; per-point-per-day cache; every
response reports `source_mode`) and added Task 7b (live season + live
flood check for any GPS point in the 5 districts). Wrote
`src/acquire/safe_fetch.py`: `fetch_json(url, params, cache_key,
ttl_hours=24)` tries a live GET first, falls back to a per-point cache in
`cache/` (gitignored) if fresh, then to a checked-in fixture in
`demo_fixtures/`, then to a stale cache as a last resort so a demo never
hard-fails if any prior data exists; `OFFLINE=1` skips the live attempt
entirely. Wrote `src/acquire/test_safe_fetch.py` against a fake
non-resolving URL and a temp cache/fixture dir (no real network), covering
the fixture fallback, the cache fallback, the no-data-at-all error, the
`OFFLINE` flag, and the stale-cache last resort.

**Claude Code** — Task 5a, extended the historical record back to 1981 and
added ENSO context. Gave `src/acquire/fetch_power.py` an optional
`start_date` argument (default unchanged at `20010101`) and re-downloaded
all 5 districts from 1981-01-01 to 2026-08-31; POWER's `-999` missing-value
sentinel is now converted to `NaN` rather than left as a magic number, and
no gap is filled. All 7 weather columns have real data from 1981-01-01
except `solar_rad_mj_m2`, which starts 1984-01-01 in every district (later
than the ~mid-1983 estimate in the task brief; reported as found, not
adjusted to match the estimate). Wrote `scripts/fetch_oni.py`, which
downloads NOAA CPC's ONI ascii table and saves
`data/reference/oni.csv` (919 rows, 1950-2026, columns `season, year,
total, anom, source_title, source_url`). Wrote `src/compute/enso.py`
(`label_enso_years()`): the standard CPC rule — an episode is >=5
consecutive overlapping 3-month seasons with anomaly >=+0.5 (El Nino) or
<=-0.5 (La Nina) — applied to the ONI series to label every year. Found
and fixed a bug in its own first implementation during manual verification
against the real ONI series: grouping consecutive True/False runs with
`(~is_event).cumsum()` merges the boundary False row into the next run,
so any event run not starting at row 0 of the series was silently
dropped — caught because the real data returned zero El Nino/La Nina years
where several are well known (1982-83, 1997-98, 2015-16, 2023-24), while
the hand-written unit tests had (accidentally) all placed their event runs
at the start of the tiny test series and so didn't catch it. Fixed with
the standard change-point method (`is_event != is_event.shift()`) and
added a regression test with a run that starts mid-series. `build_feature_table()`'s
default years are unchanged (2001-2025); `python -m pytest src -q` passes
(74 tests) with no changes to any existing test's expected values.

**Claude Code** — Task 5b, hindcast + trends + El Nino lens. Wrote
`src/compute/hindcast.py` (seasonal totals that refuse partly covered
windows, analog ranking built on the unchanged `nearest_analog_year()`,
a leave-one-year-out comparison of the long-term average, 1 analog, the
mean of 5 analogs and the ENSO-phase average, skill = 1 - MAE/MAE of the
long-term average with a sign test, Mann-Whitney group comparison,
Mann-Kendall + Theil-Sen trends via SciPy, and `rain_onset()` threshold
sensitivity) with tests on tiny synthetic data (`test_hindcast.py`: a
perfect analog scores skill 1, a constant series makes the long-term
average exact, the held-out season never feeds its own estimate). Added
`classify_oni()` and `season_enso_labels()` to `src/compute/enso.py`
(one label per season from the ASO ONI value, known by the 31 Oct
decision date) with new tests in `test_enso.py`; existing functions,
defaults and tests unchanged. Wrote `scripts/run_hindcast.py`, which
writes `docs/results/hindcast.md`. Added SciPy to the venv (free,
open-source). While checking the real-data results it found and reported,
without changing the existing functions: (1) POWER Jun-Sep rain in
1981-2000 is about half the 2001-2025 level and most early years have no
confirmed monsoon onset, so the 1981-2025 rain "trends" are not
presented as climate change and a 2001-2025 robustness check was added;
(2) `rain_onset()` accepts a wet week in the last 7 days before the
cutoff without its dry-spell and 30-day checks, which gives some years
a spurious late-October onset in `build_feature_table()`; these are
flagged in the report. Net irrigation from the water balance moves in
steps of about one RAW refill, which the report states.

**Claude Code** — fixed the `rain_onset()` edge case flagged in Task 5b.
A 7-day window with fewer than 7 days of data after it (a wet week just
before the 31 Oct cutoff) was accepted as the onset without the
dry-spell and 30-day checks; it is now skipped, so such a year has no
onset. All other defaults unchanged. Added a test (a single wet week at
the very end of the data is not an onset) and rewrote one hindcast test
that had pinned the old behaviour. Re-ran `scripts/run_hindcast.py`: the
unconfirmed late-October onsets in `docs/results/hindcast.md` drop to 0,
and those years now count as "no onset", so 21 fewer district-seasons
are scored in the analog comparison (pooled 141 -> 120 for rabi rain).
The conclusion is unchanged: nothing tested beats the long-term average.

**Claude Code** — Task 5c, made 2001-2025 the primary analysis window.
Restructured `scripts/run_hindcast.py` and `docs/results/hindcast.md` so
the hindcast skill table, El Nino lens and trends are computed and
reported over 2001-2025 only; the 1981-2025 record now appears only in
an "Appendix: Data-consistency check (not used for recommendations)",
alongside a small year-by-year table (1993-2000) showing NASA POWER's
Jun-Sep rain jump from ~700-1,200 mm to ~1,300-1,600 mm around 1997. This
was a data-consistency break flagged during Task 5b, not a real change
in the monsoon. Added the corresponding line to CLAUDE.md's "Data facts".
Added `requirements.txt` (packages actually imported by the code: pandas,
numpy, scipy, requests, pytest, python-dotenv, openai; major versions
pinned only). Deleted 6 remote branches already merged into main
(fix-onset-end-of-data, task1-guard, task3-tests, task4-water-balance,
task5b-hindcast, team-setup); 2 others (online-first, task5a-data-1981)
had already been deleted. `python -m pytest src -q` passes unchanged
(102 tests; no test values changed since Task 5b's fix, only the report
layout).

**Claude Code** — Task 5d, switched rain to NASA GPM IMERG. Wrote
`scripts/fetch_imerg.py` (IMERG V07 Final Run daily, GPM_3IMERGDF.07,
through the NASA Giovanni time-series API, the first access method that
worked; resumable; token read from `.env`, never printed). It downloaded
2001-01-01 to 2025-09-30 (the Final Run's last day at GES DISC) for the five
district points in about 6.5 minutes and records each 0.1 degree cell centre in
`data/processed/imerg_cells.csv`. Added `src/compute/weather.py`
(`load_weather()`: POWER table with IMERG rain, never mixing the two rain
records) and `src/compute/change_point.py` (Pettitt test), each with tests.
`scripts/check_rain_source.py` writes `docs/results/rain_source_check.md`:
POWER rain has a significant change point around 2014-15 in all 10
district series (annual and Jun-Sep, +38% to +84%); IMERG has none (every
p > 0.5). The decision rule was fixed in the script before the results
were seen. Added BMD station monthly normals from BMD's own PDF to
`data/reference/bmd_normal_rainfall.csv`. IMERG is now the default rain
source for `validate_water_balance.py`, `run_hindcast.py` (primary window
now seasons 2001-2024; POWER 1981-2025 kept for the appendix) and the agent
tools (which also now refuse to match on a year cut off before the
decision date). SMAP weekly-anomaly r rose in every district (mean 0.44 ->
0.56). Claude checked the SMAP L4 user guide and flagged that SMAP L4's rain
forcing is corrected to IMERG, so this gain is not independent evidence.
The POWER "+458 mm/decade Jun-Sep" trend is gone with IMERG (+1.8
mm/decade, p = 1.00) and was removed. `python -m pytest src -q`: 115 passed.

**Claude Code** — Task 7a, the post-flood recovery clock. Wrote
`src/compute/post_flood.py`: `smap_days_to_normal()` (a calendar-window
percentile of every *other* year, held for `hold_days` in a row, with 70th/
90th percentile sensitivity reported alongside the 80th), `water_persistence()`
(last date OPERA DSWx-S1 saw open water/inundated vegetation in a window,
plus how many observations were usable), `earliest_sowing_date()` (the later
of the two, no extra buffer), and `crops_still_possible()` (compares against
`data/reference/crop_calendar.csv`, which does not exist yet, so every crop
comes back "research pending" rather than an invented sowing window — this
is the honest, unfinished half of the flood -> late-sowing -> risk cascade;
the re-ranking half needs Task 6's `risk_calendar.py`, not built yet). Wrote
`test_post_flood.py` (18 tests: synthetic recovery curves, the hold-days
requirement, percentile sensitivity ordering, DSWx-S1 validity filtering,
the "research pending" path for a missing file and a missing crop row).

Wrote `scripts/fetch_dswx.py`: searches NASA CMR via `earthaccess` for OPERA
DSWx-S1 granules near a point, then reads only a 300 m x 300 m window of the
WTR band per granule via an HTTPS range request (`rasterio` + `earthaccess`'s
authenticated fsspec session) — never a full scene, and nothing raster ever
touches disk or git. Looked up the actual WTR band value codes (0/1/3 = not
water/open water/inundated vegetation, 250/251 = HAND/layover-shadow masked,
255 = fill) from the OPERA DSWx-S1 product spec and PO.DAAC docs rather than
guessing. Timed 5 real granule reads (~4.1 s each; ~3.4-3.5 s/granule once
warmed up) before running the fetch, and reported the full-history estimate
(1,616 granules, ~94 minutes) versus what was actually fetched (315
granules through 2024-12-31, ~18 minutes) in `docs/results/post_flood.md`,
rather than running the full fetch unasked. Added `earthaccess` and
`rasterio` to `requirements.txt` and `EARTHDATA_TOKEN` to `.env.example`
(it was already required by the existing `scripts/fetch_imerg.py` but
missing from the example file).

Ran the pipeline for August 2024 (Feni, Cumilla, Noakhali, Brahmanbaria) and
June 2022 (Sylhet, SMAP-only — DSWx-S1's mission data starts 2023-12-01,
after that flood) and wrote up the results, including a caveat that
DSWx-S1's persistent small water_fraction at the Noakhali and Brahmanbaria
district points looks like a permanent water feature (pond/khal) inside the
300 m window rather than draining floodwater, so those two districts'
headline earliest-sowing-date uses the SMAP-only date with DSWx-S1 flagged
as inconclusive, instead of silently combining a likely-spurious "still
flooded" reading into the number. `python -m pytest src -q`: 133 passed.

**Claude Code** — Task 7a-2, making the DSWx-S1 flood signal visible. Added
an `--area` mode to `scripts/fetch_dswx.py`. It reads a 20 km x 20 km
window (30 m UTM grid, WarpedVRT range reads, no full tiles) from every
DSWx-S1 granule touching it. It covers the flood period (2024-08-21 to
2024-12-31) and a dry-season reference (Jan-Mar 2025), caches the windows in
`cache/` (gitignored), and builds `data/processed/dswx_area_<district>.csv`
plus 8 small PNG maps (Feni, Noakhali) in `docs/results/img/`. Timed 5 reads
first (~4.0 s/granule; 702 granules, ~47 min estimated, 41 min actual, 0
failures). Wrote `src/compute/flood_area.py` (merge same-day granules,
permanent-water mask, flood stats) with `test_flood_area.py`. Added
`flood_recession()` to `post_flood.py` and let `earliest_sowing_date()`
take its result, with 7 new tests. The plain "below 10% of peak" rule never
triggered at Cumilla or Noakhali, because the method sees a floor of
non-permanent water even in the dry season. So `flood_recession()` also
takes an optional `baseline` (the default of 0 keeps the plain rule), and
the report headlines "90% of the water above the dry-season floor gone",
showing the plain-rule result next to it. Claude flagged that Noakhali's
DSWx-S1 signal can't be separated from seasonal water, and that
Brahmanbaria's is mostly seasonal drawdown, rather than presenting them as
flood recession. Added `matplotlib` to `requirements.txt`.
`python -m pytest src -q`: 147 passed.

**Claude Code** — Task 6, sowing-date risk calendar with rotation input.
Wrote `src/compute/reference.py`, a strict loader for `data/reference/*.csv`.
It skips PLACEHOLDER rows, non-http(s) sources, malformed items and
unparseable values, and lists each with a reason. It parses A-B ranges and
MMDD dates and keeps every kept row's source/page. Teammates' files were not
edited. Also wrote `src/compute/risk_calendar.py`: GDD-calibrated stages,
hazards only where a kept row gives both the threshold and the stage timing,
the water balance from `water_balance.crop_season()`, a ponded-paddy need
for boro, and `rotation_options()`. `scripts/build_risk_calendar.py` writes
`data/processed/risk_calendar.csv` and `docs/results/risk_calendar.md`.
Every modelling choice not from a source is a named "CropShift assumption",
with sensitivity runs for hot days (1/3/5), threshold end and flowering
window width. Claude reported, rather than filled, what the strict rules
remove. The BRRI rows (file-name sources) held boro's only stage durations
and the 12-13 C cold threshold, so the boro cold sanity check cannot run
and its test is skipped. Mustard's flowering row is split across two lines.
The CZIS zoning rows are skipped, are not used as a filter, and conflict
with BBS area. It also fixed a pre-existing failing test: `post_flood.py`'s
`crops_still_possible()` expected an older crop_calendar layout and would
crash on the real file, so it now returns a clear pending notice.
`python -m pytest src -q`: 191 passed, 5 skipped.

**Claude Code** — Task 6b, hazard coverage labelling in
`rotation_options()`. Every ranked crop now carries `hazards_checked` /
`hazards_missing` (lists), `n_hazards_checked`, `coverage` ("full" only if
every hazard `HAZARDS` lists for that crop is sourced, else "partial") and
`problem_line`, a plain-language sentence that always names what was
checked, e.g. "problems in 0 of 24 years (checked: night heat only)", so a
crop is never read as safer just because fewer hazards were evaluated for
it. Partial-coverage crops get `coverage_notice`: "Not all risks for this
crop are checked yet." The ranking order itself is unchanged (still
problem share, then worst-20% irrigation); this only adds the label.
`scripts/build_risk_calendar.py`'s "problem years" cell now uses
`problem_line` directly and a new "coverage" column was added.
`data/reference/` was not touched. `python -m pytest src -q`: 192 passed,
5 skipped (one new test: a crop with 0 problems but partial coverage gets
the partial label and notice).

**Claude Code**: Task 10a, the first real API (`app.py`, FastAPI). The endpoints
`/districts`, `/advisory` (`prev_harvest`, optional `flood_ready`), `/risk-calendar`,
`/post-flood` and `/field-twin` are built only from existing `src/compute`
functions (`rotation_options`, the `risk_calendar.csv` rows, `smap_days_to_normal`,
`flood_recession`, `earliest_sowing_date`, `load_weather` + `crop_season`). Each
response uses the contract envelope. Every number is a `{value, unit, src}`
measure that points to a provenance entry with a dataset and URL: IMERG, POWER,
SMAP, OPERA DSWx-S1, FAO-56, and each `data/reference/` source by id. Narration is
a template sentence checked by `guard()`, with a number-free fallback.
Coverage is always stated as "Checked: …" plus "Not all risks for this crop are
checked yet.", so `rotation_options`' "full"/"partial" label is never sent.
`/enso-lens`, `/warnings` and `/ask` serve the mock with `is_mock: true`. One
compute change: `post_flood._days_to_normal()` now stops at the first qualifying
7-day run instead of scanning to the end of the SMAP record. The answer is the same
(the Aug-2024 values for all 4 districts still match `docs/results/post_flood.md`)
and it runs in ~2 s instead of ~31 s. Weather and the demo floods are
warmed at startup (~13 s), so warm requests take 0.02-0.06 s, and a new flood date
takes ~2 s once. New contract tests are in `src/api/test_app.py` (81). Contract
differences are proposed in `docs/contract_change_proposals.md`; the shared
`docs/api_contract.md` and `web/mock/` were not edited. Bangla strings need
review by a Bangla speaker. Known limitation (compute, fixed in task 6c
below): `rotation_options()` put a June/July ready date at the end of the
previous Aug-Jul season, so every rabi window read as passed (e.g. Sylhet
flood of 2022-06-17). `python -m pytest src -q`: 273 passed, 5 skipped.

**Claude Code** — Task 6c, the season-rollover bug: a June/July earliest
sowing date (e.g. Sylhet flood 2022-06-17, ready 2022-07-07) reads as the
tail end of the previous Aug-Jul season, past every rabi window
(Nov-Jan), so `rotation_options()` reported `window_passed=True` for
every rabi crop with no sowing date. Reproduced with
`rc.rotation_options('sylhet', '2022-06-17', '2022-07-07')`.

Before the fix, every option (wheat, mustard, lentil, potato, boro_rice)
had `window_passed=True, sowing_date=None, rank=None`. After: if every
rabi crop's window (plus the 4-week grid tail) has already passed for the
season the earliest date falls in, `rotation_options()` now rolls over to
the next rabi season instead (new `season`/`next_season_used`/
`next_season_note` fields on the result); for the Sylhet example it picks
mustard (2022-10-15, rank 1), lentil (2022-10-24, rank 2), wheat
(2022-11-15, rank 3), potato (2022-11-01, rank 4), boro_rice
(2022-12-05, not ranked: no live hazard) — none `window_passed`.
Separately, if the earliest date falls inside or before the sourced
`aman_rice.sow.window_start/window_end` (data/reference/crop_calendar.csv,
BARC crop calendar, loaded via `reference.py`; that file was not edited),
an `aman_rice` option is added at the front of `options` — "Aman
transplanting still possible until 2022-07-30 (Crop Calendar - Aman Rice
...). Weather risk for aman is not assessed yet." — with the citation in
its `citations` field and no invented risk numbers (`rank: None`,
`hazards_checked: []`).

`app.py`: `split_options()` and the `/post-flood` cascade loop now skip
the `aman_rice` note (it is not one of app.py's `CROP_NAMES` crops and
carries no risk numbers, so it is not rendered through the per-crop
contract shape yet — a follow-up task, not this one). `crop_option()`'s
sowing-window display dates now use the `season` `rotation_options()`
actually used, so a rolled-over rabi season shows the correct year.
`ALL_WINDOWS_PASSED`'s text and trigger condition (`/advisory` and
`/post-flood`) were updated to fire only when every crop is truly
unavailable (every option's `sowing_date` is `None`), since a rolled-over
season almost always has *something* available now.

New pytest coverage in `src/compute/test_risk_calendar.py`: the Sylhet
2022 rollover case (every rabi crop gets a real sowing date, none
`window_passed`, ranking unchanged from the equivalent November case);
the aman_rice option's exact text and citation; a normal November harvest
date behaves exactly as before (no rollover, no aman option).
`python -m pytest src -q`: 276 passed, 5 skipped (3 new tests).

## Data sources
All NASA/scientific data used is from NASA POWER, NASA GPM IMERG (via
Giovanni), NASA SMAP (via AppEEARS), OPERA DSWx-S1 (via NASA CMR/earthaccess),
BMD station normals, and FAO-56 (Allen et al., 1998) reference values — see
README and inline docstrings in `src/compute/agroclimate.py` for exact
citations per number.
## Review log

- **External review by a second Claude session** of the agent-layer code
  (tools.json, tool_functions.py, backtest_rotation). It found: cite_check
  exposed as a model-callable tool (moved inside guard(), so the check
  can't be skipped); analog_year being ignored by backtest_rotation(); a
  missing result key on empty results; misspelled crops silently dropped;
  and empty 0-of-0 results for pre-2015 analog years. Each fix was checked
  before being applied, and one proposed fix was changed (it would have
  broken rotations that cross into the next year).
- **Real-data checks with Claude** then found further issues: inconsistent
  column names across district files, a stale Sylhet file, and the
  whole-year soil-moisture ranking penalizing every dry-season crop. That
  ranking was replaced with a seasonal percentile, validated against
  independent POWER rainfall (scripts/check_smap_years.py).

**Claude Code (task 10b)** — wrote `Dockerfile`, `.dockerignore`, and
`scripts/deploy_hf_space.py` (huggingface_hub upload script) to deploy
`app.py` to a Hugging Face Space. Running the deploy script surfaced that
HF now requires a PRO subscription to create a Docker-SDK Space even on
free `cpu-basic` hardware (`402 Payment Required` on a plain free
account) — per CLAUDE.md's free-tiers-only rule, this was reported instead
of proceeding on a paid tier. Asked, the user chose to redeploy on
Render's free tier instead. Wrote `render.yaml` (Docker runtime,
`plan: free`) reusing the same Dockerfile, and changed the Dockerfile's
`CMD` to read `$PORT` (falling back to 7860) so the same image works on
both Render (which assigns `PORT`) and a future HF Space. Neither the
Render MCP connector nor a `RENDER_API_KEY` was available in this
session, so the actual deploy (creating the service, polling the live
URL, timing the three test calls) is left for the user or a follow-up
session — see the "Hosted API" section of README.md. Verified locally
instead: `python -m pytest src -q` (276 passed, 5 skipped) and
`uvicorn app:app` serving `/api/v1/districts`, `/api/v1/advisory` and
`/api/v1/post-flood` with 200 responses.

**Claude Code (task 12)** — connected the prototype website (`web/app/`)
to the API. In `web/app/index.html` it removed the hard-coded sample data
(crop, plan, flood and source constants) and the in-browser ranking
(`scorePlan` etc.) and rewrote the data layer so every number shown comes
from `/advisory`, `/post-flood`, `/field-twin` or `/districts`, each with a
source link to the response's provenance. It kept the look, screens,
animations, EN/Bangla, voice and navigation; added the source-mode badge,
notices, errors in the chosen language, a "waking up the server" state with
retry, and localStorage "offline copies". API text is read aloud with the
phone's Bangla voice when there is no recorded clip. It wrote
`web/app/config.js`, removed the direct NASA GIBS map layer, and marked
water access, priorities and soil as "coming soon". On the backend it added
optional `lat`/`lon` (nearest district within 60 km), `problem_line`,
`aman_option`, the SMAP recovery curve (`post_flood.smap_recovery_curve()`,
with tests), flood images via `GET /api/v1/images/{name}`, per-week twin
events, and `GET /` → `/docs`; added a Render static site to `render.yaml`
and copied the images into the Docker image. Checked with
`python -m pytest src -q` and in a browser against a local uvicorn, the
mock files and the live API. Bangla strings were written with AI help and
need a review by a Bangla speaker.

**Claude Code (task 14, back button)** — navigation only, in
`web/app/index.html`: every screen change in `go()` is now a browser-history
entry (`history.pushState({screen, depth}, "", "#" + screen)`, not pushed
when the screen did not change); a "‹ Back" / "‹ ফিরে যান" button (44 px)
at the left of the header calls `history.back()` and is hidden on the start
screen and when there is nothing to go back to; the phone/browser back
button (`popstate`) closes any modal, stops speech and shows the saved
screen via `go(s, {fromHistory: true})`; opening the site with a hash
(`#flood`, also `#plans` → crop, `#farm` → prev) opens that screen as the
first entry (`history.replaceState`). On phones up to 460 px wide the
"Survey Crops" words are hidden while Back shows so the header fits. No
data, API calls or numbers changed. Checked in a browser against a local
uvicorn: start → field → farm → plans → twin, then Back ×4 with the button
and with the browser back button, a reload on `#plans`, and the header at
375 px in Bangla. The Bangla label needs a review by a Bangla speaker.

**Claude Code (task 13, source links)** — made every "Source" card open a
real page. In `app.py` the IMERG, POWER, SMAP and OPERA provenance entries
got an optional `view_url` ("See the satellite data"): NASA Worldview over
the 5 districts with GIBS layers it confirmed in the WMTS GetCapabilities
(`IMERG_Precipitation_Rate` 2024-08-21, `SMAP_L4_Analyzed_Root_Zone_Soil_Moisture`
2024-08-25, `OPERA_L3_Dynamic_Surface_Water_Extent-Sentinel-1` 2024-08-28),
and the POWER Data Access Viewer. SMAP's `url` now points to the NSIDC page
for SPL4SMGP version 8 (AppEEARS moved to the note). It added
`public_url()`, so research rows whose `source_url` is not a web address
are sent with `url: ""` and a "Link pending" note (no URLs were invented
and the CSVs were not edited). It updated `srcCard` in
`web/app/index.html` ("Dataset page ↗", "See the satellite data ↗", "Link
pending"), wrote `scripts/check_links.py` (writes `docs/results/link_check.md`
and `docs/results/broken_source_links.md`), and added tests in
`src/api/test_app.py`. Checked with `python -m pytest src -q`, the link
check, and in a browser against a local uvicorn. The Bangla link labels
need a review by a Bangla speaker.

**Claude Code (task 15, rename to Survey Crops)** — replaced "CropShift"
with "Survey Crops" (Bangla: "সার্ভে ক্রপস") in every user-visible string
in `web/app/index.html` and in the text `app.py` returns (error messages,
notices, method/basis text, provenance dataset names, `sms_en`/`sms_bn`,
the FastAPI title). Comments, file names, identifiers and URLs were not
changed, and neither were the shared `web/mock/*.json` files (they need
their own PR). The 6th bottom tab is now "My plan" / "আমার পরিকল্পনা" (the
icon and "Pictures only" switch are unchanged). Compared the recorded
Bangla sentences before and after with the page's own `__collectBn()`
helper: none of the 61 recorded sentences changed, so no clip falls back
to the phone voice. Added tests that no API response contains "CropShift"
and that the error text and API title use the new name. Checked with
`python -m pytest src -q` and in a browser (Bangla tab bar at 375 px).
The Bangla wording needs a review by a Bangla speaker.

**Claude Code (task 16, Survey Crops name + assumptions doc)** — the
registered team name is now "Survey Crops" (it was "Team Regolith"). Replaced
the team name in `app.py` (agency fields), `CLAUDE.md`, `CONTRIBUTING.md` and
`scripts/deploy_hf_space.py`; member names, URLs, the repo name, git history
and the shared `web/mock/*.json` were not touched (the mock needs its own
PR). Past entries in this file are history and keep the old name. Added a
`why` line to every entry of `ASSUMPTIONS` (`src/compute/risk_calendar.py`)
and `API_ASSUMPTIONS` (`app.py`), wrote `scripts/build_assumptions_doc.py`
which generates `docs/assumptions.md` from them, and added
`src/api/test_assumptions_doc.py`, which fails if the doc is stale. The
"assumptions" provenance entry in `app.py` now links to that doc. Checked
with `python -m pytest src -q`. The `why` sentences are the AI's wording of
the reasons; the team should check them.

**Claude Code (task 17, mock team name)** — changed one string in
`web/mock/advisory.json` ("Team Regolith analysis of NASA POWER" -> "Survey
Crops analysis of NASA POWER") to match the registered team name. Checked
with `python -m pytest src -q`.

**Claude Code (task 17 follow-up)** — resolved the `docs/AI_USE.md` merge
conflict with main (kept both entries). Made
`src/api/test_assumptions_doc.py` read `docs/assumptions.md` with universal
newlines, so the stale-doc check does not fail on Windows CRLF checkouts.

**Claude Code (water question)** — made "How much water can you give?" real.
`src/compute/risk_calendar.py` now counts waterings per season from the same
FAO-56 balance as `irrigation_mm` (new `irrigation_events_mean` and
`irrigation_events_worst20` in `data/processed/risk_calendar.csv`; for boro
rice, land preparation counts as one watering plus each pond top-up; new
`irrigation_event_count` assumption, `docs/assumptions.md` regenerated).
`app.py` `/api/v1/advisory` takes an optional `water` (`rain_only`, `limited`,
`regular`, `plenty`; absent = today's result), documented in
`docs/api_contract.md`. `web/app/index.html` sends `water` once the farmer
answers and drops the "coming soon" pill from that question only. The two
new calendar columns were merged into the committed CSV; a full rebuild
would also change mustard and boro rows because newer reference data exists,
so that refresh is left for its own PR. The `limited` cut-off (at most 2
waterings in the worst 20% of years) is the user's rule, not a sourced value.
Checked with `python -m pytest src -q` and by driving the page against a
local API.

## Task: "What matters most to you?" made real (`priority` on /advisory)

Claude (Sonnet 5.5) wrote `check_priority`, `legume_crops`, `apply_priority` and
`ranked_by_block` in `app.py`, the `data.ranked_by` block, the caution and
"research pending: legume source" notices, the narration sentence, the
`priority` section of `docs/api_contract.md`, the website change in
`web/app/index.html` (sends `priority` in tap order, shows the "Ranked by"
line, removes "coming soon" from that question only, and starts with no
priority selected instead of a pre-ticked placeholder), the `_TEMPLATE.csv`
example row for `<crop>.soil.legume`, and the tests in `src/api/test_app.py`.
The ranking keys are the user's rules; no new numbers or reference values
were invented. There are no `soil.legume` rows yet, so the soil priority does
nothing until the team adds a cited row. Checked with `python -m pytest src -q`
and by driving the page against a local API.

## Task: "Your soil" made real (`/api/v1/soil`, ISRIC SoilGrids)

Claude (Sonnet 5.5) wrote `src/acquire/soilgrids_point.py` (one SoilGrids call,
0-30 cm depth-weighting, USDA texture via the existing `usda_texture`, disk
cache), the `/api/v1/soil` endpoint, the `soilgrids` provenance entry and the
district fallback in `app.py`, `web/mock/soil.json`, the `docs/api_contract.md`
section, the Farm screen soil box in `web/app/index.html` (texture, pH, organic
carbon with Source buttons, field record shown next to the estimate, "coming
soon" removed from that question only), and `src/api/test_soil.py` (SoilGrids
mocked; no test uses the network). The ranking is unchanged: field soil is
shown only. The SoilGrids layer names, units (g/kg, pH x10, dg/kg) and the 5
requests/minute limit were checked against the live API, which answered on
2026-10-10. Checked with `python -m pytest src -q` and by driving the page
against a local API.

## Task: Session A, partition the repo and fix the Field Twin heat flag (T0)

Claude (Sonnet 5.5) wrote `docs/ARCHITECTURE_MAP.md`, `docs/PROJECT_STATE.md`, the
`MODULE*.md` files next to each feature area, `src/compute/common/` (a
`Provenance` dataclass and `measured()`), `scripts/check_module_docs.py`, the
tests in `tests/common/` and `tests/docs/`, and the working-rules section of
`CLAUDE.md`. In `app.py` it changed `twin_heat_limits`, `twin_week_events` and
added `twin_stage_days`, so each crop stage in the Field Twin replay is judged
against its own cited limit (wheat grain fill now uses 35.4 C, not the 31 C
flowering limit). The failing test (`src/api/test_field_twin_stage.py`) was
written first. No new numbers or thresholds were added: the limits are the
existing `data/reference/crop_thresholds.csv` rows. Checked with
`python -m pytest src tests -q` and `python scripts/check_module_docs.py`.

## Task: T1 full-year rotation engine (`src/compute/rotation/`)

Claude (Sonnet 5.5) wrote `src/compute/rotation/` (`core.py`, `context.py`,
`crop_table.py`, `MODULE.md`), `data/reference/crops.csv`, the tests in
`tests/rotation/` and one small public function in `src/compute/risk_calendar.py`
(`season_row`, a wrapper of two existing functions; `crop_calendar` is unchanged).
The acceptance tests were written first. Every filled cell of `crops.csv` was
copied from an existing cited row in `data/reference/` or `data/processed/kc_table.csv`
and points at it in a `*_src` column; cells with no source in the repo (legume
flag, FAO-29 salt values, turnaround source, Kharif-1 crop) were left blank and
listed under "Open questions" in `docs/PROJECT_STATE.md`. No new threshold or
citation was invented. Checked with `python -m pytest src tests -q` and
`python scripts/check_module_docs.py`.

## Task: T2 farmer priorities (`src/compute/priorities/`, `POST /api/v1/rotation/rank`)

Claude (Sonnet 5.5) wrote `src/compute/priorities/` (`core.py`, `MODULE.md`), the
endpoint in `app.py`, `web/mock/rotation_rank.json` (a real response, marked as
an example), the tests in `tests/priorities/` and `src/api/test_rotation_rank.py`,
and a small addition to `src/compute/rotation/core.py` (`problem_years_by_hazard`
in the summary and `hazards_hit` per year, needed for the flood-related share).
The tests were written first. No new number, threshold or citation was invented:
every raw value is a rotation-module measure with its provenance, and the
weights are the farmer's. Checked with `python -m pytest src tests -q` and
`python scripts/check_module_docs.py`.

## Task: fixups-after-t2 (review fixes for Session A, T1, T2)

Claude (Sonnet 5.5) changed `src/agents/guard.py` (accepts `source_url`) and its
tests, added value-level and contract tests (`src/api/test_field_twin_stage.py`,
`src/api/test_app.py`), changed `src/compute/priorities/core.py` (unknown legume
flag is unranked; `how_to_include` hints) with tests, corrected the Aman wording in
`src/compute/rotation/core.py` and `MODULE.md`, rewrote the top of `CLAUDE.md`,
and filled `is_legume` in `data/reference/crops.csv`. The legume flags come from
Wikipedia species pages opened in this session (each URL is in `legume_src`); no
other number, threshold or citation was added, and no threshold was changed (the
mustard heat check only read existing values). Checked with
`python -m pytest src tests -q` and `python scripts/check_module_docs.py`.

## Task: T3a OPERA water stacks (`src/compute/field_profile/`)

Claude (Sonnet 5.5) wrote `src/compute/field_profile/` (`core.py`, `access.py`, `MODULE.md`),
`scripts/build_water_stacks.py`, `scripts/write_coverage_report.py`,
`scripts/make_field_profile_fixture.py`, the tests in `tests/field_profile/`, the real
50 x 50 Feni fixture, `data/reference/opera_classes.csv` and the coverage report. The tests were
written first. Class codes were read from the OPERA product specifications (HLS D-107395 Rev B,
S1 D-108761 Rev A, Table 4-1) and cited per row; the one choice not in the specs (HAND-masked =
not water) is flagged in the CSV and PROJECT_STATE. Credentials were read from `.env` only
and never printed. Checked with `python -m pytest src tests -q` and
`python scripts/check_module_docs.py`.

## Task: T3b field water profile (`src/compute/field_profile/`)

Claude (Sonnet 5.5) wrote `events.py`, `profile.py`, `hf.py`, the changes to `core.py` and
`access.py`, the scripts that build class stacks and layers, `tests/field_profile/test_events.py`
and `test_layers_api.py`, and the rules file `data/reference/field_profile_rules.csv`. The rule
values are project choices, flagged as such in the CSV. Checked with `python -m pytest src tests -q`
and `python scripts/check_module_docs.py`.

## Task: W1a district boundaries, common grid, POWER + IMERG for 64 districts

Claude (Sonnet 5.5) wrote `src/compute/district_grid/` (grid, boundaries, features), `src/acquire/imerg_subset.py`
and `power_points.py`, `src/compute/common/proj_guard.py`, the root `conftest.py`, the scripts
`fetch_imerg_bgd.py`, `fetch_power64.py`, `build_boundaries.py`, `build_district_features.py`, `_proj.py`, the
tests in `tests/district_grid/`, `src/acquire/test_*` and `src/compute/common/test_proj_guard.py`, and
`docs/harmonisation.md`. The tests were written first. The boundary licence was read from the geoBoundaries
API (`boundaryLicense`) and recorded in the GeoJSON; the district slug spellings and the three season windows
are project choices (flagged in PROJECT_STATE). Credentials were read from `.env` only and never printed.
Checked with `python -m pytest src tests -q` and `python scripts/check_module_docs.py`.

## Task: W1b Earthdata downloads (Colab) for SMAP, MODIS, NASADEM, GRACE-FO, HLS, ECOSTRESS, GEDI

Claude (Sonnet 5.5) wrote `src/acquire/w1b/` (products, appeears, convert, tables, dem + MODULE.md + test_w1b.py),
`src/compute/district_grid/regrid.py` with `tests/district_grid/test_regrid.py`, `scripts/pack_w1b.py` and the
Colab notebook `notebooks/w1b_earthdata_colab.ipynb`. The tests were written against hand calculations. Product
IDs, layer names, fill values, scale factors and start dates were read from the public AppEEARS product API and
NASA CMR (no login); source links were opened and returned 200. Claude had no Earthdata login and entered no
credentials: the user types them into the notebook (hidden box, not saved). The notebook cells were run only on
synthetic files shaped like the real ones; the real downloads have not been run. Three quality-mask rules
(MODIS pixel_reliability, HLS Fmask bits, GEDI unit) are recalled from product guides and listed as open
questions in PROJECT_STATE.

## Task: W2 indicators, homogeneity check, satellite vs ground check

Claude (Sonnet 5.5) wrote `src/compute/indicators/` (core, thresholds, trend, ground, build, explain + MODULE.md),
`tests/indicators/` (four test files, expected values counted by hand in the test comments), `scripts/build_indicators.py`,
`scripts/build_w2_reports.py`, and the generated tables and reports. Thresholds come only from cited rows already in
`data/reference/crop_thresholds.csv`; the ETCCDI index definitions (R20mm, Rx1day, CDD) were opened and read on 10 Nov.
No threshold or citation was invented. Claude's findings (IMERG reading low against BMD normals; the residual-Pettitt rule
missing the POWER step) are reported as found, with the caveats, in `docs/results/w2_*.md`. Nothing committed.

## Task: W1b results added (NASADEM, GRACE-FO), 11 Nov

Tanha ran the Colab cells and downloaded the files; Claude (Sonnet 5.5) copied them to `data/processed/`, checked them
(row counts, missing values, value ranges, size of files, cell sharing, date gaps), wrote
`scripts/build_w1b_columns.py` and `tests/district_grid/test_w1b_outputs.py`, and recorded the caveats in
`docs/harmonisation.md`. No value was changed or filled. The GRACE-FO unit (cm) was not read from the file's own
attributes: it is inferred from the product and the value range, and said so in the caveats.

## Task: W1b intake (MODIS, HLS, ECOSTRESS; status table), 11 Nov

Claude (Sonnet 5.5) wrote `src/compute/sat_layers/` (provenance, loaders, status, intake, MODULE.md),
`scripts/build_w1b_intake.py` and `tests/sat_layers/`. Each delivered file was checked before it was accepted;
the numbers come from the files, not from memory. The ECOSTRESS documentation was read through a subagent that
opened the NASA catalogue page (the PDF user guide and ATBD could not be decoded, so the cloud-code meaning is
unconfirmed). Claude found that its own earlier ECOSTRESS unit conversion in the Colab notebook is probably wrong and
marked the series "unverified units/mask" instead of using it. No credentials were used or stored. Checked with
`python -m pytest src tests -q` and `python scripts/check_module_docs.py`.

## Task: W1b status wiring, ECOSTRESS findings, MODIS 2017 (11 Nov)

Claude (Sonnet 5.5) recorded Tanha's ECOSTRESS findings (units unresolved, cloud mask supported by one scene) exactly
as supplied; those numbers come from Tanha's Colab run and were not re-run. It wrote `src/compute/indicators/layer_status.py`
and `tests/indicators/test_layer_status.py` (tests first), changed `indicators/build.py`, `explain.py`,
`scripts/build_indicators.py` and the text of `scripts/build_w2_reports.py` so W2 reads `docs/w1b_data_status.csv`, regenerated
`data/processed/indicators_*` and `docs/results/w2_homogeneity.md`, and accepted `modis_district_2017.csv.gz` after the
same checks as the other years. The GRACE-FO trend reuses the existing Theil-Sen, Kendall and Pettitt test. No unit was
assumed and no credential was used.

## Task: W2 extra indicators (heavy-rain days, Tmin cold limits, POWER temperature vs BMD)

Claude (Sonnet 5.5) wrote `src/compute/indicators/{heavy_rain,cold_limits}.py`, the temperature functions in
`ground.py`, `load_crop_params_report` in `water_balance.py`, test files/blocks written first with hand-counted
values, `scripts/list_skipped_reference_rows.py`, the temperature-check part of `scripts/build_w2_reports.py`, and the
regenerated tables and reports. Every limit comes from a row in data/reference (source title, link and page are in
the handoff); no value, threshold or citation was invented. Judgment calls Claude made and flagged: reading the heavy-rain
row from the file because the strict loader rejects its item name; accepting only a plain number or "below N" for cold
limits; counting a row as Tmin only if its item or unit says so. Nothing was committed or pushed.

## Task: W3, the three SI comparisons with model cards

Claude (Fable) wrote `src/ml/si_models/` (validation, features, stress, season_types, transitions, report),
`scripts/build_w3_models.py`, the 55 tests in `tests/si_models/` with hand-worked fixtures, the six model cards
(generated by the script), `data/reference/w3_known_events.csv`, and this round of PROJECT_STATE/handoff updates.
Claude also ran the web searches and page fetches for the known-event sources; only events whose source page was
actually read were cited (2 of 6 candidates), the rest are GAP rows with the candidate URLs. Judgment calls Claude
made and flagged in the outputs: z-limit 2, the top-20% season-type cut, the four-month transition search windows,
the >= 4 composites rule for an NDVI season mean, the >= 50% dates-found rule for a method to count as assessed,
and deriving green-up reference windows from cited sowing windows plus cited seedling ages. No threshold, event or
citation was invented; models are scikit-learn (Isolation Forest, k-means) with fixed seeds; no AI/LLM calls in the
code. Nothing was committed until tests passed.

## Task: W4, rotation strategy exploration

Claude (Fable) wrote `src/compute/strategies/` (core, indicators, facts, cards, matrix), the 56 tests in
`tests/strategies/` with hand-counted fixtures written first (bare-field days 130 of 365, bootstrap edge cases,
nine synthetic slope districts, the erosion product), the MODULE.md, the section-10 endpoint proposal in
`docs/contract_change_proposals.md`, and this round of PROJECT_STATE/handoff updates. Every fact comes from a row
in data/reference or a computed measure with provenance; no value, threshold or citation was invented. Judgment
calls Claude made and flagged in the outputs: reimplementing the W3 bootstrap with numpy only (same seed, count
and level) so Layer 1 never imports src/ml; reading `crop_family.csv` and `forage.csv` raw with a source-URL check
because the strict loader skips every row of both (noted in each provenance note and in Open questions); slope
terciles across the 64 districts as our choice, relative ranking only; erosion exposure as a relative product, not
USLE; income shown as a cited market price (BDT/kg), never income per hectare. The cards are deterministic
templates and the words "predict" and "forecast" never appear (tested). No AI/LLM imports in src/compute; no
credential was used. Nothing was committed until the full suite passed.

## Task: W3 events update (13 Nov 2026)

Claude (Sonnet 5.5) installed the research teammate's updated `data/reference/w3_known_events.csv` unchanged (no row
written or edited by Claude), added `stress.event_summary` and its test, made `scripts/build_w3_models.py` report events
outside 2001-2024 as "not scored" instead of counting them, re-ran the build script, and updated the two stress model
cards, `docs/results/w3_metrics.json`, the W3 handoff and PROJECT_STATE. No threshold, event or citation was invented;
no AI/LLM calls in the code. Nothing was committed until tests passed.

## Task: W4 soil pH and organic carbon (13 Nov 2026)

Claude (Sonnet 5.5) wrote `src/acquire/soilgrids_ph_oc.py`, `scripts/fetch_soil_ph_oc.py`, `src/compute/soil_chem/`, the tests in `tests/soil_chem/` and `tests/strategies/test_soil_wiring.py` (hand-counted fixtures written first, including a d_factor 100 case so the unit conversion cannot be hard-coded), the wiring in `strategies/core.py` and `cards.py`, and the docs. The licence (CC BY 4.0), the no-key access and the 5-calls-per-minute fair use come from the ISRIC docs pages (read by a subagent; the REST docs page itself and the data-policy PDF could not be read, so no-key access was confirmed by calling the service). pH x10 and dg/kg come from the service's own `unit_measure` metadata. The data fetch was run once by Claude (7 calls, no key); no value was invented, interpolated or moved to a neighbouring cell. No AI/LLM calls in the code. Nothing was committed until tests passed.
## W5 map (12 Nov 2026, branch w5-map)
Claude (Sonnet 5.5) wrote `src/compute/map_layers/` (layers, outlines, scenario, passport), the 40 tests in
`tests/map_layers/` (written first; hand-counted heat days, slider at 0/0 equal to the Layer 1 water balance,
gap years None not 0), `src/api/map_routes.py` with its 17 tests, `web/app/map.html`, the MODULE.md, the
section-11 proposal in `docs/contract_change_proposals.md`, the handoff and the PROJECT_STATE update. The
geoBoundaries licence was re-checked against its public API (no personal data sent). Judgment calls flagged in the
outputs: MODIS 12-composite and SMAP 300-day rules, scenario simplifications (humidity unchanged, whole-season heat
counts), vulnerability zones not built because no cited thresholds exist, lazy imports in `district_grid/__init__.py`
so the deployed API does not need shapely. No AI/LLM imports in src/compute; no credential used; nothing costs money.

## W5 follow-up: shapely proof and relative zones (12 Nov 2026, branch w5-vulnerability)
Claude (Sonnet 5.5) wrote `tests/api_deploy/` (a fresh-interpreter probe that blocks shapely, and shapely plus
rasterio, records every import attempt with its repo frames, and calls every route in `app.py` and
`map_routes.py`), `src/compute/map_layers/zones.py`, the tests in `tests/map_layers/test_zones.py` (hand-built 4x4
grids, written first), the passport wiring, a fix so a missing rasterio no longer gives a 500 in the passport, the
zone rendering in `web/app/map.html`, the section-12 proposal, MODULE.md, the handoff and PROJECT_STATE. Judgment
calls flagged in the outputs: the tercile cuts and the "at least one day" rule (ours, labelled as relative rankings),
nearest-pixel re-sampling for the overlap. No AI/LLM imports in src/compute; no credential used; nothing costs money.
The map page was not opened in a browser (the pane was hidden): its script was syntax-checked and the API fields it reads are tested.

## 13 Nov 2026: modes.html API client (web-sync-modes, Task 3)
Claude Code wrote `web/config.js` (server address, `?api=` override), `web/api-client.js` (60 s timeout, one retry, saved-sample fallback, per-endpoint log) and the small wiring in `web/modes.html` (status banner, English and Bangla strings, per-screen DEMO badge switch). The Bangla strings are AI-written and need native review. No number is computed in the page; the saved samples in `web/mock/live/` are real server answers.

Same day (web-sync-modes): Claude Code added the exact harvest-date question and the "Get my plan from the server" card on the Farm page of `web/modes.html` (the farmer's dates, water and priority answers are sent to `/post-flood` and `/advisory`; the page only shows the answer). Bangla strings are AI-written and need native review.

Same day (web-sync-modes, Task 4 step 1): Claude Code wrote `web/adapters/advisory.js` (renames and tidies the `/advisory` answer, no maths) and rebuilt the Rotation page in `web/modes.html` from it. The page's own ranking and sowing-date code (`ranked`, `sowFor`-driven cards, `compareTable`, `stratCard`) was removed from that page; the server's ranking, dates and numbers are shown, each with a Source button that lists the server's provenance. Bangla strings are AI-written and need native review.

Same day (web-sync-modes, Task 4 step 2, flood): Claude Code wrote `web/adapters/postflood.js` and the flood section of `web/modes.html` (Issues page card and the compact box on the Farm page), drawn from `/api/v1/post-flood`: earliest sowing date, radar pictures via `/images/{name}`, water-on-ground and soil-recovery charts (plotting the server's rows, with the server's own marker dates), sensitivity table, crops still possible, the flood cascade, notices and a Source button per number. The page's own "ready date" maths was removed from these two places. Bangla strings are AI-written and need native review.

Same day (web-sync-modes, Task 4 step 3, plan): Claude Code rebuilt the Plan page, the SMS text, the "raw JSON" button and the sowing-date tile on the Pictures page of `web/modes.html` from the server's option for the chosen crop (`/advisory`, plus `/post-flood` when the farmer reported a flood), with a Source button per number and an Officer provenance table built from the server's provenance list. The old demo data (`NEXT`) and its page-side ranking and date code were deleted. The SMS refuses to copy saved-sample numbers. Bangla strings are AI-written and need native review.

Same day (web-sync-modes, Twin page redesign): Claude Code rebuilt the Twin page as a field dashboard (`web/pages/twin.js`, adapters `web/adapters/twin.js`, `soil.js`, `passport.js`, `scenario.js`) after the team's reference screenshots: satellite map with 30 m terrain cells and round layer buttons, soil tiles, a past-season replay with a week scrubber and charts (soil water, rain vs crop demand, temperature, crop stage and weather flags), and a "what if" panel (rain and temperature sliders over past seasons). Everything shown comes from `/field-twin`, `/soil`, `/map/passport` and `/map/scenario`; the page only plots the server's numbers. Labelled as past seasons, never a forecast. No 3D moisture surface, light layer or invented data. Bangla strings are AI-written and need native review.

Same day (web-sync-modes, Task 4 step 5, risk calendar): Claude Code wrote `web/adapters/riskcal.js` and `web/pages/risk.js`, a "When is sowing risky?" card on the Issues page from `/api/v1/risk-calendar`: a crop picker, the cited sowing window, a colour grid of past-season problem counts per hazard and sowing date (grey = not assessed, never 0), water need per sowing date, the "other ways of counting" table for officers, the server's narration with its wording-check result, and a Source button per block. The page computes nothing. Bangla strings are AI-written and need native review.

Same day (web-sync-modes, Task 4 step 6, warnings and El Nino context): Claude Code wrote `web/adapters/warnings.js`, `web/adapters/enso.js` and `web/pages/outlook.js`, two cards on the Issues page from `/api/v1/warnings` and `/api/v1/enso-lens`: the server's weather warnings (type, date, amount, limit, action) and the all-years vs El Nino-years table with the number of El Nino years, each with Source buttons. Both server answers are marked example data, so the DEMO badge and the server's "not built yet" notice stay on. The warnings narration is not shown and one server notice that used a banned word is replaced by a plain Open-Meteo line. The page computes nothing. Bangla strings are AI-written and need native review.

Same day (web-sync-modes, Task 5, data and evidence pages): Claude Code wrote `web/adapters/dataset.js`, `models.js`, `strategies.js` and `web/pages/data.js`, five new pages in `web/modes.html` from the server: `#/data` (every dataset with its status, reason, units, resolution and source link, plus the districts coverage table from `/districts`), `#/model` (held-out results from `/models` with each interval and n as returned, shown to 3 decimals with the full value on hover, the server's own method choice and caveats, and the model cards), `#/strategies` and `#/evidence` (from `/rotation/strategies`: problem years with the 95% range, Kc-weighted irrigation need, legume count, gaps shown as not assessed, a Source button per number), and `#/server` (officer: asks each endpoint once and shows ok, slow or failed, kind of answer and raw JSON). The rotation list for the picker comes from POST `/rotation/rank` with equal weights (only the names are used). Two saved samples were added to `web/mock/live` (data_sources, models). The page computes nothing. Not done: pictures-first strategy cards, a pest-cycle field from a dedicated backend field, map-layers card. Bangla strings are AI-written and need native review.

## 13 Nov 2026: strategies and model-metrics endpoints
Claude Code wrote `src/api/strategy_model_routes.py` (two read-only routes that wrap existing Layer 1 `build_strategies` and the W3 metrics file), its 7 tests in `src/api/test_strategy_model_routes.py`, the registration lines at the end of `app.py` and section 13 of `docs/contract_change_proposals.md`. No new numbers are created: the routes only pass through existing, cited outputs. No AI/LLM import in these routes; nothing costs money. Needs a human review before merge, and the web team's agreement (shared contract file).

Same day, same branch: Claude Code also wrote `src/api/data_routes.py` (read-only data/reference/disease-rules routes over the existing strict loader and status table), `src/api/test_data_routes.py` (9 tests), the Dockerfile and `.dockerignore` fix for the `/map/layers` 500, and section 14 of the contract proposals. It reproduced the 500 by copying only the Dockerfile's folders into a clean directory. No numbers are created; skipped rows are listed with their reason.

## 13 Nov 2026: voice lines for the newer pages (web-voice, Task 6)
Claude Code wrote `web/pages/voice.js` (seven short narration lines with a speaker button on the risk calendar, weather warnings, El Nino context, Data, Model, Strategies and Evidence), added the same lines to `web/audio/narration_manifest.json` (now 52 clips, 6,210 characters in both languages), added `tests/test_voice_manifest.py` (page lines match the manifest; no banned wording), and kept `notebooks/make_voice.py`, which reads the ElevenLabs key from a Colab secret or an environment variable and never from the site or git. A missing recording now shows "Voice file not added yet" in both languages; the phone robot voice is not used for these clips. No audio was generated yet. The lines contain no numbers. The Bangla lines are AI-written and need native review, and a native speaker must also check the finished audio.

## 13 Nov 2026: vercel.json for modes.html
Claude Code added `web/vercel.json` (one rewrite: `/` opens `modes.html`). It only applies to a Vercel project whose Root Directory is `web`; the existing project (Root Directory `web/app`) ignores it. No code or data changed.

## 13 Nov 2026: officer explanations and the (i) Sources page (web-officer-notes)
Claude Code fixed the (i) page (it was empty because the old source list had been removed): `web/pages/officer.js` now lists every source the server names in any real answer (`CS_API.prov()` in `web/api-client.js`), with period, resolution, note, dataset link and the "see the satellite data" link, and a search box. It also adds the server's "In short" sentence with its wording-check result and the "district for your location" line on Rotation and Flood, a "Your soil" card on the Farm page (texture, pH, organic carbon, notices, from `/soil`), a NASA Worldview link centred on the farmer's field, and fixes the Server status check that sent no harvest date. The page computes nothing. Bangla strings are AI-written and need native review.

## 13 Nov 2026: real weather warnings (api-weather-warnings)
Claude Code built `GET /api/v1/warnings`: `src/acquire/open_meteo.py` (Open-Meteo, live then cache then fixture), `src/compute/weather_warnings/` (pure comparison with thresholds read from `data/reference/` rows that have a source), `src/api/warnings_routes.py`, tests, five small fixtures fetched from Open-Meteo on 13 Nov, `Dockerfile` / `.dockerignore` (ship `demo_fixtures/`), `web/mock/live/warnings.json` (a real answer), docs. The action texts (English and Bangla) are AI-written, have no source, and need native review. No threshold was invented; unsourced ones are skipped and listed in PROJECT_STATE open questions.

## 13 Nov 2026: mustard flowering timing (data-flowering-timing)
Claude Code replaced one placeholder row in `data/reference/crop_calendar.csv` (`mustard.stage.days_to_flowering` = `37-44`, BARI Annual Research Report 2024-2025 p. 156; the file is owned by the research teammate), rebuilt `data/processed/risk_calendar.csv` and `docs/results/risk_calendar.md` with `scripts/build_risk_calendar.py`, added three tests to `src/compute/test_risk_calendar.py`, changed one assertion in `src/api/test_app.py` (mustard is now fully checked) and listed the remaining placeholders in `docs/PROJECT_STATE.md`. No new numbers were invented; the Tmax limits (25-29 C) were already cited rows.

## 13 Nov 2026: disease weather risk (api-disease-risks)
Claude Code built `src/compute/disease_risk/` (counts the past seasons, 2001-2024, in which weather favourable for potato late blight occurred; wheat blast, lentil Stemphylium and the crops without a rule are "not assessed"), `src/api/disease_block.py`, the additive `disease_risks` field in `/api/v1/risk-calendar`, the `web/pages/risk.js` + `web/adapters/riskcal.js` + pest-card display, tests and docs. Tanha chose "potato only" after seeing which rows had sources. A human should check the Hyre 1954 rule reading (5-day mean temperature, 10 days in a row) against the paper.

## 13 Nov 2026: cited prices as fixtures (api-live-prices)
Claude Code researched the three price sources (none was free, permitted and working for our crops), then, at Tanha's choice, built prices as saved fixtures: `src/compute/prices/` (month, type, market, exact unit conversion), `src/api/price_block.py` (`market_price` on `/advisory` options), the extra keys on the strategies `market_price`, `web/pages/price.js` and the card lines, tests and docs. Four teammate-supplied price rows were appended to `data/reference/prices.csv` (no rows changed or deleted). Nothing is fetched live.

## 13 Nov 2026: Twin layout, phone view and prices link (web-ui-fixes)
Claude Code (1) moved the what-if panel under the map on the Field Twin page so the two columns end close together (left 622 px vs right 2,169 px before, 1,476 vs 1,653 after); (2) added `web/pages/view.js`: a Phone button (wide screens only) that opens the same page in a 390 x 844 phone frame, copying language, mode and page, so desktop and phone layouts can both be shown; (3) added a button on the Rotation page to the Other-ways-to-rotate page, where the cited market prices are shown. No data or numbers changed. Bangla strings are AI-written and need native review.

## 13 Nov 2026: voice recordings (web-voice-audio)
The 104 narration clips in `web/audio/` (52 ids in `narration_manifest.json`, each in English and Bangla) are AI-generated speech made with ElevenLabs. Tanha generated them by hand (nothing in the repo calls ElevenLabs) with adult voices chosen by Tanha, on the **free plan**. The voice names are: TO BE FILLED IN BY TANHA. The Bangla clips need a native speaker's check before final submission, as the Bangla text itself is also AI-written. **Licence not verified:** free ElevenLabs plans may require credit and may not allow commercial use; the terms have not been read by Claude and must be checked by a person before the final submission. A credit line "Voice: ElevenLabs" is shown at the end of the Limits area on the (i) Sources page, in English and Bangla.

## 13 Nov 2026: Desktop | Phone switch (web-view-switch)
Claude Code replaced the single Phone button in web/pages/view.js with a Desktop | Phone switch that is always in the top bar (icons only on narrow screens). On a wide screen, Phone opens the same page in a 390 x 844 phone frame (a real phone-width window). On a phone, Desktop asks for the wide layout (viewport width 1100, remembered for the tab) and Phone switches back. No data or numbers changed. Bangla labels are AI-written and need native review.

## 13 Nov 2026: Twin page rows and prices on Rotation (web-twin-symmetric)
Claude Code rebuilt the Field Twin page as balanced rows: map beside the replay controls (equal height, the map fills its card), a full-width Season charts card (two charts across; three in Farmer mode with the last full width), then the what-if panel beside soil and season totals. Desktop columns are now equal (840 and 840 px, then 688 and 688) instead of 622 vs 2,169. Phone width stays one column. Also added a Market prices card at the top of the Rotation page (the server's cited price with month and Source button, a price not income) and made the past-prices gap line officer-only. No numbers are computed in the page. Bangla strings are AI-written and need native review.

## 13 Nov 2026: disease risk always visible (web-disease-visible)
Claude Code changed web/pages/risk.js so the pest card on the Issues page always shows the potato late-blight weather risk from /risk-calendar (disease_risks), whichever crop chip is selected (it previously showed only when the Potato chip was selected, and the default chip is Mustard). The Source buttons open the sources of that answer. Other crops say no sourced rule yet (officer view). The page only displays the server's count (7 of 24 past seasons) and never says the disease occurred. Bangla strings are AI-written and need native review.

## SoilGrids pH and organic carbon for masked points (api-soil-cache)
Claude Code (Sonnet 5.5) ported the unfinished `api-soil-cache` work from the old Crop-Shift repo: `src/acquire/soilgrids_point.py` (cache, saved fixture, background fetch, retries, cooldown), `src/acquire/soilgrids_neighbours.py` (when a point's own cell is masked, the median of valid neighbour cells: 8 cells at about 1 km, then about 2 km, at least 3 values, a failed call counts as no cell), the soil route notices in `app.py`, three test files, and a Source button on the Farm soil card (`web/pages/officer.js`). It rewrote `scripts/build_soil_fixture.py` to be fast and resumable (4 calls at a time, 1.5 s pause, saved after every point, 5-minute limit, stops on HTTP 429). The build ran once on 13 Nov 2026: ISRIC answered very slowly, so only the Cumilla point has a value in `demo_fixtures/soilgrids_points.json` (estimate from 3 cells within 2 km); Noakhali, Feni, Brahmanbaria and Sylhet are not in the file and use district soil. No value was invented or moved to a neighbour except through the labelled median. The estimate threshold (3 cells), the 1 km and 2 km rings and the wait budgets are our choices, not from a source. No AI/LLM imports in the code; nothing costs money.

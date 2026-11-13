# CLAUDE.md: Survey Crops rules for Claude Code (keep this file short; it loads every session)

Survey Crops (repo: CropShift) is our entry for NASA Space Apps 2026, Challenge 7, "Field Shift". Headline: **"A rotation planner that knows how *your* field floods and dries."** It helps farmers and agriculture officers (SAAOs) choose a year-round crop rotation for each field, using how the field floods and dries as seen by NASA satellites, plus its soil and the farmer's priorities. Event: 13-14 Nov 2026 (dry run 12 Nov, freeze 10-11 Nov). The plan, decisions and task list (T0-T20) are in `docs/innovation-decision-2026-10.md`; current status is in `docs/PROJECT_STATE.md` (read it first).

## Districts
- Live today: Cumilla, Feni, Brahmanbaria, Noakhali, Sylhet. Planned (Tanha confirmed 24 Oct 2026): Chattogram, Khulna, Rajshahi, Barishal, 9 in total (tasks T10a-d).
- Everywhere else: **basic mode**, NASA data only, labelled "basic, weather and soil-moisture only, not validated here" (T11).

## Online-first
- The app is online-first: live -> cache -> fixture fallback, in that order. Only the **backend** ever fetches live data (NASA POWER near-real-time, SMAP latest, OPERA DSWx latest scenes, Open-Meteo, NOAA ENSO, FIRMS); `web/` never calls out.
- Secrets (API keys, tokens) only via environment variables / HF Space secrets. Never hardcode, never commit.
- Cache is keyed per point per day, lives in `cache/` (gitignored). Demo fixtures live in `demo_fixtures/` and are kept in git so the demo works with no network.
- Every response that used `safe_fetch` reports `source_mode` (`"live"`, `"cache"`, or `"fixture"`) so the UI/agent can be honest about where a number came from.

## Working with Tanha (a beginner)
- Before acting, say in 2-3 plain sentences what you will do and why. After acting, say what changed and how to check it.
- Save tokens: read only the files a task needs; never print whole data CSVs (use `head` or pandas summaries); run tests with `-q`; keep answers short unless asked.
- One task per session. When a task is done and committed, tell Tanha to start a fresh session.

## What Survey Crops says (don't drift back to the old crop-and-date pitch)
- **Headline = the rotation planner.** Each candidate rotation (Aman then a rabi crop, etc.) is tested on 24 past seasons (2001-2024): "problems in X of N years", irrigation need in mm (Kc-weighted FAO-56 balance), legume count, flood exposure; then re-ranked by the farmer's priorities (save water / soil health / lowest risk / flood safety). The plan re-adjusts the day floodwater leaves. Flood features inside it: flood-tolerant variety matching, satellite damage map vs DAE figures, (if time) safest seedbed finder.
- The per-crop sowing-date risk calendar, the Field Twin (closest analog year) and El Nino context are supporting features, not the story. The closest analog year is an **example, never a forecast**, and is not used in the ranking. El Nino lens: all years vs El Nino years, always "context, not forecast", with n shown.
- **Never write "predict" or "forecast"** in user-facing text; use "past seasons show", "estimated", "tested on". Say "NASA data for the area around your field" for district-level numbers; "your field" only where a number really comes from that field (the 30 m field water profile, task T3).
- Where a rotation has no sourced hazard or water model, say "not assessed", never 0.

## Non-negotiable architecture
1. `src/compute/`: deterministic Python, pytest for every function, no AI calls.
2. `src/ml/`: a real model only, with honest held-out accuracy.
3. `src/agents/`: a free Hugging Face open model (never a paid API), a plain loop with a max of 6 steps, **`guard()` blocks any number not found in a tool result that carries a `dataset` and a link (`source_url`, or the older `url`)**, a template fallback, and never empty JSON.
4. `web/`: static; renders API JSON only; never computes; never calls NASA or HF.
5. Every shown number is cited. Free tiers only (if something costs money, stop and tell Tanha). Raw rasters never go in git. Apache-2.0.
6. **Never cut:** the analog backtest (Field Twin), the Kc-weighted water comparison, `guard()`, and the hindcast / honesty scorecard.

## Data facts
- `data/processed/`: POWER daily 1981-01-01 to 2026-08-31 (`rainfall_mm, temp_mean_c, temp_max_c, temp_min_c, rh_pct, wind_speed_ms, solar_rad_mj_m2`); IMERG daily rain 2001-01-01 to 2025-09-30 (`imerg_<district>_daily.csv`, cells in `imerg_cells.csv`); SMAP root-zone 2015-2026; `kc_table.csv`; `district_metadata.csv`.
- **Rain source = NASA GPM IMERG V07 Final Run** (0.1 deg). Always load weather with `load_weather(district)` (`src/compute/weather.py`): IMERG rain + POWER temperature/RH/wind/solar. POWER rain has step changes (~1997 and ~2014-15, `docs/results/rain_source_check.md`); never use it for recommendations, rankings or trends.
- **Feni and Noakhali share one POWER cell** (temperature etc.). With IMERG their rain comes from separate cells, but Noakhali is only ~1-4% wetter: don't headline a contrast.
- OPERA DSWx-S1 exists over Feni/Cumilla from 21 Aug 2024 only (true first date UNVERIFIED, see PROJECT_STATE open questions).
- Researched values: `data/reference/*.csv` with the columns `item,value,unit,source_title,source_url,page,year,notes` (`crops.csv` is a wide table with `*_src` columns). No source means no row.
- Primary window = seasons 2001-2024 (IMERG starts 2001; its Final Run ends 2025-09-30). POWER 1981-2025 is appendix-only.
- SMAP L4's rain forcing is corrected to IMERG, so model-vs-SMAP r is not independent evidence for IMERG.

## Task order (one per session, one branch, tests, then a PR)
The ordered list T0-T20 with owners is `docs/innovation-decision-2026-10.md` section 6.2; status per task is the table in `docs/PROJECT_STATE.md`. Build order: T0 > T1 (rotation engine) > T2 (priorities) > T3 (30 m field water profile) > T4 > T5 > T6 > T7 > T9 (+T9b) > T8 > T17 > T18 > T10a > T10b + T14 + T15 > T10c + T16 > T10d > T12 > T13 > T20 > T11 > T19 last. Cut order if late: section 6.3 of the same file (new add-ons first, last-in first-out: T11, T20, T13, T12, T10d, T16, T15, T14; then UI polish, ML sophistication, Sentinel-1 details, district count). Do not start a task out of order without asking Tanha. The old tasks 1-11 (guard, water balance, hindcast, risk calendar, post-flood, API, ...) are built; their code map is `docs/ARCHITECTURE_MAP.md`.

## Folders
- **Tanha:** `src/`, `tests/`, `data/processed/`, `app.py`, `scripts/`.
- **Teammates:** `web/` (not `web/mock/`), `data/reference/`, `docs/research/`.
- **Shared (both agree, in its own PR):** `docs/api_contract.md`, `web/mock/`, `CLAUDE.md`, `CONTRIBUTING.md`.

## Commands (Windows, venv active, from the repo root)
- Tests: `python -m pytest src tests -q` (takes ~3 minutes), then `python scripts/check_module_docs.py`.
- Before a commit: tests pass, check `git status`, **no staged file over 5 MB**, `docs/AI_USE.md` updated if AI wrote code.


## WORKING RULES FOR EVERY SESSION
(Added 24 Oct 2026. Where these differ from the older lines above, such as the 50 MB limit, these rules win.)

1. Layer 1 (src/compute) is pure deterministic Python, no AI/LLM imports ever, fully unit-tested. Layer 2 (src/ml) = real trained model with honest held-out metrics. Layer 3 (src/agents) = free Hugging Face model, plain state machine, hard step cap 6, guard() provenance check as CODE, and template fallback (never empty or broken JSON). Layer 4 (web/) only renders API responses.
2. Every number returned by the API carries provenance (dataset, source_url, retrieved, granule/file).
3. Never invent numbers, thresholds or citations. If a source cannot be verified, stop and add it to "Open questions" in PROJECT_STATE.md instead of guessing.
4. Raw rasters/scenes never go into git; fail if any file >5 MB is staged. Only small derived files go into data/processed/.
5. User-facing text never says "predict" or "forecast"; use "past seasons show", "estimated", "tested on".
6. One task per branch; all tests must pass before merging.
7. Every task ends with: self-review checklist, handoff report in docs/handoff/, updated PROJECT_STATE.md, updated MODULE.md for touched modules, updated docs/AI_USE.md.
8. New features go in their own module folder with MODULE.md and tests; files under ~400 lines.

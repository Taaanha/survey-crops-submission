# Handoff: real weather warnings (13 Nov 2026, branch api-weather-warnings, cut from origin/main)

## What was built
`GET /api/v1/warnings?district=` now returns `is_mock: false`. Open-Meteo's 7-day daily numbers (rain sum, Tmax, Tmin) for the district point are compared with thresholds read from `data/reference/` rows that have a source; nothing is hard-coded.
- `src/acquire/open_meteo.py`: fetch through `safe_fetch.fetch_json` (live, per-point per-day cache, fixture `demo_fixtures/openmeteo_<district>.json`), `source_mode` reported.
- `src/compute/weather_warnings/core.py`: pure, tested. Rules: heavy rain (BMD 44 mm/24 h, very heavy 88), heat at flowering (mustard 29, wheat 31, lentil 32, boro 35 C), cold night (BAMIS Tmin below 10 C for boro, mustard, potato).
- `src/api/warnings_routes.py`: the route, provenance (`om` + one entry per threshold row), notices (Open-Meteo is not NASA + attribution; saved-copy caution).
- Skipped for lack of a usable source (reported, never warned on): wheat cold (SUSPECT), Aman cold (placeholder). Wind, hail, fog: no rows exist. See Open questions in PROJECT_STATE.

## How to check
`python -m pytest tests/weather_warnings src/api/test_warnings_route.py -q` (20 tests), then `GET /api/v1/warnings?district=cumilla`. Turn the network off (or set `OFFLINE=1`) to see `source_mode: "fixture"` and the caution notice. On the Issues page, the card shows no DEMO badge.

## Still demo / honest limits
Crop stage is not checked (heat warnings are conditional). Action texts are our wording. Fixtures are real Open-Meteo answers from 13 Nov, so a fixture answer shows old dates and says so. The voice line for this page still says "example data".

## Not verified
Not opened in a browser on the deployed site (the API on Render is not redeployed yet); the adapter was run with node on the saved real answer. `tests/api_deploy/test_no_shapely.py::test_every_route_was_called_and_none_crashed` already fails on main (six routes from other tasks have no probe entry); not touched here.

## Self-review checklist
- [x] No "predict"/"forecast" in user-facing text (test); JSON key `forecast` kept, renamed by the adapter.
- [x] Every number has a dataset and source URL in `provenance[]`.
- [x] No threshold invented; unsourced skipped (tests).
- [x] Files under 400 lines; MODULE.md, AI_USE.md, PROJECT_STATE.md, contract proposal updated.
- [x] No raw rasters, no staged file over 5 MB, no secrets.

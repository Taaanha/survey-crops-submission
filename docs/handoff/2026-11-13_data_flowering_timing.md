# Handoff: mustard flowering timing (13 Nov 2026, branch data-flowering-timing)

## What was wrong
Mustard "heat at flowering" showed as "not assessed" on the risk calendar. The loader already ignored the placeholder row (`mustard.stage.days_to_flowering` = 45), but the cited `_low` row (37) was added on 11 Nov and `data/processed/risk_calendar.csv` (which `app.py` reads) had been built on 10 Oct, so it still listed `heat_flowering` as missing.

## What changed
- `data/reference/crop_calendar.csv` (research teammate's file, one row): placeholder replaced by `37-44` days, ANNUAL RESEARCH REPORT 2024-2025, page 156, quote "The variety required 37 to 44 days to reach 50% flowering variety BARI Sarisha-18". The `_low` = 37 row stays; the code merges both as one source.
- `data/processed/risk_calendar.csv` and `docs/results/risk_calendar.md` rebuilt (280 rows, about 80 s).
- `src/compute/test_risk_calendar.py`: 3 tests (range row accepted and placeholder skipped; real reference gives mustard flowering 37-44 with the BARI link and a live `heat_flowering`; committed calendar has counts for all 5 districts).
- `src/api/test_app.py`: mustard no longer expected to carry the "not all risks checked" notice.
- `docs/PROJECT_STATE.md` Open questions: every other placeholder and the source it needs.

## Result
Mustard `heat_flowering` has counts (not null) in Brahmanbaria, Cumilla, Feni, Noakhali and Sylhet (11 sowing dates each). Flowering is now taken as the midpoint 40.5 days (was 37) in the day-degree method, median 44.5-45.5 days after sowing. Limit used: `mustard.heat.flowering_tmax_low/high` = 25 / 29 C on daily maximum temperature; the onset end (25 C) is used for the headline, 29 C for "severe".

## Caveats
- The 37-44 days is ONE variety (BARI Sarisha-18), not every mustard variety.
- Rebuilding also changed boro_rice rows (stage method, maturity) because cited boro maturity rows had arrived after the old build.
- In Cumilla, sowings of 1, 8, 15 Oct and 10 Dec show heat problems in 24 of 24 years, 5 Nov in only 3: a consequence of the mild 25 C onset limit, see the "Mustard heat check" note in Open questions.
- `tests/api_deploy/test_no_shapely.py::test_every_route_was_called_and_none_crashed` fails on main too (not from this change).

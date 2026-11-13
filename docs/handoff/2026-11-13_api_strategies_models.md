# Handoff: strategies and model-metrics endpoints (13 Nov 2026)

Branch `api-strategies-models`. Adds `GET /api/v1/rotation/strategies` and `GET /api/v1/models`
(`src/api/strategy_model_routes.py`, registered at the end of `app.py`). Tests: `src/api/test_strategy_model_routes.py`
(7 pass; all of `src/api` passes, 225 total). `scripts/check_module_docs.py`: 0 problems.

Check: `python -m pytest src/api -q`, then open `/docs` on the running API.
Also: `/data/sources`, `/data/reference[/name]`, `/disease-rules` (`src/api/data_routes.py`, section 14), and the `/map/layers` 500 fix (Dockerfile now ships `docs/w1b_data_status.csv` and `docs/results/w3_metrics.json`).
Not done: licence text (no source column exists); full test suite not re-run (only `src/api`); not deployed, so Render still shows the 500 until it redeploys.
Needs: web team agreement on section 13 of `docs/contract_change_proposals.md`; deploy to Render to go live.

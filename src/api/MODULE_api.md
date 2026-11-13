# API (FastAPI app)
Layer: API
Code: app.py
Purpose (2–3 sentences): `app.py` (repo root, ~1950 lines) is the CropShift API, v1. It adds no science: each endpoint calls Layer 1 code, packs the result into the envelope from docs/api_contract.md (every number a {value, unit, src} measure whose `src` ids point to a provenance entry), and narrates with a template sentence checked by `guard()`. The website in `web/` only renders these responses.
Public API (exact signatures + one-line description each):
- `measure(value, unit, src, decimals=0)` : builds one {value, unit, src} measure (old contract; see gaps in docs/ARCHITECTURE_MAP.md).
- `respond(endpoint, request, build)` : runs an endpoint's builder and wraps the envelope or the error envelope.
- `narrate(texts, fallback, data)` : template narration, passed through `guard()` or replaced by the fallback.
- `build_provenance(data)` : provenance entries (dataset, url, period, note) for every `src` id used.
- `districts()` : GET /api/v1/districts.
- `advisory(...)` : GET /api/v1/advisory (what to sow, ranked, `water` and `priority` options).
- `soil(...)` : GET /api/v1/soil (ISRIC SoilGrids for the field point, district fallback).
- `rotation_rank(request: Request)` : POST /api/v1/rotation/rank {district, weights} (farmer priorities, see src/compute/priorities/MODULE.md).
- `risk_calendar(...)` : GET /api/v1/risk-calendar.
- `post_flood(...)` : GET /api/v1/post-flood.
- `field_twin(...)` : GET /api/v1/field-twin (see MODULE_field_twin.md).
- `enso_lens(request: Request)` : still serves the web/mock file with `is_mock: true`.
- `GET /api/v1/warnings?district=` (src/api/warnings_routes.py): real since 13 Nov; Open-Meteo outlook vs sourced thresholds, see src/compute/weather_warnings/MODULE.md.
Inputs (data files / other modules) and their provenance: everything in src/compute, src/agents/guard.py, src/acquire/soilgrids_point.py; `data/processed/*`; `web/mock/*.json` for the not-built endpoints.
Outputs (shape + units + provenance fields): envelope {api_version, endpoint, request, generated_at, source_mode, is_mock, data, provenance, notices}; `source_mode` is live, cache or fixture.
Reference tables used (data/reference/*.csv rows): through the compute modules; `ref_provenance` turns each reference row into a provenance entry.
Tests (file names + what each proves): src/api/test_app.py (contract keys vs web/mock files, provenance ids exist, narration passes guard, error envelope); src/api/test_soil.py (SoilGrids mocked); src/api/test_rotation_rank.py (rotation/rank contract vs its mock); src/api/test_assumptions_doc.py; src/api/test_field_twin_stage.py.
Known limitations / honest caveats: provenance entries have dataset and url but no `retrieved` date or `granule_or_file` (gap vs the new rule). `/enso-lens` and `/ask` are mocks. app.py is too long to paste; use the line ranges. Planned endpoints (T18): /rotation (list), /field-profile, /replan, /block-summary, /validation/*, /scorecard.
CHAT KIT: src/api/MODULE_api.md, docs/api_contract.md, web/mock/advisory.json (or the matching mock file), app.py (read the relevant section only), src/api/test_app.py (matching tests only)
Last changed: 2026-10-24 by T2 (rotation/rank)

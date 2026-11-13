# data inputs (weather loader, strict reference loader, safe fetch)
Layer: 1 compute (plus acquire helpers)
Code: src/compute/weather.py, src/compute/reference.py, src/acquire/safe_fetch.py
Purpose (2–3 sentences): The shared inputs every feature starts from. `load_weather` gives IMERG rain plus POWER temperature, humidity, wind and solar; `load_reference` keeps only cited, non-placeholder rows of data/reference/*.csv; `fetch_json` is the online-first fetch (live, then cache, then fixture).
Public API (exact signatures + one-line description each):
- `load_weather(district, rain_source=DEFAULT_RAIN_SOURCE, data_dir=DATA_DIR)` : daily table with `rainfall_mm` from IMERG and a `rain_source` column.
- `load_reference(files=None, reference_dir=REFERENCE_DIR)` : kept reference rows (a ReferenceData) and the skipped ones with reasons.
- `check_row(row)` : (reason, detail) for the first rule a row breaks, or None if kept.
- `citation(row)` : the provenance of one kept row.
- `parse_value(value, unit)` : parses numbers and ranges.
- `fetch_json(url, params, cache_key, ttl_hours=24)` : returns (data, source_mode) with source_mode live, cache or fixture.
Inputs (data files / other modules) and their provenance: `data/processed/imerg_<district>_daily.csv` (NASA GPM IMERG V07 Final Run), `power_<district>_daily.csv` (NASA POWER); `data/reference/*.csv`; `cache/` and `demo_fixtures/`.
Outputs (shape + units + provenance fields): pandas tables; ReferenceData with citations; fetch results with `source_mode`.
Reference tables used (data/reference/*.csv rows): all of data/reference/ (the strict loader rejects PLACEHOLDER rows and rows without a source).
Tests (file names + what each proves): src/compute/test_weather.py, src/compute/test_reference.py, src/acquire/test_safe_fetch.py.
Known limitations / honest caveats: reference CSVs use the columns item,value,unit,source_title,source_url,page,year,notes, while new coefficients must use name,value,unit,source_title,source_url,page_or_table,note; the strict loader does not read the new columns yet, so T1 needs a small adapter first.
CHAT KIT: src/compute/MODULE_data_inputs.md, src/compute/weather.py, src/compute/reference.py, src/compute/test_reference.py, data/reference/_TEMPLATE.csv
Last changed: 2026-10-24 by session A (partition)

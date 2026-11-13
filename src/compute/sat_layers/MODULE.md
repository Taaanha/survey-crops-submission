# sat_layers (loaders, provenance and the data status table for the W1b satellite layers)
Layer: 1 compute (no AI, no network)
Code: src/compute/sat_layers/provenance.py, src/compute/sat_layers/loaders.py, src/compute/sat_layers/status.py, src/compute/sat_layers/intake.py
Purpose (2–3 sentences): One small loader per delivered W1b layer (NASADEM, GRACE-FO, MODIS, HLS, ECOSTRESS) that returns the data with its provenance (dataset, source URL, resolution, coverage years, units) and plain-language caveats, plus a status table saying which layer is assessed, partial or not assessed and why. W2 and later code read the status table here instead of hard-coding "not downloaded". A missing value stays NaN and is never written as 0.
Public API (exact signatures + one-line description each):
- `provenance(key, coverage_years)` : copy of a layer's provenance dict with the coverage years found in the data added.
- `load_nasadem(data_dir=DATA_DIR)` : 64-district mean elevation and slope; notes say slope is a relative ranking only.
- `nasadem_tile_summary(name, data_dir=DATA_DIR)` : pixel count, lowest and highest elevation and the pixels below 0 m of a 30 m demo tile.
- `load_grace(data_dir=DATA_DIR)` : GRACE-FO district table; raises if any row is not flagged regional.
- `grace_gaps(df, min_days=GAP_DAYS)` : list of (from, to, days) gaps between consecutive GRACE-FO dates.
- `grace_cells(df)` : number of mascon cells used and the most districts sharing one cell.
- `load_modis(data_dir=DATA_DIR)` : all MODIS year files joined on (date, district); overlap copies must agree or it raises.
- `modis_years_present(df, min_composites=MIN_COMPOSITES)` : calendar years that have enough composites.
- `ndvi_anomaly(df, district, min_other=MIN_OTHER_YEARS, min_years=MIN_YEARS_FOR_ANOMALY)` : NDVI z-score of each composite against the same composite in other years, with a status string; not assessed with fewer than 6 years.
- `load_hls(data_dir=DATA_DIR)` : HLS tile-mean NDVI per scene for the two demo tiles.
- `hls_clear_counts(df, min_clear=CLEAR_MIN)` : per tile and sensor, scenes listed, with pixels, and with clear_share at or above the cut-off.
- `load_ecostress(data_dir=DATA_DIR, allow_unverified=False)` : ECOSTRESS ET series; raises LayerUnverified unless opted in, because units and mask are unverified.
- `load_status(path=STATUS_PATH)` : the status table (docs/w1b_data_status.csv) as a DataFrame, validated.
- `status_of(key, path=STATUS_PATH)` : (status, reason) for one layer; unknown keys raise KeyError.
- `require_assessed(key, allow_partial=True, path=STATUS_PATH)` : returns the status or raises NotAssessed with the reason.
- `run_checks(data_dir=L.DATA_DIR)` : facts computed from the delivered files (years, overlaps, gaps, cells, counts, plausibility).
- `build_status(c)` : the status table rows built from run_checks output.
Inputs (data files / other modules) and their provenance: data/processed/{nasadem_district_static.csv, nasadem_30m_*.npz, grace_district_monthly.csv, modis_district_<year>.csv.gz, hls_ndvi_tile_series.csv, ecostress_tile_series.csv} produced by notebooks/w1b_earthdata_colab.ipynb from NASA AppEEARS and PO.DAAC (source URLs in provenance.py, each one opened or read on 10-11 Nov 2026); indicators.core.leave_one_out_z.
Outputs (shape + units + provenance fields): Layer(data, provenance, notes); docs/w1b_data_status.csv (key, dataset, coverage, districts, status, reason, source_url, units, resolution) and docs/results/w1b_intake_checks.md, both written by scripts/build_w1b_intake.py.
Reference tables used (data/reference/*.csv rows): none.
Tests (file names + what each proves): tests/sat_layers/test_loaders.py (overlap removal and conflict error, years present, z-score and status by hand, HLS counts, ECOSTRESS refusal, tile summary, GRACE gaps and cells, provenance fields and URLs), tests/sat_layers/test_status.py (reader, require_assessed, the shipped table equals one rebuilt from the files, the real MODIS join, GRACE and HLS counts).
Known limitations / honest caveats: ECOSTRESS units and cloud code are unverified (catalogue says W/m2 but the values look like mm/day), so that layer is not assessed. MODIS has 9 of 24 years (2017 and 2001-2014 missing), so its anomaly is partial. The 0.5 clear_share cut-off and the 20-composite rule for a year are our choices. The MODIS pixel_reliability rule and the HLS Fmask bits are recalled from the product guides, not confirmed. NASADEM slope is a relative ranking only. GRACE-FO is regional (about 300 km) with irregular dates and gaps.
CHAT KIT: src/compute/sat_layers/MODULE.md, src/compute/sat_layers/loaders.py, tests/sat_layers/test_loaders.py, docs/w1b_data_status.csv, docs/results/w1b_intake_checks.md
Last changed: 2026-11-11 by W1b intake

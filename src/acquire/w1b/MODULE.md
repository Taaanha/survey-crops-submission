# w1b (Earthdata downloads for 64 districts and the demo tiles: SMAP, MODIS, NASADEM, GRACE-FO, HLS, ECOSTRESS, GEDI)
Layer: acquisition helpers (no AI, no web app; run from the Colab notebook notebooks/w1b_earthdata_colab.ipynb, never from web/)
Code: src/acquire/w1b/products.py, src/acquire/w1b/appeears.py, src/acquire/w1b/convert.py, src/acquire/w1b/tables.py, src/acquire/w1b/dem.py
Purpose (2–3 sentences): Builds AppEEARS request bodies, talks to the AppEEARS API, applies the quality masks and unit conversions, and turns each raster into a small district table on the common 0.1 degree grid (plan section W1, rules in docs/harmonisation.md). Everything that needs the user's Earthdata login is run by the user in Colab; this code only receives the login from the notebook and never stores it.
Public API (exact signatures + one-line description each):
- `demo_field_bboxes(processed_dir)` : the two 20 km demo tiles (Feni, Cumilla) as (west, south, east, north), read from their T3 manifests.
- `appeears_date(iso)` : '2024-07-01' to '07-01-2024'.
- `year_chunks(first_year, last_year)` : one (start, end) ISO date pair per calendar year, to keep 250 m requests small.
- `bbox_feature_collection(bbox, name='area')` : GeoJSON rectangle for an AppEEARS area request.
- `area_task(name, key, start, end, bbox, layers=None, fmt='netcdf4')` : AppEEARS area-task body for a catalogue entry; refuses non-AppEEARS products, unknown layers and dates before the product starts.
- `login(session, username, password, api=APPEEARS_API)` : AppEEARS bearer token.
- `submit(session, token, task, api=APPEEARS_API)` : submit a task, returns its id.
- `wait(session, token, task_id, poll_s=30, max_wait_s=6 * 3600, api=APPEEARS_API, sleep=time.sleep)` : poll until done; raises on error or timeout.
- `list_files(session, token, task_id, suffixes=('.nc',), api=APPEEARS_API)` : output files of a finished task.
- `download(session, token, task_id, file_id, dest_path, api=APPEEARS_API)` : stream one file to disk.
- `check_range(arr, lo, hi, name, tolerance=0.01)` : raises if a raster still looks unscaled (more than 1% outside its valid range).
- `mod13_clean(vi, reliability, keep=MOD13_KEEP, name='ndvi')` : MODIS NDVI/EVI with non-kept pixels set to NaN, plus the share kept.
- `fmask_clear(fmask, bad_bits=FMASK_BAD_BITS)` : True where an HLS pixel is observed and not cloud, adjacent cloud, shadow or snow.
- `ndvi(nir, red)` : (NIR - red) / (NIR + red), NaN where undefined.
- `hls_ndvi(red, nir, fmask)` : HLS NDVI with cloud, shadow and snow pixels masked.
- `mask_range(arr, lo, hi)` : values outside [lo, hi] become NaN.
- `wm2_to_mm_per_day(w_m2)` : ECOSTRESS daily latent heat flux (W/m2) to mm of water per day (FAO-56 factor 0.408 per MJ/m2/day).
- `find_variable(names, layer)` : which variable of a downloaded file holds an AppEEARS layer; raises KeyError listing what exists.
- `find_coord(names, axis)` : name of the 'lat' or 'lon' coordinate.
- `wrap_longitude(lons)` : 0..360 to -180..180.
- `kelvin_to_celsius(k)` : K to degrees C.
- `all_district_weights(districts=None)` : slugs and area weights [district, lat, lon] for the 64 districts on the IMERG grid.
- `stack_to_district_table(stack, dates, slugs, weights, column)` : [time, lat, lon] raster to a long table (date, district, value, coverage).
- `static_to_district_table(grids, slugs, weights)` : static [lat, lon] grids to one row per district with coverage.
- `scene_stats(stack, dates, column, **meta)` : per-scene mean of valid pixels and clear_share, for the demo tiles.
- `to_wide(table, column)` : long table to date x district columns (keeps daily SMAP under 5 MB).
- `coverage_summary(table)` : per district, share of dates with data and the lowest coverage.
- `grace_table(lwe, times, lons, lats, points, uncertainty=None)` : GRACE-FO nearest mascon cell per district point, with the cell used and a regional flag.
- `column_rows(spec)` : rows for a *_columns.csv (dataset, unit, source URL, years).
- `dem_cell_stats(read_strip, grid_lons, grid_lats, step_deg)` : mean elevation, mean slope and pixel count per 0.1 degree cell, one strip of cells at a time.
- `gedi_cell_means(values, lon2d, lat2d, grid_lons, grid_lats, nodata=None)` : GEDI 1 km biomass averaged per 0.1 degree cell (context only).
Inputs (data files / other modules) and their provenance: AppEEARS products SPL4SMGP.008, MOD13Q1.061, NASADEM_NC.001, HLSL30.020, HLSS30.020, ECO_L3T_JET.002, ECO_L2T_LSTE.002 (names, layers, fill values and start dates read from https://appeears.earthdatacloud.nasa.gov/api/product on 2026-11-10); JPL GRACE/GRACE-FO mascons TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4 (PO.DAAC, CMR concept C3195527175-POCLOUD); GEDI L4B V2.1 (ORNL DAAC, DOI 10.3334/ORNLDAAC/2299, CMR concept C2792577683-ORNL_CLOUD); data/reference/bgd_adm2_districts.geojson; data/processed/field_profile_manifest_<district>.json. Source URL and DOI for each are in products.PRODUCTS.
Outputs (shape + units + provenance fields): the notebook writes small result files to Google Drive: smap_<layer>_district_daily.csv.gz (date x 64 districts, m3/m3), modis_district_<year>.csv.gz (date, district, ndvi, evi, coverage), nasadem_district_static.csv (elev_mean_m, slope_mean_deg), grace_district_monthly.csv (lwe_thickness_cm, uncertainty_cm, cell_lon, cell_lat, regional), hls_ndvi_tile_series.csv, ecostress_tile_series.csv, gedi_tile_means.csv, plus .npz rasters that stay out of git.
Reference tables used (data/reference/*.csv rows): none.
Tests (file names + what each proves): src/acquire/w1b/test_w1b.py (request bodies and refusals, client flow with a fake session, masks and NDVI by hand, district tables equal hand calculations, GRACE nearest cell, DEM strips on planes of known slope); tests/district_grid/test_regrid.py (cell means, nearest cell, slope).
Known limitations / honest caveats: `wm2_to_mm_per_day` is UNVERIFIED for ECOSTRESS ETdaily: the delivered values suggest the layer may already be in mm/day (docs/results/w1b_intake_checks.md); do not use it for ECOSTRESS until the unit is confirmed. Nothing in this module has been run against the live services in the session that wrote it (no Earthdata login is available there); the notebook cells were run only on synthetic files shaped like the real ones. MODIS pixel_reliability 0 = good and the HLS Fmask bit meanings are recalled from the product guides, not read in this session (open questions in docs/PROJECT_STATE.md). AppEEARS reprojects to latitude/longitude with its own resampling. SMAP (9 km) has only 1 to 2 pixels per 0.1 degree cell. GRACE-FO is about 300 km effective: a regional signal, not a district one. GEDI mostly measures trees, not field crops. The two "demo fields" are the 20 km T3 tiles, not single farm plots.
CHAT KIT: src/acquire/w1b/MODULE.md, src/acquire/w1b/products.py, src/acquire/w1b/test_w1b.py, notebooks/w1b_earthdata_colab.ipynb, docs/harmonisation.md
Last changed: 2026-11-10 by W1b

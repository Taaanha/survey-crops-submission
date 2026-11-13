# district_grid (64 district boundaries, common 0.1 degree grid, district x season features)
Layer: 1 compute
Code: src/compute/district_grid/grid.py, src/compute/district_grid/boundaries.py, src/compute/district_grid/features.py, src/compute/district_grid/regrid.py
Purpose (2–3 sentences): Puts every gridded NASA layer onto one 0.1 degree analysis grid (the IMERG grid, Bangladesh box) and averages it over the true outline of each of the 64 districts, instead of a 20 km square around one point. It then builds the district x season feature table (W1 of docs/plan-2026-11-10.md). Rules for each dataset are in docs/harmonisation.md.
Public API (exact signatures + one-line description each):
- `imerg_axes()` : cell-centre longitudes (52) and latitudes (64) of the Bangladesh box on the IMERG grid.
- `cell_weights(geom, lons, lats, res=RES)` : [lat, lon] array, the share (0..1) of each cell's area inside a shapely polygon.
- `district_mean(field, weights)` : area-weighted mean over a district of a [lat, lon] or [time, lat, lon] field; NaN cells are left out; returns (mean, coverage), and (NaN, 0) when nothing was observed.
- `slug_for(boundary_name)` : geoBoundaries district name to our slug; unknown names raise KeyError.
- `load_districts(path=GEOJSON)` : the 64 districts as dicts (slug, name, geometry, point) from data/reference/bgd_adm2_districts.geojson.
- `metadata(path=GEOJSON)` : licence, attribution and source URLs stored in the boundary file.
- `season_range(season, year)` : first and last day of kharif1 / kharif2 / rabi for a season year (rabi runs into February of the next year).
- `bin_mean_to_grid(values, lons, lats, grid_lons, grid_lats)` : mean of the finer native pixels inside each 0.1 degree cell (SMAP, MODIS, NASADEM); returns (mean, count).
- `bin_mean_scattered(values, lon, lat, grid_lons, grid_lats)` : the same for pixels on a projected grid (GEDI), given each pixel's lon and lat.
- `nearest_cell(field, lons, lats, lon, lat)` : value of a coarse grid (GRACE-FO 0.5 degree) at the nearest cell, with the cell's lon and lat.
- `slope_degrees(elev, lats, step_deg)` : terrain slope in degrees for a lat/lon DEM.
- `season_features(rain, power, years, seasons=('kharif1', 'kharif2', 'rabi'))` : one row per season for one district: rain total and largest day (IMERG), temperature, humidity, wind and solar sums (POWER), and observed-day counts.
Inputs (data files / other modules) and their provenance: data/reference/bgd_adm2_districts.geojson (geoBoundaries gbOpen BGD ADM2, CC BY 3.0 IGO, source BBS via OCHA ROAP, retrieved 2026-11-10); IMERG V07 Final Run daily subset (GPM_3IMERGDF.07, DOI 10.5067/GPM/IMERGDF/DAY/07) read by src/acquire/imerg_subset.py; NASA POWER daily read by src/acquire/power_points.py.
Outputs (shape + units + provenance fields): data/processed/imerg_polygon_daily_wide.csv.gz (mm/day, one column per district), imerg_polygon_coverage.csv, power64_points.csv, power64_cell_groups.csv, district_season_features.csv (64 districts x 24 season years x 3 seasons) and district_season_features_columns.csv (dataset, unit, source_url, years covered per column).
Reference tables used (data/reference/*.csv rows): none (boundary file is GeoJSON).
Tests (file names + what each proves): tests/district_grid/test_grid.py (area-fraction weights and district means equal hand calculations on small fixture grids; NaN handling), tests/district_grid/test_boundaries.py (64 valid polygons, file under 2 MB, licence recorded, no guessed names), tests/district_grid/test_regrid.py (cell means, NaN and edge handling, nearest cell, slope of planes with known angle), tests/district_grid/test_features.py (season windows, totals by hand, NaN rule, every column has dataset, unit and source URL).
Known limitations / honest caveats: Weights are exact areas in degree space; the cos(latitude) difference inside one district (under 2%) is ignored. The boundary file is the simplified geoBoundaries geometry (about 2020 boundaries); coastal and river edges are approximate. A district smaller than one IMERG cell still gets weights, but its value is mostly the neighbouring cell's: IMERG is 0.1 degree (about 11 km). The three season windows are our analysis windows, not a cited crop calendar (open question in PROJECT_STATE). POWER is about 0.5 degree, so neighbouring districts can share a POWER cell.
CHAT KIT: src/compute/district_grid/MODULE.md, src/compute/district_grid/grid.py, tests/district_grid/test_grid.py, docs/harmonisation.md
Last changed: 2026-11-10 by W1

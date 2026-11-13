# Harmonisation: how every dataset reaches the common 0.1° grid

Plan section W1. Status of each row is honest: **done in W1a** means built, run and tested; **W1b: code ready, not run** means the code and the Colab notebook are built and tested on synthetic data, but the download needs the user's Earthdata login and has not been run yet.

## The common grid

- **Grid:** the NASA GPM IMERG V07 grid, 0.1°, cell centres at x.x5. Bangladesh box: longitude 87.85 to 92.95°E (52 cells), latitude 20.45 to 26.75°N (64 cells). Defined in `src/compute/district_grid/grid.py` (`imerg_axes`).
- **District averages:** for each district, each cell gets a weight = the share of that cell's area inside the district polygon (exact polygon-box intersection, `cell_weights`). The district value is the weighted mean of the cells that have data (`district_mean`); cells with no data are left out and the share of weight that had data is reported as `coverage`.
- **Boundary:** geoBoundaries gbOpen, Bangladesh ADM2 (64 districts), simplified geometry, boundary year 2020. Licence **CC BY 3.0 IGO** (original source Bangladesh Bureau of Statistics via OCHA ROAP). Checked 2026-11-10 against the geoBoundaries API (`boundaryLicense`) and recorded inside `data/reference/bgd_adm2_districts.geojson` (`metadata` block). Attribution must appear wherever the map is shown.
- **Area weighting detail:** weights are areas in degree space. A cell's true area changes with cos(latitude) by under 2% across one district, so this is ignored.

## Rules per dataset

| Dataset | Native size | How it goes onto the 0.1° grid | District value | Status |
|---|---|---|---|---|
| GPM IMERG V07 Final Run daily | 0.1° | none needed, same grid; subset read from GES DISC OPeNDAP | area-weighted mean of cells (mm/day) | **done in W1a** |
| NASA POWER daily | about 0.5° (some inputs coarser) | nearest cell: one query at the district point (polygon centroid, or a point inside the polygon if the centroid falls outside) | the point value | **done in W1a** |
| SMAP L4 | 9 km | mean of the 9 km cells inside each 0.1° cell | area-weighted mean | W1b: code ready, not run |
| MODIS MOD13Q1 | 250 m | mean of the 250 m pixels inside each 0.1° cell | area-weighted mean | **partial (11 Nov): 10 of 24 years delivered (2015-2024)** |
| NASADEM | 30 m | slope from the 30 m DEM, then mean elevation and mean slope per cell | area-weighted mean | **done in W1b (run in Colab, 11 Nov); file checked** |
| GRACE-FO mascons | 0.5° mascon, about 300 km effective | nearest; flagged "regional" | the mascon value (cell used is recorded) | **done in W1b (run in Colab, 11 Nov); file checked** |

## Sources and how they were read

- **IMERG:** product `GPM_3IMERGDF.07` (DOI 10.5067/GPM/IMERGDF/DAY/07), page https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary. Read through NASA Earthdata OPeNDAP (Hyrax) with a server-side subset of the Bangladesh box, 2001-01-01 to 2025-09-30 (`scripts/fetch_imerg_bgd.py`, `src/acquire/imerg_subset.py`). Free; needs the Earthdata token already in `.env`. Raw yearly files stay in `data/raw/imerg_bgd/` (not in git).
- **POWER:** AG community daily point API, https://power.larc.nasa.gov/docs/services/api/temporal/daily/ (`scripts/fetch_power64.py`, `src/acquire/power_points.py`). The coordinates POWER echoes back (the query point, not its native cell) are saved in `data/processed/power64_points.csv`; which districts really share one POWER cell is found from identical temperature series and saved in `data/processed/power64_cell_groups.csv`. Raw daily files stay in `data/raw/power64/`.
- **POWER rain is not used.** Its rain record has step changes (`docs/results/rain_source_check.md`); rain always comes from IMERG.
- **Field-detail tier (two 20 km demo tiles, no district average):** HLS NDVI (30 m, cloud/shadow/snow masked, tile mean per scene), ECOSTRESS evapotranspiration and land-surface temperature (70 m, cloud masked), NASADEM at 30 m, GEDI L4B biomass (1 km, **context only: mostly measures trees, not field crops**). Tile means per scene are CSV; pixels stay in .npz outside git.

## Caveats for the layers already delivered (NASADEM, GRACE-FO)

Files: `data/processed/nasadem_district_static.csv`, `nasadem_cells_0p1deg.npz`, `nasadem_30m_{feni,cumilla}.npz`, `grace_district_monthly.csv`, column labels in `nasadem_grace_columns.csv`. Checked on 11 Nov: 64 districts, no missing values, NASADEM coverage 1.0 everywhere, GRACE-FO 64 districts x 261 dates on 48 mascon cells.

1. **NASADEM near the coast.** A 0.1 degree cell on the coast includes sea pixels, so its mean elevation is pulled down; the district polygons are land only, so the effect on a district value is small but not zero. Separately, the 30 m tiles contain a few negative elevations (0.2% of Feni pixels and 0.0% of Cumilla pixels are below 0 m, lowest -20 m): small DEM noise, not real depressions. The DEM is a single 2000 acquisition and does not show later land change.
2. **GRACE-FO is regional, not a district number.** The mascons are 0.5 degree cells (about 300 km effective). Each district takes the nearest cell, so up to 3 districts share exactly the same series (48 cells for 64 districts); the cell used is in `cell_lon`/`cell_lat` and `regional` is always True. Say "regional groundwater and storage signal", never "your district's groundwater".
3. **GRACE-FO is not monthly in the strict sense.** The table has 261 irregular dates (2002-04 to 2026-09) with gaps: several of 60 to 110 days and one of 370 days (2017-06 to 2018-06, between GRACE and GRACE-FO). Do not interpolate silently; a trend over this record should use only the dates present, say so, and show n.
4. **GRACE-FO unit.** Values are taken as centimetres of equivalent water thickness (anomaly from the time mean), the unit of the JPL product; the range seen (-77 to +55 cm) fits that. The unit attribute printed in the Colab run was not seen by the session that checked the file.

## W1b intake, 11 Nov: status of every layer

The status of each layer is in `docs/w1b_data_status.csv` (assessed / partial / not assessed, with the reason) and is read by code through `src/compute/sat_layers/status.py`; the numbers behind it are in `docs/results/w1b_intake_checks.md`. A layer that is not assessed is shown as "not assessed" with its reason, never as 0.

| Layer | Status | In one line |
|---|---|---|
| NASADEM elevation | assessed | 64 districts, complete |
| NASADEM slope | partial | relative ranking only; about 2 degrees on flat districts is probably surface noise |
| GRACE-FO | partial | regional only (48 cells for 64 districts); 20 gaps over 40 days; never district groundwater |
| MODIS NDVI / EVI | partial | years 2015-2024 only; 2001-2014 missing; year files overlap by one composite (removed, copies agree) |
| MODIS NDVI anomaly | partial | 10 years present (rule: at least 6, and 5 other years per composite) |
| HLS NDVI | partial | two demo tiles, 2024; scenes with clear_share >= 0.5 (our cut-off) are about a third; June to August have none |
| SMAP, 64 districts | not assessed | AppEEARS job did not finish; the five live districts use the existing point files |
| ECOSTRESS ET | not assessed | units unresolved (see below) |
| ECOSTRESS LST, GEDI | not assessed | not delivered / not run |

**ECOSTRESS is not used: units unresolved.** Findings from Tanha's Colab run (11 Nov), full text in `docs/results/w1b_intake_checks.md`:
- The file metadata for ETdaily says "W/m²", but the same tag is on the 0/1 `cloud` layer, so the units attribute looks like a blanket label, not reliable per layer.
- `cloud` holds only 0 and 1. In one scene, pixels with cloud = 1 had no ETdaily value and cloud = 0 pixels had a value in 53.6% of cases, so cloud = 1 behaves as "cloudy, no usable ET". This mask is supported by the data in one scene, **not documented**.
- Raw values (median about 2) are plausible as mm/day and not as W/m² (about 0.07 mm/day). **Units: UNRESOLVED.** No conversion is applied and no unit is chosen.

The series stays "not assessed (units unresolved)" for any comparison with FAO-56 ET0, and the loader refuses it unless a caller opts in (its message says the ETdaily unit in the ECO_L3T_JET.002 User Guide or ATBD would resolve it). W2 reads this status from the table (`src/compute/indicators/layer_status.py`).

## W1b sources and how they are read (all through the user's Earthdata login in Colab)

- **SMAP L4** `SPL4SMGP.008` (9 km, daily, from 2015-03-31), layers `sm_rootzone`, `sm_surface`, AppEEARS area task over the Bangladesh box; valid range 0 to 0.9 m3/m3 from the layer record. DOI 10.5067/T5RUATAQREF8, page https://nsidc.org/data/spl4smgp/versions/8 .
- **MODIS** `MOD13Q1.061` (250 m, 16-day), layers NDVI, EVI, pixel_reliability; one AppEEARS task per year; only `pixel_reliability` = 0 pixels are kept (open question). DOI 10.5067/MODIS/MOD13Q1.061 .
- **NASADEM** `NASADEM_NC.001` (30 m, layer `NASADEM_HGT`), processed in strips of 0.1 degree cells. Sphere with the mean Earth radius for metres per degree (well under 1% error in slope).
- **GRACE-FO** JPL mascons `TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4` (PO.DAAC, 2002-04 on, one global file about 44 MB). Always labelled **regional, about 300 km effective**; several districts share one mascon cell and the cell is recorded.
- **HLS** `HLSL30.020` and `HLSS30.020` (NDVI = (NIR - red)/(NIR + red) with B05 or B8A as NIR), **ECOSTRESS** `ECO_L3T_JET.002` (ETdaily) and `ECO_L2T_LSTE.002` (LST), **GEDI** L4B V2.1 (ORNL DAAC, DOI 10.3334/ORNLDAAC/2299).
- Product names, layers, fill values and start dates were read from the public AppEEARS product API and NASA CMR on 2026-11-10. How to run it: `notebooks/w1b_earthdata_colab.ipynb`.

## Check that the grid is right

`scripts/build_district_features.py` compares, for the five live districts, the IMERG cell under the old Giovanni point with the same cell in the new subset. The numbers are in the handoff (`docs/handoff/2026-11-10_W1a.md`).

## Season windows used in the feature table

kharif1 = 1 Mar to 30 Jun, kharif2 = 1 Jul to 31 Oct, rabi = 1 Nov to end of February of the next year. These are **analysis windows chosen by us**, not a cited crop calendar (open question in `docs/PROJECT_STATE.md`). A season total is only given when every day in the window was observed.

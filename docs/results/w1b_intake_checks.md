# W1b intake checks (11 Nov 2026)

Each file was checked before it was accepted. Numbers below are computed from the files by `src/compute/sat_layers/intake.py`; the status table is `docs/w1b_data_status.csv`.

## MODIS MOD13Q1 (NDVI, EVI), `modis_district_<year>.csv.gz`
- Files: 10; years present (composite years with at least 20 of 23 composites): [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]. Missing from 2001-2024: [2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014].
- Every year file starts with the previous year's last composite (for example 2018-12-19 in the 2019 file). Confirmed in all 10 files. Joined on (date, district): 15,360 rows became 14,784 after removing 576 duplicates; the duplicate copies agreed exactly (the loader stops with an error if they do not), so nothing was chosen between them.
- Districts: 64 (all 64) in every file. Dates 2014-12-19 to 2024-12-18. 9.5% of district-composites have no good pixel and stay NaN (never 0); highest shares: thakurgaon 35%, joypurhat 22%, dinajpur 22%.
- Vegetation anomaly: with 10 years (the rule needs at least 6, and at least 5 other years per composite) the status is **partial (10 years of 24 present)**. Years not downloaded: 14 of 24 (2001-2014), so this is not a 24-season statistic.
- Quality rule (`pixel_reliability` = 0 kept) is recalled from the product guide and not confirmed (open question).

## ECOSTRESS ECO_L3T_JET.002, `ecostress_tile_series.csv` -> **not assessed: units unresolved**
- Documentation opened: https://www.earthdata.nasa.gov/data/catalog/lpcloud-eco-l3t-jet-002 (NASA Earthdata catalogue page, its Variables table). It lists `ETdaily` in W/m2 and, for the `cloud` layer, only fill 255 and valid range 0 to 1, not what 1 means. The User Guide and ATBD PDFs linked from that page could not be read (the fetch returned undecoded PDF bytes).
- Findings from Tanha's Colab run (11 Nov; supplied by Tanha, not re-run here):
  - The file metadata for ETdaily says units "W/m²". The same "W/m²" tag is also on the `cloud` layer, which is a 0/1 flag, so the units attribute looks like a blanket label and is not reliable per layer.
  - `cloud` holds only the values 0 and 1 (valid_min 0, valid_max 1). In one scene: 2,433,733 pixels with 0 and 844,427 pixels with 1.
  - In that scene, pixels with cloud = 1 have NO ETdaily value (share of finite ET = 0.0), while cloud = 0 pixels have a value in 53.6% of cases. Median raw ET for cloud = 0 is 1.91. So cloud = 1 behaves as "cloudy, no usable ET". **Mask: supported by the data in one scene, not documented.**
  - Raw values (median about 2 across the series) are plausible as mm/day and not plausible as W/m² (about 0.07 mm/day). **Units: UNRESOLVED.** No conversion is applied and no unit is chosen.
- The delivered file has 245 scenes (2018-09-29 to 2026-08-09), ET only (no land-surface temperature). Its `et_mm_day` column came from a W/m2 to mm/day conversion in the Colab cell and must not be used while the units are unresolved.
- Decision: the series is "not assessed (units unresolved)" for any comparison with FAO-56 ET0. The loader refuses it unless `allow_unverified=True`, and its message says what would resolve it: the ETdaily unit stated in the ECO_L3T_JET.002 User Guide or ATBD. That unit is not assumed here.

## HLS NDVI, `hls_ndvi_tile_series.csv`
- 264 scenes, 2024-01-01 to 2024-12-31, two 20 km demo tiles (tile mean, not a field). About 1% of red/NIR values were outside 0-1 and were set to missing in the Colab run (as reported by Tanha; not re-checkable from the tile-mean file).
- Scenes with `clear_share` >= 0.5 (**the 0.5 cut-off is our choice, not a standard**):

| tile | sensor | scenes | with any valid pixel | clear_share >= 0.5 |
|---|---|---|---|---|
| cumilla | hls_l30 | 78 | 57 | 27 |
| cumilla | hls_s30 | 67 | 49 | 25 |
| feni | hls_l30 | 59 | 42 | 15 |
| feni | hls_s30 | 60 | 47 | 25 |

- Usable scenes per month (month: scenes, both tiles and sensors): 1: 7, 2: 8, 3: 19, 4: 7, 5: 10, 6: 0, 7: 0, 8: 0, 9: 2, 10: 5, 11: 12, 12: 22. Months with none: [6, 7, 8]. The monsoon season is poorly covered by optical data.
- The cloud-mask bit rule (Fmask bits 1-4) is recalled from the product guide and not confirmed (open question).

## NASADEM
- 64 districts, no missing values, coverage 1.0.
- **Slope is a relative ranking only.** Mean slope is 1.55 degrees at the lowest and 2.20 at the median, and about 2 degrees on flat delta districts (live districts: cumilla 2.12, feni 2.50, brahmanbaria 2.35, noakhali 1.86, sylhet 3.26); that is probably surface noise in the DEM, not real terrain. Compare districts with each other (hill districts such as Bandarban and Rangamati stand out), never read a district's slope as a physical gradient.
- Negative elevations in the 30 m demo tiles (Bangladesh land is almost never below sea level, so these are DEM noise):
  - feni: 466,470 pixels, lowest -12 m, highest 44 m, 888 pixels below 0 m (0.19%)
  - cumilla: 470,526 pixels, lowest -20 m, highest 78 m, 188 pixels below 0 m (0.04%)

## GRACE-FO, `grace_district_monthly.csv` -> partial, REGIONAL
- 64 districts share 48 mascon cells (up to 3 districts per cell); every row is flagged `regional`. **Never show it as district-level groundwater.** Say "regional water-storage signal, about 300 km effective".
- 261 dates from 2002-04-17 to 2026-09-16 (irregular, not strictly monthly). Gaps longer than 40 days (20):
  - 2002-05-10 to 2002-08-16: 98 days
  - 2003-05-11 to 2003-07-16: 66 days
  - 2004-01-07 to 2004-02-17: 41 days
  - 2010-12-14 to 2011-02-18: 66 days
  - 2011-05-16 to 2011-07-18: 63 days
  - 2011-11-01 to 2012-01-01: 61 days
  - 2012-04-04 to 2012-06-16: 73 days
  - 2012-09-13 to 2012-11-18: 66 days
  - 2013-02-14 to 2013-04-21: 66 days
  - 2013-07-16 to 2013-10-16: 92 days
  - 2014-01-09 to 2014-03-16: 66 days
  - 2014-06-13 to 2014-08-16: 64 days
  - 2014-11-17 to 2015-01-22: 66 days
  - 2015-04-27 to 2015-07-15: 79 days
  - 2015-09-14 to 2015-12-23: 100 days
  - 2016-03-16 to 2016-05-20: 65 days
  - 2016-08-21 to 2016-11-27: 98 days
  - 2017-01-21 to 2017-03-31: 69 days
  - 2017-06-11 to 2018-06-16: 370 days
  - 2018-07-10 to 2018-10-31: 113 days
- The 2017-06 to 2018-06 gap is the break between GRACE and GRACE-FO.
- Uncertainty column: 2.08 to 23.51 cm. Values range -77.3 to 55.5 cm; the unit (cm) is inferred from the product, not read from the file.

## SMAP, 64 districts -> not assessed
The AppEEARS job did not finish, so there is no 64-district SMAP file. The five live districts use the existing point files `smap_<district>_2015_2026.csv` (status `smap_live5`: partial).

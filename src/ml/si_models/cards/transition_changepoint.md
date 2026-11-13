# Model card: transition_changepoint

- **Problem:** estimated green-up and browning dates from MODIS NDVI
- **Method:** Savitzky-Golay smoothing (5 composites, order 2: our choice) + Pettitt change point in a four-month search window (our choice)
- **Used by the app:** yes: Method A is not assessed, so the two methods cannot be compared; the app shows the Method B dates as estimates that need local validation
- **Sample (n):** 10 years (2015 to 2024) x 5 districts
- **Validation:** leave-one-year-out; bootstrap 95% intervals; seed 20261112

## Inputs
- NASA MODIS MOD13Q1.061 NDVI (16-day, district polygon mean) (https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061)

## Metrics (held-out years only)
- aman_browning: error: not assessed (no cited Aman harvest window: the only days-to-maturity row cites a placeholder URL (BRRI handbook), so it is not used); dates found 50 of 50
- aman_greenup: median days outside the cited window: 0 (95% interval 0 to 0, n = 41); dates found 41 of 50
- aman_greenup: share of dates inside the window: 0.68 (95% interval 0.54 to 0.83, n = 41)
- boro_browning: error: not assessed (no cited Boro harvest window: the BAMIS duration row does not say where the count starts and its stage dates are a GAP); dates found 21 of 50
- boro_greenup: median days outside the cited window: 11 (95% interval 11 to 11, n = 49); dates found 49 of 50
- boro_greenup: share of dates inside the window: 0.31 (95% interval 0.18 to 0.43, n = 49)

## Limits
- Composites are 16 days apart: an error below about 16 days cannot be resolved.
- boro_greenup window: earliest cited seedbed sowing 31/10 + youngest cited seedling age 35 days, to the cited date transplanting should be complete. Sources: boro_rice.sow.seedbed_start; https://apps.barc.gov.bd/cropcalendar/index.php; boro_rice.sow.seedbed_start; https://journal.safebd.org/index.php/jafe/article/download/35/33/65; boro_rice.sow.window_end; https://journal.safebd.org/index.php/jafe/article/download/35/33/65; boro_rice.stage.seedling_age; https://apps.barc.gov.bd/cropcalendar/index.php.
- aman_greenup window: cited seedbed sowing window 15/06 to 30/07 (both variety groups) + cited seedling age 25 to 30 days. Sources: aman_rice.sow.window_end; https://apps.barc.gov.bd/cropcalendar/index.php; aman_rice.sow.window_start; https://apps.barc.gov.bd/cropcalendar/index.php; aman_rice.stage.seedling_age; https://apps.barc.gov.bd/cropcalendar/index.php.
- The satellite sees the canopy turning green, which is later than transplanting; no cited lag is subtracted.
- District-mean NDVI mixes rice with all other land cover; June to August composites are often cloudy.
- MODIS status: partial (years missing from 2001-2024: [2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014]; 9.5% of district-composites have no good pixel (NaN, not 0)).
- Small sample (5 districts, 10 to 24 seasons): intervals are wide, and district-seasons of the same year are not independent, so the true uncertainty is larger. Needs local validation.
- It describes past seasons ("flags past seasons that look unusual", "estimated", "tested on"); it says nothing about a coming season.

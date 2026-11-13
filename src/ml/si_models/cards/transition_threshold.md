# Model card: transition_threshold

- **Problem:** estimated green-up and browning dates from MODIS NDVI
- **Method:** fixed NDVI threshold 0.1 (https://earthobservatory.nasa.gov/features/MeasuringVegetation; provisional, global, not Bangladesh rice)
- **Used by the app:** no: Method A is not assessed, so the two methods cannot be compared; the app shows the Method B dates as estimates that need local validation
- **Sample (n):** 10 years (2015 to 2024) x 5 districts
- **Validation:** leave-one-year-out; bootstrap 95% intervals; seed 20261112

## Inputs
- NASA MODIS MOD13Q1.061 NDVI (16-day, district polygon mean) (https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061)

## Metrics (held-out years only)
- aman_browning: error: not assessed (no cited Aman harvest window: the only days-to-maturity row cites a placeholder URL (BRRI handbook), so it is not used); dates found 0 of 50
- aman_greenup: median days outside the cited window: 8 (95% interval 0 to 15, n = 2); dates found 2 of 50
- boro_browning: error: not assessed (no cited Boro harvest window: the BAMIS duration row does not say where the count starts and its stage dates are a GAP); dates found 1 of 50
- boro_greenup: median days outside the cited window: not assessed (n = 0); dates found 0 of 50

## Limits
- Composites are 16 days apart: an error below about 16 days cannot be resolved.
- boro_greenup window: earliest cited seedbed sowing 31/10 + youngest cited seedling age 35 days, to the cited date transplanting should be complete. Sources: boro_rice.sow.seedbed_start; https://apps.barc.gov.bd/cropcalendar/index.php; boro_rice.sow.seedbed_start; https://journal.safebd.org/index.php/jafe/article/download/35/33/65; boro_rice.sow.window_end; https://journal.safebd.org/index.php/jafe/article/download/35/33/65; boro_rice.stage.seedling_age; https://apps.barc.gov.bd/cropcalendar/index.php.
- aman_greenup window: cited seedbed sowing window 15/06 to 30/07 (both variety groups) + cited seedling age 25 to 30 days. Sources: aman_rice.sow.window_end; https://apps.barc.gov.bd/cropcalendar/index.php; aman_rice.sow.window_start; https://apps.barc.gov.bd/cropcalendar/index.php; aman_rice.stage.seedling_age; https://apps.barc.gov.bd/cropcalendar/index.php.
- The satellite sees the canopy turning green, which is later than transplanting; no cited lag is subtracted.
- District-mean NDVI mixes rice with all other land cover; June to August composites are often cloudy.
- MODIS status: partial (years missing from 2001-2024: [2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014]; 9.5% of district-composites have no good pixel (NaN, not 0)).
- Method A status: not assessed (the district-mean NDVI crosses the cited 0.1 bare-soil limit in only 3 of 200 district-year search windows, below our 50% rule; the Bangladesh-specific threshold row is a GAP).
- Small sample (5 districts, 10 to 24 seasons): intervals are wide, and district-seasons of the same year are not independent, so the true uncertainty is larger. Needs local validation.
- It describes past seasons ("flags past seasons that look unusual", "estimated", "tested on"); it says nothing about a coming season.

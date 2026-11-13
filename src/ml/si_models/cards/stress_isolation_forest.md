# Model card: stress_isolation_forest

- **Problem:** flags past seasons that look unusual
- **Method:** Isolation Forest (200 trees) fitted on the other years; cut-off from the training scores at the z-score rule's training flag rate
- **Used by the app:** no: Isolation Forest did not beat the z-score rule on the listed events (the interval of the difference includes 0 or there are too few events), so the app uses the z-score rule
- **Sample (n):** 360 district-seasons
- **Validation:** leave-one-year-out; bootstrap 95% intervals; seed 20261112

## Inputs
- NASA GPM IMERG V07 Final Run daily (GPM_3IMERGDF.07), 0.1 degree cell at the district point (https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary)
- FAO-56 Penman-Monteith reference evaporation (ET0) computed from NASA POWER weather (https://www.fao.org/4/x0490e/x0490e00.htm)
- NASA POWER daily, AG community, district query point (https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- NASA SMAP L4 root-zone soil moisture (SPL4SMGP.008), district query point (https://nsidc.org/data/spl4smgp/versions/8)
- NASA MODIS MOD13Q1.061 NDVI (16-day, district polygon mean) (https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061)

## Metrics (held-out years only)
- weather features, 2001-2024: independent events with any district flagged: 2 of 2 (flood_aug2024 2024: 4 of 4 districts flagged; haor_flood_2017 2017: 1 of 1 districts flagged)
- weather features, 2001-2024: listed district-seasons flagged: 5 of 5 assessed (5 listed); rate 1.00 (95% interval 1.00 to 1.00, n = 5)
- weather features, 2001-2024: seasons flagged outside listed events: 118 of 355; rate 0.33 (95% interval 0.28 to 0.38, n = 355)
- weather features, 2001-2024: years: 2001 to 2024 (n = 24 years, 360 district-seasons)
- with SMAP and NDVI: independent events with any district flagged: 2 of 2 (flood_aug2024 2024: 4 of 4 districts flagged; haor_flood_2017 2017: 1 of 1 districts flagged)
- with SMAP and NDVI: listed district-seasons flagged: 5 of 5 assessed (5 listed); rate 1.00 (95% interval 1.00 to 1.00, n = 5)
- with SMAP and NDVI: seasons flagged outside listed events: 91 of 135; rate 0.67 (95% interval 0.59 to 0.75, n = 135)
- with SMAP and NDVI: years: 2015 to 2024 (n = 10 years, 140 district-seasons)

## Limits
- Cited events used: cumilla 2024 kharif2 flood_aug2024 (https://today.thefinancialexpress.com.bd/print/at-least-13-die-as-calamitous-floods-devastate-11-districts-1724435341); feni 2024 kharif2 flood_aug2024 (https://reliefweb.int/report/bangladesh/bangladesh-eastern-flash-floods-2024-situation-report-no-02-30-august-2024); noakhali 2024 kharif2 flood_aug2024 (https://reliefweb.int/report/bangladesh/bangladesh-eastern-flash-floods-2024-situation-report-no-02-30-august-2024); brahmanbaria 2024 kharif2 flood_aug2024 (https://reliefweb.int/report/bangladesh/flooding-eastern-bangladesh-feni-comilla-noakhali-habiganj-moulvibazar-khagracchari-and-rangamati-briefing-note-24082024); sylhet 2017 kharif1 haor_flood_2017 (https://www.dhakatribune.com/bangladesh/nation/19126/114-000-hectare-boro-crops-damaged-in-4-sylhet).
- Districts hit by the same regional event are not independent hits: the four Aug 2024 districts count as one event, so the district-season hit rate overstates the evidence (2 independent events in all).
- Rows not used (GAP, reason from the reference file): event.cold_wave.any_live_district: NOT USED: no source read on 12 Nov 2026 names a year (2001-2024) and one of the five live districts for crop damage from a cold wave; event.cold_wave_jan2026.sylhet: NOT USED (needs year check): Prothom Alo page says published 05 Jan 2026 and lists Sylhet among districts under a mild cold wave, but two photo captions are dated 2025, so the year is unconfirmed; event.cold_wave_feb2025.sylhet: NOT USED: TBS/UNB 8 Feb 2025 cold-wave district list is Rajshahi, Pabna, Naogaon, Dinajpur, Moulvibazar, Chuadanga.
- Cited events not scored: cumilla 2026 rabi cold_wave_jan2026: not scored (outside the data period 2001-2024; IMERG rain ends 2025-09-30).
- The event list is not a complete list of bad seasons, so flags outside it are an upper bound on false alarms.
- SMAP has 10 usable years and MODIS NDVI only the years in the status table, so the second feature set covers fewer seasons.
- Weather values are area values (IMERG 0.1 degree, POWER about 0.5 degree), not a field.
- With several features and a limit of 2, the rule flags a large share of ordinary seasons; the limit was not tuned on the events.
- Small sample (5 districts, 10 to 24 seasons): intervals are wide, and district-seasons of the same year are not independent, so the true uncertainty is larger. Needs local validation.
- It describes past seasons ("flags past seasons that look unusual", "estimated", "tested on"); it says nothing about a coming season.

# Model card: season_type_kmeans

- **Problem:** season types (hot, wet, typical) for past seasons
- **Method:** k-means on z-scores of season rain and mean Tmax; k from 2 to 5 by training silhouette
- **Used by the app:** yes: k-means types are better separated on held-out seasons and no less stable
- **Sample (n):** 360 district-seasons, 2001-2024
- **Validation:** leave-one-year-out; bootstrap 95% intervals; seed 20261112

## Inputs
- NASA GPM IMERG V07 Final Run daily (GPM_3IMERGDF.07), 0.1 degree cell at the district point (https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary)
- NASA POWER daily, AG community, district query point (https://power.larc.nasa.gov/docs/services/api/temporal/daily/)

## Metrics (held-out years only)
- stability (same type with and without the year): 0.99 (95% interval 0.99 to 1.00, n = 360)
- held-out silhouette (-1 to 1): 0.42 (95% interval 0.40 to 0.44, n = 360)
- k: 2 with all years; by held-out row: {2: 360}
- type centres with all years (z units): [{'rain_total_mm': 1.037, 'tmax_mean_c': -0.732}, {'rain_total_mm': -0.579, 'tmax_mean_c': 0.409}]

## Limits
- No ground truth exists for a season type; the scores measure consistency, not correctness.
- Season windows are our analysis windows, not a cited crop calendar.
- Small sample (5 districts, 10 to 24 seasons): intervals are wide, and district-seasons of the same year are not independent, so the true uncertainty is larger. Needs local validation.
- It describes past seasons ("flags past seasons that look unusual", "estimated", "tested on"); it says nothing about a coming season.

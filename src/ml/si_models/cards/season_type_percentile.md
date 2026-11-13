# Model card: season_type_percentile

- **Problem:** season types (hot, wet, typical) for past seasons
- **Method:** percentile rule: top 20% of the other years for rain and/or mean Tmax (cut: our choice)
- **Used by the app:** no: k-means types are better separated on held-out seasons and no less stable
- **Sample (n):** 360 district-seasons, 2001-2024
- **Validation:** leave-one-year-out; bootstrap 95% intervals; seed 20261112

## Inputs
- NASA GPM IMERG V07 Final Run daily (GPM_3IMERGDF.07), 0.1 degree cell at the district point (https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary)
- NASA POWER daily, AG community, district query point (https://power.larc.nasa.gov/docs/services/api/temporal/daily/)

## Metrics (held-out years only)
- stability (same type with and without the year): 0.97 (95% interval 0.95 to 0.99, n = 360)
- held-out silhouette (-1 to 1): 0.25 (95% interval 0.22 to 0.27, n = 360)
- share of seasons by type: {'typical': 0.575, 'wet': 0.203, 'hot': 0.2, 'hot and wet': 0.022}

## Limits
- No ground truth exists for a season type; the scores measure consistency, not correctness.
- Season windows are our analysis windows, not a cited crop calendar.
- Small sample (5 districts, 10 to 24 seasons): intervals are wide, and district-seasons of the same year are not independent, so the true uncertainty is larger. Needs local validation.
- It describes past seasons ("flags past seasons that look unusual", "estimated", "tested on"); it says nothing about a coming season.

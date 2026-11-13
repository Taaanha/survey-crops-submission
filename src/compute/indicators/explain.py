"""
src/compute/indicators/explain.py

Source records and one-line plain-English explainers for every W2 indicator family.
The family is the part of the indicator name before "__" (heat_days__wheat.heat.anthesis_tmax).
Wording rule: past-seasons language only; district numbers are "NASA data for the area around your field".
"""

IMERG = {"dataset": "NASA GPM IMERG V07 Final Run daily (GPM_3IMERGDF.07), 0.1 degree cell at the district point",
         "source_url": "https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGDF_07/summary"}
POWER = {"dataset": "NASA POWER daily, AG community, district query point",
         "source_url": "https://power.larc.nasa.gov/docs/services/api/temporal/daily/"}
ET0 = {"dataset": "FAO-56 Penman-Monteith reference evaporation (ET0) computed from NASA POWER weather",
       "source_url": "https://www.fao.org/4/x0490e/x0490e00.htm"}
SMAP = {"dataset": "NASA SMAP L4 root-zone soil moisture (SPL4SMGP.008), district query point",
        "source_url": "https://nsidc.org/data/spl4smgp/versions/8"}
MODIS = {"dataset": "NASA MODIS MOD13Q1.061 NDVI (16-day, district polygon mean)",
         "source_url": "https://www.earthdata.nasa.gov/data/catalog/lpcloud-mod13q1-061"}
GRACE = {"dataset": "NASA GRACE-FO JPL mascons (regional, about 300 km effective)",
         "source_url": "https://podaac.jpl.nasa.gov/dataset/TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4"}
ECOSTRESS = {"dataset": "NASA ECOSTRESS ET, ECO_L3T_JET.002 (units unresolved)",
             "source_url": "https://appeears.earthdatacloud.nasa.gov/api/product/ECO_L3T_JET.002"}
ETCCDI_URL = "http://etccdi.pacificclimate.org/list_27_indices.shtml"

EXPLAINERS = {
    "heat_days": "Days in the season window when the daily highest temperature was above a heat limit "
                 "that a paper reports for one crop stage; the limit is for that stage, the window is ours.",
    "night_heat_days": "Days in the season window when the daily lowest temperature stayed above a "
                       "hot-night limit reported for a crop stage; the limit is for that stage, the window is ours.",
    "cold_nights": "Days in the season window when the daily lowest temperature fell below a cold limit "
                   "reported for a crop stage; the limit is for that stage, the window is ours.",
    "extreme_rain_days_r20mm": "Days with 20 mm of rain or more (standard ETCCDI index R20mm, "
                               "not a Bangladesh-specific limit).",
    "heavy_rain_days_bmd": "Days with rain at or above the BMD heavy-rain limit (a cited row, from a news report of the BMD "
                           "scale). IMERG is a cell mean, not point rainfall, so it may undercount point extremes. "
                           "Shown beside R20mm, which uses a lower, standard limit.",
    "rx1day": "The heaviest single day of rain in the season window (ETCCDI Rx1day, here per season "
              "window rather than per month; not a Bangladesh-specific limit).",
    "cdd": "The longest run of days in a row with less than 1 mm of rain (ETCCDI CDD, counted inside "
           "the season window).",
    "et0_season_total": "How much water the air could pull from a well-watered grass surface over the "
                        "season window (FAO-56 reference evaporation).",
    "rain_minus_et0": "Season rain minus season reference evaporation: a simple climate balance, not the "
                      "Kc-weighted crop balance (that is the crop water use in W4).",
    "smap_rootzone_z": "How wet the root zone was this season compared with the same season in the other "
                       "years (z-score; context, only about ten usable SMAP years, so always check n).",
    "modis_ndvi_z": "How green the land was compared with other years (MODIS NDVI z-score). "
                    "Its status and years present come from the data status table; only some years are downloaded.",
    "grace_fo_trend": "Trend of regional water storage (GRACE-FO, about 300 km effective, shared by "
                      "neighbouring districts; not district groundwater).",
    "ecostress_et_comparison": "How our evaporation estimate compares with ECOSTRESS satellite "
                               "evaporation on the demo fields. Not assessed: the ECOSTRESS evaporation units are unresolved.",
    "trend:rain": "Whether season rain (NASA IMERG) shows a steady change, a level shift, or neither.",
    "trend:tmean": "Whether season mean temperature (NASA POWER) shows a steady change, a level shift, or neither.",
    "trend:et0": "Whether season reference evaporation shows a steady change, a level shift, or neither.",
}


def family(indicator):
    return indicator.split("__")[0]


def explain(indicator):
    """One-line explainer for an indicator name (family before '__')."""
    return EXPLAINERS[family(indicator)]

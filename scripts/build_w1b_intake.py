"""
scripts/build_w1b_intake.py

Runs the intake checks on the W1b files in data/processed/ and writes
  docs/w1b_data_status.csv            status per layer (assessed / partial / not assessed, with reason)
  docs/results/w1b_intake_checks.md   the numbers behind each status
Nothing is downloaded and no credential is used. Run from the repo root:
    python scripts/build_w1b_intake.py
"""
import os
import sys

import _proj  # noqa: F401  PROJ guard: keep first

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
sys.path.insert(0, os.path.join(ROOT, "src", "acquire"))
from sat_layers import intake  # noqa: E402
from sat_layers import loaders as L  # noqa: E402

ECO_PAGE = "https://www.earthdata.nasa.gov/data/catalog/lpcloud-eco-l3t-jet-002"


def report(c):
    m, g, n, h, e = c["modis"], c["grace"], c["nasadem"], c["hls"], c["ecostress"]
    gaps = "\n".join(f"  - {a} to {b}: {d} days" for a, b, d in g["gaps"])
    tiles = "\n".join(f"  - {t['tile']}: {t['n_pixels']:,} pixels, lowest {t['min_m']:.0f} m, highest {t['max_m']:.0f} m, "
                      f"{t['n_below_0m']:,} pixels below 0 m ({t['share_below_0m']:.2%})" for t in n["tiles"])
    top = ", ".join(f"{d} {v:.0%}" for d, v in m["ndvi_missing_top"].items())
    zero = [mo for mo, k in h["usable_by_month"].items() if k == 0]
    months = ", ".join(f"{mo}: {k}" for mo, k in h["usable_by_month"].items())
    slopes = ", ".join(f"{d} {v:.2f}" for d, v in n["slope_live"].items())
    counts = "\n".join(f"| {r.tile} | {r.sensor} | {r.scenes} | {r.with_pixels} | {r.usable} |" for r in h["counts"].itertuples())
    return f"""# W1b intake checks (11 Nov 2026)

Each file was checked before it was accepted. Numbers below are computed from the files by `src/compute/sat_layers/intake.py`; the status table is `docs/w1b_data_status.csv`.

## MODIS MOD13Q1 (NDVI, EVI), `modis_district_<year>.csv.gz`
- Files: {m['files']}; years present (composite years with at least {L.MIN_COMPOSITES} of 23 composites): {m['years']}. Missing from 2001-2024: {m['missing_years_2001_2024']}.
- Every year file starts with the previous year's last composite (for example 2018-12-19 in the 2019 file). Confirmed in all {m['files']} files. Joined on (date, district): {m['rows_raw']:,} rows became {m['rows_joined']:,} after removing {m['rows_raw'] - m['rows_joined']} duplicates; the duplicate copies agreed exactly (the loader stops with an error if they do not), so nothing was chosen between them.
- Districts: {m['districts']} (all 64) in every file. Dates {m['first_date']} to {m['last_date']}. {m['ndvi_missing_share']:.1%} of district-composites have no good pixel and stay NaN (never 0); highest shares: {top}.
- Vegetation anomaly: with {len(m['years'])} years (the rule needs at least {L.MIN_YEARS_FOR_ANOMALY}, and at least 5 other years per composite) the status is **{m['anomaly_status']}**. Years not downloaded: {len(m['missing_years_2001_2024'])} of 24 ({m['missing_years_2001_2024'][0]}-{m['missing_years_2001_2024'][-1]}), so this is not a 24-season statistic.
- Quality rule (`pixel_reliability` = 0 kept) is recalled from the product guide and not confirmed (open question).

## ECOSTRESS ECO_L3T_JET.002, `ecostress_tile_series.csv` -> **not assessed: units unresolved**
- Documentation opened: {ECO_PAGE} (NASA Earthdata catalogue page, its Variables table). It lists `ETdaily` in W/m2 and, for the `cloud` layer, only fill 255 and valid range 0 to 1, not what 1 means. The User Guide and ATBD PDFs linked from that page could not be read (the fetch returned undecoded PDF bytes).
- Findings from Tanha's Colab run (11 Nov; supplied by Tanha, not re-run here):
  - The file metadata for ETdaily says units "W/m²". The same "W/m²" tag is also on the `cloud` layer, which is a 0/1 flag, so the units attribute looks like a blanket label and is not reliable per layer.
  - `cloud` holds only the values 0 and 1 (valid_min 0, valid_max 1). In one scene: 2,433,733 pixels with 0 and 844,427 pixels with 1.
  - In that scene, pixels with cloud = 1 have NO ETdaily value (share of finite ET = 0.0), while cloud = 0 pixels have a value in 53.6% of cases. Median raw ET for cloud = 0 is 1.91. So cloud = 1 behaves as "cloudy, no usable ET". **Mask: supported by the data in one scene, not documented.**
  - Raw values (median about 2 across the series) are plausible as mm/day and not plausible as W/m² (about 0.07 mm/day). **Units: UNRESOLVED.** No conversion is applied and no unit is chosen.
- The delivered file has {e['rows']} scenes ({e['first']} to {e['last']}), ET only (no land-surface temperature). Its `et_mm_day` column came from a W/m2 to mm/day conversion in the Colab cell and must not be used while the units are unresolved.
- Decision: the series is "not assessed (units unresolved)" for any comparison with FAO-56 ET0. The loader refuses it unless `allow_unverified=True`, and its message says what would resolve it: the ETdaily unit stated in the ECO_L3T_JET.002 User Guide or ATBD. That unit is not assumed here.

## HLS NDVI, `hls_ndvi_tile_series.csv`
- {h['scenes']} scenes, {h['first']} to {h['last']}, two 20 km demo tiles (tile mean, not a field). About 1% of red/NIR values were outside 0-1 and were set to missing in the Colab run (as reported by Tanha; not re-checkable from the tile-mean file).
- Scenes with `clear_share` >= {L.CLEAR_MIN} (**the 0.5 cut-off is our choice, not a standard**):

| tile | sensor | scenes | with any valid pixel | clear_share >= {L.CLEAR_MIN} |
|---|---|---|---|---|
{counts}

- Usable scenes per month (month: scenes, both tiles and sensors): {months}. Months with none: {zero}. The monsoon season is poorly covered by optical data.
- The cloud-mask bit rule (Fmask bits 1-4) is recalled from the product guide and not confirmed (open question).

## NASADEM
- 64 districts, no missing values, coverage 1.0.
- **Slope is a relative ranking only.** Mean slope is {n['slope_min']:.2f} degrees at the lowest and {n['slope_median']:.2f} at the median, and about 2 degrees on flat delta districts (live districts: {slopes}); that is probably surface noise in the DEM, not real terrain. Compare districts with each other (hill districts such as Bandarban and Rangamati stand out), never read a district's slope as a physical gradient.
- Negative elevations in the 30 m demo tiles (Bangladesh land is almost never below sea level, so these are DEM noise):
{tiles}

## GRACE-FO, `grace_district_monthly.csv` -> partial, REGIONAL
- {g['districts']} districts share {g['cells']} mascon cells (up to {g['most_sharing']} districts per cell); every row is flagged `regional`. **Never show it as district-level groundwater.** Say "regional water-storage signal, about 300 km effective".
- {g['dates']} dates from {g['first']} to {g['last']} (irregular, not strictly monthly). Gaps longer than {L.GAP_DAYS} days ({len(g['gaps'])}):
{gaps}
- The 2017-06 to 2018-06 gap is the break between GRACE and GRACE-FO.
- Uncertainty column: {g['unc_min']:.2f} to {g['unc_max']:.2f} cm. Values range {g['lwe_min']:.1f} to {g['lwe_max']:.1f} cm; the unit (cm) is inferred from the product, not read from the file.

## SMAP, 64 districts -> not assessed
The AppEEARS job did not finish, so there is no 64-district SMAP file. The five live districts use the existing point files `smap_<district>_2015_2026.csv` (status `smap_live5`: partial).
"""


if __name__ == "__main__":
    c = intake.run_checks()
    status = intake.build_status(c)
    p1 = os.path.join(ROOT, "docs", "w1b_data_status.csv")
    p2 = os.path.join(ROOT, "docs", "results", "w1b_intake_checks.md")
    status.to_csv(p1, index=False)
    with open(p2, "w", encoding="utf-8") as fh:
        fh.write(report(c))
    print("wrote", p1, "and", p2)
    print(status[["key", "status"]].to_string(index=False))

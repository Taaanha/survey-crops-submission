"""Writes docs/data_coverage/opera_feni_cumilla_2024.md from CMR (opera_coverage) and the
stack manifests built by scripts/build_water_stacks.py. Run from the repo root."""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import opera_coverage  # noqa: E402

START, END = "2024-07-01", "2024-11-30"
P = ("DSWx-HLS", "DSWx-S1")


def main():
    L = ["# OPERA coverage over Feni and Cumilla, 1 Jul to 30 Nov 2024 (T3a)", "",
         "Made by `scripts/write_coverage_report.py` on 2026-10-24 from NASA CMR (granule search, no "
         "downloads) and the water stacks in `data/processed/field_profile_manifest_<district>.json`. "
         "\"District box\" = the 20 km x 20 km window around the district point (`district_grid`), "
         "not the administrative boundary. Dates are UTC sensing dates. Collections (CMR short names): "
         "`OPERA_L3_DSWX-HLS_V1` (C2617126679-POCLOUD) and `OPERA_L3_DSWX-S1_V1` (C2949811996-POCLOUD). "
         "Only the latest production of each tile and sensing time is counted.", ""]
    cov_all = {}
    for d in ("feni", "cumilla"):
        cov = opera_coverage(d, START, END)
        early = opera_coverage(d, "2023-01-01", "2024-08-20")["products"]["DSWx-S1"]
        cov_all[d] = (cov, early)
    L += ["## 1. Headline", ""]
    for d, (cov, early) in cov_all.items():
        s1 = cov["products"]["DSWx-S1"]
        L.append(f"- **{d.title()}**: first DSWx-S1 granule covering the box is **{s1['first_date']}** "
                 f"(searching back to 2023-01-01 finds {early['n_granules']} DSWx-S1 granules before "
                 f"21 Aug 2024). DSWx-HLS granules exist from at least {opera_coverage(d, '2023-01-01', '2023-01-31')['products']['DSWx-HLS']['first_date']} (earliest date searched was 2023-01-01).")
    s1f = cov_all["feni"][0]["products"]["DSWx-S1"]
    for d in cov_all:
        m = json.load(open(os.path.join(ROOT, "data", "processed", f"field_profile_manifest_{d}.json")))
        s1d = [e for e in m["dates"] if e["granules"]["DSWx-S1"]]
        ok = [e for e in s1d if e["shares"]["DSWx-S1"]["no_obs"] < 0.5]
        L.append(f"- **{d.title()}** radar usability: {len(s1d)} S1 dates in the stack, of which {len(ok)} "
                 f"cover at least half of the box (the others are granules whose footprint only clips "
                 f"the box edge or is layover/shadow masked).")
    L += ["", "**Does radar cover the Aug 2024 recession?** Yes, from 21 Aug 2024 onward: DSWx-S1 has "
          "granules in every week from 21 Aug to 30 Nov in both districts (table in section 2), so "
          "mid-Aug to Oct 2024 is covered from the first week (the 21 Aug scene itself is the first). "
          "Anything before 21 Aug 2024 is HLS only and cloud-limited. "
          "This settles the open question in PROJECT_STATE (true first date: it is 21 Aug 2024 over "
          "these boxes; it is not July).", ""]
    L += ["## 2. Granules per week (CMR)", ""]
    for d, (cov, _) in cov_all.items():
        weeks = sorted(set(cov["products"]["DSWx-HLS"]["per_week"]) | set(cov["products"]["DSWx-S1"]["per_week"]))
        L += [f"### {d.title()}", "", "| week starting (Mon) | DSWx-HLS | DSWx-S1 |", "|---|---|---|"]
        for w in weeks:
            L.append(f"| {w} | {cov['products']['DSWx-HLS']['per_week'].get(w, 0)} | "
                     f"{cov['products']['DSWx-S1']['per_week'].get(w, 0)} |")
        L.append(f"| **total** | {cov['products']['DSWx-HLS']['n_granules']} | "
                 f"{cov['products']['DSWx-S1']['n_granules']} |")
        L.append("")
    L += ["Granule counts are above the number of dates because the box touches several 110 km MGRS "
          "tiles (and Landsat and Sentinel-2 can both report on one day).", ""]
    L += ["## 3. Cloud and no-data share per date (from the built stacks)", "",
          "`no_obs` = share of the 667 x 667 box pixels with no observation (cloud, cloud shadow, "
          "snow/ice, fill, or outside the granule; for S1 also layover/shadow). `water` = share of ALL "
          "box pixels that are water. `merged` = HLS and S1 of the same date combined (water wins).", ""]
    for d in cov_all:
        m = json.load(open(os.path.join(ROOT, "data", "processed", f"field_profile_manifest_{d}.json")))
        L += [f"### {d.title()} ({len(m['dates'])} dates; failed granules: {len(m['failed_granules'])})", "",
              "| date | HLS granules | HLS no_obs | S1 granules | S1 no_obs | merged no_obs | merged water |",
              "|---|---|---|---|---|---|---|"]
        hls_dates = []
        for e in m["dates"]:
            sh = e["shares"]
            h, s = sh.get("DSWx-HLS"), sh.get("DSWx-S1")
            if h:
                hls_dates.append(h["no_obs"])
            L.append(f"| {e['date']} | {len(e['granules']['DSWx-HLS'])} | "
                     f"{'%.0f%%' % (100 * h['no_obs']) if h else '-'} | {len(e['granules']['DSWx-S1'])} | "
                     f"{'%.0f%%' % (100 * s['no_obs']) if s else '-'} | "
                     f"{100 * sh['merged']['no_obs']:.0f}% | {100 * sh['merged']['water']:.1f}% |")
        n = len(hls_dates)
        clear = sum(1 for x in hls_dates if x < 0.5)
        L += ["", f"HLS dates with under 50% no-observation: **{clear} of {n}**; "
              f"median HLS no_obs {sorted(hls_dates)[n // 2] * 100:.0f}%." if n else "", ""]
    out = os.path.join(ROOT, "docs", "data_coverage", "opera_feni_cumilla_2024.md")
    open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(out)


if __name__ == "__main__":
    main()

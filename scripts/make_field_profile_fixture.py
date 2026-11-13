"""Cuts the small offline test fixture for src/compute/field_profile (T3a).

Finds a 50 x 50 pixel window around a main river channel in Feni (a pixel that is water on
most observed dates, with some land in the window), keeps a few dates that have at most one
granule per product, and saves the raw WTR codes of those granules plus the merged result to
tests/fixtures/field_profile/. Needs the cached raw windows from scripts/build_water_stacks.py.

Run from the repo root: python scripts/make_field_profile_fixture.py
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src", "compute"))
from field_profile import encode_hls, encode_s1, merge_water  # noqa: E402

DISTRICT, N, N_DATES = "feni", 50, 5
BASE = os.path.join(ROOT, "data", "raw", "opera_stacks", DISTRICT)
OUT = os.path.join(ROOT, "tests", "fixtures", "field_profile")


def main():
    manifest = json.load(open(os.path.join(ROOT, "data", "processed",
                                           f"field_profile_manifest_{DISTRICT}.json")))
    stack = np.load(os.path.join(BASE, f"water_stack_{manifest['start']}_{manifest['end']}.npz"))
    dates, water = list(stack["dates"]), stack["water"]
    observed = water != 255
    n_obs = observed.sum(0)
    share = np.where(n_obs >= 8, (water == 1).sum(0) / np.maximum(n_obs, 1), 0)
    cand = np.argwhere(share > 0.6)
    h, w = share.shape
    best = None
    for y, x in cand[::3]:
        if not (N // 2 <= y < h - N // 2 and N // 2 <= x < w - N // 2):
            continue
        win = share[y - N // 2:y + N // 2, x - N // 2:x + N // 2]
        frac_water = (win > 0.5).mean()
        if 0.02 <= frac_water <= 0.5 and (best is None or n_obs[y, x] > best[0]):
            best = (n_obs[y, x], y, x)
    if best is None:
        sys.exit("no river window found")
    _, y, x = best
    y0, x0 = y - N // 2, x - N // 2
    entries = {e["date"]: e for e in manifest["dates"]}
    # dates with one granule per product at most, and few missing pixels at the channel
    picks = [d for d in dates if all(len(v) <= 1 for v in entries[d]["granules"].values())
             and water[dates.index(d), y, x] != 255]
    # spread them over the season, prefer ones with both products
    both = [d for d in picks if all(entries[d]["granules"].values())]
    picks = sorted(set(both[:: max(1, len(both) // N_DATES)][:N_DATES]
                       + [d for d in picks if d not in both][:2]))[:N_DATES + 2]
    hls_raw, s1_raw, merged, used = [], [], [], []
    for d in picks:
        e = entries[d]
        parts, raws = [], {}
        for key, product, enc in (("hls", "DSWx-HLS", encode_hls), ("s1", "DSWx-S1", encode_s1)):
            ids = e["granules"][product]
            if ids:
                raw = np.load(os.path.join(BASE, "raw_windows", ids[0] + ".npz"))["wtr"]
                raw = raw[y0:y0 + N, x0:x0 + N]
                parts.append(enc(raw))
            else:
                raw = np.full((N, N), 255, np.uint8)
            raws[key] = raw
        hls_raw.append(raws["hls"])
        s1_raw.append(raws["s1"])
        merged.append(merge_water(*parts))
        used.append({"date": d, "granules": e["granules"], "source_urls": e["source_urls"]})
    os.makedirs(OUT, exist_ok=True)
    np.savez_compressed(os.path.join(OUT, "feni_river_50x50.npz"), hls_raw=np.stack(hls_raw),
                        s1_raw=np.stack(s1_raw), merged=np.stack(merged))
    grid = dict(manifest["grid"])
    t = list(grid["transform"])
    t[2] += x0 * grid["res"]
    t[5] -= y0 * grid["res"]
    grid.update(transform=t, width=N, height=N)
    meta = {"district": DISTRICT, "note": "window cut from the 20 km Feni grid; see MODULE.md",
            "window_origin_rowcol_in_district_grid": [int(y0), int(x0)],
            "channel_pixel": [N // 2, N // 2], "grid": grid, "dates": used}
    json.dump(meta, open(os.path.join(OUT, "feni_river_meta.json"), "w"), indent=1)
    print("fixture:", picks, "window origin", y0, x0)


if __name__ == "__main__":
    main()
